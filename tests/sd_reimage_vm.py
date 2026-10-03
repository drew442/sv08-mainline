#!/usr/bin/env python3
"""Bounded installed ARM64 attended fixture, coordinator execution only.

Separate disposable source/target virtio disks substitute eMMC hardware. The
source is mounted read-only; target admission is explicitly regular-file-only.
Actual mmc controller/CID and physical compatibility remain untested.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from recovery_vm import QMP
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from build_sd_recovery_host import safe, sha, run, put, PARTUUID


FIXTURE_DROPIN = '/run/systemd/system/sv08-recovery-display.service.d/zz-h12-fixture.conf'


def ssh_command(port, key, command, known, timeout, input=None):
    """Driver-local timeout; other SD harness defaults remain unchanged."""
    args = ['ssh', '-p', str(port), '-i', str(key), '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=5', '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=accept-new', '-o', 'UserKnownHostsFile='+str(known),
            'recovery@127.0.0.1', 'set -e; '+command]
    result = subprocess.run(args, input=input, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise AssertionError('Installed guest command failed: '+result.stderr)
    return result.stdout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'work', 'test-key'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--port', type=int, default=22284)
    p.add_argument('--seconds', type=int, default=240)
    a = p.parse_args()
    build, work, key = safe(a.build), safe(a.work), safe(a.test_key, True)
    if work.exists() or build in work.parents or work in build.parents: raise ValueError('Fresh separate work required')
    if not 1024 <= a.port <= 65535 or not 30 <= a.seconds <= 600: raise ValueError('Bounded port/deadline required')
    record = json.loads((build/'composition.json').read_text())
    if not record.get('test_only_authorized_key') or not record.get('sd_reimage_inputs'):
        raise ValueError('New explicitly test-only composition required')
    for path, expected in [('recovery.ext4', record['root_sha256']),
                           ('boot/initrd.img', record['payloads']['initrd.img']['sha256']),
                           ('vm-vmlinuz', record['vm_kernel_sha256'])]:
        if sha(build/path) != expected: raise ValueError('Changed composed artifact')
    if not a.execute:
        print(json.dumps(dict(execute=False, memory_mib=768, extra_disks_mib=16, fixture_only=True))); return
    work.mkdir(parents=True, mode=0o700)
    disk = work/'sd.img'
    with disk.open('xb') as stream: stream.truncate(704*1024**2)
    run('sgdisk', '--clear', '--new=1:32768:294911', '--typecode=1:0700',
        '--new=2:294912:1343487', '--typecode=2:8300', '--partition-guid=2:'+PARTUUID, disk)
    with disk.open('r+b') as stream:
        stream.seek(144*1024**2)
        with (build/'recovery.ext4').open('rb') as source: shutil.copyfileobj(source, stream)
    data = b'installed attended SD fixture\n'*4096
    for name, filename, payload in [('source', 'image', data), ('target', 'target', b'x'*(len(data)+512))]:
        tree = work/(name+'-tree'); tree.mkdir(); (tree/filename).write_bytes(payload)
        with (work/(name+'.ext4')).open('xb') as stream: stream.truncate(8*1024**2)
        run('mkfs.ext4', '-q', '-F', '-d', tree, work/(name+'.ext4'))
    before = {name:sha(work/name) for name in ('sd.img','source.ext4')}
    qpath = work/'qmp.sock'; known = work/'known'
    cmd = ['qemu-system-aarch64','-machine','virt','-cpu','cortex-a53','-accel','tcg,thread=multi',
           '-smp','2','-m','768','-kernel',str(build/'vm-vmlinuz'),'-initrd',str(build/'boot/initrd.img'),
           '-append',f'console=ttyAMA0 root=PARTUUID={PARTUUID} ro sv08.envelope={record["manifest_sha256"]}',
           '-device','virtio-gpu-pci','-device','qemu-xhci','-device','usb-kbd','-device','usb-tablet',
           '-netdev',f'user,id=net,hostfwd=tcp:127.0.0.1:{a.port}-:22',
           '-device','virtio-net-pci,netdev=net,romfile=', '-display','none', '-serial','stdio',
           '-qmp',f'unix:{qpath},server=on,wait=off','-no-reboot']
    for index, name in enumerate(('sd.img','source.ext4','target.ext4')):
        cmd += ['-drive', f'if=none,id=d{index},format=raw,file={work/name}'+(',readonly=on' if index == 1 else ''),
                '-device', f'virtio-blk-pci,drive=d{index}']
    put(work/'command.json', json.dumps(cmd, indent=2)+'\n')
    started = time.monotonic()
    with (work/'console.log').open('wb') as log:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        q = None
        try:
            def guest(command, timeout=90, input=None):
                remaining = a.seconds-(time.monotonic()-started)
                if remaining <= 0: raise TimeoutError('Installed VM deadline exceeded')
                return ssh_command(a.port, key, command, known, min(timeout, remaining), input)
            while time.monotonic()-started < a.seconds:
                if proc.poll() is not None: raise AssertionError('Guest exited')
                try:
                    guest('systemctl is-active sv08-recovery-display.service', timeout=20)
                    break
                except (AssertionError, subprocess.TimeoutExpired): time.sleep(1)
            else: raise AssertionError('Guest startup deadline')
            wiring = guest("systemctl cat sv08-recovery-display.service; pgrep -af '[s]v08_sd_reimage_ui.py'")
            assert '/usr/lib/sv08/sv08_sd_reimage_ui.py' in wiring
            installed = guest('sha256sum /usr/lib/sv08/sv08_sd_reimage*.py /etc/systemd/system/sv08-recovery-display.service.d/reimage.conf')
            for expected in record['sd_reimage_inputs'].values(): assert expected in installed
            guest('sudo -n mkdir -p /run/h12/source /run/h12/target; sudo -n mount -o ro,noload /dev/vdb /run/h12/source; sudo -n mount /dev/vdc /run/h12/target')
            driver = Path(__file__).with_name('sd_reimage_gtk.py').read_text()
            # Fixed stdin transport of public fixture source, no upload framework.
            guest('cat > /run/sd-owner/h12-gtk.py', timeout=20, input=driver)
            override = ('[Service]\nExecStart=\nExecStart=/usr/bin/xinit /usr/bin/python3 /run/sd-owner/h12-gtk.py '
                        '--runtime /usr/lib/sv08 --work /run/h12/results --source /run/h12/source/image '
                        '--target /run/h12/target/target -- :0 vt1 -nolisten tcp\n')
            # xinit passes only the client-side arguments (before --) to Python.
            guest("sudo -n mkdir -p /run/systemd/system/sv08-recovery-display.service.d; "
                  "printf '%s' '"+override+"' | sudo -n tee "+FIXTURE_DROPIN+" >/dev/null; "
                  'sudo -n systemctl daemon-reload; sudo -n systemctl restart sv08-recovery-display.service')
            fixture_exec = guest('systemctl show sv08-recovery-display.service --property=ExecStart --value')
            assert '/run/sd-owner/h12-gtk.py' in fixture_exec, 'Fixture ExecStart not active: '+fixture_exec
            while time.monotonic()-started < a.seconds:
                try:
                    result = json.loads(guest('sudo -n cat /run/h12/results/run.json')); break
                except (AssertionError, json.JSONDecodeError): time.sleep(1)
            else: raise AssertionError('Installed GTK driver deadline')
            assert len(result['results']) == 10
            assert result['source_sha256'] == hashlib.sha256(data).hexdigest()
            assert result['target_sha256'] == hashlib.sha256(data+b'x'*512).hexdigest()
            mounts = guest('findmnt /run/h12/source; findmnt /run/h12/target; cat /proc/meminfo; df -k / /run /tmp')
            guest('sudo -n rm '+FIXTURE_DROPIN+'; sudo -n systemctl daemon-reload; sudo -n systemctl restart sv08-recovery-display.service')
            restored_exec = guest('systemctl show sv08-recovery-display.service --property=ExecStart --value')
            assert '/usr/lib/sv08/sv08_sd_reimage_ui.py' in restored_exec and '/run/sd-owner/h12-gtk.py' not in restored_exec
            time.sleep(3)
            relaunch = guest("systemctl is-active sv08-recovery-display.service; pgrep -af '[s]v08_sd_reimage_ui.py'; sha256sum /run/h12/target/target")
            assert result['target_sha256'] in relaunch
            guest('sudo -n umount /run/h12/target; sudo -n umount /run/h12/source')
            q = QMP(qpath); q.call('quit'); proc.wait(timeout=10)
        finally:
            if proc.poll() is None: proc.terminate(); proc.wait(timeout=10)
            if q: q.file.close(); q.sock.close()
    for name, expected in before.items(): assert sha(work/name) == expected, name+' changed'
    put(work/'run.json',json.dumps(dict(installed=result, wiring=wiring, fixture_exec=fixture_exec,
        restored_exec=restored_exec, installed_hashes=installed,
        mounts_resources=mounts, relaunch=relaunch, preserved=before, driver_sha256=sha(Path(__file__)),
        kernel_substitution='Debian 6.12.107; virtio disks, file-fixture admission; no physical compatibility',
        composition_sha256=sha(build/'composition.json')),indent=2)+'\n')


if __name__ == '__main__': main()
