"""Exercise the diagnostic persistent environment with actual U-Boot tools."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
spec = importlib.util.spec_from_file_location('board_diagnostic', REPO / 'scripts/assemble_board_diagnostic.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class DiagnosticTests(unittest.TestCase):
    def test_partition_identity_does_not_depend_on_profile_list_order(self):
        profile = json.loads((REPO / 'configs/host-os/recovery-test-sv08-01.json').read_text())
        parts = m.layout(json.loads((REPO / 'configs/images/host-ab.json').read_text()))
        expected = m.expected_partitions(profile, parts)
        profile['partitions'].reverse()
        self.assertEqual(m.expected_partitions(profile, parts), expected)
        parts[4]['size_bytes'] += 1024**2
        with self.assertRaises(ValueError): m.expected_partitions(profile, parts)

    @unittest.skipUnless(shutil.which('mkenvimage') and shutil.which('fw_printenv'), 'requires U-Boot image/environment tools')
    def test_complete_environment_survives_raw_crc_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            text = work / 'seed.txt'; text.write_text(m.seed_environment())
            binary = work / 'env.bin'
            subprocess.run(['mkenvimage', '-r', '-s', '65536', '-o', str(binary), str(text)], check=True)
            disk = work / 'disk.img'
            disk.write_bytes(binary.read_bytes()*2)
            config = work / 'fw_env.config'
            config.write_text(f'{disk} 0x0 0x10000\n{disk} 0x10000 0x10000\n')
            output = subprocess.check_output(['fw_printenv', '-c', str(config)], text=True)
            actual = dict(line.split('=', 1) for line in output.splitlines())
            expected = dict(line.split('=', 1) for line in text.read_text().splitlines())
            self.assertEqual(actual, expected)
            self.assertEqual((actual['BOOT_ORDER'], actual['BOOT_A_LEFT'], actual['BOOT_B_LEFT']), ('A', '3', '0'))
            self.assertIn('bootflow scan -b', actual['sv08_dispatch'])
            self.assertIn('systemd.mask=sv08-klipper.service', actual['sv08_consoleargs'])
            # A bad first copy must retain the same complete policy via its peer.
            with disk.open('r+b') as stream: stream.write(b'BAD!')
            self.assertEqual(subprocess.check_output(['fw_printenv', '-c', str(config)], text=True), output)

    def test_recovery_has_independent_raw_ramdisk_and_bound_partition(self):
        profile = json.loads((REPO / 'configs/host-os/recovery-test-sv08-01.json').read_text())
        command = m.recovery_script(profile, 'a'*64)
        self.assertIn('root=PARTUUID='+profile['recovery']['partuuid'], command)
        self.assertIn('${ramdisk_addr_r}:${sv08_recovery_initrd_size}', command)
        self.assertNotIn('root-a', command)
        self.assertNotIn('uInitrd', command)
        for digest in ('', 'A'*64, 'a'*63, 'a'*64+'; reset'):
            with self.assertRaises(ValueError): m.recovery_script(profile, digest)


if __name__ == '__main__': unittest.main()
