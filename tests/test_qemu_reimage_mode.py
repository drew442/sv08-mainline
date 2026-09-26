"""Signed QEMU-only job and separate bundle admission checks."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.host_qemu_sd_network_emmc_write import (
    DISK_GUID, IMAGE_BYTES, IMAGE_SHA256, expected_records)
from tests.sv08_emmc_job import canonical_json
from tests.sv08_reimage_signature import (
    FORMAT, policy, policy_hash, sign_test_job, verify_job)
from scripts.build_qemu_reimage_mode import build


def descriptor():
    return {
        'format': FORMAT, 'job_id': 'qemu-reimage-test-001',
        'issued_unix': 1000, 'expires_unix': 2000,
        'source': {'bytes': IMAGE_BYTES, 'sha256': IMAGE_SHA256, 'mode': 'read-only-nfs'},
        'target_policy_sha256': policy_hash(policy()),
        'image': {'bytes': IMAGE_BYTES, 'sha256': IMAGE_SHA256,
                  'layout': {'disk_guid': DISK_GUID, 'image_bytes': IMAGE_BYTES,
                             'backup_gpt_at_image_end': True,
                             'partitions': expected_records()}},
    }


class QemuReimageModeTests(unittest.TestCase):
    def test_signed_contract_refuses_missing_changed_stale_wrong_key_and_layout(self):
        job = descriptor()
        raw = canonical_json(job)
        signature = sign_test_job(job)
        self.assertEqual(verify_job(raw, signature, policy(), now=1500), job)
        cases = [
            (raw, b'', policy(), 1500),
            (raw, signature, policy(), 2000),
            (raw + b' ', signature, policy(), 1500),
            (raw, signature, dict(policy(), cid='0' * 32), 1500),
        ]
        changed = copy.deepcopy(job)
        changed['source']['sha256'] = '0' * 64
        cases.append((canonical_json(changed), signature, policy(), 1500))
        wrong_layout = copy.deepcopy(job)
        wrong_layout['image']['layout']['partitions'][0]['name'] = 'changed'
        cases.append((canonical_json(wrong_layout), sign_test_job(wrong_layout), policy(), 1500))
        wrong_key = bytearray(signature)
        wrong_key[0] ^= 1
        cases.append((raw, bytes(wrong_key), policy(), 1500))
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / 'other-key.pem'
            job_path = Path(tmp) / 'job.json'
            sig_path = Path(tmp) / 'wrong-key.sig'
            job_path.write_bytes(raw)
            subprocess.run(['openssl', 'genpkey', '-algorithm', 'Ed25519', '-out', str(key)],
                           check=True, capture_output=True)
            subprocess.run(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', str(key),
                            '-in', str(job_path), '-out', str(sig_path)],
                           check=True, capture_output=True)
            cases.append((raw, sig_path.read_bytes(), policy(), 1500))
        for payload, sig, target_policy, now in cases:
            with self.subTest(payload_hash=hashlib.sha256(payload).hexdigest(), now=now):
                with self.assertRaises(ValueError):
                    verify_job(payload, sig, target_policy, now=now)

    def test_builder_is_explicit_qemu_only_and_reproducible(self):
        job = descriptor()
        raw, sig = canonical_json(job), sign_test_job(job)
        with tempfile.TemporaryDirectory() as tmp:
            roots = [Path(tmp) / 'first', Path(tmp) / 'second']
            manifests = []
            for root in roots:
                root.mkdir()
                manifests.append(build(root, raw, sig, now=1500))
            self.assertEqual(manifests, [manifests[0]] * 2)
            self.assertEqual((roots[0] / 'sd-network-init').read_bytes(),
                             (roots[1] / 'sd-network-init').read_bytes())
            self.assertFalse(manifests[0]['physical_target_supported'])
            self.assertFalse(manifests[0]['bootable_sd_image'])
            self.assertNotIn('u-boot-sunxi-with-spl.bin', [p.name for p in roots[0].iterdir()])
            self.assertEqual(json.loads((roots[0] / 'job.json').read_text()), job)
            c_source = Path(__file__).parent / 'fixtures/sd-network-root/emmc_image_writer.c'
            native = Path(tmp) / 'bundle-guard'
            subprocess.run([
                'cc', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                '-DSV08_BUNDLE_SELFTEST',
                f'-DSV08_JOB_DESCRIPTOR_SHA256="{manifests[0]["job_sha256"]}"',
                f'-DSV08_JOB_SIGNATURE_SHA256="{manifests[0]["signature_sha256"]}"',
                f'-DSV08_TARGET_POLICY_SHA256="{manifests[0]["trusted_policy_sha256"]}"',
                '-o', str(native), str(c_source)], check=True, capture_output=True)
            def admission():
                return subprocess.check_output([str(native), str(roots[0])], text=True).strip()
            self.assertEqual(admission(), 'admitted')
            for name in ('job.json', 'job.sig', 'synthetic-target-policy.json'):
                path = roots[0] / name
                original = path.read_bytes()
                path.write_bytes(original + b'x')
                self.assertEqual(admission(), 'refused', name)
                path.write_bytes(original)
            with self.assertRaises(ValueError):
                build(roots[0], raw, sig, now=1500)
            third = Path(tmp) / 'rejected'
            third.mkdir()
            with self.assertRaises(ValueError):
                build(third, raw, b'unsigned', now=1500)
            self.assertEqual(list(third.iterdir()), [])

    def test_virtual_board_guard_precedes_target_open(self):
        source = (Path(__file__).parent / 'fixtures/sd-network-root/emmc_image_writer.c').read_text()
        self.assertLess(source.index('!qemu_virt_only()'), source.index('out=open(target,O_RDWR'))
        self.assertIn('linux,dummy-virt', source)
        self.assertIn('#define SV08_EMMC_SECTORS 61079552ULL', source)
        default = (Path(__file__).parent.parent / 'scripts/build_sd_network_image.py').read_text()
        self.assertNotIn('emmc_image_writer.c', default)
        self.assertNotIn('build_qemu_reimage_mode', default)


if __name__ == '__main__':
    unittest.main()
