#!/usr/bin/env python3
"""Guest-only RAUC partition test on an explicitly identified disposable QEMU disk.

Requires --execute, QEMU virtualization, the fixture disk serial, non-deployable
release metadata and no mounted inactive targets. Never install on a printer.
This tests actual ext4/vfat handlers; the boot chooser remains a test double.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()
if not args.execute:
    print('Inspection only: requires --execute inside the disposable QEMU guest.')
    sys.exit(0)
if subprocess.check_output(['systemd-detect-virt', '--vm'], text=True).strip() != 'qemu':
    sys.exit('Refusing to run outside QEMU')
if subprocess.check_output(['lsblk', '-dn', '-o', 'SERIAL', '/dev/vda'], text=True).strip() != 'SV08-QEMU-DISPOSABLE':
    sys.exit('Refusing an unidentified disk')
config = json.loads(Path('/usr/lib/sv08/release.json').read_text())
if config.get('deployable') is not False:
    sys.exit('Refusing a deployable image')
sys.path.insert(0, '/usr/lib/sv08')
from sv08_boot import slot_from_cmdline, verify_devices


def sha(path, size):
    h = hashlib.sha256()
    with open(path, 'rb', buffering=0) as stream:
        while size:
            data = stream.read(min(size, 1024*1024))
            if not data:
                raise ValueError('Short partition read')
            h.update(data)
            size -= len(data)
    return h.hexdigest()


bus = service = None
try:
    assert slot_from_cmdline(Path('/proc/cmdline').read_text()) == 'A'
    verify_devices(config, 'A')
    boot = json.loads(Path('/run/sv08/boot.json').read_text())
    assert boot['mode'] == 'immutable' and not boot['trial']
    version = subprocess.check_output(['rauc', '--version'], text=True).strip()
    assert version == 'rauc 1.15.2', version
    targets = {('rootfs', 'A'): config['devices']['root-a'], ('boot', 'A'): config['devices']['boot-a'],
               ('rootfs', 'B'): config['devices']['root-b'], ('boot', 'B'): config['devices']['boot-b']}
    mounted = {line.split()[2] for line in Path('/proc/self/mountinfo').read_text().splitlines()}
    for (kind, slot), path in targets.items():
        assert subprocess.check_output(['lsblk', '-dn', '-o', 'PKNAME', path], text=True).strip() == 'vda'
        if slot == 'B':
            dev = os.stat(path).st_rdev
            assert f'{os.major(dev)}:{os.minor(dev)}' not in mounted, 'Inactive target is mounted'
    fixture = Path('/data/fixture')
    bundle, cert = fixture / 'paired.raucb', fixture / 'test.cert'
    info = json.loads(subprocess.check_output(['rauc', 'info', '--keyring='+str(cert),
                                             '--output-format=json-2', str(bundle)], text=True))
    assert info['update']['compatible'] == 'sv08-offline-test-only'
    assert info['bundle']['format'] == 'verity'
    images = {x['slot-class']: x for x in info['images']}
    assert set(images) == {'rootfs', 'boot'} and len(info['images']) == 2
    for (kind, slot), path in targets.items():
        assert int(subprocess.check_output(['blockdev', '--getsize64', path], text=True)) == images[kind]['size']
    before = {kind: sha(targets[kind, 'A'], image['size']) for kind, image in images.items()}
    work = Path('/data/sv08/qemu-rauc')
    work.mkdir(mode=0o700)
    (work / 'state').mkdir()
    chooser = work / 'chooser.py'
    (work / 'chooser.json').write_text(json.dumps({'primary': 'A', 'A': 'good', 'B': 'good'}))
    chooser.write_text('''#!/usr/bin/python3
import json,sys
from pathlib import Path
p=Path(__file__).with_name('chooser.json'); s=json.loads(p.read_text()); a=sys.argv[1:]
if a==['get-primary']: print(s['primary'])
elif a==['get-current']: print('A')
elif len(a)==2 and a[0]=='get-state': print(s[a[1]])
elif len(a)==2 and a[0]=='set-primary': s['primary']=a[1]
elif len(a)==3 and a[0]=='set-state': s[a[1]]=a[2]
else: raise SystemExit(1)
p.write_text(json.dumps(s))
''')
    chooser.chmod(0o700)
    system = work / 'system.conf'
    text = f'''[system]
compatible=sv08-offline-test-only
bootloader=custom
bundle-formats=verity
activate-installed=false
perform-pre-check=true
data-directory={work / 'state'}
[handlers]
bootloader-custom-backend={chooser}
[keyring]
path={cert}
'''
    for number, slot in enumerate(('A', 'B')):
        text += f'\n[slot.rootfs.{number}]\ndevice={targets["rootfs",slot]}\ntype=ext4\nbootname={slot}\n'
        text += f'\n[slot.boot.{number}]\ndevice={targets["boot",slot]}\ntype=vfat\nparent=rootfs.{number}\n'
    system.write_text(text)
    bus = subprocess.Popen(['dbus-daemon', '--session', '--nofork', '--print-address=1'], stdout=subprocess.PIPE, text=True)
    address = bus.stdout.readline().strip()
    assert address
    env = dict(os.environ, DBUS_SYSTEM_BUS_ADDRESS=address)
    with (work / 'service.log').open('w') as log:
        service = subprocess.Popen(['rauc', '--conf='+str(system), '--mount=/run/qemu-rauc',
                                    'service', '--override-boot-slot=A'], env=env, stdout=log, stderr=log)
        for attempt in range(100):
            status = subprocess.run(['rauc', '--conf='+str(system), 'status'], env=env, capture_output=True)
            if status.returncode == 0:
                break
            if service.poll() is not None:
                raise RuntimeError((work / 'service.log').read_text())
            time.sleep(.1)
        else:
            raise RuntimeError('RAUC service did not start')
        with (work / 'install.log').open('w') as install_log:
            result = subprocess.run(['rauc', '--conf='+str(system), 'install', str(bundle)],
                                    env=env, stdout=install_log, stderr=install_log)
        if result.returncode:
            raise RuntimeError((work / 'install.log').read_text())
        for kind, image in images.items():
            assert sha(targets[kind, 'A'], image['size']) == before[kind], 'Active partition changed'
            assert sha(targets[kind, 'B'], image['size']) == image['checksum'], 'Inactive image hash mismatch'
        state = json.loads((work / 'chooser.json').read_text())
        assert state == {'primary': 'A', 'A': 'good', 'B': 'bad'}, state
        filesystem = os.statvfs('/data')
        free = filesystem.f_bavail * filesystem.f_frsize
        assert free >= 512*1024*1024, 'Persistent free-space reserve was consumed'
        report = dict(passed=True, kernel=os.uname().release, rauc=version,
                      slot_handlers=['ext4','vfat'], active_pair_unchanged=True,
                      inactive_pair_matches_signed_images=True, primary_unchanged=True,
                      inactive_remains_bad_until_activation=True, bundle_bytes=bundle.stat().st_size,
                      data_available_bytes=free, hardware=False)
        (work / 'result.json').write_text(json.dumps(report, indent=2)+'\n')
        print('SV08_QEMU_RAUC_RESULT '+json.dumps(report), flush=True)
except BaseException as error:
    print('SV08_QEMU_RAUC_FAILURE '+repr(error), flush=True)
finally:
    for process in (service, bus):
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    try:
        subprocess.run(['systemctl', 'poweroff'], check=True, timeout=20)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        subprocess.run(['systemctl', '--force', 'poweroff'], check=False)
