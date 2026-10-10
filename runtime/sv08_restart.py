#!/usr/bin/env python3
"""Boot-bound shutdown admission and coherent controlled restart eligibility.

/run is volatile; the boot identity also makes retained disposable fixtures safe.
Callers publish/clear intent while holding state and service admission locks.
"""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import uuid

BOOT_ID = Path('/proc/sys/kernel/random/boot_id')


def intent(runtime=Path('/run/sv08'), boot_id=BOOT_ID):
    path = Path(runtime) / 'shutdown.json'
    if path.is_symlink():
        raise ValueError('Invalid shutdown intent')
    try:
        with path.open() as stream:
            value = json.loads(stream.read(2049))
    except FileNotFoundError:
        return None
    if (not isinstance(value, dict) or set(value) != {'format_version', 'boot_id', 'id'} or
            value['format_version'] != 1 or not isinstance(value['boot_id'], str) or
            not value['boot_id'] or len(value['boot_id']) > 80 or
            not isinstance(value['id'], str) or len(value['id']) != 32 or
            any(c not in '0123456789abcdef' for c in value['id'])):
        raise ValueError('Invalid shutdown intent')
    return value if value['boot_id'] == Path(boot_id).read_text().strip() else None


def require_running(runtime=Path('/run/sv08'), boot_id=BOOT_ID):
    if intent(runtime, boot_id):
        raise ValueError('Controlled restart is queued; shutdown admission is closed')


def publish(runtime, boot_id=BOOT_ID):
    from sv08_state import atomic_json
    require_running(runtime, boot_id)
    value = dict(format_version=1, boot_id=Path(boot_id).read_text().strip(), id=uuid.uuid4().hex)
    atomic_json(Path(runtime) / 'shutdown.json', value)
    return value


def clear(runtime, expected, boot_id=BOOT_ID):
    from sv08_state import fsync_dir
    if intent(runtime, boot_id) != expected:
        raise ValueError('Shutdown intent changed; administrator inspection required')
    (Path(runtime) / 'shutdown.json').unlink()
    fsync_dir(Path(runtime))


@contextmanager
def start_admitted(runtime=Path('/run/sv08'), boot_id=BOOT_ID):
    """The same nonblocking barrier used by controlled service operations."""
    fd = os.open(Path(runtime) / 'admission.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_running(runtime, boot_id)
        yield
    finally:
        os.close(fd)


def require_mode_change(store, state):
    journal = store.root / 'update.json'
    if journal.is_symlink(): raise ValueError('Invalid update journal')
    tx = json.loads(journal.read_text()) if journal.exists() else None
    if state['pending'] or tx is not None and (not isinstance(tx, dict) or tx.get('phase') not in ('complete', 'cancelled', 'failed')):
        raise ValueError('Finish or cancel the pending image transaction before changing mode')
    require_jobs_idle(store)


def require_jobs_idle(store):
    """Caller holds state lock; image ledger lock follows it, never precedes it."""
    root = store.root / 'admin-image-jobs'
    if root.exists():
        from sv08_admin_jobs import Jobs
        jobs = Jobs(root, '')
        with jobs.lock('ledger.lock'):
            if any(jobs.blocking(row) for row in jobs.load()):
                raise ValueError('An image job is pending or uncertain; inspect it before restarting or changing mode')
    for path in (store.root / 'customizations').glob('*.json'):
        if path.is_symlink(): raise ValueError('Invalid package operation record')
        if json.loads(path.read_text()).get('status') not in ('completed', 'failed'):
            raise ValueError('A package operation has an uncertain outcome; inspect it before restarting or changing mode')
    root = store.root / 'software/jobs'
    for path in root.glob('*.json'):
        if path.is_symlink():
            raise ValueError('Invalid software job record')
        if path.name.endswith('.policy.json'):
            raise ValueError('Interrupted package service policy requires recovery before restarting or changing mode')
        record = json.loads(path.read_text())
        if record.get('status') not in ('completed', 'failed', 'acknowledged'):
            raise ValueError('A software job is pending or uncertain; inspect it before restarting or changing mode')


def require_restart(store):
    from sv08_transaction import Transaction
    require_jobs_idle(store)
    state = store.load()
    tx = Transaction(store, None, None).load()
    pending = state['pending']
    if tx and tx['phase'] not in ('complete', 'cancelled', 'failed') and tx['boot_id'] != store.boot_id.read_text().strip():
        raise ValueError('Image transaction belongs to an earlier boot; reconcile before restarting')
    if tx and tx['phase'] in ('staged', 'armed'):
        source = state['slots'].get(tx['previous_slot'])
        if not source or source['release'] != tx['previous_release']:
            raise ValueError('Image source state requires reconciliation before restarting')
        path = store.runtime / 'boot.json'
        if path.is_symlink(): raise ValueError('Invalid running boot context')
        if path.exists():
            boot = json.loads(path.read_text())
            if any(boot.get(key) != value for key, value in (('slot', tx['previous_slot']), ('release', tx['previous_release']), ('boot_id', tx['boot_id']), ('mode', 'immutable'))):
                raise ValueError('Running boot and image transaction disagree; reconcile before restarting')
    if tx and tx['phase'] == 'armed':
        expected = dict(slot=tx['slot'], release=tx['release'], previous_slot=tx['previous_slot'], phase='armed', id=tx['id'])
        if pending != expected or state['requested_mode'] != 'immutable' or (tx.get('update_policy', {}).get('check_customization', True) and any(r['customized'] for r in state['slots'].values())):
            raise ValueError('Armed image state requires reconciliation before restarting')
    elif pending or tx and tx['phase'] not in ('staged', 'complete', 'cancelled', 'failed'):
        raise ValueError('Image transaction is transitional or uncertain; reconcile before restarting')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check-start',))
    parser.parse_args()
    with start_admitted():
        pass


if __name__ == '__main__':
    main()


def controlled_restart(command, runtime, boot_id=BOOT_ID, admission=None, *,
                       before_dispatch=None, acknowledged=None, launch_failed=None, uncertain=None):
    """Shared admitted restart; callbacks persist dispatch, not health completion.

    Caller holds persistent state and any operation locks. No callback may
    reopen admission after the command can have reached systemd.
    """
    from sv08_admission import Admission, KLIPPER
    class RestartSystemd:
        rebooting=False
        def state(self,name):
            state=command('systemctl','show',name,'-p','ActiveState','--value')
            if name==KLIPPER:
                legacy=command('systemctl','show','klipper.service','-p','ActiveState','--value')
                if legacy not in ('inactive','failed'): raise ValueError('Legacy Klipper prevents controlled restart')
                if state!='active':
                    modes=[command('systemctl','show',unit,'-p','UnitFileState','--value') for unit in (KLIPPER,'klipper.service')]
                    if state!='inactive' or legacy!='inactive' or modes!=['masked','masked']:
                        raise ValueError('Printer idle cannot be proven; restart refused')
            return state
        def stop(self,name):
            command('systemctl','stop',name)
            if command('systemctl','show',name,'-p','ActiveState','--value') not in ('inactive','failed'):
                raise ValueError('Printer service did not stop')
        def start(self,name):
            if not self.rebooting: command('systemctl','start',name)
    systemd=RestartSystemd()
    admission=admission or Admission(runtime,systemd=systemd,boot_id=boot_id)
    with admission() as lease:
        if command('systemctl','show','klipper.service','-p','ActiveState','--value') not in ('inactive','failed'):
            raise ValueError('Legacy Klipper prevents controlled restart')
        expected=publish(runtime,boot_id)
        # Once the request can reach systemd, a lost acknowledgement cannot
        # prove that shutdown was refused. Keep the barrier through that
        # uncertainty, including interrupted callers.
        if before_dispatch: before_dispatch(expected)
        systemd.rebooting=True
        if lease is not None: lease.keep_stopped=True
        try:
            command('systemctl','--no-block','reboot')
        except (FileNotFoundError, PermissionError):
            # The subprocess could not launch. Clear only our exact intent
            # before allowing the admitted services to be restored.
            clear(runtime,expected,boot_id)
            if launch_failed: launch_failed(expected)
            systemd.rebooting=False
            if lease is not None: lease.keep_stopped=False
            raise
        except Exception:
            if uncertain: uncertain(expected)
            raise ValueError('Restart acknowledgment is uncertain; admission remains closed until the next boot') from None
        if acknowledged: acknowledged(expected)
    return dict(restarting=True)
