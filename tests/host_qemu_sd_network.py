#!/usr/bin/env python3
"""Disposable QEMU test of the exact SD kernel/initramfs and minimal NFS root.

Run inside `sudo unshare -n -m` with a locally extracted nfs-ganesha package
tree. All service sockets and mounts stay in that namespace; no host export is
installed. This does not emulate H616 SPL, U-Boot, SD priority or Ethernet.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--package-root', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    work, packages = a.work.resolve(), a.package_root.resolve()
    receipt = json.loads((work / 'composition.json').read_text())
    boot = work / 'boot'
    for name, record in receipt['payloads'].items():
        if sha(boot / name) != record['sha256']:
            raise ValueError(f'Boot payload changed: {name}')
    nfs_root = work / 'nfs-root'
    if sorted(str(path.relative_to(nfs_root)) for path in nfs_root.rglob('*')) != [
            'data', 'dev', 'proc', 'run', 'sd-network-init', 'sys', 'tmp']:
        raise ValueError('NFS export has unexpected contents')
    if sha(nfs_root / 'sd-network-init') != receipt['nfs_root_init_sha256']:
        raise ValueError('NFS init changed')
    manifest = work / 'nfs-root-manifest.json'
    if sha(manifest) != receipt['nfs_root_manifest_sha256']:
        raise ValueError('NFS export manifest changed')
    if json.loads(manifest.read_text())['files']['sd-network-init']['sha256'] != sha(nfs_root / 'sd-network-init'):
        raise ValueError('NFS export file differs from manifest')
    if receipt['server_address'] != '10.0.2.2' or receipt['export_path'] != '/srv/sv08-sd-nfs':
        raise ValueError('QEMU fixture expects its isolated NFS address/path')
    cmd = (work / 'boot.cmd').read_text()
    match = re.search(r'^setenv bootargs "([^"]+)"$', cmd, re.M)
    if not match or 'root=/dev/nfs ro ip=dhcp' not in match[1]:
        raise ValueError('Unexpected SD kernel command line')
    kernel_args = match[1]
    if os.geteuid() != 0:
        raise ValueError('Run in a disposable root-owned network and mount namespace')
    for name in ('net', 'mnt'):
        if os.readlink(f'/proc/self/ns/{name}') == os.readlink(f'/proc/1/ns/{name}'):
            raise ValueError(f'Disposable {name} namespace required')
    print(json.dumps({'execute': a.execute, 'kernel_sha256': sha(boot / 'Image'),
                      'initrd_sha256': sha(boot / 'initrd.img')}), flush=True)
    if not a.execute:
        return
    subprocess.run(['mount', '--make-rprivate', '/'], check=True)
    subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', '/run'], check=True)
    subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True)
    prefix = packages / 'usr/lib/x86_64-linux-gnu'
    env = dict(os.environ, LD_LIBRARY_PATH=':'.join((str(packages / 'usr/lib/ganesha'),
                                                      str(prefix), str(prefix / 'ganesha'))))
    plugin = prefix / 'ganesha'
    idmap = work / 'idmapd-qemu.conf'
    idmap.write_text('[General]\nDomain = localdomain\n')
    config = work / 'ganesha-qemu.conf'
    Path('/run/ganesha').mkdir()
    config.write_text(f'''NFSv4 {{ IdmapConf = "{idmap}"; UseGetpwnam = true; Graceless = true; RecoveryRoot = "/run/ganesha"; }}
NFS_CORE_PARAM {{ Protocols = 3,4; mount_path_pseudo = true; Plugins_Dir = "{plugin}"; }}
EXPORT {{ Export_Id = 1; Path = "{nfs_root}"; Pseudo = "/srv/sv08-sd-nfs"; Access_Type = RO; Squash = Root_Squash; SecType = sys; Protocols = 3,4; Transports = TCP; FSAL {{ Name = VFS; }} }}
''')
    rpcbind = packages / 'sbin/rpcbind'
    ganesha = packages / 'usr/bin/ganesha.nfsd'
    processes = []
    try:
        processes.append(subprocess.Popen([str(rpcbind), '-f', '-s'], env=env,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        processes.append(subprocess.Popen([str(ganesha), '-F', '-f', str(config),
                                           '-L', str(work / 'ganesha-qemu.log'),
                                           '-p', '/run/ganesha.pid'], env=env,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        ready = False
        for _ in range(40):
            if any(process.poll() is not None for process in processes):
                raise RuntimeError('Isolated NFS service exited before ready')
            try:
                with socket.create_connection(('127.0.0.1', 2049), timeout=0.2):
                    ready = True
                    break
            except OSError:
                time.sleep(0.2)
        if not ready:
            raise RuntimeError('Isolated NFS service did not start')
        qemu = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a53',
                '-smp', '2', '-m', '1024', '-kernel', str(boot / 'Image'),
                '-initrd', str(boot / 'initrd.img'), '-append', kernel_args,
                '-display', 'none', '-serial', 'null', '-no-reboot',
                '-device', 'qemu-xhci,id=xhci', '-device', 'usb-net,netdev=n0',
                '-netdev', 'user,id=n0']

        def guest(name, marker, timeout):
            serial_path = work / f'qemu-{name}-serial.log'
            command = qemu + ['-chardev', f'file,id=serial,path={serial_path}',
                              '-device', 'pci-serial,chardev=serial']
            began = time.monotonic()
            with (work / f'qemu-{name}-process.log').open('w') as log:
                proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                try:
                    while time.monotonic() - began < timeout:
                        serial = serial_path.read_text(errors='replace') if serial_path.exists() else ''
                        if (marker in serial or
                                'Halting automatically due to panic= boot argument' in serial or
                                proc.poll() is not None):
                            break
                        time.sleep(0.5)
                    else:
                        raise TimeoutError(f'QEMU {name} exceeded {timeout}s')
                finally:
                    if proc.poll() is None:
                        proc.terminate()
                    try:
                        proc.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)
            return serial_path.read_text(errors='replace'), round(time.monotonic() - began, 2)

        serial, duration = guest('online', 'SV08_SD_NFS_', 120)
        result = {'elapsed_seconds': duration,
                  'dhcp': 'DHCP' in serial or 'IP-Config:' in serial,
                  'nfs_root_ro_volatile_data': 'SV08_SD_NFS_PASS' in serial,
                  'server_reachable': ready}
        if not result['nfs_root_ro_volatile_data'] or not result['dhcp']:
            raise RuntimeError('Exact kernel/initramfs NFS-root acceptance failed')
        processes[1].send_signal(signal.SIGTERM)
        processes[1].wait(timeout=8)
        missing, missing_duration = guest('server-missing',
                                         'Halting automatically due to panic= boot argument', 90)
        result['missing_server'] = {
            'elapsed_seconds': missing_duration,
            'dhcp': 'DHCP' in missing or 'IP-Config:' in missing,
            'halted_without_root': 'Halting automatically due to panic= boot argument' in missing,
            'root_probe_did_not_run': 'SV08_SD_NFS_' not in missing,
        }
        (work / 'qemu-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
        if not all(result['missing_server'][key] for key in
                   ('dhcp', 'halted_without_root', 'root_probe_did_not_run')):
            raise RuntimeError('Missing-server failure was not bounded and inert')
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
        for process in reversed(processes):
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        if any(process.poll() is None for process in processes):
            raise RuntimeError('NFS process cleanup failed')


if __name__ == '__main__':
    main()
