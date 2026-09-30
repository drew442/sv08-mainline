#!/usr/bin/env python3
"""Prepare one local H616 image job and durable claim; never touch block devices.

This attended commissioning tool is not a release updater. Its claim-state
implementation is the already-tested synthetic protocol in tests/sv08_emmc_job.py;
retire that test-module dependency when the protocol is promoted for release.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import tempfile
import time

from scripts.build_h616_reimage_candidate import IMAGE_BYTES, policy_fields, verify_signed_job
from tests.sv08_emmc_job import (ClaimHTTPServer, ClaimState, canonical_json,
                                receipt_message, sign_receipt)

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO / 'local'


def sha256_file(path: Path) -> str:
    with path.open('rb', buffering=0) as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def private_input(path: Path) -> bytes:
    path = Path(os.path.abspath(path))
    if (not path.is_relative_to(LOCAL) or
            any(part.is_symlink() for part in (path, *path.parents)) or
            not path.resolve(strict=True).is_relative_to(LOCAL.resolve()) or
            not stat.S_ISREG(path.lstat().st_mode) or
            stat.S_IMODE(path.stat().st_mode) != 0o600 or
            path.stat().st_uid != os.getuid() or path.stat().st_nlink != 1):
        raise ValueError('Private regular 0600 owner input under local/ required')
    return path.read_bytes()


def source_image(path: Path, expected_sha256: str, *, digest=sha256_file) -> Path:
    path = Path(os.path.abspath(path))
    if (path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode) or
            path.stat().st_size != IMAGE_BYTES or
            digest(path) != expected_sha256):
        raise ValueError('Source must be the exact reviewed raw 8 GB image')
    return path


def verify_receipt_pair(signing_key: Path, verification_key: Path) -> None:
    payload = receipt_message('key-check', '0' * 64, '1' * 64)
    signature = sign_receipt(payload, signing_key)
    with tempfile.TemporaryDirectory(dir=LOCAL) as temporary:
        root = Path(temporary)
        message, sig = root / 'receipt', root / 'signature'
        message.write_bytes(payload)
        sig.write_bytes(signature)
        result = subprocess.run(['openssl', 'pkeyutl', '-verify', '-rawin',
                                 '-pubin', '-inkey', str(verification_key),
                                 '-in', str(message), '-sigfile', str(sig)],
                                capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError('Receipt signing and verification keys differ')


def sign_job(raw: bytes, signing_key: Path) -> bytes:
    with tempfile.TemporaryDirectory(dir=LOCAL) as temporary:
        root = Path(temporary)
        message, sig = root / 'job', root / 'signature'
        message.write_bytes(raw)
        subprocess.run(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey',
                        str(signing_key), '-in', str(message), '-out', str(sig)],
                       check=True, capture_output=True, timeout=30)
        return sig.read_bytes()


def durable_file(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError('Short durable write')
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def prepare(*, policy_path: Path, image_path: Path, job_signing_key: Path,
            job_verification_key: Path, receipt_signing_key: Path,
            receipt_verification_key: Path, state_dir: Path, source_server: str,
            source_export: str, claim_port: int, valid_seconds: int = 1800,
            execute: bool = False, now: int | None = None,
            synthetic_test: bool = False, image_digest=sha256_file,
            preflight_only: bool = False) -> dict:
    LOCAL.mkdir(mode=0o700, exist_ok=True)
    paths = (policy_path, job_signing_key, job_verification_key,
             receipt_signing_key, receipt_verification_key)
    for path in paths:
        private_input(path)
    policy_raw = private_input(policy_path)
    policy = policy_fields(json.loads(policy_raw))
    if policy_raw != canonical_json(policy):
        raise ValueError('Target policy must be canonical JSON')
    if synthetic_test != (policy['board_compatible'] == 'test,synthetic-h616'):
        raise ValueError('Synthetic and physical target policy must stay separate')
    if preflight_only and synthetic_test:
        raise ValueError('Preflight requires a physical target policy')
    if execute and not synthetic_test and os.geteuid() != 0:
        raise PermissionError('Physical service state must be prepared by root')
    if not synthetic_test and image_digest is not sha256_file:
        raise ValueError('Physical preparation requires streaming source hash')
    try:
        server = str(ipaddress.IPv4Address(source_server))
    except (ipaddress.AddressValueError, TypeError) as error:
        raise ValueError('Invalid source server') from error
    if (server != source_server or not re.fullmatch(r'/[A-Za-z0-9_./-]+', source_export)
            or '..' in source_export.split('/') or not 1024 <= claim_port <= 65535
            or policy['claim_server'] != server or not 60 <= valid_seconds <= 3600):
        raise ValueError('Source, claim endpoint or validity outside reviewed bounds')
    image = source_image(image_path, policy['image_sha256'], digest=image_digest)
    state_dir = Path(os.path.abspath(state_dir))
    if (not state_dir.is_relative_to(LOCAL) or state_dir.exists() or
            any(path.is_symlink() for path in (state_dir, *state_dir.parents))):
        raise ValueError('Fresh non-symlink state directory under local/ required')
    issued = int(time.time()) if now is None else now
    job = {'format': ('sv08-h616-signed-preflight-v1' if preflight_only else
                      'sv08-h616-signed-reimage-v1'),
           'job_id': secrets.token_hex(16), 'issued_unix': issued,
           'expires_unix': issued + valid_seconds,
           'source': {'bytes': IMAGE_BYTES, 'sha256': policy['image_sha256'],
                      'mode': 'read-only-nfs'},
           'target_policy_sha256': hashlib.sha256(policy_raw).hexdigest(),
           'image': {'bytes': IMAGE_BYTES, 'sha256': policy['image_sha256'],
                     'layout': policy['image_layout']}}
    raw = canonical_json(job)
    signature = sign_job(raw, job_signing_key)
    verify_signed_job(raw, signature, private_input(job_verification_key), policy,
                      now=issued, preflight_only=preflight_only)
    verify_receipt_pair(receipt_signing_key, receipt_verification_key)
    receipt = {'status': 'prepared-not-served', 'job_id': job['job_id'],
               'issued_unix': issued, 'expires_unix': job['expires_unix'],
               'policy_sha256': hashlib.sha256(policy_raw).hexdigest(),
               'image_sha256': policy['image_sha256'],
               'image_bytes': IMAGE_BYTES, 'source_server': server,
               'source_export': source_export, 'claim_port': claim_port,
               'job_sha256': hashlib.sha256(raw).hexdigest(),
               'signature_sha256': hashlib.sha256(signature).hexdigest(),
               'receipt_verifier_sha256': sha256_file(receipt_verification_key),
               'synthetic_test': synthetic_test, 'preflight_only': preflight_only,
               'job_format': job['format'], 'automatic_rearm': False}
    if not execute:
        return receipt
    state_dir.mkdir(mode=0o700, parents=False)
    durable_file(state_dir / 'job.json', raw)
    durable_file(state_dir / 'job.sig', signature)
    durable_file(state_dir / 'target-policy.json', policy_raw)
    durable_file(state_dir / 'receipt-verifier.pem', private_input(receipt_verification_key))
    durable_file(state_dir / 'state.json', canonical_json(receipt))
    fsync_dir(state_dir)
    ClaimState.arm_new(state_dir / 'claim', job)
    fsync_dir(state_dir)
    return receipt


class ExpiringClaim:
    """Refuse late claims even if a prepared service remains running."""

    def __init__(self, state: ClaimState, expires_unix: int):
        self.state = state
        self.expires_unix = expires_unix

    def consume(self, request):
        if int(time.time()) >= self.expires_unix:
            return 409, b'EXPIRED\n'
        return self.state.consume(request)


def build_claim_server(*, state_dir: Path, image_path: Path,
                       job_verification_key: Path, receipt_signing_key: Path,
                       bind: str, image_digest=sha256_file,
                       synthetic_test: bool = False, now: int | None = None,
                       listen_bind: str | None = None,
                       preflight_only: bool | None = None):
    """Validate durable state and source before opening the one-shot listener."""
    if listen_bind is not None and (not synthetic_test or
                                    listen_bind not in ('127.0.0.1', '0.0.0.0')):
        raise ValueError('Listener override is synthetic-test-only')
    state_dir = Path(os.path.abspath(state_dir))
    if (not state_dir.is_relative_to(LOCAL) or state_dir.is_symlink() or
            stat.S_IMODE(state_dir.stat().st_mode) != 0o700 or
            state_dir.stat().st_uid != os.getuid()):
        raise ValueError('Private owner state directory required')
    def stored(name):
        return private_input(state_dir / name)
    receipt_raw = stored('state.json')
    receipt = json.loads(receipt_raw)
    if canonical_json(receipt) != receipt_raw or receipt.get('automatic_rearm') is not False:
        raise ValueError('Malformed persisted job state')
    stored_mode = receipt.get('preflight_only', False)
    if type(stored_mode) is not bool:
        raise ValueError('Malformed persisted job purpose')
    if preflight_only is None:
        preflight_only = stored_mode
    if (stored_mode is not preflight_only or
            receipt.get('job_format', 'sv08-h616-signed-reimage-v1') !=
            ('sv08-h616-signed-preflight-v1' if preflight_only else
             'sv08-h616-signed-reimage-v1')):
        raise ValueError('Persisted job purpose mismatch')
    policy_raw = stored('target-policy.json')
    policy = policy_fields(json.loads(policy_raw))
    if (canonical_json(policy) != policy_raw or
            synthetic_test != (policy['board_compatible'] == 'test,synthetic-h616') or
            (not synthetic_test and image_digest is not sha256_file)):
        raise ValueError('Wrong persisted target policy')
    raw = stored('job.json')
    signature = stored('job.sig')
    current = int(time.time()) if now is None else now
    job = verify_signed_job(raw, signature, private_input(job_verification_key),
                            policy, now=current, preflight_only=preflight_only)
    if (receipt.get('job_sha256') != hashlib.sha256(raw).hexdigest() or
            receipt.get('signature_sha256') != hashlib.sha256(signature).hexdigest() or
            receipt.get('policy_sha256') != hashlib.sha256(policy_raw).hexdigest() or
            receipt.get('job_id') != job['job_id'] or
            receipt.get('expires_unix') != job['expires_unix'] or
            receipt.get('image_sha256') != policy['image_sha256'] or
            receipt.get('receipt_verifier_sha256') != hashlib.sha256(
                stored('receipt-verifier.pem')).hexdigest() or
            bind != policy['claim_server'] or
            not isinstance(receipt.get('claim_port'), int) or
            not 1024 <= receipt['claim_port'] <= 65535):
        raise ValueError('Persisted job or listener mismatch')
    source_image(image_path, policy['image_sha256'], digest=image_digest)
    private_input(receipt_signing_key)
    verify_receipt_pair(receipt_signing_key, state_dir / 'receipt-verifier.pem')
    state = ClaimState.reopen(state_dir / 'claim', job)
    if state.claimed.exists():
        raise ValueError('Claim already consumed; no retry or rearm')
    return ClaimHTTPServer((listen_bind or bind, receipt['claim_port']),
                           ExpiringClaim(state, job['expires_unix']),
                           receipt_signing_key=receipt_signing_key)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('policy', 'image', 'job-signing-key', 'job-verification-key',
                 'receipt-signing-key', 'receipt-verification-key', 'state-dir'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--source-server', required=True)
    parser.add_argument('--source-export', required=True)
    parser.add_argument('--claim-port', required=True, type=int)
    parser.add_argument('--valid-seconds', type=int, default=1800)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    result = prepare(policy_path=args.policy, image_path=args.image,
                     job_signing_key=args.job_signing_key,
                     job_verification_key=args.job_verification_key,
                     receipt_signing_key=args.receipt_signing_key,
                     receipt_verification_key=args.receipt_verification_key,
                     state_dir=args.state_dir, source_server=args.source_server,
                     source_export=args.source_export, claim_port=args.claim_port,
                     valid_seconds=args.valid_seconds, execute=args.execute,
                     preflight_only=args.preflight_only)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
