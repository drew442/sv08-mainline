#!/usr/bin/env python3
"""Exercise native RAUC against disposable regular-file slots and a private D-Bus.

Requires root and an explicit --execute. Inputs must be offline test artifacts.
Never points RAUC at physical block devices. The custom chooser is a test double;
U-Boot environment integration is tested separately, not established here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

REPO = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rauc', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--keyring', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    rauc, bundle, keyring, work = (x.resolve() for x in (a.rauc, a.bundle, a.keyring, a.work))
    if not work.is_relative_to(REPO / 'build') or work == REPO / 'build' or work.exists():
        p.error('Use a new disposable directory below build/')
    info = json.loads(subprocess.check_output([str(rauc), 'info', '--keyring='+str(keyring),
                      '--output-format=json-2', str(bundle)], text=True))
    if info['update']['compatible'] != 'sv08-offline-test-only' or info['bundle']['format'] != 'verity':
        p.error('Only the explicit offline test verity bundle is accepted')
    images = {image['slot-class']: image for image in info['images']}
    if set(images) != {'boot', 'rootfs'} or len(info['images']) != 2:
        p.error('Expected exactly paired boot/root images')
    print(json.dumps({'execute': a.execute, 'work': str(work), 'compatible': info['update']['compatible']}), flush=True)
    if not a.execute:
        return
    if os.geteuid() != 0:
        p.error('RAUC loop/verity mounts need root; run in a private mount namespace')
    work.mkdir(mode=0o700)
    (work / 'state').mkdir()
    slots = {}
    for slot in ('A', 'B'):
        for kind, image in images.items():
            path = work / f'{kind}-{slot}.img'
            with path.open('xb') as stream:
                stream.write(f'preserve-{kind}-{slot}'.encode())
                stream.truncate(image['size'])
            slots[kind, slot] = path
    originals = {str(path): sha(path) for path in slots.values()}
    chooser_state = work / 'chooser.json'
    chooser_state.write_text(json.dumps({'primary': 'A', 'A': 'good', 'B': 'good'}))
    chooser = work / 'chooser.py'
    chooser.write_text('''#!/usr/bin/python3
import json, sys
from pathlib import Path
path = Path(__file__).with_name('chooser.json')
s = json.loads(path.read_text())
a = sys.argv[1:]
if a == ['get-primary']: print(s['primary'])
elif a == ['get-current']: print('A')
elif len(a) == 2 and a[0] == 'get-state': print(s[a[1]])
elif len(a) == 2 and a[0] == 'set-primary': s['primary'] = a[1]
elif len(a) == 3 and a[0] == 'set-state': s[a[1]] = a[2]
else: raise SystemExit(1)
path.write_text(json.dumps(s))
''')
    chooser.chmod(0o700)
    config = work / 'system.conf'
    text = f'''[system]
compatible=sv08-offline-test-only
bootloader=custom
bundle-formats=verity
activate-installed=false
data-directory={work / 'state'}
perform-pre-check=true
[handlers]
bootloader-custom-backend={chooser}
[keyring]
path={keyring}
'''
    for number, slot in enumerate(('A', 'B')):
        text += f'\n[slot.rootfs.{number}]\ndevice={slots["rootfs", slot]}\ntype=raw\nbootname={slot}\n'
        text += f'\n[slot.boot.{number}]\ndevice={slots["boot", slot]}\ntype=raw\nparent=rootfs.{number}\n'
    config.write_text(text)
    bus = subprocess.Popen(['dbus-daemon', '--session', '--nofork', '--print-address=1'], stdout=subprocess.PIPE, text=True)
    service = None
    try:
        address = bus.stdout.readline().strip()
        if not address:
            raise RuntimeError('Private D-Bus did not start')
        env = dict(os.environ, DBUS_SYSTEM_BUS_ADDRESS=address)
        with (work / 'service.log').open('w') as log:
            def start(compatible, trust=keyring):
                process = subprocess.Popen([str(rauc), '--conf='+str(config),
                    '--confopt=system:compatible='+compatible, '--confopt=keyring:path='+str(trust),
                    '--mount='+str(work / 'mount'),
                    'service', '--override-boot-slot=A'], env=env, stdout=log, stderr=log)
                try:
                    for attempt in range(100):
                        status = subprocess.run([str(rauc), '--conf='+str(config), 'status', '--output-format=json'],
                                                env=env, capture_output=True, text=True)
                        if status.returncode == 0:
                            return process
                        if process.poll() is not None:
                            raise RuntimeError('RAUC service failed: ' + (work / 'service.log').read_text())
                        time.sleep(.1)
                    raise RuntimeError('Private RAUC service did not become ready')
                except BaseException:
                    process.terminate()
                    process.wait(timeout=10)
                    raise

            rejected = {}
            def reject(candidate, name, expected_error):
                result = subprocess.run([str(rauc), '--conf='+str(config), 'install', str(candidate)],
                                        env=env, capture_output=True, text=True)
                output = result.stdout + result.stderr
                (work / (name+'.log')).write_text(output)
                assert result.returncode != 0, name + ' was accepted'
                assert expected_error.lower() in output.lower(), output
                assert all(sha(path) == originals[str(path)] for path in slots.values()), name + ' altered a slot'
                rejected[name] = 'rejected before slot writes'

            wrong_key = work / 'wrong-trust.key'
            wrong_cert = work / 'wrong-trust.cert'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                            '-keyout', str(wrong_key), '-out', str(wrong_cert), '-days', '1',
                            '-subj', '/CN=SV08-wrong-trust-test-only'], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            wrong_key.chmod(0o600)
            service = start('sv08-offline-test-only', wrong_cert)
            reject(bundle, 'untrusted-signature', 'signature')
            service.terminate()
            service.wait(timeout=10)
            service = start('sv08-wrong-target-test')
            reject(bundle, 'wrong-compatible', 'compatible')
            service.terminate()
            service.wait(timeout=10)
            service = start('sv08-offline-test-only')
            # Mutate payload and CMS signature separately. Signature-only info
            # checks cannot establish the integrity of all verity payload blocks.
            for name, offset, expected in [('corrupt-payload', 4096, 'verity'),
                                           ('corrupt-signature', bundle.stat().st_size-16, 'signature')]:
                damaged = work / (name+'.raucb')
                subprocess.run(['cp', '--reflink=auto', str(bundle), str(damaged)], check=True)
                with damaged.open('r+b') as stream:
                    stream.seek(offset)
                    byte = stream.read(1)
                    stream.seek(offset)
                    stream.write(bytes([byte[0] ^ 1]))
                reject(damaged, name, expected)
            result = subprocess.run([str(rauc), '--conf='+str(config), 'install', str(bundle)],
                                    env=env, capture_output=True, text=True)
            (work / 'install.log').write_text(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError('RAUC installation failed; inspect ' + str(work / 'install.log'))
            for kind, image in images.items():
                assert sha(slots[kind, 'A']) == originals[str(slots[kind, 'A'])], 'Active slot changed'
                assert sha(slots[kind, 'B']) == image['checksum'], 'Inactive slot differs from signed image'
            state = json.loads(chooser_state.read_text())
            assert state['primary'] == 'A', 'Staging unexpectedly selected new primary'
            report = {'active_pair_unchanged': True, 'inactive_pair_matches_signed_hashes': True,
                      'activate_installed_false_preserves_primary': True, 'chooser_after_install': state,
                      'rejected_bundles': rejected,
                      'slot_backend': 'regular-file raw test fixtures', 'physical_hardware': False}
            (work / 'result.json').write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps(report, indent=2))
    finally:
        for process in (service, bus):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    main()
