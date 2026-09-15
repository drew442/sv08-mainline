import hashlib
import os
from pathlib import Path
import sys
from unittest.mock import patch

from test_admin_images import ImageAdministrationTests
from test_transaction import admitted
from sv08_admin_jobs import Jobs, LIMIT


class ImageResolutionTests(ImageAdministrationTests):
    def setUp(self):
        super().setUp()
        self.boot['boot_id'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.launches = []
        self.jobs = Jobs(self.store.root / 'admin-image-jobs', self.boot['boot_id'], self.launches.append)
        self.controller.jobs = self.jobs
        self.service = {'owner': ':1.41', 'package': '1.15.2-0sv08.1', 'busy_guard': 'GetSlotStatus'}
        self.backend.writer = admitted
        self.backend.resolution_evidence = lambda boot: dict(self.service)
        self.jobs.worker_evidence = lambda identity: {
            'LoadState': 'loaded', 'ActiveState': 'failed', 'SubState': 'failed',
            'InvocationID': 'a'*32, 'MainPID': '0',
            'ExecMainStartTimestampMonotonic': '1', 'ExecMainExitTimestampMonotonic': '2', 'Result': 'signal',
        }

    def interrupted(self, identity='1'*32):
        plan = self.controller.plan('image.stage', {'digest': self.digest})
        self.jobs.submit(identity, plan, self.controller)
        with self.jobs.lock('ledger.lock'):
            rows = self.jobs.load(); rows[0].update(phase='interrupted', message='Outcome uncertain.')
            self.jobs.save(rows)
        return plan

    def inspect(self, identity='1'*32):
        return self.controller.request({'method': 'image.inspect', 'id': identity})

    def dispose(self, plan):
        return self.controller.request({'method': 'image.dispose', 'plan': plan})

    def test_review_is_observation_then_durable_unknown_disposition(self):
        self.interrupted()
        before = (self.jobs.root / 'jobs.json').read_bytes()
        with patch('sv08_transaction.Transaction.reconcile', side_effect=AssertionError('must not reconcile')):
            review = self.inspect()
        self.assertEqual((self.jobs.root / 'jobs.json').read_bytes(), before)
        self.assertEqual(review['plan']['kind'], 'retain-unknown-v1')
        self.assertEqual(review['receipt']['phase'], 'interrupted')
        result = self.dispose(review['plan'])
        self.assertEqual(result['phase'], 'interrupted')
        self.assertIn('unknown', result['message'])
        self.assertFalse(self.jobs.history()['blocked'])
        stored = self.jobs.load()[0]
        self.assertEqual(stored['disposition']['outcome'], 'unknown')
        self.assertEqual(stored['disposition']['evidence']['original_sha256'],
                         hashlib.sha256(__import__('json').dumps({k:v for k,v in stored.items() if k != 'disposition'}, sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    def test_disposition_retry_is_idempotent_and_changed_review_refuses(self):
        self.interrupted(); review = self.inspect(); first = self.dispose(review['plan'])
        self.assertEqual(self.dispose(review['plan']), first)
        changed = dict(review['plan'], evidence_sha256='f'*64)
        with self.assertRaisesRegex(ValueError, 'different review'):
            self.dispose(changed)

    def test_changed_or_unavailable_evidence_refuses_without_publication(self):
        self.interrupted(); review = self.inspect()
        self.service['owner'] = ':1.42'
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            self.dispose(review['plan'])
        self.assertNotIn('disposition', self.jobs.load()[0])
        self.jobs.worker_evidence = lambda _: (_ for _ in ()).throw(ValueError('Image worker is active'))
        with self.assertRaisesRegex(ValueError, 'worker is active'):
            self.inspect()
        self.assertNotIn('disposition', self.jobs.load()[0])

    def test_publication_failure_leaves_unknown_receipt_and_can_retry(self):
        self.interrupted(); review = self.inspect(); save = self.jobs.save
        with patch.object(self.jobs, 'save', side_effect=OSError('No space left on device')):
            with self.assertRaisesRegex(OSError, 'No space'):
                self.dispose(review['plan'])
        self.assertNotIn('disposition', self.jobs.load()[0])
        self.assertEqual(self.dispose(review['plan'])['phase'], 'interrupted')

    def test_full_history_can_retain_existing_unknown_but_not_admit_new_identity(self):
        self.interrupted()
        with self.jobs.lock('ledger.lock'):
            original = self.jobs.load()[0]
            terminal = dict(original, phase='refused', message='Earlier reviewed refusal.')
            rows = [original] + [dict(terminal, id=f'{value:032x}') for value in range(1, LIMIT)]
            self.jobs.save(rows)
        review = self.inspect(); self.dispose(review['plan'])
        self.assertFalse(self.jobs.history()['blocked'])
        plan = self.controller.plan('image.stage', {'digest': self.digest})
        with self.assertRaisesRegex(ValueError, 'history is full'):
            self.jobs.submit('f'*32, plan, self.controller)

    def test_legacy_receipt_without_disposition_remains_readable(self):
        self.interrupted()
        self.assertEqual(self.jobs.load()[0]['phase'], 'interrupted')
        self.assertNotIn('disposition', self.jobs.load()[0])
