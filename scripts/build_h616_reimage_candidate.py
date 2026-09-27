#!/usr/bin/env python3
"""Build an inert, nonbootable H616 commissioning root from private local inputs.

This is not a printer deployment command. The separate H12 review must provide
the live identity, trigger, boot chain, recovery operation and write authority.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tests'))
from sv08_emmc_job import canonical_json  # noqa: E402

WRITER = REPO / 'tests/fixtures/sd-network-root/emmc_image_writer.c'
IMAGE_BYTES = 7_818_182_656
SECTORS = 61_079_552
TARGET_BYTES = SECTORS * 512
FIELDS = {'format', 'cid', 'controller', 'card_type', 'sectors', 'dev_t',
          'target_device', 'board_compatible', 'claim_server', 'image_bytes',
          'image_sha256', 'image_layout'}
TEST_DISK_GUID = '8aae17d2-09b3-47ab-8e35-8e91e63cf2b0'
TEST_PART_GUIDS = tuple(f'ed49c82b-2455-4709-8f41-66fd41664e{i:02d}' for i in range(1, 7))
TEST_IMAGE_SHA256 = '7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec'
# Read-only artifact audit: docs/hardware/host-board-image-20260925-v5-gpt-audit-20260927.json.
# This is the image GPT identity, never the prior destination's pre-write GUID.
V5_IMAGE_SHA256 = 'ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f'
V5_IMAGE_DISK_GUID = 'b643a41a-d63f-40aa-9940-74a8f4e19a8d'
V5_IMAGE_PARTITIONS = (
    ('boot-a', 'ba55a9b4-7969-423b-a739-db62e231b7a1', 16777216, 201326592),
    ('root-a', '26c68198-9248-47af-bbd3-643f1b604ef5', 218103808, 2147483648),
    ('boot-b', '7b6e5211-6c5f-432f-9afc-2ac7e4f80b04', 2365587456, 201326592),
    ('root-b', 'd8d04a9a-f51f-41b3-a474-e079efe97186', 2566914048, 2147483648),
    ('recovery', 'b28438ed-f895-4b93-9bad-d27d3890ccd3', 4714397696, 536870912),
    ('data', '4773f966-0678-4cf5-bb83-8ee6fb11d8eb', 5251268608, 2565865472),
)
REVIEWED_PHYSICAL_IMAGES = {V5_IMAGE_SHA256: V5_IMAGE_DISK_GUID}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def private_file(path):
    path = Path(path).absolute()
    private_root = REPO / 'local'
    if (not path.is_relative_to(private_root) or
            any(entry.is_symlink() for entry in (path, *path.parents) if entry.is_relative_to(private_root)) or
            not path.resolve().is_relative_to(private_root.resolve()) or
            not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600):
        raise ValueError('Private regular 0600 input under this worktree local/ required')
    return path.read_bytes()


def safe_output_root(path, *, synthetic_test):
    root = Path(path).absolute()
    private_root = REPO / 'local'
    try:
        if any(entry.is_symlink() for entry in (root, *root.parents)):
            return False
        if not synthetic_test and (
                not root.is_relative_to(private_root) or
                not root.resolve().is_relative_to(private_root.resolve())):
            return False
    except (OSError, RuntimeError):
        return False
    return True


def expected_image_layout(synthetic_test, image_sha256):
    """Derive names/geometry and physical PARTUUIDs from reviewed source pins."""
    sys.path.insert(0, str(REPO / 'scripts'))
    from prepare_host_os import layout  # noqa: E402
    config = json.loads((REPO / 'configs/images/host-ab.json').read_text())
    parts = layout(config)
    if config['image_bytes'] != IMAGE_BYTES or len(parts) != 6:
        raise ValueError('Reviewed host image layout changed')
    if synthetic_test:
        if image_sha256 != TEST_IMAGE_SHA256:
            return None
        identities = TEST_PART_GUIDS
        disk_guid = TEST_DISK_GUID
    else:
        disk_guid = REVIEWED_PHYSICAL_IMAGES.get(image_sha256)
        if disk_guid is None:
            return None
        profile = json.loads((REPO / 'configs/host-os/recovery-test-sv08-01.json').read_text())
        audited = [dict(number=index, name=name, partuuid=partuuid,
                        offset_bytes=offset, size_bytes=size)
                   for index, (name, partuuid, offset, size) in enumerate(V5_IMAGE_PARTITIONS, 1)]
        identities = tuple(item['partuuid'] for item in profile['partitions'])
        if (len(identities) != 6 or
                [(item['index'], item['role']) for item in profile['partitions']] !=
                [(index, part['name']) for index, part in enumerate(parts, 1)] or
                records_for_layout(parts, identities) != audited):
            raise ValueError('Reviewed board partition identity changed')
    records = records_for_layout(parts, identities)
    return {'disk_guid': disk_guid, 'image_bytes': IMAGE_BYTES,
            'backup_gpt_at_image_end': True, 'partitions': records}


def records_for_layout(parts, identities):
    return [dict(number=index, name=part['name'], partuuid=identities[index - 1],
                 offset_bytes=part['offset_bytes'], size_bytes=part['size_bytes'])
            for index, part in enumerate(parts, 1)]


def exact_image_layout(value, *, synthetic_test, image_sha256):
    if not isinstance(value, dict) or set(value) != {
            'disk_guid', 'image_bytes', 'backup_gpt_at_image_end', 'partitions'}:
        return False
    expected = expected_image_layout(synthetic_test, image_sha256)
    if expected is None:
        return False
    try:
        disk_guid = value['disk_guid']
        if not isinstance(disk_guid, str) or str(uuid.UUID(disk_guid)) != disk_guid or uuid.UUID(disk_guid).int == 0:
            return False
    except (ValueError, AttributeError, TypeError):
        return False
    records = value['partitions']
    if (not isinstance(records, list) or len(records) != 6 or
            any(not isinstance(item, dict) or set(item) != {
                'number', 'name', 'partuuid', 'offset_bytes', 'size_bytes'} or
                type(item['number']) is not int or type(item['offset_bytes']) is not int or
                type(item['size_bytes']) is not int or not isinstance(item['name'], str) or
                not isinstance(item['partuuid'], str) for item in records)):
        return False
    return (type(value['image_bytes']) is int and value['image_bytes'] == IMAGE_BYTES and
            value['backup_gpt_at_image_end'] is True and
            records == expected['partitions'] and disk_guid == expected['disk_guid'])


def policy_fields(value):
    if not isinstance(value, dict) or set(value) != FIELDS or value['format'] != 'sv08-h616-commissioning-policy-v1':
        raise ValueError('Malformed local target policy')
    if (not isinstance(value['cid'], str) or not re.fullmatch(r'[0-9a-f]{32}', value['cid']) or
            value['controller'] != '4022000.mmc' or value['card_type'] != 'MMC' or
            type(value['sectors']) is not int or value['sectors'] != SECTORS or
            value['target_device'] != '/dev/mmcblk0' or
            not isinstance(value['dev_t'], str) or
            not re.fullmatch(r'[1-9][0-9]{0,4}:[0-9]{1,7}', value['dev_t']) or
            not isinstance(value['board_compatible'], str) or
            not re.fullmatch(r'[a-z0-9][a-z0-9,._-]{3,79}', value['board_compatible']) or
            value['board_compatible'] in ('linux,dummy-virt', 'allwinner,sun50i-h616') or
            type(value['image_bytes']) is not int or value['image_bytes'] != IMAGE_BYTES or
            not isinstance(value['image_sha256'], str) or
            not re.fullmatch(r'[0-9a-f]{64}', value['image_sha256']) or
            not exact_image_layout(value['image_layout'],
                                   synthetic_test=value['board_compatible'] == 'test,synthetic-h616',
                                   image_sha256=value['image_sha256'])):
        raise ValueError('Untrusted or incomplete H616 target/image policy')
    try:
        server = str(ipaddress.IPv4Address(value['claim_server']))
    except (ipaddress.AddressValueError, TypeError) as error:
        raise ValueError('Invalid local claim server') from error
    if server != value['claim_server'] or ipaddress.IPv4Address(server).is_loopback or ipaddress.IPv4Address(server).is_multicast:
        raise ValueError('Unsafe local claim server')
    return value


def verify_signed_job(raw, signature, verification_key, target_policy, *, now=None):
    try:
        job = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError('Malformed signed job') from error
    if canonical_json(job) != raw or not isinstance(job, dict) or set(job) != {
            'format', 'job_id', 'issued_unix', 'expires_unix', 'source',
            'target_policy_sha256', 'image'}:
        raise ValueError('Noncanonical or malformed signed job')
    import time
    now = int(time.time()) if now is None else now
    issued, expires = job['issued_unix'], job['expires_unix']
    if (job['format'] != 'sv08-h616-signed-reimage-v1' or
            not isinstance(job['job_id'], str) or not re.fullmatch(r'[a-z0-9-]{1,64}', job['job_id']) or
            type(issued) is not int or type(expires) is not int or
            not issued <= now < expires or expires - issued > 86400 or
            job['target_policy_sha256'] != digest(canonical_json(target_policy))):
        raise ValueError('Stale job or policy mismatch')
    source, image = job['source'], job['image']
    expected_source = {'bytes': IMAGE_BYTES, 'sha256': target_policy['image_sha256'], 'mode': 'read-only-nfs'}
    expected_image = {'bytes': IMAGE_BYTES, 'sha256': target_policy['image_sha256'],
                      'layout': target_policy['image_layout']}
    if source != expected_source or image != expected_image or len(signature) != 64:
        raise ValueError('Source, image, layout or signature mismatch')
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        payload = Path(temporary) / 'job'
        sig = Path(temporary) / 'signature'
        key = Path(temporary) / 'verifier'
        payload.write_bytes(raw)
        sig.write_bytes(signature)
        key.write_bytes(verification_key)
        check = subprocess.run(['openssl', 'pkeyutl', '-verify', '-rawin', '-pubin',
                                '-inkey', str(key), '-in', str(payload), '-sigfile', str(sig)],
                               capture_output=True, timeout=30)
        if check.returncode:
            raise ValueError('Invalid detached job signature')
    return job


def build(root, policy_path, key_path, job_path, signature_path, *, now=None,
          synthetic_test=False, fault=None, claim_only=False):
    root = Path(root).absolute()
    if (not safe_output_root(root, synthetic_test=synthetic_test) or
            (root.exists() and (not root.is_dir() or any(root.iterdir())))):
        raise ValueError('Fresh empty output required; physical candidates stay under local/')
    if (fault or claim_only) and not synthetic_test:
        raise ValueError('Fault injection and claim-only builds are synthetic QEMU only')
    if fault not in (None, 'before-write', 'partial-write', 'abrupt-after-write', 'flush', 'readback'):
        raise ValueError('Unknown injected fault')
    policy_raw = private_file(policy_path)
    target_policy = policy_fields(json.loads(policy_raw))
    if canonical_json(target_policy) != policy_raw:
        raise ValueError('Local policy must use canonical JSON')
    verification_key = private_file(key_path)
    raw_job, signature = private_file(job_path), private_file(signature_path)
    job = verify_signed_job(raw_job, signature, verification_key, target_policy, now=now)
    if synthetic_test and target_policy['board_compatible'] != 'test,synthetic-h616':
        raise ValueError('Synthetic QEMU build requires synthetic board policy')
    if not synthetic_test and target_policy['board_compatible'] == 'test,synthetic-h616':
        raise ValueError('Synthetic identity cannot build a physical candidate')
    flags = ['-DSV08_H616_COMMISSIONING=1',
             f'-DSV08_H616_EXPECTED_CID="{target_policy["cid"]}"',
             f'-DSV08_H616_EXPECTED_DEV_T="{target_policy["dev_t"]}"',
             f'-DSV08_H616_BOARD_COMPATIBLE="{target_policy["board_compatible"]}"',
             f'-DSV08_H616_CLAIM_SERVER="{target_policy["claim_server"]}"',
             f'-DSV08_TARGET_BYTES={TARGET_BYTES}ULL',
             f'-DSV08_JOB_ID="{job["job_id"]}"',
             f'-DSV08_JOB_DESCRIPTOR_SHA256="{digest(raw_job)}"',
             f'-DSV08_TARGET_POLICY_SHA256="{digest(policy_raw)}"',
             f'-DSV08_JOB_NOT_BEFORE={job["issued_unix"]}LL',
             f'-DSV08_JOB_EXPIRES={job["expires_unix"]}LL',
             f'-DSV08_SOURCE_SHA256="{target_policy["image_sha256"]}"',
             f'-DSV08_JOB_SIGNATURE_SHA256="{digest(signature)}"']
    if synthetic_test:
        flags.append('-DSV08_H616_SYNTHETIC_TEST=1')
    if claim_only:
        flags.append('-DSV08_CLAIM_ONLY=1')
    if fault:
        flags.append(f'-DSV08_TEST_FAULT="{fault}"')
    root.mkdir(mode=0o755, exist_ok=True)
    root.chmod(0o755)
    for directory in ('dev', 'proc', 'sys', 'run', 'data', 'tmp'):
        (root / directory).mkdir()
    (root / 'job.json').write_bytes(raw_job)
    (root / 'job.sig').write_bytes(signature)
    (root / 'commissioning-target-policy.json').write_bytes(policy_raw)
    (root / 'expected.sha256').write_text(target_policy['image_sha256'] + '\n')
    output = root / 'sd-network-init'
    subprocess.run(['aarch64-linux-gnu-gcc', '-static', '-Os', '-D_FORTIFY_SOURCE=2',
                    '-Wall', '-Wextra', '-Werror', *flags, '-o', str(output), str(WRITER)],
                   check=True, capture_output=True, timeout=120)
    output.chmod(0o755)
    manifest = {'status': 'nondeployable-commissioning-candidate', 'mode': 'h616-commissioning',
                'bootable_sd_image': False, 'physical_target_validated': False,
                'synthetic_test': synthetic_test, 'claim_trigger_provisioned': False,
                'policy_sha256': digest(policy_raw), 'job_sha256': digest(raw_job),
                'signature_sha256': digest(signature), 'verifier_sha256': digest(verification_key),
                'writer_sha256': digest(WRITER.read_bytes()), 'binary_sha256': digest(output.read_bytes()),
                'compiler': subprocess.check_output(['aarch64-linux-gnu-gcc', '--version'], text=True).splitlines()[0]}
    (root / 'reimage-manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('h616-commissioning',), required=True)
    for name in ('root', 'policy', 'verification-key', 'job', 'signature'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.policy, args.verification_key, args.job,
                           args.signature), sort_keys=True))


if __name__ == '__main__':
    main()
