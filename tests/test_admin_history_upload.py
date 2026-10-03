"""Archive must not weaken upload raw-phase or artifact-dependency gates."""
import copy
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from sv08_admin import ACTIONS
from sv08_admin_history import History
from sv08_state import atomic_json
from test_admin_history import receipt, disposed
from test_admin_upload import UploadTests


class ArchivedUploadTests(unittest.TestCase):
    setUp = UploadTests.setUp
    receive = UploadTests.receive

    def fill(self, unknown=False, stage=False):
        rows=[receipt(i) for i in range(128)]
        if unknown:rows[0]=disposed(0)
        if stage:
            title,effect=ACTIONS['image.stage']
            rows[1]['plan']=dict(action='image.stage',arguments={'digest':self.digest},revision='b'*64,
                                  title=title,effect=effect,preserves_user_data=True)
        self.jobs.root.mkdir(mode=0o700,exist_ok=True);atomic_json(self.jobs.root/'jobs.json',rows)
        History(self.jobs).apply(History(self.jobs).review())
        return rows

    def test_disposed_archived_unknown_still_blocks_upload(self):
        rows=self.fill(unknown=True);History(self.jobs).apply(History(self.jobs).review())
        self.assertEqual(self.jobs.load(),rows)
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.u.plan('bundle',10)
        self.assertEqual(self.jobs.history()['jobs'][-1]['phase'],'interrupted')

    def test_archive_protects_stage_with_missing_failed_mismatched_journal(self):
        self.receive();rows=self.fill(stage=True);History(self.jobs).apply(History(self.jobs).review())
        name=self.digest+'.raucb'
        with self.assertRaisesRegex(ValueError,'Missing transaction'):self.u.cleanup_plan(name)
        for tx in (dict(phase='failed',bundle_sha256=self.digest),dict(phase='cancelled',bundle_sha256='f'*64)):
            atomic_json(self.store.root/'update.json',tx)
            with self.assertRaises((ValueError,KeyError)):self.u.cleanup_plan(name)
        self.assertTrue((self.staging.root/name).exists());self.assertEqual(self.jobs.load(),rows)

    def test_rollover_invalidates_cleanup_review_even_identical_rows(self):
        self.receive();self.fill()
        name=self.digest+'.raucb';plan=self.u.cleanup_plan(name)
        History(self.jobs).apply(History(self.jobs).review())
        with self.assertRaisesRegex(ValueError,'changed'):self.u.cleanup(plan)
        self.assertTrue((self.staging.root/name).exists())
