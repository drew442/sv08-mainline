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
import threading
from sv08_state import atomic_json, fsync_dir

UNIT = 'sv08-admin-image-worker@.service'
LIMIT = 128
RECEIPT_BYTES = 512 * 1024
# Every retained unknown outcome may carry at most 16 KiB of review evidence.
# Reserve another KiB for its plan/outcome JSON framing. The complete receipt
# file therefore has a finite 2.625 MiB limit, and atomic replacement needs an
# additional 2.625 MiB temporary-file reserve on /data.
MAX_EVIDENCE_BYTES = 16 * 1024
MAX_DISPOSITION_BYTES = MAX_EVIDENCE_BYTES + 1024
MAX_BYTES = RECEIPT_BYTES + LIMIT * MAX_DISPOSITION_BYTES
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
    def __init__(self, root, boot_id, launcher=launch, budget=None):
        self.root, self.boot_id, self.launcher = Path(root), boot_id, launcher
        self.queue_seconds = QUEUE_SECONDS
        self.budget = budget
        self._locks = threading.local()

    @property
    def ledger_fd(self): return getattr(self._locks, 'ledger_fd', None)

    @ledger_fd.setter
    def ledger_fd(self, value): self._locks.ledger_fd = value

    @contextmanager
    def lock(self, name, nonblocking=False):
        from sv08_admin_history import directory, pair, safe
        if name not in ('ledger.lock', 'worker.lock'): raise ValueError('Invalid image job lock name')
        if self.root.is_symlink(): raise ValueError('Invalid image job directory')
        self.root.mkdir(mode=0o700, exist_ok=True)
        with directory(self.root) as directory_fd:
            # Validate preexisting aliases without ever rotating the inode.
            if name == 'ledger.lock': pair(directory_fd)
            fd = os.open(name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
            previous = self.ledger_fd
            try:
                safe(os.fstat(fd), 2 if name == 'ledger.lock' and pair(directory_fd) else 1)
                fcntl.flock(fd, fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0))
                if name == 'ledger.lock':
                    fenced = pair(directory_fd, fd)
                    if not fenced:
                        bound = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                        safe(os.fstat(fd))
                        if (bound.st_dev, bound.st_ino) != (os.fstat(fd).st_dev, os.fstat(fd).st_ino):
                            raise ValueError('Ledger lock inode changed')
                    self.ledger_fd = fd
                yield
            finally:
                self.ledger_fd = previous
                os.close(fd)

    def view(self):
        from sv08_admin_history import History
        return History(self).view()

    def acknowledged(self, view=None):
        from sv08_admin_history import History
        return History(self).acknowledged(view or self.view())

    def load(self):
        """Validated all-history observation; never save this concatenation."""
        return self.view()['rows']

    def validate_rows(self, rows):
        if not isinstance(rows, list) or len(rows) > LIMIT: raise ValueError('Invalid image job ledger')
        identities = set()
        for row in rows:
            if (not isinstance(row, dict) or set(row) not in ({'id', 'plan', 'boot_id', 'phase', 'message', 'queued_at'},
                                                               {'id', 'plan', 'boot_id', 'phase', 'message', 'queued_at', 'disposition'}) or
                    not isinstance(row['id'], str) or not re.fullmatch('[0-9a-f]{32}', row['id']) or
                    row['id'] in identities or row['phase'] not in (*TERMINAL, 'queued', 'running', 'interrupted') or
                    type(row['queued_at']) is not int or row['queued_at'] < 0 or
                    not isinstance(row['boot_id'], str) or not isinstance(row['message'], str)):
                raise ValueError('Invalid image job receipt')
            self.validate_plan(row['plan']); identities.add(row['id'])
            self.validate_disposition(row)
        if sum(self.blocking(row) for row in rows) > 1:
            raise ValueError('Conflicting image job receipts')
        originals = [{key: value for key, value in row.items() if key != 'disposition'} for row in rows]
        if len((json.dumps(originals, indent=2)+'\n').encode()) > RECEIPT_BYTES:
            raise ValueError('Original image receipts exceed their bound')
        if len((json.dumps(rows, indent=2)+'\n').encode()) > MAX_BYTES:
            raise ValueError('Image job ledger exceeds its bound')

    @staticmethod
    def blocking(row):
        return row['phase'] not in TERMINAL and 'disposition' not in row

    @staticmethod
    def validate_disposition(row):
        if 'disposition' not in row:
            return
        from sv08_admin import revision
        from sv08_admin_resolution import KIND, MAX_EVIDENCE
        value = row['disposition']
        original = {key: item for key, item in row.items() if key != 'disposition'}
        if (row['phase'] in TERMINAL or not isinstance(value, dict) or
                set(value) != {'outcome', 'plan', 'evidence'} or value['outcome'] != 'unknown' or
                not isinstance(value['evidence'], dict) or
                value['evidence'].get('original_sha256') != revision(original) or
                value['plan'] != {'kind': KIND, 'id': row['id'],
                                  'evidence_sha256': revision(value['evidence'])} or
                len(json.dumps(value['evidence'], sort_keys=True, separators=(',', ':')).encode()) > MAX_EVIDENCE):
            raise ValueError('Corrupt or unbound image disposition evidence')

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

    def save(self, rows, expected=None, result=False):
        from sv08_admin_history import History
        view = self.view()
        if view['format'] == 2 and expected is None:
            raise ValueError('Active history saves require the observed revision')
        if expected is not None and expected != view['revision']:
            raise ValueError('Image history changed')
        archived = {row['id'] for row in view['rows']} - {row['id'] for row in view['active']}
        if view['format'] == 2 and not {row['id'] for row in view['active']}.issubset({row['id'] for row in rows}):
            raise ValueError('Existing active receipt identities must be preserved')
        if any(row['id'] in archived for row in rows): raise ValueError('Archived receipts are immutable')
        if view['format'] == 2:
            previous = {row['id']: row for row in view['active']}
            for row in rows:
                old = previous.get(row['id'])
                if old is None: continue
                if any(row.get(key) != old[key] for key in ('id', 'plan', 'boot_id', 'queued_at')):
                    raise ValueError('Original receipt identity and plan are immutable')
                if (old.get('disposition') or old['phase'] in TERMINAL) and row != old:
                    raise ValueError('Settled receipt and disposition are immutable')
        History(self).publish(view, rows, result=result)

    def public(self, row):
        value = {key: row[key] for key in ('id', 'phase', 'message')}
        value['action'] = row['plan']['action']
        if row['phase'] not in TERMINAL and not row.get('disposition'):
            if row['boot_id'] != self.boot_id:
                value.update(phase='interrupted', message='Boot changed. Reconciliation is required; this operation will not be replayed.')
            elif row['phase'] == 'queued' and time.monotonic() - row['queued_at'] > QUEUE_SECONDS:
                value.update(phase='interrupted', message='Worker did not start within 30 seconds. Reconciliation is required; the expired job cannot execute.')
            elif row['phase'] == 'running':
                try:
                    with self.lock('worker.lock', True):
                        value.update(phase='interrupted', message='Worker exited without a durable result. Reconciliation is required.')
                except BlockingIOError: pass
        if row.get('disposition'):
            value.update(phase='interrupted',
                         message='Outcome unknown. Administrative review retained; no replay or success was inferred.',
                         disposition=row['disposition']['plan'])
        return value

    def row(self, identity):
        if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{32}', identity):
            raise ValueError('Invalid image receipt identity')
        row = next((item for item in self.load() if item['id'] == identity), None)
        if row is None:
            raise ValueError('Unknown image receipt')
        return row

    def worker_evidence(self, identity):
        unit = 'sv08-admin-image-worker@'+identity+'.service'
        output = subprocess.check_output(['/usr/bin/systemctl', 'show', unit,
            '--property=LoadState,ActiveState,SubState,InvocationID,MainPID,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,Result'],
            text=True, timeout=5)
        if len(output) > 4096:
            raise ValueError('Worker evidence exceeds its bound')
        values = dict(line.split('=', 1) for line in output.splitlines())
        if (values.get('LoadState') != 'loaded' or values.get('ActiveState') not in ('inactive', 'failed') or
                values.get('MainPID') != '0'):
            raise ValueError('Image worker is active or its lifecycle is unavailable')
        return values

    def history(self):
        # Never acquire the state/transaction lock, including on initial page load.
        with self.lock('ledger.lock'):
            view = self.acknowledged(); rows = view['rows']
            active = len(view['active']); archives = len(view['manifest']['archives']) if view['format'] == 2 else 0
            from sv08_admin_history import History, TOTAL
            try: maintenance = History(self).review(view); reason = ''
            except ValueError as error: maintenance = None; reason = str(error)
            return dict(history_revision=view['revision'], active=active, archives=archives, total=len(rows),
                        total_capacity=TOTAL, total_remaining=TOTAL-len(rows),
                        maintenance_available=maintenance is not None, maintenance_reason=reason,
                        format=view['format'], jobs=[self.public(row) for row in reversed(rows)], capacity=LIMIT,
                        remaining=LIMIT-active, blocked=any(self.blocking(row) for row in rows))

    def submit(self, identity, plan, controller):
        if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{32}', identity):
            raise ValueError('Invalid image retry identity')
        self.validate_plan(plan)
        with self.lock('ledger.lock'):
            view = self.view(); rows = view['rows']
            for row in rows:
                if row['id'] == identity:
                    if row['plan'] != plan: raise ValueError('Retry identity was used for a different review')
                    self.acknowledged(view)
                    return self.public(row)
            if view['format'] == 1 and view['fenced']:
                raise ValueError('Interrupted history migration requires explicit reviewed resume before new identities')
            if len(view['active']) >= LIMIT or len(rows) >= 1152: raise ValueError('Image job history is full; reviewed maintenance is required. No receipts were removed.')
            if any(self.blocking(row) for row in rows):
                raise ValueError('An image job is pending or requires reconciliation')
        # Do not hold the ledger while acquiring the state/admission path.  A
        # disposition holds worker -> state -> writer before its short ledger
        # publication, so this avoids a ledger/state inversion.
        if controller.context != 'host' or controller.plan(plan['action'], plan['arguments']) != plan:
            raise ValueError('System state changed. Refresh and review again.')
        with self.lock('ledger.lock'):
            view = self.view(); rows = view['rows']
            for row in rows:
                if row['id'] == identity:
                    if row['plan'] != plan: raise ValueError('Retry identity was used for a different review')
                    self.acknowledged(view)
                    return self.public(row)
            if view['format'] == 1 and view['fenced']:
                raise ValueError('Interrupted history migration requires explicit reviewed resume before new identities')
            if len(view['active']) >= LIMIT or len(rows) >= 1152: raise ValueError('Image job history is full; reviewed maintenance is required. No receipts were removed.')
            if any(self.blocking(row) for row in rows):
                raise ValueError('An image job is pending or requires reconciliation')
            row = dict(id=identity, plan=plan, boot_id=self.boot_id, phase='queued', queued_at=int(time.monotonic()),
                       message='Queued for the independent image worker. Never resubmit with a new identity if the outcome is unknown.')
            rows = list(view['active']); rows.append(row); self.save(rows, view['revision'])
        try: self.launcher(identity)
        except (OSError, subprocess.SubprocessError) as error:
            # Start acknowledgement may be lost even if systemd started the unit.
            with self.lock('ledger.lock'):
                view = self.view(); rows = view['active']; row = next(r for r in rows if r['id'] == identity)
                if row['phase'] == 'queued':
                    row.update(phase='interrupted', message='Worker launch was not acknowledged. Reconciliation is required; no automatic retry.')
                    self.save(rows, view['revision'], result=True)
        with self.lock('ledger.lock'):
            return self.public(next(r for r in self.acknowledged()['rows'] if r['id'] == identity))

    def work(self, controller_factory, identity=None):
        with self.lock('worker.lock'):
            with self.lock('ledger.lock'):
                view = self.view(); rows = view['active']
                if identity is not None and not any(r['id'] == identity for r in rows): return
                pending = [r for r in rows if self.blocking(r)]
                if not pending or pending[0]['phase'] != 'queued': return
                row = pending[0]
                if identity is not None and row['id'] != identity: return
                if row['boot_id'] != self.boot_id or time.monotonic() - row['queued_at'] > QUEUE_SECONDS:
                    row.update(phase='interrupted', message='Boot changed or worker start expired; reconciliation is required.')
                    self.save(rows, view['revision'], result=True); return
                row.update(phase='running', message='Revalidating review and executing the image transaction.')
                self.save(rows, view['revision'], result=True)
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
                view = self.view(); rows = view['active']; row = next(r for r in rows if r['id'] == row['id'])
                row.update(phase=phase, message=message); self.save(rows, view['revision'], result=True)


def main():
    try:
        if len(sys.argv) != 2 or not re.fullmatch('[0-9a-f]{32}', sys.argv[1]):
            raise ValueError('The image worker requires one validated receipt identity')
        from sv08_admin import installed_controller, installed_job_context
        _, jobs = installed_job_context()
        jobs.work(installed_controller, sys.argv[1])
        return 0
    except Exception as error:
        print('Image worker refused: '+str(error), file=sys.stderr)
        return 1


if __name__ == '__main__': sys.exit(main())
