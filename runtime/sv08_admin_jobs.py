#!/usr/bin/env python3
"""Bounded image-operation receipts around the existing transaction controller.

ADR 0010: no scheduler, replay, or transaction reconciliation. A fixed systemd
service consumes one durably queued receipt. Separate locks keep reads responsive.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import stat
import time
from sv08_state import atomic_json, fsync_dir

UNIT = 'sv08-admin-image-worker@.service'
LIMIT = 128
MAX_BYTES = 512 * 1024
QUEUE_SECONDS = 30
IMAGE_ACTIONS = ('image.stage', 'image.arm', 'image.cancel')
TERMINAL = ('succeeded', 'refused')


def launch(identity):
    # No user-controlled arguments, environment or unit properties.
    if not re.fullmatch('[0-9a-f]{32}', identity): raise ValueError('Invalid image retry identity')
    unit = 'sv08-admin-image-worker@'+identity+'.service'
    subprocess.run(['/usr/bin/systemctl', 'start', '--no-block', unit],
                   check=True, capture_output=True, timeout=15)


class Jobs:
    def __init__(self, root, boot_id, launcher=launch):
        self.root, self.boot_id, self.launcher = Path(root), boot_id, launcher

    @contextmanager
    def lock(self, name, nonblocking=False):
        if self.root.is_symlink(): raise ValueError('Invalid image job directory')
        self.root.mkdir(mode=0o700, exist_ok=True)
        info = self.root.stat()
        if info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError('Image job directory must be private and owned by the administrator')
        fd = os.open(self.root / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1 or info.st_mode & 0o077:
                raise ValueError('Invalid image job lock')
            fcntl.flock(fd, fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0))
            yield
        finally: os.close(fd)

    def load(self):
        path = self.root / 'jobs.json'
        if path.is_symlink(): raise ValueError('Invalid image job ledger')
        if not path.exists(): return []
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1 or info.st_mode & 0o077:
            raise ValueError('Invalid image job ledger permissions')
        if info.st_size > MAX_BYTES: raise ValueError('Image job ledger exceeds its bound')
        rows = json.loads(path.read_text())
        if not isinstance(rows, list) or len(rows) > LIMIT: raise ValueError('Invalid image job ledger')
        identities = set()
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {'id', 'plan', 'boot_id', 'phase', 'message', 'queued_at'} or
                    not isinstance(row['id'], str) or not re.fullmatch('[0-9a-f]{32}', row['id']) or
                    row['id'] in identities or row['phase'] not in (*TERMINAL, 'queued', 'running', 'interrupted') or
                    type(row['queued_at']) is not int or row['queued_at'] < 0 or not isinstance(row['boot_id'], str) or not isinstance(row['message'], str)):
                raise ValueError('Invalid image job receipt')
            self.validate_plan(row['plan']); identities.add(row['id'])
        if sum(row['phase'] not in TERMINAL for row in rows) > 1:
            raise ValueError('Conflicting image job receipts')
        return rows

    @staticmethod
    def validate_plan(plan):
        from sv08_admin import ACTIONS, validate_arguments
        if (not isinstance(plan, dict) or set(plan) != {'action', 'arguments', 'revision', 'title', 'effect', 'preserves_user_data'} or
                plan['action'] not in IMAGE_ACTIONS): raise ValueError('Review an image operation first')
        validate_arguments(plan['action'], plan['arguments'])
        title, effect = ACTIONS[plan['action']]
        if (plan['title'] != title or plan['effect'] != effect or plan['preserves_user_data'] is not True or
                not isinstance(plan['revision'], str) or not re.fullmatch('[0-9a-f]{64}', plan['revision'])):
            raise ValueError('Invalid reviewed image operation')

    def save(self, rows):
        if len((json.dumps(rows, indent=2)+'\n').encode()) > MAX_BYTES: raise ValueError('Image job ledger exceeds its bound')
        atomic_json(self.root / 'jobs.json', rows)
        fsync_dir(self.root.parent)

    def public(self, row):
        value = {key: row[key] for key in ('id', 'phase', 'message')}
        value['action'] = row['plan']['action']
        if row['phase'] not in TERMINAL:
            if row['boot_id'] != self.boot_id:
                value.update(phase='interrupted', message='Boot changed. Reconciliation is required; this operation will not be replayed.')
            elif row['phase'] == 'queued' and time.monotonic() - row['queued_at'] > QUEUE_SECONDS:
                value.update(phase='interrupted', message='Worker did not start within 30 seconds. Reconciliation is required; the expired job cannot execute.')
            elif row['phase'] == 'running':
                try:
                    with self.lock('worker.lock', True):
                        value.update(phase='interrupted', message='Worker exited without a durable result. Reconciliation is required.')
                except BlockingIOError: pass
        return value

    def history(self):
        # Never acquire the state/transaction lock, including on initial page load.
        with self.lock('ledger.lock'):
            rows = self.load()
            return dict(jobs=[self.public(row) for row in reversed(rows)], capacity=LIMIT,
                        remaining=LIMIT-len(rows), blocked=any(row['phase'] not in TERMINAL for row in rows))

    def submit(self, identity, plan, controller):
        if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{32}', identity):
            raise ValueError('Invalid image retry identity')
        self.validate_plan(plan)
        with self.lock('ledger.lock'):
            rows = self.load()
            for row in rows:
                if row['id'] == identity:
                    if row['plan'] != plan: raise ValueError('Retry identity was used for a different review')
                    return self.public(row)
            if len(rows) >= LIMIT: raise ValueError('Image job history is full; reviewed maintenance is required. No receipts were removed.')
            if any(row['phase'] not in TERMINAL for row in rows):
                raise ValueError('An image job is pending or requires reconciliation')
            if controller.context != 'host' or controller.plan(plan['action'], plan['arguments']) != plan:
                raise ValueError('System state changed. Refresh and review again.')
            row = dict(id=identity, plan=plan, boot_id=self.boot_id, phase='queued', queued_at=int(time.monotonic()),
                       message='Queued for the independent image worker. Never resubmit with a new identity if the outcome is unknown.')
            rows.append(row); self.save(rows)
        try: self.launcher(identity)
        except (OSError, subprocess.SubprocessError) as error:
            # Start acknowledgement may be lost even if systemd started the unit.
            with self.lock('ledger.lock'):
                rows = self.load(); row = next(r for r in rows if r['id'] == identity)
                if row['phase'] == 'queued':
                    row.update(phase='interrupted', message='Worker launch was not acknowledged. Reconciliation is required; no automatic retry.')
                    self.save(rows)
        with self.lock('ledger.lock'):
            return self.public(next(r for r in self.load() if r['id'] == identity))

    def work(self, controller_factory, identity=None):
        with self.lock('worker.lock'):
            with self.lock('ledger.lock'):
                rows = self.load()
                pending = [r for r in rows if r['phase'] not in TERMINAL]
                if not pending or pending[0]['phase'] != 'queued': return
                row = pending[0]
                if identity is not None and row['id'] != identity: return
                if row['boot_id'] != self.boot_id or time.monotonic() - row['queued_at'] > QUEUE_SECONDS:
                    row.update(phase='interrupted', message='Boot changed or worker start expired; reconciliation is required.')
                    self.save(rows); return
                row.update(phase='running', message='Revalidating review and executing the image transaction.')
                self.save(rows)
            # Running receipt is durable before any controller/backend invocation.
            phase, message = 'interrupted', 'Outcome uncertain. Inspect the transaction journal; do not replay this job.'
            try:
                controller = controller_factory()
                if controller.boot['boot_id'] != row['boot_id'] or controller.context != 'host':
                    raise ValueError('Boot context changed before execution')
                if controller.plan(row['plan']['action'], row['plan']['arguments']) != row['plan']:
                    raise ValueError('System state changed. Refresh and review again.')
            except (ValueError, OSError, KeyError, TypeError) as error:
                phase, message = 'refused', str(error)[:1000]
            else:
                try:
                    result = controller.apply(row['plan'])
                    phase, message = 'succeeded', result['message'][:1000]
                except Exception:
                    # Even a validation-looking backend exception can follow writes.
                    # Journal is authoritative; never turn it into a retryable failure.
                    pass
            with self.lock('ledger.lock'):
                rows = self.load(); row = next(r for r in rows if r['id'] == row['id'])
                row.update(phase=phase, message=message); self.save(rows)


def main():
    try:
        if len(sys.argv) != 2 or not re.fullmatch('[0-9a-f]{32}', sys.argv[1]):
            raise ValueError('The image worker requires one validated receipt identity')
        from sv08_admin import installed_controller
        controller = installed_controller()
        controller.jobs.work(installed_controller, sys.argv[1])
        return 0
    except Exception as error:
        print('Image worker refused: '+str(error), file=sys.stderr)
        return 1


if __name__ == '__main__': sys.exit(main())
