from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from stage_admin_ui import stage, REPO


class StageUITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        target = self.work / 'rootfs/usr/lib/sv08'; target.mkdir(parents=True)
        for path in (REPO / 'runtime').glob('*.py'): shutil.copyfile(path, target / path.name)

    def test_dry_run_and_explicit_host_staging(self):
        result = stage(self.work, 'host')
        self.assertFalse(result['execute'])
        target = self.work / 'rootfs/usr/share/cockpit/sv08-host'
        self.assertFalse(target.exists())
        result = stage(self.work, 'host', True)
        self.assertTrue((target / 'manifest.json').is_file())
        self.assertFalse(result['activated'])
        self.assertFalse((self.work / 'rootfs/etc/systemd/system/sockets.target.wants').exists())
        with self.assertRaises(ValueError): stage(self.work, 'host', True)

    def test_recovery_does_not_stage_cockpit_or_enable_service(self):
        result = stage(self.work, 'recovery', True)
        self.assertFalse(result['activated'])
        self.assertTrue((self.work / 'rootfs/usr/share/xsessions/sv08-recovery.desktop').is_file())
        self.assertFalse((self.work / 'rootfs/usr/share/cockpit').exists())
        self.assertFalse((self.work / 'rootfs/etc/sv08-recovery-image').exists())
        self.assertFalse((self.work / 'rootfs/etc/systemd/system/multi-user.target.wants').exists())

    def test_mismatched_runtime_is_refused(self):
        (self.work / 'rootfs/usr/lib/sv08/sv08_state.py').write_text('old code')
        with self.assertRaisesRegex(ValueError, 'matching'): stage(self.work, 'host', True)
