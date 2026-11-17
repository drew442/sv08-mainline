#!/usr/bin/env python3
"""Real disposable mounts and slot-local account replacement; no host PAM writes.

Run under sudo unshare --mount --propagation private with root-safe scratch.
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
from sv08_owner import Owner, shadow_text

with tempfile.TemporaryDirectory(prefix='sv08-mount-test-', dir=os.environ.get('SV08_TEST_ROOT')) as temporary:
    base = Path(temporary); data = base/'data'
    store = Store(data, reserve_bytes=0); store.initialize(); (data/'system').chmod(0o700)
    owner=Owner(data); owner.save('fixture owner password','fixture owner password',owner.status())
    for name,raw in [('machine-id','0'*32+'\n'),('hostname','sv08\n'),('hosts','127.0.0.1 localhost\n'),('random-seed','')]:
        (data/'system'/name).write_text(raw)
    roots={}; package_entries={slot:'' for slot in ('A','B')}
    for slot in ('A','B'):
        root=base/('root-'+slot);root.mkdir();roots[slot]=root
        for source, destination in BINDS.items():
            dest=root/destination;dest.parent.mkdir(parents=True,exist_ok=True)
            if (data/source).is_file():dest.touch()
            else:dest.mkdir(exist_ok=True)
        for path in list(TMPFS)+['run','var/lib/dpkg','etc']:(root/path).mkdir(parents=True,exist_ok=True)
        (root/'etc/passwd').write_text('root:x:0:0::/root:/bin/bash\nsv08:x:1000:1000::/home/sv08:/bin/bash\n')
        (root/'etc/shadow').write_text('root:*:1:2:3:4:5:6:7\nsv08:*::0:99999:7:::\ndaemon:!:10:0:99999:7:::\n')
        (root/'etc/shadow').chmod(0o640)
        (root/'var/lib/dpkg/status').write_text('slot-local package database')
    boots=[('A','immutable',False),('A','writable',False),('B','writable',True),
           ('A','writable',False),('A','immutable',False),('B','immutable',False)]
    for slot,mode,reset in boots:
        if reset:owner.save('rotated owner password','rotated owner password',owner.status(),reset=True)
        root=roots[slot];path=root/'etc/shadow';before=path.stat()
        expected=shadow_text(path.read_text(),(root/'etc/passwd').read_text(),owner.load()[0]['password_hash'])
        subprocess.run(['mount','--bind',str(root),str(root)],check=True)
        try:
            subprocess.run(['mount','-t','tmpfs','tmpfs',str(root/'run')],check=True)
            store.policy(mode=mode);boot=store.prepare_boot(slot,'release-1')
            apply(root,data,boot,bind_root=True,owner_setup=True)
            assert path.read_text()==expected
            assert path.read_text().endswith('daemon:!:10:0:99999:7:::\n'+package_entries[slot])
            mounted=subprocess.run(['findmnt','--mountpoint',str(path),'--noheadings'],stdout=subprocess.DEVNULL).returncode==0
            assert mounted==(mode=='immutable')
            if mode=='immutable':
                try:path.write_text('unexpected');raise AssertionError('Immutable shadow accepted a write')
                except OSError as error:assert error.errno==errno.EROFS,error
            else:
                after=path.stat()
                assert (after.st_uid,after.st_gid,after.st_mode)==(before.st_uid,before.st_gid,before.st_mode)
                if not package_entries[slot]:
                    append='package-append-'+slot+':!:22000:0:99999:7:::\n'
                    replace='package-replace-'+slot+':!:22000:0:99999:7:::\n'
                    with path.open('a') as stream:stream.write(append)
                    staged=path.with_name('shadow.package');staged.write_text(path.read_text()+replace);staged.chmod(0o640)
                    os.replace(staged,path);package_entries[slot]=append+replace
                    assert path.read_text().endswith(package_entries[slot])
            try:
                (root/'etc/os-write-test').write_text('customization')
                assert mode=='writable','immutable root accepted a write'
            except OSError as error:assert mode=='immutable' and error.errno==errno.EROFS,error
            assert (root/'var/lib/dpkg/status').read_text()=='slot-local package database'
            (root/'home/sv08/persistent.txt').write_text(mode)
            assert (data/'users/sv08/persistent.txt').read_text()==mode
            (root/'run/sv08/printer_data/config/test.cfg').write_text(mode)
            (root/'var/cache/temporary').write_text('ephemeral');assert not (data/'var/cache').exists()
        finally:subprocess.run(['umount','-R',str(root)],check=True)
    for slot in ('A','B'):
        assert store.load()['slots'][slot]['customized']
        assert (roots[slot]/'etc/shadow').read_text().endswith(package_entries[slot])
    print(json.dumps(dict(real_mount_namespace=True,immutable_write_rejected=True,writable_write_succeeded=True,
                          persistent_write_succeeded=True,both_mode_transitions=True,dpkg_slot_local=True,
                          immutable_shadow_readonly=True,writable_shadow_regular=True,package_shadow_atomic_replace=True,
                          package_accounts_survive_same_slot_boot=True,owner_reset_AB=True)))
