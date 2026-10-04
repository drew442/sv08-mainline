import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
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
            with self.assertRaisesRegex(ValueError,'temporary'):stage.stage(root,expected,True)
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
if __name__=='__main__':unittest.main()
