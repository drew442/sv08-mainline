#!/usr/bin/env python3
"""Create tiny real signed RAUC fixtures in a fresh private offline directory.

No keys enter production staging or the guest; guest consumes certificate/policy.
Synthetic image dimensions do not represent deployable slots.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def create(work, rauc):
    work.mkdir(mode=0o700, parents=True, exist_ok=False)
    content = work / 'content'; content.mkdir()
    for name in ('rootfs', 'boot'):
        (content / (name+'.img')).write_bytes(hashlib.shake_256(name.encode()).digest(256*1024))
    pin = 'f089b5d53c6ca5ed2e7fc5c0e481c2e61aaeffdd'
    policy = dict(compatible='sv08-upload-fixture', layout='upload-fixture-v1', state_schema=1,
                  klipper_commit=pin, max_bundle_bytes=8*1024*1024,
                  image_bytes=dict(rootfs=256*1024, boot=256*1024))
    (work / 'policy.json').write_text(json.dumps(policy))
    (content / 'manifest.raucm').write_text(f'''[update]
compatible=sv08-upload-fixture
version=upload-fixture-1
[bundle]
format=verity
[image.rootfs]
filename=rootfs.img
[image.boot]
filename=boot.img
[meta.sv08]
layout=upload-fixture-v1
state-schema=1
klipper-commit={pin}
''')
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(work/'private.key'),
                    '-out',str(work/'keyring.pem'),'-days','30','-subj','/CN=SV08 disposable upload fixture'],check=True,capture_output=True)
    (work/'private.key').chmod(0o600)
    subprocess.run([str(rauc),'bundle','--cert='+str(work/'keyring.pem'),'--key='+str(work/'private.key'),
                    '--signing-keyring='+str(work/'keyring.pem'),str(content),str(work/'signed.raucb')],check=True)
    return {name:hashlib.sha256((work/name).read_bytes()).hexdigest() for name in ('signed.raucb','policy.json','keyring.pem')}


if __name__ == '__main__': print(json.dumps(create(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())))
