#!/usr/bin/env python3
"""Local idle service admission for image/package operations.

The Klipper extension must atomically accept quiescence; HTTP idle polling never
permits stopping a running service. The shared flock also blocks service starts.
This is an integration callback, not an enabled automatic update scheduler.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess

KLIPPER = 'sv08-klipper.service'
MOONRAKER = 'sv08-moonraker.service'


def quiesce(path, timeout=3.):
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as connection:
        connection.settimeout(timeout)
        connection.connect(str(path))
        connection.sendall(b'{"action":"quiesce"}')
        packet, _, flags, _ = connection.recvmsg(4096)
        if flags & socket.MSG_TRUNC:
            raise ValueError('Oversized idle admission response')
        result = json.loads(packet)
        if result.get('accepted') is not True or result.get('wait_for_service_exit') is not True:
            raise ValueError('Idle admission refused: '+str(result.get('reason', 'invalid response')))
        return result


class Systemd:
    def state(self, name):
        return subprocess.check_output(['systemctl', 'show', '-p', 'ActiveState', '--value', name], text=True).strip()

    def stop(self, name):
        subprocess.run(['systemctl', 'stop', name], check=True, timeout=120)
        if self.state(name) not in ('inactive', 'failed'):
            raise ValueError('Service did not stop: '+name)

    def start(self, name):
        subprocess.run(['systemctl', 'start', name], check=True, timeout=120)


class Admission:
    def __init__(self, runtime=Path('/run/sv08'), systemd=None, request=quiesce):
        self.runtime = Path(runtime)
        self.systemd = systemd if systemd is not None else Systemd()
        self.request = request

    @contextmanager
    def __call__(self):
        if os.geteuid() != 0:
            raise ValueError('Service admission requires root')
        lock = os.open(self.runtime / 'admission.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        restore = []
        entered = False
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            states = {name: self.systemd.state(name) for name in (KLIPPER, MOONRAKER)}
            if any(state not in ('active', 'inactive', 'failed') for state in states.values()):
                raise ValueError('Printer services are transitioning; retry after they settle')
            if states[KLIPPER] == 'active':
                self.request(self.runtime / 'printer_data/comms/update.sock')
                # ACK means the G-code mutex remains held until Klipper exits.
                # Keep the process-start barrier through stop and all writes.
                self.systemd.stop(KLIPPER)
                restore.append(KLIPPER)
            if states[MOONRAKER] == 'active':
                self.systemd.stop(MOONRAKER)
                restore.append(MOONRAKER)
            entered = True
            yield
        finally:
            os.close(lock)
            # A failed/timeout stop can leave an outstanding systemd job. Do not
            # enqueue a competing start in that case; surface the failure.
            if entered:
                for name in restore:
                    self.systemd.start(name)
