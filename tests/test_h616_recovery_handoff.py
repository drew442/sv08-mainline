"""Focused purpose binding checks; FIT tooling and hardware are not invoked."""
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest import mock

from scripts import build_h616_recovery_handoff as handoff


class PreflightCompositionTests(unittest.TestCase):
    def test_native_fit_records_small_fixture_memory_footprint(self):
        with tempfile.TemporaryDirectory(dir=handoff.REPO / 'local') as temporary:
            root = Path(temporary)
            bundle = root / 'bundle'
            bundle.mkdir()
            (bundle / 'job.json').write_text(json.dumps({
                'format': 'sv08-h616-signed-preflight-v1', 'job_id': 'offline-fixture'}))
            kernel, initrd, dtb = (root / name for name in ('Image', 'initrd', 'board.dtb'))
            kernel.write_bytes(b'offline-kernel-fixture')
            initrd.write_bytes(b'offline-initramfs-fixture')
            subprocess.run(['dtc', '-I', 'dts', '-O', 'dtb', '-o', str(dtb), '-'],
                           input='/dts-v1/; / { compatible = "test,fixture"; };',
                           text=True, check=True, capture_output=True, timeout=30)
            manifest = {'preflight_only': True, 'job_format': 'sv08-h616-signed-preflight-v1',
                        'synthetic_test': False, 'trusted_initramfs': True,
                        'recovery_handoff': True, 'binary_sha256': 'a' * 64}
            # Only bundle intake/append are modeled: real installed dtc/mkimage
            # compose the tiny FIT. This is not a signed or bootable physical job.
            with (mock.patch.object(handoff, 'commissioning_bundle',
                                    return_value=(bundle, manifest, {})),
                  mock.patch.object(handoff, 'verify_compiled_writer', return_value='b' * 64),
                  mock.patch.object(handoff, 'append_commissioning_initramfs',
                                    return_value={'offline_fixture': True})):
                result = handoff.build(root / 'out', kernel, initrd, dtb, bundle,
                                       '192.0.2.1', '/source', 12000)
            self.assertEqual(result['initramfs_bytes'], initrd.stat().st_size)
            self.assertEqual(result['kernel_bytes'], kernel.stat().st_size)
            self.assertEqual(result['dtb_bytes'], dtb.stat().st_size)
            self.assertLess(result['fit_load_end'], handoff.MARKER_ADDR)
            self.assertLessEqual(result['fit_bytes'], result['fit_max_bytes'])
            self.assertIn('sv08.h616_preflight=1', result['bootargs'])
            self.assertIn('RAM preflight', (root / 'out/writer.its').read_text())
            result['fixture_total_bytes'] = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
            print('Native tiny FIT resource evidence: ' + json.dumps(result, sort_keys=True))

    def test_signed_format_must_match_binary_manifest_before_composition(self):
        (handoff.REPO / 'local').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=handoff.REPO / 'local') as temporary:
            root = Path(temporary)
            bundle = root / 'bundle'
            bundle.mkdir()
            inputs = []
            for name in ('Image', 'initrd.img', 'board.dtb'):
                path = root / name
                path.write_bytes(name.encode())
                inputs.append(path)
            job_path = bundle / 'job.json'
            manifest = {'preflight_only': True, 'job_format': 'sv08-h616-signed-preflight-v1',
                        'synthetic_test': False, 'trusted_initramfs': True,
                        'recovery_handoff': True, 'binary_sha256': 'a' * 64}
            def attempt(job_format, binary_manifest=manifest):
                job_path.write_text(json.dumps({'format': job_format, 'job_id': 'offline-test'}))
                with mock.patch.object(handoff, 'commissioning_bundle',
                                       return_value=(bundle, binary_manifest, {})):
                    return handoff.build(root / 'out', *inputs, bundle,
                                         '192.0.2.1', '/source', 12000)

            with self.assertRaisesRegex(ValueError, 'purpose.*mode mismatch'):
                attempt('sv08-h616-signed-reimage-v1')
            self.assertFalse((root / 'out').exists())
            with self.assertRaisesRegex(ValueError, 'purpose.*mode mismatch'):
                attempt('sv08-h616-signed-preflight-v1',
                        dict(manifest, preflight_only=False))
            self.assertFalse((root / 'out').exists())

            def fake_mkimage(argv, **kwargs):
                work = kwargs['cwd']
                (work / argv[-1]).write_bytes(b'FIT' if argv[-1] == 'writer.itb'
                                               else b'SCRIPT')

            with (mock.patch.object(handoff, 'commissioning_bundle',
                                    return_value=(bundle, manifest, {})),
                  mock.patch.object(handoff, 'verify_compiled_writer', return_value='b' * 64),
                  mock.patch.object(handoff, 'append_commissioning_initramfs',
                                    return_value={'offline': True}),
                  mock.patch.object(handoff.subprocess, 'run', side_effect=fake_mkimage)):
                result = attempt('sv08-h616-signed-preflight-v1')
            self.assertTrue(result['preflight_only'])
            self.assertEqual(result['job_format'], 'sv08-h616-signed-preflight-v1')
            self.assertEqual(result['writer_sha256'], manifest['binary_sha256'])
            self.assertEqual(result['fit_sha256'], hashlib.sha256(b'FIT').hexdigest())
            self.assertEqual(result['initramfs_sha256'],
                             hashlib.sha256(inputs[1].read_bytes()).hexdigest())


class V2CompiledAlgorithmTests(unittest.TestCase):
    def test_actual_algorithm_guard_and_no_transfer_preflight(self):
        from scripts.build_h616_reimage_candidate import (compiled_purpose_bytes,
            elf_compiled_purpose, verify_compiled_writer, runtime_compile_flags, WRITER, digest)
        from tests.test_h616_reimage_candidate import (PhysicalPreflightTests,
                                                       physical_v2_policy)
        from tests.sv08_emmc_job import canonical_json
        import subprocess
        case = PhysicalPreflightTests()
        self.addCleanup(case.doCleanups)
        policy = physical_v2_policy()
        raw_policy = canonical_json(policy)
        job = {'format': 'sv08-h616-signed-preflight-v1',
               'target_policy_sha256': digest(raw_policy)}
        raw_job = canonical_json(job)
        extra = [f'-DSV08_TARGET_POLICY_SHA256="{digest(raw_policy)}"',
                 f'-DSV08_JOB_DESCRIPTOR_SHA256="{digest(raw_job)}"']
        manifest = {'preflight_only': True, 'trusted_initramfs': True,
                    'recovery_handoff': True, 'synthetic_test': False}
        # Same signed digest/job, different actual algorithm. The v1 ELF cannot
        # authorize v2 even when its unsigned metadata is relabeled.
        for v2 in (False, True):
            result, binary = case.compile_case(f'#include "{WRITER}"\n',
                extra + (runtime_compile_flags(policy) if v2 else []))
            self.assertEqual(result.returncode, 0, result.stderr)
            root = binary.parent
            (root / 'sd-network-init').write_bytes(binary.read_bytes())
            (root / 'job.json').write_bytes(raw_job)
            (root / 'commissioning-target-policy.json').write_bytes(raw_policy)
            if not v2:
                with self.assertRaisesRegex(ValueError, 'Actual ELF compiled purpose'):
                    verify_compiled_writer(root, manifest)
                continue
            self.assertEqual(elf_compiled_purpose(binary), compiled_purpose_bytes(
                job['format'], digest(raw_job), digest(raw_policy),
                trusted_initramfs=True, recovery_handoff=True, synthetic_test=False,
                policy=policy))
            verify_compiled_writer(root, manifest)
            imports = subprocess.check_output(['nm', '-u', str(binary)], text=True)
            for forbidden in ('pwrite', ' write@', 'sendfile', 'splice'):
                self.assertNotIn(forbidden, imports)
            # Production compile itself refuses synthetic v2, independently of Python.
            result, _ = case.compile_case(f'#include "{WRITER}"\n',
                extra + runtime_compile_flags(policy) + ['-DSV08_H616_SYNTHETIC_TEST=1'])
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
