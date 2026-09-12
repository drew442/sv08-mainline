#!/usr/bin/env python3
"""Finite administration API for Cockpit and the local recovery interface.

No shell, arbitrary path, or automatic hardware discovery. Root authorization is
provided by Cockpit's privileged bridge or the recovery session. See ADR 0010.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
from sv08_state import fsync_dir
from sv08_state import Store

ACTIONS = {
    'policy.auto': ('Automatic updates', 'Change the policy for future automatic staging and activation. An already armed update remains armed.'),
    'policy.mode': ('Operating mode', 'Apply this mode at the next normal boot. Existing files and customizations are preserved.'),
    'image.stage': ('Stage image', 'Verify and install the uploaded release into the inactive OS slot. Keep the running slot and user data.'),
    'image.arm': ('Use staged image next boot', 'Select the staged release for the next normal boot. Do not restart the printer now.'),
    'image.cancel': ('Cancel pending update', 'Keep the current release selected. Preserve the uploaded image and state generations.'),
    'software.install': ('Install additional software', 'Install the selected reviewed package in writable mode. Record the customization.'),
    'software.remove': ('Remove additional software', 'Remove the selected additional package. Preserve user artifacts.'),
    'config.hostname': ('Printer name', 'Save the persistent host name for the next boot. The current network connection is unchanged.'),
    'recovery.boot': ('Boot a preserved system', 'Select the reviewed preserved OS slot. Keep configuration and user files.'),
    'recovery.restore': ('Restore an OS image', 'Verify a signed image and replace only the selected OS slot. Preserve user data and the other slot.'),
    'recovery.export': ('Save user data', 'Copy readable configuration and user files to the selected removable destination.'),
    'recovery.check': ('Check storage', 'Inspect storage without repairing, formatting or changing files.'),
    'system.reboot': ('Restart when idle', 'Restart only after the printer accepts idle admission. Never interrupt a print.'),
}
HOST_ACTIONS = {key for key in ACTIONS if not key.startswith('recovery.')}
RECOVERY_ACTIONS = {key for key in ACTIONS if key.startswith('recovery.')}


def revision(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def atomic_text(path, text):
    temporary = path.with_name('.' + path.name + '-' + uuid.uuid4().hex)
    try:
        with temporary.open('x') as stream:
            os.chmod(temporary, 0o644)
            stream.write(text); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path); fsync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def hosts_with_name(text, new_name, old_name):
    """Preserve existing aliases; write this before changing the hostname file."""
    lines = text.splitlines()
    found = False
    for index, line in enumerate(lines):
        fields = line.split('#', 1)[0].split()
        if not fields: continue
        if new_name in fields[1:] and fields[0] != '127.0.1.1':
            raise ValueError('This name already has a custom hosts mapping; choose another name')
        if fields[0] == '127.0.1.1':
            found = True
            aliases = list(dict.fromkeys([*fields[1:], *([old_name] if old_name else []), new_name]))
            comment = ' #'+line.split('#', 1)[1] if '#' in line else ''
            lines[index] = '127.0.1.1\t'+' '.join(aliases)+comment
    if not found:
        lines.append('127.0.1.1\t'+' '.join(dict.fromkeys([*([old_name] if old_name else []), new_name])))
    return '\n'.join(lines)+'\n'


def snapshot(store, boot, context):
    """Caller holds the state lock. Never initialize or repair damaged state."""
    state = store.load()
    journal = store.root / 'update.json'
    if journal.is_symlink(): raise ValueError('Invalid update journal')
    transaction = json.loads(journal.read_text()) if journal.exists() else None
    name = store.root / 'system/hostname'
    if name.is_symlink() or name.parent.is_symlink(): raise ValueError('Invalid persistent hostname path')
    hostname = name.read_text().strip() if name.is_file() else None
    hosts = name.with_name('hosts')
    if hosts.is_symlink(): raise ValueError('Invalid persistent hosts path')
    hosts_text = hosts.read_text() if hosts.is_file() else '127.0.0.1 localhost\n::1 localhost\n'
    return dict(state=state, transaction=transaction, boot=boot, context=context,
                hostname=hostname, hosts=hosts_text)


def validate_arguments(action, arguments):
    if action not in ACTIONS or not isinstance(arguments, dict):
        raise ValueError('Unknown administration operation')
    field = {'policy.auto': 'enabled', 'policy.mode': 'mode', 'image.stage': 'digest',
             'software.install': 'package', 'software.remove': 'package',
             'config.hostname': 'hostname', 'recovery.boot': 'slot',
             'recovery.restore': 'image', 'recovery.export': 'destination'}.get(action)
    if set(arguments) != ({field} if field else set()):
        raise ValueError('Unexpected operation fields')
    if field == 'enabled' and type(arguments[field]) is not bool:
        raise ValueError('Use a boolean update policy')
    if field == 'mode' and arguments[field] not in ('immutable', 'writable'):
        raise ValueError('Choose immutable or writable mode')
    if field == 'slot' and arguments[field] not in ('A', 'B'):
        raise ValueError('Choose OS slot A or B')
    if field and field not in ('enabled', 'mode', 'slot'):
        import re
        value = arguments[field]
        pattern = '[0-9a-f]{64}' if field == 'digest' else ('[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?' if field == 'hostname' else '[a-zA-Z0-9][a-zA-Z0-9._+-]{0,79}')
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise ValueError('Choose a valid item from the displayed list')


class Controller:
    """Backend adapter must revalidate plans and admission under its write lock.

    Recovery adapters own device identification and target admission. Missing
    adapters always produce unavailable actions, never simulated success.
    """
    def __init__(self, store, boot, context='host', adapter=None, jobs=None):
        if context not in ('host', 'recovery'):
            raise ValueError('Invalid administration context')
        self.store, self.boot, self.context, self.adapter = store, boot, context, adapter
        self.jobs = jobs

    def status(self):
        if not (self.store.root / 'state.json').is_file():
            raise ValueError('Persistent state is unavailable; no initialization or repair was attempted')
        with self.store.locked(nonblocking=True):
            view = snapshot(self.store, self.boot, self.context)
            state, transaction = view['state'], view['transaction']
            capacities = os.statvfs(self.store.root)
            allowed = HOST_ACTIONS if self.context == 'host' else RECOVERY_ACTIONS
            capabilities = {}
            for action in ACTIONS:
                reason = 'Available after the verified OS backend is integrated.'
                available = False
                if action not in allowed:
                    reason = 'Available in the recovery screen.' if action.startswith('recovery.') else 'Available in the running host.'
                elif action in ('policy.auto', 'policy.mode', 'config.hostname'):
                    available, reason = True, ''
                    if action == 'policy.mode' and (state['pending'] or transaction and transaction['phase'] not in ('complete', 'cancelled', 'failed')):
                        available, reason = False, 'Finish or cancel the pending image update first.'
                elif self.adapter is not None:
                    available, reason = self.adapter.capability(action, view)
                capabilities[action] = dict(available=available, reason=reason)
            return dict(context=self.context, revision=revision(view), boot=self.boot,
                        requested_mode=state['requested_mode'], auto_update=state['auto_update'],
                        slots=state['slots'], pending=state['pending'], transaction=transaction,
                        free_bytes=capacities.f_bavail * capacities.f_frsize,
                        capabilities=capabilities,
                        catalog=self.adapter.catalog() if self.adapter else [],
                        destinations=self.adapter.destinations() if self.adapter else [],
                        images=self.adapter.images() if self.adapter else [],
                        hostname=view['hostname'] or '')

    def plan(self, action, arguments):
        validate_arguments(action, arguments)
        status = self.status()
        capability = status['capabilities'][action]
        if not capability['available']:
            raise ValueError(capability['reason'])
        title, effect = ACTIONS[action]
        return dict(action=action, arguments=arguments, revision=status['revision'],
                    title=title, effect=effect, preserves_user_data=True)

    def apply(self, plan):
        if not isinstance(plan, dict) or set(plan) != {'action', 'arguments', 'revision', 'title', 'effect', 'preserves_user_data'}:
            raise ValueError('Review an operation before applying it')
        current = self.plan(plan['action'], plan['arguments'])
        if plan != current:
            raise ValueError('System state changed. Refresh and review the operation again.')
        action, args = plan['action'], plan['arguments']
        if action in ('policy.auto', 'policy.mode', 'config.hostname'):
            # Recheck under the same lock as publication; do not nest Store.policy.
            with self.store.locked():
                view = snapshot(self.store, self.boot, self.context)
                state = view['state']
                if revision(view) != plan['revision']:
                    raise ValueError('System state changed. Review again.')
                if action == 'config.hostname':
                    parent = self.store.root / 'system'
                    parent.mkdir(mode=0o700, exist_ok=True)
                    # Keep old/new local names resolvable even if interrupted
                    # between the two publications. Running bind mounts retain
                    # their old inodes until the next boot.
                    hosts = hosts_with_name(view['hosts'], args['hostname'], view['hostname'])
                    atomic_text(parent / 'hosts', hosts)
                    atomic_text(parent / 'hostname', args['hostname']+'\n')
                else:
                    state['auto_update' if action == 'policy.auto' else 'requested_mode'] = args['enabled' if action == 'policy.auto' else 'mode']
                    self.store.save(state)
            return dict(message='Saved. Host name and mode changes apply on the next boot; an armed update is unchanged.')
        if self.adapter is None:
            raise ValueError('Backend unavailable')
        return self.adapter.apply(plan)  # Required to recheck revision/admission.

    def request(self, request):
        if not isinstance(request, dict): raise ValueError('Expected an object')
        method = request.get('method')
        expected = {'status': {'method'}, 'plan': {'method', 'action', 'arguments'},
                    'apply': {'method', 'plan'}, 'jobs': {'method'},
                    'image.submit': {'method', 'id', 'plan'}}.get(method)
        if expected is None or set(request) != expected:
            raise ValueError('Unknown request or fields')
        if method == 'jobs':
            return self.jobs.history() if self.jobs else dict(jobs=[], capacity=0, remaining=0, blocked=False)
        if method == 'image.submit':
            if self.jobs is None: raise ValueError('Image worker integration unavailable')
            return self.jobs.submit(request['id'], request['plan'], self)
        if method == 'apply' and isinstance(request['plan'], dict) and request['plan'].get('action') in ('image.stage', 'image.arm', 'image.cancel') and self.jobs is not None:
            raise ValueError('Submit a reviewed image job with a retry identity')
        if method == 'status': return self.status()
        if method == 'plan': return self.plan(request['action'], request['arguments'])
        return self.apply(request['plan'])


def installed_controller():
    if os.geteuid() != 0: raise ValueError('Administrator access is required')
    # Fixed paths only. No request can override roots, devices or executables.
    config = json.loads(Path('/usr/lib/sv08/admin-context.json').read_text())
    if config != {'format_version': 1, 'context': 'host'}:
        raise ValueError('The installed administration context is not supported')
    boot = json.loads(Path('/run/sv08/boot.json').read_text())
    store = Store('/data/sv08')
    from sv08_admin_jobs import Jobs
    controller = Controller(store, boot, jobs=Jobs('/data/sv08/admin-image-jobs', boot['boot_id']))
    # These reviewed build inputs do not yet ship in the non-deployable baseline.
    paths = {name: Path('/usr/lib/sv08') / name for name in
             ('release.json', 'update-policy.json', 'layout.json', 'environment.json')}
    if all(path.is_file() for path in paths.values()):
        from sv08_rauc import Backend
        from sv08_admin_images import HostImages
        from sv08_admission import Admission
        from sv08_staging import Staging
        documents = {name: json.loads(path.read_text()) for name, path in paths.items()}
        backend = Backend(*(documents[name] for name in paths))
        controller.adapter = HostImages(store, boot, backend,
            Staging('/data/sv08/uploads'), Admission())
    return controller


def main():
    try:
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384: raise ValueError('Request is too large')
        result = installed_controller().request(json.loads(raw))
        print(json.dumps({'ok': True, 'result': result}))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}))
        return 0  # A valid RPC error envelope; bridge/transport failures are separate.
    return 0


if __name__ == '__main__':
    sys.exit(main())
