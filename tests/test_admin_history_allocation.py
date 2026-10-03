from test_data_budget import fixture_root
"""Real processes share a leaf exclusion; default reserves remain real."""
from io import BytesIO
import hashlib
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest
from sv08_admin_history import History
from sv08_admin_jobs import Jobs
from sv08_data_budget import Budget
from sv08_staging import Staging
from sv08_state import Store, atomic_json
from test_admin_history import receipt


def _upload(root, ready, resume):
    root=Path(root);payload=b'fixture allocation'*1024
    class Stream(BytesIO):
        def read(self,size=-1):
            if self.tell()==0:ready.set();assert resume.wait(5)
            return super().read(size)
    staging=Staging(root/'uploads',owner_uid=os.geteuid(),budget=Budget(root))
    sha=hashlib.sha256(payload).hexdigest()
    staging.receive(Stream(payload),len(payload),sha,lambda path:dict(bundle_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))


def _copy(root,ready,resume):
    import sv08_state
    original=sv08_state.snapshot
    def snapshot(*args):ready.set();assert resume.wait(5);return original(*args)
    sv08_state.snapshot=snapshot
    Store(root,budget=Budget(root)).prepare_boot('B','release-2')


class AllocationTests(unittest.TestCase):
    def test_upload_copy_and_history_actual_default_reserves(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
            root=Path(tmp)/'sv08';store=Store(root);store.initialize();store.prepare_boot('A','release-1')
            uploads=root/'uploads';uploads.mkdir(mode=0o700)
            jobs=Jobs(root/'admin-image-jobs','fixture',lambda i:None,budget=store.budget);jobs.root.mkdir(mode=0o700)
            rows=[receipt(i) for i in range(128)];atomic_json(jobs.root/'jobs.json',rows)
            # Stage only the state-copy announcement, no RAUC/backend/device operation.
            store.expect_trial('B','release-2','A')
            context=multiprocessing.get_context('spawn')
            for operation in (_upload,_copy):
                ready=context.Event();resume=context.Event();child=context.Process(target=operation,args=(str(root),ready,resume));child.start()
                try:
                    self.assertTrue(ready.wait(5));start=time.monotonic()
                    with self.assertRaisesRegex(ValueError,'allocation is busy'):History(jobs).apply(History(jobs).review())
                    self.assertLess(time.monotonic()-start,.5);self.assertEqual(jobs.load(),rows)
                    self.assertFalse((jobs.root/'history-format-v2.lock').exists())
                    if operation is _upload:
                        with self.assertRaisesRegex(ValueError,'allocation is busy'):store.prepare_boot('B','release-2')
                    resume.set();child.join(5);self.assertEqual(child.exitcode,0)
                finally:
                    if child.is_alive():child.kill();child.join(5)
            History(jobs).apply(History(jobs).review());self.assertEqual(jobs.load(),rows)
            self.assertTrue(list(uploads.glob('*.raucb')))
            committed=(jobs.root/'jobs.json').read_bytes();inode=(jobs.root/'ledger.lock').stat().st_ino
            store.prepare_boot('A','release-1')
            self.assertEqual((jobs.root/'jobs.json').read_bytes(),committed)
            self.assertEqual((jobs.root/'ledger.lock').stat().st_ino,inode)
