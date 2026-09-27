#!/usr/bin/env python3
"""Reboot an existing synthetic QEMU case with its consumed claim unchanged.

Run as root inside private network and mount namespaces. The only guest drive
is the case's disposable regular file. No printer or real block device is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import subprocess
import sys
import threading
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.build_sd_network_image import boot_script  # noqa: E402
from tests.host_qemu_sd_network_emmc_write import (H616_TARGET_BYTES, SERIAL,
                                                     digest, isolated, secure_path)  # noqa: E402
from tests.sv08_emmc_job import ClaimHTTPServer, ClaimState  # noqa: E402


def safe_dir(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    if any(part.is_symlink() for part in (path, *path.parents)) or not path.is_dir():
        raise ValueError('Existing non-symlink directory required')
    return path


def run(case: Path, work: Path, packages: Path, sd_dtb: Path) -> dict:
    isolated()
    case, packages, sd_dtb = safe_dir(case), safe_dir(packages), secure_path(sd_dtb)
    work = Path(os.path.abspath(work))
    if (work.exists() or work.is_symlink() or not case.is_dir() or
            not packages.is_dir() or not sd_dtb.is_file()):
        raise ValueError('Existing case and fresh second-boot work required')
    receipt = json.loads((case / 'result.json').read_bytes())
    claim = (receipt.get('fault_evidence') or receipt).get('claim', {})
    if (receipt.get('status') not in ('qemu-only-pass', 'qemu-injected-fault-pass',
                                      'qemu-abrupt-interruption-pass') or
            claim.get('status') != 'consumed-before-write'):
        raise ValueError('Case has no admitted consumed claim')
    nfs_root = safe_dir(case / 'nfs-root')
    if {item.name for item in nfs_root.iterdir()} != {'image.bin'}:
        raise ValueError('NFS source contains unexpected content')
    sd_boot = case / 'composed-sd/boot'
    for name in ('Image', 'initrd.img'):
        secure_path(sd_boot / name)
    target = secure_path(case / 'target.img')
    if not stat.S_ISREG(target.lstat().st_mode) or target.stat().st_size != H616_TARGET_BYTES:
        raise ValueError('Only a disposable regular target of exact size is accepted')
    work.mkdir(mode=0o700)
    extracted = work / 'initramfs'
    subprocess.run(['unmkinitramfs', str(sd_boot / 'initrd.img'), str(extracted)],
                   check=True, capture_output=True, timeout=60)
    descriptor = json.loads((extracted / 'job.json').read_bytes())
    state = ClaimState.reopen(case / 'claim-state', descriptor)
    if not state.claimed.is_file() or state.armed.exists():
        raise ValueError('Claim is not durably consumed')
    claim_before = digest(state.claimed)
    target_fd = os.open(target, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
    before = os.pread(target_fd, 1024 * 1024, 0)
    subprocess.run(['mount', '--make-rprivate', '/'], check=True)
    subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', '/run'], check=True)
    subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True)
    prefix = packages / 'usr/lib/x86_64-linux-gnu'
    env = dict(os.environ, LD_LIBRARY_PATH=':'.join((str(packages / 'usr/lib/ganesha'),
                                                      str(prefix), str(prefix / 'ganesha'))))
    Path('/run/ganesha').mkdir()
    (work / 'idmap.conf').write_text('[General]\nDomain = localdomain\n')
    (work / 'ganesha.conf').write_text(
        f'NFSv4 {{ IdmapConf = "{work / "idmap.conf"}"; UseGetpwnam = true; Graceless = true; RecoveryRoot = "/run/ganesha"; }}\n'
        f'NFS_CORE_PARAM {{ Protocols = 3,4; mount_path_pseudo = true; Plugins_Dir = "{prefix / "ganesha"}"; }}\n'
        f'EXPORT {{ Export_Id = 1; Path = "{nfs_root}"; Pseudo = "/srv/sv08-sd-nfs"; '
        'Access_Type = RO; Squash = Root_Squash; SecType = sys; Protocols = 3,4; '
        'Transports = TCP; FSAL { Name = VFS; } }\n')
    claim_server = ClaimHTTPServer(('0.0.0.0', 0), state)
    claim_thread = threading.Thread(target=claim_server.serve_forever, daemon=True)
    children = []
    try:
        children.append(subprocess.Popen([str(packages / 'sbin/rpcbind'), '-f', '-s'],
                                         env=env, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL))
        children.append(subprocess.Popen([str(packages / 'usr/bin/ganesha.nfsd'), '-F',
                                          '-f', str(work / 'ganesha.conf'), '-L',
                                          str(work / 'ganesha.log'), '-p', '/run/ganesha.pid'],
                                         env=env, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL))
        for _ in range(100):
            if any(child.poll() is not None for child in children):
                raise RuntimeError('NFS service exited')
            try:
                with socket.create_connection(('127.0.0.1', 2049), timeout=.2):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise TimeoutError('NFS service did not become ready')
        claim_thread.start()
        hashes = {name: digest(path) for name, path in {
            'Image': sd_boot / 'Image', 'initrd.img': sd_boot / 'initrd.img',
            'sv08.dtb': sd_dtb}.items()}
        command_text = boot_script('10.0.2.2', '/srv/sv08-sd-nfs', hashes,
                                   claim_port=claim_server.server_port)
        (work / 'boot.cmd').write_text(command_text)
        args = re.search(r'^setenv bootargs "([^"]+)"$', command_text, re.M).group(1)
        command = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a53',
                   '-smp', '2', '-m', '2048', '-rtc',
                   'base=' + time.strftime('%Y-%m-%dT%H:%M:%S',
                                           time.gmtime(descriptor['issued_unix'] + 600)),
                   '-kernel', str(sd_boot / 'Image'),
                   '-initrd', str(sd_boot / 'initrd.img'), '-append', args,
                   '-display', 'none', '-serial', 'null', '-no-reboot',
                   '-device', 'qemu-xhci,id=xhci', '-device', 'usb-net,netdev=n0',
                   '-netdev', 'user,id=n0', '-drive',
                   f'file=/proc/self/fd/{target_fd},if=none,id=target,format=raw,cache=none,discard=unmap,detect-zeroes=unmap',
                   '-device', f'usb-storage,drive=target,serial={SERIAL}',
                   '-chardev', f'file,id=serial,path={work / "serial.log"}',
                   '-device', 'pci-serial,chardev=serial']
        with (work / 'qemu.log').open('w') as log:
            guest = subprocess.Popen(command, pass_fds=(target_fd,), stdout=log,
                                     stderr=subprocess.STDOUT)
            try:
                guest.wait(timeout=300)
            except subprocess.TimeoutExpired:
                guest.kill()
                guest.wait(timeout=10)
                raise TimeoutError('Second boot did not refuse within five minutes')
        serial = (work / 'serial.log').read_text(errors='replace')
        if (guest.returncode != 0 or
                'SV08_H616_COMMISSIONING_REFUSED_OR_UNCERTAIN_CLAIM' not in serial or
                'SV08_H616_COMMISSIONING_SOURCE_HASH_START' in serial or
                'SV08_H616_COMMISSIONING_TARGET_OPEN_START' in serial or
                'SV08_H616_COMMISSIONING_PASS' in serial or
                os.pread(target_fd, 1024 * 1024, 0) != before or
                digest(state.claimed) != claim_before):
            raise RuntimeError('Consumed job was not terminal on second boot')
        result = {'status': 'qemu-second-boot-refused',
                  'case_result_sha256': digest(case / 'result.json'),
                  'serial_sha256': digest(work / 'serial.log'),
                  'claim_unchanged': True, 'target_prefix_unchanged': True,
                  'source_hash_started': False, 'target_open_attempted': False}
        (work / 'result.json').write_text(json.dumps(result, sort_keys=True) + '\n')
        return result
    finally:
        if claim_thread.ident is not None:
            claim_server.shutdown()
            claim_thread.join(timeout=5)
        claim_server.server_close()
        for child in reversed(children):
            if child.poll() is None:
                child.send_signal(signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        os.close(target_fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--package-root', type=Path, required=True)
    parser.add_argument('--sd-dtb', type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(run(options.case, options.work, options.package_root, options.sd_dtb),
                     sort_keys=True))
