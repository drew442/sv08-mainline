import copy
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import zlib

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'runtime'))
from sv08_rauc_bootloader import handle, parse_values, primary, slot_good, verify_environment_copies


class BootloaderHandlerTests(unittest.TestCase):
    def setUp(self):
        self.values = dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A',
                           BOOT_A_LEFT='3', BOOT_B_LEFT='0')
        self.writes = []
        self.context = None
        self.running_slot = 'A'

    def read(self):
        return copy.deepcopy(self.values)

    def write(self, name, value):
        self.writes.append((name, value))
        self.values[name] = value

    def operation(self):
        return self.context

    def call(self, *arguments):
        with patch('os.geteuid', return_value=0):
            return handle(list(arguments), read=self.read, write=self.write,
                          operation=self.operation, running=lambda: self.running_slot,
                          verify_copies=lambda: None)

    def test_read_operations_match_rauc_uboot_primary_and_good_semantics(self):
        self.values.update(BOOT_ORDER='B A', BOOT_A_LEFT='3', BOOT_B_LEFT='2')
        self.assertEqual(primary(self.values), 'B')
        self.assertEqual(self.call('get-primary'), 'B')
        self.assertEqual(self.call('get-current'), 'A')
        self.assertEqual(self.call('get-state', 'B'), 'good')
        self.values['BOOT_B_LEFT'] = '0'
        self.assertEqual(self.call('get-state', 'B'), 'bad')

    def test_install_bad_is_exact_noop_only_for_disabled_target(self):
        self.context = dict(action='install', slot='B')
        self.assertEqual(self.call('set-state', 'B', 'bad'), '')
        self.assertEqual(self.writes, [])
        for order, attempts in [('A B', '0'), ('A B', '3'), ('B A', '1')]:
            self.values.update(BOOT_ORDER=order, BOOT_B_LEFT=attempts)
            before = self.read()
            with self.subTest(order=order, attempts=attempts), self.assertRaisesRegex(ValueError, 'Refusing RAUC slot write'):
                self.call('set-state', 'B', 'bad')
            self.assertEqual(self.values, before)
            self.assertEqual(self.writes, [])
        self.values.update(BOOT_ORDER='B', BOOT_A_LEFT='3', BOOT_B_LEFT='0')
        self.running_slot = 'A'
        with self.assertRaisesRegex(ValueError, 'source remains selected'):
            self.call('set-state', 'B', 'bad')
        self.assertEqual(self.writes, [])

    def test_cancel_and_fallback_bad_mark_retains_rauc_disarm_semantics(self):
        self.values.update(BOOT_ORDER='B A', BOOT_B_LEFT='2')
        self.context = dict(action='set-bad', slot='B')
        self.call('set-state', 'B', 'bad')
        self.assertEqual(self.values['BOOT_ORDER'], 'A')
        self.assertEqual(self.values['BOOT_B_LEFT'], '0')
        self.assertEqual(self.values['BOOT_A_LEFT'], '3')
        self.assertFalse(slot_good(self.values, 'B'))
        self.assertEqual(primary(self.values), 'A')

    def test_good_confirmation_and_primary_activation_require_matching_context(self):
        self.context = dict(action='set-good', slot='B')
        self.call('set-state', 'B', 'good')
        self.assertEqual(self.values['BOOT_B_LEFT'], '3')
        self.context = dict(action='set-primary', slot='B')
        self.call('set-primary', 'B')
        self.assertEqual(self.values['BOOT_ORDER'], 'B A')
        self.assertEqual(self.values['BOOT_B_LEFT'], '3')
        self.assertEqual(primary(self.values), 'B')
        self.context = None
        with self.assertRaisesRegex(ValueError, 'validated arm transaction'):
            self.call('set-primary', 'A')
        with self.assertRaisesRegex(ValueError, 'validated confirmation transaction'):
            self.call('set-state', 'A', 'good')

    def test_bad_state_mutation_requires_validated_cancel_context(self):
        self.values.update(BOOT_ORDER='B A', BOOT_B_LEFT='2')
        with self.assertRaisesRegex(ValueError, 'validated cancel/fallback'):
            self.call('set-state', 'B', 'bad')
        self.assertEqual(self.values['BOOT_ORDER'], 'B A')
        self.assertEqual(self.values['BOOT_B_LEFT'], '2')
        self.assertEqual(self.writes, [])

    def test_malformed_or_extra_fw_printenv_output_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Malformed'):
            parse_values('malformed\n')
        with self.assertRaisesRegex(ValueError, 'Unrecognized'):
            parse_values('sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A A\nBOOT_A_LEFT=3\nBOOT_B_LEFT=0\n')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            parse_values('sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A\nBOOT_ORDER=B\nBOOT_A_LEFT=3\nBOOT_B_LEFT=0\n')

    def test_both_raw_environment_copies_must_have_valid_crc_and_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'emmc.img'
            with target.open('wb') as stream:
                stream.truncate(0x900000)
            values = b'sv08_env_layout=ab-8gb-v1\0BOOT_ORDER=A\0BOOT_A_LEFT=3\0BOOT_B_LEFT=0\0\0'
            bank = bytearray(b'\xff' * 0x10000)
            bank[4] = 3
            bank[5:5+len(values)] = values
            bank[:4] = zlib.crc32(bank[5:]).to_bytes(4, 'little')
            with target.open('r+b') as stream:
                for offset, flag in ((0x400000, 3), (0x800000, 2)):
                    item = bytearray(bank)
                    item[4] = flag
                    item[:4] = zlib.crc32(item[5:]).to_bytes(4, 'little')
                    stream.seek(offset)
                    stream.write(item)
            config = Path(directory) / 'fw_env.config'
            config.write_text(f'{target} 0x400000 0x10000\n{target} 0x800000 0x10000\n')
            verify_environment_copies(config)
            with target.open('r+b') as stream:
                stream.seek(0x800000+100)
                stream.write(b'X')
            with self.assertRaisesRegex(ValueError, 'bad CRC'):
                verify_environment_copies(config)


if __name__ == '__main__':
    unittest.main()
