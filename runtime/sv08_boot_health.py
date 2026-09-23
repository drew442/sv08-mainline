#!/usr/bin/env python3
"""Bounded boot reconciliation. This confirms host OS viability, never printer readiness."""
import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path
import subprocess
import time
import uuid

from sv08_boot import slot_from_cmdline, verify_devices
from sv08_state import Store, atomic_json, identifier
from sv08_transaction import Transaction

STABLE_SECONDS = 5
DEADLINE_SECONDS = 60
RECORD_LIMIT = 64 * 1024
RETAINED_LIMIT = 1024 * 1024
BOOT_FIELDS = {'slot', 'release', 'mode', 'generation', 'trial', 'customized', 'boot_id'}


def bounded_json(path, limit=RECORD_LIMIT):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Missing, linked or oversized boot input: ' + path.name)
    return json.loads(path.read_text())


def validate_boot(boot, store, manifest, *, boot_id, cmdline, observed_slot,
                  verify=verify_devices):
    """Independently bind the early-boot record to the current kernel and registry."""
    if not isinstance(boot, dict) or set(boot) != BOOT_FIELDS:
        raise ValueError('Malformed boot record')
    if (boot['slot'] != slot_from_cmdline(cmdline) or boot['slot'] != observed_slot or
            boot['boot_id'] != str(uuid.UUID(boot_id)) or boot['boot_id'] != boot_id or
            boot['release'] != identifier(manifest['release']) or
            manifest['state_schema'] != 1 or boot['mode'] not in ('immutable', 'writable') or
            type(boot['trial']) is not bool or type(boot['customized']) is not bool):
        raise ValueError('Boot identity, release, mode or schema differs')
    state = store.load()
    record = state['slots'].get(boot['slot'])
    if (not record or record['release'] != boot['release'] or record['schema'] != manifest['state_schema'] or
            boot['mode'] != state['requested_mode'] or boot['customized'] != record['customized'] or
            boot['trial'] != bool(state['pending'] and state['pending']['slot'] == boot['slot'] and
                                  state['pending']['release'] == boot['release'])):
        raise ValueError('Boot record and state registry disagree')
    generation = store.generation_path(record)
    if boot['generation'] != str(generation) or generation.is_symlink():
        raise ValueError('Boot generation differs from state registry')
    verify(manifest, boot['slot'])
    return state


def observed_rauc_slot(command=subprocess.check_output):
    output = command(['/usr/bin/rauc', 'status', '--output-format=json'],
                     text=True, timeout=3)
    if len(output.encode()) > 32 * 1024:
        raise ValueError('RAUC boot observation exceeds bound')
    slot = json.loads(output)['booted']
    if slot not in ('A', 'B'):
        raise ValueError('RAUC reported an unknown boot slot')
    return slot


@contextmanager
def boot_admission(path=Path('/run/sv08/boot-health.lock')):
    """Only serialize boot coordinators; Transaction owns state and RAUC locks."""
    if os.geteuid() != 0:
        raise ValueError('Boot admission requires root')
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


class HealthFailure(ValueError):
    pass


class HostHealth:
    def __init__(self, backend, manifest, *, now=time.monotonic, sleep=time.sleep,
                 command=subprocess.check_output, stable=STABLE_SECONDS,
                 deadline=DEADLINE_SECONDS - 15):
        self.backend, self.manifest = backend, manifest
        self.now, self.sleep, self.command = now, sleep, command
        if not 0 < stable <= 5 or not stable < deadline <= 60:
            raise ValueError('Unreviewed host health bounds')
        self.stable, self.deadline = stable, deadline

    def probe(self, boot):
        unit = self.command(['systemctl', 'is-active', 'sv08-prepare.service'],
                            text=True, timeout=3).strip()
        if unit != 'active':
            raise HealthFailure('Persistent boot preparation is not active')
        data = self.command(['findmnt', '-n', '-o', 'SOURCE', '--mountpoint', '/data'],
                            text=True, timeout=3).strip()
        if Path(data).resolve() != Path(self.manifest['devices']['data']).resolve():
            raise HealthFailure('Persistent data mount differs from manifest')
        self.backend.validate_context(boot)
        self.backend.resolution_evidence(boot)

    def __call__(self, boot):
        if boot['mode'] != 'immutable':
            raise HealthFailure('Image trial requires immutable root')
        start, stable_since = self.now(), None
        while self.now() - start <= self.deadline:
            try:
                self.probe(boot)
            except (OSError, subprocess.SubprocessError, ValueError):
                stable_since = None
            else:
                if stable_since is None:
                    stable_since = self.now()
                if self.now() - stable_since >= self.stable:
                    return True
            self.sleep(min(0.5, max(0, self.deadline - (self.now() - start))))
        raise HealthFailure('Host OS health was not stable within deadline')


def record_failure(store, boot, reason):
    """Retain bounded failed-generation evidence without rotating it away."""
    directory = store.root / 'shared/logs/journal/boot-health'
    if directory.is_symlink():
        raise ValueError('Diagnostic directory must not be linked')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / (boot['boot_id'] + '.json')
    if path.exists() or path.is_symlink():
        raise ValueError('Boot failure already recorded; refusing silent retry')
    payload = dict(boot_id=boot['boot_id'], slot=boot['slot'], release=boot['release'],
                   generation=boot['generation'], reason=str(reason)[:2048])
    encoded = json.dumps(payload, sort_keys=True).encode()
    if len(encoded) > RECORD_LIMIT or sum(p.stat().st_size for p in directory.iterdir() if p.is_file()) + len(encoded) > RETAINED_LIMIT:
        raise ValueError('Retained boot diagnostic budget exceeded')
    atomic_json(path, payload)


def run(boot, transaction, os_health, admission, fallback, *, ready, trial_marker=None,
        validate, record=record_failure):
    """Dispatch one validated boot; only a validated failed target may request fallback."""
    ready = Path(ready)
    ready.unlink(missing_ok=True)
    validate()
    state = transaction.store.load()
    tx = transaction.load()
    if tx and tx['phase'] not in ('complete', 'cancelled', 'failed'):
        # Backend validation is trial-only; normal writable source boots stay usable.
        transaction.backend.validate_context(boot)
    outcome = transaction.reconcile(boot, admission=admission)
    if outcome == 'needs-arm':
        transaction.arm(boot)
    elif outcome == 'needs-cancel':
        if (not tx or boot['slot'] != tx['previous_slot'] or
                boot['release'] != tx['previous_release'] or boot['boot_id'] == tx['boot_id']):
            raise ValueError('Fallback source identity is unverified')
        transaction.cancel(boot)
        outcome = 'idle'
    elif outcome == 'needs-health':
        if (not tx or boot['slot'] != tx['slot'] or boot['release'] != tx['release'] or
                not boot['trial'] or not state['pending'] or state['pending']['id'] != tx['id'] or
                boot['mode'] != 'immutable'):
            raise ValueError('Target trial identity is unverified')
        try:
            transaction.confirm(boot, os_health, admission=admission)
        except HealthFailure as exc:
            record(transaction.store, boot, exc)
            # The selected target, transaction, current boot and backend were
            # checked above. Never rearm or directly mark/cancel the target.
            transaction.backend.validate_context(boot)
            if (transaction.load()['id'] != tx['id'] or
                    transaction.store.load()['pending']['id'] != tx['id']):
                raise ValueError('Failed trial backend or journal changed before fallback')
            fallback(boot, tx['id'], str(exc))
            return 'needs-health'
        outcome = 'idle'
    if outcome in ('idle', 'staged', 'awaiting-reboot', 'needs-arm'):
        if outcome == 'idle' and transaction.store.load()['pending'] is not None:
            raise ValueError('Pending trial remains after reconciliation')
        if boot['trial']:
            if trial_marker is None or not Path(trial_marker).is_file():
                raise ValueError('Prepared trial marker is missing')
            Path(trial_marker).unlink()
        ready.touch(mode=0o600)
    return outcome


def main():
    if os.geteuid() != 0:
        raise ValueError('Boot health requires root')
    root = Path('/usr/lib/sv08')
    manifest = bounded_json(root / 'release.json')
    boot = bounded_json('/run/sv08/boot.json')
    store = Store('/data/sv08')
    bounded_json(store.root / 'state.json')
    def validate():
        validate_boot(boot, store, manifest,
                      boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                      cmdline=Path('/proc/cmdline').read_text(),
                      observed_slot=observed_rauc_slot())
    validate()
    documents = [root / name for name in ('release.json', 'update-policy.json',
                                          'layout.json', 'environment.json')]
    tx_path = store.root / 'update.json'
    live = tx_path.exists() and bounded_json(tx_path).get('phase') not in ('complete', 'cancelled', 'failed')
    if live and not all(path.is_file() for path in documents):
        raise ValueError('Live image transaction lacks reviewed backend inputs')
    if all(path.is_file() for path in documents):
        from sv08_admin import disposable_backend_fixture
        from sv08_rauc import Backend
        inputs = [bounded_json(path) for path in documents]
        backend = Backend(*inputs, fixture=disposable_backend_fixture(inputs[0]))
    else:
        class IdleBackend:
            def writer(self):
                from contextlib import nullcontext
                return nullcontext()
        backend = IdleBackend()
    from sv08_admission import Admission
    tx = Transaction(store, backend, Admission())
    def fallback(_boot, _id, _reason):
        subprocess.run(['/usr/bin/systemctl', 'reboot'], check=True, timeout=5)
    health = HostHealth(backend, manifest)
    outcome = run(boot, tx, health, boot_admission, fallback,
                  ready='/run/sv08/os-health-ready', trial_marker='/run/sv08/trial',
                  validate=validate)
    if outcome not in ('idle', 'staged', 'awaiting-reboot', 'needs-arm', 'needs-health'):
        raise ValueError('Unsupported boot outcome')


if __name__ == '__main__':
    main()
