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
        self.assertEqual((root / 'etc/systemd/system/nginx.service').readlink(), Path('/dev/null'))
        wants = root / 'etc/systemd/system/multi-user.target.wants'
        self.assertEqual({p.name for p in wants.iterdir()},
                         {'sv08-boot-health.service', 'sv08-printer-api.service', 'sv08-mainsail.service'})
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
