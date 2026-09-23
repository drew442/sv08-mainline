from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_boot_health import (CoordinatorDeadline, HealthFailure, HostHealth,
                              bounded_json, coordinator_deadline, main,
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
    def writer(self): return admitted()
    def validate_context(self, boot): self.calls.append('validate')
    def resolution_evidence(self, boot): return {'operation': 'idle'}
    def primary(self): return self.selected
    def good(self, slot): return self.states[slot]
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
        self.boot = self.store.prepare_boot('A', 'release-1')
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
        self.boot = self.store.prepare_boot('A', 'release-1'); self.boot['boot_id'] = str(uuid.uuid4())
        self.assertEqual(run(self.boot, self.tx, Mock(side_effect=AssertionError('health')),
                             admitted, Mock(side_effect=AssertionError('reboot')),
                             ready=self.ready, validate=self.validate), 'idle')
        self.assertTrue(self.ready.is_file())

    def test_staged_source_boot_can_publish_health_marker(self):
        proof = {'release': 'release-2', 'bundle_sha256': 'a' * 64}
        self.tx.stage('bundle', proof, self.boot)
        self.assertEqual(run(self.boot, self.tx, Mock(side_effect=AssertionError('health')),
                             admitted, Mock(side_effect=AssertionError('reboot')),
                             ready=self.ready, validate=self.validate), 'staged')
        self.assertTrue(self.ready.is_file())

    def test_interrupted_arming_repair_keeps_validated_source_usable(self):
        proof = {'release': 'release-2', 'bundle_sha256': 'a' * 64}
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
        self.assertEqual(run(self.boot, self.tx, Mock(side_effect=AssertionError('health')),
                             boot_admission, Mock(side_effect=AssertionError('reboot')),
                             ready=self.ready, validate=self.validate), 'needs-arm')
        self.assertEqual(calls, ['boot', 'staging'])
        self.assertEqual(self.tx.load()['phase'], 'armed')
        self.assertTrue(self.ready.is_file())

    def trial(self):
        proof = {'release': 'release-2', 'bundle_sha256': 'a' * 64}
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
        proof = {'release': 'release-2', 'bundle_sha256': 'a' * 64}
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
        self.assertIn('TimeoutStartSec=60', service)
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
        stage(work, manifest, owner_key=key)
        wants = root / 'etc/systemd/system/multi-user.target.wants'
        self.assertEqual({path.name for path in wants.iterdir()}, {'sv08-boot-health.service'})
        self.assertTrue((wants / 'sv08-boot-health.service').resolve().is_file())


if __name__ == '__main__':
    unittest.main()
