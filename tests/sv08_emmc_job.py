#!/usr/bin/env python3
"""Single-use claim service used only by the disposable QEMU eMMC writer."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import fcntl
import hashlib
import json
import os
from pathlib import Path
import threading
import time


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def write_all(fd, payload):
    view = memoryview(payload)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise OSError('short state write')
        view = view[count:]


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class ClaimState:
    """An armed token is durably replaced by one claim; ambiguous state refuses."""

    def __init__(self, state_dir, descriptor):
        self.state_dir = Path(state_dir)
        self.descriptor = descriptor
        self.descriptor_bytes = canonical_json(descriptor)
        self.descriptor_sha256 = sha256_bytes(self.descriptor_bytes)
        self.job_id = descriptor['job_id']
        self.armed = self.state_dir / 'armed.json'
        self.claimed = self.state_dir / 'claim.json'
        self.lock_path = self.state_dir / '.lock'
        self.lock = threading.Lock()
        self.last_claim_ms = None

    @classmethod
    def arm_new(cls, state_dir, descriptor):
        state_dir = Path(state_dir)
        state_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
        instance = cls(state_dir, descriptor)
        lock_fd = os.open(instance.lock_path, os.O_RDWR | os.O_CREAT | os.O_EXCL |
                          os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        os.fsync(lock_fd)
        os.close(lock_fd)
        fd = os.open(instance.armed, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            write_all(fd, instance.descriptor_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)
        fsync_directory(state_dir)
        return instance

    @classmethod
    def reopen(cls, state_dir, descriptor):
        instance = cls(state_dir, descriptor)
        if instance.lock_path.is_symlink() or not instance.lock_path.is_file():
            raise ValueError('missing or invalid claim lock; fail closed')
        # Any existing claim, including a malformed/partial one, consumes the
        # job. Missing both state files is corruption, not a fresh arm.
        if not instance.armed.exists() and not instance.claimed.exists():
            raise ValueError('missing claim state; fail closed')
        if instance.armed.exists():
            if instance.armed.is_symlink() or instance.armed.read_bytes() != instance.descriptor_bytes:
                raise ValueError('armed descriptor changed; fail closed')
        return instance

    def consume(self, request):
        started = time.monotonic()
        if not isinstance(request, dict) or set(request) != {'job_id', 'descriptor_sha256'}:
            return 400, b'REFUSED malformed request\n'
        if request['job_id'] != self.job_id or request['descriptor_sha256'] != self.descriptor_sha256:
            return 409, b'REFUSED stale descriptor\n'
        with self.lock:
            lock_fd = os.open(self.lock_path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
                if self.armed.is_symlink() or self.claimed.is_symlink():
                    return 503, b'UNCERTAIN state symlink\n'
                if self.claimed.exists():
                    return 409, b'CONSUMED\n'
                if {item.name for item in self.state_dir.iterdir()} - {'armed.json', '.lock'}:
                    return 503, b'REFUSED unexpected claim state\n'
                if not self.armed.exists() or self.armed.read_bytes() != self.descriptor_bytes:
                    return 503, b'REFUSED invalid claim state\n'
                payload = canonical_json({
                    'job_id': self.job_id,
                    'descriptor_sha256': self.descriptor_sha256,
                    'state': 'consumed-before-write',
                })
                fd = os.open(self.claimed, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                             os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
                try:
                    write_all(fd, payload)
                    os.fsync(fd)
                finally:
                    os.close(fd)
                fsync_directory(self.state_dir)
                # Once claim.json is synced, deleting armed.json is cleanup;
                # even a crash before cleanup is interpreted as consumed.
                self.armed.unlink()
                fsync_directory(self.state_dir)
                self.last_claim_ms = (time.monotonic() - started) * 1000
                return 200, f'CLAIMED {self.job_id} {self.descriptor_sha256}\n'.encode()
            except FileExistsError:
                return 409, b'CONSUMED\n'
            except (OSError, ValueError):
                # Never remove a partially persisted claim or restore armed.
                return 503, b'UNCERTAIN state persistence\n'
            finally:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                finally:
                    os.close(lock_fd)


class ClaimHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address, claim_state, *, drop_first_ack=False):
        self.claim_state = claim_state
        self.drop_first_ack = drop_first_ack
        self._dropped = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *_args):
                pass

            def do_POST(self):
                if self.path != '/claim':
                    self.send_error(404)
                    return
                try:
                    length = int(self.headers.get('Content-Length', '-1'))
                    if not 0 <= length <= 4096:
                        raise ValueError('bad request length')
                    raw = self.rfile.read(length)
                    request = json.loads(raw)
                except (ValueError, json.JSONDecodeError):
                    status, payload = 400, b'REFUSED malformed request\n'
                else:
                    status, payload = owner.claim_state.consume(request)
                if owner.drop_first_ack and not owner._dropped and status == 200:
                    owner._dropped = True
                    self.close_connection = True
                    return
                reason = {200: 'OK', 400: 'Bad Request', 409: 'Conflict', 503: 'Service Unavailable'}.get(status, 'Error')
                self.send_response(status, reason)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(payload)
                self.close_connection = True

        super().__init__(address, Handler)


def make_descriptor(*, job_id, source_bytes, source_sha256, target_serial,
                    target_bytes, image_bytes, image_sha256, gpt):
    return {
        'format': 'sv08-qemu-emmc-job-v1',
        'job_id': job_id,
        'source': {'bytes': source_bytes, 'sha256': source_sha256,
                   'mode': 'read-only-nfs'},
        'target': {'identity': target_serial, 'bytes': target_bytes,
                   'mode': 'synthetic-qemu-only'},
        'image': {'bytes': image_bytes, 'sha256': image_sha256,
                  'layout': gpt},
    }
