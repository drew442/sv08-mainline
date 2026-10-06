import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
spec=importlib.util.spec_from_file_location('stage_printer',ROOT/'scripts/stage_printer_ui.py');stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)

class StageTests(unittest.TestCase):
    def fixture(self,root):
        for folder in ('runtime','ui/host'):
            for source in (ROOT/folder).glob('*'):
                if not source.is_file():continue
                target=root/('usr/lib/sv08' if folder=='runtime' else 'usr/share/cockpit/sv08-host')/source.name
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
        for name,raw in [('etc/cockpit/cockpit.conf','[WebService]\nShell=/sv08-host/index.html\n'),('usr/lib/sv08/admin-context.json','{"format_version":1,"context":"host"}')]:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(raw)
        return stage.inventory(root,[str(p.relative_to(root)) for p in root.rglob('*')])
    def test_fresh_restore_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);expected=self.fixture(root)
            backend=root/'usr/lib/sv08/sv08_printer_store.py';backend_inode=backend.stat().st_ino
            report=stage.stage(root,expected,True,True)
            self.assertEqual(backend.stat().st_ino,backend_inode)
            html=(root/'usr/share/cockpit/sv08-host/index.html').read_text()
            self.assertIn('id="printer"',html);self.assertEqual(html.count('src="session.js"'),1)
            target=root/'usr/share/cockpit/sv08-printer/app.js';raw=target.read_bytes();target.write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError,'Afterimage'):stage.restore(root,report)
            self.assertEqual((root/'usr/share/cockpit/sv08-host/index.html').read_text(),html)
            target.write_bytes(raw);stage.restore(root,report);self.assertEqual(stage.inventory(root,expected),expected)
    def test_validation_asset_requires_exact_pinned_dictionary(self):
        with tempfile.TemporaryDirectory() as temporary:
            fake=Path(temporary)/'dict';fake.write_bytes(b'wrong revision')
            with self.assertRaisesRegex(ValueError,'revision'):stage.payload(fake)
        source=Path(os.environ.get('SV08_PRINTER_SOURCE_ROOT','/home/drew/sv08-mainline'))/'artifacts/test-sv08-01-mcu-usb-v1/klipper.dict'
        if source.exists():self.assertEqual(stage.payload(source)['usr/share/sv08/printer/validation/klipper.dict'],source.read_bytes())
    def test_unknown_preimage_refuses_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);target=root/'usr/share/cockpit/sv08-host/app.js';target.write_bytes(b'unknown')
            expected=stage.inventory(root,[str(p.relative_to(root)) for p in root.rglob('*')])
            with self.assertRaisesRegex(ValueError,'Unknown host'):stage.stage(root,expected,True)
            self.assertFalse((root/'usr/share/cockpit/sv08-printer').exists())
    def test_temporary_conflict_is_prechecked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);expected=self.fixture(root)
            conflict=root/'usr/share/cockpit/sv08-host/index.html.integration-tmp';conflict.write_bytes(b'unexpected')
            with self.assertRaisesRegex(ValueError,'temporary|inventory drift'):stage.stage(root,expected,True)
            self.assertEqual(stage.inventory(root,expected),expected)
            self.assertFalse((root/'usr/share/cockpit/sv08-printer').exists())
    def test_publication_failure_preserves_entry_and_recovers(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);expected=self.fixture(root);report=stage.stage(root,expected)
            host=root/'usr/share/cockpit/sv08-host/index.html';original=host.read_bytes();replace=stage.os.replace
            def fail(source,target):
                if target==host:raise OSError('Injected interruption before host entry')
                replace(source,target)
            with patch.object(stage.os,'replace',side_effect=fail):
                with self.assertRaisesRegex(OSError,'interruption'):stage.stage(root,expected,True)
            self.assertEqual(host.read_bytes(),original)
            self.assertTrue((root/'usr/share/cockpit/sv08-printer/panel.html').is_file())
            stage.restore(root,report,interrupted=True)
            self.assertEqual(stage.inventory(root,expected),expected)
    def test_historical_narrow_transform(self):
        raw=subprocess.check_output(['git','show','85cb5c7:ui/host/app.js'],cwd=ROOT)
        result=stage.integrate_app(raw)
        self.assertIn(b'not(#printer button)',result)
        # Unrelated host operations/receipts remain byte-for-byte.
        a=raw.index(b"$('review').addEventListener('close'");b=raw.index(b"document.querySelectorAll('[data-page]'")
        self.assertIn(raw[a:b],result)
        with self.assertRaises(ValueError):stage.integrate_app(raw+b'function page(name, focus = true) {')
    def test_interrupted_publication_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);expected=self.fixture(root);report=stage.stage(root,expected,True,True)
            # Simulate index publication not yet reached; old entry stays usable.
            name='usr/share/cockpit/sv08-host/index.html';(root/name).write_bytes(bytes.fromhex(report['originals'][name]))
            stage.restore(root,report,interrupted=True);self.assertEqual(stage.inventory(root,expected),expected)
    def test_process_contention_no_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);expected=self.fixture(root)
            report=stage.stage(root,expected,True)
            before=stage.inventory(root,[str(p.relative_to(root)) for p in root.rglob('*')])
            with stage.root_lock(root):
                # Different process, independently opened directory descriptor.
                code="import sys;sys.path.insert(0,'scripts');from stage_printer_ui import stage;stage(sys.argv[1],{},True)"
                child=subprocess.run(['python3','-c',code,str(root)],cwd=ROOT,capture_output=True,text=True)
                self.assertNotEqual(child.returncode,0);self.assertIn('Offline root busy',child.stderr)
                with self.assertRaisesRegex(ValueError,'busy'):stage.restore(root,report)
            self.assertEqual(stage.inventory(root,before),before)
            stage.restore(root,report)
            self.assertEqual(stage.inventory(root,expected),expected)

    def test_lock_held_through_publication_and_restoration(self):
        from unittest.mock import patch
        import sys
        sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'runtime'))
        import stage_admin_ui
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);root=work/'rootfs';root.mkdir();expected=self.fixture(root)
            report=stage.stage(root,expected);replace=stage.os.replace;calls=[]
            def check_lock(source,target):
                for action in (lambda:stage.stage(root,expected,True),lambda:stage.restore(root,report,True),lambda:stage_admin_ui.stage(work,'host',True,True)):
                    with self.assertRaisesRegex(ValueError,'busy'):action()
                calls.append(str(target));replace(source,target)
            with patch.object(stage.os,'replace',side_effect=check_lock):
                stage.stage(root,expected,True)
                stage.restore(root,report)
            self.assertGreater(len(calls),1)
            self.assertEqual(stage.inventory(root,expected),expected)

    def test_drift_visible_during_restore_is_preserved(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);expected=self.fixture(root);report=stage.stage(root,expected,True)
            target=root/'usr/share/cockpit/sv08-printer/app.js';replace=stage.os.replace
            def drift(source,destination):
                replace(source,destination)
                target.write_bytes(b'uncooperative writer')
            with patch.object(stage.os,'replace',side_effect=drift):
                with self.assertRaisesRegex(ValueError,'drift'):stage.restore(root,report)
            self.assertEqual(target.read_bytes(),b'uncooperative writer')
            # Earlier navigation restoration is per-file, never claimed atomic.
            self.assertEqual((root/'usr/share/cockpit/sv08-host/index.html').read_bytes(),bytes.fromhex(report['originals']['usr/share/cockpit/sv08-host/index.html']))

    def test_existing_directory_inventory_drift_refuses_without_mutation(self):
        import os, shutil, stat
        def snapshot(root):
            result={}
            for path in root.rglob('*'):
                st=path.lstat()
                content=os.readlink(path) if stat.S_ISLNK(st.st_mode) else path.read_bytes() if stat.S_ISREG(st.st_mode) else None
                result[str(path.relative_to(root))]=(st.st_mode,st.st_uid,st.st_gid,content)
            return result
        for historical in (False,True):
            for phase in ('stage','restore','interrupted'):
                for kind in ('file','directory','link'):
                    with self.subTest(historical=historical,phase=phase,kind=kind),tempfile.TemporaryDirectory() as tmp:
                        root=Path(tmp);self.fixture(root)
                        if historical:
                            for folder,package in [('ui/host','sv08-host'),('ui/printer','sv08-printer')]:
                                target=root/'usr/share/cockpit'/package
                                if target.exists():shutil.rmtree(target)
                                target.mkdir()
                                for name in subprocess.check_output(['git','ls-tree','--name-only','85cb5c7',folder+'/'],cwd=ROOT,text=True).splitlines():
                                    (target/Path(name).name).write_bytes(subprocess.check_output(['git','show','85cb5c7:'+name],cwd=ROOT))
                        expected=stage.inventory(root,[str(p.relative_to(root)) for p in root.rglob('*')])
                        if phase!='stage':report=stage.stage(root,expected,True)
                        directory=root/'usr/share/cockpit'/('sv08-host' if phase=='stage' else 'sv08-printer')
                        extra=directory/'unexpected'
                        if kind=='file':extra.write_bytes(b'preserve unexpected bytes')
                        elif kind=='directory':extra.mkdir()
                        else:extra.symlink_to('app.js')
                        before=snapshot(root)
                        if phase=='stage':
                            for execute in (False,True):
                                with self.assertRaises(ValueError):stage.stage(root,expected,execute)
                                self.assertEqual(snapshot(root),before)
                        else:
                            with self.assertRaises(ValueError):stage.restore(root,report,phase=='interrupted')
                            self.assertEqual(snapshot(root),before)

    def test_fresh_and_historical_factory_capacity(self):
        import os
        layout=json.loads((ROOT/'configs/images/host-ab.json').read_text())
        partitions={p['name']:p['mib']*1024**2 for p in layout['partitions']}
        receipts={}
        for historical in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.fixture(root)
                if historical:
                    for folder in ('ui/host','ui/printer'):
                        names=subprocess.check_output(['git','ls-tree','--name-only','85cb5c7',folder+'/'],cwd=ROOT,text=True).splitlines()
                        for name in names:
                            target=root/'usr/share/cockpit'/('sv08-host' if folder=='ui/host' else 'sv08-printer')/Path(name).name
                            target.parent.mkdir(parents=True,exist_ok=True)
                            target.write_bytes(subprocess.check_output(['git','show','85cb5c7:'+name],cwd=ROOT))
                expected=stage.inventory(root,[str(p.relative_to(root)) for p in root.rglob('*')])
                report=stage.stage(root,expected);cap=report['capacity']
                self.assertLessEqual(len(json.dumps(report,indent=2).encode()),cap['data_report_bytes_upper_bound'])
                root_reserve=partitions['root-a']-layout['root_content_budget_mib']*1024**2
                boot_reserve=partitions['boot-a']-layout['boot_content_budget_mib']*1024**2
                # Shared /data floor and history admission overhead, unchanged.
                from sv08_data_budget import Budget, BATCH_BYTES, METADATA_BYTES, HISTORY_INODES, rounded
                floor=768*1024**2;overhead=2*rounded(BATCH_BYTES,4096)+rounded(METADATA_BYTES,4096)
                root_peak=cap['root_peak_increment_blocks']*4096
                data_peak=cap['data_peak_increment_blocks']*4096
                self.assertLess(root_peak,root_reserve);self.assertLess(data_peak+floor+overhead,partitions['data'])
                receipts['historical' if historical else 'fresh']=dict(capacity=cap,payload_bytes=report['payload_bytes'],root_delta_bytes=report['root_delta_bytes'],
                    factory_root_partition_bytes=partitions['root-a'],root_content_budget_bytes=layout['root_content_budget_mib']*1024**2,root_reserve_bytes=root_reserve,root_reserve_after_peak_bytes=root_reserve-root_peak,
                    factory_boot_partition_bytes=partitions['boot-a'],boot_content_budget_bytes=layout['boot_content_budget_mib']*1024**2,boot_reserve_bytes=boot_reserve,
                    factory_data_partition_bytes=partitions['data'],data_floor_bytes=floor,data_history_headroom_bytes=overhead,data_remaining_after_floor_history_peak_bytes=partitions['data']-floor-overhead-data_peak,
                    required_free_root_inodes=cap['root_peak_increment_inodes'],required_free_data_inodes=cap['data_peak_increment_inodes']+HISTORY_INODES,
                    measured_factory_free_inodes=None,installed_admission=False)
        if os.environ.get('SV08_CAPACITY_RECEIPT'):
            Path(os.environ['SV08_CAPACITY_RECEIPT']).write_text(json.dumps(receipts,indent=2)+'\n')

if __name__=='__main__':unittest.main()
