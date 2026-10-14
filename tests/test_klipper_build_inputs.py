import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import build_klipper_inputs as m


class BuildInputsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.c = json.loads((REPO / 'configs/host/klipper-build-inputs.json').read_text())

    def test_source_tamper_and_symlink_rejected(self):
        source = self.base / 'source.tar.gz'
        source.write_bytes(b'fixture')
        self.c['markupsafe']['source_sha256'] = m.sha(source)
        m.validate_source(self.c, 'markupsafe', source)
        source.write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            m.validate_source(self.c, 'markupsafe', source)
        link = self.base / 'link'
        link.symlink_to(source)
        with self.assertRaises(ValueError):
            m.validate_source(self.c, 'markupsafe', link)

    def test_helper_pin_and_clean_source(self):
        with patch.object(m, 'output', side_effect=[self.c['helper']['source_commit'], '']):
            m.validate_source(self.c, 'helper', self.base)
        for values in [['0' * 40], [self.c['helper']['source_commit'], ' M klippy/chelper/pyhelper.c']]:
            with patch.object(m, 'output', side_effect=values), self.assertRaises(ValueError):
                m.validate_source(self.c, 'helper', self.base)

    def test_fresh_path_and_ancestor_symlink(self):
        existing = self.base / 'existing'
        existing.mkdir()
        with self.assertRaises(ValueError):
            m.fresh(existing)
        link = self.base / 'link'
        link.symlink_to(existing)
        with self.assertRaises(ValueError):
            m.fresh(link / 'new')

    def test_commands_offline_and_canonical_paths(self):
        root = self.base
        work = root / 'tmp/run-a'
        command = m.wheel_plan(self.c, root, work, '/tmp/backend')
        for flag in ['--no-index', '--no-deps', '--no-build-isolation', '--no-cache-dir']:
            self.assertIn(flag, command)
        self.assertIn('-i', command)
        cflags = next(x for x in command if x.startswith('CFLAGS='))
        self.assertIn('-ffile-prefix-map=/tmp/run-a=/usr/src/sv08-wheel-build', cflags)
        helper = m.helper_command(self.c, self.base / 'run-a')
        self.assertTrue(any(x.endswith('=/usr/src/sv08-klipper-build') for x in helper))
        with self.assertRaises(ValueError):
            m.wheel_plan(self.c, root, root / 'etc/run', '/tmp/backend')
        with self.assertRaises(ValueError):
            m.wheel_plan(self.c, root, work, '/tmp/../etc')

    def test_backend_content_hash_and_installed_tamper(self):
        wheels = self.base / 'wheels'
        wheels.mkdir()
        pin = self.c['markupsafe']['backends']['setuptools']
        wheel = wheels / pin['filename']
        with zipfile.ZipFile(wheel, 'w') as z:
            z.writestr('setuptools/__init__.py', b'backend')
        pin['sha256'] = m.sha(wheel)
        target = self.base / 'tmp/backend/lib/python3.13/site-packages/setuptools/__init__.py'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'backend')
        m.verify_backends(self.c, self.base, '/tmp/backend', wheels)
        target.write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            m.verify_backends(self.c, self.base, '/tmp/backend', wheels)
        target.write_bytes(b'backend')
        wheel.write_bytes(b'changed-wheel')
        with self.assertRaises(ValueError):
            m.verify_backends(self.c, self.base, '/tmp/backend', wheels)

    def test_selected_build_mismatch_retains_report_and_artifact(self):
        work = self.base / 'build'
        work.mkdir()
        artifact = work / 'c_helper-aarch64.so'
        artifact.write_bytes(b'diagnostic output')
        report = dict(kind='helper', sha256=m.sha(artifact))
        with self.assertRaises(ValueError):
            m.save_report(self.c, 'helper', work, report)
        retained = json.loads((work / 'report.json').read_text())
        self.assertEqual(retained['sha256'], m.sha(artifact))
        self.assertFalse(retained['matches_selected_build'])
        self.assertEqual(retained['selected_sha256'], self.c['helper']['selected_sha256'])
        self.c['helper']['selected_sha256'] = m.sha(artifact)
        m.save_report(self.c, 'helper', work, report)
        self.assertTrue(json.loads((work / 'report.json').read_text())['matches_selected_build'])

    def test_only_selected_package_identity_accepted(self):
        import test_package_klipper as package_tests
        case = package_tests.PackageInputsTests('test_locked_inputs_accepted')
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.assertEqual(case.c['version'], '0.0+gitf0892d82-2')
        self.assertEqual(len(case.verify()[1]), 1)
        for version in ('0.0+gitf0892d82-1', '0.0+gitf0892d82-3', 'unreviewed'):
            case.c['version'] = version
            with self.assertRaises(ValueError):
                case.verify()

    def test_selected_rebuilt_inputs_and_lock_digest(self):
        selected = json.loads((REPO / 'configs/apps/klipper.json').read_text())
        recipe = json.loads((REPO / 'configs/host/klipper-build-inputs.json').read_text())
        self.assertEqual(selected['helper_sha256'], recipe['helper']['selected_sha256'])
        self.assertNotEqual(selected['helper_sha256'], recipe['helper']['historical_sha256'])
        lock = REPO / selected['runtime_lock']
        self.assertEqual(m.sha(lock), selected['runtime_lock_sha256'])
        self.assertIn('MarkupSafe==1.1.1 --hash=sha256:' + recipe['markupsafe']['selected_sha256'], lock.read_text())
        self.assertNotIn(recipe['markupsafe']['historical_sha256'], lock.read_text())

    def test_admission_matches_selected_klipper_without_source_change(self):
        admission = json.loads((REPO / 'configs/apps/update-admission.json').read_text())
        klipper = json.loads((REPO / 'configs/apps/klipper.json').read_text())
        self.assertEqual(admission['klipper_commit'], klipper['source_commit'])
        self.assertEqual(admission['klipper_package_version'], klipper['version'])
        self.assertEqual(admission['version'], '0.1.0-3')
        expected = 'ea67e7a0afce39754c6c691bbfd0ead399a2dfe57fbe3fd7e837d639bb190522'
        self.assertEqual(admission['source_sha256'], expected)
        self.assertEqual(m.sha(REPO / admission['source']), expected)


if __name__ == '__main__':
    unittest.main()
