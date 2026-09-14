import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_boot_rearm', REPO / 'scripts/prepare_boot_rearm.py')
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)


class PrepareBootRearmTests(unittest.TestCase):
    def test_text_contains_exact_rearm_policy(self):
        values = dict(line.split('=', 1) for line in tool.environment_text().splitlines())
        self.assertEqual({key: values[key] for key in ('sv08_env_layout', 'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT')},
                         {'sv08_env_layout': 'ab-8gb-v1', 'BOOT_ORDER': 'A', 'BOOT_A_LEFT': '3', 'BOOT_B_LEFT': '0'})
        self.assertIn('systemd.mask=sv08-klipper.service', values['sv08_consoleargs'])

    @unittest.skipUnless(shutil.which('mkenvimage'), 'requires U-Boot tools')
    def test_binary_is_two_valid_serial_ordered_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            output = work / 'pair.bin'
            text = work / 'environment.txt'; text.write_text(tool.environment_text())
            single = work / 'single.bin'
            subprocess.run(['mkenvimage', '-r', '-s', '65536', '-o', str(single), str(text)], check=True)
            first, second = bytearray(single.read_bytes()), bytearray(single.read_bytes())
            first[4], second[4] = 5, 6
            output.write_bytes(first + second)
            pair = output.read_bytes()
            self.assertTrue(tool.valid_copy(pair[:65536]))
            self.assertTrue(tool.valid_copy(pair[65536:]))
            self.assertEqual((pair[4], pair[65536 + 4]), (5, 6))
