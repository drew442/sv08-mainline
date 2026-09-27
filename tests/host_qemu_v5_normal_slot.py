#!/usr/bin/env python3
"""Read-only QEMU probe of the reviewed v5 root-A after a reimage trial.

It boots an external test kernel/initramfs with the target's root-A as `/`,
then verifies a pinned release file from that root. This proves the root-A
filesystem can start a shell in QEMU; it is not a physical H616 boot or a
full systemd/printer-service acceptance test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys

import pexpect

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.build_h616_reimage_candidate import V5_IMAGE_SHA256

IMAGE_BYTES = 7_818_182_656
TARGET_BYTES = 31_272_730_624
RELEASE_SHA256 = 'aa3724f0aaea3f9a59e4fa4ea15014a2f3f4860b2cae5bf1c70f0ffc4b5af519'
KERNEL_SHA256 = '5bc7c62df2b521610d0dea0a82b38aceb54af7d340a44b02a27428d6ea28dc34'
INITRD_SHA256 = '8be88ee081ad61c64de216425b031b8988447d6fb009022edeffaf53f115d09e'


def digest(path, limit):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        remaining = limit
        while remaining:
            block = stream.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError('Short target image')
            h.update(block)
            remaining -= len(block)
    return h.hexdigest()


def compose_readonly_probe_initrd(source, work):
    """Keep the reviewed drivers, bypass only the writable /data init hook."""
    tree = work / 'initrd-tree'
    subprocess.run(['unmkinitramfs', str(source), str(tree)], check=True,
                   capture_output=True, timeout=60)
    hook = tree / 'scripts/local-bottom/sv08-data'
    order = tree / 'scripts/local-bottom/ORDER'
    if (not hook.is_file() or
            '/scripts/local-bottom/sv08-data' not in order.read_text()):
        raise ValueError('Reviewed persistent hook not found in base initrd')
    hook.unlink()
    order.write_text('# Read-only root-A probe: never initialize or mount /data.\n')
    archive = work / 'probe.cpio'
    names = ['.', *(str(path.relative_to(tree)) for path in sorted(tree.rglob('*')))]
    with archive.open('wb') as out:
        subprocess.run(['cpio', '--null', '--quiet', '--reproducible',
                        '--owner=0:0', '-o', '-H', 'newc'], cwd=tree,
                       input=('\0'.join(names) + '\0').encode(), stdout=out,
                       check=True, timeout=60)
    result = work / 'probe-initrd.img'
    with result.open('wb') as out:
        subprocess.run(['gzip', '-n', '-9', '-c', archive], stdout=out,
                       check=True, timeout=120)
    return result


def execute(target, kernel, initrd, work):
    target = target.resolve(strict=True)
    kernel = kernel.resolve(strict=True)
    initrd = initrd.resolve(strict=True)
    work = work.absolute()
    if (work.exists() or not work.is_relative_to(REPO / 'local') or
            not stat.S_ISREG(target.stat().st_mode) or
            target.stat().st_size != TARGET_BYTES or
            digest(target, IMAGE_BYTES) != V5_IMAGE_SHA256 or
            digest(kernel, kernel.stat().st_size) != KERNEL_SHA256 or
            digest(initrd, initrd.stat().st_size) != INITRD_SHA256):
        raise ValueError('Fresh local work and exact reviewed v5 target required')
    work.mkdir(mode=0o700)
    probe_initrd = compose_readonly_probe_initrd(initrd, work)
    command = ['-machine', 'virt', '-cpu', 'cortex-a53', '-smp', '2',
               '-m', '1024', '-kernel', str(kernel), '-initrd', str(probe_initrd),
               '-append', ('console=ttyS0,115200 root=/dev/sda2 '
                           'rootfstype=ext4 ro rootwait init=/bin/sh panic=0'),
               '-display', 'none', '-serial', 'null', '-no-reboot', '-nic', 'none',
               '-device', 'qemu-xhci,id=xhci',
               '-drive', f'file={target},if=none,id=target,format=raw,readonly=on',
               '-device', 'usb-storage,drive=target',
               '-chardev', 'stdio,id=serial,signal=off',
               '-device', 'pci-serial,chardev=serial']
    log = work / 'serial.log'
    child = pexpect.spawn('qemu-system-aarch64', command, encoding='utf-8',
                          timeout=180, echo=False)
    try:
        with log.open('w') as output:
            child.logfile_read = output
            child.expect_exact('# ', timeout=180)
            child.sendline('sha256sum /usr/lib/sv08/release.json')
            child.expect_exact(RELEASE_SHA256 + '  /usr/lib/sv08/release.json',
                               timeout=30)
            child.expect_exact('# ', timeout=30)
            child.sendline("awk '$2==\"/\" {print \"SV08_ROOT=\" $1 \" \" $3 \" \" $4}' /proc/mounts")
            child.expect_exact('SV08_ROOT=/dev/sda2 ext4 ro', timeout=30)
            child.expect_exact('# ', timeout=30)
            child.sendline("printf 'SV08_%s\\n' QEMU_V5_ROOT_A_READONLY_PASS")
            child.expect_exact('SV08_QEMU_V5_ROOT_A_READONLY_PASS', timeout=30)
    finally:
        child.terminate(force=True)
        child.close(force=True)
    result = {'status': 'PASS', 'target_sha256': V5_IMAGE_SHA256,
              'kernel_sha256': KERNEL_SHA256, 'initrd_sha256': INITRD_SHA256,
              'readonly_probe_initrd_sha256': digest(probe_initrd, probe_initrd.stat().st_size),
              'persistent_hook_skipped_for_readonly_probe': True,
              'root_a_release_sha256': RELEASE_SHA256,
              'root_a_mounted_read_only': True,
              'guest_memory_mb': 1024, 'physical_h616_boot_tested': False,
              'full_host_services_tested': False}
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
