"""Exercise ordered recovery staging and boot-policy arming on regular files."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.build_h616_reimage_candidate import build as build_writer
from scripts.build_h616_recovery_handoff import build as build_handoff
from scripts.stage_h616_recovery_handoff import (arm_regular_image,
                                                 parse_env_record,
                                                 stage_mounted_recovery,
                                                 verify_artifact)
from tests.test_h616_reimage_candidate import signed_inputs
from tests.test_h616_recovery_handoff_builder import base_initrd


REPO = Path(__file__).resolve().parents[1]


class RecoveryStageTests(unittest.TestCase):
    def test_faulted_staging_and_separate_two_copy_arm(self):
        (REPO / 'local').mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            root = Path(temporary)
            files, _, job = signed_inputs(root)
            bundle = root / 'bundle'
            build_writer(bundle, *files.values(), now=1500, synthetic_test=True,
                         trusted_initramfs=True, recovery_handoff=True,
                         source_server='10.0.2.2', source_export='/srv/sv08-sd-nfs')
            kernel = root / 'Image';kernel.write_bytes(b'K'*4096)
            dtb = root / 'board.dtb';dtb.write_bytes(b'D'*512)
            artifact = root / 'handoff'
            build_handoff(artifact, kernel, base_initrd(root), dtb, bundle,
                          '10.0.2.2', '/srv/sv08-sd-nfs', 12345)
            for fault, marker_expected, wrapper_expected in (
                    ('after-original', False, False),
                    ('after-fit', False, False),
                    ('after-wrapper', False, True),
                    ('after-marker', True, True)):
                recovery = root / fault
                recovery.mkdir()
                (recovery / 'recovery.scr').write_bytes(b'ORIGINAL-UI')
                journal = root / (fault+'-journal')
                state = stage_mounted_recovery(recovery, artifact, journal,
                                               fault=fault)
                self.assertEqual(state['job_id'], job['job_id'])
                self.assertEqual((recovery / 'sv08-reimage/armed').exists(), marker_expected)
                self.assertEqual((recovery / 'recovery.scr').read_bytes() ==
                                 (artifact / 'recovery.scr').read_bytes(), wrapper_expected)
                self.assertEqual((recovery / 'sv08-reimage/recovery-original.scr').read_bytes(),
                                 b'ORIGINAL-UI')
                self.assertEqual(json.loads((journal / 'state.json').read_text())['phase'],
                                 state['phase'])
            recovery = root / 'armed-recovery'
            recovery.mkdir()
            (recovery / 'recovery.scr').write_bytes(b'ORIGINAL-UI')
            journal = root / 'arm-journal'
            stage_mounted_recovery(recovery, artifact, journal)
            disk = root / 'target.img'
            with disk.open('xb') as stream:
                stream.truncate(8 * 1024 * 1024 * 1024)
            source = root / 'initial.env'
            source.write_text('sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A B\n'
                              'BOOT_A_LEFT=3\nBOOT_B_LEFT=0\n')
            record = root / 'initial.bin'
            subprocess.run(['mkenvimage', '-r', '-s', '65536', '-o', record, source],
                           check=True, capture_output=True)
            with disk.open('r+b') as stream:
                for offset in (0x400000, 0x800000):
                    os.pwrite(stream.fileno(), record.read_bytes(), offset)
            partial = root / 'partial-target.img'
            with partial.open('xb') as stream:
                stream.truncate(8 * 1024 * 1024 * 1024)
            with partial.open('r+b') as stream:
                for offset in (0x400000, 0x800000):
                    os.pwrite(stream.fileno(), record.read_bytes(), offset)
            partial_state = arm_regular_image(partial, root / 'after-marker-journal',
                                              fault='after-arm-copy-1')
            self.assertEqual(partial_state['phase'], 'arm-copy-1-written')
            with partial.open('rb') as stream:
                banks = [parse_env_record(os.pread(stream.fileno(), 65536, offset))
                         for offset in (0x400000, 0x800000)]
            self.assertEqual(sum(bank.get(b'sv08_reimage_arm') == job['job_id'].encode()
                                 for bank in banks), 1)
            result = arm_regular_image(disk, journal)
            self.assertEqual(result['phase'], 'armed-both-verified')
            with disk.open('rb') as stream:
                for offset in (0x400000, 0x800000):
                    fields = parse_env_record(os.pread(stream.fileno(), 65536, offset))
                    self.assertEqual(fields[b'BOOT_A_LEFT'], b'0')
                    self.assertEqual(fields[b'BOOT_B_LEFT'], b'0')
                    self.assertEqual(fields[b'sv08_reimage_arm'], job['job_id'].encode())
            with self.assertRaisesRegex(ValueError, 'Marker not durably staged'):
                arm_regular_image(disk, root / 'after-fit-journal')

            changed = root / 'changed-compiled-script'
            shutil.copytree(artifact, changed)
            (changed / 'bad.cmd').write_text('echo BAD-SELECTOR\n')
            subprocess.run(['mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none',
                            '-n', 'SV08 one-shot recovery selector', '-d', 'bad.cmd',
                            'recovery.scr'], cwd=changed, check=True, capture_output=True)
            manifest = json.loads((changed / 'build.json').read_text())
            manifest['files_sha256']['recovery.scr'] = hashlib.sha256(
                (changed / 'recovery.scr').read_bytes()).hexdigest()
            (changed / 'build.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Compiled recovery selector'):
                verify_artifact(changed)


if __name__ == '__main__':
    unittest.main()
