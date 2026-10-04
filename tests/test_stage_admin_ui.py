from test_data_budget import fixture_root
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from stage_admin_ui import stage, REPO


class StageUITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=fixture_root()); self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        target = self.work / 'rootfs/usr/lib/sv08'; target.mkdir(parents=True)
        for path in (REPO / 'runtime').glob('*.py'): shutil.copyfile(path, target / path.name)
        (target / 'sv08_rauc_bootloader.py').chmod(0o755)

    def test_shared_root_lock_refuses_stage_and_refresh(self):
        from stage_printer_ui import root_lock
        root=self.work/'rootfs'
        before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        with root_lock(root):
            for execute,refresh in ((False,False),(True,False),(True,True)):
                with self.assertRaisesRegex(ValueError,'busy'):stage(self.work,'host',execute,refresh)
        self.assertEqual({str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()},before)
        stage(self.work,'host',True)
        with root_lock(root):
            with self.assertRaisesRegex(ValueError,'busy'):stage(self.work,'host',True,True)

    def test_host_only_navigation_has_no_dead_printer_references(self):
        stage(self.work,'host',True)
        entry=self.work/'rootfs/usr/share/cockpit/sv08-host/index.html'
        for refresh in (False,True):
            if refresh:stage(self.work,'host',True,refresh=True)
            html=entry.read_text()
            self.assertNotIn('../sv08-printer/',html)
            self.assertIn('src="navigation.js"',html)
            self.assertTrue((entry.parent/'navigation.js').is_file())
    def test_matching_printer_package_composes_before_host_refresh(self):
        package=self.work/'rootfs/usr/share/cockpit/sv08-printer';package.parent.mkdir(parents=True)
        shutil.copytree(REPO/'ui/printer',package)
        stage(self.work,'host',True)
        entry=package.parent/'sv08-host/index.html';before=entry.read_bytes()
        self.assertIn(b'id="printer"',before)
        self.assertEqual(before.count(b'src="session.js"'),1)
        (package/'app.js').write_bytes(b'unknown')
        with self.assertRaisesRegex(ValueError,'matching printer'):stage(self.work,'host',True,refresh=True)
        self.assertEqual(entry.read_bytes(),before)
    def test_dry_run_and_explicit_host_staging(self):
        result = stage(self.work, 'host')
        self.assertFalse(result['execute'])
        target = self.work / 'rootfs/usr/share/cockpit/sv08-host'
        self.assertFalse(target.exists())
        result = stage(self.work, 'host', True)
        entry=(self.work/'rootfs/usr/share/cockpit/sv08-host/index.html').read_text()
        self.assertNotIn('../sv08-printer/',entry)
        self.assertIn('navigation.js',entry)
        self.assertTrue((target / 'manifest.json').is_file())
        self.assertEqual((self.work / 'rootfs/etc/cockpit/ws-certs.d').readlink(),
                         Path('/data/sv08/system/cockpit/ws-certs.d'))
        self.assertFalse((self.work / 'rootfs/etc/systemd/system/cockpit.service.d').exists())
        self.assertFalse(result['activated'])
        unit = 'usr/lib/systemd/system/sv08-admin-image-worker@.service'
        self.assertEqual((self.work / 'rootfs' / unit).read_bytes(), (REPO / 'configs/host-os/sv08-admin-image-worker@.service').read_bytes())
        for relative, source in [('usr/lib/sv08/rauc-service-policy.json', 'rauc-service-policy.json'),
                                 ('etc/dbus-1/system.d/zz-sv08-rauc.conf', 'sv08-rauc-policy.conf'),
                                 ('etc/systemd/system/rauc.service.d/sv08.conf', 'sv08-rauc-service.conf')]:
            self.assertEqual((self.work / 'rootfs' / relative).read_bytes(),
                             (REPO / 'configs/host-os' / source).read_bytes())
        self.assertIn(unit, result['hashes'])
        for name in ('branding.css', 'badge.svg'):
            relative = 'usr/share/cockpit/branding/debian/' + name
            self.assertEqual((self.work / 'rootfs' / relative).read_bytes(),
                             (REPO / 'configs/host-os/cockpit-branding' / name).read_bytes())
            self.assertIn(relative, result['hashes'])
        import json, os
        Path(fixture_root()).joinpath('history-staged-inventory.json').write_text(json.dumps(result, indent=2))
        for name in ('sv08_admin_history.py', 'sv08_data_budget.py'):
            self.assertIn('usr/lib/sv08/'+name, result['hashes'])
        for unit_name in ('sv08-feed.service', 'sv08-feed.timer'):
            name = 'usr/lib/systemd/system/' + unit_name
            self.assertEqual((self.work / 'rootfs' / name).read_bytes(),
                             (REPO / 'configs/host-os' / unit_name).read_bytes())
            self.assertIn(name, result['hashes'])
        self.assertEqual((self.work / 'rootfs/etc/systemd/system/timers.target.wants/sv08-feed.timer').readlink(),
                         Path('/usr/lib/systemd/system/sv08-feed.timer'))
        self.assertIn('ConditionPathExists=/usr/lib/sv08/feed.json',
                      (self.work / 'rootfs/usr/lib/systemd/system/sv08-feed.service').read_text())
        self.assertIn('usr/lib/sv08/rauc-service-policy.json', result['hashes'])
        self.assertIn('usr/lib/sv08/sv08_admin_jobs.py', result['hashes'])
        self.assertFalse((self.work / 'rootfs/etc/systemd/system/sockets.target.wants').exists())
        with self.assertRaises(ValueError): stage(self.work, 'host', True)

    def test_current_image_branding_replaces_only_regular_supported_assets(self):
        branding = self.work / 'rootfs/usr/share/cockpit/branding/debian'
        branding.mkdir(parents=True)
        (branding / 'branding.css').write_text('stock package branding fixture')
        (branding / 'preserve.txt').write_text('unrelated asset')
        stage(self.work, 'host', True)
        self.assertEqual((branding / 'branding.css').read_bytes(),
                         (REPO / 'configs/host-os/cockpit-branding/branding.css').read_bytes())
        self.assertEqual((branding / 'preserve.txt').read_text(), 'unrelated asset')

    def test_host_refresh_replaces_only_reviewed_ui_outputs(self):
        stage(self.work, 'host', True)
        root = self.work / 'rootfs'
        target = root / 'usr/share/cockpit/sv08-host'
        (target / 'stale.txt').write_text('obsolete\n')
        result = stage(self.work, 'host', True, refresh=True)
        self.assertTrue(result['execute'])
        self.assertTrue((target / 'manifest.json').is_file())
        self.assertFalse((target / 'stale.txt').exists())
        self.assertEqual((root / 'etc/cockpit/cockpit.conf').read_text(),
                         '[WebService]\nShell=/sv08-host/index.html\n')
        self.assertEqual((root / 'etc/cockpit/ws-certs.d').readlink(),
                         Path('/data/sv08/system/cockpit/ws-certs.d'))

    def test_certificate_directory_must_be_empty_and_unlinked_before_first_stage(self):
        certs = self.work / 'rootfs/etc/cockpit/ws-certs.d'
        certs.mkdir(parents=True)
        (certs / 'owner.cert').write_text('preserve')
        with self.assertRaisesRegex(ValueError, 'must be empty'):
            stage(self.work, 'host', True)
        self.assertEqual((certs / 'owner.cert').read_text(), 'preserve')
        (certs / 'owner.cert').unlink()
        stage(self.work, 'host', True)
        self.assertTrue(certs.is_symlink())

    def test_unexpected_certificate_directory_link_is_rejected(self):
        certs = self.work / 'rootfs/etc/cockpit/ws-certs.d'
        certs.parent.mkdir(parents=True)
        certs.symlink_to('/tmp/unrelated', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Unexpected Cockpit certificate'):
            stage(self.work, 'host', True)

    def test_recovery_refresh_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'only supported'):
            stage(self.work, 'recovery', True, refresh=True)

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
        self.assertIn('etc/cockpit/ws-certs.d', result['hashes'])
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


    def test_history_runtime_modules_are_strict_dependencies(self):
        for name in ('sv08_admin_history.py', 'sv08_data_budget.py'):
            path = self.work / 'rootfs/usr/lib/sv08' / name
            raw = path.read_bytes(); path.unlink()
            with self.assertRaisesRegex(ValueError, name): stage(self.work, 'host', True)
            self.assertFalse((self.work / 'rootfs/usr/share/cockpit/sv08-host').exists())
            path.write_bytes(raw)
            path.write_bytes(raw+b'\n# mismatched fixture\n')
            with self.assertRaisesRegex(ValueError, name): stage(self.work, 'host', True)
            path.write_bytes(raw)
