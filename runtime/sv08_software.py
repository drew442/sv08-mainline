#!/usr/bin/env python3
"""Reviewed catalog APT operations; fixed installed paths and durable private jobs.

Offline reports are not derived image validation. Customizations always retain
image activation's existing reconciliation gate. No package purge or autoremove.
"""
import argparse
import base64
import stat
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid
from sv08_state import Store, atomic_json
from sv08_admission import Admission
from sv08_package import require_writable, SERVICES

CATALOG = [dict(package=name, title=title, service=service) for name, title, service in
           [('nano', 'Nano text editor', None), ('htop', 'Process monitor', None),
            ('tmux', 'Terminal multiplexer', None), ('vnstat', 'Network usage statistics', 'vnstat.service')]]
MIB = 1024 * 1024
ROOT_RESERVE = 256 * MIB
MAX_RECORD = 2 * MIB
MAX_JOBS = 64
GUARD = b'#!/bin/sh\n# SV08 admitted package operation: explicit service action required.\nexit 101\n'
TOKEN = re.compile(r'^[0-9a-f]{32}$')
PROTECTED = re.compile(r'^(?:linux|u-boot|grub|initramfs|systemd|libsystemd|rauc|sv08|klipper|moonraker|cockpit|openssh|network-manager|sudo|apt|dpkg|libc6)(?:[-:.]|$)')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def private_directory(path):
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink(): raise ValueError('Software storage contains a symlink')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('Software storage must be private and administrator-owned')


def read_record(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_RECORD:
        raise ValueError('Invalid software record')
    return json.loads(path.read_text())


def same_review(current, plan):
    def stable(value):
        return {key:item for key,item in value.items() if key not in ('root_free_bytes','data_free_bytes')}
    return (current['binding'] == plan['binding'] and current['available'] == plan['available'] and
            stable(current['preview']) == stable(plan['preview']))


@contextmanager
def null_guard():
    yield


class Apt:
    """All executables and options are fixed; only catalog names enter commands."""
    def __init__(self, root=Path('/'), runtime=Path('/run/sv08')):
        self.root, self.runtime = Path(root), Path(runtime)

    def run(self, command, timeout=120, token=None):
        if command[0] in ('apt-get','apt-cache','apt-mark'):
            # Resolve from the signed lists in memory. Preview/status must not
            # create tens of MiB of cache files on an immutable or small root.
            command = [command[0], '-o', 'Dir::Cache::pkgcache=',
                       '-o', 'Dir::Cache::srcpkgcache=', *command[1:]]
        env = dict(os.environ, LC_ALL='C', LANG='C', DEBIAN_FRONTEND='noninteractive')
        if token: env['SV08_PACKAGE_TOKEN'] = token
        # The admission lease covers every dpkg/maintainer-script descendant,
        # including timeout teardown. Killing only apt-get releases it too soon.
        deadline = time.monotonic() + timeout
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            output, _ = process.communicate(timeout=timeout)
        except BaseException:
            self.stop_group(process)
            raise
        if token:
            # A successful leader can leave a background script. Wait under the
            # lease; terminate stragglers when the operation deadline is reached.
            while self.group_live(process.pid):
                if time.monotonic() >= deadline:
                    self.stop_group(process)
                    raise ValueError('Software descendants exceeded the operation deadline')
                time.sleep(.05)
        if process.returncode: raise ValueError('Software command failed: '+command[0]+' (exit '+str(process.returncode)+')')
        if len(output.encode()) > MAX_RECORD: raise ValueError('Software command report is too large')
        return output

    @staticmethod
    def group_live(group):
        for path in Path('/proc').glob('[0-9]*/stat'):
            try:
                fields = path.read_text().rsplit(') ', 1)[1].split()
                if int(fields[2]) == group and fields[0] not in ('Z', 'X'):
                    return True
            except (OSError, ValueError, IndexError):
                continue
        return False

    @classmethod
    def stop_group(cls, process):
        def send(sig):
            try: os.killpg(process.pid, sig)
            except ProcessLookupError: pass
        send(signal.SIGTERM)
        try: process.communicate(timeout=3)
        except subprocess.TimeoutExpired: pass
        send(signal.SIGKILL)
        # An uninterruptible child must keep printer admission held until it
        # exits. Zombies cannot execute writes and do not retain the lease.
        while cls.group_live(process.pid):
            send(signal.SIGKILL)
            time.sleep(.05)
        process.communicate()

    def inventory(self):
        rows = self.run(['dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\t${db:Status-Abbrev}\n'])
        return [line.split('\t') for line in rows.splitlines() if line.endswith('ii ') or '\tii ' in line]

    def evidence(self):
        hashes = {}
        # Never read auth.conf or private key material. URL/config contents are
        # represented only by hashes, not returned through the browser.
        paths = [self.root/'etc/apt/sources.list', self.root/'etc/apt/preferences']
        for directory in ('etc/apt/sources.list.d', 'etc/apt/preferences.d', 'etc/apt/apt.conf.d',
                          'var/lib/apt/lists', 'etc/systemd/system/vnstat.service.d'):
            parent = self.root/directory
            if parent.is_dir(): paths.extend(p for p in parent.rglob('*') if p.is_file())
        for path in sorted(paths):
            if path.is_symlink():
                hashes[str(path.relative_to(self.root))] = 'symlink:'+str(path.readlink())
            elif path.is_file():
                h = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(65536), b''): h.update(chunk)
                hashes[str(path.relative_to(self.root))] = h.hexdigest()
        return dict(inventory=self.inventory(), manual=self.run(['apt-mark', 'showmanual']).splitlines(), held=self.run(['apt-mark', 'showhold']).splitlines(),
                    configuration=hashes, service=self.service())

    def worker_state(self, ident):
        return self.run(['systemctl','show','-p','ActiveState','--value','sv08-software-worker@'+ident+'.service']).strip()

    def service(self):
        result = {}
        for field in ('ActiveState', 'UnitFileState'):
            result[field] = self.run(['systemctl', 'show', '-p', field, '--value', 'vnstat.service']).strip()
        return result

    def command(self, action, package):
        return ['apt-get', '-o', 'Dir::Cache::pkgcache=', '-o', 'Dir::Cache::srcpkgcache=', '-o', 'Dpkg::Lock::Timeout=0', '-o', 'APT::Get::AutomaticRemove=false',
                '-o', 'APT::Get::AllowUnauthenticated=false', '-o', 'APT::Get::allow-Downgrades=false',
                '-o', 'APT::Get::allow-Remove-Essential=false', '-o', 'APT::Get::allow-Change-Held-Packages=false',
                '--no-install-recommends', *(['--no-remove'] if action == 'install' else []), action, package]

    def audit(self):
        return self.run(['dpkg','--audit']).strip()

    def simulate(self, action, package, inventory):
        if self.audit(): raise ValueError('dpkg has unfinished package state; administrator recovery required')
        command = self.command(action, package)
        output = self.run(command[:1]+['--simulate']+command[1:])
        installs, removes = [], []
        installed = {row[0].split(':')[0]: row[1] for row in inventory}
        for line in output.splitlines():
            if line.startswith('Inst '):
                match = re.match(r'Inst (\S+)(?: \[[^]]+\])? \((\S+)', line)
                if not match: raise ValueError('Unsupported APT simulation output')
                name, version = match.groups()
                if PROTECTED.match(name) or (name.split(':')[0] in installed and name.split(':')[0] not in {c['package'] for c in CATALOG}):
                    raise ValueError('Dependency change affects protected or existing system software: '+name)
                installs.append(dict(package=name, version=version))
            elif line.startswith('Remv '):
                name = line.split()[1]
                if action != 'remove' or name.split(':')[0] != package:
                    raise ValueError('Removal would affect other software: '+name)
                removes.append(name)
        if action == 'remove' and installs: raise ValueError('Removal requires additional package changes')
        download, delta = 0, 0
        for item in installs:
            metadata = self.run(['apt-cache', '-o', 'Dir::Cache::pkgcache=', '-o', 'Dir::Cache::srcpkgcache=', 'show', item['package']+'='+item['version']])
            fields = dict(re.findall(r'^(Size|Installed-Size): (\d+)$', metadata, re.M))
            if set(fields) != {'Size', 'Installed-Size'}: raise ValueError('Package size metadata is unavailable')
            download += int(fields['Size']); delta += int(fields['Installed-Size'])*1024
        if package in self.run(['apt-mark', 'showhold']).splitlines(): raise ValueError('Selected software is held; preserve the administrator pin')
        # Conservative: do not subtract replaced/removed package size or caches.
        return dict(install=installs, remove=removes, download_bytes=download,
                    installed_delta_bytes=delta, simulation_digest=digest(output))

    def root_capacity(self, needed, writable=True):
        fs = os.statvfs(self.root)
        if writable and fs.f_flag & os.ST_RDONLY: raise ValueError('Root filesystem is read-only')
        free = fs.f_bavail * fs.f_frsize
        if free < needed + ROOT_RESERVE or fs.f_favail < 1024:
            raise ValueError('Insufficient root space or inodes; keep 256 MiB recovery headroom')
        return dict(root_free_bytes=free, required_bytes=needed+ROOT_RESERVE)

    def stopped(self):
        states = {name: self.run(['systemctl', 'show', '-p', 'ActiveState', '--value', name]).strip() for name in SERVICES}
        for name in ('klipper.service', 'moonraker.service', 'octoprint.service'):
            value = self.run(['systemctl', 'show', '-p', 'ActiveState', '--value', name]).strip()
            if value not in ('inactive', 'failed', ''): raise ValueError('Unmanaged printer service is running: '+name)
        return states

    def locks(self):
        handles = []
        try:
            for name in ('var/lib/dpkg/lock-frontend', 'var/lib/dpkg/lock'):
                fd = os.open(self.root/name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
                handles.append(fd); fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('APT/dpkg is busy; review again') from None
        finally:
            for fd in handles: os.close(fd)

    def execute(self, action, arguments, token):
        if action in ('install', 'remove'):
            vnstat = arguments['package'] == 'vnstat'
            installed = vnstat and any(row[0].split(':')[0] == 'vnstat' for row in self.inventory())
            previous = self.service() if installed and action == 'install' else None
            if vnstat and installed and action == 'remove':
                # policy-rc.d suppresses maintainer-script stop as well as start;
                # explicitly stop the unit before its files are removed.
                self.run(['systemctl', 'disable', '--now', 'vnstat.service'], token=token)
            command = self.command(action, arguments['package'])
            try:
                self.run(command[:1]+['--yes']+command[1:], timeout=1800, token=token)
            except Exception:
                # A postinst may enable the unit before a later trigger fails.
                # Keep the fresh-install intent while admission is still held.
                if vnstat and action == 'install' and not installed and (self.root/'usr/lib/systemd/system/vnstat.service').is_file():
                    self.run(['systemctl', 'disable', '--now', 'vnstat.service'], token=token)
                raise
            if vnstat and action == 'install':
                if not installed:
                    # Debian postinst can enable a unit for a later boot even
                    # when policy-rc.d refused its immediate start.
                    self.run(['systemctl', 'disable', '--now', 'vnstat.service'], token=token)
                else:
                    self.restore_service(previous, token)
        elif action == 'service':
            self.run(['systemctl', 'enable' if arguments['enabled'] else 'disable', '--now', 'vnstat.service'], token=token)

    def restore_service(self, previous, token):
        """Retain the existing user's enablement and activity across reinstall."""
        current = self.service()
        if current['UnitFileState'] != previous['UnitFileState']:
            commands = {'enabled': ['enable'], 'disabled': ['disable'],
                        'enabled-runtime': ['enable', '--runtime'],
                        'masked': ['mask'], 'masked-runtime': ['mask', '--runtime']}
            options = commands.get(previous['UnitFileState'])
            if options is None:
                raise ValueError('Existing vnstat service enablement changed; inspect the uncertain outcome')
            self.run(['systemctl', *options, 'vnstat.service'], token=token)
        was_active = previous['ActiveState'] == 'active'
        if (current['ActiveState'] == 'active') != was_active:
            self.run(['systemctl', 'start' if was_active else 'stop', 'vnstat.service'], token=token)


class Software:
    def __init__(self, store, boot, apt=None, admission=None, launch=None):
        self.store, self.boot = store, boot
        self.apt = apt or Apt()
        self.admission = admission or Admission()
        self.launch = launch or (lambda ident: subprocess.run(['systemctl', 'start', '--no-block', 'sv08-software-worker@'+ident+'.service'], check=True))
        self.root = store.root/'software'

    def setup(self):
        private_directory(self.root)
        for name in ('plans', 'jobs', 'exports'): private_directory(self.root/name)

    def write(self, path, value):
        if len(json.dumps(value).encode()) > MAX_RECORD: raise ValueError('Software record exceeds its limit')
        self.store.budget.check(MAX_RECORD, 2)
        atomic_json(path, value)

    def eligibility(self, state):
        if self.boot['mode'] != 'writable' or state['requested_mode'] != 'writable':
            raise ValueError('Package and service changes require writable mode applied at boot')
        if state['pending']: raise ValueError('Finish or cancel the pending image transaction first')
        journal = self.store.root/'update.json'
        if journal.exists() and read_record(journal).get('phase') not in ('complete', 'cancelled', 'failed'):
            raise ValueError('An image transaction is in progress')
        self.apt.stopped()  # Reject unmanaged printer services even during review.

    def validate(self, action, arguments):
        if action not in ('install', 'remove', 'service', 'reconcile', 'acknowledge') or not isinstance(arguments, dict): raise ValueError('Unknown software action')
        fields = {'id'} if action == 'acknowledge' else set() if action == 'reconcile' else ({'package', 'enabled'} if action == 'service' else {'package'})
        if set(arguments) != fields: raise ValueError('Unexpected software arguments')
        if action == 'acknowledge':
            if not isinstance(arguments['id'],str) or not TOKEN.fullmatch(arguments['id']): raise ValueError('Invalid unknown job identity')
            return
        if action != 'reconcile' and arguments['package'] not in {c['package'] for c in CATALOG}: raise ValueError('Choose software from the catalog')
        if action == 'service' and (arguments['package'] != 'vnstat' or type(arguments['enabled']) is not bool): raise ValueError('Only the vnstat service can be configured')

    def jobs(self):
        result = []
        for path in sorted((self.root/'jobs').glob('*.json')):
            if path.name.endswith('.policy.json'): continue
            record = read_record(path)
            if record['status'] in ('queued', 'running'):
                restarted = record['boot_id'] != self.boot['boot_id']
                stopped = time.time()-record['created_at'] > 30 and self.apt.worker_state(record['id']) not in ('active','activating','reloading')
                if restarted or stopped:
                    record = dict(record, status='unknown', message='Worker interrupted; inspect package state before continuing.')
            result.append(record)
        return result

    def busy(self, report=False):
        if not report and list((self.root/'jobs').glob('*.policy.json')): raise ValueError('Interrupted package service policy requires administrator recovery; preimage retained')
        if any(job['status'] in (('queued','running') if report else ('queued', 'running', 'unknown')) for job in self.jobs()):
            raise ValueError('A software job is pending or has an unknown outcome; inspect it before continuing')
        if len(self.jobs()) >= MAX_JOBS: raise ValueError('Software history is full; retained receipts require administrator review')

    def preview(self, action, arguments, state):
        reason = ''
        if action != 'reconcile':
            try: self.eligibility(state)
            except ValueError as error: reason = str(error)
        evidence = self.apt.evidence()
        if action == 'service' and 'vnstat' not in {row[0].split(':')[0] for row in evidence['inventory']}:
            raise ValueError('Install vnstat before configuring its service')
        preview = self.apt.simulate(action, arguments['package'], evidence['inventory']) if action in ('install', 'remove') else dict(install=[], remove=[], download_bytes=0, installed_delta_bytes=0)
        if action != 'reconcile': preview.update(self.apt.root_capacity(preview['download_bytes']+preview['installed_delta_bytes'], writable=not reason))
        if action in ('install', 'remove') and arguments['package'] == 'vnstat':
            installed = 'vnstat' in {row[0].split(':')[0] for row in evidence['inventory']}
            if action == 'remove':
                effect = 'Stop and disable vnstat before removing its package; preserve conffiles and user artifacts.'
            elif installed:
                effect = 'Preserve the existing vnstat service enablement and activity.'
            else:
                effect = 'Install vnstat stopped and disabled; enable it only through a separate reviewed service action.'
            preview['service_effect'] = effect
        if action == 'acknowledge': preview['outcome'] = self.inspect(arguments['id'])
        preview['data_free_bytes'] = os.statvfs(self.store.root).f_bavail * os.statvfs(self.store.root).f_frsize
        preview['data_reserve_bytes'] = self.store.budget.floor
        return dict(action=action, arguments=arguments, available=not reason, reason=reason, binding=digest(dict(state=state, boot=self.boot, evidence=evidence)), preview=preview,
                    preserves_user_data=True, reconciliation_required=True)

    def status_view(self, state, evidence):
        inventory = {row[0].split(':')[0]: row[1] for row in evidence['inventory']}
        reason = ''
        try: self.eligibility(state); self.busy()
        except ValueError as error: reason = str(error)
        return dict(boot=self.boot, requested_mode=state['requested_mode'], customized=state['slots'][self.boot['slot']]['customized'],
            catalog=[dict(item, installed=item['package'] in inventory, version=inventory.get(item['package']),
                service_state=evidence['service'] if item['service'] else None) for item in CATALOG],
            capabilities={name: dict(available=not reason or name == 'reconcile', reason='' if name == 'reconcile' else reason) for name in ('install','remove','service','reconcile')},
            storage=dict(root_free_bytes=os.statvfs(self.apt.root).f_bavail*os.statvfs(self.apt.root).f_frsize, root_reserve_bytes=ROOT_RESERVE,
                data_free_bytes=os.statvfs(self.store.root).f_bavail*os.statvfs(self.store.root).f_frsize, data_reserve_bytes=self.store.budget.floor),
            jobs=self.jobs(), reconciliation=dict(activation_blocked=state['slots'][self.boot['slot']]['customized'],
                reason='Customized roots require a validated derived image; this report cannot validate arbitrary root edits.', exports=[p.stem for p in sorted((self.root/'exports').glob('*.json'),key=lambda p:p.stat().st_mtime)]))


    def status(self):
        # Atomic receipts/cache remain readable while the write owner holds the
        # state lock for APT. Never wait for a long operation to display progress.
        lock = self.store.locked(nonblocking=True)
        try: lock.__enter__()
        except ValueError:
            cache = self.root/'status.json'
            cached = read_record(cache) if cache.exists() else self.status_view(self.store.load(),self.apt.evidence())
            cached['jobs'] = self.jobs()
            for name, capability in cached['capabilities'].items():
                capability.update(available=name=='reconcile', reason='' if name=='reconcile' else 'Software or image operation is running; progress remains available')
            return cached
        try:
            return self.status_view(self.store.load(),self.apt.evidence())
        finally: lock.__exit__(None,None,None)

    def plan(self, action, arguments):
        self.validate(action, arguments)
        with self.store.locked(nonblocking=True), self.store.budget.locked():
            self.setup(); self.prune()
            self.busy(report=action in ('reconcile','acknowledge'))
            if len(list((self.root/'plans').glob('*.json'))) >= MAX_JOBS: raise ValueError('Software review history is full')
            state = self.store.load()
            evidence = self.apt.evidence()
            self.write(self.root/'status.json',self.status_view(state,evidence))
            plan = self.preview(action, arguments, state)
            token = uuid.uuid4().hex
            plan.update(token=token, created_at=int(time.time()))
            plan['digest'] = digest(plan)
            self.write(self.root/'plans'/(token+'.json'), plan)
            return plan

    def apply(self, token, reviewed_digest):
        if not isinstance(token, str) or not TOKEN.fullmatch(token): raise ValueError('Invalid reviewed token')
        with self.store.locked(nonblocking=True), self.store.budget.locked():
            self.setup(); self.prune()
            path = self.root/'jobs'/(token+'.json')
            if path.exists():
                job = read_record(path)
                if job['digest'] != reviewed_digest: raise ValueError('Reviewed digest does not match')
                return job
            plan = read_record(self.root/'plans'/(token+'.json'))
            self.busy(report=plan['action'] in ('reconcile','acknowledge'))
            if plan['digest'] != reviewed_digest or digest({k:v for k,v in plan.items() if k != 'digest'}) != reviewed_digest:
                raise ValueError('Reviewed digest does not match')
            if not plan['available']: raise ValueError(plan['reason'])
            if time.time() - plan['created_at'] > 1800: raise ValueError('Software review expired; review again')
            current = self.preview(plan['action'], plan['arguments'], self.store.load())
            if not same_review(current, plan): raise ValueError('Software state changed; refresh and review again')
            job = dict(id=token, digest=reviewed_digest, action=plan['action'], arguments=plan['arguments'], status='queued', boot_id=self.boot['boot_id'], created_at=int(time.time()), message='Waiting for admitted worker')
            self.write(path, job)
        try: self.launch(token)
        except (OSError, subprocess.SubprocessError):
            with self.store.locked(), self.store.budget.locked():
                job.update(status='failed', message='Could not launch software worker; no package operation was requested')
                self.write(path, job)
        return job

    def reconcile(self, plan, evidence):
        compatible, conflicts = [], []
        names = {row[0].split(':')[0] for row in evidence['inventory']}
        for item in CATALOG:
            if item['package'] not in names: continue
            try:
                preview = self.apt.simulate('install', item['package'], evidence['inventory'])
                compatible.append(dict(package=item['package'], preview=preview))
            except ValueError as error: conflicts.append(dict(package=item['package'], reason=str(error)))
        record = dict(format_version=1, base_release=self.boot['release'], slot=self.boot['slot'], evidence=evidence,
                      requested_catalog=[c['package'] for c in CATALOG if c['package'] in names], compatible=compatible, conflicts=conflicts,
                      activation_blocked=True, reason='No derived candidate validated; arbitrary root edits and configuration changes require preservation and isolated image reconciliation.')
        export_path = self.root/'exports'/(plan['token']+'.json')
        if export_path.exists(): record['before_evidence'] = read_record(export_path).get('before_evidence',read_record(export_path)['evidence'])
        record['intended_operation'] = dict(action=plan['action'],arguments=plan['arguments'])
        self.write(export_path, record)
        return record

    @contextmanager
    def activation_guard(self, ident):
        """Suppress maintainer-script starts; preserve exact preimage privately.

        A crash leaves the blocking guard and its recovery receipt in place.
        Never guess how to restore a policy changed by another administrator.
        """
        path = self.apt.root/'usr/sbin/policy-rc.d'
        if path.is_symlink(): raise ValueError('Unsupported policy-rc.d symlink; administrator review required')
        existed = path.exists()
        preimage = path.read_bytes() if existed else b''
        if len(preimage) > 65536: raise ValueError('Unexpected policy-rc.d size')
        if existed and (path.stat().st_uid != os.geteuid() or path.stat().st_mode & 0o022): raise ValueError('Unsafe service policy ownership or permissions')
        mode = stat.S_IMODE(path.stat().st_mode) if existed else 0o755
        journal = self.root/'jobs'/(ident+'.policy.json')
        self.write(journal, dict(existed=existed, mode=mode, preimage=base64.b64encode(preimage).decode()))
        guard = GUARD
        temporary = path.with_name('.sv08-policy-'+ident)
        with temporary.open('xb') as stream:
            os.chmod(temporary,0o755); stream.write(guard); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary,path)
        from sv08_state import fsync_dir
        fsync_dir(path.parent)
        try: yield
        finally:
            if path.is_symlink() or path.read_bytes() != guard:
                raise ValueError('Package service policy changed; private preimage retained for administrator recovery')
            if existed:
                with temporary.open('xb') as stream:
                    os.chmod(temporary,mode); stream.write(preimage); stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary,path)
            else: path.unlink()
            fsync_dir(path.parent)
            journal.unlink(); fsync_dir(journal.parent)

    def prune(self):
        """Bound terminal metadata; never evict unknown or active outcomes.

        Customization exports are retained separately; one current report per
        slot remains sufficient for blocked reconciliation and rollback records.
        """
        from sv08_state import fsync_dir
        now = time.time()
        for path in (self.root/'plans').glob('*.json'):
            if (self.root/'jobs'/path.name).exists(): continue
            record = read_record(path)
            if now-record.get('created_at',now)>1800: path.unlink()
        terminal = sorted((j for j in self.jobs() if j['status'] in ('completed','failed') and j.get('prior_outcome') != 'unknown'),key=lambda j:j['created_at'])
        while len(self.jobs()) >= MAX_JOBS and terminal:
            job=terminal.pop(0)
            (self.root/'jobs'/(job['id']+'.json')).unlink()
            (self.root/'plans'/(job['id']+'.json')).unlink(missing_ok=True)
        exports=sorted((self.root/'exports').glob('*.json'),key=lambda p:p.stat().st_mtime)
        # Retain at least the newest report for each slot even at capacity.
        newest={}
        for path in exports: newest[read_record(path)['slot']]=path
        while len(exports)>=MAX_JOBS:
            removable=next((p for p in exports if p not in newest.values()),None)
            if removable is None: break
            removable.unlink(); exports.remove(removable)
        for name in ('plans','jobs','exports'): fsync_dir(self.root/name)

    def inspect(self, ident):
        target=next((job for job in self.jobs() if job['id']==ident),None)
        if target is None or target['status']!='unknown': raise ValueError('Inspect an unknown software outcome')
        policy=self.root/'jobs'/(ident+'.policy.json')
        recoverable=False
        if policy.exists():
            read_record(policy)
            path=self.apt.root/'usr/sbin/policy-rc.d'
            recoverable=not path.is_symlink() and path.is_file() and path.read_bytes()==GUARD
        audit=self.apt.audit()
        return dict(job=target,evidence=self.apt.evidence(),dpkg_audit=audit,
                    policy_recovery_required=policy.exists(),policy_recoverable=recoverable,
                    warning='Acknowledge uncertainty only after reviewing inventory. No package transaction will be replayed; customized image activation remains blocked.')

    def restore_policy(self, ident):
        journal=self.root/'jobs'/(ident+'.policy.json')
        if not journal.exists(): return
        record=read_record(journal)
        path=self.apt.root/'usr/sbin/policy-rc.d'
        if path.is_symlink() or not path.is_file() or path.read_bytes()!=GUARD:
            raise ValueError('Service policy differs from the known blocking guard; administrator recovery required')
        contents=base64.b64decode(record['preimage'],validate=True)
        if len(contents)>65536 or type(record['mode']) is not int: raise ValueError('Invalid policy recovery preimage')
        temporary=path.with_name('.sv08-policy-restore-'+ident)
        if record['existed']:
            with temporary.open('xb') as stream:
                os.chmod(temporary,record['mode']); stream.write(contents); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary,path)
        else: path.unlink()
        from sv08_state import fsync_dir
        fsync_dir(path.parent); journal.unlink(); fsync_dir(journal.parent)

    def worker(self, ident):
        if not TOKEN.fullmatch(ident): raise ValueError('Invalid job identity')
        with self.store.locked(nonblocking=True), self.store.budget.locked():
            self.setup(); path = self.root/'jobs'/(ident+'.json'); job = read_record(path)
            if job['status'] != 'queued': raise ValueError('Software job is not queued')
            if job['boot_id'] != self.boot['boot_id']: raise ValueError('Software job belongs to an earlier boot')
            plan = read_record(self.root/'plans'/(ident+'.json'))
            changed = False
            try:
                if plan['digest'] != job['digest']: raise ValueError('Job review mismatch')
                current = self.preview(plan['action'], plan['arguments'], self.store.load())
                if not same_review(current, plan): raise ValueError('Software state changed; review again')
                job.update(status='running', message='Applying reviewed software operation'); self.write(path, job)
                if plan['action'] == 'reconcile':
                    self.reconcile(plan, self.apt.evidence())
                elif plan['action'] == 'acknowledge':
                    with self.admission():
                        require_writable(self.boot,self.store.load(),self.apt.stopped())
                        self.apt.locks()
                        changed = True
                        self.restore_policy(plan['arguments']['id'])
                        target_path = self.root/'jobs'/(plan['arguments']['id']+'.json')
                        original = read_record(target_path)
                        original.update(status='acknowledged', prior_outcome='unknown', message='Uncertain outcome acknowledged after inventory inspection; no APT replay')
                        self.write(target_path,original)
                        self.reconcile(plan,self.apt.evidence())
                else:
                    with self.admission():
                        state = self.store.load()
                        require_writable(self.boot, state, self.apt.stopped())
                        current = self.preview(plan['action'], plan['arguments'], state)
                        # Admission legitimately stops services; package/repository
                        # evidence and preview must remain unchanged otherwise.
                        if not same_review(current, plan): raise ValueError('Software changed during admission; review again')
                        self.apt.locks()
                        state['slots'][self.boot['slot']]['customized'] = True; self.store.save(state)
                        self.reconcile(plan,self.apt.evidence())
                        changed = True
                        atomic_json(self.apt.runtime/'package-lease.json', dict(token=ident, pid=os.getpid()))
                        try:
                            with self.activation_guard(ident) if plan['action'] in ('install','remove') else null_guard():
                                self.apt.execute(plan['action'], plan['arguments'], ident)
                        finally: (self.apt.runtime/'package-lease.json').unlink(missing_ok=True)
                        self.reconcile(plan, self.apt.evidence())
                job.update(status='completed', message='Operation completed; customizations remain preserved and image reconciliation is required')
            except Exception as error:
                job.update(status='unknown' if changed else 'failed', message=str(error)[:240])
            self.write(path, job)
            return job

    def request(self, request):
        if not isinstance(request, dict): raise ValueError('Expected software request object')
        method = request.get('method')
        fields = {'status':{'method'}, 'plan':{'method','action','arguments'}, 'apply':{'method','token','digest'},
                  'job':{'method','id'}, 'inspect':{'method','id'}, 'reconciliation-export':{'method','id'}}.get(method)
        if fields is None or set(request) != fields: raise ValueError('Unknown software request fields')
        if method == 'status': return self.status()
        if method == 'plan': return self.plan(request['action'],request['arguments'])
        if method == 'apply': return self.apply(request['token'],request['digest'])
        ident = request['id']
        if not isinstance(ident,str) or not TOKEN.fullmatch(ident): raise ValueError('Invalid software identity')
        if method == 'inspect': return self.inspect(ident)
        if method == 'job':
            for job in self.jobs():
                if job['id'] == ident: return job
            raise ValueError('Software job not found')
        return read_record(self.root/'exports'/(ident+'.json'))


def installed():
    if os.geteuid() != 0: raise ValueError('Administrator access is required')
    context = json.loads(Path('/usr/lib/sv08/admin-context.json').read_text())
    if context != {'format_version':1,'context':'host'}: raise ValueError('Unsupported software context')
    catalog = json.loads(Path('/usr/lib/sv08/software-catalog.json').read_text())
    if catalog != {'format_version':1,'packages':CATALOG}: raise ValueError('Installed software catalog does not match the supported policy')
    boot = json.loads(Path('/run/sv08/boot.json').read_text())
    return Software(Store('/data/sv08'), boot)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--worker')
    args = parser.parse_args()
    try:
        backend = installed()
        if args.worker: result = backend.worker(args.worker)
        else:
            raw = sys.stdin.buffer.read(16385)
            if len(raw)>16384: raise ValueError('Software request is too large')
            result = backend.request(json.loads(raw))
        print(json.dumps(dict(ok=True,result=result)))
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        print(json.dumps(dict(ok=False,error=str(error))))
    return 0


if __name__ == '__main__': sys.exit(main())
