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
        self.policy = dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A B', BOOT_A_LEFT='3', BOOT_B_LEFT='0')
    def validate_context(self, boot):
        pass
    def primary(self):
        return self.selected
    def good(self, slot):
        return self.states[slot]
    def validate_bundle(self, bundle, proof, target):
        self.calls.append('bundle-validated')
    def install(self, bundle, proof, target):
        self.calls.append('install'); self.states[target] = False
    def mark_active(self, slot):
        self.calls.append('active'); self.selected = slot; self.states[slot] = True
    def mark_bad(self, slot):
        self.calls.append('bad'); self.states[slot] = False
        self.policy['BOOT_'+slot+'_LEFT'] = '0'
        self.policy['BOOT_ORDER'] = ' '.join(value for value in self.policy['BOOT_ORDER'].split() if value != slot)
        if self.selected == slot:
            self.selected = 'B' if slot == 'A' else 'A'
    def boot_policy(self):
        return dict(self.policy)
    def disarm_target(self, target, source):
        self.mark_bad(target)
    def restore_pre_disarm(self, previous, target, source):
        self.calls.append('restore')
        expected = dict(previous)
        expected['BOOT_ORDER'] = ' '.join(value for value in previous['BOOT_ORDER'].split() if value != target)
        expected['BOOT_'+target+'_LEFT'] = '0'
        if self.policy not in (previous, expected) or self.selected != source or not self.good(source):
            raise ValueError('unexpected boot policy state')
        self.policy = dict(previous)
        self.states[target] = previous['BOOT_'+target+'_LEFT'] != '0'
        self.selected = source
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

    def test_automatic_opt_out_refuses_before_admission_or_writes(self):
        self.store.policy(auto_update=False)
        with patch.object(self.tx, 'admission', side_effect=AssertionError('service stop')):
            with self.assertRaisesRegex(ValueError, 'disabled'):
                self.tx.stage('test-bundle', self.proof, self.boot, automatic=True)
        self.assertIsNone(self.tx.load())
        self.assertEqual(self.backend.calls, [])
        # Opt-out leaves explicitly requested installation available.
        self.stage()
        self.tx.arm(self.boot)
        self.assertEqual(self.backend.primary(), 'B')

    def test_opt_out_between_stage_and_arm_preserves_staged_target(self):
        self.tx.stage('test-bundle', self.proof, self.boot, automatic=True)
        self.store.policy(auto_update=False)
        with patch.object(self.tx, 'admission', side_effect=AssertionError('service stop')):
            with self.assertRaisesRegex(ValueError, 'disabled'):
                self.tx.arm(self.boot, automatic=True)
        self.assertEqual(self.tx.load()['phase'], 'staged')
        self.assertEqual(self.backend.primary(), 'A')
        self.assertIsNone(self.store.load()['pending'])
        self.store.policy(auto_update=True)
        self.tx.arm(self.boot, automatic=True)
        self.assertEqual(self.backend.primary(), 'B')

    def test_opt_out_does_not_undo_armed_update_and_cancel_still_works(self):
        self.tx.stage('test-bundle', self.proof, self.boot, automatic=True)
        self.tx.arm(self.boot, automatic=True)
        self.store.policy(auto_update=False)
        self.assertEqual(self.tx.reconcile(self.boot), 'awaiting-reboot')
        self.assertEqual(self.backend.primary(), 'B')
        self.tx.cancel(self.boot)
        self.assertEqual(self.backend.primary(), 'A')

    def test_boot_reconcile_and_confirm_use_non_stopping_admission(self):
        calls = []
        @contextmanager
        def staging():
            calls.append('staging'); yield
        @contextmanager
        def boot_admission():
            calls.append('boot'); yield
        self.tx.admission = staging
        target = self.trial()
        self.assertIn('staging', calls)
        calls.clear()
        self.assertEqual(self.tx.reconcile(target, admission=boot_admission), 'needs-health')
        self.assertEqual(calls, ['boot'])
        calls.clear()
        checks = []
        self.tx.confirm(target, lambda current: checks.append(current['boot_id']) or True,
                        admission=boot_admission)
        self.assertEqual(calls, ['boot'])
        self.assertEqual(checks, [target['boot_id']])

    def test_automatic_flag_requires_boolean(self):
        for value in ('false', 'true', 0, 1, None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'boolean'):
                self.tx.stage('test-bundle', self.proof, self.boot, automatic=value)
        self.assertEqual(self.backend.calls, [])

    def test_stage_does_not_copy_state_or_select_target(self):
        self.stage()
        self.assertEqual(self.backend.primary(), 'A')
        self.assertEqual(self.backend.calls[:3], ['bundle-validated', 'bad', 'install'])
        self.assertEqual(self.backend.policy['BOOT_ORDER'], 'A')
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

    def test_crash_after_pre_disarm_restores_old_policy_before_any_slot_write(self):
        original = self.tx.save
        def fail(tx, phase):
            if phase == 'installing':
                raise OSError('power loss after disarm')
            original(tx, phase)
        with patch.object(self.tx, 'save', side_effect=fail):
            with self.assertRaises(OSError):
                self.stage()
        tx = self.tx.load()
        self.assertEqual(tx['phase'], 'preparing')
        self.assertNotIn('install', self.backend.calls)
        self.assertEqual(self.backend.policy['BOOT_ORDER'], 'A')
        self.assertEqual(self.tx.reconcile(self.boot), 'restored-pre-disarm')
        self.assertEqual(self.backend.policy, tx['previous_boot_policy'])
        self.assertEqual(self.backend.primary(), 'A')
        self.assertNotIn('install', self.backend.calls)

    def test_preparing_journal_failure_has_no_policy_or_slot_writes(self):
        with patch.object(self.tx, 'save', side_effect=OSError('journal fsync failed')):
            with self.assertRaisesRegex(OSError, 'fsync'):
                self.stage()
        self.assertIsNone(self.tx.load())
        self.assertEqual(self.backend.policy['BOOT_ORDER'], 'A B')
        self.assertTrue(self.backend.good('A'))
        self.assertNotIn('bad', self.backend.calls)
        self.assertNotIn('install', self.backend.calls)

    def test_disarm_write_failure_does_not_restore_unrecognized_intermediate(self):
        # Exercise B as a still-bootable previous fallback. Production writes
        # BOOT_ORDER first, then the attempt counter, so interruption between
        # those writes leaves this exact intermediate state.
        self.backend.states['B'] = True
        self.backend.policy['BOOT_B_LEFT'] = '3'
        def partial_disarm(target, source):
            self.backend.policy['BOOT_ORDER'] = 'A'
            raise OSError('power loss before counter write')
        with patch.object(self.backend, 'disarm_target', side_effect=partial_disarm):
            with self.assertRaisesRegex(OSError, 'before counter'):
                self.stage()
        self.assertEqual(self.tx.load()['phase'], 'preparing')
        with self.assertRaisesRegex(ValueError, 'unexpected boot policy state'):
            self.tx.reconcile(self.boot)
        self.assertEqual(self.backend.policy['BOOT_ORDER'], 'A')
        self.assertEqual(self.backend.policy['BOOT_B_LEFT'], '3')
        self.assertTrue(self.backend.good('A'))
        self.assertEqual(self.backend.primary(), 'A')
        self.assertNotIn('install', self.backend.calls)

    def test_unknown_partial_disarm_is_left_disabled_and_not_repaired(self):
        def unexpected_disarm(target, source):
            self.backend.policy['BOOT_'+target+'_LEFT'] = '0'
            self.backend.policy['BOOT_ORDER'] = 'B A'
            raise OSError('unexpected boot policy mutation')
        with patch.object(self.backend, 'disarm_target', side_effect=unexpected_disarm):
            with self.assertRaisesRegex(OSError, 'unexpected'):
                self.stage()
        with self.assertRaisesRegex(ValueError, 'unexpected boot policy state'):
            self.tx.reconcile(self.boot)
        self.assertEqual(self.backend.primary(), 'A')
        self.assertFalse(self.backend.good('B'))
        self.assertNotIn('install', self.backend.calls)

    def test_failure_at_first_slot_write_never_restores_target_policy(self):
        def first_write_then_power_loss(bundle, proof, target):
            self.backend.calls.append('first-slot-write')
            self.backend.states[target] = False  # target now contains a partial image
            raise OSError('power loss at first slot write')
        with patch.object(self.backend, 'install', side_effect=first_write_then_power_loss):
            with self.assertRaisesRegex(OSError, 'first slot write'):
                self.stage()
        self.assertEqual(self.tx.load()['phase'], 'installing')
        self.assertEqual(self.backend.primary(), 'A')
        self.assertTrue(self.backend.good('A'))
        self.assertFalse(self.backend.good('B'))
        self.assertEqual(self.backend.policy['BOOT_ORDER'], 'A')
        self.assertEqual(self.tx.reconcile(self.boot), 'needs-cancel')
        self.assertEqual(self.backend.policy['BOOT_ORDER'], 'A')

    def test_invalid_bundle_is_rejected_before_policy_journal_or_disarm(self):
        with patch.object(self.backend, 'validate_bundle', side_effect=ValueError('bad signature')):
            with self.assertRaisesRegex(ValueError, 'bad signature'):
                self.stage()
        self.assertIsNone(self.tx.load())
        self.assertEqual(self.backend.primary(), 'A')
        self.assertEqual(self.backend.calls, [])

    def test_installing_crash_keeps_target_disarmed_and_requires_cancel(self):
        with patch.object(self.backend, 'install', side_effect=OSError('unknown write progress')):
            with self.assertRaises(OSError):
                self.stage()
        self.assertEqual(self.tx.load()['phase'], 'installing')
        self.assertEqual(self.backend.policy['BOOT_ORDER'], 'A')
        self.assertEqual(self.tx.reconcile(self.boot), 'needs-cancel')
        self.assertEqual(self.backend.policy['BOOT_ORDER'], 'A')

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
