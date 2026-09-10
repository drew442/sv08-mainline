#!/usr/bin/env python3
"""Persistent policy and release-state transactions for SV08 image integration.

Gap: RAUC manages slots, not application-state generations or OS customization.
Use atomic JSON publication, SQLite backup and ordinary filesystems. Retire into
an upstream state-migration integration if it provides these semantics. See ADR
0006 and tests/test_host_state.py. This module does not install or select slots.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import uuid

MIB = 1024 * 1024


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', value):
        raise ValueError('Invalid release/generation identifier')
    return value


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path, value):
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            os.chmod(temporary, 0o600)
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def fingerprint(root):
    result = {}
    for path in sorted(root.rglob('*')):
        kind = path.lstat().st_mode
        if stat.S_ISDIR(kind):
            continue
        if not stat.S_ISREG(kind):
            raise ValueError('State copy requires regular files/directories; export unsupported links first')
        if path.name.endswith('-shm'):
            continue
        result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def snapshot(source, target):
    """Copy quiesced state, recovering SQLite WAL into the new generation only."""
    before = fingerprint(source)
    shutil.copytree(source, target)
    for path in source.rglob('*'):
        if not path.is_file() or path.name.endswith(('-wal', '-shm')):
            continue
        with path.open('rb') as stream:
            is_sqlite = stream.read(16) == b'SQLite format 3\0'
        if not is_sqlite:
            continue
        copied = target / path.relative_to(source)
        copied.unlink()
        for suffix in ('-wal', '-shm'):
            Path(str(copied) + suffix).unlink(missing_ok=True)
        # SQLite's backup API includes committed WAL data without modifying A's DB.
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as src:
            if src.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise ValueError('Source SQLite integrity check failed')
            with sqlite3.connect(copied) as dst:
                src.backup(dst)
                if dst.execute('PRAGMA quick_check').fetchone() != ('ok',):
                    raise ValueError('Copied SQLite integrity check failed')
    if fingerprint(source) != before:
        raise ValueError('State changed during copy; keep applications quiesced and retry')
    for path in target.rglob('*'):
        if path.is_file():
            with path.open('rb') as stream:
                os.fsync(stream.fileno())
    for path in sorted((p for p in target.rglob('*') if p.is_dir()), reverse=True):
        fsync_dir(path)
    fsync_dir(target)


class Store:
    def __init__(self, root, reserve_bytes=512*MIB, copy_limit_bytes=256*MIB):
        self.root = Path(root).absolute()
        for path in (self.root, *self.root.parents):
            if path.is_symlink():
                raise ValueError('Persistent root must not contain symlinks')
        self.reserve_bytes = reserve_bytes
        self.copy_limit_bytes = copy_limit_bytes

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.root / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def load(self):
        path = self.root / 'state.json'
        if path.is_symlink():
            raise ValueError('State registry must not be a symlink')
        state = json.loads(path.read_text())
        if state['format_version'] != 1 or state['requested_mode'] not in ('immutable', 'writable'):
            raise ValueError('Unsupported or corrupt state registry; use recovery')
        if not isinstance(state['auto_update'], bool) or not isinstance(state['slots'], dict):
            raise ValueError('Invalid policy/slot registry')
        for slot, record in state['slots'].items():
            if slot not in ('A', 'B') or not isinstance(record['customized'], bool):
                raise ValueError('Invalid slot record')
            identifier(record['release'])
            identifier(record['generation'])
            if record['schema'] != 1:
                raise ValueError('Unsupported state schema; migration implementation required')
        pending = state['pending']
        if pending is not None:
            if not isinstance(pending, dict) or set(pending) != {'slot', 'release', 'previous_slot', 'phase', 'id'}:
                raise ValueError('Invalid pending transaction')
            if (pending['slot'] not in ('A', 'B') or
                    pending['previous_slot'] not in state['slots'] or
                    pending['slot'] == pending['previous_slot'] or
                    pending['phase'] not in ('armed', 'trial')):
                raise ValueError('Invalid pending transaction slots/phase')
            identifier(pending['release'])
            identifier(pending['id'])
            if pending['phase'] == 'trial':
                trial = state['slots'].get(pending['slot'])
                if trial is None or trial['release'] != pending['release']:
                    raise ValueError('Trial state does not match slot registry')
        return state

    def save(self, state):
        atomic_json(self.root / 'state.json', state)

    def initialize(self):
        with self.locked():
            if (self.root / 'state.json').is_symlink():
                raise ValueError('State registry must not be a symlink')
            state = self.load() if (self.root / 'state.json').exists() else None
            for name in ('generations', 'shared/gcodes', 'shared/timelapse', 'shared/logs', 'shared/logs/journal',
                         'system/ssh', 'system/network-connections', 'system/network-state',
                         'system/rauc', 'system/timesync', 'system/rfkill', 'system/linger', 'users/sv08'):
                path = self.root / name
                if any(p.is_symlink() for p in (path, *path.parents)):
                    raise ValueError('Unexpected persistent directory link')
                path.mkdir(parents=True, exist_ok=True, mode=0o700)
            if state is None:
                state = dict(format_version=1, requested_mode='immutable', auto_update=True,
                             slots={}, pending=None)
                self.save(state)
            return state

    def policy(self, mode=None, auto_update=None):
        with self.locked():
            state = self.load()
            if mode is not None:
                if mode not in ('immutable', 'writable'):
                    raise ValueError('Unknown operating mode')
                if state['pending']:
                    raise ValueError('Finish or cancel the pending image transaction before changing mode')
                state['requested_mode'] = mode
            if auto_update is not None:
                state['auto_update'] = bool(auto_update)
            self.save(state)
            return state

    def expect_trial(self, slot, release, previous_slot):
        """Record a verified trial AFTER an installer has staged the paired images.

        Does not arm a bootloader. Callers must synchronize recording and boot
        selection; unexpected combinations fail closed at prepare_boot.
        """
        identifier(release)
        with self.locked():
            state = self.load()
            if slot not in ('A', 'B') or previous_slot not in ('A', 'B') or slot == previous_slot:
                raise ValueError('Trial must target the other slot')
            if state['pending']:
                raise ValueError('Another image transaction is pending')
            if state['requested_mode'] == 'writable' or state['slots'][previous_slot]['customized']:
                raise ValueError('Customized/writable system needs explicit reconciliation; update blocked')
            state['pending'] = dict(slot=slot, release=release, previous_slot=previous_slot,
                                    phase='armed', id=uuid.uuid4().hex)
            self.save(state)
            return state

    def cancel_trial(self):
        """Caller must disarm boot selection first; a running trial cannot be cancelled."""
        with self.locked():
            state = self.load()
            if state['pending'] and state['pending']['phase'] != 'armed':
                raise ValueError('Trial has started; use explicit rollback')
            state['pending'] = None
            self.save(state)
            return state

    def generation_path(self, record):
        path = self.root / 'generations' / identifier(record['generation'])
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_dir():
            raise ValueError('Missing/invalid state generation; use recovery')
        return path

    def check_copy_budget(self, record, reserve_full_copy=False):
        """Read-only preflight; caller holds the state lock and quiesces writers.

        Count destination blocks/inodes, including directories and sparse file
        expansion. Staging reserves the entire configured copy allowance because
        configuration can grow before the next boot. Boot rechecks actual usage.
        This is admission, not a filesystem quota or a promise against later writes.
        """
        origin = self.generation_path(record)
        fs = os.statvfs(self.root)
        block = fs.f_frsize or fs.f_bsize
        required, inodes = block, 1  # Destination generation directory.
        for path in origin.rglob('*'):
            entry = path.lstat()
            if not (stat.S_ISREG(entry.st_mode) or stat.S_ISDIR(entry.st_mode)):
                raise ValueError('State copy requires regular files/directories; export unsupported links first')
            required += block if stat.S_ISDIR(entry.st_mode) else ((entry.st_size + block - 1) // block) * block
            inodes += 1
        if required > self.copy_limit_bytes:
            raise ValueError('Insufficient state-copy budget; original state retained')
        allowance = self.copy_limit_bytes if reserve_full_copy else required
        if (fs.f_bavail * block < self.reserve_bytes + allowance or
                fs.f_favail < inodes + 128):
            raise ValueError('Insufficient state-copy space or inodes; original state retained')
        return dict(copy_bytes=required, copy_inodes=inodes, reserved_copy_bytes=allowance)

    def prepare_boot(self, slot, release, schema=1):
        """Run before any state-writing applications, not at image staging time."""
        identifier(release)
        if slot not in ('A', 'B') or schema != 1:
            raise ValueError('Unsupported slot/schema')
        with self.locked():
            state = self.load()
            pending = state['pending']
            if pending and pending['slot'] == slot and pending['release'] != release:
                raise ValueError('Booted trial slot has an unexpected release')
            trial = bool(pending and pending['slot'] == slot and pending['release'] == release)
            record = state['slots'].get(slot)
            if not record or record['release'] != release:
                source = None
                if trial:
                    source = state['slots'][pending['previous_slot']]
                elif state['slots']:
                    # Initial mirrored A/B release may start either slot.
                    same_release = [r for r in state['slots'].values() if r['release'] == release]
                    if not same_release:
                        raise ValueError('Unannounced release; keep applications stopped')
                    source = same_release[0]
                generation = release[:60] + '-' + uuid.uuid4().hex[:12]
                target = self.root / 'generations' / generation
                if source:
                    if source['schema'] != schema:
                        raise ValueError('No supported state migration for this schema')
                    origin = self.generation_path(source)
                    self.check_copy_budget(source)
                    try:
                        snapshot(origin, target)
                    except BaseException:
                        if target.exists():
                            shutil.rmtree(target)
                        raise
                else:
                    target.mkdir()
                    for name in ('config', 'database', 'ui'):
                        (target / name).mkdir()
                    fsync_dir(target)
                fsync_dir(target.parent)
                record = dict(release=release, generation=generation, schema=schema,
                              customized=False, parent_generation=source['generation'] if source else None)
                state['slots'][slot] = record
            self.generation_path(record)
            # Conservatively retain customization status across writable -> immutable.
            if state['requested_mode'] == 'writable':
                record['customized'] = True
            if trial:
                pending['phase'] = 'trial'
            elif pending and pending['phase'] == 'trial' and pending['previous_slot'] == slot:
                # Bootloader fallback retains both generations and disables blind retry.
                state['last_failed_trial'] = pending
                state['pending'] = None
            self.save(state)
            return dict(slot=slot, release=release, mode=state['requested_mode'],
                        generation=str(self.generation_path(record)), trial=trial,
                        customized=record['customized'])

    def confirm(self, slot, release):
        with self.locked():
            state = self.load()
            pending = state['pending']
            if not pending or pending['phase'] != 'trial' or pending['slot'] != slot or pending['release'] != release:
                raise ValueError('No matching prepared trial')
            state['pending'] = None
            self.save(state)
            return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=Path('/data/sv08'))
    p.add_argument('--execute', action='store_true')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('initialize')
    policy = sub.add_parser('policy')
    policy.add_argument('--mode', choices=('immutable', 'writable'))
    policy.add_argument('--auto-update', choices=('yes', 'no'))
    boot = sub.add_parser('prepare-boot')
    boot.add_argument('--slot', choices=('A', 'B'), required=True)
    boot.add_argument('--release', required=True)
    a = p.parse_args()
    store = Store(a.data)
    if a.command == 'status':
        result = store.load()
    elif not a.execute:
        result = dict(execute=False, command=a.command, data=str(store.root))
    elif a.command == 'initialize':
        result = store.initialize()
    elif a.command == 'policy':
        result = store.policy(a.mode, None if a.auto_update is None else a.auto_update == 'yes')
    else:
        result = store.prepare_boot(a.slot, a.release)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
