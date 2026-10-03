#!/usr/bin/env python3
"""Complete SD recovery GUI/SSH runtime with two fresh offline VM starts.

Regular fixtures only; test private key must be synthetic, never an owner key.
QEMU virt substitutes the pinned Debian kernel for the H616 kernel. Same root,
initramfs, config inventory, gate and installed GTK/SSH userspace are tested.
"""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import shutil
import re
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_sd_recovery_host import safe, sha, run, put, PARTUUID, SIZE
from recovery_vm import QMP


def ssh(port, key, command, known, authorized=True, password=False):
    args=['ssh','-p',str(port),'-o','BatchMode=yes','-o','ConnectTimeout=5',
          '-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(known),
          '-o','IdentitiesOnly=yes','-i',str(key)]
    if password:
        args+=['-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no']
    result=subprocess.run(args+['recovery@127.0.0.1',command],capture_output=True,text=True,timeout=20)
    if authorized and result.returncode:
        raise AssertionError('Authorized SSH failed: '+result.stderr)
    if not authorized and result.returncode==0:
        raise AssertionError('Unauthorized SSH succeeded')
    return dict(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','work','test-key'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--port',type=int,default=22283)
    p.add_argument('--seconds',type=int,default=240)
    p.add_argument('--observe',type=int,default=210)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args();build=safe(a.build);work=safe(a.work);key=safe(a.test_key,True)
    if work.exists() or build in work.parents or work in build.parents:
        raise ValueError('Fresh separate VM work required')
    record=json.loads((build/'composition.json').read_text())
    if not record.get('test_only_authorized_key'):
        raise ValueError('Explicit fixture-authentication image required')
    if not 1024<=a.port<=65535 or not 30<=a.seconds<=600 or not 15<=a.observe<=300:
        raise ValueError('Invalid bounded VM port/deadline/observation')
    image=safe(build/'recovery.ext4',True)
    if sha(image)!=record['root_sha256'] or sha(build/'boot/initrd.img')!=record['payloads']['initrd.img']['sha256']:
        raise ValueError('Composed artifacts changed')
    if not a.execute:
        print(json.dumps(dict(execute=False,memory_mib=768,restarts=2,observe=a.observe)));return
    harness_sha256=sha(Path(__file__))
    work.mkdir(parents=True,mode=0o700)
    disk=work/'sd.img'
    with disk.open('xb') as stream:stream.truncate(704*1024**2)
    run('sgdisk','--clear','--new=1:32768:294911','--typecode=1:0700','--partition-guid=1:91a855d4-e0d7-4bd5-ab68-62c44d36e60f',
        '--new=2:294912:1343487','--typecode=2:8300','--partition-guid=2:'+PARTUUID,disk)
    with disk.open('r+b') as stream:
        stream.seek(144*1024**2)
        with image.open('rb') as source:shutil.copyfileobj(source,stream)
    before=sha(disk)
    run('ssh-keygen','-q','-t','ed25519','-N','','-f',work/'unauthorized-key')
    records=[]
    for boot in (1,2):
        logpath=work/f'boot-{boot}.log';qmp=work/f'qmp-{boot}.sock';known=work/f'known-{boot}'
        cmd=['qemu-system-aarch64','-machine','virt','-cpu','cortex-a53','-accel','tcg,thread=multi',
             '-smp','2','-m','768','-kernel',str(build/'vm-vmlinuz'),'-initrd',str(build/'boot/initrd.img'),
             '-append',f'console=ttyAMA0 root=PARTUUID={PARTUUID} ro sv08.envelope={record["manifest_sha256"]} systemd.log_target=console',
             '-drive',f'if=none,id=sd,format=raw,file={disk}', '-device','virtio-blk-pci,drive=sd',
             '-device','virtio-gpu-pci,id=video0,xres=1024,yres=768','-device','qemu-xhci',
             '-device','usb-kbd','-device','usb-tablet',
             '-netdev',f'user,id=net,hostfwd=tcp:127.0.0.1:{a.port}-:22','-device','virtio-net-pci,netdev=net,romfile=',
             '-display','none','-serial','stdio','-qmp',f'unix:{qmp},server=on,wait=off','-no-reboot']
        put(work/f'command-{boot}.json',json.dumps(cmd,indent=2)+'\n')
        started=time.monotonic();q=None
        with logpath.open('wb') as log:
            proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            try:
                ready=False
                while proc.poll() is None and time.monotonic()-started<a.seconds:
                    output=logpath.read_text(errors='replace')
                    if 'SV08_RECOVERY_REFUSED' in output:
                        raise AssertionError('Positive root gate refused: '+output[-1500:])
                    if 'Server listening on 0.0.0.0 port 22' in output and 'SpiRegistry daemon is running' in output:
                        try:
                            attempt=subprocess.run(['ssh','-p',str(a.port),'-i',str(key),'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(known),'-o','ConnectTimeout=2','recovery@127.0.0.1','systemctl is-active sv08-recovery-display.service && test -f /run/sv08/boot-report.json'],capture_output=True,timeout=15)
                        except subprocess.TimeoutExpired:
                            time.sleep(1);continue
                        if attempt.returncode==0:
                            ready=True;break
                    time.sleep(1)
                if not ready:raise AssertionError('Full userspace SSH deadline: '+logpath.read_text(errors='replace')[-2500:])
                command="""set -e
cat /proc/1/comm
sudo -n id -u
systemctl is-active sv08-recovery-display.service sd-host-ssh.service systemd-networkd.service
pgrep -af sv08_sd_reimage_ui.py
systemctl --no-pager --plain list-units --type=service --state=running --no-legend
systemctl --no-pager --plain list-sockets --all --no-legend
cat /run/sv08/boot-report.json
printf test > /run/sd-owner/runtime-write
if sudo -n touch /etc/sd-host-forbidden-write 2>/dev/null; then exit 88; fi
cat /proc/mounts
cat /proc/sys/kernel/random/boot_id
"""
                fingerprint=run('ssh-keygen','-lf',known).decode().split()[1]
                if fingerprint not in logpath.read_text(errors='replace'):
                    raise AssertionError('SSH server fingerprint differs from generated console identity')
                protected=ssh(a.port,key,'sudo -n blockdev --getro /dev/vda2; findmnt -n -o OPTIONS /; findmnt -n -o FSTYPE --target /run; findmnt -n -o FSTYPE --target /tmp',known)
                protection_lines=protected['stdout'].splitlines()
                if protection_lines[0]!='1' or not protection_lines[1].startswith('ro,') or protection_lines[2:]!=['tmpfs','tmpfs']:
                    raise AssertionError('Root partition ioctl/mount protection absent')
                initial=ssh(a.port,key,command,known)
                boot_report=json.loads(ssh(a.port,key,'cat /run/sv08/boot-report.json',known)['stdout'])
                if 'sv08_sd_reimage_ui.py' not in initial['stdout']:
                    raise AssertionError('Actual GTK process missing')
                if boot_report['registry_exists']:
                    raise AssertionError('Persistent registry initialized unexpectedly')
                if 'systemd' not in initial['stdout'] or initial['stdout'].count('active')<3:
                    raise AssertionError('Normal init/UI/SSH service missing')
                if qmp.exists():
                    q=QMP(qmp);time.sleep(3);q.shot(work/f'ui-{boot}.ppm')
                    frame=(work/f'ui-{boot}.ppm').read_bytes().split(b'\n',3)[-1]
                    if len(set(frame))<2:raise AssertionError('GTK display frame is blank')
                    q.key('tab');time.sleep(1);q.key('alt','r');time.sleep(2)
                    q.shot(work/f'ui-review-{boot}.ppm');q.key('esc')
                else:raise AssertionError('QMP display unavailable')
                denied=ssh(a.port,work/'unauthorized-key','true',known,False)
                password=ssh(a.port,key,'true',known,False,True)
                observe_start=time.monotonic()
                while time.monotonic()-observe_start<(a.observe if boot==1 else 30):
                    if proc.poll() is not None:raise AssertionError('Normal init exited during observation')
                    time.sleep(1)
                final=ssh(a.port,key,'systemctl is-active sv08-recovery-display.service sd-host-ssh.service; cat /proc/sys/kernel/random/boot_id',known)
                if final['stdout'].splitlines()[:2]!=['active','active']:
                    raise AssertionError('GUI/SSH ceased running during observation')
                records.append(dict(protected_root=protected,boot_report=boot_report,host_fingerprint=fingerprint,boot=boot,initial=initial,final=final,unauthorized=denied,password=password,
                                    observed_seconds=time.monotonic()-observe_start,known_hosts=known.read_text(),
                                    elapsed_seconds=time.monotonic()-started))
                put(work/f'boot-{boot}-result.json',json.dumps(records[-1],indent=2)+'\n')
            finally:
                if proc.poll() is None:
                    if q:
                        try:q.call('quit')
                        except (ValueError,OSError):pass
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
                if q:q.file.close();q.sock.close()
                qmp.unlink(missing_ok=True)
    if records[0]['known_hosts']==records[1]['known_hosts']:
        raise AssertionError('Volatile host identity did not change on fresh boot')
    # No NIC is present: local GUI must still start and accept keyboard input.
    no_net=cmd[:]
    index=no_net.index('-netdev');del no_net[index:index+4]
    no_net+=['-nic','none']
    qpath=work/'qmp-no-network.sock';logpath=work/'no-network.log'
    no_net[no_net.index('-qmp')+1]=f'unix:{qpath},server=on,wait=off'
    no_network_report=None;q=None
    with logpath.open('wb') as log:
        proc=subprocess.Popen(no_net,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        start=time.monotonic()
        try:
            while proc.poll() is None and time.monotonic()-start<a.seconds:
                text=logpath.read_text(errors='replace')
                for line in text.splitlines():
                    if 'SV08_RECOVERY_BOOT_REPORT ' not in line:continue
                    report=json.loads(line.split('SV08_RECOVERY_BOOT_REPORT ',1)[1])
                    if 'SpiRegistry daemon is running' in text and 'ActiveState=active' in report['display_unit'] and any('/usr/bin/X' in p['command'] for p in report['processes']):
                        no_network_report=report
                if no_network_report:break
                time.sleep(1)
            if not no_network_report:raise AssertionError('No-network GTK deadline')
            q=QMP(qpath);time.sleep(3);q.shot(work/'no-network-ui.ppm');q.key('alt','r');time.sleep(2)
            q.shot(work/'no-network-review.ppm');q.key('esc')
            time.sleep(15)
            if proc.poll() is not None:raise AssertionError('No-network recovery exited')
        finally:
            if proc.poll() is None:
                if q:
                    try:q.call('quit')
                    except (ValueError,OSError):pass
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            if q:q.file.close();q.sock.close()
            qpath.unlink(missing_ok=True)
    negatives=[]
    # The whole disk remains writable: early admission protects partition 2.
    # No block devices, loops or physical storage are used on the host.
    base=cmd[:]
    for name in ('wrong-hash','wrong-index','corrupt-usr'):
        changed=False
        cmd=base[:]
        if name=='wrong-hash':
            i=cmd.index('-append')+1
            cmd[i]=cmd[i].replace(record['manifest_sha256'],'0'*64)
        elif name=='wrong-index':
            run('sgdisk','--partition-guid=1:'+PARTUUID,
                '--partition-guid=2:773cf3bf-82ba-43df-b602-dafc52f24665',disk)
        else:
            output=run('debugfs','-R','bmap /usr.squashfs 0',image).decode().strip().splitlines()[-1]
            block=int(output)
            stats=run('dumpe2fs','-h',image).decode()
            block_size=int(re.search(r'Block size:\s+(\d+)',stats).group(1))
            offset=144*1024**2+block*block_size
            with disk.open('r+b') as stream:
                stream.seek(offset);original=stream.read(1);stream.seek(offset)
                stream.write(bytes([original[0]^1]))
            changed=True
        qpath=work/f'qmp-{name}.sock';logpath=work/f'{name}.log'
        cmd[cmd.index('-qmp')+1]=f'unix:{qpath},server=on,wait=off'
        with logpath.open('wb') as log:
            proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            start=time.monotonic()
            try:
                while proc.poll() is None and time.monotonic()-start<120:
                    text=logpath.read_text(errors='replace')
                    if 'SV08_RECOVERY_REFUSED' in text:break
                    time.sleep(1)
                text=logpath.read_text(errors='replace')
                if 'SV08_RECOVERY_REFUSED' not in text or 'SV08_RECOVERY_VERIFIED' in text:
                    raise AssertionError('Negative admission failed: '+name)
                negatives.append(dict(name=name,refusal=[line for line in text.splitlines() if 'SV08_RECOVERY_REFUSED' in line],seconds=time.monotonic()-start))
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
                qpath.unlink(missing_ok=True)
        if name=='wrong-index':
            run('sgdisk','--partition-guid=1:91a855d4-e0d7-4bd5-ab68-62c44d36e60f','--partition-guid=2:'+PARTUUID,disk)
        if changed:
            with disk.open('r+b') as stream:stream.seek(offset);stream.write(original)
    after=sha(disk)
    if sha(Path(__file__))!=harness_sha256:
        raise AssertionError('Harness source changed during run')
    if before!=after or sha(image)!=record['root_sha256']:
        raise AssertionError('Recovery source/disk mutated')
    put(work/'run.json',json.dumps(dict(complete_userspace=True,physical_boot=False,boots=records,
        harness_sha256=harness_sha256,guest_ram_mib=768,no_network_local_gui=no_network_report,negative_admission=negatives,source_preserved=True,disk_sha256=after,
        vm_kernel_sha256=sha(build/'vm-vmlinuz'),shared_initramfs_sha256=sha(build/'boot/initrd.img'),
        shared_gate_sha256=record['boot_gate_sha256']),indent=2)+'\n')

if __name__=='__main__':main()
