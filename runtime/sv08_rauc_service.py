#!/usr/bin/env python3
"""Selected RAUC service observation and exclusion for supported writers."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

POLICY = Path('/usr/lib/sv08/rauc-service-policy.json')
LOCK = Path('/run/lock/sv08-rauc-writer.lock')
TIMEOUT = 10


class Service:
    def __init__(self, policy=POLICY, lock=LOCK, runner=subprocess.run):
        self.policy_path, self.lock_path, self.runner, self.depth = Path(policy), Path(lock), runner, 0

    def policy(self):
        value = json.loads(self.policy_path.read_text())
        required = {'format_version', 'package', 'version', 'executable', 'executable_sha256', 'service', 'bus_name', 'config_paths'}
        if (not isinstance(value, dict) or set(value) != required or value.get('format_version') != 1 or
                value.get('package') != 'rauc' or value.get('bus_name') != 'de.pengutronix.rauc' or
                value.get('executable') != '/usr/bin/rauc' or not re.fullmatch('[0-9a-f]{64}', value.get('executable_sha256', '')) or
                not isinstance(value.get('config_paths'), list) or not all(isinstance(path, str) and path.startswith('/') for path in value['config_paths'])):
            raise ValueError('Invalid selected RAUC service policy')
        return value

    @contextmanager
    def writer(self):
        if self.depth:
            self.depth += 1
            try: yield
            finally: self.depth -= 1
            return
        if os.geteuid() != 0: raise ValueError('RAUC writer requires administrator access')
        self.lock_path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o077:
                raise ValueError('Invalid RAUC writer lock')
            try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error: raise ValueError('A supported RAUC writer is active') from error
            self.depth = 1
            try: yield
            finally: self.depth = 0
        finally: os.close(fd)

    def call(self, destination, interface, method, signature='', *arguments):
        object_path = '/org/freedesktop/DBus' if destination == 'org.freedesktop.DBus' else '/'
        command = ['/usr/bin/busctl', '--system', '--auto-start=no', '--allow-interactive-authorization=no', '--json=short', '--timeout='+str(TIMEOUT), 'call', destination, object_path, interface, method]
        if signature: command.extend([signature, *arguments])
        try:
            result = self.runner(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=TIMEOUT, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
        except (OSError, subprocess.SubprocessError) as error: raise ValueError('RAUC service evidence unavailable, busy or timed out') from error
        if result.returncode:
            if 'already processing a different method' in (result.stderr or ''): raise ValueError('RAUC service is internally busy')
            raise ValueError('RAUC service call refused')
        if len(result.stdout.encode()) > 32 * 1024: raise ValueError('RAUC service response exceeds its bound')
        try: return json.loads(result.stdout)['data']
        except (KeyError, json.JSONDecodeError, TypeError) as error: raise ValueError('Invalid RAUC service response') from error

    @staticmethod
    def digest(path):
        with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

    def owner(self, name):
        owner = self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetNameOwner', 's', name)[0]
        if not isinstance(owner, str) or not re.fullmatch(r':[0-9]+\.[0-9]+', owner): raise ValueError('Invalid RAUC service owner')
        return owner

    def identity(self, owner, policy):
        pid = self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetConnectionUnixProcessID', 's', owner)[0]
        if type(pid) is not int or pid <= 1: raise ValueError('Invalid RAUC service process')
        process = Path('/proc') / str(pid)
        if (process / 'exe').resolve() != Path(policy['executable']) or self.digest(process / 'exe') != policy['executable_sha256']:
            raise ValueError('Unexpected RAUC service executable')
        version = subprocess.check_output(['/usr/bin/dpkg-query', '-W', '-f=${Version}', policy['package']], text=True, timeout=TIMEOUT, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}).strip()
        if version != policy['version']: raise ValueError('Unexpected RAUC service package version')
        unit = subprocess.check_output(['/usr/bin/systemctl', 'show', policy['service'], '--property=MainPID,InvocationID,ActiveState,FragmentPath,DropInPaths'], text=True, timeout=TIMEOUT, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
        values = dict(line.split('=', 1) for line in unit.splitlines())
        if (values.get('MainPID') != str(pid) or values.get('ActiveState') != 'active' or not re.fullmatch('[0-9a-f]{32}', values.get('InvocationID', '')) or values.get('FragmentPath') != '/usr/lib/systemd/system/rauc.service' or values.get('DropInPaths') != '/etc/systemd/system/rauc.service.d/sv08.conf'):
            raise ValueError('Unexpected RAUC systemd invocation')
        files = {}
        for name in policy['config_paths']:
            path = Path(name)
            if not path.is_file() or not os.statvfs(path).f_flag & os.ST_RDONLY: raise ValueError('RAUC execution/configuration identity is mutable or missing')
            files[name] = self.digest(path)
        return {'pid': pid, 'executable_sha256': policy['executable_sha256'], 'package': version, 'unit': values, 'files': files}

    def observe(self):
        if not self.depth: raise ValueError('RAUC observation requires writer exclusion')
        policy = self.policy(); name = policy['bus_name']; bus = self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetId')[0]; owner = self.owner(name)
        if self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetConnectionUnixUser', 's', owner) != [0]: raise ValueError('Unexpected RAUC service credentials')
        identity = self.identity(owner, policy)
        operation = self.call(owner, 'org.freedesktop.DBus.Properties', 'Get', 'ss', name+'.Installer', 'Operation')[0]
        if not isinstance(operation, dict) or operation.get('data') != 'idle': raise ValueError('RAUC service is busy')
        # RAUC 1.15.2 checks its internal busy flag before GetSlotStatus.
        slots = self.call(owner, name+'.Installer', 'GetSlotStatus')
        if not slots: raise ValueError('RAUC slot observation is unavailable')
        if self.call('org.freedesktop.DBus', 'org.freedesktop.DBus', 'GetId')[0] != bus or self.owner(name) != owner or self.identity(owner, policy) != identity:
            raise ValueError('RAUC service owner or identity changed during observation')
        return {'bus': bus, 'owner': owner, 'identity': identity, 'operation': 'idle', 'busy_guard': 'GetSlotStatus', 'slot_status_sha256': hashlib.sha256(json.dumps(slots, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
