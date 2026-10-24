from test_data_budget import fixture_root
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from integrate_host_os import stage, validate


class IntegrationManifestTests(unittest.TestCase):
    def admission_fixture(self):
        temporary = tempfile.TemporaryDirectory(dir=fixture_root())
        self.addCleanup(temporary.cleanup)
        work = Path(temporary.name)
        root = work / 'rootfs'
        (work / 'refresh-complete').touch()
        for directory in ('etc/systemd/system', 'etc/ssh', 'etc/apt/apt.conf.d',
                          'etc/initramfs-tools/conf.d', 'usr/bin', 'usr/sbin',
                          'etc/sudoers.d', 'home/sovol/.ssh', 'usr/lib/sv08/klipper-extras'):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / 'etc/passwd').write_text('sv08:x:1000:1000::/home/sv08:/bin/bash\n')
        (root / 'etc/group').write_text('sv08:x:1000:\n')
        (root / 'home/sovol/.ssh/authorized_keys').write_text('ssh-ed25519 fixture owner\n')
        extension = root / 'usr/lib/sv08/klipper-extras/sv08_update.py'
        source = Path(__file__).resolve().parents[1] / 'extensions/klipper/sv08_update.py'
        extension.write_bytes(source.read_bytes())
        extension.chmod(0o644)
        return work, root, extension

    def manifest(self):
        return dict(release='fixture-1', state_schema=1, deployable=False,
                    devices={name: '/dev/disk/by-partuuid/'+str(uuid.uuid4()) for name in
                             ('boot-a', 'root-a', 'boot-b', 'root-b', 'data', 'recovery')})

    def test_requires_distinct_real_uuid_paths_and_non_deployable_status(self):
        manifest = self.manifest()
        validate(manifest)
        for field, value in [('deployable', True), ('state_schema', 2)]:
            changed = dict(manifest, **{field: value})
            with self.assertRaises(ValueError):
                validate(changed)
        changed = json.loads(json.dumps(manifest))
        changed['devices']['data'] = changed['devices']['root-a']
        with self.assertRaises(ValueError):
            validate(changed)
        changed['devices']['data'] = '/dev/disk/by-partuuid/'+'-'*36
        with self.assertRaises(ValueError):
            validate(changed)

    def test_package_admission_survives_fresh_stage_and_controlled_refresh(self):
        work, root, extension = self.admission_fixture()
        original = extension.read_bytes()
        identity = extension.stat()
        directory_identity = extension.parent.stat()
        with patch('integrate_host_os.rebuild_initramfs') as rebuild:
            stage(work, self.manifest())
            self.assertEqual(extension.read_bytes(), original)
            self.assertTrue((work / 'integration-staged.json').is_file())
            target = extension.parent.parent
            (target / 'stale.py').write_text('obsolete runtime\n')
            # Production staging runs as root; permit this rootless fixture's
            # second write to the deliberately read-only sudoers file.
            (root / 'etc/sudoers.d/sv08-owner').chmod(0o640)
            stage(work, self.manifest(), refresh=True)
        self.assertEqual(rebuild.call_count, 2)
        self.assertFalse((target / 'stale.py').exists())
        self.assertEqual(extension.read_bytes(), original)
        self.assertEqual(extension.stat(), identity)
        self.assertEqual(extension.parent.stat(), directory_identity)
        self.assertEqual((target / 'sv08_state.py').read_bytes(),
                         (Path(__file__).resolve().parents[1] / 'runtime/sv08_state.py').read_bytes())

    def test_unrecognized_admission_content_fails_before_any_mutation(self):
        for refresh in (False, True):
            for kind in ('changed', 'extra', 'file-link', 'directory-link', 'empty'):
                with self.subTest(refresh=refresh, kind=kind):
                    work, root, extension = self.admission_fixture()
                    if kind == 'changed':
                        extension.write_text('changed extension\n')
                    elif kind == 'extra':
                        (extension.parent / 'unknown.py').write_text('unknown\n')
                    elif kind == 'file-link':
                        source = work / 'extension.py'
                        extension.rename(source)
                        extension.symlink_to(source)
                    elif kind == 'directory-link':
                        source = work / 'extras'
                        extension.parent.rename(source)
                        extension.parent.symlink_to(source, target_is_directory=True)
                    else:
                        extension.unlink()
                    def snapshot():
                        return {str(p.relative_to(work)): (p.lstat(),
                                str(p.readlink()) if p.is_symlink() else
                                p.read_bytes() if p.is_file() else None)
                                for p in work.rglob('*')}
                    before = snapshot()
                    with patch('integrate_host_os.rebuild_initramfs') as rebuild:
                        with self.assertRaisesRegex(ValueError, 'admission extension'):
                            stage(work, self.manifest(), refresh=refresh)
                    rebuild.assert_not_called()
                    self.assertEqual(snapshot(), before)

    def test_fresh_stage_refuses_unknown_runtime_beside_admission(self):
        work, root, extension = self.admission_fixture()
        unknown = extension.parent.parent / 'unknown.py'
        unknown.write_text('keep me\n')
        original = extension.read_bytes()
        with self.assertRaisesRegex(ValueError, 'unknown files'):
            stage(work, self.manifest())
        self.assertEqual(unknown.read_text(), 'keep me\n')
        self.assertEqual(extension.read_bytes(), original)
        self.assertFalse((work / 'integration-staged.json').exists())

    def test_refresh_precondition_failure_preserves_admission(self):
        work, root, extension = self.admission_fixture()
        original = extension.read_bytes()
        identity = extension.stat()
        (root / 'usr/bin/sv08-state').write_text('unrecognized\n')
        with self.assertRaisesRegex(ValueError, 'runtime command conflicts'):
            stage(work, self.manifest(), refresh=True)
        self.assertEqual(extension.read_bytes(), original)
        self.assertEqual(extension.stat(), identity)

    def test_refresh_replaces_only_a_reviewed_existing_runtime(self):
        temporary = tempfile.TemporaryDirectory(dir=fixture_root()); self.addCleanup(temporary.cleanup)
        work = Path(temporary.name); root = work / 'rootfs'
        (work / 'refresh-complete').touch()
        for directory in ('etc/systemd/system', 'etc/ssh', 'etc/apt/apt.conf.d',
                          'etc/initramfs-tools/conf.d', 'usr/bin', 'usr/sbin', 'etc/default',
                          'etc/sudoers.d', 'home/sovol/.ssh'):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / 'etc/passwd').write_text('sv08:x:1000:1000::/home/sv08:/bin/bash\n')
        (root / 'etc/group').write_text('sv08:x:1000:\n')
        owner_key = work / 'owner-authorized_keys'
        owner_key.write_text('ssh-ed25519 fixture owner\n')
        target = root / 'usr/lib/sv08'; target.mkdir(parents=True)
        (target / 'stale.py').write_text('obsolete runtime\n')
        command = root / 'usr/bin/sv08-state'
        command.symlink_to('../lib/sv08/sv08_state.py')

        with patch('integrate_host_os.rebuild_initramfs') as rebuild:
            stage(work, self.manifest(), refresh=True, owner_key=owner_key)
        rebuild.assert_called_once_with(root)

        from sv08_printer_stack import MOONRAKER, NGINX
        self.assertEqual((target / 'seed/config/moonraker.conf').read_text(), MOONRAKER)
        self.assertEqual((target / 'seed/config/nginx-mainsail.conf').read_text(), NGINX)
        self.assertTrue((root / 'etc/sv08/nginx-mainsail-service.conf').is_file())
        self.assertEqual((target / 'sv08_mainsail_access.py').read_bytes(),
                         (Path(__file__).resolve().parents[1] / 'runtime/sv08_mainsail_access.py').read_bytes())
        self.assertEqual((target/'sv08_network.py').read_bytes(),
                         (Path(__file__).resolve().parents[1]/'runtime/sv08_network.py').read_bytes())
        self.assertEqual((target/'sv08_software.py').read_bytes(),
                         (Path(__file__).resolve().parents[1]/'runtime/sv08_software.py').read_bytes())
        self.assertEqual((target/'software-catalog.json').read_bytes(),
                         (Path(__file__).resolve().parents[1]/'configs/host-os/software-catalog.json').read_bytes())
        units=root/'etc/systemd/system'
        self.assertIn('--worker %i',(units/'sv08-software-worker@.service').read_text())
        self.assertIn('--recover-boot',(units/'sv08-prepare.service.d/network-rollback.conf').read_text())
        self.assertFalse((units/'NetworkManager.service.d/sv08-network-rollback.conf').exists())
        self.assertEqual((units/'timers.target.wants/sv08-network-rollback.timer').readlink(),
                         Path('/etc/systemd/system/sv08-network-rollback.timer'))
        self.assertIn('After=sv08-prepare.service NetworkManager.service',(units/'sv08-network-rollback.service').read_text())
        self.assertEqual((root / 'etc/systemd/system/nginx.service').readlink(), Path('/dev/null'))
        wants = root / 'etc/systemd/system/multi-user.target.wants'
        self.assertEqual({p.name for p in wants.iterdir()},
                         {'sv08-boot-health.service', 'sv08-printer-api.service', 'sv08-mainsail.service'})
        observer=(units/'sv08-calibration-reconcile.service').read_text()
        self.assertIn('sv08_calibration_reconcile.py',observer)
        self.assertIn('ConditionPathExists=!/run/sv08/trial',observer)
        self.assertNotIn('Wants=sv08-klipper.service',observer)
        self.assertIn('WantedBy=sv08-klipper.service',observer)
        self.assertIn('PartOf=sv08-klipper.service',observer)
        self.assertEqual((units/'sv08-klipper.service.wants/sv08-calibration-reconcile.service').readlink(),Path('../sv08-calibration-reconcile.service'))
        self.assertFalse((units/'multi-user.target.wants/sv08-calibration-reconcile.service').exists())
        for name in ('sv08-klipper.service', 'sv08-moonraker.service'):
            self.assertFalse((wants / name).exists())
        self.assertFalse((target / 'seed/config/printer.cfg').exists())
        self.assertFalse((target / 'stale.py').exists())
        self.assertEqual((target / 'seed/authorized_keys').read_text(),
                         'ssh-ed25519 fixture owner\n')
        self.assertEqual(command.readlink(), Path('../lib/sv08/sv08_state.py'))

    def test_refresh_refuses_unrecognized_command_before_removing_runtime(self):
        temporary = tempfile.TemporaryDirectory(dir=fixture_root()); self.addCleanup(temporary.cleanup)
        work = Path(temporary.name); root = work / 'rootfs'
        (work / 'refresh-complete').touch()
        for directory in ('etc', 'usr/bin', 'usr/lib/sv08'):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / 'etc/passwd').write_text('sv08:x:1000:1000::/home/sv08:/bin/bash\n')
        (root / 'etc/group').write_text('sv08:x:1000:\n')
        stale = root / 'usr/lib/sv08/stale.py'; stale.write_text('keep me\n')
        (root / 'usr/bin/sv08-state').write_text('unrecognized\n')

        with self.assertRaisesRegex(ValueError, 'runtime command conflicts'):
            stage(work, self.manifest(), refresh=True)
        self.assertEqual(stale.read_text(), 'keep me\n')
