import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tests/fixtures/sd-network-root/init.c'
HARNESS = ROOT / 'tests/fixtures/sd-network-root/env_parser_test.c'
MMC_HARNESS = ROOT / 'tests/fixtures/sd-network-root/emmc_locator_test.c'


class SdNetworkEnvProbeTests(unittest.TestCase):
    def test_shared_environment_parser_fixtures(self):
        with tempfile.TemporaryDirectory(prefix='sv08-env-probe-') as directory:
            binary = pathlib.Path(directory) / 'env-parser-test'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-o', str(binary), str(HARNESS)], check=True)
            result = subprocess.run([str(binary)], check=True, text=True,
                                    capture_output=True)
            self.assertIn('valid/corrupt/policy checks passed', result.stdout)

    def test_probe_has_bounded_read_only_eMMC_access(self):
        source = SOURCE.read_text()
        self.assertIn('#define ENV_A_OFFSET 0x400000', source)
        self.assertIn('#define ENV_B_OFFSET 0x800000', source)
        self.assertIn('/4022000.mmc/mmc_host', source)
        self.assertIn('emmc_device_at(EMMC_HOST_SYSFS', source)
        self.assertIn('open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW)', source)
        self.assertIn('pread(fd,', source)
        self.assertNotRegex(source, r'\b(pwrite|write|ioctl|system|popen)\s*\(')
        self.assertNotIn('O_RDWR', source)

    def test_probe_distinguishes_complete_and_incomplete_environment_pairs(self):
        source = SOURCE.read_text()
        self.assertIn('a.crc_ok && b.crc_ok ? "READ_ONLY_VALID_PAIR" :', source)
        self.assertIn('"READ_ONLY_INCOMPLETE_PAIR"', source)
        self.assertIn('return a.crc_ok && b.crc_ok;', source)
        self.assertIn('copy4_flag=%s', source)
        self.assertIn('copy8_flag=%s', source)

    def test_controller_locator_ignores_mmc_host_number_and_rejects_ambiguity(self):
        with tempfile.TemporaryDirectory(prefix='sv08-emmc-locator-') as directory:
            binary = pathlib.Path(directory) / 'emmc-locator-test'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-o', str(binary), str(MMC_HARNESS)], check=True)
            result = subprocess.run([str(binary)], check=True, text=True,
                                    capture_output=True)
            self.assertIn('numbering/uniqueness checks passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
