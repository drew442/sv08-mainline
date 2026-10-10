"""Controlled shutdown policy fixtures; no service or hardware commands."""
import json
from pathlib import Path
import tempfile
import unittest
from test_data_budget import fixture_budget, fixture_root
from sv08_state import Store, atomic_json
from sv08_restart import (clear, intent, publish, require_running, require_restart,
                          start_admitted)
from sv08_transaction import Transaction
from test_transaction import Backend, admitted


class RestartTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=fixture_root())
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.runtime = root/'run'; self.runtime.mkdir()
        self.boot_id = root/'boot-id'; self.boot_id.write_text('boot-1')
        self.store = Store(root/'data', reserve_bytes=0, budget=fixture_budget(),
                           runtime=self.runtime, boot_id=self.boot_id)
        self.store.initialize()
        self.boot = self.store.prepare_boot('A', 'release-1', release_revision=1)
        self.boot['boot_id'] = 'boot-1'
        atomic_json(self.runtime/'boot.json', self.boot)
        self.backend = Backend()
        self.transaction = Transaction(self.store, self.backend, admitted)

    def stage(self):
        self.transaction.stage('bundle', dict(release='release-2', release_revision=2, signer_trusted=True, bundle_sha256='a'*64), self.boot)

    def test_shutdown_intent_closes_start_and_policy_until_new_boot(self):
        expected = publish(self.runtime, self.boot_id)
        for operation in (lambda: require_running(self.runtime, self.boot_id),
                          lambda: self.store.policy(mode='writable'),
                          lambda: self.store.policy(auto_update=False),
                          lambda: self.store.expect_trial('B', 'release-2', 'A')):
            with self.assertRaisesRegex(ValueError, 'shutdown'): operation()
        with self.assertRaisesRegex(ValueError, 'shutdown'), start_admitted(self.runtime, self.boot_id): pass
        self.assertEqual(intent(self.runtime, self.boot_id), expected)
        # Read-only policy/status observation remains available.
        self.assertEqual(self.store.policy()['requested_mode'], 'immutable')
        self.boot_id.write_text('boot-2')
        require_running(self.runtime, self.boot_id)
        with start_admitted(self.runtime, self.boot_id): pass
        self.store.policy(auto_update=False)
        replacement = publish(self.runtime, self.boot_id)
        self.assertNotEqual(replacement['id'], expected['id'])
        clear(self.runtime, replacement, self.boot_id)
        self.assertFalse((self.runtime/'shutdown.json').exists())

    def test_invalid_or_changed_intent_fails_closed(self):
        path = self.runtime/'shutdown.json'
        path.write_text('{')
        with self.assertRaises(ValueError): require_running(self.runtime, self.boot_id)
        path.unlink()
        first = publish(self.runtime, self.boot_id)
        changed = dict(first, id='f'*32); atomic_json(path, changed)
        with self.assertRaisesRegex(ValueError, 'changed'): clear(self.runtime, first, self.boot_id)
        self.assertEqual(intent(self.runtime, self.boot_id), changed)
        path.unlink(); path.symlink_to(self.boot_id)
        with self.assertRaisesRegex(ValueError, 'Invalid'): require_running(self.runtime, self.boot_id)

    def test_start_barrier_serializes_admission(self):
        with start_admitted(self.runtime, self.boot_id):
            with self.assertRaises(BlockingIOError), start_admitted(self.runtime, self.boot_id): pass

    def test_staged_and_coherently_armed_restarts_preserve_next_boot_selection(self):
        self.stage()
        with self.store.locked(): require_restart(self.store)
        before = self.transaction.load()
        with self.assertRaisesRegex(ValueError, 'pending'): self.store.policy(mode='writable')
        self.transaction.arm(self.boot)
        with self.store.locked(): require_restart(self.store)
        self.assertEqual(self.backend.primary(), 'B')
        self.assertEqual(self.transaction.load()['id'], before['id'])
        self.assertEqual(self.transaction.load()['phase'], 'armed')
        state = self.store.load(); state['pending']['release'] = 'different'; self.store.save(state)
        with self.store.locked(), self.assertRaisesRegex(ValueError, 'reconciliation'): require_restart(self.store)

    def test_transitional_old_boot_or_customized_arm_is_refused(self):
        self.stage()
        tx = self.transaction.load()
        for phase in ('preparing', 'installing', 'arming', 'confirming'):
            self.transaction.save(tx, phase)
            with self.store.locked(), self.assertRaisesRegex(ValueError, 'transitional'): require_restart(self.store)
        self.transaction.save(tx, 'staged')
        self.boot_id.write_text('boot-2')
        with self.store.locked(), self.assertRaisesRegex(ValueError, 'earlier boot'): require_restart(self.store)
        self.boot_id.write_text('boot-1')
        self.transaction.arm(self.boot)
        state = self.store.load(); state['slots']['A']['customized'] = True; self.store.save(state)
        with self.store.locked(), self.assertRaisesRegex(ValueError, 'reconciliation'): require_restart(self.store)

    def test_uncertain_package_receipts_and_service_policy_block_mode_and_restart(self):
        root = self.store.root/'software/jobs'; root.mkdir(parents=True)
        path = root/'job.json'
        for status in ('queued', 'running', 'unknown'):
            atomic_json(path, dict(status=status))
            with self.store.locked(), self.assertRaisesRegex(ValueError, 'software job'): require_restart(self.store)
            with self.assertRaisesRegex(ValueError, 'software job'): self.store.policy(mode='writable')
        for status in ('completed', 'failed', 'acknowledged'):
            atomic_json(path, dict(status=status))
            with self.store.locked(): require_restart(self.store)
        atomic_json(root/'job.policy.json', {})
        with self.store.locked(), self.assertRaisesRegex(ValueError, 'service policy'): require_restart(self.store)
        (root/'job.policy.json').unlink()
        history = self.store.root/'customizations'; history.mkdir()
        atomic_json(history/'legacy.json', dict(status='started'))
        with self.store.locked(), self.assertRaisesRegex(ValueError, 'package operation'): require_restart(self.store)

    def test_image_transaction_cannot_start_after_reboot_queue(self):
        publish(self.runtime, self.boot_id)
        with self.assertRaisesRegex(ValueError, 'shutdown'): self.stage()
        self.assertEqual(self.backend.calls, [])
        self.assertFalse(self.transaction.path.exists())

    def test_all_managed_starts_use_same_gate(self):
        root = Path(__file__).resolve().parents[1]/'configs/host-os/systemd'
        for name in ('klipper', 'moonraker', 'mainsail', 'web-prepare', 'web-auth', 'printer-api'):
            with self.subTest(unit=name):
                self.assertIn('/usr/bin/python3 /usr/lib/sv08/sv08_restart.py check-start',
                              (root/('sv08-'+name+'.service')).read_text())
