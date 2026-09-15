#!/usr/bin/env python3
"""Build and run the disposable ARM64 RAUC interrupted-job fixture.

Default mode inspects prerequisites. ``--execute`` creates a fresh ignored
directory below ``build/`` and boots QEMU with no network or host devices.  The
fixture uses a signed hook only to hold an installation deterministically; it is
not a production RAUC handler or host-image input.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]


def asset_repo():
    """Locate shared ignored build inputs when this test runs from a worktree."""
    listing = subprocess.check_output(['git', '-C', str(REPO), 'worktree', 'list', '--porcelain'], text=True)
    for line in listing.splitlines():
        if line.startswith('worktree '):
            candidate = Path(line.removeprefix('worktree '))
            if (candidate / 'build/host-rauc-v1/rootfs/usr/bin/rauc').is_file():
                return candidate
    raise ValueError('No worktree exposes the reviewed ignored ARM64 fixture inputs')


ASSETS = asset_repo()
BASE = ASSETS / 'build/host-rauc-v1/rootfs'
NATIVE_RAUC = ASSETS / 'build/rauc-native-v2/rauc'
KERNEL = BASE / 'boot/vmlinuz-6.12.107+deb13-arm64'
INITRD = BASE / 'boot/initrd.img-6.12.107+deb13-arm64'
GUEST = REPO / 'tests/fixtures/rauc-resolution/qemu-rauc-resolution.py'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, **kwargs):
    return subprocess.run([str(item) for item in command], check=True, **kwargs)


def write(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(mode)


def require(path, description):
    if not path.is_file() or path.is_symlink():
        raise ValueError('Missing reviewed ' + description + ': ' + str(path))


def bundle(work):
    content = work / 'bundle-content'
    content.mkdir()
    images = {}
    for name in ('rootfs', 'boot'):
        value = hashlib.shake_256(('rauc-resolution-' + name).encode()).digest(256 * 1024)
        (content / (name + '.img')).write_bytes(value)
        images[name] = hashlib.sha256(value).hexdigest()
    write(content / 'hook.sh', '''#!/bin/sh
case "$1" in
  slot-pre-install)
    if [ "$RAUC_SLOT_CLASS" = rootfs ]; then
      : > /data/fixture/barrier-entered
      while [ ! -e /data/fixture/release-barrier ]; do sleep 1; done
    fi
    ;;
  *) exit 1 ;;
esac
exit 0
''', 0o755)
    write(content / 'manifest.raucm', '''[update]
compatible=sv08-rauc-resolution-fixture
version=rauc-resolution-fixture-1
description=Disposable signed paired RAUC interruption fixture

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
    key, certificate = work / 'fixture.key', work / 'fixture.cert'
    run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key,
         '-out', certificate, '-days', '2', '-subj', '/CN=SV08 RAUC resolution fixture'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    key.chmod(0o600)
    output = work / 'signed.raucb'
    run([NATIVE_RAUC, 'bundle', '--cert=' + str(certificate), '--key=' + str(key),
         '--signing-keyring=' + str(certificate), content, output])
    return output, certificate, images


def prepare(work):
    root, seed = work / 'rootfs', work / 'data-seed'
    # The selected root was prepared in a live-like build tree.  Its /dev has
    # character devices (including /dev/zero), while proc/sys/run/tmp are
    # volatile mount points.  They must never be copied into a filesystem image.
    shutil.copytree(BASE, root, symlinks=True,
                    ignore=lambda directory, names: {'dev', 'proc', 'sys', 'run', 'tmp'}
                    if Path(directory) == BASE else set())
    for name in ('dev', 'proc', 'sys', 'run', 'tmp'):
        (root / name).mkdir()
    # Service identity intentionally requires immutable configuration.  The
    # test root is booted with ``ro`` and fstab retains that state if systemd
    # performs its normal root-remount unit.
    write(root / 'etc/fstab', 'rootfs / ext4 ro 0 1\n')
    for name in ('qemu-rauc.service', 'qemu-probe.service'):
        (root / 'etc/systemd/system/multi-user.target.wants' / name).unlink(missing_ok=True)
    # sv08-prepare deliberately requires the complete production A/B state
    # layout. This service-only fixture has a synthetic data disk, so mask the
    # inherited unit before boot rather than weakening its production checks.
    prepare = root / 'etc/systemd/system/sv08-prepare.service'
    prepare.unlink(missing_ok=True)
    prepare.symlink_to('/dev/null')
    # The selected initramfs owns the persistent-data mount and verifies a
    # fixed PARTUUID before systemd starts.  Keep that real identity boundary
    # in the fixture instead of replacing it with a systemd mount unit.
    (root / 'etc/systemd/system/data.mount').unlink(missing_ok=True)
    (root / 'etc/systemd/system/local-fs.target.wants/data.mount').unlink(missing_ok=True)
    runtime = root / 'usr/lib/sv08'
    for source in (REPO / 'runtime').glob('*.py'):
        shutil.copyfile(source, runtime / source.name)
    for source, destination in [
        (REPO / 'configs/host-os/rauc-service-policy.json', runtime / 'rauc-service-policy.json'),
        (REPO / 'configs/host-os/sv08-rauc-policy.conf', root / 'etc/dbus-1/system.d/zz-sv08-rauc.conf'),
        (REPO / 'configs/host-os/sv08-rauc-service.conf', root / 'etc/systemd/system/rauc.service.d/sv08.conf'),
        (GUEST, runtime / 'qemu-rauc-resolution.py'),
    ]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    (runtime / 'qemu-rauc-resolution.py').chmod(0o755)
    write(root / 'usr/lib/systemd/system/qemu-rauc-resolution.service', '''[Unit]
Description=Disposable RAUC interrupted-job resolution test
After=local-fs.target dbus.service

[Service]
Type=oneshot
TimeoutStartSec=5min
ExecStart=/usr/bin/python3 /usr/lib/sv08/qemu-rauc-resolution.py
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=multi-user.target
''')
    write(root / 'etc/rauc/system.conf', '''[system]
compatible=sv08-rauc-resolution-fixture
bootloader=custom
bundle-formats=verity
activate-installed=false
data-directory=/data/rauc-state

[handlers]
bootloader-custom-backend=/data/fixture/chooser.py

[keyring]
path=/etc/rauc/release-keyring.pem

[slot.rootfs.0]
device=/data/fixture/slots/rootfs-A.img
type=raw
bootname=A

[slot.boot.0]
device=/data/fixture/slots/boot-A.img
type=raw
parent=rootfs.0

[slot.rootfs.1]
device=/data/fixture/slots/rootfs-B.img
type=raw
bootname=B

[slot.boot.1]
device=/data/fixture/slots/boot-B.img
type=raw
parent=rootfs.1
''')
    # The service identity records this reviewed path even though this fixture
    # uses RAUC's custom test boot chooser instead of a U-Boot environment.
    write(root / 'etc/fw_env.config', '# disposable RAUC-resolution fixture\n')
    fixture = seed / 'fixture'; slots = fixture / 'slots'; slots.mkdir(parents=True)
    source = {}
    for slot in ('A', 'B'):
        for name in ('rootfs', 'boot'):
            path = slots / (name + '-' + slot + '.img')
            value = (('fixture-' + name + '-' + slot + '\n').encode() * 16384)[:256 * 1024]
            path.write_bytes(value)
            if slot == 'A': source[name] = hashlib.sha256(value).hexdigest()
    write(fixture / 'chooser.py', '''#!/usr/bin/python3
import json, sys
from pathlib import Path
path = Path('/data/fixture/chooser.json')
state = json.loads(path.read_text())
args = sys.argv[1:]
if args == ['get-primary']: print(state['primary'])
elif args == ['get-current']: print('A')
elif len(args) == 2 and args[0] == 'get-state': print(state[args[1]])
elif len(args) == 2 and args[0] == 'set-primary': state['primary'] = args[1]
elif len(args) == 3 and args[0] == 'set-state': state[args[1]] = args[2]
else: raise SystemExit(1)
path.write_text(json.dumps(state))
''', 0o755)
    write(fixture / 'chooser.json', json.dumps({'primary': 'A', 'A': 'good', 'B': 'bad'}))
    output, certificate, images = bundle(work)
    shutil.copyfile(output, fixture / 'signed.raucb')
    shutil.copyfile(certificate, root / 'etc/rauc/release-keyring.pem')
    write(fixture / 'expected.json', json.dumps({'source': source, 'installed': images}, indent=2) + '\n')
    run(['systemctl', '--root', root, 'enable', 'qemu-rauc-resolution.service'],
        stdout=subprocess.DEVNULL)
    (root / 'etc/machine-id').write_text('')
    for path in (root / 'etc/ssh').glob('ssh_host_*'):
        path.unlink()
    run(['truncate', '-s', '2G', work / 'root.ext4'])
    run(['mkfs.ext4', '-q', '-F', '-d', root, work / 'root.ext4'])
    data = work / 'data.img'
    run(['truncate', '-s', '512M', data])
    # This UUID is embedded in the selected initramfs and is deliberately a
    # fixture-specific copy of its reviewed persistent-data contract.
    run(['sgdisk', '--clear', '--new=1:2048:1048542', '--typecode=1:8300',
         '--partition-guid=1:4773f966-0678-4cf5-bb83-8ee6fb11d8eb', data])
    run(['mkfs.ext4', '-q', '-F', '-d', seed, '-E', 'offset=1048576', data, '130812'])
    return dict(bundle_sha256=digest(output), root_sha256=digest(work / 'root.ext4'),
                data_sha256=digest(data), source_root_sha256=digest(BASE / 'usr/bin/rauc'))


def execute(work):
    report = prepare(work)
    command = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a53', '-smp', '2', '-m', '1024',
               '-nographic', '-no-reboot', '-nic', 'none', '-kernel', KERNEL, '-initrd', INITRD,
               '-append', 'root=/dev/vda ro rootwait console=ttyAMA0 rauc.slot=A sv08.test=rauc-resolution',
               '-drive', 'file=' + str(work / 'data.img') + ',format=raw,if=none,id=data',
               '-device', 'virtio-blk-device,drive=data,serial=SV08-QEMU-RESOLUTION-DATA',
               # qemu's platform virtio transport enumerates the last device
               # first on this ARM64 ``virt`` machine.  Keep the root device
               # last so the guest's explicitly checked /dev/vda is root.
               '-drive', 'file=' + str(work / 'root.ext4') + ',format=raw,if=none,id=root',
               '-device', 'virtio-blk-device,drive=root,serial=SV08-QEMU-DISPOSABLE']
    log = work / 'boot.log'
    with log.open('w') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=420, check=True)
    markers = [line.split('SV08_QEMU_RAUC_RESOLUTION_RESULT ', 1)[1]
               for line in log.read_text(errors='replace').splitlines()
               if 'SV08_QEMU_RAUC_RESOLUTION_RESULT ' in line]
    if len(markers) != 1:
        raise RuntimeError('No single success marker in ' + str(log))
    result = json.loads(markers[0])
    if result.get('passed') is not True:
        raise RuntimeError('Fixture did not report success')
    report.update(result, boot_log_sha256=digest(log))
    (work / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ASSETS / 'build/host-qemu-rauc-resolution-v1')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    for path, description in [(BASE / 'usr/bin/rauc', 'selected ARM64 root'), (NATIVE_RAUC, 'native RAUC bundle tool'),
                              (KERNEL, 'ARM64 kernel'), (INITRD, 'ARM64 initramfs'), (GUEST, 'guest fixture')]:
        require(path, description)
    if digest(BASE / 'usr/bin/rauc') != '51d7c057c7fb00917287b5324303c747e71c5406f4c1363a678578ac7a3b12e3':
        raise ValueError('Selected root does not contain the pinned RAUC executable')
    work = args.work.resolve()
    if not work.is_relative_to(ASSETS / 'build') or work == ASSETS / 'build':
        raise ValueError('Fixture output must be a fresh directory below build/')
    print(json.dumps({'execute': args.execute, 'work': str(work), 'base': str(BASE),
                      'rauc': '1.15.2-0sv08.1', 'network': 'disabled', 'hardware': False}, indent=2))
    if not args.execute:
        return
    if os.geteuid() != 0:
        raise ValueError('Use root for the disposable rootfs copy and QEMU fixture')
    if work.exists():
        raise ValueError('Use a fresh fixture work directory')
    work.mkdir(mode=0o700)
    print(json.dumps(execute(work), indent=2))


if __name__ == '__main__':
    main()
