from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_boot import (slot_from_cmdline, verify_devices, initialize_identity,
                       initialize_owner_authorized_keys, prepare_permissions,
                       bind_boot_identity)
from sv08_state import Store


class BootIdentityTests(unittest.TestCase):
    def test_runtime_jobs_use_changing_kernel_boot_not_persistent_identity(self):
        from sv08_admin_jobs import Jobs
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / 'data', reserve_bytes=0)
            store.initialize()
            original = store.prepare_boot('A', 'release-1')
            first = 'b16f14c8-389c-4ef4-92c9-c123e1bd7975'
            second = '3902033a-d823-4880-8b2f-14e180165c12'
            with patch('sv08_boot.Path.read_text', return_value=first):
                one = bind_boot_identity(original)
            with patch('sv08_boot.Path.read_text', return_value=second):
                two = bind_boot_identity(original)
            self.assertEqual(Jobs(store.root / 'jobs', one['boot_id']).boot_id, first)
            self.assertEqual(Jobs(store.root / 'jobs', two['boot_id']).boot_id, second)
            self.assertNotIn('boot_id', original)
            self.assertNotIn('boot_id', store.load()['slots']['A'])
            for bad in ('', 'machine-id', '00000000-0000-0000-0000-000000000000'):
                with patch('sv08_boot.Path.read_text', return_value=bad), self.assertRaises(ValueError):
                    bind_boot_identity(original)

    def test_copied_application_files_receive_application_ownership(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / 'data', reserve_bytes=0)
            store.initialize()
            boot = store.prepare_boot('A', 'release-1')
            config = Path(boot['generation']) / 'config/printer.cfg'
            config.write_text('example')
            store.expect_trial('B', 'release-2', 'A')
            trial = store.prepare_boot('B', 'release-2')
            copied = Path(trial['generation']) / 'config/printer.cfg'
            with patch('sv08_boot.os.chown') as chown:
                prepare_permissions(store.root, trial['generation'])
            self.assertIn(unittest.mock.call(copied, 1000, 1000), chown.call_args_list)
            self.assertNotIn(unittest.mock.call(config, 1000, 1000), chown.call_args_list)

    def test_cockpit_certificate_store_is_private_root_owned_persistent_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / 'data', reserve_bytes=0)
            store.initialize()
            certs = store.root / 'system/cockpit/ws-certs.d'
            self.assertTrue(certs.is_dir())
            cert = certs / 'fixture.crt'
            key = certs / 'fixture.key'
            cert.write_text('certificate sentinel')
            key.write_text('private key sentinel')
            with patch('sv08_boot.os.chown') as chown:
                prepare_permissions(store.root, store.prepare_boot('A', 'release-1')['generation'])
            self.assertEqual(certs.stat().st_mode & 0o777, 0o700)
            self.assertIn(unittest.mock.call(certs, 0, 0), chown.call_args_list)
            store.initialize()
            store.expect_trial('B', 'release-2', 'A')
            with patch('sv08_boot.os.chown'):
                prepare_permissions(store.root, store.prepare_boot('B', 'release-2')['generation'])
            self.assertEqual(cert.read_text(), 'certificate sentinel')
            self.assertEqual(key.read_text(), 'private key sentinel')

    def test_cockpit_certificate_store_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / 'data', reserve_bytes=0)
            store.initialize()
            certs = store.root / 'system/cockpit/ws-certs.d'
            certs.rmdir()
            outside = Path(temporary) / 'outside'
            outside.mkdir()
            certs.symlink_to(outside, target_is_directory=True)
            with patch('sv08_boot.os.chown'), self.assertRaisesRegex(ValueError, 'real persistent directory'):
                prepare_permissions(store.root, store.prepare_boot('A', 'release-1')['generation'])

    def test_identity_symlink_does_not_modify_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / 'data')
            store.initialize()
            outside = Path(temporary) / 'outside'
            outside.write_text('preserve')
            (store.root / 'system/machine-id').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'symlinks'):
                initialize_identity(store.root)
            self.assertEqual(outside.read_text(), 'preserve')

    def test_owner_key_is_seeded_once_and_preserves_owner_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = Store(root / 'data', reserve_bytes=0)
            store.initialize()
            seed = root / 'authorized_keys'
            seed.write_text('ssh-ed25519 initial owner-key\n')
            self.assertTrue(initialize_owner_authorized_keys(
                store.root, seed, uid=os.getuid(), gid=os.getgid()))
            key = store.root / 'users/sv08/.ssh/authorized_keys'
            self.assertEqual(key.read_text(), 'ssh-ed25519 initial owner-key\n')
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)
            key.write_text('ssh-ed25519 owner-replacement\n')
            seed.write_text('ssh-ed25519 image-update-key\n')
            self.assertFalse(initialize_owner_authorized_keys(
                store.root, seed, uid=os.getuid(), gid=os.getgid()))
            self.assertEqual(key.read_text(), 'ssh-ed25519 owner-replacement\n')

    def test_owner_key_symlink_is_rejected_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = Store(root / 'data', reserve_bytes=0)
            store.initialize()
            seed = root / 'authorized_keys'
            seed.write_text('ssh-ed25519 initial owner-key\n')
            ssh = store.root / 'users/sv08/.ssh'
            ssh.mkdir()
            outside = root / 'outside'
            outside.write_text('preserve')
            (ssh / 'authorized_keys').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'not a regular'):
                initialize_owner_authorized_keys(store.root, seed,
                                                 uid=os.getuid(), gid=os.getgid())
            self.assertEqual(outside.read_text(), 'preserve')

    def test_slot_must_be_unambiguous(self):
        self.assertEqual(slot_from_cmdline('root=x ro rauc.slot=A'), 'A')
        for cmdline in ('', 'rauc.slot=C', 'rauc.slot=A rauc.slot=B', 'rauc.slot=A rauc.slot=A'):
            with self.assertRaises(ValueError):
                slot_from_cmdline(cmdline)

    def test_wrong_data_partition_rejected(self):
        config = {'devices': {'root-a': 'root', 'boot-a': 'boot', 'data': 'data'}}
        with patch('sv08_boot.device_number', side_effect=['1:1', '1:2', '1:3']), patch('sv08_boot.subprocess.check_output', side_effect=['1:1', '1:9']):
            with self.assertRaisesRegex(ValueError, 'Mounted device'):
                verify_devices(config, 'A')
