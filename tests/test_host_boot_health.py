from contextlib import contextmanager
import json
import signal
from pathlib import Path
import sys
import tempfile
import time
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_boot_health import (CoordinatorDeadline, DiagnosticBackend, HealthFailure, HostHealth,
                              bounded_json, coordinator_deadline, main, COORDINATOR_SECONDS,
                              COORDINATOR_LIMIT_SECONDS, HEALTH_WINDOW_SECONDS,
                              observed_rauc_slot, record_failure, run, validate_boot)
from sv08_state import Store
from sv08_transaction import Transaction
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from integrate_host_os import stage


@contextmanager
def admitted():
    yield


class Backend:
    def __init__(self):
        self.selected, self.states = 'A', {'A': True, 'B': False}
        self.calls = []
        self.policy = dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A B', BOOT_A_LEFT='3', BOOT_B_LEFT='0')
    def writer(self): return admitted()
    def validate_context(self, boot): self.calls.append('validate')
    def resolution_evidence(self, boot):
        self.validate_context(boot)
        return {'operation': 'idle'}
    def normal_resolution_evidence(self, boot):
        self.calls.append('normal-validate')
    def confirm_normal(self, boot):
        self.calls.append('normal-good')
        self.policy['BOOT_'+boot['slot']+'_LEFT'] = '3'
    def primary(self): return self.selected
    def good(self, slot): return self.states[slot]
    def validate_bundle(self, bundle, proof, target): pass
    def boot_policy(self): return dict(self.policy)
    def disarm_target(self, target, source): self.calls.append('bad'); self.states[target] = False
    def restore_pre_disarm(self, previous, target, source): self.calls.append('restore')
    def install(self, bundle, proof, target): self.calls.append('install'); self.states[target] = False
    def mark_active(self, slot): self.calls.append('active'); self.selected = slot; self.states[slot] = True
    def mark_good(self, slot): self.calls.append('good'); self.states[slot] = True
    def mark_bad(self, slot): self.calls.append('bad'); self.states[slot] = False; self.selected = 'A'


class BootHealthTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = Store(self.root / 'data', reserve_bytes=0)
        self.store.initialize()
        self.boot = self.store.prepare_boot('A', 'release-1', release_revision=1)
        self.boot['boot_id'] = str(uuid.uuid4())
        self.backend = Backend()
        self.tx = Transaction(self.store, self.backend, admitted)
        self.manifest = {'release': 'release-1', 'state_schema': 1}
        self.ready = self.root / 'ready'

    def validate(self, boot=None):
        boot = boot or self.boot
        return validate_boot(boot, self.store, self.manifest, boot_id=self.boot['boot_id'] if boot is self.boot else getattr(self, 'current_boot_id', self.boot['boot_id']),
                             cmdline='console=ttyS0 rauc.slot=' + boot['slot'],
                             observed_slot=boot['slot'],
                             verify=lambda *_: None)

    def test_exact_boot_record_and_state_identity(self):
        self.validate()
        for changed in (dict(self.boot, unknown=True), dict(self.boot, boot_id=str(uuid.uuid4())),
                        dict(self.boot, generation=str(self.root / 'other'))):
            with self.assertRaises(ValueError):
                self.validate(changed)
        with self.assertRaises(ValueError):
            validate_boot(self.boot, self.store, self.manifest, boot_id=self.boot['boot_id'],
                          cmdline='rauc.slot=B', observed_slot='A', verify=lambda *_: None)
        with self.assertRaises(ValueError):
            validate_boot(self.boot, self.store, self.manifest, boot_id=self.boot['boot_id'],
                          cmdline='rauc.slot=A', observed_slot='B', verify=lambda *_: None)
        generation = Path(self.boot['generation'])
        generation.rename(generation.with_name(generation.name + '-interrupted'))
        with self.assertRaises(ValueError):
            self.validate()

    def test_nontrial_writable_boot_releases_only_host_marker(self):
        self.store.policy(mode='writable')
        self.boot = self.store.prepare_boot('A', 'release-1', release_revision=1); self.boot['boot_id'] = str(uuid.uuid4())
        self.assertEqual(run(self.boot, self.tx, Mock(return_value=True),
                             admitted, Mock(side_effect=AssertionError('reboot')),
                             ready=self.ready, validate=self.validate), 'idle')
        self.assertTrue(self.ready.is_file())

    def test_staged_source_boot_can_publish_health_marker(self):
        proof = {'release': 'release-2', 'bundle_sha256': 'a' * 64,
                 'signer_trusted': True, 'release_revision': 2}
        self.tx.stage('bundle', proof, self.boot)
        self.assertEqual(run(self.boot, self.tx, Mock(return_value=True),
                             admitted, Mock(side_effect=AssertionError('reboot')),
                             ready=self.ready, validate=self.validate), 'staged')
        self.assertTrue(self.ready.is_file())

    def test_interrupted_arming_repair_keeps_validated_source_usable(self):
        proof = {'release': 'release-2', 'bundle_sha256': 'a' * 64,
                 'signer_trusted': True, 'release_revision': 2}
        self.tx.stage('bundle', proof, self.boot)
        original = self.backend.mark_active
        def interrupted(slot):
            original(slot)
            raise OSError('interrupted after boot selection')
        self.backend.mark_active = interrupted
        with self.assertRaises(OSError):
            self.tx.arm(self.boot)
        self.backend.mark_active = original
        self.assertEqual(self.tx.load()['phase'], 'arming')
        calls = []
        @contextmanager
        def staging():
            calls.append('staging'); yield
        @contextmanager
        def boot_admission():
            calls.append('boot'); yield
        self.tx.admission = staging
        self.assertEqual(run(self.boot, self.tx, Mock(return_value=True),
                             boot_admission, Mock(side_effect=AssertionError('reboot')),
                             ready=self.ready, validate=self.validate), 'needs-arm')
        self.assertEqual(calls, ['boot', 'staging', 'boot'])
        self.assertEqual(self.tx.load()['phase'], 'armed')
        self.assertTrue(self.ready.is_file())

    def test_more_than_three_healthy_normal_boots_refill_only_running_slot(self):
        self.backend.policy.update(BOOT_A_LEFT='1', BOOT_B_LEFT='2')
        for _ in range(5):
            # Model upstream U-Boot consuming one attempt before entering Linux.
            self.backend.policy['BOOT_A_LEFT'] = str(int(self.backend.policy['BOOT_A_LEFT']) - 1)
            self.boot['boot_id'] = str(uuid.uuid4())
            state = self.store.load()
            health = Mock(return_value=True)
            run(self.boot, self.tx, health, admitted, Mock(), ready=self.ready, validate=self.validate)
            health.assert_called_once_with(self.boot)
            self.assertEqual(self.backend.policy,
                             dict(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A B', BOOT_A_LEFT='3', BOOT_B_LEFT='2'))
            self.assertEqual(self.store.load(), state)
            self.assertIsNone(self.tx.load())
            self.assertTrue(self.ready.exists())

    def test_failed_normal_health_does_not_refill_or_release_stale_ready(self):
        self.ready.touch()
        self.backend.policy['BOOT_A_LEFT'] = '0'
        fallback = Mock()
        with self.assertRaises(HealthFailure):
            run(self.boot, self.tx, Mock(side_effect=HealthFailure('unstable')),
                admitted, fallback, ready=self.ready, validate=self.validate)
        self.assertEqual(self.backend.policy['BOOT_A_LEFT'], '0')
        self.assertNotIn('normal-good', self.backend.calls)
        self.assertFalse(self.ready.exists())
        fallback.assert_not_called()

    def test_unknown_normal_context_and_changed_state_do_not_refill(self):
        for fail in ('identity', 'state'):
            with self.subTest(fail=fail):
                self.backend.calls.clear()
                def health(_boot):
                    if fail == 'state':
                        state = self.store.load(); state['auto_update'] = False; self.store.save(state)
                    return True
                def validate():
                    if fail == 'identity': raise ValueError('unknown boot identity')
                    return self.validate()
                with self.assertRaises(ValueError):
                    run(self.boot, self.tx, health, admitted, Mock(), ready=self.ready, validate=validate)
                self.assertNotIn('normal-good', self.backend.calls)
                self.assertFalse(self.ready.exists())

    def test_normal_health_and_write_hold_state_admission_and_writer(self):
        held = []
        @contextmanager
        def admission():
            held.append('admission')
            try: yield
            finally: held.pop()
        @contextmanager
        def writer():
            held.append('writer')
            try: yield
            finally: held.pop()
        self.tx.writer = writer
        def assert_locks(_boot):
            self.assertEqual(held, ['admission', 'writer'])
            with self.assertRaisesRegex(ValueError, 'busy'):
                with self.store.locked(nonblocking=True): pass
            return True
        self.backend.confirm_normal = assert_locks
        run(self.boot, self.tx, assert_locks, admission, Mock(), ready=self.ready, validate=self.validate)

    def test_armed_source_refill_preserves_pending_trial_and_target_attempts(self):
        self.tx.stage('bundle', {'release': 'release-2', 'bundle_sha256': 'a'*64, 'signer_trusted': True, 'release_revision': 2}, self.boot)
        self.tx.arm(self.boot)
        self.backend.policy.update(BOOT_ORDER='B A', BOOT_A_LEFT='0', BOOT_B_LEFT='1')
        state, journal = self.store.load(), self.tx.load()
        self.assertEqual(run(self.boot, self.tx, Mock(return_value=True), admitted, Mock(),
                             ready=self.ready, validate=self.validate), 'awaiting-reboot')
        self.assertEqual(self.backend.policy['BOOT_ORDER'], 'B A')
        self.assertEqual(self.backend.policy['BOOT_B_LEFT'], '1')
        self.assertEqual(self.backend.policy['BOOT_A_LEFT'], '3')
        self.assertEqual(self.store.load(), state)
        self.assertEqual(self.tx.load(), journal)

    def test_legacy_diagnostic_health_has_no_environment_write(self):
        self.backend.diagnostic_only = True
        self.backend.confirm_normal = Mock(side_effect=AssertionError('legacy write'))
        health = Mock(return_value=True)
        run(self.boot, self.tx, health, admitted, Mock(), ready=self.ready, validate=self.validate)
        health.assert_called_once_with(self.boot)
        self.backend.confirm_normal.assert_not_called()
        self.assertTrue(self.ready.exists())

    def test_writable_customized_normal_health_keeps_image_operations_blocked(self):
        self.store.policy(mode='writable')
        self.boot = self.store.prepare_boot('A', 'release-1', release_revision=1); self.boot['boot_id'] = str(uuid.uuid4())
        self.assertTrue(self.boot['customized'])
        self.manifest['devices'] = {'data': '/data-device'}
        clock = [0.0]
        health = HostHealth(self.backend, self.manifest, now=lambda: clock[0],
                            sleep=lambda seconds: clock.__setitem__(0, clock[0]+seconds),
                            command=lambda args, **_: 'active' if args[0] == 'systemctl' else '/data-device')
        run(self.boot, self.tx, health, admitted, Mock(), ready=self.ready,
            validate=self.validate, normal_health=health.normal)
        self.assertIn('normal-validate', self.backend.calls)
        self.assertIn('normal-good', self.backend.calls)
        with self.assertRaisesRegex(ValueError, 'immutable mode'):
            self.tx.stage('bundle', {'release': 'release-2', 'bundle_sha256': 'a'*64, 'signer_trusted': True, 'release_revision': 2}, self.boot)
        with self.assertRaisesRegex(HealthFailure, 'immutable'):
            health(self.boot)

    def trial(self):
        proof = {'release': 'release-2', 'bundle_sha256': 'a' * 64,
                 'signer_trusted': True, 'release_revision': 2}
        self.tx.stage('bundle', proof, self.boot)
        self.tx.arm(self.boot)
        target = self.store.prepare_boot('B', 'release-2')
        target['boot_id'] = str(uuid.uuid4())
        self.current_boot_id = target['boot_id']
        self.manifest['release'] = 'release-2'
        return target

    def test_trial_health_called_once_and_gate_cleared_after_confirmation(self):
        target = self.trial(); gate = self.root / 'trial'; gate.touch()
        health = Mock(return_value=True)
        self.assertEqual(run(target, self.tx, health, admitted, Mock(), ready=self.ready,
                             trial_marker=gate, validate=lambda: self.validate(target)), 'idle')
        health.assert_called_once_with(target)
        self.assertFalse(gate.exists())
        self.assertTrue(self.ready.exists())
        self.assertEqual(self.tx.load()['phase'], 'complete')

    def test_failed_health_retains_gate_and_requests_only_validated_fallback(self):
        target = self.trial(); gate = self.root / 'trial'; gate.touch()
        calls = []
        @contextmanager
        def boot_admission():
            calls.append('boot'); yield
        @contextmanager
        def writer():
            calls.append('writer'); yield
        self.tx.writer = writer
        def fallback(boot, transaction_id, reason):
            self.assertEqual(transaction_id, self.tx.load()['id'])
            self.assertEqual(calls[-2:], ['boot', 'writer'])
            with self.assertRaisesRegex(ValueError, 'busy'):
                with self.store.locked(nonblocking=True):
                    pass
        fallback = Mock(side_effect=fallback)
        result = run(target, self.tx, Mock(side_effect=HealthFailure('failed')), boot_admission,
                     fallback, ready=self.ready, trial_marker=gate,
                     validate=lambda: self.validate(target))
        self.assertEqual(result, 'needs-health')
        fallback.assert_called_once()
        self.assertTrue(gate.exists())
        self.assertFalse(self.ready.exists())
        self.assertEqual(self.tx.load()['phase'], 'armed')
        failures = list((self.store.root / 'shared/logs/journal/boot-health').glob('*.json'))
        self.assertEqual(len(failures), 1)
        self.assertEqual(json.loads(failures[0].read_text())['generation'], target['generation'])

    def test_unknown_backend_confirmation_does_not_fallback(self):
        target = self.trial(); gate = self.root / 'trial'; gate.touch()
        fallback = Mock()
        self.backend.mark_good = Mock(side_effect=OSError('unknown outcome'))
        with self.assertRaises(OSError):
            run(target, self.tx, Mock(return_value=True), admitted, fallback,
                ready=self.ready, trial_marker=gate, validate=lambda: self.validate(target))
        fallback.assert_not_called()
        self.assertTrue(gate.exists())
        self.assertFalse(self.ready.exists())
        self.assertEqual(self.tx.load()['phase'], 'confirming')

    def test_cleared_trial_with_incomplete_journal_resumes_on_next_target_boot(self):
        target = self.trial(); gate = self.root / 'trial'; gate.touch()
        original_save = self.tx.save
        def interrupted(tx, phase):
            if phase == 'complete':
                raise OSError('power loss before complete journal')
            return original_save(tx, phase)
        with unittest.mock.patch.object(self.tx, 'save', side_effect=interrupted):
            with self.assertRaises(OSError):
                run(target, self.tx, Mock(return_value=True), admitted, Mock(),
                    ready=self.ready, trial_marker=gate,
                    validate=lambda: self.validate(target))
        self.assertIsNone(self.store.load()['pending'])
        self.assertEqual(self.tx.load()['phase'], 'confirming')
        self.assertTrue(gate.exists())
        self.assertFalse(self.ready.exists())
        # /run is recreated at the next boot; early preparation keeps the
        # target generation and records the new kernel boot identity.
        gate.unlink()
        resumed = self.store.prepare_boot('B', 'release-2')
        resumed['boot_id'] = str(uuid.uuid4())
        self.current_boot_id = resumed['boot_id']
        self.assertFalse(resumed['trial'])
        self.backend.selected = 'A'
        with self.assertRaisesRegex(ValueError, 'good and primary'):
            run(resumed, self.tx, Mock(return_value=True), admitted, Mock(),
                ready=self.ready, validate=lambda: self.validate(resumed))
        self.assertFalse(self.ready.exists())
        self.backend.selected = 'B'
        health = Mock(return_value=True)
        self.assertEqual(run(resumed, self.tx, health, admitted, Mock(),
                             ready=self.ready, validate=lambda: self.validate(resumed)), 'idle')
        health.assert_called_once_with(resumed)
        self.assertTrue(self.ready.exists())
        self.assertEqual(self.tx.load()['phase'], 'complete')

    def test_interrupted_generation_copy_preserves_source_and_retries_handoff(self):
        proof = {'release': 'release-2', 'bundle_sha256': 'a' * 64,
                 'signer_trusted': True, 'release_revision': 2}
        self.tx.stage('bundle', proof, self.boot)
        self.tx.arm(self.boot)
        source = self.store.load()['slots']['A']['generation']
        with unittest.mock.patch('sv08_state.snapshot', side_effect=OSError('interrupted copy')):
            with self.assertRaises(OSError):
                self.store.prepare_boot('B', 'release-2')
        self.assertEqual(self.store.load()['slots']['A']['generation'], source)
        self.assertNotIn('B', self.store.load()['slots'])
        self.assertEqual(self.tx.load()['phase'], 'armed')
        target = self.store.prepare_boot('B', 'release-2')
        target['boot_id'] = str(uuid.uuid4())
        self.current_boot_id = target['boot_id']
        self.manifest['release'] = 'release-2'
        gate = self.root / 'trial'; gate.touch()
        self.assertEqual(run(target, self.tx, Mock(return_value=True), admitted, Mock(),
                             ready=self.ready, trial_marker=gate,
                             validate=lambda: self.validate(target)), 'idle')
        self.assertEqual(self.tx.load()['phase'], 'complete')

    def test_same_boot_restart_clears_stale_ready_before_bad_input(self):
        self.ready.touch()
        real_path = Path
        def path(value):
            return self.ready if str(value) == '/run/sv08/os-health-ready' else real_path(value)
        def bad_input(value, **kwargs):
            if str(value).endswith('/release.json'):
                raise ValueError('bad input')
            return bounded_json(value, **kwargs)
        with unittest.mock.patch('sv08_boot_health.os.geteuid', return_value=0), \
             unittest.mock.patch('sv08_boot_health.Path', side_effect=path), \
             unittest.mock.patch('sv08_boot_health.bounded_json', side_effect=bad_input), \
             unittest.mock.patch('sv08_boot_health.Store', return_value=self.store), \
             unittest.mock.patch('sv08_boot_health.record_failure') as record:
            with self.assertRaisesRegex(ValueError, 'bad input'):
                main()
        self.assertFalse(self.ready.exists())
        record.assert_called_once()

    def test_process_deadline_interrupts_blocked_probe_and_releases_state_lock(self):
        def command(args, **_):
            return 'active\n' if args[0] == 'systemctl' else '/data-device\n'
        self.manifest['devices'] = {'data': '/data-device'}
        self.backend.validate_context = lambda _boot: time.sleep(0.2)
        health = HostHealth(self.backend, self.manifest, command=command)
        with self.assertRaises(CoordinatorDeadline):
            with coordinator_deadline(0.05), self.store.locked():
                health.probe(self.boot)
        with self.store.locked(nonblocking=True):
            pass

    def test_extended_startup_deadline_is_limited_to_identified_fixture_callers(self):
        with self.assertRaises(ValueError):
            with coordinator_deadline(COORDINATOR_LIMIT_SECONDS + 1): pass
        with coordinator_deadline(0.01, disposable_fixture=True):
            pass
        with self.assertRaises(ValueError):
            with coordinator_deadline(181, disposable_fixture=True): pass
        with self.assertRaises(ValueError):
            HostHealth(self.backend, self.manifest, deadline=61)
        HostHealth(self.backend, self.manifest, deadline=61, disposable_fixture=True)

    def test_default_outer_budget_includes_full_poll_and_bounded_overhead(self):
        self.assertEqual(HEALTH_WINDOW_SECONDS,40)
        self.assertEqual(COORDINATOR_SECONDS,HEALTH_WINDOW_SECONDS+30)
        self.assertEqual(COORDINATOR_LIMIT_SECONDS,90)
        with patch('sv08_boot_health.signal.setitimer') as timer:
            with coordinator_deadline():
                pass
        self.assertEqual(timer.call_args_list[0].args,(signal.ITIMER_REAL,70))
        unit=Path(__file__).resolve().parents[1]/'configs/host-os/systemd/sv08-boot-health.service'
        import configparser
        config=configparser.ConfigParser();config.read(unit)
        self.assertEqual(config.getint('Service','TimeoutStartSec'),95)
        self.assertGreater(config.getint('Service','TimeoutStartSec'),COORDINATOR_LIMIT_SECONDS)

    def test_production_dispatch_uses_derived_outer_budget_without_fixture_extension(self):
        reset=Mock()
        @contextmanager
        def deadline(seconds):
            self.assertEqual(seconds,COORDINATOR_SECONDS)
            yield reset
        real_path=Path
        def path(value):
            return self.ready if str(value)=='/run/sv08/os-health-ready' else real_path(value)
        with patch('sv08_boot_health.Path',side_effect=path), \
             patch.object(Path,'read_text',return_value=''), \
             patch('sv08_boot_health.bounded_json',return_value={'deployable':True}), \
             patch('sv08_boot_health.coordinator_deadline',side_effect=deadline), \
             patch('sv08_boot_health._main') as dispatch:
            main()
        dispatch.assert_called_once_with(disposable_fixture=False)
        reset.assert_not_called()

    def test_failed_health_full_window_records_and_calls_fallback_within_outer_budget(self):
        clock=[12.0]  # Prior context/boot validation already consumed time.
        journal=dict(id='trial',phase='armed',slot='B',release='target',previous_slot='A',
                     previous_release='source',boot_id=str(uuid.uuid4()))
        state=dict(slots={'A':dict(release='source',generation='source'),
                         'B':dict(release='target',parent_generation='source')},
                   pending=dict(id='trial',phase='trial'))
        store=Mock();store.load.return_value=state;store.locked.side_effect=admitted
        backend=Mock();transaction=Mock(store=store,backend=backend)
        transaction.load.return_value=journal;transaction.reconcile.return_value='needs-health'
        transaction.writer.side_effect=admitted
        boot=dict(slot='B',release='target',mode='immutable',trial=True,boot_id=str(uuid.uuid4()))
        health=HostHealth(backend,{},now=lambda:clock[0],
                          sleep=lambda seconds:clock.__setitem__(0,clock[0]+seconds),
                          command=lambda *a,**k:'inactive')
        transaction.confirm.side_effect=lambda boot,callback,**kwargs:callback(boot)
        def callback(*args):
            clock[0]+=5  # Bounded final validation/reboot callback allowance.
        fallback=Mock(side_effect=callback);record=Mock()
        with patch('sv08_boot_health.signal.setitimer'):
            with coordinator_deadline():
                result=run(boot,transaction,health,admitted,fallback,ready=self.ready,
                           validate=lambda:None,record=record)
        self.assertEqual(result,'needs-health')
        self.assertEqual(clock[0],57.0)
        self.assertLess(clock[0],COORDINATOR_SECONDS)
        self.assertIsInstance(record.call_args.args[2],HealthFailure)
        self.assertIn('not stable within deadline',str(record.call_args.args[2]))
        fallback.assert_called_once()
        backend.mark_bad.assert_not_called()
        self.assertFalse(self.ready.exists())

    def test_health_probe_uses_one_backend_context_validation(self):
        def command(args, **_):
            return 'active\n' if args[0] == 'systemctl' else '/data-device\n'
        self.manifest['devices'] = {'data': '/data-device'}
        self.backend.calls.clear()
        HostHealth(self.backend, self.manifest, command=command).probe(self.boot)
        self.assertEqual(self.backend.calls, ['validate'])

    def test_deadline_before_run_records_bounded_startup_failure(self):
        self.ready.touch()
        real_path = Path
        def path(value):
            return self.ready if str(value) == '/run/sv08/os-health-ready' else real_path(value)
        def blocked(path, **kwargs):
            if str(path).endswith('/release.json'):
                time.sleep(0.2)
            return bounded_json(path, **kwargs)
        with unittest.mock.patch('sv08_boot_health.os.geteuid', return_value=0), \
             unittest.mock.patch('sv08_boot_health.Path', side_effect=path), \
             unittest.mock.patch('sv08_boot_health.bounded_json', side_effect=blocked), \
             unittest.mock.patch('sv08_boot_health.Store', return_value=self.store):
            with self.assertRaises(CoordinatorDeadline):
                main(deadline_seconds=0.05)
        self.assertFalse(self.ready.exists())
        records = list((self.store.root / 'shared/logs/journal/boot-health').glob('*.json'))
        self.assertEqual(len(records), 1)
        self.assertLessEqual(records[0].stat().st_size, 64 * 1024)
        self.assertIn('deadline', records[0].read_text())

    def test_host_health_does_not_require_printer_or_network(self):
        clock = [0.0]
        commands = []
        def command(args, **_):
            commands.append(args)
            return 'active\n' if args[0] == 'systemctl' else '/data-device\n'
        self.manifest['devices'] = {'data': '/data-device'}
        health = HostHealth(self.backend, self.manifest, now=lambda: clock[0],
                            sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
                            command=command)
        self.assertTrue(health(dict(self.boot, mode='immutable')))
        self.assertEqual({args[0] for args in commands}, {'systemctl', 'findmnt'})

    def test_legacy_backend_requires_current_paired_mount_and_mode(self):
        manifest = {'devices': {'boot-a': '/explicit/boot-a'}}
        backend = DiagnosticBackend(manifest)
        self.assertFalse(hasattr(backend, 'confirm_normal'))
        with patch('sv08_boot_health.verify_devices') as verify, \
             patch('sv08_boot_health.device_number', return_value='254:1'), \
             patch('sv08_boot_health.subprocess.check_output', return_value='254:1'), \
             patch('sv08_boot_health.os.statvfs', return_value=SimpleNamespace(f_flag=0)):
            backend.normal_resolution_evidence(dict(self.boot, mode='writable'))
            verify.assert_called_once_with(manifest, 'A')
            with self.assertRaisesRegex(ValueError, 'operating mode'):
                backend.normal_resolution_evidence(self.boot)
        with patch('sv08_boot_health.verify_devices'), \
             patch('sv08_boot_health.device_number', return_value='254:1'), \
             patch('sv08_boot_health.subprocess.check_output', return_value='254:3'):
            with self.assertRaisesRegex(ValueError, 'boot mount'):
                backend.normal_resolution_evidence(self.boot)

    def test_normal_stability_restarts_when_backend_identity_changes(self):
        clock = [0.0]
        self.manifest['devices'] = {'data': '/data-device'}
        self.backend.normal_resolution_evidence = lambda boot: {'identity': clock[0]}
        health = HostHealth(self.backend, self.manifest, now=lambda: clock[0],
                            sleep=lambda seconds: clock.__setitem__(0, clock[0]+seconds),
                            command=lambda args, **_: 'active' if args[0] == 'systemctl' else '/data-device',
                            stable=1, deadline=2)
        with self.assertRaises(HealthFailure):
            health.normal(self.boot)

    def test_malformed_and_oversized_records_refused(self):
        path = self.root / 'input.json'
        path.write_text('{')
        with self.assertRaises(ValueError): bounded_json(path)
        path.write_text('x' * (64 * 1024 + 1))
        with self.assertRaises(ValueError): bounded_json(path)
        record_failure(self.store, self.boot, 'failed')
        with self.assertRaises(ValueError): record_failure(self.store, self.boot, 'repeat')
        self.assertEqual(observed_rauc_slot(lambda *_args, **_kwargs: '{"booted":"A"}'), 'A')
        with self.assertRaises(ValueError):
            observed_rauc_slot(lambda *_args, **_kwargs: '{"booted":"B"}' + ' ' * (32 * 1024))

    def test_service_orders_health_before_klipper_and_enables_on_host(self):
        repo = Path(__file__).resolve().parents[1]
        service = (repo / 'configs/host-os/systemd/sv08-boot-health.service').read_text()
        klipper = (repo / 'configs/host-os/systemd/sv08-klipper.service').read_text()
        integration = (repo / 'scripts/integrate_host_os.py').read_text()
        self.assertIn('After=sv08-prepare.service', service)
        self.assertIn('Before=sv08-klipper.service', service)
        self.assertIn('TimeoutStartSec=95', service)
        self.assertIn('Requires=sv08-prepare.service sv08-boot-health.service', klipper)
        self.assertIn('ConditionPathExists=/run/sv08/os-health-ready', klipper)
        self.assertIn('ConditionPathExists=!/run/sv08/trial', klipper)
        self.assertIn("health_link.symlink_to('../sv08-boot-health.service')", integration)

        work = self.root / 'image'; root = work / 'rootfs'
        (work / 'refresh-complete').parent.mkdir(parents=True)
        (work / 'refresh-complete').touch()
        for directory in ('etc/systemd/system', 'etc/ssh', 'etc/apt/apt.conf.d',
                          'etc/initramfs-tools/conf.d', 'usr/bin', 'usr/sbin',
                          'etc/default', 'etc/sudoers.d'):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / 'etc/passwd').write_text('sv08:x:1000:1000::/home/sv08:/bin/bash\n')
        (root / 'etc/group').write_text('sv08:x:1000:\n')
        key = work / 'owner-key'; key.write_text('ssh-ed25519 fixture owner\n')
        manifest = dict(release='fixture-1', state_schema=1, deployable=False,
                        devices={name: '/dev/disk/by-partuuid/' + str(uuid.uuid4())
                                 for name in ('boot-a', 'root-a', 'boot-b', 'root-b', 'data', 'recovery')})
        from unittest.mock import patch
        with patch('integrate_host_os.rebuild_initramfs') as rebuild:
            stage(work, manifest, owner_key=key)
        rebuild.assert_called_once_with(root)
        wants = root / 'etc/systemd/system/multi-user.target.wants'
        self.assertEqual({path.name for path in wants.iterdir()}, {'sv08-boot-health.service', 'sv08-printer-api.service', 'sv08-mainsail.service'})
        self.assertTrue((wants / 'sv08-boot-health.service').resolve().is_file())


if __name__ == '__main__':
    unittest.main()
