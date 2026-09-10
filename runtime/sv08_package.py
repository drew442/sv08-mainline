#!/usr/bin/env python3
"""Idle/offline package workflow for writable mode, with a shared admission lock.

Until the active-printer admission extension is validated, require the supported
printer services to be stopped. Never stop an active job to satisfy this check.
This fills the policy gap between apt/dpkg and image/state transactions (ADR 0006).
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from sv08_state import Store, atomic_json

SERVICES = ('sv08-klipper.service', 'sv08-moonraker.service')


def require_writable(boot, state, service_states):
    if boot['mode'] != 'writable' or state['requested_mode'] != 'writable':
        raise ValueError('Package changes require writable mode applied at boot')
    if state['pending']:
        raise ValueError('Finish or cancel the pending image transaction first')
    if any(service_states.get(name) not in ('inactive', 'failed') for name in SERVICES):
        raise ValueError('Stop the printer services while idle before package changes; no service is stopped automatically')


def hook():
    token = os.environ.get('SV08_PACKAGE_TOKEN')
    lease = json.loads(Path('/run/sv08/package-lease.json').read_text())
    if not token or token != lease['token']:
        raise ValueError('Use sv08-package for supported apt operations')
    os.kill(lease['pid'], 0)
    with open('/run/sv08/admission.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        raise ValueError('Package admission lease is no longer held')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--hook', action='store_true')
    p.add_argument('apt_args', nargs=argparse.REMAINDER)
    args = p.parse_args()
    if args.hook:
        hook()
        return
    if not args.apt_args:
        p.error('Specify apt-get arguments, for example: --execute install package-name')
    if not args.execute:
        print(json.dumps(dict(execute=False, command=['apt-get'] + args.apt_args)))
        return
    if os.geteuid() != 0:
        p.error('Supported package operations require root')
    boot = json.loads(Path('/run/sv08/boot.json').read_text())
    store = Store('/data/sv08')
    with store.locked(), open('/run/sv08/admission.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = store.load()
        services = {name: subprocess.check_output(['systemctl', 'show', '-p', 'ActiveState', '--value', name], text=True).strip() for name in SERVICES}
        require_writable(boot, state, services)
        if os.statvfs('/').f_flag & os.ST_RDONLY:
            raise ValueError('Root filesystem is still read-only')
        state['slots'][boot['slot']]['customized'] = True
        store.save(state)
        token = uuid.uuid4().hex
        lease = Path('/run/sv08/package-lease.json')
        atomic_json(lease, dict(token=token, pid=os.getpid()))
        history = store.root / 'customizations'
        history.mkdir(exist_ok=True, mode=0o700)
        record = dict(slot=boot['slot'], release=boot['release'], command=['apt-get'] + args.apt_args,
                      status='started', reconciliation='required-before-image-update')
        record_path = history / (token + '.json')
        atomic_json(record_path, record)
        try:
            result = subprocess.run(['apt-get'] + args.apt_args, env=dict(os.environ, SV08_PACKAGE_TOKEN=token))
            record['exit_status'] = result.returncode
            record['status'] = 'completed' if result.returncode == 0 else 'failed'
            record['packages'] = subprocess.check_output(['dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\n'], text=True).splitlines()
            record['manual_packages'] = subprocess.check_output(['apt-mark', 'showmanual'], text=True).splitlines()
            atomic_json(record_path, record)
        finally:
            lease.unlink(missing_ok=True)
        sys.exit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, FileNotFoundError, BlockingIOError) as error:
        sys.exit(str(error))
