#!/usr/bin/env python3
"""Boot the reviewed v5 root-A with its unchanged initramfs in QEMU.

The 32 GB regular-file target is opened through QEMU's temporary snapshot
overlay. This exercises normal Debian/systemd startup but not H616 firmware,
printer electronics, or the physical boot selector.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from tests.host_qemu_v5_normal_slot import (IMAGE_BYTES, TARGET_BYTES,
                                             V5_IMAGE_SHA256, KERNEL_SHA256,
                                             INITRD_SHA256, digest)


def execute(target, kernel, initrd, work):
    target, kernel, initrd = (Path(item).resolve(strict=True)
                              for item in (target, kernel, initrd))
    work = Path(work).absolute()
    if (work.exists() or not work.is_relative_to(REPO / 'local') or
            not stat.S_ISREG(target.stat().st_mode) or
            target.stat().st_size != TARGET_BYTES or
            digest(target, IMAGE_BYTES) != V5_IMAGE_SHA256 or
            digest(kernel, kernel.stat().st_size) != KERNEL_SHA256 or
            digest(initrd, initrd.stat().st_size) != INITRD_SHA256):
        raise ValueError('Fresh local work and exact reviewed v5 inputs required')
    work.mkdir(mode=0o700)
    serial = work / 'serial.log'
    command = [
        'qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a53',
        '-smp', '2', '-m', '1024', '-kernel', str(kernel), '-initrd', str(initrd),
        '-append', ('console=ttyS0,115200 root=/dev/sda2 rootfstype=ext4 '
                    'ro rootwait rauc.slot=A systemd.unit=multi-user.target panic=0'),
        '-display', 'none', '-serial', 'null', '-no-reboot',
        '-netdev', 'user,id=n0,restrict=on', '-device', 'qemu-xhci,id=xhci',
        '-device', 'usb-net,netdev=n0',
        '-drive', f'file={target},if=none,id=target,format=raw,snapshot=on',
        '-device', 'usb-storage,drive=target',
        '-chardev', f'file,id=serial,path={serial}',
        '-device', 'pci-serial,chardev=serial',
    ]
    env = dict(os.environ, TMPDIR=str(work))
    ansi = re.compile(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07|[M])')
    with (work / 'qemu.log').open('w') as qemu_log:
        guest = subprocess.Popen(command, stdout=qemu_log, stderr=subprocess.STDOUT,
                                 env=env)
        try:
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                output = ansi.sub('', serial.read_text(errors='replace')) if serial.exists() else ''
                if all(marker in output for marker in
                       ('Finished sv08-prepare.service',
                        'Reached target multi-user.target', 'sv08 login: ')):
                    break
                if guest.poll() is not None:
                    raise RuntimeError('Guest stopped before normal login')
                time.sleep(1)
            else:
                raise TimeoutError('Guest did not reach normal login within 300 seconds')
        finally:
            guest.terminate()
            try:
                guest.wait(timeout=15)
            except subprocess.TimeoutExpired:
                guest.kill()
                guest.wait()
    output = ansi.sub('', serial.read_text(errors='replace'))
    if (not ('EXT4-fs (sda2): mounted filesystem' in output and
             'EXT4-fs (sda6): mounted filesystem' in output) or
            'Failed to start sv08-prepare.service' in output or
            'reboot: Restarting system' in output or
            digest(target, IMAGE_BYTES) != V5_IMAGE_SHA256):
        raise RuntimeError('Normal boot failed or changed the snapshot source')
    result = {'status': 'PASS', 'target_sha256': V5_IMAGE_SHA256,
              'kernel_sha256': KERNEL_SHA256, 'initrd_sha256': INITRD_SHA256,
              'serial_sha256': hashlib.sha256(serial.read_bytes()).hexdigest(),
              'normal_multi_user_reached': True, 'prepare_succeeded': True,
              'login_prompt_seen': True, 'temporary_snapshot': True,
              'source_unchanged': True, 'guest_memory_mb': 1024,
              'physical_h616_boot_tested': False,
              'printer_services_tested': False}
    (work / 'result.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('target', 'kernel', 'initrd', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({'execute': False, 'work': str(args.work.absolute())}))
        return
    execute(args.target, args.kernel, args.initrd, args.work)


if __name__ == '__main__':
    main()
