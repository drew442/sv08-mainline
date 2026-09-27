"""Exercise ordered recovery staging and boot-policy arming on regular files."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zlib

from scripts.build_h616_reimage_candidate import build as build_writer
from scripts.build_h616_recovery_handoff import build as build_handoff, script_text
from scripts.stage_h616_recovery_handoff import (arm_regular_image,
                                                 parse_env_record,
                                                 stage_mounted_recovery,
                                                 verify_artifact)
from tests.test_h616_reimage_candidate import signed_inputs
from tests.test_h616_recovery_handoff_builder import base_initrd


REPO = Path(__file__).resolve().parents[1]


def create_reviewed_target(path, policy):
    image_bytes = policy['image_bytes']
    with path.open('xb') as stream:
        stream.truncate(image_bytes)
    layout = policy['image_layout']
    command = ['sgdisk', '--clear', f"--disk-guid={layout['disk_guid']}",
               '--move-main-table=4096']
    for part in layout['partitions']:
        start = part['offset_bytes'] // 512
        last = (part['offset_bytes'] + part['size_bytes']) // 512 - 1
        index = part['number']
        command += [f'--new={index}:{start}:{last}',
                    f"--change-name={index}:{part['name']}",
                    f"--partition-guid={index}:{part['partuuid']}"]
    subprocess.run(command + [str(path)], check=True, capture_output=True)
    with path.open('r+b') as stream:
        stream.truncate(8 * 1024 * 1024 * 1024)


class RecoveryStageTests(unittest.TestCase):
    def test_faulted_staging_and_separate_two_copy_arm(self):
        (REPO / 'local').mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            root = Path(temporary)
            files, policy, job = signed_inputs(root)
            bundle = root / 'bundle'
            build_writer(bundle, *files.values(), now=1500, synthetic_test=True,
                         trusted_initramfs=True, recovery_handoff=True,
                         source_server='10.0.2.2', source_export='/srv/sv08-sd-nfs')
            kernel = root / 'Image';kernel.write_bytes(b'K'*4096)
            dtb = root / 'board.dtb';dtb.write_bytes(b'D'*512)
            artifact = root / 'handoff'
            build_handoff(artifact, kernel, base_initrd(root), dtb, bundle,
                          '10.0.2.2', '/srv/sv08-sd-nfs', 12345)
            build_hash = hashlib.sha256((artifact / 'build.json').read_bytes()).hexdigest()
            original_hash = hashlib.sha256(b'ORIGINAL-UI').hexdigest()
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
                                               bundle=bundle,
                                               verification_key=files['key'], now=1500,
                                               expected_build_sha256=build_hash,
                                               expected_original_sha256=original_hash,
                                               disposable_directory_fixture=True,
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
            with self.assertRaisesRegex(ValueError, 'reviewed build'):
                stage_mounted_recovery(recovery, artifact, journal,
                                       bundle=bundle,
                                       verification_key=files['key'], now=1500,
                                       expected_build_sha256='0' * 64,
                                       expected_original_sha256=original_hash,
                                       disposable_directory_fixture=True)
            with self.assertRaisesRegex(ValueError, 'Stale job'):
                stage_mounted_recovery(recovery, artifact, journal,
                                       bundle=bundle,
                                       verification_key=files['key'], now=3000,
                                       expected_build_sha256=build_hash,
                                       expected_original_sha256=original_hash,
                                       disposable_directory_fixture=True)
            self.assertFalse(journal.exists())
            with self.assertRaisesRegex(ValueError, 'Original recovery script'):
                stage_mounted_recovery(recovery, artifact, journal,
                                       bundle=bundle,
                                       verification_key=files['key'], now=1500,
                                       expected_build_sha256=build_hash,
                                       expected_original_sha256='0' * 64,
                                       disposable_directory_fixture=True)
            stage_mounted_recovery(recovery, artifact, journal,
                                   bundle=bundle,
                                   verification_key=files['key'], now=1500,
                                   expected_build_sha256=build_hash,
                                   expected_original_sha256=original_hash,
                                   disposable_directory_fixture=True)
            disk = root / 'target.img'
            create_reviewed_target(disk, policy)
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
            create_reviewed_target(partial, policy)
            with partial.open('r+b') as stream:
                for offset in (0x400000, 0x800000):
                    os.pwrite(stream.fileno(), record.read_bytes(), offset)
            bound = root / 'bound-target-journal'
            bound.mkdir()
            bound_state = json.loads((root / 'after-marker-journal/state.json').read_text())
            bound_state['recovery_admission'] = {
                'target_regular_dev': disk.stat().st_dev,
                'target_regular_ino': disk.stat().st_ino,
            }
            (bound / 'state.json').write_text(json.dumps(bound_state))
            with self.assertRaisesRegex(ValueError, 'Arming target differs'):
                arm_regular_image(partial, bound, target_policy=policy)
            partial_state = arm_regular_image(partial, root / 'after-marker-journal',
                                              target_policy=policy,
                                              fault='after-arm-copy-1')
            self.assertEqual(partial_state['phase'], 'arm-copy-1-written')
            with partial.open('rb') as stream:
                banks = [parse_env_record(os.pread(stream.fileno(), 65536, offset))
                         for offset in (0x400000, 0x800000)]
            self.assertEqual(sum(bank.get(b'sv08_reimage_arm') == job['job_id'].encode()
                                 for bank in banks), 1)
            wrong_policy = dict(policy, cid='f' * 32)
            with self.assertRaisesRegex(ValueError, 'Arming policy differs'):
                arm_regular_image(disk, journal, target_policy=wrong_policy)
            with disk.open('r+b') as stream:
                original_guid_byte = os.pread(stream.fileno(), 1, 512 + 56)
                os.pwrite(stream.fileno(), bytes([original_guid_byte[0] ^ 1]), 512 + 56)
            with self.assertRaisesRegex(ValueError, 'GPT header CRC'):
                arm_regular_image(disk, journal, target_policy=policy)
            with disk.open('r+b') as stream:
                os.pwrite(stream.fileno(), original_guid_byte, 512 + 56)
            result = arm_regular_image(disk, journal, target_policy=policy)
            self.assertEqual(result['phase'], 'armed-both-verified')
            with disk.open('rb') as stream:
                for offset in (0x400000, 0x800000):
                    fields = parse_env_record(os.pread(stream.fileno(), 65536, offset))
                    self.assertEqual(fields[b'BOOT_A_LEFT'], b'0')
                    self.assertEqual(fields[b'BOOT_B_LEFT'], b'0')
                    self.assertEqual(fields[b'sv08_reimage_arm'], job['job_id'].encode())
            with self.assertRaisesRegex(ValueError, 'Marker not durably staged'):
                arm_regular_image(disk, root / 'after-fit-journal', target_policy=policy)

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

            changed_fit = root / 'changed-fit-kernel'
            shutil.copytree(artifact, changed_fit)
            fit_path = changed_fit / 'writer.itb'
            fit = bytearray(fit_path.read_bytes())
            kernel_offset = fit.find(b'K' * 64)
            self.assertGreater(kernel_offset, 0)
            fit[kernel_offset] = ord('X')
            fit_path.write_bytes(fit)
            manifest = json.loads((changed_fit / 'build.json').read_text())
            manifest['fit_crc32'] = f'{zlib.crc32(fit):08x}'
            (changed_fit / 'recovery.cmd').write_text(script_text(
                manifest['job_id'], manifest['bootargs'], len(fit), zlib.crc32(fit)))
            subprocess.run(['mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none',
                            '-n', 'SV08 one-shot recovery selector', '-d', 'recovery.cmd',
                            'recovery.scr'], cwd=changed_fit, check=True, capture_output=True)
            for name in ('writer.itb', 'recovery.scr'):
                manifest['files_sha256'][name] = hashlib.sha256(
                    (changed_fit / name).read_bytes()).hexdigest()
            (changed_fit / 'build.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'FIT component differs'):
                verify_artifact(changed_fit)


if __name__ == '__main__':
    unittest.main()
