from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_boot import slot_from_cmdline, verify_devices, initialize_identity, prepare_permissions
from sv08_state import Store


class BootIdentityTests(unittest.TestCase):
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
