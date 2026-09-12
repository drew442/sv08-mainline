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

    def test_shell_config_conflict_is_rejected_without_overwrite(self):
        config = self.work / 'rootfs/etc/cockpit/cockpit.conf'
        config.parent.mkdir(parents=True); config.write_text('[WebService]\nOrigins=https://owner.example\n')
        for execute in (False, True):
            with self.assertRaisesRegex(ValueError, 'conflicts'): stage(self.work, 'host', execute)
        self.assertIn('Origins=', config.read_text())
        self.assertFalse((self.work / 'rootfs/usr/share/cockpit/sv08-host').exists())

    def test_symlink_parent_and_stock_package_are_rejected(self):
        parent = self.work / 'rootfs/usr/share'; parent.mkdir(parents=True)
        outside = self.work / 'outside'; outside.mkdir()
        (parent / 'cockpit').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'): stage(self.work, 'host', True)
        self.assertEqual(list(outside.iterdir()), [])
        (parent / 'cockpit').unlink(); (parent / 'cockpit/shell').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'Unexpected Cockpit'): stage(self.work, 'host', True)

    def test_manifest_shell_modes_and_no_sudo_grant(self):
        import json
        result = stage(self.work, 'host', True)
        root = self.work / 'rootfs'
        manifest = json.loads((root / 'usr/share/cockpit/sv08-host/manifest.json').read_text())
        self.assertEqual(manifest['bridges'], [{'privileged': True,
            'environ': ['SUDO_ASKPASS=${libexecdir}/cockpit-askpass'],
            'spawn': ['sudo', '-k', '-A', 'cockpit-bridge', '--privileged']}])
        self.assertEqual((root / 'etc/cockpit/cockpit.conf').read_text(), '[WebService]\nShell=/sv08-host/index.html\n')
        self.assertIn('etc/cockpit/cockpit.conf', result['hashes'])
        self.assertFalse((root / 'etc/sudoers.d').exists())
        self.assertEqual((root / 'usr/share/cockpit/sv08-host').stat().st_mode & 0o777, 0o755)
        for path in (root / 'usr/share/cockpit/sv08-host').iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)

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

    def test_upload_dependency_mismatch_refuses_before_staging(self):
        for name in ('sv08_admin_upload.py','sv08_staging.py','sv08_bundle.py','sv08_rauc.py','sv08_boot.py'):
            path=self.work/'rootfs/usr/lib/sv08'/name;original=path.read_bytes()
            path.write_text('older core')
            with self.assertRaisesRegex(ValueError,name):stage(self.work,'host',True)
            self.assertFalse((self.work/'rootfs/usr/share/cockpit').exists())
            path.write_bytes(original)
