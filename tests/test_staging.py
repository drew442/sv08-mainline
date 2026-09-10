import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_staging import Staging


class StagingTests(unittest.TestCase):
    def setUp(self):
        # A private home child avoids treating world-writable /tmp as trusted.
        directory = tempfile.TemporaryDirectory(prefix='.sv08-staging-test-', dir=Path.home())
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.staging = Staging(self.root, max_bytes=4096, reserve_bytes=0, owner_uid=os.getuid())
        self.payload = b'fixture upload'
        self.digest = hashlib.sha256(self.payload).hexdigest()

    def verify(self, path):
        # Transport tests only; production must use sv08_bundle.inspect.
        return {'bundle_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def receive(self, data=None, size=None, digest=None, verify=None):
        return self.staging.receive(io.BytesIO(self.payload if data is None else data),
            len(self.payload) if size is None else size, digest or self.digest, verify or self.verify)

    def test_private_publish_and_exclusive_install_lease(self):
        path, proof = self.receive()
        self.assertEqual(path.read_bytes(), self.payload)
        self.assertEqual(path.stat().st_mode & 0o777, 0o400)
        with self.staging.lease(self.digest, self.verify) as leased:
            self.assertEqual(leased, (path, proof))
            with self.assertRaises(BlockingIOError):
                with self.staging.locked(): pass
        with self.assertRaisesRegex(ValueError, 'existing'):
            self.receive()

    def test_invalid_stream_or_digest_leaves_no_published_file(self):
        for kwargs in ({'data': b'x'}, {'data': self.payload+b'extra'}, {'digest': '0'*64}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.receive(**kwargs)
            self.assertEqual([p.name for p in self.root.iterdir()], ['.lock'])

    def test_signature_failure_never_publishes(self):
        def reject(path): raise ValueError('untrusted signature')
        with self.assertRaisesRegex(ValueError, 'signature'): self.receive(verify=reject)
        self.assertFalse(self.staging.path(self.digest).exists())
        self.assertFalse(list(self.root.glob('.partial-*')))

    def test_limits_and_space_refuse_before_read(self):
        stream = io.BytesIO(self.payload)
        fs = SimpleNamespace(f_frsize=4096, f_bsize=4096, f_bavail=0, f_favail=1000)
        with patch('sv08_staging.os.statvfs', return_value=fs):
            with self.assertRaisesRegex(ValueError, 'space'):
                self.staging.receive(stream, len(self.payload), self.digest, self.verify)
        self.assertEqual(stream.tell(), 0)
        for size in (0, -1, True, 4097):
            with self.assertRaises(ValueError): self.receive(size=size)

    def test_interrupted_upload_is_retained_for_explicit_resolution(self):
        stale = self.root / '.partial-interrupted'; stale.write_bytes(b'old')
        with self.assertRaisesRegex(ValueError, 'interrupted'): self.receive()
        self.assertEqual(stale.read_bytes(), b'old')

    def test_replaced_or_linked_bundle_is_refused(self):
        path, _ = self.receive()
        other = self.root / 'hardlink'; os.link(path, other)
        with self.assertRaisesRegex(ValueError, 'ownership'):
            with self.staging.lease(self.digest, self.verify): pass
        other.unlink(); path.unlink(); path.symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'ownership'):
            with self.staging.lease(self.digest, self.verify): pass

    def test_untrusted_directory_and_lock_refused(self):
        self.root.chmod(0o777)
        with self.assertRaisesRegex(ValueError, 'ancestry'):
            Staging(self.root, owner_uid=os.getuid())
        self.root.chmod(0o700)
        (self.root / '.lock').symlink_to('/etc/passwd')
        with self.assertRaises(OSError): self.receive()
        for digest in ('../x', 'a'*63, 'A'*64):
            with self.assertRaises(ValueError): self.staging.path(digest)

    def test_cleanup_requires_explicit_transaction_clearance(self):
        path, _ = self.receive()
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            self.staging.discard(path.name, lambda: False)
        self.assertTrue(path.exists())
        self.staging.discard(path.name, lambda: True)
        self.assertFalse(path.exists())
        partial = self.root / ('.partial-' + 'a'*32)
        partial.write_bytes(b'interrupted'); partial.chmod(0o600)
        self.staging.discard(partial.name, lambda: True)
        self.assertFalse(partial.exists())
        with self.assertRaisesRegex(ValueError, 'filename'):
            self.staging.discard('.lock', lambda: True)
