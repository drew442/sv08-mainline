#!/usr/bin/env python3
"""Durable, non-mutating disposition for an interrupted image receipt.

This is deliberately separate from ``Transaction.reconcile``.  A disposition
records that the original result remains unknown; it neither repairs a
transaction nor permits the interrupted worker to run again.
"""
from contextlib import ExitStack, contextmanager, nullcontext
import json
from pathlib import Path
import time

from sv08_admin import revision, snapshot
from sv08_transaction import Transaction

KIND = 'retain-unknown-v1'
MAX_EVIDENCE = 16 * 1024


def reviewable(jobs, row):
    """Return whether this durable receipt has a public unknown outcome.

    The caller owns ``worker.lock``.  That makes a running row from this boot
    reviewable only after its worker has ended; a live worker cannot be turned
    into a disposition by a concurrent browser request.
    """
    if row['phase'] == 'interrupted' or row['boot_id'] != jobs.boot_id:
        return True
    return row['phase'] == 'queued' and time.monotonic() - row['queued_at'] > jobs.queue_seconds


def backend_for(controller):
    if controller.context != 'host' or controller.adapter is None:
        raise ValueError('Identified host image backend is unavailable')
    backend = controller.adapter.backend
    if not hasattr(backend, 'resolution_evidence'):
        raise ValueError('Selected RAUC service observation is unavailable')
    return backend


@contextmanager
def admitted(jobs, controller):
    """Acquire the one supported writer path before collecting evidence.

    Lock order is worker -> state -> RAUC writer -> ledger.  No ledger lock is
    held while querying the service, waiting for admission, or hashing a
    device.  The service lease is project protocol for supported writers;
    privileged intervention outside that protocol remains unsupported.
    """
    stack = ExitStack()
    try:
        stack.enter_context(jobs.lock('worker.lock', True))
        stack.enter_context(controller.store.locked(nonblocking=True))
        backend = backend_for(controller)
        stack.enter_context(getattr(backend, 'writer', nullcontext)())
        yield stack, backend
    finally:
        stack.close()


def evidence(jobs, controller, backend, row):
    if not reviewable(jobs, row):
        raise ValueError('Only a receipt with an unknown outcome can be reviewed')
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if boot_id != controller.boot['boot_id']:
        raise ValueError('Current boot evidence changed')
    # ``snapshot`` and ``Transaction.load`` only parse existing state.  They do
    # not call reconcile, mark a boot slot, start a service, or repair storage.
    current = snapshot(controller.store, controller.boot, 'host')
    transaction = Transaction(controller.store, backend, controller.adapter.admission).load()
    worker = jobs.worker_evidence(row['id'])
    service = backend.resolution_evidence(controller.boot)
    if jobs.worker_evidence(row['id']) != worker:
        raise ValueError('Image worker lifecycle changed during review')
    original = {key: value for key, value in row.items() if key != 'disposition'}
    value = {
        'format_version': 1,
        'original_sha256': revision(original),
        'state_sha256': revision(current['state']),
        'transaction_sha256': revision(transaction),
        'boot': current['boot'],
        'worker': worker,
        'service': service,
        # Old receipts did not persist a transaction ID.  Do not manufacture
        # one from a current journal during a later administrative review.
        'historical_transaction_link': None,
    }
    if len(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()) > MAX_EVIDENCE:
        raise ValueError('Image review evidence exceeds its bound')
    return value


def inspect(jobs, identity, controller):
    with admitted(jobs, controller) as (_, backend):
        with jobs.lock('ledger.lock'):
            row = jobs.row(identity)
            if row.get('disposition'):
                return {'receipt': jobs.public(row), 'plan': None}
        observed = evidence(jobs, controller, backend, row)
        plan = {'kind': KIND, 'id': identity, 'evidence_sha256': revision(observed)}
        return {
            'receipt': jobs.public(row),
            'evidence': observed,
            'plan': plan,
            'message': 'Keep the original outcome as unknown. This review does not retry, cancel, select an image, or change a boot slot.',
        }


def apply(jobs, plan, controller):
    if (not isinstance(plan, dict) or set(plan) != {'kind', 'id', 'evidence_sha256'} or
            plan['kind'] != KIND or not isinstance(plan['id'], str) or
            not isinstance(plan['evidence_sha256'], str)):
        raise ValueError('Inspect the unknown image outcome before retaining it')
    # An acknowledgement retry returns the original disposition before reading
    # current state.  This is the at-most-once publication boundary.
    with jobs.lock('ledger.lock'):
        row = jobs.row(plan['id'])
        disposition = row.get('disposition')
        if disposition:
            if disposition['plan'] != plan:
                raise ValueError('This receipt was retained with different review evidence')
            return jobs.public(row)
    with admitted(jobs, controller) as (_, backend):
        with jobs.lock('ledger.lock'):
            rows = jobs.load()
            row = next(item for item in rows if item['id'] == plan['id'])
            if row.get('disposition'):
                if row['disposition']['plan'] != plan:
                    raise ValueError('This receipt was retained with different review evidence')
                return jobs.public(row)
        observed = evidence(jobs, controller, backend, row)
        if revision(observed) != plan['evidence_sha256']:
            raise ValueError('Image evidence changed. Inspect the outcome again.')
        # Keep worker/state/writer exclusion through the single durable ledger
        # replacement.  A delayed worker cannot reacquire worker.lock and claim
        # this receipt after the disposition is saved.
        with jobs.lock('ledger.lock'):
            rows = jobs.load()
            row = next(item for item in rows if item['id'] == plan['id'])
            if row.get('disposition'):
                if row['disposition']['plan'] != plan:
                    raise ValueError('This receipt was retained with different review evidence')
                return jobs.public(row)
            if not reviewable(jobs, row):
                raise ValueError('Image receipt changed during review')
            row['disposition'] = {'outcome': 'unknown', 'plan': plan, 'evidence': observed}
            jobs.save(rows)
            return jobs.public(row)
