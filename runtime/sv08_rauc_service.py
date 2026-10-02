#!/usr/bin/env python3
"""Selected RAUC service observation and cooperative privileged writer lease.

The system-bus policy excludes ordinary callers. Supported privileged writers
hold this lease; uncooperative root intervention is outside the contract.
Never activate a service or fetch GetSlotStatus (which can clean persistent data).
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

NAME = 'de.pengutronix.rauc'
INTERFACE = NAME + '.Installer'
BINARY_SHA256 = '83e71fb2b88f2bf650baa5718dd172d3f7f4b8d94f3e9ac10f4f543e25d1d83b'
PACKAGE = '1.13-3+deb13u1'
PATH = '/usr/sbin:/usr/bin:/sbin:/bin'
SECONDS = 10


def bounded(path, size=65536):
    with Path(path).open('rb') as stream: value = stream.read(size+1)
    if len(value) > size: raise ValueError('RAUC evidence file exceeds its bound')
    return value


def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


class Busy(ValueError): pass


class Service:
    def __init__(self, lock=Path('/run/lock/sv08-rauc-writer.lock')):
        self.lock_path, self.depth = Path(lock), 0

    @contextmanager
    def writer(self):
        if self.depth:
            self.depth += 1
            try: yield
            finally: self.depth -= 1
            return
        if os.geteuid() != 0: raise ValueError('RAUC writer requires administrator access')
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o077:
                raise ValueError('Invalid RAUC writer lock')
            try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise ValueError('A supported RAUC writer is active') from None
            self.depth = 1
            try: yield
            finally: self.depth = 0
        finally: os.close(fd)

    def call(self, destination, interface, method, signature='', *arguments):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0: raise ValueError('RAUC observation timed out')
        obj = '/org/freedesktop/DBus' if destination == 'org.freedesktop.DBus' else '/'
        command = ['/usr/bin/busctl', '--system', '--json=short', '--auto-start=no',
                   '--allow-interactive-authorization=no', '--timeout='+str(remaining),
                   'call', destination, obj, interface, method]
        if signature: command += [signature, *arguments]
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=remaining, env={'PATH': PATH, 'LC_ALL': 'C'})
            if result.returncode:
                if method == 'GetArtifactStatus' and result.stderr.strip() == b'Call failed: already processing a different method':
                    raise Busy('RAUC service is internally busy')
                raise ValueError('RAUC service call refused')
            output = result.stdout
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError('RAUC service evidence unavailable, busy or timed out') from error
        if len(output) > 16384: raise ValueError('RAUC observation exceeds its bound')
        return json.loads(output)['data']

    def owner(self):
        owner = self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetNameOwner', 's', NAME)[0]
        if not re.fullmatch(r':[0-9]+\.[0-9]+', owner): raise ValueError('Invalid RAUC unique owner')
        return owner

    def identity(self, owner):
        pid = self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetConnectionUnixProcessID', 's', owner)[0]
        process = Path('/proc') / str(pid)
        if (process/'exe').resolve() != Path('/usr/bin/rauc') or digest(process/'exe') != BINARY_SHA256:
            raise ValueError('Unsupported RAUC service executable')
        if bounded(process/'cmdline') != b'/usr/bin/rauc\0--mount=/run/rauc/mnt\0service\0':
            raise ValueError('Unexpected RAUC service arguments')
        environment = dict(item.split(b'=', 1) for item in bounded(process/'environ').split(b'\0') if item)
        if environment.get(b'PATH') != PATH.encode(): raise ValueError('Unexpected RAUC helper PATH')
        if (os.stat(process/'root').st_dev, os.stat(process/'root').st_ino) != (os.stat('/').st_dev, os.stat('/').st_ino):
            raise ValueError('RAUC service has a different filesystem root')
        unit_output = subprocess.check_output(['/usr/bin/systemctl', 'show', 'rauc.service', '--property=MainPID,InvocationID,FragmentPath,DropInPaths,ActiveState'], timeout=max(.001,self.deadline-time.monotonic()), text=True)
        if len(unit_output) > 4096: raise ValueError('RAUC unit evidence exceeds its bound')
        unit = dict(line.split('=',1) for line in unit_output.splitlines())
        if unit.get('MainPID') != str(pid) or not re.fullmatch('[0-9a-f]{32}',unit.get('InvocationID','')) or unit.get('ActiveState') != 'active' or unit.get('FragmentPath') != '/usr/lib/systemd/system/rauc.service' or unit.get('DropInPaths') != '/etc/systemd/system/rauc.service.d/sv08.conf':
            raise ValueError('Unexpected RAUC systemd invocation')
        paths = ['/etc/rauc/system.conf', '/etc/rauc/release-keyring.pem', '/etc/fw_env.config',
                 '/usr/bin/fw_printenv', '/usr/lib/systemd/system/rauc.service',
                 '/etc/systemd/system/rauc.service.d/sv08.conf', '/etc/dbus-1/system.d/zz-sv08-rauc.conf']
        hashes = {}
        for path in paths:
            service_path = process / 'root' / path.lstrip('/')
            if not os.statvfs(service_path).f_flag & os.ST_RDONLY or not os.statvfs(path).f_flag & os.ST_RDONLY:
                raise ValueError('RAUC execution/configuration identity is not immutable')
            hashes[path] = digest(service_path)
            if hashes[path] != digest(path): raise ValueError('RAUC namespace configuration differs')
        return dict(pid=pid, unit=unit, start_ticks=bounded(process/'stat').decode().rsplit(')', 1)[1].split()[19],
                    executable_sha256=BINARY_SHA256, package=PACKAGE, files=hashes,
                    mountinfo_sha256=digest(process/'mountinfo'))

    def observe(self):
        if not self.depth: raise ValueError('RAUC observation requires writer exclusion')
        self.deadline = time.monotonic() + SECONDS
        bus = self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetId')[0]
        owner = self.owner()
        if self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetConnectionUnixUser', 's', owner) != [0]:
            raise ValueError('Unexpected RAUC service credentials')
        identity = self.identity(owner)
        # Exact selected source checks internal busy before serializing this
        # empty in-memory table. Configuration validation forbids repositories.
        if self.call(owner, INTERFACE, 'GetArtifactStatus') != [[]]:
            raise ValueError('RAUC artifact repositories are unsupported')
        props = {}
        for key in ('Operation', 'Compatible', 'Variant', 'BootSlot'):
            value = self.call(owner, 'org.freedesktop.DBus.Properties', 'Get', 'ss', INTERFACE, key)[0]
            props[key] = value['data']
        if props['Operation'] != 'idle': raise ValueError('RAUC service is busy')
        primary = self.call(owner, INTERFACE, 'GetPrimary')[0]
        if primary not in ('rootfs.0', 'rootfs.1'): raise ValueError('Unknown RAUC primary')
        if self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetId')[0] != bus or self.owner() != owner or self.identity(owner) != identity:
            raise ValueError('RAUC owner or execution identity changed')
        return dict(bus=bus, owner=owner, identity=identity, properties=props, primary=primary)

    def mark(self, action, slot):
        evidence = self.observe()
        self.call(evidence['owner'], INTERFACE, 'Mark', 'ss', action, slot)
        if self.owner() != evidence['owner']: raise ValueError('RAUC owner changed during mark')

    def install(self, bundle):
        evidence = self.observe()
        owner = evidence['owner']
        self.call(owner, INTERFACE, 'InstallBundle', 'sa{sv}', bundle, '0')
        # The service owns installation after the method returns. Lease loss is
        # not inactivity; subsequent callers must pass the internal busy guard.
        while True:
            self.deadline = time.monotonic() + SECONDS
            if self.owner() != owner: raise ValueError('RAUC owner changed during install')
            try:
                artifacts = self.call(owner, INTERFACE, 'GetArtifactStatus')
            except Busy:
                time.sleep(.2)
                continue
            if artifacts != [[]]: raise ValueError('Unexpected artifact repository')
            final = self.observe()
            if final['owner'] != owner: raise ValueError('RAUC owner changed during install')
            error = self.call(owner, 'org.freedesktop.DBus.Properties', 'Get', 'ss', INTERFACE, 'LastError')[0]['data']
            if error: raise ValueError('RAUC installation failed: '+error[:1000])
            return
