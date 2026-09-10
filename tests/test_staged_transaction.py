from contextlib import contextmanager
import fcntl
import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_staging import Staging
from sv08_state import Store
from sv08_transaction import Transaction
from test_transaction import Backend


class StagedTransactionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='.sv08-transaction-', dir=Path.home())
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        upload = self.root / 'uploads'; upload.mkdir(mode=0o700)
        self.staging = Staging(upload, reserve_bytes=0, owner_uid=os.getuid())
        self.store = Store(self.root / 'state', reserve_bytes=0)
        self.store.initialize()
        self.boot = self.store.prepare_boot('A', 'release-1')
        self.boot['boot_id'] = 'boot-1'
        self.events = []
        self.payload = b'offline fixture, not a signed bundle'
        self.digest = hashlib.sha256(self.payload).hexdigest()
        with self.store.locked():
            self.staging.receive(io.BytesIO(self.payload), len(self.payload), self.digest, self.verify)
        self.events.clear()
        self.backend = Backend()
        self.transaction = Transaction(self.store, self.backend, self.admission)

    def verify(self, path):
        self.events.append('verify')
        # Actual signatures are covered by the separate real RAUC fixtures.
        return dict(release='release-2', bundle_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def assert_locks(self):
        with (self.store.root / '.lock').open('rb') as stream:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with self.assertRaises(BlockingIOError):
            with self.staging.locked(): pass

    @contextmanager
    def admission(self):
        self.events.append('admission')
        self.assert_locks()
        yield
        self.assert_locks()
        self.events.append('release-admission')

    def stage(self):
        return self.transaction.stage_upload(self.staging, self.digest, self.verify,
                                             self.boot, automatic=True)

    def test_authentication_precedes_admission_and_lease_spans_install(self):
        original = self.backend.install
        def install(bundle, proof, target):
            self.assert_locks()
            self.assertEqual(bundle, self.staging.path(self.digest))
            self.assertEqual(proof['bundle_sha256'], self.digest)
            self.events.append('install')
            with self.assertRaises(BlockingIOError):
                self.staging.discard(bundle.name, lambda: True)
            original(bundle, proof, target)
        with patch.object(self.backend, 'install', side_effect=install): self.stage()
        self.assertEqual(self.events, ['verify', 'admission', 'install', 'release-admission'])
        self.assertEqual(self.transaction.load()['phase'], 'staged')
        self.assertEqual(self.backend.primary(), 'A')
        with self.staging.locked(): pass  # Lease released after publication.

    def test_bad_signature_never_admits_or_journals(self):
        with patch.object(self, 'verify', side_effect=ValueError('untrusted signature')):
            with self.assertRaisesRegex(ValueError, 'signature'): self.stage()
        self.assertEqual(self.events, [])
        self.assertIsNone(self.transaction.load())
        self.assertEqual(self.backend.calls, [])

    def test_opt_out_precedes_upload_verification(self):
        self.store.policy(auto_update=False)
        with self.assertRaisesRegex(ValueError, 'disabled'): self.stage()
        self.assertEqual(self.events, [])
        self.assertIsNone(self.transaction.load())

    def test_failed_install_retains_upload_and_journal_but_releases_lease(self):
        with patch.object(self.backend, 'install', side_effect=OSError('interrupted write')):
            with self.assertRaisesRegex(OSError, 'interrupted'): self.stage()
        self.assertEqual(self.transaction.load()['phase'], 'installing')
        self.assertEqual(self.staging.path(self.digest).read_bytes(), self.payload)
        with self.staging.locked(): pass
        self.assertEqual(self.backend.primary(), 'A')
