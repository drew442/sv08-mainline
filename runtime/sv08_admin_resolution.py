#!/usr/bin/env python3
"""Administrative evidence for unknown image-job outcomes, never reconciliation."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import time
from sv08_admin import revision, snapshot
from sv08_transaction import Transaction

MAX_EVIDENCE = 16384
KIND = 'retain-unknown-v1'


def worker(identity):
    unit = 'sv08-admin-image-worker@'+identity+'.service'
    output = subprocess.check_output(['/usr/bin/systemctl', 'show', unit,
        '--property=LoadState,ActiveState,SubState,InvocationID,MainPID,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,Result'],
        text=True, timeout=5)
    if len(output) > 4096: raise ValueError('Worker evidence exceeds its bound')
    values = dict(line.split('=', 1) for line in output.splitlines())
    if (values.get('LoadState') != 'loaded' or values.get('ActiveState') not in ('inactive', 'failed') or
            values.get('MainPID') != '0'):
        raise ValueError('Image worker is active or its lifecycle is unavailable')
    return values


@contextmanager
def admitted(jobs, controller):
    if controller.context != 'host' or controller.adapter is None:
        raise ValueError('Identified host backend is unavailable')
    backend = controller.adapter.backend
    # Worker -> state -> RAUC writer -> short ledger. No printer-service stop,
    # transaction reconciliation, device hashing or service activation here.
    with jobs.lock('worker.lock', True), controller.store.locked(nonblocking=True), backend.writer():
        yield backend


def evidence(jobs, controller, backend, row):
    from sv08_admin_jobs import QUEUE_SECONDS
    if not (row['phase'] in ('running', 'interrupted') or row['boot_id'] != jobs.boot_id or
            row['phase'] == 'queued' and time.monotonic() - row['queued_at'] > QUEUE_SECONDS):
        raise ValueError('Only an interrupted receipt can be reviewed')
    boot = controller.boot
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != boot['boot_id']:
        raise ValueError('Current boot evidence changed')
    lifecycle = worker(row['id'])
    view = snapshot(controller.store, boot, 'host')
    # Validate journal schema without reconcile or any historical association.
    Transaction(controller.store, backend, controller.adapter.admission).load()
    backend.validate_context(boot)
    service = backend.observation(boot)
    values = backend.environment_values()
    if worker(row['id']) != lifecycle: raise ValueError('Worker lifecycle changed')
    original = {key:value for key,value in row.items() if key != 'disposition'}
    value = dict(format_version=1, original=original, original_sha256=revision(original),
                 current=view, worker=lifecycle, service=service, environment=values,
                 historical_transaction_link=None)
    if len(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()) > MAX_EVIDENCE:
        raise ValueError('Image review evidence exceeds its bound')
    return value


def inspect(jobs, identity, controller):
    with admitted(jobs, controller) as backend:
        with jobs.lock('ledger.lock'):
            row = next((r for r in jobs.load() if r['id'] == identity), None)
            if row is None: raise ValueError('Unknown image receipt')
            if row.get('disposition'): return dict(receipt=jobs.public(row), plan=None)
        observed = evidence(jobs, controller, backend, row)
        plan = dict(kind=KIND, id=identity, evidence_sha256=revision(observed))
        return dict(receipt=jobs.public(row), evidence=observed, plan=plan,
                    message='Retain the original outcome as unknown and finish receipt review. This does not cancel, retry or select an image.')


def apply(jobs, plan, controller):
    if (not isinstance(plan, dict) or set(plan) != {'kind','id','evidence_sha256'} or plan['kind'] != KIND):
        raise ValueError('Review the unknown-outcome disposition first')
    # Historical acknowledgment retry precedes current service/state checks.
    with jobs.lock('ledger.lock'):
        row = next((r for r in jobs.load() if r['id'] == plan['id']), None)
        if row is None: raise ValueError('Unknown image receipt')
        if row.get('disposition'):
            if row['disposition']['plan'] != plan: raise ValueError('Disposition was already reviewed with different evidence')
            return jobs.public(row)
    with admitted(jobs, controller) as backend:
        with jobs.lock('ledger.lock'):
            rows = jobs.load()
            row = next(r for r in rows if r['id'] == plan['id'])
            if row.get('disposition'):
                if row['disposition']['plan'] != plan: raise ValueError('Disposition evidence changed')
                return jobs.public(row)
        observed = evidence(jobs, controller, backend, row)
        if revision(observed) != plan['evidence_sha256']:
            raise ValueError('Image evidence changed. Inspect and review again.')
        # The worker and all supported writers remain excluded through fsync.
        # Original row bytes/semantics remain untouched, including queued/running
        # stored phases whose public observation became interrupted.
        with jobs.lock('ledger.lock'):
            rows = jobs.load()
            current = next(r for r in rows if r['id'] == row['id'])
            if current != row: raise ValueError('Image receipt changed')
            current['disposition'] = dict(plan=plan, outcome='unknown', evidence=observed)
            jobs.save(rows)
            return jobs.public(current)
