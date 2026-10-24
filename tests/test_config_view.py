"""Finite endpoint boundary tests; no installed paths or printer access."""
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import sv08_view as view


class ViewTests(unittest.TestCase):
    def test_read_allowlist_constructs_fixed_child_requests(self):
        for area in view.SCRIPTS:
            with self.subTest(area=area), patch.object(view.subprocess, 'run') as run:
                run.return_value = subprocess.CompletedProcess([], 0, '{"ok":true,"result":{}}', '')
                self.assertEqual(view.read({'area': area, 'method': 'status'}), {})
                args, kw = run.call_args
                self.assertEqual(args[0][:3], ['/usr/bin/python3', '-I', '-c'])
                self.assertEqual(args[0][3], view.child_code(area))
                self.assertEqual(kw['env'], view.ENV)
                self.assertEqual(kw['cwd'], '/')
                self.assertEqual(json.loads(kw['input']), {'action': 'status'} if area == 'printer' else {'method': 'status'})
                self.assertNotIn('PYTHONPATH', kw['env'])
                self.assertNotIn('PYTHONHOME', kw['env'])
        for method in ('jobs', 'upload.list'):
            self.assertEqual(view.validate({'area':'host','method':method}), ('host', method))

    def test_mutations_exports_paths_modules_and_extra_fields_denied_before_child(self):
        attempts = [None, [], {}, {'area':'host','method':'status','path':'/etc/shadow'},
                    {'area':'host','method':'status','module':'os'},
                    {'area':'host','method':'status','request':{'method':'apply'}},
                    {'area':'../../sv08_admin','method':'status'}, {'area':[], 'method':'status'}]
        for area in view.SCRIPTS:
            for method in ('apply','save','restore','plan','wifi.scan','restart','reconciliation-export','bundle.export','bundle.restore','certificate.create','settings','source_add','configuration_export','publication_apply'):
                attempts.append({'area':area,'method':method})
        with patch.object(view.subprocess, 'run') as run:
            for request in attempts:
                with self.subTest(request=request), self.assertRaises(ValueError): view.read(request)
            run.assert_not_called()

    def test_private_response_refused_and_future_fields_not_exposed(self):
        self.assertEqual(view.public('identity','status',{'ca_fingerprint':'public','private_key':'secret'}), {'ca_fingerprint':'public'})
        for key in view.SECRET_FIELDS:
            with self.subTest(key=key), self.assertRaises(ValueError):
                view.public('printer','status', {'state':{'nested':[{key:'secret'}]}})
        status={'mode':'certificate','username':'sv08','certificates':[{'id':'a','label':'Browser','fingerprint':'public','expires':42,'revoked':False}]}
        self.assertEqual(view.public('mainsail-access','status',status),status)

    def test_compatible_component_choices_survive_public_printer_read(self):
        choices={'sv08-main':[{'id':'bed_assembly','devices':[]}]}
        self.assertEqual(view.public('printer','status',{'available_components':choices,'unreviewed_future_field':'hidden'}),{'available_components':choices})
        status={'state':'conflict','message':'Review unsupported SAVE_CONFIG changes before printing.'}
        self.assertEqual(view.public('printer','status',{'native_calibration_status':status,'private_debug_log':'hidden'}),{'native_calibration_status':status})

    def test_public_certificate_is_exact_and_never_private(self):
        certificate={'filename':'sv08-printer-ca.crt','content':'-----BEGIN CERTIFICATE-----\nQUFB\n-----END CERTIFICATE-----\n'}
        self.assertEqual(view.public('identity','ca.download',certificate),certificate)
        for content in ['-----BEGIN PRIVATE KEY-----\nQUFB\n-----END PRIVATE KEY-----\n',certificate['content']+'secret']:
            with self.assertRaises(ValueError): view.public('identity','ca.download',{**certificate,'content':content})
        with self.assertRaises(ValueError): view.public('identity','ca.download',{**certificate,'private_key':'secret'})
        self.assertEqual(view.validate({'area':'identity','method':'ca.download'}),('identity','ca.download'))

    def test_software_inspection_accepts_only_exact_receipt(self):
        request={'area':'software','method':'inspect','id':'a'*32}
        self.assertEqual(view.validate(request),('software','inspect'))
        for ident in ['../secret','a'*31,'A'*32,None,[], 'a'*32+'\n']:
            with self.assertRaises(ValueError):view.validate({**request,'id':ident})
        with self.assertRaises(ValueError):view.validate({**request,'path':'/etc/shadow'})

    def test_child_error_is_sanitized(self):
        with patch.object(view.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'{"ok":false,"error":"password secret /private/path"}','private stderr')):
            with self.assertRaisesRegex(ValueError, '^Read unavailable$'): view.read({'area':'host','method':'status'})

    def test_duplicate_fields_rejected(self):
        with self.assertRaises(ValueError): json.loads('{"area":"host","area":"identity","method":"status"}',object_pairs_hook=view.unique)

    def test_entry_cli_and_nonroot_refused_without_child(self):
        for argv, uid in [(['view.py','--worker'],0),(['view.py'],1000)]:
            with patch.object(sys,'argv',argv), patch.object(view.os,'geteuid',return_value=uid), patch.object(view,'read') as read, patch('sys.stdout',new_callable=io.StringIO) as out:
                self.assertEqual(view.main(),0)
                self.assertFalse(json.loads(out.getvalue())['ok']); read.assert_not_called()

    def test_access_adapter_does_not_recover_or_submit(self):
        code=view.child_code('mainsail-access')
        self.assertNotIn('recover',code); self.assertNotIn('.request(',code)
        self.assertIn('b.load()',code); self.assertIn('b.status(',code)

    @unittest.skipIf(view.os.geteuid()==0, 'Requires ordinary execution identity')
    def test_existing_helpers_still_refuse_ordinary_invocation(self):
        root=Path(__file__).resolve().parents[1]/'runtime'
        for script in view.SCRIPTS.values():
            with self.subTest(script=script):
                result=subprocess.run([sys.executable,str(root/Path(script).name)],input='{"method":"status"}',text=True,capture_output=True,timeout=5)
                self.assertFalse(json.loads(result.stdout)['ok'])
                self.assertNotIn('"ok": true',result.stdout)

    def test_environment_hooks_not_used_by_entry(self):
        with patch.dict(view.os.environ,{'PYTHONPATH':'/evil','PYTHONHOME':'/evil','LD_PRELOAD':'/evil','PATH':'/evil'}), patch.object(view.subprocess,'run') as run:
            run.return_value=subprocess.CompletedProcess([],0,'{"ok":true,"result":{}}','')
            view.read({'area':'network','method':'status'})
            self.assertEqual(run.call_args.kwargs['env'],view.ENV)
            self.assertNotIn('LD_PRELOAD',run.call_args.kwargs['env'])


if __name__ == '__main__': unittest.main()
