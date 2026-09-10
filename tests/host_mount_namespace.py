#!/usr/bin/env python3
"""Real mount/write assertions. Run under sudo unshare --mount --propagation private.

The only mounted paths are disposable directories created by this script.
"""
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'runtime'))
from sv08_state import Store
from sv08_mounts import BINDS, TMPFS, apply

with tempfile.TemporaryDirectory(prefix='sv08-mount-test-') as temporary:
    base = Path(temporary)
    data = base / 'data'
    store = Store(data, reserve_bytes=0)
    store.initialize()
    (data / 'system/machine-id').write_text('0' * 32 + '\n')
    (data / 'system/hostname').write_text('sv08\n')
    (data / 'system/hosts').write_text('127.0.0.1 localhost\n')
    (data / 'system/random-seed').touch()
    for mode in ('immutable', 'writable', 'immutable'):
        root = base / ('root-' + mode + '-' + os.urandom(3).hex())
        root.mkdir()
        for source, destination in BINDS.items():
            dst = root / destination
            dst.parent.mkdir(parents=True, exist_ok=True)
            if (data / source).is_file():
                dst.touch()
            else:
                dst.mkdir(exist_ok=True)
        for path in list(TMPFS) + ['run', 'var/lib/dpkg', 'etc']:
            (root / path).mkdir(parents=True, exist_ok=True)
        (root / 'var/lib/dpkg/status').write_text('slot-local package database')
        subprocess.run(['mount', '--bind', str(root), str(root)], check=True)
        subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', str(root / 'run')], check=True)
        store.policy(mode=mode)
        boot = store.prepare_boot('A', 'release-1')
        apply(root, data, boot, bind_root=True)
        try:
            (root / 'etc/os-write-test').write_text('customization')
            assert mode == 'writable', 'immutable root accepted a write'
        except OSError as error:
            assert mode == 'immutable' and error.errno == errno.EROFS, error
        assert (root / 'var/lib/dpkg/status').read_text() == 'slot-local package database'
        (root / 'home/sv08/persistent.txt').write_text(mode)
        assert (data / 'users/sv08/persistent.txt').read_text() == mode
        (root / 'run/sv08/printer_data/config/test.cfg').write_text(mode)
        (root / 'var/cache/temporary').write_text('ephemeral')
        assert not (data / 'var/cache').exists()
        subprocess.run(['umount', '-R', str(root)], check=True)
    assert store.load()['slots']['A']['customized']
    print(json.dumps({'real_mount_namespace': True, 'immutable_write_rejected': True,
                      'writable_write_succeeded': True, 'persistent_write_succeeded': True,
                      'both_mode_transitions': True, 'dpkg_slot_local': True}))
