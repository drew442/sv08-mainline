"""Check the actual RAM-writer gate for both U-Boot environment records."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.ed25519_build import ED25519_SOURCES


REPO = Path(__file__).resolve().parents[1]
WRITER = REPO / 'tests/fixtures/sd-network-root/emmc_image_writer.c'


class RecoveryEnvironmentTests(unittest.TestCase):
    def test_only_job_bound_exhausted_crc_valid_record_is_admitted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / 'env-check'
            flags = [
                '-DSV08_H616_COMMISSIONING=1', '-DSV08_H616_RECOVERY_HANDOFF=1',
                '-DSV08_RECOVERY_ENV_SELFTEST=1',
                '-DSV08_H616_EXPECTED_CID="00000000000000000000000000000001"',
                '-DSV08_H616_EXPECTED_DEV_T="8:0"',
                '-DSV08_H616_BOARD_COMPATIBLE="test,synthetic-h616"',
                '-DSV08_H616_CLAIM_SERVER="10.0.2.2"',
                '-DSV08_JOB_ID="test-job"',
            ]
            subprocess.run(['cc', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-function', *flags,
                            f'-I{REPO / "upstream/monocypher/src"}',
                            f'-I{REPO / "upstream/monocypher/src/optional"}',
                            '-o', binary, WRITER,
                            *(str(path) for path in ED25519_SOURCES)],
                           check=True)

            def result(name, text, *, corrupt=False):
                source = root / (name+'.txt')
                source.write_text(text)
                record = root / (name+'.bin')
                subprocess.run(['mkenvimage', '-r', '-s', '65536', '-o', record,
                                source], check=True, capture_output=True)
                if corrupt:
                    with record.open('r+b') as stream:
                        stream.seek(100)
                        byte = stream.read(1)
                        stream.seek(100)
                        stream.write(bytes([byte[0] ^ 1]))
                return subprocess.check_output([binary, record], text=True).strip()

            base = ('sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A B\n'
                    'BOOT_A_LEFT=0\nBOOT_B_LEFT=0\n'
                    'sv08_reimage_arm=test-job\n')
            self.assertEqual(result('valid', base), 'admitted')
            self.assertEqual(result('counter', base.replace('BOOT_A_LEFT=0',
                                                             'BOOT_A_LEFT=1')), 'refused')
            self.assertEqual(result('wrong-job', base.replace('test-job',
                                                               'other-job')), 'refused')
            self.assertEqual(result('bad-crc', base, corrupt=True), 'refused')
            self.assertEqual(result('duplicate', base+'BOOT_A_LEFT=0\n'), 'refused')


if __name__ == '__main__':
    unittest.main()
