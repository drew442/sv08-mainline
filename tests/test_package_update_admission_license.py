import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import package_update_admission as package


class AdmissionLicenseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = json.loads((REPO / 'configs/apps/update-admission.json').read_text())
        for name in ('configs/apps/update-admission.json', 'configs/apps/klipper.json',
                     self.config['source'], 'LICENSE', 'LICENSING.md'):
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((REPO / name).read_bytes())
        self.patch = patch.object(package, 'REPO', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_missing_tampered_or_linked_license_refuses_without_output(self):
        path = self.root / 'LICENSE'
        original = path.read_bytes()
        for mode in ('missing', 'tampered', 'symlink'):
            path.unlink()
            if mode == 'tampered':
                path.write_bytes(b'changed terms')
            elif mode == 'symlink':
                path.symlink_to(self.root / 'LICENSING.md')
            work = self.root / ('refused-' + mode)
            with self.assertRaises(ValueError):
                package.build(work, execute=True)
            self.assertFalse(work.exists())
            if path.exists() or path.is_symlink():
                path.unlink()
            path.write_bytes(original)

    def test_grant_tamper_and_missing_pin_refuse_without_output(self):
        grant = self.root / 'LICENSING.md'
        grant.write_bytes(b'different grant')
        work = self.root / 'refused-grant'
        with self.assertRaises(ValueError):
            package.build(work, execute=True)
        self.assertFalse(work.exists())
        grant.write_bytes((REPO / 'LICENSING.md').read_bytes())
        self.config['license_files'] = self.config['license_files'][:1]
        (self.root / 'configs/apps/update-admission.json').write_text(json.dumps(self.config))
        with self.assertRaises(ValueError):
            package.build(work, execute=True)
        self.assertFalse(work.exists())

    def test_real_package_pair_carries_grant_without_runtime_changes(self):
        work_a, work_b = self.root / 'a', self.root / 'b'
        a = package.build(work_a, execute=True)
        b = package.build(work_b, execute=True)
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertEqual(a['config']['version'], '0.1.0-3')
        payload = work_a / 'package'
        doc = payload / 'usr/share/doc/sv08-update-admission'
        for name in ('LICENSE', 'LICENSING.md'):
            self.assertEqual((doc / name).read_bytes(), (REPO / name).read_bytes())
        self.assertIn('License: AGPL-3.0-or-later', (doc / 'copyright').read_text())
        source = payload / 'usr/lib/sv08/klipper-extras/sv08_update.py'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), self.config['source_sha256'])
        link = payload / 'opt/sv08-mainline/klipper/klippy/extras/sv08_update.py'
        self.assertEqual(str(link.readlink()), '/usr/lib/sv08/klipper-extras/sv08_update.py')
        control = (payload / 'DEBIAN/control').read_text()
        self.assertIn('Depends: sv08-klipper (= 0.0+gitf0892d82-2)', control)
        self.assertFalse(a['enables_extension'])
        self.assertFalse(a['changes_mcu'])


if __name__ == '__main__':
    unittest.main()
