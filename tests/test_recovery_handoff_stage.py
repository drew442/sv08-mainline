"""Exercise ordered recovery staging and boot-policy arming on regular files."""
import json
import hashlib
import gzip
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
import zlib
from unittest import mock

from scripts.build_h616_reimage_candidate import (build as build_writer, digest,
    WRITER, V5_IMAGE_SHA256, expected_image_layout, verify_compiled_writer)
from scripts.ed25519_build import ED25519_SOURCES, raw_public_key
from scripts.build_h616_recovery_handoff import build as build_handoff, script_text
from scripts.stage_h616_recovery_handoff import (arm_regular_image,
                                                 activate_mounted_recovery,
                                                 parse_env_record,
                                                 stage_mounted_recovery,
                                                 verify_artifact, verify_signed_stage_bundle)
from scripts import stage_h616_recovery_handoff as stager
from tests.test_h616_reimage_candidate import signed_inputs
from tests.sv08_emmc_job import canonical_json
from tests.test_h616_recovery_handoff_builder import base_initrd


REPO = Path(__file__).resolve().parents[1]


def inert_purpose_bundle(root, *, preflight_only):
    """Compile actual C with an expired fixture job; never a physical candidate.

    The production builder still refuses fixture verification keys for physical
    builds. This direct offline compiler harness does not relax that guard.
    """
    root.mkdir(parents=True)
    files, policy, job = signed_inputs(root)
    policy.update(board_compatible='fixture,offline-h616', image_sha256=V5_IMAGE_SHA256,
                  image_layout=expected_image_layout(False, V5_IMAGE_SHA256))
    files['policy'].write_bytes(canonical_json(policy))
    job['format'] = ('sv08-h616-signed-preflight-v1' if preflight_only else
                     'sv08-h616-signed-reimage-v1')
    job['target_policy_sha256'] = digest(canonical_json(policy))
    job['source']['sha256'] = V5_IMAGE_SHA256
    job['image'].update(sha256=V5_IMAGE_SHA256, layout=policy['image_layout'])
    files['job'].write_bytes(canonical_json(job))
    subprocess.run(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', root / 'signer.pem',
                    '-in', files['job'], '-out', files['signature']],
                   check=True, capture_output=True, timeout=30)
    bundle = root / 'bundle'
    bundle.mkdir()
    for name, key in [('job.json', 'job'), ('job.sig', 'signature'),
                      ('commissioning-target-policy.json', 'policy')]:
        shutil.copyfile(files[key], bundle / name)
    (bundle / 'expected.sha256').write_text(V5_IMAGE_SHA256 + '\n')
    receipt_key = (REPO / 'tests/fixtures/sd-network-root/receipt-test-keys/test-verification-key.pem').read_bytes()
    flags = ['-DSV08_H616_COMMISSIONING=1', '-DSV08_H616_TRUSTED_INITRAMFS=1',
             '-DSV08_H616_RECOVERY_HANDOFF=1',
             f'-DSV08_H616_EXPECTED_CID="{policy["cid"]}"',
             f'-DSV08_H616_EXPECTED_DEV_T="{policy["dev_t"]}"',
             f'-DSV08_H616_BOARD_COMPATIBLE="{policy["board_compatible"]}"',
             f'-DSV08_H616_CLAIM_SERVER="{policy["claim_server"]}"',
             '-DSV08_IMAGE_NFS_SOURCE="10.0.2.2:/srv/sv08-sd-nfs"',
             f'-DSV08_JOB_ID="{job["job_id"]}"',
             f'-DSV08_JOB_DESCRIPTOR_SHA256="{digest(files["job"].read_bytes())}"',
             f'-DSV08_TARGET_POLICY_SHA256="{digest(files["policy"].read_bytes())}"',
             f'-DSV08_JOB_SIGNATURE_SHA256="{digest(files["signature"].read_bytes())}"',
             f'-DSV08_SOURCE_SHA256="{V5_IMAGE_SHA256}"',
             '-DSV08_JOB_NOT_BEFORE=1000LL', '-DSV08_JOB_EXPIRES=2000LL',
             f'-DSV08_RECEIPT_PUBLIC_KEY_HEX="{raw_public_key(receipt_key).hex()}"',
             '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections']
    if preflight_only:
        flags += ['-DSV08_H616_PREFLIGHT_ONLY=1', '-Wno-unused-variable', '-Wno-unused-function']
    subprocess.run(['aarch64-linux-gnu-gcc', '-static', '-Os', '-D_FORTIFY_SOURCE=2',
                    '-Wall', '-Wextra', '-Werror', *flags,
                    f'-I{REPO / "upstream/monocypher/src"}',
                    f'-I{REPO / "upstream/monocypher/src/optional"}',
                    '-o', str(bundle / 'sd-network-init'), str(WRITER),
                    *(str(path) for path in ED25519_SOURCES)],
                   check=True, capture_output=True, timeout=120)
    manifest = {'status': 'nondeployable-commissioning-candidate', 'mode': 'h616-commissioning',
                'offline_expired_fixture': True, 'bootable_sd_image': False,
                'claim_trigger_provisioned': False, 'trusted_initramfs': True,
                'recovery_handoff': True, 'preflight_only': preflight_only,
                'synthetic_test': False, 'job_format': job['format'],
                'image_nfs_source': '10.0.2.2:/srv/sv08-sd-nfs'}
    for name, key in [('sd-network-init', 'binary_sha256'), ('job.json', 'job_sha256'),
                      ('job.sig', 'signature_sha256'),
                      ('commissioning-target-policy.json', 'policy_sha256')]:
        manifest[key] = digest((bundle / name).read_bytes())
    manifest['compiled_purpose_sha256'] = verify_compiled_writer(bundle, manifest)
    (bundle / 'reimage-manifest.json').write_text(json.dumps(manifest, sort_keys=True))
    return bundle, files['key'], policy, job


def purpose_artifact(root, *, preflight_only):
    bundle, key, policy, job = inert_purpose_bundle(root, preflight_only=preflight_only)
    kernel, dtb = root / 'Image', root / 'board.dtb'
    kernel.write_bytes(b'K' * 4096)
    dtb.write_bytes(b'D' * 512)
    artifact = root / 'handoff'
    build_handoff(artifact, kernel, base_initrd(root), dtb, bundle,
                  '10.0.2.2', '/srv/sv08-sd-nfs', 12345)
    return artifact, bundle, key, policy, job


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
                    ('after-wrapper', False, True)):
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
            bound_state = json.loads((root / 'after-wrapper-journal/state.json').read_text())
            bound_state['recovery_admission'] = {
                'target_regular_dev': disk.stat().st_dev,
                'target_regular_ino': disk.stat().st_ino,
            }
            (bound / 'state.json').write_text(json.dumps(bound_state))
            with self.assertRaisesRegex(ValueError, 'Arming target differs'):
                arm_regular_image(partial, bound, target_policy=policy)
            partial_state = arm_regular_image(partial, root / 'after-wrapper-journal',
                                              target_policy=policy,
                                              fault='after-arm-copy-1')
            self.assertEqual(partial_state['phase'], 'arm-copy-1-written')
            self.assertFalse((root / 'after-wrapper/sv08-reimage/armed').exists())
            with self.assertRaisesRegex(ValueError, 'Both environment copies'):
                activate_mounted_recovery(root / 'after-wrapper', artifact,
                                          root / 'after-wrapper-journal', image=partial,
                                          target_policy=policy,
                                          disposable_directory_fixture=True)
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
            self.assertFalse((recovery / 'sv08-reimage/armed').exists())
            preserved = recovery / 'sv08-reimage/recovery-original.scr'
            preserved.write_bytes(b'CHANGED-UI')
            with self.assertRaisesRegex(ValueError, 'Staged handoff changed'):
                activate_mounted_recovery(
                    recovery, artifact, journal, image=disk,
                    target_policy=policy, disposable_directory_fixture=True)
            preserved.write_bytes(b'ORIGINAL-UI')
            activated = activate_mounted_recovery(
                recovery, artifact, journal, image=disk, target_policy=policy,
                disposable_directory_fixture=True)
            self.assertEqual(activated['phase'], 'marker-durable')
            self.assertEqual((recovery / 'sv08-reimage/armed').read_bytes(),
                             b'SV08-REIMAGE-ONCE\n')
            with disk.open('rb') as stream:
                for offset in (0x400000, 0x800000):
                    fields = parse_env_record(os.pread(stream.fileno(), 65536, offset))
                    self.assertEqual(fields[b'BOOT_A_LEFT'], b'0')
                    self.assertEqual(fields[b'BOOT_B_LEFT'], b'0')
                    self.assertEqual(fields[b'sv08_reimage_arm'], job['job_id'].encode())
            with self.assertRaisesRegex(ValueError, 'Recovery wrapper not durably staged'):
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


class PurposeStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (REPO / 'local').mkdir(exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=REPO / 'local')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.preflight = purpose_artifact(cls.root / 'preflight', preflight_only=True)
        cls.write = purpose_artifact(cls.root / 'write', preflight_only=False)

    def test_actual_signed_stage_accepts_both_purposes_before_marker(self):
        for fixture in (self.preflight, self.write):
            artifact, bundle, key, policy, job = fixture
            with self.subTest(purpose=job['format']):
                real_run = subprocess.run
                def supported_tools(argv, *args, **kwargs):
                    self.assertNotIn(Path(argv[0]).name, ('readelf', 'unmkinitramfs'))
                    return real_run(argv, *args, **kwargs)
                with mock.patch.object(stager.subprocess, 'run', side_effect=supported_tools):
                    self.assertEqual(verify_signed_stage_bundle(verify_artifact(artifact), bundle,
                                                                key, now=1500), policy)
                recovery = artifact.parent / 'recovery'
                recovery.mkdir()
                (recovery / 'recovery.scr').write_bytes(b'ORIGINAL-UI')
                journal = artifact.parent / 'journal'
                state = stage_mounted_recovery(
                    recovery, artifact, journal, bundle=bundle, verification_key=key, now=1500,
                    expected_build_sha256=digest((artifact / 'build.json').read_bytes()),
                    expected_original_sha256=digest(b'ORIGINAL-UI'),
                    disposable_directory_fixture=True)
                self.assertEqual(state['phase'], 'wrapper-durable')
                self.assertEqual(state['build_sha256'], digest((artifact / 'build.json').read_bytes()))
                self.assertFalse((recovery / 'sv08-reimage/armed').exists())

    def test_recomputed_unsigned_labels_cannot_turn_actual_write_binary_into_preflight(self):
        artifact, original_bundle, key, _, _ = self.preflight
        _, write_bundle, _, _, _ = self.write
        bundle = self.root / 'relabelled-bundle'
        shutil.copytree(original_bundle, bundle)
        shutil.copyfile(write_bundle / 'sd-network-init', bundle / 'sd-network-init')
        writer_manifest = json.loads((bundle / 'reimage-manifest.json').read_text())
        writer_manifest['binary_sha256'] = digest((bundle / 'sd-network-init').read_bytes())
        (bundle / 'reimage-manifest.json').write_text(json.dumps(writer_manifest))
        manifest = verify_artifact(artifact)
        manifest['composition'] = dict(manifest['composition'],
            bundle_manifest_sha256=digest((bundle / 'reimage-manifest.json').read_bytes()),
            writer_sha256=writer_manifest['binary_sha256'])
        manifest['writer_sha256'] = writer_manifest['binary_sha256']
        with self.assertRaisesRegex(ValueError, 'Actual ELF compiled purpose'):
            verify_signed_stage_bundle(manifest, bundle, key, now=1500)
        # Composer refuses the same bundle before creating artifact files.
        with self.assertRaisesRegex(ValueError, 'Actual ELF compiled purpose'):
            build_handoff(self.root / 'refused-compose', artifact / 'Image',
                          artifact / 'writer-initrd.img', artifact / 'sv08.dtb', bundle,
                          '10.0.2.2', '/srv/sv08-sd-nfs', 12345)
        self.assertFalse((self.root / 'refused-compose').exists())

    def test_stage_refusals_precede_journal_or_recovery_mutation(self):
        artifact, bundle, key, _, _ = self.preflight
        for name, change, now, error in (
                ('artifact-write-label', {'preflight_only': False}, 1500, 'purpose'),
                ('nonboolean-label', {'preflight_only': 1}, 1500, 'purpose'),
                ('expired', {}, 3000, 'Stale job')):
            changed_artifact = self.root / (name + '-artifact')
            shutil.copytree(artifact, changed_artifact)
            manifest = json.loads((changed_artifact / 'build.json').read_text())
            manifest.update(change)
            (changed_artifact / 'build.json').write_text(json.dumps(manifest))
            recovery = self.root / (name + '-recovery')
            recovery.mkdir()
            (recovery / 'recovery.scr').write_bytes(b'ORIGINAL-UI')
            journal = self.root / (name + '-journal')
            with self.assertRaisesRegex(ValueError, error):
                stage_mounted_recovery(
                    recovery, changed_artifact, journal, bundle=bundle, verification_key=key, now=now,
                    expected_build_sha256=digest((changed_artifact / 'build.json').read_bytes()),
                    expected_original_sha256=digest(b'ORIGINAL-UI'),
                    disposable_directory_fixture=True)
            self.assertFalse(journal.exists())
            self.assertFalse((recovery / 'sv08-reimage').exists())

    def test_signed_cross_purpose_and_invalid_signature_are_refused(self):
        artifact, bundle, key, _, _ = self.preflight
        _, write_bundle, _, _, _ = self.write
        manifest = verify_artifact(artifact)
        manifest['composition'] = dict(manifest['composition'],
            bundle_manifest_sha256=digest((write_bundle / 'reimage-manifest.json').read_bytes()))
        with self.assertRaisesRegex(ValueError, 'purpose'):
            verify_signed_stage_bundle(manifest, write_bundle, key, now=1500)
        changed = self.root / 'bad-signature-bundle'
        shutil.copytree(bundle, changed)
        signature = bytearray((changed / 'job.sig').read_bytes())
        signature[0] ^= 1
        (changed / 'job.sig').write_bytes(signature)
        writer_manifest = json.loads((changed / 'reimage-manifest.json').read_text())
        writer_manifest['signature_sha256'] = digest(signature)
        (changed / 'reimage-manifest.json').write_text(json.dumps(writer_manifest))
        manifest = verify_artifact(artifact)
        manifest['composition'] = dict(manifest['composition'],
            bundle_manifest_sha256=digest((changed / 'reimage-manifest.json').read_bytes()))
        with self.assertRaisesRegex(ValueError, 'Invalid detached job signature'):
            verify_signed_stage_bundle(manifest, changed, key, now=1500)

    def test_actual_initramfs_writer_must_match_bundle(self):
        artifact, bundle, key, _, _ = self.preflight
        _, other_bundle, _, _, _ = self.write
        changed = self.root / 'changed-embedded-writer'
        shutil.copytree(artifact, changed)
        unpacked = changed / 'unpacked'
        subprocess.run(['unmkinitramfs', changed / 'writer-initrd.img', unpacked],
                       check=True, capture_output=True, timeout=30)
        shutil.copyfile(other_bundle / 'sd-network-init', unpacked / 'trusted-writer')
        paths = ['.', *(str(p.relative_to(unpacked)) for p in sorted(unpacked.rglob('*')))]
        archive = changed / 'changed.cpio'
        with archive.open('wb') as stream:
            subprocess.run(['cpio', '--null', '--quiet', '--reproducible', '--owner=0:0',
                            '-o', '-H', 'newc'], cwd=unpacked,
                           input=('\0'.join(paths) + '\0').encode(), stdout=stream,
                           check=True, timeout=30)
        with (changed / 'writer-initrd.img').open('wb') as stream:
            subprocess.run(['gzip', '-n', '-9', '-c', archive], stdout=stream,
                           check=True, timeout=30)
        subprocess.run(['mkimage', '-f', 'writer.its', 'writer.itb'], cwd=changed,
                       check=True, capture_output=True, timeout=30)
        manifest = json.loads((changed / 'build.json').read_text())
        fit = (changed / 'writer.itb').read_bytes()
        manifest.update(fit_bytes=len(fit), fit_crc32=f'{zlib.crc32(fit):08x}')
        manifest['composition']['initramfs_sha256'] = digest((changed / 'writer-initrd.img').read_bytes())
        manifest['composition']['initramfs_cpio_sha256'] = digest(archive.read_bytes())
        (changed / 'recovery.cmd').write_text(script_text(manifest['job_id'], manifest['bootargs'],
                                                        len(fit), zlib.crc32(fit)))
        subprocess.run(['mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none', '-n',
                        'SV08 one-shot recovery selector', '-d', 'recovery.cmd', 'recovery.scr'],
                       cwd=changed, check=True, capture_output=True, timeout=30)
        for name in manifest['files_sha256']:
            manifest['files_sha256'][name] = digest((changed / name).read_bytes())
        (changed / 'build.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'Actual initramfs.*trusted-writer'):
            verify_signed_stage_bundle(verify_artifact(changed), bundle, key, now=1500)


class InitramfsParserTests(unittest.TestCase):
    @staticmethod
    def entry(name, payload=b'', mode=stat.S_IFREG | 0o644, *, advertised_size=None):
        name = name.encode() + b'\0'
        values = [1, mode, 0, 0, 1, 0,
                  len(payload) if advertised_size is None else advertised_size, 0, 0, 0, 0, len(name), 0]
        result = b'070701' + ''.join(f'{value:08x}' for value in values).encode() + name
        return result + b'\0' * (-len(result) % 4) + payload + b'\0' * (-len(payload) % 4)

    def test_bounded_archive_refuses_malformed_entries(self):
        trailer = self.entry('TRAILER!!!', mode=0)
        valid = self.entry('job.json', b'signed') + trailer
        cases = {
            'truncated': valid[:100],
            'duplicate': self.entry('job.json', b'signed') * 2 + trailer,
            'absolute': self.entry('/job.json', b'signed') + trailer,
            'traversal': self.entry('../job.json', b'signed') + trailer,
            'symlink': self.entry('job.json', b'signed', stat.S_IFLNK | 0o777) + trailer,
            'missing': trailer,
            'member-overflow': self.entry('job.json', advertised_size=2**31) + trailer,
            'unsupported-magic': b'070702' + valid[6:],
            'trailing-data': valid + b'NONZERO',
        }
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            archive = Path(temporary) / 'archive.gz'
            archive.write_bytes(gzip.compress(valid, mtime=0))
            self.assertEqual(stager.verify_initramfs_members(archive, {'job.json': b'signed'}),
                             hashlib.sha256(valid).hexdigest())
            for name, raw in cases.items():
                with self.subTest(name=name):
                    archive.write_bytes(gzip.compress(raw, mtime=0))
                    with self.assertRaises(ValueError):
                        stager.verify_initramfs_members(archive, {'job.json': b'signed'})
            archive.write_bytes(gzip.compress(valid, mtime=0))
            with (mock.patch.object(stager, 'ARCHIVE_MAX_BYTES', len(valid) - 1),
                  self.assertRaisesRegex(ValueError, 'budget')):
                stager.verify_initramfs_members(archive, {'job.json': b'signed'})
            bad_crc = bytearray(archive.read_bytes())
            bad_crc[-8] ^= 1
            archive.write_bytes(bad_crc)
            with self.assertRaises(gzip.BadGzipFile):
                stager.verify_initramfs_members(archive, {'job.json': b'signed'})


if __name__ == '__main__':
    unittest.main()
