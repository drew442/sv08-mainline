from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_state import Store
from sv08_transaction import Transaction


class Backend:
    def __init__(self):
        self.selected = 'A'; self.states = {'A': True, 'B': False}; self.calls = []
    def validate_context(self, boot):
        pass
    def primary(self):
        return self.selected
    def good(self, slot):
        return self.states[slot]
    def install(self, bundle, proof, target):
        self.calls.append('install'); self.states[target] = False
    def mark_active(self, slot):
        self.calls.append('active'); self.selected = slot; self.states[slot] = True
    def mark_bad(self, slot):
        self.calls.append('bad'); self.states[slot] = False
        if self.selected == slot:
            self.selected = 'B' if slot == 'A' else 'A'
    def mark_good(self, slot):
        self.calls.append('good'); self.states[slot] = True


@contextmanager
def admitted():
    yield


class TransactionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name)/'state', reserve_bytes=0)
        self.store.initialize()
        self.boot = self.store.prepare_boot('A', 'release-1'); self.boot['boot_id'] = 'boot-1'
        self.backend = Backend(); self.tx = Transaction(self.store, self.backend, admitted)
        self.proof = dict(release='release-2', bundle_sha256='a'*64)

    def stage(self):
        return self.tx.stage('test-bundle', self.proof, self.boot)

    def trial(self):
        self.stage(); self.tx.arm(self.boot)
        boot = self.store.prepare_boot('B', 'release-2'); boot['boot_id'] = 'boot-2'
        return boot

    def test_stage_does_not_copy_state_or_select_target(self):
        self.stage()
        self.assertEqual(self.backend.primary(), 'A')
        self.assertIsNone(self.store.load()['pending'])
        self.assertNotIn('B', self.store.load()['slots'])

    def test_pending_is_durable_before_activation_and_arm_is_idempotent(self):
        self.stage()
        original = self.backend.mark_active
        def activate(slot):
            self.assertEqual(self.store.load()['pending']['slot'], slot)
            original(slot)
        self.backend.mark_active = activate
        self.tx.arm(self.boot); self.tx.arm(self.boot)
        self.assertEqual(self.backend.calls.count('active'), 1)

    def test_install_failure_remains_inspectable_and_can_cancel(self):
        with patch.object(self.backend, 'install', side_effect=OSError('power loss')):
            with self.assertRaises(OSError): self.stage()
        self.assertEqual(self.tx.load()['phase'], 'installing')
        with self.assertRaises(ValueError): self.stage()
        self.assertEqual(self.tx.cancel(self.boot)['phase'], 'cancelled')
        self.stage()

    def test_crash_after_boot_selection_can_resume_only_in_same_boot(self):
        self.stage(); original = self.tx.save
        def fail(tx, phase):
            if phase == 'armed': raise OSError('power loss')
            original(tx, phase)
        with patch.object(self.tx, 'save', side_effect=fail):
            with self.assertRaises(OSError): self.tx.arm(self.boot)
        self.assertEqual(self.backend.primary(), 'B')
        self.assertEqual(self.store.load()['pending']['phase'], 'armed')
        with self.assertRaises(ValueError): self.tx.arm(dict(self.boot, boot_id='reboot'))
        self.tx.arm(self.boot)
        self.assertEqual(self.tx.load()['phase'], 'armed')

    def test_fallback_disarms_before_clearing_journal(self):
        self.trial()
        boot = self.store.prepare_boot('A', 'release-1'); boot['boot_id'] = 'boot-3'
        self.assertEqual(self.tx.cancel(boot)['phase'], 'failed')
        self.assertFalse(self.backend.good('B'))
        self.assertEqual(self.backend.primary(), 'A')

    def test_failed_health_never_marks_good_or_releases_pending(self):
        boot = self.trial()
        with self.assertRaises(ValueError): self.tx.confirm(boot, lambda boot: False)
        self.assertNotIn('good', self.backend.calls)
        self.assertIsNotNone(self.store.load()['pending'])
        self.tx.confirm(boot, lambda boot: True)
        self.assertIsNone(self.store.load()['pending'])
        self.assertEqual(self.tx.load()['phase'], 'complete')

    def test_confirmation_crash_after_state_publication_is_retryable(self):
        boot = self.trial(); original = self.tx.save
        def fail(tx, phase):
            if phase == 'complete': raise OSError('power loss')
            original(tx, phase)
        with patch.object(self.tx, 'save', side_effect=fail):
            with self.assertRaises(OSError): self.tx.confirm(boot, lambda boot: True)
        self.assertIsNone(self.store.load()['pending'])
        self.assertEqual(self.tx.load()['phase'], 'confirming')
        self.tx.confirm(boot, lambda boot: True)
        self.assertEqual(self.tx.load()['phase'], 'complete')

    def test_bad_mark_failure_preserves_pending(self):
        self.stage(); self.tx.arm(self.boot)
        with patch.object(self.backend, 'mark_bad', side_effect=OSError('write failure')):
            with self.assertRaises(OSError): self.tx.cancel(self.boot)
        self.assertIsNotNone(self.store.load()['pending'])

    def test_customized_inactive_slot_and_existing_release_are_not_overwritten(self):
        state = self.store.load(); state['slots']['B'] = dict(state['slots']['A'], customized=True)
        self.store.save(state)
        with self.assertRaisesRegex(ValueError, 'Customized'): self.stage()
        state['slots']['B']['customized'] = False; self.store.save(state)
        with self.assertRaisesRegex(ValueError, 'unique'):
            self.tx.stage('bundle', dict(self.proof, release='release-1'), self.boot)

    def test_failed_admission_never_starts_or_records_install(self):
        @contextmanager
        def busy():
            raise ValueError('printer busy')
            yield
        transaction = Transaction(self.store, self.backend, busy)
        with self.assertRaisesRegex(ValueError, 'busy'):
            transaction.stage('bundle', self.proof, self.boot)
        self.assertFalse(transaction.path.exists())
        self.assertEqual(self.backend.calls, [])

    def test_corrupt_journal_is_not_reset(self):
        self.tx.path.write_text('{bad')
        with self.assertRaises(ValueError): self.stage()
        self.assertEqual(self.tx.path.read_text(), '{bad')
        self.assertEqual(self.backend.calls, [])

    def test_healthy_final_attempt_can_reset_counter_before_primary_check(self):
        boot = self.trial()
        # U-Boot decrements before Linux boots. On B's final attempt, RAUC
        # reports A as next primary until B's successful mark-good resets it.
        self.backend.states['B'] = False
        self.backend.selected = 'A'
        def good(slot):
            self.backend.states[slot] = True
            self.backend.selected = slot
        with patch.object(self.backend, 'mark_good', side_effect=good):
            self.tx.confirm(boot, lambda boot: True)
        self.assertIsNone(self.store.load()['pending'])
        self.assertEqual(self.tx.load()['phase'], 'complete')

    def test_changed_order_cannot_be_confirmed_as_primary(self):
        boot = self.trial()
        self.backend.selected = 'A'
        with self.assertRaisesRegex(ValueError, 'primary'):
            self.tx.confirm(boot, lambda boot: True)
        self.assertIsNotNone(self.store.load()['pending'])

    def test_copy_budget_refusal_precedes_install_and_journal(self):
        with patch.object(self.store, 'check_copy_budget', side_effect=ValueError('no copy capacity')):
            with self.assertRaisesRegex(ValueError, 'copy capacity'):
                self.stage()
        self.assertEqual(self.backend.calls, [])
        self.assertIsNone(self.tx.load())
        self.assertIsNone(self.store.load()['pending'])

    def test_reconcile_power_loss_after_activation_before_journal(self):
        self.stage(); original = self.tx.save
        def fail(tx, phase):
            if phase == 'armed': raise OSError('power loss')
            original(tx, phase)
        with patch.object(self.tx, 'save', side_effect=fail):
            with self.assertRaises(OSError): self.tx.arm(self.boot)
        boot = self.store.prepare_boot('B', 'release-2'); boot['boot_id'] = 'boot-2'
        calls = list(self.backend.calls)
        self.assertEqual(self.tx.reconcile(boot), 'needs-health')
        self.assertEqual(self.tx.load()['phase'], 'armed')
        self.assertEqual(self.store.load()['pending']['phase'], 'trial')
        self.assertEqual(self.backend.calls, calls)
        self.assertEqual(self.tx.reconcile(boot), 'needs-health')
        with self.assertRaisesRegex(ValueError, 'health'):
            self.tx.confirm(boot, lambda boot: False)
        self.tx.confirm(boot, lambda boot: True)
        self.assertEqual(self.tx.reconcile(boot), 'idle')

    def test_reconcile_source_reboot_never_rearms(self):
        self.stage()
        self.assertEqual(self.tx.reconcile(self.boot), 'staged')
        self.tx.arm(self.boot)
        self.assertEqual(self.tx.reconcile(self.boot), 'awaiting-reboot')
        calls = list(self.backend.calls)
        reboot = dict(self.boot, boot_id='new-boot')
        self.assertEqual(self.tx.reconcile(reboot), 'needs-cancel')
        self.assertEqual(self.backend.calls, calls)
        self.tx.cancel(reboot)
        self.assertEqual(self.tx.reconcile(reboot), 'idle')

    def test_reconcile_actual_fallback_retains_failed_trial(self):
        self.trial()
        fallback = self.store.prepare_boot('A', 'release-1'); fallback['boot_id'] = 'boot-3'
        self.assertEqual(self.tx.reconcile(fallback), 'needs-cancel')
        self.assertEqual(self.tx.cancel(fallback)['phase'], 'failed')
        self.assertEqual(self.tx.reconcile(fallback), 'idle')
        self.assertEqual(self.store.load()['last_failed_trial']['release'], 'release-2')

    def test_reconcile_refuses_orphan_pending_and_unannounced_target(self):
        self.store.expect_trial('B', 'release-2', 'A')
        with self.assertRaisesRegex(ValueError, 'no live transaction'):
            self.tx.reconcile(self.boot)
        self.store.cancel_trial()
        self.stage()
        self.store.expect_trial('B', 'release-2', 'A')
        boot = self.store.prepare_boot('B', 'release-2'); boot['boot_id'] = 'boot-2'
        with self.assertRaisesRegex(ValueError, 'disagree'):
            self.tx.reconcile(boot)
