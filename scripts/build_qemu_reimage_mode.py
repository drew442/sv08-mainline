#!/usr/bin/env python3
"""Build a nondeployable QEMU NFS-root reimage bundle, never an SD/eMMC image."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tests'))
from sv08_emmc_job import canonical_json  # noqa: E402
from sv08_reimage_signature import policy, policy_hash, verify_job  # noqa: E402

WRITER = REPO / 'tests/fixtures/sd-network-root/emmc_image_writer.c'
HEADERS = (REPO / 'tests/fixtures/sd-network-root/emmc_cid_admission.h',
           REPO / 'tests/fixtures/sd-network-root/emmc_locator.h')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(root, raw_job, signature, *, fault=None, claim_only=False, now=None):
    root = Path(root)
    if not root.is_dir() or any(root.iterdir()):
        raise ValueError('Fresh empty QEMU root required')
    target_policy = policy()
    descriptor = verify_job(raw_job, signature, target_policy, now=now)
    job_hash = hashlib.sha256(raw_job).hexdigest()
    for directory in ('dev', 'proc', 'sys', 'run', 'data', 'tmp'):
        (root / directory).mkdir()
    (root / 'job.json').write_bytes(raw_job)
    (root / 'job.sig').write_bytes(signature)
    (root / 'synthetic-target-policy.json').write_bytes(canonical_json(target_policy))
    args = ['aarch64-linux-gnu-gcc', '-static', '-Os', '-D_FORTIFY_SOURCE=2',
            '-Wall', '-Wextra', '-Werror',
            f'-DSV08_JOB_ID="{descriptor["job_id"]}"',
            f'-DSV08_JOB_DESCRIPTOR_SHA256="{job_hash}"',
            f'-DSV08_TARGET_POLICY_SHA256="{policy_hash(target_policy)}"',
            f'-DSV08_JOB_NOT_BEFORE={descriptor["issued_unix"]}LL',
            f'-DSV08_JOB_EXPIRES={descriptor["expires_unix"]}LL',
            f'-DSV08_SOURCE_SHA256="{descriptor["source"]["sha256"]}"',
            f'-DSV08_JOB_SIGNATURE_SHA256="{hashlib.sha256(signature).hexdigest()}"']
    if claim_only:
        args.append('-DSV08_CLAIM_ONLY=1')
    if fault:
        if fault not in {'before-write', 'partial-write', 'flush', 'readback'}:
            raise ValueError('Invalid QEMU-only injected fault')
        args.append(f'-DSV08_TEST_FAULT="{fault}"')
    args += ['-o', str(root / 'sd-network-init'), str(WRITER)]
    subprocess.run(args, check=True, timeout=120, capture_output=True)
    (root / 'sd-network-init').chmod(0o755)
    manifest = {
        'status': 'nondeployable-qemu-only', 'mode': 'qemu-reimage',
        'physical_target_supported': False, 'bootable_sd_image': False,
        'job_sha256': job_hash, 'signature_sha256': hashlib.sha256(signature).hexdigest(),
        'trusted_policy_sha256': policy_hash(target_policy),
        'trusted_test_verifier_sha256': digest(
            REPO / 'tests/fixtures/sd-network-root/synthetic-keys/test-verification-key.pem'),
        'writer_sha256': digest(WRITER),
        'builder_sha256': digest(Path(__file__)),
        'signature_contract_sha256': digest(REPO / 'tests/sv08_reimage_signature.py'),
        'header_sha256': {path.name: digest(path) for path in HEADERS},
        'binary_sha256': digest(root / 'sd-network-init'),
        'compiler': subprocess.check_output(['aarch64-linux-gnu-gcc', '--version'], text=True).splitlines()[0],
        'source_date_epoch': 1790380800,
    }
    (root / 'reimage-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('qemu-reimage',), required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--signature', type=Path, required=True)
    args = parser.parse_args()
    if args.root.exists():
        raise ValueError('Output root must be new')
    args.root.mkdir(mode=0o700)
    print(json.dumps(build(args.root, args.job.read_bytes(), args.signature.read_bytes())))


if __name__ == '__main__':
    main()
