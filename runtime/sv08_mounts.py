#!/usr/bin/env python3
"""Apply explicit state mounts; never overlay the whole root, /etc or /var.

Used by the early boot integration after device identity and release checks.
Mount operations are separate from state preparation. Tests use private Linux
mount namespaces and disposable directories, never printer media.
"""
import json
import os
from pathlib import Path
import subprocess

# Destinations must exist in the image before its first read-only boot.
BINDS = {
    'system/machine-id': 'etc/machine-id',
    'system/hostname': 'etc/hostname',
    'system/hosts': 'etc/hosts',
    'system/network-connections': 'etc/NetworkManager/system-connections',
    'system/network-state': 'var/lib/NetworkManager',
    'system/rauc': 'var/lib/rauc',
    'system/random-seed': 'var/lib/systemd/random-seed',
    'system/timesync': 'var/lib/systemd/timesync',
    'system/rfkill': 'var/lib/systemd/rfkill',
    'system/linger': 'var/lib/systemd/linger',
    'shared/logs': 'var/log',
    'users/sv08': 'home/sv08',
}
TMPFS = {'tmp': 'mode=1777,size=64M', 'var/tmp': 'mode=1777,size=32M',
         'var/cache': 'mode=0755,size=96M'}


def plan(root, data, boot):
    root, data = Path(root).absolute(), Path(data).absolute()
    if boot['mode'] not in ('immutable', 'writable'):
        raise ValueError('Unknown mode')
    generation = Path(boot['generation'])
    if generation.parent != data / 'generations' or generation.is_symlink():
        raise ValueError('Generation outside persistent store')
    actions = []
    for src, dest in BINDS.items():
        actions.append(('bind', str(data / src), str(root / dest)))
    for dest, options in TMPFS.items():
        actions.append(('tmpfs', options, str(root / dest)))
    # /run is supplied by systemd. The app-facing view is created there each boot.
    actions.append(('view', str(generation), str(root / 'run/sv08/printer_data')))
    actions.append(('mode', boot['mode'], str(root)))
    return actions


def apply(root, data, boot, bind_root=False):
    root, data = Path(root).absolute(), Path(data).absolute()
    actions = plan(root, data, boot)
    if subprocess.run(['findmnt', '--mountpoint', str(root), '--noheadings'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        raise ValueError('Root must be an existing mount point')
    for kind, source, destination in actions:
        dest = Path(destination)
        for p in (dest, *dest.parents):
            if p.is_symlink():
                raise ValueError('Mount target contains a symlink: ' + str(p))
        if kind == 'bind':
            src = Path(source)
            if not src.exists() or src.is_symlink() or not dest.exists():
                raise ValueError('Missing/invalid explicit mount path: ' + destination)
    mounted = []
    try:
        for kind, source, destination in actions:
            if kind == 'bind':
                subprocess.run(['mount', '--bind', source, destination], check=True)
                mounted.append(destination)
            elif kind == 'tmpfs':
                subprocess.run(['mount', '-t', 'tmpfs', '-o', source, 'tmpfs', destination], check=True)
                mounted.append(destination)
            elif kind == 'view':
                view = Path(destination)
                view.mkdir(parents=True, exist_ok=False)
                for name in ('config', 'database', 'ui'):
                    (view / name).symlink_to(Path(source) / name)
                for name in ('gcodes', 'timelapse'):
                    (view / name).symlink_to(data / 'shared' / name)
                (view / 'logs').symlink_to(data / 'shared/logs/printer')
                (view / 'comms').mkdir()
            elif kind == 'mode':
                options = 'remount,' + ('bind,' if bind_root else '') + ('ro' if source == 'immutable' else 'rw')
                subprocess.run(['mount', '-o', options, destination], check=True)
        status = root / 'run/sv08/boot.json'
        status.write_text(json.dumps(boot, indent=2) + '\n')
    except BaseException:
        # Caller leaves printer services stopped and enters diagnostics/recovery.
        # Do not silently continue with incomplete persistent mounts.
        for destination in reversed(mounted):
            subprocess.run(['umount', destination], check=False)
        raise
