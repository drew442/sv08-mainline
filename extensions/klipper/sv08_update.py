# Local idle admission for image-managed SV08 hosts.
# Uses Klipper's extension, reactor and G-code mutex interfaces; no core patch.
import errno
import json
import math
import os
import socket
import stat


class SV08Update:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.path = config.get('socket_path', '/run/sv08/printer_data/comms/update.sock')
        self.max_temperature = config.getfloat('max_temperature', 50., minval=1., maxval=50.)
        self.listener = self.handler = None
        self.bound_identity = None
        self.clients = {}
        self.printer.register_event_handler('klippy:ready', self.ready)
        self.printer.register_event_handler('klippy:disconnect', self.close)

    def ready(self):
        if os.path.lexists(self.path):
            existing = os.lstat(self.path)
            if not stat.S_ISSOCK(existing.st_mode) or existing.st_uid != os.getuid():
                raise ValueError('Unexpected update socket path')
            with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as probe:
                probe.settimeout(.1)
                try:
                    probe.connect(self.path)
                except OSError as error:
                    if error.errno != errno.ECONNREFUSED:
                        raise
                else:
                    raise ValueError('An update admission listener already exists')
            os.unlink(self.path)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        try:
            listener.setblocking(False)
            listener.bind(self.path)
        except Exception:
            listener.close()
            raise
        self.listener = listener
        bound = os.lstat(self.path)
        self.bound_identity = (bound.st_dev, bound.st_ino)
        os.chmod(self.path, 0o600)
        self.listener.listen(1)
        self.handler = self.reactor.register_fd(self.listener.fileno(), self.accept)

    def accept(self, eventtime):
        if self.listener is None:
            return
        try:
            client, _ = self.listener.accept()
        except BlockingIOError:
            return
        client.setblocking(False)
        if self.clients:
            client.close()
            return
        fd = client.fileno()
        handler = self.reactor.register_fd(fd, lambda eventtime: self.request(fd, eventtime))
        # No client can retain a G-code lock simply by connecting: the lock is
        # acquired only after receiving the complete one-packet request.
        timer = self.reactor.register_timer(lambda eventtime: self.expire(fd), eventtime+5.)
        self.clients[fd] = (client, handler, timer)

    def expire(self, fd):
        self.drop(fd)
        return self.reactor.NEVER

    def drop(self, fd):
        client = self.clients.pop(fd, None)
        if client:
            connection, handler, timer = client
            if handler is not None:
                self.reactor.unregister_fd(handler)
            if timer is not None:
                self.reactor.unregister_timer(timer)
            connection.close()

    def require_idle(self, eventtime):
        if self.printer.get_state_message()[1] != 'ready':
            raise ValueError('Klipper is not ready')
        for name in ('virtual_sdcard', 'pause_resume', 'print_stats', 'idle_timeout', 'toolhead', 'heaters'):
            if self.printer.lookup_object(name, None) is None:
                raise ValueError('Missing required idle status: '+name)
        if self.printer.lookup_object('virtual_sdcard').is_active():
            raise ValueError('A print is active')
        if self.printer.lookup_object('pause_resume').get_status(eventtime)['is_paused']:
            raise ValueError('A print is paused')
        if self.printer.lookup_object('print_stats').get_status(eventtime)['state'] not in ('standby', 'complete', 'cancelled'):
            raise ValueError('Print state is not idle')
        if self.printer.lookup_object('idle_timeout').get_status(eventtime)['state'] != 'Idle':
            raise ValueError('Configured idle timeout has not elapsed')
        if self.printer.lookup_objects('manual_stepper'):
            raise ValueError('Independent manual-stepper queues need a reviewed admission policy')
        queued, estimated, empty = self.printer.lookup_object('toolhead').check_busy(eventtime)
        if not all(math.isfinite(v) for v in (queued, estimated)) or not empty or queued > estimated:
            raise ValueError('Motion remains queued')
        heaters = self.printer.lookup_object('heaters')
        names = heaters.get_all_heaters()
        if not names:
            raise ValueError('No heater status is available')
        for name in names:
            heater = heaters.lookup_heater(name.split()[-1])
            temperature, target = heater.get_temp(eventtime)
            power = heater.get_status(eventtime)['power']
            # Klipper get_temp returns zero for stale data. Refuse that value,
            # non-finite readings, commanded heat and recent nonzero PWM.
            if (not all(math.isfinite(v) for v in (temperature, target, power)) or
                    not 0. < temperature <= self.max_temperature or target != 0. or power != 0.):
                raise ValueError('Heater is hot, active or lacks fresh temperature data: '+name)

    def quiesce(self, acknowledge):
        gcode = self.printer.lookup_object('gcode')
        mutex = gcode.get_mutex()
        # Reactor callbacks do not interleave without yielding. Refuse an
        # occupied mutex instead of waiting behind a long-running print command.
        if mutex.test():
            raise ValueError('A G-code command is in progress')
        mutex.__enter__()
        committed = False
        try:
            self.require_idle(self.reactor.monotonic())
            acknowledge()  # No exit if the requesting client has disappeared.
            committed = True
            # Keep the mutex held through normal Klipper shutdown. Releasing it
            # before reactor termination could admit an already queued new print.
            try:
                gcode.request_restart('exit')
            except Exception:
                self.printer.request_exit('error_exit')
                raise
        finally:
            if not committed:
                mutex.__exit__()

    def request(self, fd, eventtime):
        client = self.clients.get(fd)
        if client is None:
            return
        connection, handler, timer = client
        self.reactor.unregister_timer(timer)
        self.clients[fd] = (connection, handler, None)
        try:
            packet, _, flags, _ = connection.recvmsg(512)
            if flags & socket.MSG_TRUNC or json.loads(packet) != {'action': 'quiesce'}:
                raise ValueError('Expected one quiesce request')
            # Remove the FD callback before any mutex wait/greenlet switch.
            self.reactor.unregister_fd(handler)
            self.clients[fd] = (connection, None, None)
            def acknowledge():
                response = b'{"accepted":true,"wait_for_service_exit":true}\n'
                if connection.send(response) != len(response):
                    raise ValueError('Client did not receive the admission response')
            self.quiesce(acknowledge)
        except Exception as error:
            # A malformed request or unsupported status must not crash Klipper.
            # If normal shutdown itself failed, quiesce already requested exit.
            try:
                connection.send(json.dumps({'accepted': False, 'reason': str(error)}).encode())
            except OSError:
                pass
        finally:
            self.drop(fd)

    def close(self):
        for fd in list(self.clients):
            self.drop(fd)
        if self.handler is not None:
            self.reactor.unregister_fd(self.handler)
            self.handler = None
        if self.listener is not None:
            self.listener.close()
            self.listener = None
            try:
                current = os.lstat(self.path)
                if (current.st_dev, current.st_ino) == self.bound_identity:
                    os.unlink(self.path)
            except FileNotFoundError:
                pass
            self.bound_identity = None


def load_config(config):
    return SV08Update(config)
