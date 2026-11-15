from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_installed_cockpit import check, probe, check_runtime, REQUIRED_RUNTIME, CALIBRATION_UNIT
from test_data_budget import fixture_root


class InstalledReadinessTests(unittest.TestCase):
    def test_rpc_errors_fail_even_when_process_exits_zero_and_do_not_leak(self):
        result = subprocess.CompletedProcess([], 0, '{"ok":false,"error":"private sentinel"}', '')
        with patch('check_installed_cockpit.subprocess.run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'refused') as error:
                probe(Path('/'), 'sv08_printer_helper.py', 'action')
        self.assertNotIn('private sentinel', str(error.exception))

    def test_manifest_cannot_read_outside_ui_assets(self):
        with self.assertRaises(ValueError):
            check(Path('/'), {'files': {'etc/shadow': '0' * 64}}, lambda *_: {})

    def test_runtime_manifest_is_mandatory_and_paths_are_finite(self):
        for manifest in ({},{'runtime_files':{}},{'runtime_files':{name:'0'*64 for name in REQUIRED_RUNTIME}|{'etc/shadow':'0'*64}}):
            with self.assertRaises(ValueError):check_runtime(Path('/'),manifest)
        with tempfile.TemporaryDirectory() as temporary:
            report=check_runtime(Path(temporary),{'runtime_files':{name:'0'*64 for name in REQUIRED_RUNTIME}})
            self.assertFalse(any(report.values()))

    @unittest.skipUnless(os.geteuid() == 0, 'real ownership fixture; run with sudo')
    def test_populated_status_assets_and_managed_ownership_all_required(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as temp:
            root = Path(temp)
            asset = root / 'usr/share/cockpit/sv08-host/app.js'
            asset.parent.mkdir(parents=True); asset.write_text('fixture asset')
            manifest = {'files': {str(asset.relative_to(root)): hashlib.sha256(asset.read_bytes()).hexdigest()}}
            manifest['runtime_files']={}
            for name in REQUIRED_RUNTIME:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture runtime')
                manifest['runtime_files'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
            wants=root/'etc/systemd/system/sv08-klipper.service.wants';wants.mkdir()
            (wants/'sv08-calibration-reconcile.service').symlink_to('../sv08-calibration-reconcile.service')
            config = root / 'data/sv08/generations/test/config'; config.mkdir(parents=True)
            managed = config / 'printer-managed'; managed.mkdir(mode=0o750); os.chown(managed, 0, 1000)
            boot = root / 'run/sv08/boot.json'; boot.parent.mkdir(parents=True); boot.write_text(json.dumps({'generation': '/data/sv08/generations/test'}))
            def good(*_):
                return {'state': {'format_version': 1, 'revision': 9, 'draft': {'devices': [1]}, 'current': {}, 'previous': {}}, 'definitions': [1], 'sources': {'test': {}}}
            baseline = check(root, manifest, good)
            self.assertTrue(baseline['passed'])
            self.assertTrue(check(root, manifest, good, baseline)['passed'])
            different = {**baseline, 'hardware': {**baseline['hardware'], 'sources': 0}}
            self.assertFalse(check(root, manifest, good, different)['passed'])
            os.chown(managed, 1000, 1000)
            report = check(root, manifest, good)
            self.assertFalse(report['passed']); self.assertFalse(report['storage']['printer-managed'])
            os.chown(managed, 0, 1000)
            def failed(*_): raise ValueError('private sentinel')
            report = check(root, manifest, failed)
            self.assertFalse(report['passed']); self.assertFalse(report['helpers']['hardware'])
            self.assertNotIn('private sentinel', json.dumps(report))
            asset.write_text('unexpected asset')
            self.assertFalse(check(root, manifest, good)['passed'])


if __name__ == '__main__': unittest.main()
