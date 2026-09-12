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
        unit = 'usr/lib/systemd/system/sv08-admin-image-worker@.service'
        self.assertEqual((self.work / 'rootfs' / unit).read_bytes(), (REPO / 'configs/host-os/sv08-admin-image-worker@.service').read_bytes())
        self.assertIn(unit, result['hashes'])
        self.assertIn('usr/lib/sv08/sv08_admin_jobs.py', result['hashes'])
        self.assertFalse((self.work / 'rootfs/etc/systemd/system/sockets.target.wants').exists())
        with self.assertRaises(ValueError): stage(self.work, 'host', True)

    def test_recovery_does_not_stage_cockpit_or_enable_service(self):
        result = stage(self.work, 'recovery', True)
        self.assertFalse(result['activated'])
        self.assertTrue((self.work / 'rootfs/usr/share/xsessions/sv08-recovery.desktop').is_file())
        self.assertFalse((self.work / 'rootfs/usr/share/cockpit').exists())
        self.assertFalse((self.work / 'rootfs/etc/sv08-recovery-image').exists())
        self.assertIn('usr/lib/sv08/sv08_recovery_media.py', result['hashes'])
        self.assertFalse((self.work / 'rootfs/etc/sv08/recovery-media-policy.json').exists())
        self.assertFalse((self.work / 'rootfs/run/sv08-recovery/media-context.json').exists())
        self.assertFalse((self.work / 'rootfs/etc/systemd/system/multi-user.target.wants').exists())

    def test_mismatched_runtime_is_refused(self):
        (self.work / 'rootfs/usr/lib/sv08/sv08_state.py').write_text('old code')
        with self.assertRaisesRegex(ValueError, 'matching'): stage(self.work, 'host', True)

    def test_provider_missing_or_mismatched_is_refused_before_staging(self):
        provider = self.work / 'rootfs/usr/lib/sv08/sv08_recovery_media.py'
        provider.unlink()
        with self.assertRaisesRegex(ValueError, 'sv08_recovery_media'): stage(self.work, 'recovery', True)
        provider.write_text('older provider')
        with self.assertRaisesRegex(ValueError, 'sv08_recovery_media'): stage(self.work, 'recovery', True)
        self.assertFalse((self.work / 'rootfs/usr/share/xsessions').exists())

    def test_worker_missing_is_refused_before_host_ui_staging(self):
        (self.work / 'rootfs/usr/lib/sv08/sv08_admin_jobs.py').unlink()
        with self.assertRaisesRegex(ValueError, 'sv08_admin_jobs'): stage(self.work, 'host', True)
        self.assertFalse((self.work / 'rootfs/usr/share/cockpit').exists())
