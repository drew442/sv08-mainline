"""Exercise the pinned real Klipper reactor/mutex/dispatcher without MCU I/O.

Only chelper's clock binding is replaced by time.monotonic, avoiding its automatic
source-tree C build. Printer hardware/status objects are explicit test doubles.
"""
import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'extensions/klipper'))
from sv08_update import SV08Update


def source_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, REPO / 'upstream/klipper/klippy' / relative)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module

try:
    import greenlet
except ImportError:
    greenlet = None


@unittest.skipUnless(greenlet, 'requires python3-greenlet for pinned Klipper reactor')
class AdmissionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.path = str(Path(tmp.name)/'update.sock')
        # No import of chelper's auto-compiling implementation or bundled build.
        util = source_module('sv08_test_util', 'util.py')
        clock = SimpleNamespace(get_ffi=lambda: (None, SimpleNamespace(get_monotonic=time.monotonic)))
        with patch.dict(sys.modules, {'chelper': clock, 'util': util}):
            reactor_module = source_module('sv08_test_reactor', 'reactor.py')
        self.reactor = reactor_module.SelectReactor()
        self.addCleanup(self.reactor.finalize)
        self.events = {}; self.moves = []; self.exit_result = None
        self.objects = {}
        self.state = 'ready'; self.active = False; self.paused = False
        self.print_state = 'standby'; self.idle_state = 'Idle'
        self.busy = (0., 1., True); self.temperature = 25.; self.target = 0.; self.power = 0.
        self.manual = []
        printer = SimpleNamespace(get_reactor=lambda: self.reactor,
            get_start_args=lambda: {}, get_state_message=lambda: ('test', self.state),
            register_event_handler=lambda name, cb: self.events.setdefault(name, []).append(cb),
            lookup_object=lambda name, default=None: self.objects.get(name, default),
            lookup_objects=lambda name: self.manual if name == 'manual_stepper' else [],
            request_exit=self.exit, send_event=lambda *args: [],
            invoke_shutdown=lambda reason: setattr(self, 'state', 'shutdown'))
        self.objects.update(virtual_sdcard=SimpleNamespace(is_active=lambda: self.active),
            pause_resume=SimpleNamespace(get_status=lambda t: {'is_paused': self.paused}),
            print_stats=SimpleNamespace(get_status=lambda t: {'state': self.print_state}),
            idle_timeout=SimpleNamespace(get_status=lambda t: {'state': self.idle_state}),
            toolhead=SimpleNamespace(check_busy=lambda t: self.busy, get_last_move_time=lambda: 0.,
                dwell=lambda duration: self.reactor.pause(self.reactor.monotonic()+.02), wait_moves=lambda: None),
            heaters=SimpleNamespace(get_all_heaters=lambda: ['extruder'], lookup_heater=lambda name:
                SimpleNamespace(get_temp=lambda t: (self.temperature, self.target),
                                get_status=lambda t: {'power': self.power})))
        gcode_module = source_module('sv08_test_gcode', 'gcode.py')
        self.gcode = self.objects['gcode'] = gcode_module.GCodeDispatch(printer)
        self.gcode.is_printer_ready = True
        self.gcode.register_command('TEST_MOVE', lambda cmd: self.moves.append('moved'), when_not_ready=True)
        config = SimpleNamespace(get_printer=lambda: printer,
            get=lambda key, default: self.path, getfloat=lambda *args, **kwargs: 50.)
        self.extension = SV08Update(config)
        self.addCleanup(self.extension.close)

    def exit(self, reason):
        self.exit_result = reason
        self.reactor.end()

    def run_loop(self, callback):
        self.reactor.register_callback(callback)
        self.reactor.register_callback(lambda t: self.exit('test-timeout'), self.reactor.monotonic()+1.)
        self.reactor.run()

    def test_pending_gcode_cannot_start_after_atomic_admission(self):
        acknowledgements = []
        attempted = []
        def pending(eventtime):
            attempted.append(True)
            self.gcode.run_script('TEST_MOVE')
        def enter(eventtime):
            def acknowledge():
                acknowledgements.append(True)
                self.reactor.register_callback(pending)
            self.extension.quiesce(acknowledge)
        self.run_loop(enter)
        self.assertEqual(self.exit_result, 'exit')
        self.assertEqual(acknowledgements, [True])
        self.assertEqual(attempted, [True])
        self.assertEqual(self.moves, [])
        self.assertTrue(self.gcode.get_mutex().test())

    def test_refusal_releases_mutex_and_preserves_command_processing(self):
        self.active = True
        def enter(eventtime):
            with self.assertRaises(ValueError): self.extension.quiesce(lambda: self.fail('Acknowledged busy printer'))
            self.gcode.run_script('TEST_MOVE')
            self.exit('done')
        self.run_loop(enter)
        self.assertEqual(self.moves, ['moved'])
        self.assertFalse(self.gcode.get_mutex().test())

    def test_unsafe_and_unknown_statuses_refused(self):
        for field, value in [('state', 'shutdown'), ('active', True), ('paused', True),
                ('print_state', 'printing'), ('print_state', 'error'), ('idle_state', 'Ready'),
                ('busy', (2., 1., True)), ('busy', (0., 1., False)),
                ('temperature', 51.), ('temperature', 0.), ('temperature', float('nan')),
                ('target', 1.), ('power', .1), ('manual', [('manual_stepper test', object())])]:
            previous = getattr(self, field); setattr(self, field, value)
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.extension.require_idle(time.monotonic())
            setattr(self, field, previous)
        self.objects.pop('print_stats')
        with self.assertRaises(ValueError): self.extension.require_idle(time.monotonic())

    def test_disappeared_client_does_not_commit_shutdown(self):
        def enter(eventtime):
            def disappeared(): raise BrokenPipeError('closed')
            with self.assertRaises(BrokenPipeError): self.extension.quiesce(disappeared)
            self.gcode.run_script('TEST_MOVE'); self.exit('done')
        self.run_loop(enter)
        self.assertEqual(self.moves, ['moved'])

    def test_real_local_socket_accepts_atomic_quiescence(self):
        self.extension.ready()
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as client:
            client.settimeout(1.)
            client.connect(self.path); client.send(b'{"action":"quiesce"}')
            self.reactor.register_callback(lambda t: self.exit('test-timeout'), time.monotonic()+1.)
            self.reactor.run()
            self.assertEqual(json.loads(client.recv(512)), {'accepted': True, 'wait_for_service_exit': True})
        self.assertEqual(self.exit_result, 'exit')
        self.assertEqual(self.extension.clients, {})

    def test_malformed_socket_request_never_exits_klipper(self):
        self.extension.ready()
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as client:
            client.settimeout(1.)
            client.connect(self.path); client.send(b'not-json')
            self.reactor.register_callback(lambda t: self.exit('test-end'), time.monotonic()+.05)
            self.reactor.run()
            self.assertFalse(json.loads(client.recv(512))['accepted'])
        self.assertEqual(self.exit_result, 'test-end')
        self.assertFalse(self.gcode.get_mutex().test())

    def test_stale_owned_socket_is_replaced_but_regular_files_are_preserved(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as stale:
            stale.bind(self.path)
        self.extension.ready(); self.extension.close()
        Path(self.path).write_text('preserve me')
        with self.assertRaises(ValueError): self.extension.ready()
        self.assertEqual(Path(self.path).read_text(), 'preserve me')

    def test_occupied_gcode_mutex_is_refused_without_waiting(self):
        def enter(eventtime):
            with self.gcode.get_mutex():
                with self.assertRaisesRegex(ValueError, 'in progress'):
                    self.extension.quiesce(lambda: self.fail('Acknowledged occupied mutex'))
            self.exit('done')
        self.run_loop(enter)
        self.assertEqual(self.exit_result, 'done')

    def test_emergency_stop_remains_callable_during_shutdown_wait(self):
        def enter(eventtime):
            def acknowledge():
                self.reactor.register_callback(lambda t: self.gcode.cmd_M112(None))
            self.extension.quiesce(acknowledge)
        self.run_loop(enter)
        self.assertEqual(self.state, 'shutdown')
        self.assertEqual(self.exit_result, 'exit')

    def test_expired_fd_callback_is_harmless(self):
        self.extension.request(12345, time.monotonic())
        self.assertIsNone(self.exit_result)
