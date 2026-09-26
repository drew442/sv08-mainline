"""Synthetic Ed25519 job contract for disposable QEMU reimage runs only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time

from sv08_emmc_job import canonical_json

REPO = Path(__file__).resolve().parents[1]
PUBLIC_KEY = REPO / 'tests/fixtures/sd-network-root/synthetic-keys/test-verification-key.pem'
PRIVATE_KEY = REPO / 'tests/fixtures/sd-network-root/synthetic-keys/test-signing-key.pem'
CID = '00000000000000000000000000000001'
SECTORS = 61_079_552
IMAGE_BYTES = 7_818_182_656
TARGET_BYTES = 32_000_000_000
FORMAT = 'sv08-qemu-signed-reimage-v1'


def policy():
    return {'mode': 'synthetic-qemu-only', 'cid': CID, 'sectors': SECTORS,
            'dev_t': '8:0', 'usb_serial': 'SV08_QEMU_REIMAGE_TEST_ONLY',
            'usb_target_bytes': TARGET_BYTES, 'image_bytes': IMAGE_BYTES}


def policy_hash(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def signed_fields(descriptor, target_policy, now=None):
    """Require an exact, canonical contract before the claim is armed."""
    if not isinstance(descriptor, dict) or set(descriptor) != {
            'format', 'job_id', 'issued_unix', 'expires_unix', 'source',
            'target_policy_sha256', 'image'}:
        raise ValueError('Malformed signed-job fields')
    if descriptor['format'] != FORMAT or not re.fullmatch(r'[a-z0-9-]{1,64}', descriptor['job_id']):
        raise ValueError('Malformed signed-job identity')
    now = int(time.time()) if now is None else now
    issued, expires = descriptor['issued_unix'], descriptor['expires_unix']
    if type(issued) is not int or type(expires) is not int or not issued <= now < expires or expires-issued > 86400:
        raise ValueError('Stale or invalid signed job')
    if target_policy != policy() or descriptor['target_policy_sha256'] != policy_hash(target_policy):
        raise ValueError('Untrusted synthetic target policy')
    source = descriptor['source']
    if not isinstance(source, dict) or set(source) != {'bytes', 'sha256', 'mode'} or source['bytes'] != IMAGE_BYTES or source['mode'] != 'read-only-nfs' or not re.fullmatch(r'[0-9a-f]{64}', source['sha256']):
        raise ValueError('Malformed signed source')
    image = descriptor['image']
    if not isinstance(image, dict) or set(image) != {'bytes', 'sha256', 'layout'} or image['bytes'] != IMAGE_BYTES or image['sha256'] != source['sha256']:
        raise ValueError('Malformed signed image')
    from host_qemu_sd_network_emmc_write import expected_records, DISK_GUID
    expected_layout = {'disk_guid': DISK_GUID, 'image_bytes': IMAGE_BYTES,
                       'backup_gpt_at_image_end': True, 'partitions': expected_records()}
    if image['layout'] != expected_layout:
        raise ValueError('Wrong signed six-partition GPT layout')
    return canonical_json(descriptor)


def sign_test_job(descriptor):
    """Use only the committed synthetic private key in offline tests."""
    with tempfile.TemporaryDirectory() as tmp:
        payload = Path(tmp) / 'job'
        signature = Path(tmp) / 'signature'
        payload.write_bytes(canonical_json(descriptor))
        subprocess.run(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey',
                        str(PRIVATE_KEY), '-in', str(payload), '-out', str(signature)],
                       check=True, capture_output=True)
        return signature.read_bytes()


def verify_job(raw, signature, target_policy, now=None):
    """Verifier anchor is a pinned file, never a field in job data."""
    descriptor = json.loads(raw)
    if signed_fields(descriptor, target_policy, now) != raw:
        raise ValueError('Noncanonical signed-job bytes')
    if len(signature) != 64:
        raise ValueError('Missing or malformed job signature')
    with tempfile.TemporaryDirectory() as tmp:
        payload = Path(tmp) / 'job'
        sig = Path(tmp) / 'signature'
        payload.write_bytes(raw)
        sig.write_bytes(signature)
        result = subprocess.run(['openssl', 'pkeyutl', '-verify', '-rawin',
                                 '-pubin', '-inkey', str(PUBLIC_KEY), '-in',
                                 str(payload), '-sigfile', str(sig)],
                                capture_output=True)
        if result.returncode:
            raise ValueError('Invalid test-key job signature')
    return descriptor
