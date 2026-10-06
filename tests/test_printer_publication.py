from pathlib import Path
import tempfile,sys,unittest,os
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_publish import Publisher

class Publication(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.p=Publisher(self.root,lambda:True,validate=lambda preview,root:dict(validated=True))
    def tearDown(self):self.temp.cleanup()
    def files(self):return {'hardware.cfg':'[printer]\nkinematics: none\nmax_velocity: 1\nmax_accel: 1\n'}
    def test_single_activation_preserves_unmanaged_text_and_restoration_receipt(self):
        original=b'# My notes\n[gcode_macro USER_MACRO]\ngcode: G4 P0\n';(self.root/'printer.cfg').write_bytes(original)
        preview=self.p.preview(self.files(),{'boot':'one'},'plan');self.assertEqual((self.root/'printer.cfg').read_bytes(),original)
        receipt=self.p.apply(preview['review'],self.files(),{'boot':'one'},'plan')
        self.assertTrue((self.root/'printer.cfg').read_bytes().startswith(original));self.assertEqual(receipt['activation_before'],original.decode());self.assertEqual(receipt['service_action'],'none');self.assertFalse((self.root/'printer-managed/journal.json').exists())
    def test_restore_preserves_original_permissions_and_service_read_access(self):
        original=b'# Original notes\n';activation=self.root/'printer.cfg';activation.write_bytes(original);activation.chmod(0o640)
        before=activation.stat();preview=self.p.preview(self.files(),{},'plan')
        receipt=self.p.apply(preview['review'],self.files(),{},'plan')
        self.assertEqual(activation.stat().st_mode & 0o777,0o640)
        for relative in receipt['after']:
            self.assertEqual((self.root/relative).stat().st_mode & 0o777,0o640)
        self.assertEqual((self.root/'printer-managed').stat().st_mode & 0o777,0o750)
        self.assertEqual((self.root/'printer-managed/receipt.json').stat().st_mode & 0o777,0o600)
        restore=self.p.restore_preview({});self.p.restore(restore['review'],{})
        self.assertEqual(activation.read_bytes(),original)
        self.assertEqual((activation.stat().st_uid,activation.stat().st_gid),(before.st_uid,before.st_gid))
        self.assertEqual(activation.stat().st_mode & 0o777,0o640)
    def test_restore_removes_only_new_activation_when_original_missing(self):
        preview=self.p.preview(self.files(),{},'plan');self.p.apply(preview['review'],self.files(),{},'plan')
        restore=self.p.restore_preview({});self.p.restore(restore['review'],{})
        self.assertFalse((self.root/'printer.cfg').exists())
    def test_active_service_stale_review_and_drift_refuse(self):
        preview=self.p.preview(self.files(),{},'plan');self.p.admit=lambda:False
        with self.assertRaisesRegex(ValueError,'stopped'):self.p.apply(preview['review'],self.files(),{},'plan')
        self.p.admit=lambda:True;(self.root/'printer.cfg').write_text('# Manual edit\n')
        with self.assertRaisesRegex(ValueError,'stale'):self.p.apply(preview['review'],self.files(),{},'plan')
    def test_unknown_section_and_includes_conflict_before_writes(self):
        (self.root/'printer.cfg').write_text('[printer]\nkinematics: cartesian\n')
        with self.assertRaisesRegex(ValueError,'Unmanaged'):self.p.preview(self.files(),{},'p')
        (self.root/'printer.cfg').write_text('[include ../secret.cfg]\n')
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.p.preview(self.files(),{},'p')
    def test_failure_after_activation_is_journaled_and_recoverable(self):
        original=b'# Preserved\n';(self.root/'printer.cfg').write_bytes(original);preview=self.p.preview(self.files(),{},'p')
        import sv08_printer_publish as module
        real=module.atomic_json
        def fail(path,value):
            if path.name=='receipt.json':raise OSError('fixture write failure')
            return real(path,value)
        with patch.object(module,'atomic_json',side_effect=fail):
            with self.assertRaises(OSError):self.p.apply(preview['review'],self.files(),{},'p')
        self.assertTrue((self.root/'printer-managed/journal.json').exists());self.assertNotEqual((self.root/'printer.cfg').read_bytes(),original)
        self.p.reconcile();self.assertEqual((self.root/'printer.cfg').read_bytes(),original)
    def test_mixed_or_external_drift_refuses_blind_recovery(self):
        preview=self.p.preview(self.files(),{},'p')
        with patch('sv08_printer_publish.put',side_effect=OSError('fixture')):
            with self.assertRaises(OSError):self.p.apply(preview['review'],self.files(),{},'p')
        (self.root/'printer.cfg').write_text('# unrelated writer\n')
        with self.assertRaisesRegex(ValueError,'Unexpected edits'):self.p.reconcile()
    def test_missing_or_rejected_complete_validation_cannot_publish(self):
        preview=self.p.preview(self.files(),{},'p');self.p.validate=None
        with self.assertRaisesRegex(ValueError,'validation'):self.p.apply(preview['review'],self.files(),{},'p')
        self.assertFalse((self.root/'printer-managed').exists())
        self.p.validate=lambda preview,root:dict(validated=False)
        with self.assertRaisesRegex(ValueError,'validation'):self.p.apply(preview['review'],self.files(),{},'p')
        self.assertFalse((self.root/'printer.cfg').exists())
    def test_links_and_startup_templates_refused(self):
        (self.root/'printer.cfg').symlink_to('/dev/null')
        with self.assertRaisesRegex(ValueError,'link'):self.p.preview(self.files(),{},'p')
        (self.root/'printer.cfg').unlink()
        with self.assertRaisesRegex(ValueError,'startup'):self.p.preview({'hardware.cfg':'[delayed_gcode startup]\ngcode: G28\n'},{},'p')

class PinnedValidation(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('SV08_PRINTER_VALIDATION_PYTHON'),'Explicit existing pinned environment required')
    def test_complete_output_parser_and_unsupported_semantics(self):
        from sv08_printer_publish import validate_output
        from sv08_printer_generate import generate
        from sv08_printer_catalog import Catalog
        from test_printer_configuration import full_draft
        source=Path(os.environ['SV08_PRINTER_SOURCE_ROOT']);python=os.environ['SV08_PRINTER_VALIDATION_PYTHON']
        dictionary=source/'artifacts/test-sv08-01-mcu-usb-v1/klipper.dict';klippy=source/'upstream/klipper/klippy/klippy.py'
        with tempfile.TemporaryDirectory() as temporary:
            publisher=Publisher(temporary);output=generate(Catalog(ROOT/'catalog/printer/catalog.json'),full_draft(),'full')
            self.assertTrue(output['complete']);preview=publisher.preview({'hardware.cfg':output['text']},{},'test')
            self.assertTrue(validate_output(preview,Path(temporary),python,str(klippy),str(dictionary))['validated'])
            # Exercise the generated Jinja hook through the same complete parser.
            from sv08_printer_definitions import builtins
            from sv08_printer_catalog import digest
            policy=next(d for d in builtins(Catalog(ROOT/'catalog/printer/catalog.json')) if d['id']=='sv08-main.bed_assembly')
            policy={**policy,'id':'parser-check','kind':'behaviour','category':'probe','behaviours':[dict(hook='levelling.preconditions',operation='check',sensor='bed_check',comparison='at_least',threshold=25,abort='error',sources=['software-fixture'])]}
            policy.pop('components');policy.pop('connections')
            candidate=full_draft();candidate['definition_plan']=dict(format_version=1,selections=[dict(source='fixture',id=policy['id'],version=policy['version'],sha256=digest(policy),commit='a'*40)],snapshots={'fixture::'+policy['id']+'@'+policy['version']:policy})
            composed=generate(Catalog(ROOT/'catalog/printer/catalog.json'),candidate,'full')
            self.assertTrue(composed['complete']);self.assertIn('[gcode_macro SV08_LEVELLING_PRECONDITIONS]',composed['text'])
            hook=publisher.preview({'hardware.cfg':composed['text']},{},'check-only-hook')
            self.assertTrue(validate_output(hook,Path(temporary),python,str(klippy),str(dictionary))['validated'])
            bad=publisher.preview({'hardware.cfg':output['text'].replace('kinematics: corexy','kinematics: impossible')},{},'bad')
            with self.assertRaisesRegex(ValueError,'validation'):validate_output(bad,Path(temporary),python,str(klippy),str(dictionary))
            unsupported=publisher.preview({'hardware.cfg':output['text']+'\n[temperature_host]\n'},{},'unsupported')
            with self.assertRaisesRegex(ValueError,'does not support'):validate_output(unsupported,Path(temporary),python,str(klippy),str(dictionary))

if __name__=='__main__':unittest.main()
