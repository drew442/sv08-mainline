#!/usr/bin/env python3
"""Private, bounded bundle intake for a future authenticated update service.

No network endpoint or installer. Intake admission orders ledger → state → upload,
then retains only upload through receipt; never reacquire ledger/state under upload.
Legacy explicit-digest callers may retain state. Callers authorize and verify. Directory ownership and a
lease prevent an ordinary application from replacing the verified upload. This
fills the project's staging gap; retire if upstream supplies equivalent intake.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import uuid
import ctypes

MIB = 1024 * 1024


class Staging:
    def __init__(self, root, max_bytes=1024*MIB, reserve_bytes=768*MIB, owner_uid=0):
        self.root = Path(root).absolute()
        self.max_bytes, self.reserve_bytes = max_bytes, reserve_bytes
        # owner_uid is injectable for unprivileged tests, not a service option.
        self.owner_uid = owner_uid
        self.lease_fd = None
        if type(max_bytes) is not int or max_bytes <= 0 or type(reserve_bytes) is not int or reserve_bytes < 0:
            raise ValueError('Invalid staging limits')
        for path in (*reversed(self.root.parents), self.root):
            entry = path.lstat()
            if (not stat.S_ISDIR(entry.st_mode) or entry.st_uid not in (0, owner_uid) or
                    entry.st_mode & 0o022):
                raise ValueError('Staging ancestry must be owned and not writable by other users')
        entry = self.root.stat()
        if entry.st_uid != owner_uid or stat.S_IMODE(entry.st_mode) != 0o700:
            raise ValueError('Staging directory must be private and owned by the coordinator')

    @contextmanager
    def locked(self):
        # Do not unlink the lock: its inode is the shared exclusion boundary.
        fd = os.open(self.root / '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            entry = os.fstat(fd)
            if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != self.owner_uid or
                    entry.st_nlink != 1 or stat.S_IMODE(entry.st_mode) != 0o600):
                raise ValueError('Invalid staging lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            previous = self.lease_fd
            self.lease_fd = fd
            try: yield
            finally: self.lease_fd = previous
        finally:
            os.close(fd)

    def sync(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def path(self, digest):
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Expected a complete SHA-256 digest')
        return self.root / (digest + '.raucb')

    def verify_file(self, path, digest, verify):
        entry = path.lstat()
        if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != self.owner_uid or
                entry.st_nlink != 1 or stat.S_IMODE(entry.st_mode) != 0o400 or
                not 0 < entry.st_size <= self.max_bytes):
            raise ValueError('Invalid staged bundle ownership, mode or size')
        proof = verify(path)  # Must authenticate with the reviewed release keyring.
        if proof['bundle_sha256'] != digest:
            raise ValueError('Authenticated file digest differs from the uploaded digest')
        return proof

    def busy(self):
        try:
            with self.locked(): return False
        except BlockingIOError: return True

    def preflight(self, size):
        if type(size) is not int or not 0 < size <= self.max_bytes:
            raise ValueError('Upload exceeds the bundle budget')
        if any(path.name != '.lock' for path in self.root.iterdir()):
            raise ValueError('Resolve existing staged or interrupted uploads first')
        fs = os.statvfs(self.root)
        block = fs.f_frsize or fs.f_bsize
        allocated = ((size + block - 1) // block) * block
        if fs.f_bavail * block < allocated + self.reserve_bytes or fs.f_favail < 130:
            raise ValueError('Insufficient upload space or inodes')

    def receive(self, stream, size, digest, verify):
        self.path(digest)  # Preserve strict explicit-digest API.
        with self.locked():
            return self.receive_locked(stream, size, verify, digest)

    def receive_locked(self, stream, size, verify, digest=None):
        """Caller owns upload lease for entire call; never acquire higher locks."""
        self.preflight(size)
        temporary = self.root / ('.partial-' + uuid.uuid4().hex)
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as output:
                remaining, checksum = size, hashlib.sha256()
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not isinstance(chunk, bytes) or not chunk or len(chunk) > remaining:
                        raise ValueError('Truncated or invalid upload stream')
                    output.write(chunk); checksum.update(chunk); remaining -= len(chunk)
                if stream.read(1) != b'':
                    raise ValueError('Upload exceeds its declared length')
                output.flush(); os.fsync(output.fileno())
                os.fchmod(output.fileno(), 0o400); os.fsync(output.fileno())
            actual = checksum.hexdigest()
            if digest is not None and actual != digest:
                raise ValueError('Upload checksum mismatch')
            proof = self.verify_file(temporary, actual, verify)
            destination = self.path(actual)
            # Linux atomic no-replace publication leaves exactly one name even
            # under SIGKILL; link/unlink would leave uncleanable hardlink aliases.
            libc = ctypes.CDLL(None, use_errno=True)
            rename = getattr(libc, 'renameat2', None)
            if rename is None: raise ValueError('Atomic no-replace publication unavailable')
            if rename(-100, os.fsencode(temporary), -100, os.fsencode(destination), 1) != 0:
                error = ctypes.get_errno()
                raise OSError(error, os.strerror(error))
            self.sync()
            return destination, proof
        finally:
            temporary.unlink(missing_ok=True)
            self.sync()

    @contextmanager
    def lease(self, digest, verify):
        """Hold through installation; caller also holds the transaction state lock."""
        with self.locked():
            path = self.path(digest)
            yield path, self.verify_file(path, digest, verify)

    def discard(self, name, can_discard):
        """Explicit cleanup only after the caller excludes live transactions.

        Hold the state lock before calling. Never discard a bundle that an armed
        or interrupted transaction still needs for diagnosis/reconciliation.
        """
        if not isinstance(name, str) or not re.fullmatch(r'(?:[0-9a-f]{64}\.raucb|\.partial-[0-9a-f]{32})', name):
            raise ValueError('Not a managed upload filename')
        with self.locked():
            path = self.root / name
            entry = path.lstat()
            if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != self.owner_uid or
                    entry.st_nlink != 1 or stat.S_IMODE(entry.st_mode) not in (0o400, 0o600)):
                raise ValueError('Refusing cleanup of an unexpected upload object')
            if can_discard() is not True:
                raise ValueError('Transaction reconciliation has not authorized cleanup')
            path.unlink()
            self.sync()
