#!/usr/bin/env python3
"""Fixed authenticated bundle intake; ADR 0010. No installer or recovery authority.

Lock order: jobs ledger → state → upload for brief admission/cleanup. Receipt
retains upload only, never calls Controller/Jobs/Transaction while streaming.
"""
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import sys
import time
from sv08_admin import revision, snapshot
from sv08_admin_jobs import TERMINAL
from sv08_bundle import inspect as inspect_bundle
from sv08_staging import Staging

CHUNK = 65536
HEADER = 4096
IDLE_SECONDS = 20
TRANSFER_SECONDS = 1800
OUTPUT_BYTES = 2 * 1024 * 1024
NAME = r'(?:[0-9a-f]{64}\.raucb|\.partial-[0-9a-f]{32})'


class Uploads:
    def __init__(self, controller, staging, policy, keyring, verify=None):
        self.controller, self.staging = controller, staging
        self.policy, self.keyring = policy, keyring
        self.verify = verify or (lambda path: inspect_bundle(path, policy, keyring, lease_fd=staging.lease_fd))
        self.policy_revision = revision(dict(policy=policy, keyring=Path(keyring).read_text()))

    def view(self):
        c = self.controller
        if c.context != 'host': raise ValueError('Upload requires the running host context')
        view = snapshot(c.store, c.boot, c.context)
        tx = view['transaction']
        if view['state']['pending'] or tx and tx['phase'] not in ('complete', 'cancelled', 'failed'):
            raise ValueError('Preserve uploads until transaction reconciliation is complete')
        view['upload_jobs'] = c.jobs.load()
        if any(row['phase'] not in TERMINAL for row in view['upload_jobs']):
            raise ValueError('Preserve uploads while an image job is pending or ambiguous')
        return view

    @contextmanager
    def admitted(self, streaming=False):
        c = self.controller
        if not (c.store.root / 'state.json').is_file():
            raise ValueError('Persistent state unavailable; no initialization attempted')
        c.store.load()  # Refuse damaged registry before creating lock bookkeeping.
        with ExitStack() as lease:
            with ExitStack() as higher:
                higher.enter_context(c.jobs.lock('ledger.lock'))
                higher.enter_context(c.store.locked(nonblocking=True))
                view = self.view()
                lease.enter_context(self.staging.locked())
                if not streaming:
                    yield view  # Brief review/removal retains all exclusion.
                    return
            yield view  # Long intake retains upload only, no higher reacquisition.

    @staticmethod
    def metadata(name, size):
        if (not isinstance(name, str) or not 1 <= len(name.encode('utf-8')) <= 240 or
                any(ord(c) < 32 or ord(c) == 127 for c in name)):
            raise ValueError('Choose a file with a bounded printable display name')
        if type(size) is not int or size <= 0: raise ValueError('Choose a nonempty bundle')

    def plan(self, name, size):
        self.metadata(name, size)
        with self.admitted() as view:
            self.staging.preflight(size)
            return dict(name=name, size=size, revision=revision(view), policy=self.policy_revision)

    def receive(self, plan, stream):
        if not isinstance(plan, dict) or set(plan) != {'name', 'size', 'revision', 'policy'}:
            raise ValueError('Review the file before uploading')
        self.metadata(plan['name'], plan['size'])
        with self.admitted(streaming=True) as view:
            if plan['revision'] != revision(view) or plan['policy'] != self.policy_revision:
                raise ValueError('System or verification policy changed; review again')
            path, proof = self.staging.receive_locked(stream, plan['size'], self.verify)
            return dict(name=path.name, proof=proof, message='Signed manifest authenticated. Full payload verification occurs during installation. No image was installed or activated.')

    def object(self, name):
        if not isinstance(name, str) or not re.fullmatch(NAME, name):
            raise ValueError('Not a managed upload name')
        entry = (self.staging.root / name).lstat()
        if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != self.staging.owner_uid or
                entry.st_nlink != 1 or stat.S_IMODE(entry.st_mode) not in (0o400, 0o600)):
            raise ValueError('Refusing linked or unexpected managed object')
        return dict(name=name, bytes=entry.st_size, device=entry.st_dev, inode=entry.st_ino,
                    modified=entry.st_mtime_ns, changed=entry.st_ctime_ns, mode=entry.st_mode)

    def listing(self):
        busy = self.staging.busy()
        objects = []
        for path in sorted(self.staging.root.iterdir()):
            if re.fullmatch(NAME, path.name):
                try:
                    item = self.object(path.name)
                    item['state'] = 'incomplete or interrupted' if path.name.startswith('.') else 'published; signature recheck required before staging'
                    objects.append(item)
                except (OSError, ValueError):
                    objects.append(dict(name=path.name, state='unexpected object; cleanup refused'))
        return dict(busy=busy, objects=objects, message='Transfer or image lease active' if busy else 'Managed storage observed; no operation resumed')

    def referenced(self, name, view):
        # Completed/cancelled transactions and terminal receipts no longer need bytes.
        # Failed journal objects remain diagnostic dependencies until reviewed recovery.
        digest = name.removesuffix('.raucb')
        tx = view['transaction']
        historical = [row for row in view['upload_jobs']
                      if row['plan']['action'] == 'image.stage' and
                      row['plan']['arguments'].get('digest') == digest and row['phase'] != 'refused']
        if not tx and historical:
            raise ValueError('Missing transaction for historical stage; preserve diagnosis')
        if tx and (name in json.dumps(tx) or digest in json.dumps(tx) or historical):
            if tx['phase'] not in ('complete', 'cancelled') or tx.get('bundle_sha256') != digest:
                raise ValueError('Upload has unresolved transaction references')
            adapter = self.controller.adapter
            if adapter is None: raise ValueError('Verified backend context required for terminal cleanup')
            backend, boot, state = adapter.backend, view['boot'], view['state']
            observed = backend.cleanup_observation(boot, self.staging.lease_fd)
            slot = tx['slot'] if tx['phase'] == 'complete' else tx['previous_slot']
            release = tx['release'] if tx['phase'] == 'complete' else tx['previous_release']
            if (boot['slot'] != slot or boot['release'] != release or
                    state['slots'][slot]['release'] != release or observed['primary'] != slot or
                    (not observed['good'][slot] if tx['phase'] == 'complete' else observed['good'][tx['slot']])):
                raise ValueError('Terminal transaction and current boot/state disagree')

    def cleanup_plan(self, name):
        with self.admitted() as view:
            self.referenced(name, view)
            return dict(object=self.object(name), revision=revision(view), policy=self.policy_revision)

    def cleanup(self, plan):
        if not isinstance(plan, dict) or set(plan) != {'object', 'revision', 'policy'}:
            raise ValueError('Review the exact managed object before removal')
        with self.admitted() as view:
            name = plan['object']['name']
            self.referenced(name, view)
            if plan != dict(object=self.object(name), revision=revision(view), policy=self.policy_revision):
                raise ValueError('Managed object or system changed; review removal again')
            (self.staging.root / name).unlink(); self.staging.sync()
        return dict(message='Reviewed managed upload removed. No transaction was cancelled.')


def installed_uploads(controller):
    policy = Path('/usr/lib/sv08/update-policy.json')
    keyring = Path('/etc/rauc/release-keyring.pem')
    if not policy.is_file() or not keyring.is_file():
        raise ValueError('Bundle upload requires the installed host policy and release keyring')
    document = json.loads(policy.read_text())
    return Uploads(controller, Staging('/data/sv08/uploads', max_bytes=document['max_bundle_bytes']), document, keyring)


class Transport:
    def __init__(self, source, output):
        self.source, self.output = source, output
        self.deadline = time.monotonic() + TRANSFER_SECONDS
        self.acknowledged = self.emitted = 0

    def emit(self, value):
        raw = (json.dumps(value, separators=(',', ':'))+'\n').encode()
        self.emitted += len(raw)
        if self.emitted > OUTPUT_BYTES: raise ValueError('Upload output budget exceeded')
        # stdout backpressure is subject to the same server timeout as stdin.
        offset = 0
        while offset < len(raw):
            self.wait(self.output, write=True)
            offset += os.write(self.output, raw[offset:])

    def wait(self, fd, write=False):
        timeout = min(IDLE_SECONDS, self.deadline-time.monotonic())
        if timeout <= 0: raise ValueError('Upload overall deadline exceeded')
        readable, writable, _ = select.select([] if write else [fd], [fd] if write else [], [], timeout)
        if not (readable or writable): raise ValueError('Upload inactivity timeout')

    def header(self):
        raw = bytearray()
        while len(raw) <= HEADER:
            self.wait(self.source)
            byte = os.read(self.source, 1)
            if byte == b'\n': return json.loads(raw)
            if not byte: raise ValueError('Truncated upload metadata')
            raw.extend(byte)
        raise ValueError('Upload metadata exceeds its budget')

    def read(self, size):
        if self.acknowledged == self.size:  # Final EOF confirmation.
            self.wait(self.source); return os.read(self.source, 1)
        target = min(CHUNK, size)
        chunk = bytearray()
        while len(chunk) < target:
            self.wait(self.source)
            part = os.read(self.source, target-len(chunk))
            if not part: raise ValueError('Truncated upload stream')
            chunk.extend(part)
        self.acknowledged += len(chunk)
        self.emit(dict(type='ack', received=self.acknowledged))
        return bytes(chunk)


def main():
    transport = Transport(0, 1)
    def interrupted(signum, frame): raise ValueError('Upload process interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGHUP, interrupted)
    signal.signal(signal.SIGALRM, interrupted)
    signal.setitimer(signal.ITIMER_REAL, TRANSFER_SECONDS)
    try:
        if len(sys.argv) != 1: raise ValueError('Upload helper accepts no arguments')
        from sv08_admin import installed_controller
        uploads = installed_uploads(installed_controller())
        plan = transport.header()
        if not isinstance(plan, dict): raise ValueError('Expected upload metadata object')
        transport.size = plan.get('size')
        # Ready only after metadata; real admission occurs before reading payload.
        transport.emit(dict(type='ready', chunk=CHUNK))
        result = uploads.receive(plan, transport)
        transport.emit(dict(type='complete', result=result))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        try: transport.emit(dict(type='error', error=str(error)[:1000]))
        except (ValueError, OSError): pass
        return 1


if __name__ == '__main__': sys.exit(main())
