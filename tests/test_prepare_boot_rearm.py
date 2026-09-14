import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
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

    @unittest.skipUnless(shutil.which('mkenvimage') and shutil.which('fw_printenv'), 'requires U-Boot tools')
    def test_binary_is_redundant_environment_reader_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            text = work / 'environment.txt'; text.write_text(tool.environment_text())
            copy = work / 'environment.bin'
            subprocess.run(['mkenvimage', '-r', '-s', '65536', '-o', str(copy), str(text)], check=True)
            disk = work / 'disk.img'; disk.write_bytes(copy.read_bytes() * 2)
            config = work / 'fw_env.config'
            config.write_text(f'{disk} 0x0 0x10000\n{disk} 0x10000 0x10000\n')
            actual = dict(line.split('=', 1) for line in subprocess.check_output(['fw_printenv', '-c', str(config)], text=True).splitlines())
            self.assertEqual((actual['BOOT_ORDER'], actual['BOOT_A_LEFT'], actual['BOOT_B_LEFT']), ('A', '3', '0'))
