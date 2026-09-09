import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import package_klipper as m


class PackageInputsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.c = json.loads((REPO / 'configs/apps/klipper.json').read_text())
        self.wheels = self.base / 'wheels'
        self.wheels.mkdir()
        wheel = self.wheels / 'runtime.whl'
        wheel.write_bytes(b'fixture')
        lock = self.base / self.c['runtime_lock']
        lock.parent.mkdir(parents=True)
        lock.write_text('runtime==1 --hash=sha256:' + m.sha(wheel) + '\n')
        self.c['runtime_lock_sha256'] = m.sha(lock)
        self.helper = self.base / 'helper.so'
        self.helper.write_bytes(b'helper-fixture')
        self.c['helper_sha256'] = m.sha(self.helper)
        (self.base / 'upstream-lock.json').write_text(json.dumps({'submodules': [
            {'path': self.c['source_path'], 'commit': self.c['source_commit']}]}))

    def verify(self):
        with patch.object(m, 'REPO', self.base), patch.object(m.subprocess, 'check_output', return_value=self.c['source_commit']+'\n'):
            return m.verified_inputs(self.c, self.wheels, self.helper)

    def test_locked_inputs_accepted(self):
        self.assertEqual(len(self.verify()[1]), 1)

    def test_modified_or_extra_wheel_rejected(self):
        (self.wheels / 'runtime.whl').write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            self.verify()
        (self.wheels / 'runtime.whl').write_bytes(b'fixture')
        (self.wheels / 'unexpected.whl').write_bytes(b'extra')
        with self.assertRaises(ValueError):
            self.verify()

    def test_helper_mismatch_rejected(self):
        self.helper.write_bytes(b'wrong architecture or content')
        with self.assertRaises(ValueError):
            self.verify()

    def test_host_mcu_revision_mismatch_rejected(self):
        self.c['source_commit'] = '0' * 40
        with self.assertRaises(ValueError):
            self.verify()

    def test_existing_installation_not_overwritten(self):
        work = self.base / 'work'
        (work / 'rootfs/usr/bin').mkdir(parents=True)
        (work / 'rootfs/usr/bin/python3.13').touch()
        (work / 'refresh-complete').touch()
        prefix = work / 'rootfs' / self.c['source_prefix'].lstrip('/')
        prefix.mkdir(parents=True)
        keep = prefix / 'keep'
        keep.write_text('existing')
        with patch.object(m, 'run') as run:
            with self.assertRaises(ValueError):
                m.assemble(self.c, work, None, [], None, self.helper)
            run.assert_not_called()
        self.assertEqual(keep.read_text(), 'existing')

    def test_unreviewed_prefix_rejected(self):
        self.c['source_prefix'] = '/../../etc'
        with self.assertRaises(ValueError):
            self.verify()


if __name__ == '__main__':
    unittest.main()
