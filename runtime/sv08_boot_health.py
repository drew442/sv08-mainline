#!/usr/bin/env python3
"""Bounded boot reconciliation. This confirms host OS viability, never printer readiness."""
import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path
import selectors
import signal
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


def bounded_rauc_output():
    process = subprocess.Popen(['/usr/bin/rauc', 'status', '--output-format=json'],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    data = bytearray()
    deadline = time.monotonic() + 3
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise ValueError('RAUC boot observation timed out')
                block = os.read(process.stdout.fileno(), min(4096, 32 * 1024 + 1 - len(data)))
                if not block:
                    break
                data.extend(block)
                if len(data) > 32 * 1024:
                    raise ValueError('RAUC boot observation exceeds bound')
        if process.wait(timeout=max(0, deadline - time.monotonic())) != 0:
            raise ValueError('RAUC boot observation failed')
        return data.decode()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def observed_rauc_slot(command=None):
    output = (command(['/usr/bin/rauc', 'status', '--output-format=json'],
                      text=True, timeout=3) if command else bounded_rauc_output())
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


class CoordinatorDeadline(Exception):
    pass


@contextmanager
def coordinator_deadline(seconds=50, *, disposable_fixture=False):
    """Bound boot reconciliation; only identified QEMU fixtures get extra time."""
    def reset(value, *, fixture=False):
        if not 0 < value or value > (180 if fixture else 50):
            raise ValueError('Unreviewed coordinator deadline')
        signal.setitimer(signal.ITIMER_REAL, value)
    if (not 0 < seconds or seconds > (180 if disposable_fixture else 50)):
        raise ValueError('Unreviewed coordinator deadline')
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    def expired(_signum, _frame):
        raise CoordinatorDeadline('Boot coordinator exceeded its execution deadline')
    signal.signal(signal.SIGALRM, expired)
    reset(seconds, fixture=disposable_fixture)
    try:
        yield reset
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0]:
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)


class HostHealth:
    def __init__(self, backend, manifest, *, now=time.monotonic, sleep=time.sleep,
                 command=subprocess.check_output, stable=STABLE_SECONDS,
                 deadline=DEADLINE_SECONDS - 20, disposable_fixture=False):
        self.backend, self.manifest = backend, manifest
        self.now, self.sleep, self.command = now, sleep, command
        deadline_limit = 180 if disposable_fixture else 60
        if not 0 < stable <= 5 or not stable < deadline <= deadline_limit:
            raise ValueError('Unreviewed host health bounds')
        self.stable, self.deadline = stable, deadline
        self.last_probe_failure = None

    def probe(self, boot):
        unit = self.command(['systemctl', 'is-active', 'sv08-prepare.service'],
                            text=True, timeout=3).strip()
        if unit != 'active':
            raise HealthFailure('Persistent boot preparation is not active')
        data = self.command(['findmnt', '-n', '-o', 'SOURCE', '--mountpoint', '/data'],
                            text=True, timeout=3).strip()
        if Path(data).resolve() != Path(self.manifest['devices']['data']).resolve():
            raise HealthFailure('Persistent data mount differs from manifest')
        # resolution_evidence performs the backend context validation and then
        # samples the writer/busy guard. Do not repeat the expensive device and
        # RAUC identity walk immediately before that same observation.
        self.backend.resolution_evidence(boot)

    def __call__(self, boot):
        if boot['mode'] != 'immutable':
            raise HealthFailure('Image trial requires immutable root')
        start, stable_since = self.now(), None
        while self.now() - start <= self.deadline:
            try:
                self.probe(boot)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                self.last_probe_failure = f'{type(exc).__name__}: {exc}'[:512]
                stable_since = None
            else:
                self.last_probe_failure = None
                if self.now() - start > self.deadline:
                    break  # A slow probe cannot become a late success.
                if stable_since is None:
                    stable_since = self.now()
                if self.now() - stable_since >= self.stable:
                    return True
            self.sleep(min(0.5, max(0, self.deadline - (self.now() - start))))
        detail = (f'; last probe failed: {self.last_probe_failure}'
                  if self.last_probe_failure else '')
        raise HealthFailure('Host OS health was not stable within deadline' + detail)


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
                boot['mode'] != 'immutable'):
            raise ValueError('Target trial identity is unverified')
        source = state['slots'].get(tx['previous_slot'])
        target = state['slots'].get(tx['slot'])
        if (not source or source['release'] != tx['previous_release'] or
                not target or target['release'] != tx['release'] or
                target['parent_generation'] != source['generation']):
            raise ValueError('Target generation does not descend from preserved source')
        pending = state['pending']
        prepared_trial = (boot['trial'] and pending is not None and
                          pending['phase'] == 'trial' and pending['id'] == tx['id'])
        retrying_confirming = (tx['phase'] == 'confirming' and pending is None and
                               not boot['trial'])
        if retrying_confirming:
            # State was durably cleared but the final journal write failed.
            # Re-observe the selected target before retrying mark-good.
            transaction.backend.validate_context(boot)
            if (transaction.backend.primary() != tx['slot'] or
                    not transaction.backend.good(tx['slot'])):
                raise ValueError('Confirming target is not good and primary')
        elif not prepared_trial:
            raise ValueError('Target trial identity is unverified')
        try:
            transaction.confirm(boot, os_health, admission=admission)
        except HealthFailure as exc:
            record(transaction.store, boot, exc)
            if retrying_confirming:
                # A cleared trial is an unknown confirming outcome, not a
                # remaining boot attempt that may be consumed by fallback.
                raise
            # Hold the same ordering as Transaction while making the final
            # decision and sending the orderly reboot request. No bootloader
            # counter is touched here.
            with transaction.store.locked(), admission(), transaction.writer():
                current = transaction.load()
                pending_now = transaction.store.load()['pending']
                transaction.backend.validate_context(boot)
                if (not current or current['id'] != tx['id'] or
                        current['phase'] not in ('armed', 'confirming') or
                        not pending_now or pending_now['id'] != tx['id'] or
                        pending_now['phase'] != 'trial'):
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


def _main(*, disposable_fixture=False):
    if os.geteuid() != 0:
        raise ValueError('Boot health requires root')
    # A same-boot unit restart must not inherit a previous successful marker.
    Path('/run/sv08/os-health-ready').unlink(missing_ok=True)
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
        if disposable_fixture:
            # Keep the disposable guest available for its failure reporter;
            # production fallback continues to request the normal reboot.
            atomic_json(Path('/run/sv08/qemu-fallback-requested.json'),
                        dict(id=_id, reason=str(_reason)[:512]))
            return
        subprocess.run(['/usr/bin/systemctl', 'reboot'], check=True, timeout=5)
    health = HostHealth(backend, manifest, deadline=120 if disposable_fixture else DEADLINE_SECONDS - 20,
                        disposable_fixture=disposable_fixture)
    outcome = run(boot, tx, health, boot_admission, fallback,
                  ready='/run/sv08/os-health-ready', trial_marker='/run/sv08/trial',
                  validate=validate)
    if outcome not in ('idle', 'staged', 'awaiting-reboot', 'needs-arm', 'needs-health'):
        raise ValueError('Unsupported boot outcome')


def main(deadline_seconds=None):
    # A restart may not inherit a previous success if fixture detection or
    # manifest loading fails before _main begins.
    Path('/run/sv08/os-health-ready').unlink(missing_ok=True)
    try:
        with coordinator_deadline(deadline_seconds if deadline_seconds is not None else 50) as reset_deadline:
            manifest = bounded_json('/usr/lib/sv08/release.json')
            cmdline = Path('/proc/cmdline').read_text().split()
            fixture = (manifest.get('deployable') is False and 'sv08.test=rauc-backend' in cmdline and
                       subprocess.check_output(['/usr/bin/systemd-detect-virt', '--vm'], text=True,
                                               timeout=3).strip() == 'qemu')
            if deadline_seconds is None and fixture:
                reset_deadline(180, fixture=True)
            _main(disposable_fixture=fixture)
    except Exception as exc:
        # The boot record itself may be malformed. Bind a compact diagnostic to
        # the kernel boot ID without trusting its unvalidated fields.
        try:
            boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            if str(uuid.UUID(boot_id)) != boot_id:
                raise ValueError('Invalid boot identity')
            store = Store('/data/sv08')
            bounded_json(store.root / 'state.json')
            store.load()  # Never create diagnostics in uninitialized/damaged state.
            record_failure(store,
                           dict(boot_id=boot_id, slot='unknown', release='unknown',
                                generation='unvalidated'), exc)
        except (OSError, ValueError, KeyError):
            pass  # Storage may be unavailable; the unit remains failed and gated.
        raise


if __name__ == '__main__':
    main()
