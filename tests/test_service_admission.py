from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_admission import Admission, KLIPPER, MOONRAKER


class Services:
    def __init__(self):
        self.states = {KLIPPER: 'active', MOONRAKER: 'active'}
        self.calls = []
    def state(self, name): return self.states[name]
    def stop(self, name): self.calls.append(('stop', name)); self.states[name] = 'inactive'
    def start(self, name): self.calls.append(('start', name)); self.states[name] = 'active'


class ServiceAdmissionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.runtime = Path(tmp.name)
        self.services = Services()
        uid = patch('sv08_admission.os.geteuid', return_value=0); uid.start(); self.addCleanup(uid.stop)

    def test_refusal_does_not_stop_services(self):
        def refuse(path): raise ValueError('printing')
        with self.assertRaises(ValueError), Admission(self.runtime, self.services, refuse)():
            self.fail('Admitted')
        self.assertEqual(self.services.calls, [])

    def test_stops_only_after_ack_holds_barrier_and_restores_after_body_error(self):
        import fcntl
        def accepted(path):
            self.assertEqual(self.services.calls, [])
        with self.assertRaisesRegex(OSError, 'installer failure'):
            with Admission(self.runtime, self.services, accepted)():
                self.assertEqual(set(self.services.states.values()), {'inactive'})
                with (self.runtime/'admission.lock').open('a') as other:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                raise OSError('installer failure')
        self.assertEqual(self.services.calls, [('stop', KLIPPER), ('stop', MOONRAKER),
                                               ('start', KLIPPER), ('start', MOONRAKER)])

    def test_initially_stopped_services_are_not_started(self):
        self.services.states = {KLIPPER: 'inactive', MOONRAKER: 'failed'}
        with Admission(self.runtime, self.services, lambda path: self.fail('Unnecessary request'))(): pass
        self.assertEqual(self.services.calls, [])

    def test_transition_or_unresolved_stop_does_not_enqueue_start(self):
        self.services.states[MOONRAKER] = 'activating'
        with self.assertRaises(ValueError), Admission(self.runtime, self.services, lambda path: None)(): pass
        self.assertEqual(self.services.calls, [])
        self.services.states[MOONRAKER] = 'active'
        with patch.object(self.services, 'stop', side_effect=TimeoutError('unresolved stop')):
            with self.assertRaises(TimeoutError), Admission(self.runtime, self.services, lambda path: None)(): pass
        self.assertEqual(self.services.calls, [])
