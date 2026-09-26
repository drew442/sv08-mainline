"""Offline, synthetic identity gate checks; no real block node is opened."""
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/sd-network-root/emmc_cid_admission_test.c'


class SdNetworkCidAdmissionTests(unittest.TestCase):
    def test_native_synthetic_inventory_and_pre_open_spy(self):
        with tempfile.TemporaryDirectory(prefix='sv08-cid-admission-') as temp:
            binary = Path(temp) / 'cid-admission-test'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-o', str(binary), str(FIXTURE)], check=True)
            result = subprocess.run([str(binary)], check=True, capture_output=True,
                                    text=True)
            self.assertIn('pre-open refusal checks passed', result.stdout)

    def test_static_arm64_helper_build(self):
        with tempfile.TemporaryDirectory(prefix='sv08-cid-arm64-') as temp:
            binary = Path(temp) / 'cid-admission-test-arm64'
            subprocess.run(['aarch64-linux-gnu-gcc', '-static', '-std=c11',
                            '-Wall', '-Wextra', '-Werror', '-o', str(binary),
                            str(FIXTURE)], check=True)
            self.assertTrue(binary.is_file())

    def test_production_diagnostic_and_builder_do_not_include_cid_gate(self):
        for path in ('tests/fixtures/sd-network-root/init.c',
                     'scripts/build_sd_network_image.py'):
            self.assertNotIn('emmc_cid_admission', (ROOT / path).read_text())


if __name__ == '__main__':
    unittest.main()
