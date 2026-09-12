#!/usr/bin/env python3
"""Real native RAUC admission negatives; never installs or selects a slot."""
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_bundle import inspect


def checks(fixture,rauc):
    policy=json.loads((fixture/'policy.json').read_text());bundle=fixture/'signed.raucb';key=fixture/'keyring.pem'
    result=inspect(bundle,policy,key,rauc);assert result['full_payload_verified'] is False
    rejected=[]
    for field,value in [('compatible','other-profile'),('layout','other-layout'),('klipper_commit','a'*40),('state_schema',2),('max_bundle_bytes',1)]:
        bad=dict(policy);bad[field]=value
        try:inspect(bundle,bad,key,rauc)
        except ValueError:rejected.append(field)
        else:raise AssertionError(field)
    with tempfile.TemporaryDirectory(dir=fixture) as tmp:
        root=Path(tmp);corrupt=root/'corrupt.raucb';payload=bytearray(bundle.read_bytes());payload[-100]^=1;corrupt.write_bytes(payload)
        try:inspect(corrupt,policy,key,rauc)
        except ValueError:rejected.append('tampered-signature')
        else:raise AssertionError('tampered signature accepted')
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(root/'private.key'),'-out',str(root/'wrong.pem'),'-days','1','-subj','/CN=untrusted fixture'],check=True,capture_output=True)
        try:inspect(bundle,policy,root/'wrong.pem',rauc)
        except ValueError:rejected.append('untrusted-keyring')
        else:raise AssertionError('untrusted signature accepted')
    return dict(proof=result,rejected=rejected,rauc_sha256=hashlib.sha256(rauc.read_bytes()).hexdigest(),scope='native real RAUC signature tooling; tiny synthetic policy; no installation')


if __name__=='__main__':print(json.dumps(checks(Path(sys.argv[1]),Path(sys.argv[2])),indent=2))
