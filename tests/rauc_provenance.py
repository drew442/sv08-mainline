#!/usr/bin/env python3
"""Native per-request signer trust checks; disposable files, private bus/mounts only.

Run with sudo unshare --mount --propagation private python3 ... --execute.
Creates its own tiny verity bundle and test-only keys; never uses physical slots.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exercise(rauc, work):
    work.mkdir(mode=0o700)
    source = work / 'input'
    source.mkdir()
    def run(*args, **kwargs):
        return subprocess.run(list(map(str, args)), capture_output=True, text=True, **kwargs)
    for name in ('signer', 'unrelated'):
        result = run('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                     '-subj', '/CN=SV08-offline-' + name, '-keyout', work / (name+'.key'),
                     '-out', work / (name+'.cert'))
        result.check_returncode()
        (work / (name+'.key')).chmod(0o600)
    for kind in ('rootfs', 'boot'):
        (source / (kind+'.img')).write_bytes(os.urandom(65536))
    (source / 'hook.sh').write_text('#!/bin/sh\nset -eu\nprintf "%s\\n" "${RAUC_BUNDLE_SPKI_HASHES-unset}" >> '+str(work/'hook-hashes')+'\n')
    (source / 'hook.sh').chmod(0o700)
    (source / 'manifest.raucm').write_text('''[update]
compatible=sv08-offline-test-only
version=provenance-fixture
[bundle]
format=verity
[hooks]
filename=hook.sh
[image.rootfs]
filename=rootfs.img
hooks=pre-install
[image.boot]
filename=boot.img
''')
    bundle = work / 'valid.raucb'
    result = run(rauc, 'bundle', '--cert='+str(work/'signer.cert'), '--key='+str(work/'signer.key'),
                 '--mksquashfs-args=-processors 1', source, bundle)
    (work / 'bundle.log').write_text(result.stdout+result.stderr)
    result.check_returncode()
    results = {}
    def info(candidate, name, exception=False, success=False, trust='unrelated'):
        args = [rauc, 'info', '--keyring='+str(work/(trust+'.cert')), '--output-format=json-2']
        if exception:
            args.append('--ignore-signer-trust')
        result = run(*args, candidate)
        (work / (name+'.log')).write_text(result.stdout+result.stderr)
        assert (result.returncode == 0) == success, name+': '+result.stdout+result.stderr
        results[name] = {'returncode': result.returncode}
        return json.loads(result.stdout) if success else None
    info(bundle, 'default-unknown-signer')
    trusted = info(bundle, 'default-trusted-signer', success=True, trust='signer')
    admitted = info(bundle, 'exception-unknown-signer', exception=True, success=True)
    manifest_hash = admitted['manifest-hash']
    assert len(manifest_hash) == 64 and manifest_hash == trusted['manifest-hash']
    # The signature bytes end just before the big-endian 64-bit signature size.
    damaged_sig = work / 'damaged-signature.raucb'
    damaged_payload = work / 'damaged-payload.raucb'
    for target, offset in ((damaged_sig, bundle.stat().st_size-16), (damaged_payload, 4096)):
        shutil.copyfile(bundle, target)
        with target.open('r+b') as stream:
            stream.seek(offset)
            byte = stream.read(1)
            stream.seek(offset)
            stream.write(bytes([byte[0] ^ 1]))
    info(damaged_sig, 'exception-damaged-signature', exception=True)
    data = bundle.read_bytes()
    signature_size = int.from_bytes(data[-8:], 'big')
    signature_start = len(data)-8-signature_size
    malformed_cms = work / 'malformed-cms.raucb'
    malformed_cms.write_bytes(data[:signature_start]+b'\0'+data[signature_start+1:])
    missing_cms = work / 'missing-cms.raucb'
    missing_cms.write_bytes(data[:signature_start]+b'\0'*8)
    info(malformed_cms, 'exception-malformed-cms', exception=True)
    info(missing_cms, 'exception-missing-cms', exception=True)
    # Info authenticates the external manifest, not all verity payload blocks.
    info(damaged_payload, 'exception-damaged-payload-info', exception=True, success=True)
    no_verify = run(rauc, 'info', '--ignore-signer-trust', '--no-verify', bundle)
    assert no_verify.returncode != 0 and 'cannot disable' in no_verify.stderr
    results['no-verify-combination'] = {'returncode': no_verify.returncode}
    images = {image['slot-class']: image for image in admitted['images']}
    assert set(images) == {'boot', 'rootfs'}
    (work / 'state').mkdir()
    slots = {}
    for kind, image in images.items():
        for slot in ('A','B'):
            path = work / (kind+'-'+slot+'.img')
            path.write_bytes(b'preserve-'+kind.encode()+slot.encode())
            with path.open('r+b') as stream:
                stream.truncate(image['size'])
            slots[kind,slot] = path
    originals = {str(path):sha(path) for path in slots.values()}
    chooser = work / 'chooser.py'
    (work / 'chooser.json').write_text(json.dumps({'primary':'A','A':'good','B':'good'}))
    chooser.write_text('''#!/usr/bin/python3
import json, sys
from pathlib import Path
p = Path(__file__).with_name('chooser.json'); s = json.loads(p.read_text()); a = sys.argv[1:]
if a == ['get-primary']: print(s['primary'])
elif a == ['get-current']: print('A')
elif len(a) == 2 and a[0] == 'get-state': print(s[a[1]])
elif len(a) == 2 and a[0] == 'set-primary': s['primary'] = a[1]
elif len(a) == 3 and a[0] == 'set-state': s[a[1]] = a[2]
else: raise SystemExit(1)
p.write_text(json.dumps(s))
''')
    chooser.chmod(0o700)
    config = work / 'system.conf'
    text = f'''[system]
compatible=sv08-offline-test-only
bootloader=custom
bundle-formats=verity
activate-installed=false
perform-pre-check=true
data-directory={work/'state'}
[handlers]
bootloader-custom-backend={chooser}
[keyring]
path={work/'unrelated.cert'}
'''
    for n, slot in enumerate(('A','B')):
        text += f'\n[slot.rootfs.{n}]\ndevice={slots["rootfs",slot]}\ntype=raw\nbootname={slot}\n'
        text += f'\n[slot.boot.{n}]\ndevice={slots["boot",slot]}\ntype=raw\nparent=rootfs.{n}\n'
    config.write_text(text)
    bus = subprocess.Popen(['dbus-daemon','--session','--nofork','--print-address=1'], stdout=subprocess.PIPE, text=True)
    service = None
    try:
        env = dict(os.environ, DBUS_SYSTEM_BUS_ADDRESS=bus.stdout.readline().strip())
        assert env['DBUS_SYSTEM_BUS_ADDRESS']
        with (work/'service.log').open('w') as log:
            service = subprocess.Popen([str(rauc),'--conf='+str(config),'--mount='+str(work/'mount'),
                                        'service','--override-boot-slot=A'], env=env, stdout=log, stderr=log)
            for attempt in range(100):
                status = run(rauc, '--conf='+str(config), 'status', '--output-format=json', env=env)
                if status.returncode == 0:
                    break
                assert service.poll() is None, (work/'service.log').read_text()
                time.sleep(.1)
            else:
                raise AssertionError('RAUC private service not ready')
            def install(candidate, name, exception=False, success=False, required=manifest_hash):
                args = [rauc,'--conf='+str(config),'install','--require-manifest-hash='+required]
                if exception:
                    args.append('--ignore-signer-trust')
                result = run(*args,candidate,env=env)
                (work/(name+'.log')).write_text(result.stdout+result.stderr)
                assert (result.returncode == 0) == success, name+': '+result.stdout+result.stderr
                if not success:
                    assert all(sha(path)==originals[str(path)] for path in slots.values()), name+' wrote a slot'
                results[name] = {'returncode':result.returncode,'slot_writes':success}
            install(bundle,'install-default-unknown-signer')
            install(damaged_sig,'install-exception-damaged-signature',exception=True)
            install(malformed_cms,'install-exception-malformed-cms',exception=True)
            install(missing_cms,'install-exception-missing-cms',exception=True)
            install(damaged_payload,'install-exception-damaged-payload',exception=True)
            assert 'verity' in (work/'install-exception-damaged-payload.log').read_text().lower()
            install(bundle,'install-exception-wrong-manifest',exception=True,required='0'*64)
            install(bundle,'install-exception-unknown-signer',exception=True,success=True)
            for kind,image in images.items():
                assert sha(slots[kind,'A']) == originals[str(slots[kind,'A'])]
                assert sha(slots[kind,'B']) == image['checksum']
            assert json.loads((work/'chooser.json').read_text())['primary'] == 'A'
            assert (work/'hook-hashes').read_text() == '\n', 'Untrusted chain advertised to hook'
            # Trust waiver is per request: strict verification still refuses afterward.
            result = run(rauc,'--conf='+str(config),'install',bundle,env=env)
            assert result.returncode != 0 and 'signature' in (result.stdout+result.stderr).lower()
            results['install-default-after-exception'] = {'returncode':result.returncode}
    finally:
        for process in (service,bus):
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
    report = {'checks':results,'manifest_hash':manifest_hash,'binary_sha256':sha(rauc),
              'bundle_sha256':sha(bundle),'active_pair_unchanged':True,'inactive_pair_matches':True,
              'primary_unchanged':True,'untrusted_hook_spki_empty':True,'physical_hardware':False}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rauc',required=True,type=Path)
    parser.add_argument('--work',required=True,type=Path)
    parser.add_argument('--execute',action='store_true')
    args = parser.parse_args()
    work = args.work.absolute()
    if work.exists() or work.is_symlink() or work.parent.resolve() != work.parent:
        parser.error('Use a new disposable directory with no symlink parents')
    if not args.execute or os.geteuid() != 0:
        parser.error('Requires --execute and root in a private mount namespace')
    if os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
        parser.error('Requires a private mount namespace')
    exercise(args.rauc.resolve(strict=True), work)


if __name__ == '__main__':
    main()
