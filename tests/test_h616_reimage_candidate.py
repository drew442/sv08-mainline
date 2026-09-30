"""Offline tests for the inert H616 commissioning candidate and shared adapter."""
import copy
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts.build_h616_reimage_candidate import (
    REPO, WRITER, IMAGE_BYTES, SECTORS, TARGET_BYTES, V5_IMAGE_SHA256,
    V5_IMAGE_DISK_GUID, V5_IMAGE_PARTITIONS, build, digest,
    expected_image_layout, policy_fields, verify_signed_job,
)
from scripts.ed25519_build import ED25519_SOURCES, raw_public_key
from tests.host_qemu_sd_network_emmc_write import (
    DISK_GUID, IMAGE_SHA256, expected_records, synthetic_mmc_fixture,
)
from tests import host_qemu_sd_network_emmc_write as harness
from tests.sv08_emmc_job import canonical_json, receipt_message, sign_receipt

KEYS = REPO / 'tests/fixtures/sd-network-root/synthetic-keys'
RECEIPT_KEYS = REPO / 'tests/fixtures/sd-network-root/receipt-test-keys'


def compile_writer(output, flags):
    subprocess.run([
        'cc', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
        f'-I{REPO / "upstream/monocypher/src"}',
        f'-I{REPO / "upstream/monocypher/src/optional"}',
        *flags, '-o', str(output), str(WRITER),
        *(str(path) for path in ED25519_SOURCES)],
        check=True, capture_output=True)


def synthetic_policy():
    return {
        'format': 'sv08-h616-commissioning-policy-v1',
        'cid': '00000000000000000000000000000001',
        'controller': '4022000.mmc', 'card_type': 'MMC',
        'sectors': SECTORS, 'dev_t': '8:0',
        'target_device': '/dev/mmcblk0',
        'board_compatible': 'test,synthetic-h616',
        'claim_server': '10.0.2.2', 'image_bytes': IMAGE_BYTES,
        'image_sha256': IMAGE_SHA256,
        'image_layout': {'disk_guid': DISK_GUID, 'image_bytes': IMAGE_BYTES,
                         'backup_gpt_at_image_end': True,
                         'partitions': expected_records()},
    }


def synthetic_job(policy):
    return {
        'format': 'sv08-h616-signed-reimage-v1',
        'job_id': 'h616-synthetic-test-001',
        'issued_unix': 1000, 'expires_unix': 2000,
        'source': {'bytes': IMAGE_BYTES, 'sha256': IMAGE_SHA256, 'mode': 'read-only-nfs'},
        'target_policy_sha256': digest(canonical_json(policy)),
        'image': {'bytes': IMAGE_BYTES, 'sha256': IMAGE_SHA256,
                  'layout': policy['image_layout']},
    }


def private_write(path, data):
    path.write_bytes(data)
    path.chmod(0o600)
    return path


def signed_inputs(root):
    policy = synthetic_policy()
    job = synthetic_job(policy)
    raw = canonical_json(job)
    files = {
        'policy': private_write(root / 'policy.json', canonical_json(policy)),
        'key': private_write(root / 'verifier.pem', (KEYS / 'test-verification-key.pem').read_bytes()),
        'job': private_write(root / 'job.json', raw),
        'signature': root / 'job.sig',
    }
    private_key = private_write(root / 'signer.pem', (KEYS / 'test-signing-key.pem').read_bytes())
    subprocess.run(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', str(private_key),
                    '-in', str(files['job']), '-out', str(files['signature'])],
                   check=True, capture_output=True)
    files['signature'].chmod(0o600)
    return files, policy, job


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (REPO / 'local').mkdir(exist_ok=True)

    def test_reviewed_v5_source_may_use_only_a_synthetic_qemu_target(self):
        from scripts.build_h616_reimage_candidate import V5_IMAGE_SHA256, policy_fields
        from tests.host_qemu_sd_network_emmc_write import h616_synthetic_policy
        candidate = h616_synthetic_policy(V5_IMAGE_SHA256)
        self.assertEqual(policy_fields(candidate), candidate)
        self.assertEqual(candidate['image_layout']['partitions'][4]['name'], 'recovery')
        candidate['image_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Untrusted or incomplete'):
            policy_fields(candidate)

    def test_recovery_handoff_requires_trusted_initramfs_and_pins_transfer(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            work = Path(temporary)
            files, _, _ = signed_inputs(work)
            with self.assertRaisesRegex(ValueError, 'trusted initramfs'):
                build(work / 'rejected', *files.values(), now=1500,
                      synthetic_test=True, recovery_handoff=True)
            manifest = build(work / 'handoff', *files.values(), now=1500,
                             synthetic_test=True, trusted_initramfs=True,
                             source_server='10.0.2.2',
                             source_export='/srv/sv08-sd-nfs',
                             recovery_handoff=True)
            helper = WRITER.parent / 'env_last_transfer.h'
            self.assertTrue(manifest['recovery_handoff'])
            self.assertEqual(manifest['env_last_transfer_sha256'], digest(helper.read_bytes()))
            self.assertGreater((work / 'handoff/sd-network-init').stat().st_size, 0)

    def test_signed_claim_receipt_and_strict_http_framing(self):
        job_id = 'h616-synthetic-test-001'
        descriptor_hash = '12' * 32
        challenge = '34' * 32
        public_key = raw_public_key((RECEIPT_KEYS / 'test-verification-key.pem').read_bytes())
        flags = [
            '-DSV08_CLAIM_RECEIPT_SELFTEST=1',
            f'-DSV08_JOB_ID="{job_id}"',
            f'-DSV08_RECEIPT_PUBLIC_KEY_HEX="{public_key.hex()}"',
        ]
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            root = Path(temporary)
            binary = root / 'receipt-test'
            compile_writer(binary, flags)

            def check(response, expected='admitted'):
                path = root / 'response.bin'
                path.write_bytes(response)
                result = subprocess.check_output([
                    str(binary), str(path), descriptor_hash, challenge], text=True).strip()
                self.assertEqual(result, expected, response[:100])

            header = (b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n'
                      b'Content-Length: 129\r\nConnection: close\r\n\r\n')
            message = receipt_message(job_id, descriptor_hash, challenge)
            signature = sign_receipt(message, RECEIPT_KEYS / 'test-signing-key.pem')
            response = header + signature.hex().encode() + b'\n'
            check(response)

            wrong_key = sign_receipt(message, RECEIPT_KEYS / 'other-signing-key.pem')
            stale = sign_receipt(receipt_message(job_id, descriptor_hash, '56' * 32),
                                 RECEIPT_KEYS / 'test-signing-key.pem')
            replay = sign_receipt(receipt_message(job_id, descriptor_hash, '00' * 32),
                                  RECEIPT_KEYS / 'test-signing-key.pem')
            wrong_job = sign_receipt(receipt_message(job_id + '-other', descriptor_hash, challenge),
                                     RECEIPT_KEYS / 'test-signing-key.pem')
            wrong_descriptor = sign_receipt(receipt_message(job_id, '78' * 32, challenge),
                                            RECEIPT_KEYS / 'test-signing-key.pem')
            altered = bytes([signature[0] ^ 1]) + signature[1:]
            refusals = {
                'forged 200': header + bytes(64),
                'wrong key': header + wrong_key.hex().encode() + b'\n',
                'stale challenge': header + stale.hex().encode() + b'\n',
                'replayed receipt': header + replay.hex().encode() + b'\n',
                'wrong job': header + wrong_job.hex().encode() + b'\n',
                'wrong descriptor': header + wrong_descriptor.hex().encode() + b'\n',
                'altered signature': header + altered.hex().encode() + b'\n',
                'truncated signature': header + signature.hex().encode()[:-2] + b'\n',
                'extra body byte': response + b'X',
                'extra newline': response + b'\n',
                'uppercase signature': header + signature.hex().upper().encode() + b'\n',
                'wrong status': response.replace(b'200 OK', b'201 OK', 1),
                'wrong length': response.replace(b'Length: 129', b'Length: 128', 1),
                'duplicate length': response.replace(b'Connection:', b'Content-Length: 129\r\nConnection:', 1),
                'transfer encoding': response.replace(b'Connection:', b'Transfer-Encoding: chunked\r\nConnection:', 1),
                'unexpected header': response.replace(b'Connection:', b'Server: forged\r\nConnection:', 1),
                'changed content type': response.replace(b'text/plain', b'application/octet-stream', 1),
            }
            for name, invalid in refusals.items():
                with self.subTest(case=name):
                    check(invalid, 'refused')

    def test_challenges_are_fresh_and_randomness_failure_refuses(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            root = Path(temporary)
            random_binary = root / 'random-challenge'
            compile_writer(random_binary, ['-DSV08_CHALLENGE_SELFTEST=1'])
            values = [subprocess.check_output([str(random_binary)], text=True).strip()
                      for _ in range(2)]
            for value in values:
                self.assertRegex(value, r'^[0-9a-f]{64}$')
            self.assertNotEqual(values[0], values[1])

            no_random_binary = root / 'no-random-challenge'
            compile_writer(no_random_binary, [
                '-DSV08_CHALLENGE_SELFTEST=1', '-DSV08_TEST_NO_RANDOM=1'])
            self.assertEqual(subprocess.check_output(
                [str(no_random_binary)], text=True).strip(), 'refused')

    def test_physical_h616_branch_has_strict_static_compile_only(self):
        receipt_public_key = raw_public_key(
            (RECEIPT_KEYS / 'test-verification-key.pem').read_bytes()).hex()
        flags = [
            '-DSV08_H616_COMMISSIONING=1',
            '-DSV08_H616_EXPECTED_CID="00000000000000000000000000000000"',
            '-DSV08_H616_EXPECTED_DEV_T="179:0"',
            '-DSV08_H616_BOARD_COMPATIBLE="test,compile-only"',
            '-DSV08_H616_CLAIM_SERVER="192.0.2.1"',
            f'-DSV08_TARGET_BYTES={TARGET_BYTES}ULL',
            '-DSV08_JOB_ID="compile-only"',
            f'-DSV08_JOB_DESCRIPTOR_SHA256="{"0" * 64}"',
            f'-DSV08_TARGET_POLICY_SHA256="{"0" * 64}"',
            '-DSV08_JOB_NOT_BEFORE=1LL', '-DSV08_JOB_EXPIRES=2LL',
            f'-DSV08_SOURCE_SHA256="{"0" * 64}"',
            f'-DSV08_JOB_SIGNATURE_SHA256="{"0" * 64}"',
            f'-DSV08_RECEIPT_PUBLIC_KEY_HEX="{receipt_public_key}"',
            '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
        ]
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            output = Path(temporary) / 'compile-only-writer'
            subprocess.run([
                'aarch64-linux-gnu-gcc', '-static', '-Os', '-D_FORTIFY_SOURCE=2',
                '-Wall', '-Wextra', '-Werror',
                f'-I{REPO / "upstream/monocypher/src"}',
                f'-I{REPO / "upstream/monocypher/src/optional"}',
                *flags, '-o', str(output), str(WRITER),
                *(str(path) for path in ED25519_SOURCES)],
                check=True, capture_output=True, timeout=120)
            self.assertGreater(output.stat().st_size, 0)
            self.assertFalse(output.read_bytes().find(b'test,compile-only') < 0)

    def test_private_signed_candidate_is_explicit_nonbootable_and_reproducible(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            work = Path(temporary)
            files, policy, job = signed_inputs(work)
            first = build(work / 'first', *files.values(), now=1500, synthetic_test=True)
            second = build(work / 'second', *files.values(), now=1500, synthetic_test=True)
            self.assertEqual(first, second)
            self.assertEqual((work / 'first/sd-network-init').read_bytes(),
                             (work / 'second/sd-network-init').read_bytes())
            self.assertFalse(first['bootable_sd_image'])
            self.assertFalse(first['physical_target_validated'])
            self.assertFalse(first['claim_trigger_provisioned'])
            self.assertEqual(first['binary_bytes'], (work / 'first/sd-network-init').stat().st_size)
            self.assertEqual(first['ed25519']['implementation'], 'Monocypher')
            self.assertIn('upstream/monocypher/LICENCE.md', first['ed25519']['source_sha256'])
            self.assertEqual(first['receipt_verifier_sha256'],
                             digest((RECEIPT_KEYS / 'test-verification-key.pem').read_bytes()))
            self.assertNotIn('boot.scr', [item.name for item in (work / 'first').iterdir()])
            self.assertEqual(first['policy_sha256'], digest(canonical_json(policy)))
            self.assertEqual(verify_signed_job(canonical_json(job), files['signature'].read_bytes(),
                                               files['key'].read_bytes(), policy, now=1500), job)

    def test_missing_changed_or_ambiguous_private_inputs_refuse_before_output(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            work = Path(temporary)
            files, policy, job = signed_inputs(work)
            bad = copy.deepcopy(policy)
            for key, value in [('cid', '0' * 32), ('controller', '4021000.mmc'),
                               ('card_type', 'SD'), ('sectors', SECTORS + 1),
                               ('dev_t', '0:0'), ('target_device', '/dev/sda'),
                               ('image_sha256', '0' * 64)]:
                changed = copy.deepcopy(bad if key == 'cid' else policy)
                changed[key] = value
                if key == 'cid':
                    # A different but canonical CID is valid policy; the signed
                    # job must still refuse its changed policy hash.
                    self.assertEqual(policy_fields(changed), changed)
                else:
                    with self.assertRaises(ValueError):
                        policy_fields(changed)
            for mutation in ('missing-key', 'changed-signature', 'stale', 'wrong-policy',
                             'public-mode', 'read-only-mode'):
                with self.subTest(mutation=mutation):
                    inputs = dict(files)
                    if mutation == 'missing-key':
                        inputs['key'] = work / 'missing.pem'
                    elif mutation == 'changed-signature':
                        data = bytearray(files['signature'].read_bytes())
                        data[0] ^= 1
                        inputs['signature'] = private_write(work / 'bad.sig', bytes(data))
                    elif mutation == 'wrong-policy':
                        changed = dict(policy, cid='0' * 32)
                        inputs['policy'] = private_write(work / 'other-policy.json', canonical_json(changed))
                    elif mutation == 'public-mode':
                        inputs['key'] = private_write(work / 'public.pem', files['key'].read_bytes())
                        inputs['key'].chmod(0o644)
                    elif mutation == 'read-only-mode':
                        inputs['key'] = private_write(work / 'readonly.pem', files['key'].read_bytes())
                        inputs['key'].chmod(0o400)
                    with self.assertRaises(ValueError):
                        build(work / mutation, *inputs.values(), now=2000 if mutation == 'stale' else 1500,
                              synthetic_test=True)
                    self.assertFalse((work / mutation).exists())
            with self.assertRaises(ValueError):
                build(work / 'physical', *files.values(), now=1500)
            outside = work / 'outside'
            outside.mkdir()
            link = REPO / 'local' / 'h616-output-link-test'
            link.symlink_to(outside, target_is_directory=True)
            try:
                with self.assertRaises(ValueError):
                    build(link / 'output', *files.values(), now=1500,
                          synthetic_test=True)
                self.assertFalse((outside / 'output').exists())
            finally:
                link.unlink()

    def test_wrong_but_internally_consistent_policy_and_job_map_refuse(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            work = Path(temporary)
            files, policy, job = signed_inputs(work)
            edits = [
                ('disk_guid', lambda p: p['image_layout'].__setitem__(
                    'disk_guid', '4aae17d2-09b3-47ab-8e35-8e91e63cf2b0')),
                ('backup_gpt', lambda p: p['image_layout'].__setitem__(
                    'backup_gpt_at_image_end', False)),
                ('image_extent', lambda p: p['image_layout'].__setitem__(
                    'image_bytes', IMAGE_BYTES - 512)),
                ('partuuid', lambda p: p['image_layout']['partitions'][0].__setitem__(
                    'partuuid', '00000000-0000-4000-8000-000000000001')),
                ('name', lambda p: p['image_layout']['partitions'][0].__setitem__(
                    'name', 'wrong')),
                ('offset', lambda p: p['image_layout']['partitions'][0].__setitem__(
                    'offset_bytes', 0)),
                ('size', lambda p: p['image_layout']['partitions'][0].__setitem__(
                    'size_bytes', 512)),
            ]
            for name, change in edits:
                with self.subTest(name=name):
                    altered = copy.deepcopy(policy)
                    change(altered)
                    altered_job = copy.deepcopy(job)
                    altered_job['target_policy_sha256'] = digest(canonical_json(altered))
                    altered_job['image']['layout'] = altered['image_layout']
                    policy_file = private_write(work / f'{name}-policy.json', canonical_json(altered))
                    job_file = private_write(work / f'{name}-job.json', canonical_json(altered_job))
                    sig_file = work / f'{name}-job.sig'
                    subprocess.run(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey',
                                    str(work / 'signer.pem'), '-in', str(job_file),
                                    '-out', str(sig_file)], check=True, capture_output=True)
                    sig_file.chmod(0o600)
                    with self.assertRaises(ValueError):
                        build(work / name, policy_file, files['key'], job_file,
                              sig_file, now=1500, synthetic_test=True)
                    self.assertFalse((work / name).exists())

    def test_physical_layout_has_no_unreviewed_disk_guid_pin(self):
        physical = copy.deepcopy(synthetic_policy())
        physical['board_compatible'] = 'sovol,sv08'
        with self.assertRaises(ValueError):
            policy_fields(physical)

    def test_v5_physical_map_matches_public_audit_and_rejects_drift(self):
        audit = json.loads((REPO / 'docs/hardware/host-board-image-20260925-v5-gpt-audit-20260927.json').read_text())
        audited = audit['gpt']
        self.assertEqual(audit['artifact']['raw_sha256'], V5_IMAGE_SHA256)
        self.assertEqual(audited['disk_guid'], V5_IMAGE_DISK_GUID)
        self.assertEqual(tuple((item['name'], item['partuuid'], item['offset_bytes'], item['size_bytes'])
                               for item in audited['partitions']), V5_IMAGE_PARTITIONS)

        policy = copy.deepcopy(synthetic_policy())
        policy.update(board_compatible='sovol,sv08', image_sha256=V5_IMAGE_SHA256,
                      image_layout=expected_image_layout(False, V5_IMAGE_SHA256))
        self.assertEqual(policy_fields(policy), policy)
        expected = policy['image_layout']
        mutations = [
            ('hash', lambda p: p.__setitem__('image_sha256', '0' * 64)),
            ('disk-guid', lambda p: p['image_layout'].__setitem__('disk_guid', '4aae17d2-09b3-47ab-8e35-8e91e63cf2b0')),
            ('partition-guid', lambda p: p['image_layout']['partitions'][0].__setitem__('partuuid', '00000000-0000-4000-8000-000000000001')),
            ('offset', lambda p: p['image_layout']['partitions'][0].__setitem__('offset_bytes', 0)),
            ('size', lambda p: p['image_layout']['partitions'][0].__setitem__('size_bytes', 512)),
            ('order', lambda p: p['image_layout']['partitions'].reverse()),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                changed = copy.deepcopy(policy)
                mutate(changed)
                with self.assertRaises(ValueError):
                    policy_fields(changed)
        self.assertEqual(policy['image_layout'], expected)

    def test_abrupt_fault_build_is_synthetic_only(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            work = Path(temporary)
            files, _, _ = signed_inputs(work)
            manifest = build(work / 'abrupt', *files.values(), now=1500,
                             synthetic_test=True, fault='abrupt-after-write')
            self.assertTrue(manifest['synthetic_test'])
            self.assertFalse(manifest['bootable_sd_image'])
            with self.assertRaises(ValueError):
                build(work / 'physical-fault', *files.values(), now=1500,
                      fault='abrupt-after-write')
            self.assertFalse((work / 'physical-fault').exists())

    def test_recovery_env_last_faults_are_synthetic_only(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            work = Path(temporary)
            files, _, _ = signed_inputs(work)
            for fault in ('after-bulk', 'after-first-env'):
                with self.subTest(fault=fault):
                    manifest = build(work / fault, *files.values(), now=1500,
                                     synthetic_test=True, fault=fault,
                                     trusted_initramfs=True,
                                     source_server='10.0.2.2',
                                     source_export='/srv/sv08-sd-nfs',
                                     recovery_handoff=True)
                    self.assertTrue(manifest['synthetic_test'])
                    self.assertFalse(manifest['bootable_sd_image'])
                    with self.assertRaises(ValueError):
                        build(work / (fault + '-physical'), *files.values(),
                              now=1500, fault=fault,
                              trusted_initramfs=True,
                              source_server='10.0.2.2',
                              source_export='/srv/sv08-sd-nfs',
                              recovery_handoff=True)

    def test_guest_case_markers_distinguish_interruption_from_refusal(self):
        prefix = 'SV08_H616_COMMISSIONING_'
        self.assertEqual(harness.guest_case_marker(prefix, fault='abrupt-after-write'),
                         (prefix + 'PROGRESS_FIRST_MIB_WRITTEN', 'progress'))
        self.assertEqual(harness.guest_case_marker(prefix, fault='partial-write'),
                         (prefix + 'INJECTED_PARTIAL_WRITE', 'terminal'))
        for source_fault, status in [('missing', 'REFUSED_SOURCE'),
                                     ('wrong-size', 'REFUSED_SOURCE'),
                                     ('wrong-hash', 'REFUSED_SOURCE_HASH')]:
            self.assertEqual(harness.guest_case_marker(prefix, source_fault=source_fault),
                             (prefix + status, 'terminal'))
        self.assertEqual(harness.guest_case_marker(prefix, lost_claim_ack=True),
                         (prefix + 'REFUSED_OR_UNCERTAIN_CLAIM', 'terminal'))
        self.assertEqual(harness.guest_case_marker(prefix, claim_fault='forged-200'),
                         (prefix + 'REFUSED_OR_UNCERTAIN_CLAIM', 'terminal'))

    def test_h616_identity_follows_single_inventory_and_dev_number(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            root = Path(temporary)
            synthetic_mmc_fixture(root, commissioning=True)
            base = root / 'synthetic-mmc'
            dev_file = base / 'mmc0/mmc0:0001/block/mmcblk0/dev'
            binary = root / 'identity-test'
            flags = ['-DSV08_H616_COMMISSIONING=1', '-DSV08_H616_SYNTHETIC_TEST=1',
                     '-DSV08_H616_IDENTITY_SELFTEST=1',
                     '-DSV08_H616_EXPECTED_CID="00000000000000000000000000000001"',
                     '-DSV08_H616_EXPECTED_DEV_T="8:0"',
                     '-DSV08_H616_BOARD_COMPATIBLE="test,synthetic-h616"',
                     '-DSV08_H616_CLAIM_SERVER="10.0.2.2"']
            compile_writer(binary, flags)
            def check():
                return subprocess.check_output([str(binary), str(base), str(dev_file)], text=True).strip()
            self.assertEqual(check(), 'admitted 8:0')
            card = base / 'mmc0/mmc0:0001'
            for path, content in [(card / 'cid', '0' * 32 + '\n'),
                                  (card / 'type', 'SD\n'),
                                  (card / 'block/mmcblk0/size', str(SECTORS - 1) + '\n'),
                                  (dev_file, '8:1\n')]:
                original = path.read_bytes()
                path.write_text(content)
                self.assertEqual(check(), 'refused')
                path.write_bytes(original)
            controller = base / 'controller'
            controller.unlink()
            self.assertEqual(check(), 'refused')
            controller.symlink_to('mmc0')
            card_device = base / 'card-device'
            card_device.unlink()
            (base / 'mmc0-other/mmc0:0001').mkdir(parents=True)
            card_device.symlink_to('mmc0-other/mmc0:0001')
            self.assertEqual(check(), 'refused')
            card_device.unlink()
            card_device.symlink_to('mmc0/mmc0:0001')
            other = base / 'mmc1/mmc1:0001/block/mmcblk1'
            other.mkdir(parents=True)
            (other.parent.parent / 'type').write_text('MMC\n')
            (other.parent.parent / 'cid').write_text('0' * 32 + '\n')
            (other / 'size').write_text(str(SECTORS) + '\n')
            self.assertEqual(check(), 'refused')

    def test_commissioning_fixture_size_and_each_identity_fault(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            root = Path(temporary)
            binary = root / 'identity-test'
            flags = ['-DSV08_H616_COMMISSIONING=1', '-DSV08_H616_SYNTHETIC_TEST=1',
                     '-DSV08_H616_IDENTITY_SELFTEST=1',
                     '-DSV08_H616_EXPECTED_CID="00000000000000000000000000000001"',
                     '-DSV08_H616_EXPECTED_DEV_T="8:0"',
                     '-DSV08_H616_BOARD_COMPATIBLE="test,synthetic-h616"',
                     '-DSV08_H616_CLAIM_SERVER="10.0.2.2"']
            compile_writer(binary, flags)
            for fault in (None, 'wrong-cid', 'wrong-dev', 'ambiguous',
                          'wrong-controller', 'missing-controller', 'wrong-type', 'wrong-capacity'):
                with self.subTest(fault=fault):
                    case = root / (fault or 'valid')
                    case.mkdir()
                    synthetic_mmc_fixture(case, fault, commissioning=True)
                    base = case / 'synthetic-mmc'
                    block = base / 'mmc0/mmc0:0001/block/mmcblk0'
                    self.assertEqual((block / 'size').read_text(),
                                     f'{SECTORS - (fault == "wrong-capacity")}\n')
                    result = subprocess.check_output([
                        str(binary), str(base), str(block / 'dev')], text=True).strip()
                    self.assertEqual(result, 'admitted 8:0' if fault is None else 'refused')
                    if fault == 'wrong-cid':
                        self.assertNotEqual((block.parent.parent / 'cid').read_text().strip(),
                                            synthetic_policy()['cid'])
                    elif fault == 'wrong-dev':
                        self.assertEqual((block / 'dev').read_text(), '8:1\n')
                    elif fault == 'ambiguous':
                        self.assertEqual((base / 'mmc1/mmc1:0001/block/mmcblk1/size').read_text(),
                                         f'{SECTORS}\n')

    def test_commissioning_parameter_requires_exact_token(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            binary = Path(temporary) / 'token-test'
            flags = ['-DSV08_H616_COMMISSIONING=1', '-DSV08_H616_SYNTHETIC_TEST=1',
                     '-DSV08_CMDLINE_SELFTEST=1',
                     '-DSV08_H616_EXPECTED_CID="00000000000000000000000000000001"',
                     '-DSV08_H616_EXPECTED_DEV_T="8:0"',
                     '-DSV08_H616_BOARD_COMPATIBLE="test,synthetic-h616"',
                     '-DSV08_H616_CLAIM_SERVER="10.0.2.2"']
            compile_writer(binary, flags)
            for cmd, expected in [('root=/dev/nfs sv08.h616_commissioning=1 ro', 'admitted'),
                                  ('xsv08.h616_commissioning=1 ro', 'refused'),
                                  ('sv08.h616_commissioning=10', 'refused'),
                                  ('sv08.h616_commissioning=1suffix', 'refused')]:
                self.assertEqual(subprocess.check_output([str(binary), cmd], text=True).strip(), expected)

    def test_commissioning_success_rechecks_and_reports_its_target_size(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            work = Path(temporary) / 'run'
            with (mock.patch.object(harness, 'verify_inputs', return_value='root=/dev/nfs ro sv08.qemu_reimage=1'),
                  mock.patch.object(harness, 'create_synthetic_source',
                                    side_effect=lambda path: (path.write_bytes(b'synthetic'), IMAGE_SHA256)[1]),
                  mock.patch.object(harness, 'validate_source'),
                  mock.patch.object(harness, 'TARGET_BYTES', 1024),
                  mock.patch.object(harness, 'H616_TARGET_BYTES', 1536),
                  mock.patch.object(harness, 'execute', return_value={'claim': {'status': 'consumed-before-write'}}),
                  mock.patch.object(harness, 'digest', return_value=IMAGE_SHA256),
                  mock.patch.object(harness, 'inspect_gpt', return_value={
                      'partition_records': expected_records(), 'disk_guid': DISK_GUID}),
                  mock.patch('sys.argv', ['writer', '--work', str(work), '--sd-work',
                                          str(Path(temporary) / 'sd'), '--package-root',
                                          str(Path(temporary) / 'packages'),
                                          '--commissioning', '--execute']),
                  redirect_stdout(io.StringIO())):
                harness.main()
            receipt = json.loads((work / 'result.json').read_text())
            self.assertEqual(receipt['target_bytes'], 1536)
            self.assertEqual((work / 'target.img').stat().st_size, 1536)
            self.assertFalse((work / 'FAILED').exists())

    def test_default_diagnostic_is_separate_and_claim_precedes_target_open(self):
        default = (REPO / 'scripts/build_sd_network_image.py').read_text()
        self.assertNotIn('emmc_image_writer.c', default)
        self.assertNotIn('build_h616_reimage_candidate', default)
        source = WRITER.read_text()
        start = source.index('int main(void) {', source.index('#else\nint main(void)'))
        body = source[start:]
        self.assertLess(body.index('SV08_MODE_PARAMETER'), body.index('claim_once(cmd,descriptor_hash)'))
        self.assertLess(body.index('claim_once(cmd,descriptor_hash)'),
                        body.index('out=open(target,O_RDWR'))
        self.assertLess(body.index('admitted_mmc_identity(&admitted_dev)'),
                        body.index('out=open(target,O_RDWR'))
        self.assertLess(body.index('sha_final(&hash,actual)'), body.index('out=open(target,O_RDWR'))
        self.assertLess(body.index('admitted_mmc_identity(&confirmed_dev)'),
                        body.index('exact_write(out,n)'))
        self.assertEqual(body.count('out=open(target,'), 1)
        # Finalizer behavior is executed in ManagedFinalizerTests for both modes.



def compile_finalizer_harness(output, *, handoff, capture=True,
                              compiler='cc', status=None, static=False):
    """Compile the actual production finish, without production test hooks.

    capture=False/status='PASS' builds a tiny ARM64 PID1 finalizer for QMP
    reset/shutdown testing; coordinator supplies disposable VM resources.
    """
    wrapper = output.with_suffix('.c')
    prefix = ''
    if capture:
        prefix = '#define sync captured_sync\n#define reboot captured_reboot\n#define pause captured_pause\n'
    suffix = '''
#undef main
'''
    if capture:
        suffix += '''
void captured_sync(void) { puts("SYSCALL sync"); }
int captured_reboot(int operation) {
  printf("SYSCALL reboot %s\\n",operation==RB_AUTOBOOT?"AUTOBOOT":
         operation==RB_POWER_OFF?"POWER_OFF":"OTHER");
  errno=EIO;return -1;
}
int captured_pause(void) { puts("SYSCALL pause");fflush(stdout);_exit(0); }
'''
    if status is None:
        suffix += 'int main(int argc,char **argv) { if(argc!=2)return 2;finish(argv[1]);return 3; }\n'
    else:
        if status not in ('PASS','FAILED_FINAL_ENV','CLAIM_ONLY_PASS'):
            raise ValueError('Unsupported fixed VM finalizer status')
        suffix += f'int main(void) {{ finish("{status}");return 3; }}\n'
    wrapper.write_text(prefix+'#define main retained_writer_main\n#include "'+str(WRITER)+'"\n'+suffix)
    flags = ['-DSV08_H616_COMMISSIONING=1','-DSV08_SHA_SELFTEST=1',
             '-DSV08_H616_EXPECTED_CID="00000000000000000000000000000001"',
             '-DSV08_H616_EXPECTED_DEV_T="8:0"',
             '-DSV08_H616_BOARD_COMPATIBLE="test,synthetic-h616"',
             '-DSV08_H616_CLAIM_SERVER="127.0.0.1"']
    if handoff: flags.append('-DSV08_H616_RECOVERY_HANDOFF=1')
    if static: flags.append('-static')
    subprocess.run([compiler,'-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable',
                    f'-I{REPO / "upstream/monocypher/src"}',
                    f'-I{REPO / "upstream/monocypher/src/optional"}',
                    *flags,'-o',str(output),str(wrapper),
                    *(str(p) for p in ED25519_SOURCES)],check=True,capture_output=True)


class ManagedFinalizerTests(unittest.TestCase):
    def test_actual_finalizer_exact_pass_only_and_returned_reboot_stops(self):
        statuses = ('PASS','CLAIM_ONLY_PASS','PASS ','PASSx','REFUSED_TARGET_ID',
                    'REFUSED_OR_UNCERTAIN_CLAIM','INJECTED_PARTIAL_WRITE',
                    'FAILED_READBACK_HASH','FAILED_FINAL_ENV','INJECTED_AFTER_FIRST_ENV')
        with tempfile.TemporaryDirectory() as work:
            for handoff in (False,True):
                exe = Path(work)/('handoff' if handoff else 'normal')
                compile_finalizer_harness(exe,handoff=handoff)
                for status in statuses:
                    with self.subTest(handoff=handoff,status=status):
                        result=subprocess.run([str(exe),status],capture_output=True,text=True,check=True,timeout=5)
                        expected='AUTOBOOT' if handoff and status=='PASS' else 'POWER_OFF'
                        calls=[line for line in result.stdout.splitlines() if line.startswith('SYSCALL ')]
                        self.assertEqual(calls,['SYSCALL sync','SYSCALL reboot '+expected,'SYSCALL pause'])

    def test_actual_arm64_finalizer_compiles_both_operations(self):
        import shutil
        compiler=shutil.which('aarch64-linux-gnu-gcc')
        if not compiler:self.skipTest('ARM64 cross compiler unavailable')
        with tempfile.TemporaryDirectory() as work:
            for status in ('PASS','FAILED_FINAL_ENV'):
                exe=Path(work)/status
                compile_finalizer_harness(exe,handoff=True,capture=False,compiler=compiler,status=status,static=True)
                self.assertIn(b'\x7fELF',exe.read_bytes()[:4])


class PhysicalPreflightTests(unittest.TestCase):
    FLAGS = ['-DSV08_H616_COMMISSIONING=1', '-DSV08_H616_TRUSTED_INITRAMFS=1',
             '-DSV08_H616_RECOVERY_HANDOFF=1', '-DSV08_H616_PREFLIGHT_ONLY=1',
             '-DSV08_H616_EXPECTED_CID="0123456789abcdef0123456789abcdef"',
             '-DSV08_H616_EXPECTED_DEV_T="179:0"',
             '-DSV08_H616_BOARD_COMPATIBLE="sovol,sv08-h616"',
             '-DSV08_H616_CLAIM_SERVER="192.0.2.1"',
             '-DSV08_IMAGE_NFS_SOURCE="192.0.2.1:/source"',
             '-DSV08_JOB_ID="preflight-job"']

    def compile_case(self, source, extra=()):
        (REPO / 'local').mkdir(exist_ok=True)
        work = tempfile.TemporaryDirectory(dir=REPO / 'local')
        self.addCleanup(work.cleanup)
        wrapper = Path(work.name) / 'case.c'
        binary = Path(work.name) / 'case'
        wrapper.write_text(source)
        result = subprocess.run([
            'cc', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
            '-Wno-unused-variable', '-Wno-unused-parameter',
            '-Wno-misleading-indentation', *self.FLAGS, *extra,
            f'-I{REPO / "upstream/monocypher/src"}',
            f'-I{REPO / "upstream/monocypher/src/optional"}',
            f'-I{WRITER.parent}',
            '-o', str(binary), str(wrapper), *(str(path) for path in ED25519_SOURCES)],
            capture_output=True, text=True)
        return result, binary

    def test_preflight_compile_rejects_test_bypasses(self):
        source = f'#include "{WRITER}"\n'
        for flag in ('-DSV08_H616_SYNTHETIC_TEST=1', '-DSV08_CLAIM_ONLY=1',
                     '-DSV08_TEST_FAULT="before-write"', '-DSV08_SHA_SELFTEST=1',
                     '-USV08_H616_COMMISSIONING', '-USV08_H616_TRUSTED_INITRAMFS',
                     '-USV08_H616_RECOVERY_HANDOFF'):
            with self.subTest(flag=flag):
                result, _ = self.compile_case(source, [flag])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Physical preflight requires', result.stderr)

    def test_actual_preflight_main_has_no_target_transfer_imports(self):
        result, binary = self.compile_case(f'#include "{WRITER}"\n',
                                          ['-ffunction-sections', '-fdata-sections',
                                           '-Wl,--gc-sections'])
        self.assertEqual(result.returncode, 0, result.stderr)
        imports = subprocess.check_output(['nm', '-u', str(binary)], text=True)
        for symbol in ('pwrite', 'write', 'fdatasync'):
            self.assertNotRegex(imports, rf'\b{symbol}(?:@|\s|$)')
        self.assertNotIn(b'READBACK bytes=', binary.read_bytes())

    def test_signed_job_format_is_a_purpose_boundary(self):
        (REPO / 'local').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO / 'local') as temporary:
            root = Path(temporary)
            files, policy, job = signed_inputs(root)
            signature = files['signature'].read_bytes()
            verifier = files['key'].read_bytes()
            raw_write = canonical_json(job)
            self.assertEqual(verify_signed_job(raw_write, signature, verifier,
                                               policy, now=1500)['format'],
                             'sv08-h616-signed-reimage-v1')
            with self.assertRaisesRegex(ValueError, 'Stale job or policy mismatch'):
                verify_signed_job(raw_write, signature, verifier, policy, now=1500,
                                  preflight_only=True)
            job['format'] = 'sv08-h616-signed-preflight-v1'
            raw_preflight = canonical_json(job)
            files['job'].write_bytes(raw_preflight)
            subprocess.run(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey',
                            str(root / 'signer.pem'), '-in', str(files['job']), '-out',
                            str(files['signature'])], check=True, capture_output=True)
            preflight_sig = files['signature'].read_bytes()
            self.assertEqual(verify_signed_job(raw_preflight, preflight_sig, verifier,
                                               policy, now=1500,
                                               preflight_only=True)['format'], job['format'])
            with self.assertRaisesRegex(ValueError, 'Stale job or policy mismatch'):
                verify_signed_job(raw_preflight, preflight_sig, verifier, policy, now=1500)
            with self.assertRaisesRegex(ValueError, 'Preflight requires physical'):
                build(root / 'reject', *files.values(), now=1500,
                      synthetic_test=True, trusted_initramfs=True,
                      recovery_handoff=True, preflight_only=True,
                      source_server='10.0.2.2', source_export='/source')
            with self.assertRaisesRegex(ValueError, 'Stale job or policy mismatch'):
                build(root / 'reject-write', *files.values(), now=1500,
                      synthetic_test=True)

    def test_preflight_finalizer_requires_confirmed_marker(self):
        source = (f'#define reboot captured_reboot\n#define sync captured_sync\n'
                  f'#define pause captured_pause\n#define main writer_main\n'
                  f'#include "{WRITER}"\n#undef main\n'
                  'void captured_sync(void) {}\n'
                  'int captured_reboot(int op) { printf("%s\\n", op==RB_AUTOBOOT?"AUTOBOOT":"POWER_OFF");return -1; }\n'
                  'int captured_pause(void) { fflush(stdout);_exit(0); }\n'
                  'int main(int argc,char **argv) { if(argc!=3)return 2;'
                  'preflight_return_ready=atoi(argv[1]);finish(argv[2]);return 3; }\n')
        result, binary = self.compile_case(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        for confirmed, status, expected in [('0', 'PREFLIGHT_PASS', 'POWER_OFF'),
                                            ('0', 'REFUSED_RECOVERY_MARKER', 'POWER_OFF'),
                                            ('1', 'PREFLIGHT_PASS', 'AUTOBOOT'),
                                            ('1', 'REFUSED_UNSAFE_BOOT_ENV', 'AUTOBOOT')]:
            actual = subprocess.check_output([str(binary), confirmed, status], text=True)
            self.assertEqual(actual.splitlines()[-1], expected)

    def test_marker_consumption_requires_durable_unmount(self):
        # Model only the already independently tested mount/identity boundaries.
        # Keep actual main marker consumption, readiness assignment and finish.
        writer_source = WRITER.read_text()
        before, main_source = writer_source.rsplit('int main(void) {', 1)
        main_source = main_source.replace('trusted_image_mount()', 'captured_trusted_mount()')
        main_source = main_source.replace('board_compatible()', 'captured_board_compatible()')
        main_source = main_source.replace('admitted_mmc_identity(&admitted_dev)',
                                          'captured_identity(&admitted_dev)')
        writer_source = (before + 'static int captured_trusted_mount(void);\n'
                         'static int captured_board_compatible(void);\n'
                         'static int captured_identity(dev_t *number);\n'
                         'int main(void) {' + main_source)
        source = f'''#define open captured_open
#define openat captured_openat
#define read captured_read
#define fstat captured_fstat
#define close captured_close
#define mkdir captured_mkdir
#define mount captured_mount
#define unlinkat captured_unlinkat
#define fsync captured_fsync
#define syncfs captured_syncfs
#define umount2 captured_umount2
#define rmdir captured_rmdir
#define fopen captured_fopen
#define reboot captured_reboot
#define sync captured_sync
#define pause captured_pause
#define main writer_main
{writer_source}
#undef main
#undef fopen
static int fault,marker_sent,sysfs_sent,closed;
static int captured_trusted_mount(void) {{return fault!=6;}}
static int captured_board_compatible(void) {{return 1;}}
static int captured_identity(dev_t *number) {{*number=makedev(179,0);return fault!=7;}}
FILE *captured_fopen(const char *path,const char *mode) {{
 if(strcmp(path,"/proc/cmdline"))return NULL;
 FILE *stream=tmpfile();if(!stream)return NULL;
 fputs("sv08.h616_commissioning=1 sv08.h616_recovery_handoff=1 sv08.h616_preflight=1",stream);
 rewind(stream);return stream;
}}
void captured_sync(void) {{}}
int captured_reboot(int operation) {{
 printf("%s\\n",operation==RB_AUTOBOOT?"AUTOBOOT":"POWER_OFF");return -1;
}}
int captured_pause(void) {{fflush(stdout);_exit(0);}}
int captured_open(const char *path,int flags,...) {{
 if(!strcmp(path,SV08_RECOVERY_PARTITION))return 100;
 if(!strcmp(path,SV08_RECOVERY_PARTITION_SYSFS))return 101;
 if(!strcmp(path,"/sv08-reimage-recovery"))return 102;
 return -1;
}}
int captured_openat(int fd,const char *name,int flags,...) {{
 if(fd==102&&!strcmp(name,"sv08-reimage"))return 103;
 if(fd==103&&!strcmp(name,"armed"))return 104;
 return -1;
}}
ssize_t captured_read(int fd,void *out,size_t length) {{
 if(fd==101){{if(sysfs_sent++)return 0;memcpy(out,"179:5\\n",6);return 6;}}
 if(fd==104){{if(marker_sent++)return 0;
  const char marker[]="SV08-REIMAGE-ONCE\\n";
  if(length<sizeof(marker)-1)return -1;
  memcpy(out,marker,sizeof(marker)-1);return sizeof(marker)-1;}}
 return -1;
}}
int captured_fstat(int fd,struct stat *st) {{
 memset(st,0,sizeof(*st));
 if(fd==100){{st->st_mode=S_IFBLK;st->st_rdev=makedev(179,5);return 0;}}
 if(fd==104){{st->st_mode=S_IFREG;st->st_nlink=1;
             st->st_size=sizeof("SV08-REIMAGE-ONCE\\n")-1;return 0;}}
 return -1;
}}
int captured_close(int fd) {{closed++;return 0;}}
int captured_mkdir(const char *path,mode_t mode) {{return 0;}}
int captured_mount(const char *source,const char *target,const char *type,unsigned long flags,const void *data) {{return 0;}}
int captured_unlinkat(int fd,const char *name,int flags) {{return fault==1?-1:0;}}
int captured_fsync(int fd) {{return fault==2?-1:0;}}
int captured_syncfs(int fd) {{return fault==3?-1:0;}}
int captured_umount2(const char *path,int flags) {{return fault==4?-1:0;}}
int captured_rmdir(const char *path) {{return fault==5?-1:0;}}
int main(int argc,char **argv) {{if(argc!=2)return 2;fault=atoi(argv[1]);
 return writer_main();}}
'''
        result, binary = self.compile_case(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        for fault in range(8):
            with self.subTest(fault=fault):
                output = subprocess.check_output([str(binary), str(fault)], text=True).strip()
                self.assertEqual(output.splitlines()[-1], 'AUTOBOOT' if fault == 0 else 'POWER_OFF')
                self.assertIn('REFUSED_STALE_JOB' if fault == 0 else
                              'REFUSED_SOURCE_MOUNT' if fault == 6 else
                              'REFUSED_TARGET_ID' if fault == 7 else
                              'REFUSED_RECOVERY_MARKER', output)

    def test_preflight_target_readonly_opens_closes_and_checks_both_environments(self):
        source = f'''#define open captured_open
#define fstat captured_fstat
#define ioctl captured_ioctl
#define read captured_read
#define pread captured_pread
#define close captured_close
#define pwrite captured_pwrite
#define write captured_write
#define main writer_main
#include "{WRITER}"
#undef main
static unsigned char envs[2][SV08_ENV_BYTES];
static int target_opens,target_closes,target_flags,case_number,transfers;
int captured_open(const char *path,int flags,...) {{
 if(!strcmp(path,SV08_TARGET)){{target_opens++;target_flags=flags;return case_number==7?-1:100;}}
 if(!strcmp(path,SV08_TARGET_DEV_SYSFS))return 101;
 return -1;
}}
int captured_fstat(int fd,struct stat *st) {{
 if(fd!=100)return -1;memset(st,0,sizeof(*st));
 st->st_mode=S_IFBLK;st->st_rdev=makedev(case_number==5?179:179,case_number==5?1:0);
 return 0;
}}
int captured_ioctl(int fd,unsigned long request,...) {{
 if(fd!=100||request!=BLKGETSIZE64)return -1;
 va_list args;va_start(args,request);uint64_t *size=va_arg(args,uint64_t *);va_end(args);
 *size=case_number==4?TARGET_BYTES-1:TARGET_BYTES;return 0;
}}
ssize_t captured_read(int fd,void *out,size_t n) {{
 if(fd!=101)return -1;static int sent;
 if(sent){{sent=0;return 0;}}sent=1;
 const char *value="179:0\\n";if(n<6)return -1;memcpy(out,value,6);return 6;
}}
ssize_t captured_pread(int fd,void *out,size_t n,off_t off) {{
 if(fd!=100||n!=SV08_ENV_BYTES)return -1;
 int which=(uint64_t)off==sv08_env_offsets[0]?0:(uint64_t)off==sv08_env_offsets[1]?1:-1;
 if(which<0)return -1;
 if(case_number==6&&which==1)return SV08_ENV_BYTES-1;
 memcpy(out,envs[which],n);return n;
}}
int captured_close(int fd) {{if(fd==100){{target_closes++;return case_number==8?-1:0;}}return 0;}}
ssize_t captured_pwrite(int fd,const void *buf,size_t n,off_t off) {{transfers++;return -1;}}
ssize_t captured_write(int fd,const void *buf,size_t n) {{transfers++;return -1;}}
static void make_env(unsigned char *env,const char *token) {{
 const char fields[]="sv08_env_layout=ab-8gb-v1\\0BOOT_ORDER=A B\\0BOOT_A_LEFT=0\\0BOOT_B_LEFT=0\\0";
 memcpy(env+5,fields,sizeof(fields));
 size_t at=5+sizeof(fields)-1;
 snprintf((char *)env+at,SV08_ENV_BYTES-at,"sv08_reimage_arm=%s",token);
 uint32_t crc=sv08_env_crc32(env+5,SV08_ENV_BYTES-5);
 for(int i=0;i<4;i++)env[i]=(unsigned char)(crc>>(i*8));
}}
int main(int argc,char **argv) {{
 if(argc!=2)return 2;case_number=atoi(argv[1]);
 make_env(envs[0],"preflight-job");make_env(envs[1],"preflight-job");
 if(case_number==1)envs[0][10]^=1;
 if(case_number==2)envs[1][10]^=1;
 if(case_number==3)make_env(envs[1],"other-job");
 if(case_number==9)make_env(envs[0],"other-job");
 const char *status=preflight_open_target(makedev(179,0));
 printf("%s %d %d %d %d\\n",status,target_opens,target_closes,target_flags,transfers);
 return 0;
}}
'''
        source = '#include <stdarg.h>\n' + source
        result, binary = self.compile_case(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        for case, status in [(0, 'PREFLIGHT_PASS'), (1, 'REFUSED_UNSAFE_BOOT_ENV'),
                             (2, 'REFUSED_UNSAFE_BOOT_ENV'), (3, 'REFUSED_UNSAFE_BOOT_ENV'),
                             (4, 'REFUSED_INPUT'), (5, 'REFUSED_INPUT'),
                             (6, 'REFUSED_UNSAFE_BOOT_ENV'), (7, 'REFUSED_INPUT'),
                             (8, 'REFUSED_TARGET_CLOSE'), (9, 'REFUSED_UNSAFE_BOOT_ENV')]:
            with self.subTest(case=case):
                output = subprocess.check_output([str(binary), str(case)], text=True).strip()
                observed, opens, closes, flags, transfers = output.split()
                self.assertEqual((observed, opens, closes),
                                 (status, '1', '0' if case == 7 else '1'))
                self.assertEqual(transfers, '0')
                self.assertEqual(int(flags) & 3, 0)  # O_RDONLY, never O_RDWR.
                self.assertTrue(int(flags) & os.O_EXCL)


if __name__ == '__main__':
    unittest.main()
