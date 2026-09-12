import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from test_admin_images import ImageAdministrationTests
from sv08_admin_jobs import Jobs, LIMIT, launch


class ImageJobTests(ImageAdministrationTests):
    def setUp(self):
        super().setUp()
        self.launches = []
        self.jobs = Jobs(self.store.root / 'admin-image-jobs', self.boot['boot_id'], self.launches.append)
        self.controller.jobs = self.jobs

    def submit(self, identity='1'*32, action='image.stage'):
        plan = self.controller.plan(action, {'digest': self.digest} if action == 'image.stage' else {})
        return self.jobs.submit(identity, plan, self.controller), plan

    def test_stage_arm_cancel_and_duplicate_ack(self):
        row, plan = self.submit()
        self.assertEqual(row['phase'], 'queued')
        self.assertEqual(self.jobs.submit(row['id'], plan, self.controller)['id'], row['id'])
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'succeeded')
        self.assertEqual(self.backend.calls.count('install'), 1)
        self.jobs.submit(row['id'], plan, self.controller)
        self.assertEqual(self.launches, [row['id']])
        self.submit('2'*32, 'image.arm'); self.jobs.work(lambda: self.controller)
        self.assertEqual(self.backend.primary(), 'B')
        # Cancellation remains admitted from a safe source after customization.
        state = self.store.load(); state['slots']['A']['customized'] = True; self.store.save(state)
        self.submit('3'*32, 'image.cancel'); self.jobs.work(lambda: self.controller)
        self.assertEqual(self.backend.primary(), 'A')

    def test_conflicting_content_and_exclusion(self):
        row, plan = self.submit()
        other = dict(plan, arguments={'digest': 'a'*64})
        with self.assertRaisesRegex(ValueError, 'different review'): self.jobs.submit(row['id'], other, self.controller)
        with self.assertRaisesRegex(ValueError, 'pending'): self.jobs.submit('2'*32, plan, self.controller)
        self.assertEqual(self.launches, [row['id']])

    def test_capacity_never_evicts_retry_identity(self):
        row, plan = self.submit(); self.jobs.work(lambda: self.controller)
        with self.jobs.lock('ledger.lock'):
            original = self.jobs.load()[0]
            self.jobs.save([dict(original, id=f'{i:032x}') for i in range(LIMIT)])
        self.assertEqual(self.jobs.submit('0'*32, plan, self.controller)['phase'], 'succeeded')
        with self.assertRaisesRegex(ValueError, 'full'): self.jobs.submit('f'*32, plan, self.controller)
        self.assertEqual(len(self.jobs.history()['jobs']), LIMIT)

    def test_launch_uncertainty_is_never_replayed(self):
        self.jobs.launcher = lambda _: (_ for _ in ()).throw(subprocess.TimeoutExpired('systemctl', 15))
        row, plan = self.submit()
        self.assertEqual(row['phase'], 'interrupted')
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.backend.calls, [])
        self.assertEqual(self.jobs.submit(row['id'], plan, self.controller)['phase'], 'interrupted')

    def test_stale_and_changed_boot_refuse_without_backend_mutation(self):
        self.submit(); self.store.policy(auto_update=False)
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'refused')
        self.assertEqual(self.backend.calls, [])
        self.submit('2'*32); self.jobs.boot_id = 'new-boot'
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'interrupted')
        self.assertEqual(self.backend.calls, [])

    def test_capability_revalidated_and_signed_lease_still_used(self):
        self.submit(); self.backend.manifest['deployable'] = False
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'refused')
        self.backend.manifest['deployable'] = True
        self.submit('2'*32)
        os.chmod(self.staging.path(self.digest), 0o600)
        self.staging.path(self.digest).write_bytes(b'corrupt upload')
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'interrupted')
        self.assertEqual(self.backend.calls, [])

    def test_worker_crash_after_running_publication_is_observable(self):
        self.submit()
        with self.assertRaises(SystemExit): self.jobs.work(lambda: (_ for _ in ()).throw(SystemExit(7)))
        self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'interrupted')
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.backend.calls, [])

    def test_result_publication_failure_does_not_repeat_install(self):
        self.submit(); save = self.jobs.save
        def fail_result(rows):
            if rows[-1]['phase'] == 'succeeded': raise OSError('No space left on device')
            save(rows)
        with patch.object(self.jobs, 'save', side_effect=fail_result):
            with self.assertRaises(OSError): self.jobs.work(lambda: self.controller)
        self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'interrupted')
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.backend.calls.count('install'), 1)

    def test_initial_publication_failure_never_launches(self):
        with patch.object(self.jobs, 'save', side_effect=OSError('No space left on device')):
            with self.assertRaises(OSError): self.submit()
        self.assertEqual(self.launches, [])
        self.assertEqual(self.backend.calls, [])

    def test_corrupt_record_and_unsafe_directory_refuse(self):
        self.submit()
        (self.jobs.root / 'jobs.json').write_text('{}')
        with self.assertRaises(ValueError): self.jobs.history()
        os.chmod(self.jobs.root, 0o755)
        with self.assertRaisesRegex(ValueError, 'private'): self.jobs.history()

    def test_fixed_launch_and_rpc_no_synchronous_bypass(self):
        with patch('sv08_admin_jobs.subprocess.run') as run:
            launch('a'*32)
            self.assertEqual(run.call_args.args[0], ['/usr/bin/systemctl', 'start', '--no-block', 'sv08-admin-image-worker@'+'a'*32+'.service'])
            with self.assertRaises(ValueError): launch('x; touch /tmp/unwanted')
        plan = self.controller.plan('image.stage', {'digest': self.digest})
        with self.assertRaisesRegex(ValueError, 'retry identity'): self.controller.request(dict(method='apply', plan=plan))
        self.assertEqual(self.controller.request(dict(method='jobs'))['jobs'], [])

    def test_unclaimed_queue_expires_and_never_executes(self):
        row, plan = self.submit()
        queued = self.jobs.load()[0]['queued_at']
        with patch('sv08_admin_jobs.time.monotonic', return_value=queued+31):
            self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'interrupted')
            self.assertEqual(self.jobs.submit(row['id'], plan, self.controller)['phase'], 'interrupted')
            self.jobs.work(lambda: self.controller)
        self.assertEqual(self.jobs.load()[0]['phase'], 'interrupted')
        self.assertEqual(self.backend.calls, [])

    def test_instance_cannot_claim_another_receipt(self):
        self.submit()
        self.jobs.work(lambda: self.controller, '2'*32)
        self.assertEqual(self.jobs.load()[0]['phase'], 'queued')
        self.assertEqual(self.backend.calls, [])

    def test_writable_and_idle_race_refuse_before_mutation(self):
        self.submit()
        state = self.store.load(); state['requested_mode'] = 'writable'; self.store.save(state)
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'refused')
        state['requested_mode'] = 'immutable'; self.store.save(state)
        self.submit('2'*32)
        self.adapter.admission = lambda: (_ for _ in ()).throw(ValueError('Printer is busy'))
        self.jobs.work(lambda: self.controller)
        self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'interrupted')
        self.assertEqual(self.backend.calls, [])

    def test_concurrent_process_submissions_admit_once(self):
        import multiprocessing
        row, plan = self.submit()
        # Distinct OS processes see the same durable identity after lost ACK.
        context = multiprocessing.get_context('fork')
        queue = context.Queue()
        def retry(identity):
            try: queue.put(self.jobs.submit(identity, plan, self.controller)['id'])
            except ValueError: queue.put('rejected')
        workers = [context.Process(target=retry, args=(identity,)) for identity in (row['id'], '2'*32)]
        for worker in workers: worker.start()
        for worker in workers: worker.join(5); self.assertEqual(worker.exitcode, 0)
        self.assertCountEqual([queue.get(timeout=1), queue.get(timeout=1)], [row['id'], 'rejected'])
        self.assertEqual(len(self.jobs.load()), 1)

    def test_real_worker_killed_inside_transaction_is_not_replayed(self):
        import multiprocessing
        import time
        self.submit()
        context = multiprocessing.get_context('fork')
        entered = context.Event()
        def install(*_):
            entered.set()
            time.sleep(30)
        self.backend.install = install
        worker = context.Process(target=lambda: self.jobs.work(lambda: self.controller))
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            started = time.monotonic()
            self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'running')
            self.assertLess(time.monotonic()-started, .5)
            started = time.monotonic()
            with self.assertRaisesRegex(ValueError, 'busy'): self.controller.status()
            self.assertLess(time.monotonic()-started, .5)
            worker.kill(); worker.join(5)
            self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'interrupted')
            self.jobs.work(lambda: self.controller)
            with self.assertRaisesRegex(ValueError, 'pending'): self.submit('2'*32)
        finally:
            if worker.is_alive(): worker.kill(); worker.join(5)

    def test_coordinator_loss_after_publication_expires_without_launch(self):
        save = self.jobs.save
        def die(rows): save(rows); raise SystemExit(9)
        with patch.object(self.jobs, 'save', side_effect=die):
            with self.assertRaises(SystemExit): self.submit()
        self.assertEqual(self.launches, [])
        queued = self.jobs.load()[0]['queued_at']
        with patch('sv08_admin_jobs.time.monotonic', return_value=queued+31):
            self.assertEqual(self.jobs.history()['jobs'][0]['phase'], 'interrupted')
            self.jobs.work(lambda: self.controller)
        self.assertEqual(self.backend.calls, [])
