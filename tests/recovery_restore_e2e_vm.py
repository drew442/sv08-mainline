#!/usr/bin/env python3
"""Disposable GPT fixtures and QEMU command for installed restore acceptance.

No block paths accepted. Reuses the installed export VM tooling; no downloads.
The coordinator owns execution and the installed root. Guest runner is
recovery_restore_e2e.py and may be copied to a private installed fixture.
"""
import argparse
import json
import os
import stat
import shutil
import subprocess
import gzip
import hashlib
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from recovery_export_vm import (safe_regular, partition_image, gpt, embed, media, part, identity,
                               stable_key, SOURCE_BYTES, SOURCE_START, SOURCE_SECTORS, SOURCE_UUID,
                               SOURCE_PARTUUID, LINUX_GUID, FAT_GUID, RECOVERY_BYTES, RECOVERY_UUID, sha, run, _unpack_initrd)
from test_recovery_activation import state_fixture, admission, BOOT
from sv08_export import Export

TARGET_UUID='dd0a5b84-794a-4b29-8f70-2483b2958013'
TARGET_PARTUUID='c6813a08-42af-45aa-b92c-364caf4ce814'
BOOT_PARTUUID='cf648ae0-d2c7-4c59-820c-561a858b7a9b'
NORMAL_ROOT_PARTUUID='0b20b8a1-cac2-4ff3-a2e6-f9e802214823'
BOOT_UUID='E2E0-0808'
BOOT_BYTES=64*1024**2
BOOT_SECTORS=122880


def fixture_path(path,fresh=False):
    path=Path(path).absolute()
    for ancestor in path.parents:
        info=ancestor.lstat()
        if not stat.S_ISDIR(info.st_mode) or ancestor.is_symlink() or info.st_uid not in (0,os.geteuid()) or info.st_mode & 0o022:
            raise ValueError('Fixture requires safe, owned directory ancestry')
    parent=path.parent.stat()
    if parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) != 0o700:
        raise ValueError('Use an assigned private parent owned by the fixture generator')
    if fresh and path.exists(): raise ValueError('Fresh fixture required')
    if path.exists() and not path.is_dir(): raise ValueError('Fixture must be a real directory')
    return path


def prepare(work,release):
    work=fixture_path(work,fresh=True); work.mkdir(parents=True,mode=0o700)
    normal=json.loads(Path(release).read_text())
    boot=dict(slot='A',release=normal['release'],state_schema=normal['state_schema'],release_revision=normal['release_revision'])
    # Reuse exact Store schema/layout; fixture constants are disposable evidence only.
    BOOT.update(boot)
    export_tree=work/'export-tree'; export_tree.mkdir(mode=0o700)
    state_fixture(export_tree/'sv08','restored fixture configuration','b'*32)
    (export_tree/'preserved-sibling').write_text('archive container sibling')
    archive_tree=work/'archive-tree';archive_tree.mkdir(mode=0o700)
    exporter=Export(export_tree,dict(archive=dict(path=str(archive_tree),label='Disposable archive')),admission,reserve_bytes=0)
    result=exporter.execute(exporter.prepare('archive'))
    (archive_tree/result['filename']).rename(archive_tree/'backup.tar')
    target_tree=work/'target-tree';target_tree.mkdir(mode=0o700)
    state_fixture(target_tree/'sv08','previous fixture configuration','a'*32)
    (target_tree/'keep').write_text('target sibling unchanged')
    for name,tree,fsuuid,partuuid in [('archive',archive_tree,SOURCE_UUID,SOURCE_PARTUUID),('target',target_tree,TARGET_UUID,TARGET_PARTUUID)]:
        partition=work/(name+'.ext4')
        partition_image(partition,SOURCE_SECTORS*512,'ext4',fsuuid,tree)
        gpt(work/(name+'.raw'),SOURCE_BYTES,[(SOURCE_START,SOURCE_SECTORS,LINUX_GUID,partuuid)])
        embed(work/(name+'.raw'),partition,SOURCE_START)
        partition.unlink()
    boot_partition=work/'boot.vfat'
    partition_image(boot_partition,BOOT_SECTORS*512,'vfat',BOOT_UUID)
    gpt(work/'boot.raw',BOOT_BYTES,[(SOURCE_START,BOOT_SECTORS,FAT_GUID,BOOT_PARTUUID)])
    embed(work/'boot.raw',boot_partition,SOURCE_START);boot_partition.unlink()
    recovery=dict(serial='SV08-RECOVERY');archive={'device/wwid':'naa.5000000000000001'};target={'device/wwid':'naa.5000000000000003'}
    topology=[media(recovery,RECOVERY_BYTES//512,False,'virtio',[],'ext4',RECOVERY_UUID),
        media(archive,SOURCE_BYTES//512,False,'scsi',[part(1,SOURCE_START,SOURCE_SECTORS,SOURCE_UUID,'ext4',SOURCE_PARTUUID)]),
        media(target,SOURCE_BYTES//512,False,'scsi',[part(1,SOURCE_START,SOURCE_SECTORS,TARGET_UUID,'ext4',TARGET_PARTUUID)]),
        media({'device/wwid':'naa.5000000000000004'},BOOT_BYTES//512,False,'scsi',[part(1,SOURCE_START,BOOT_SECTORS,BOOT_UUID,'vfat',BOOT_PARTUUID)])]
    archive_mount='/run/sv08-recovery/archives/backup';target_mount='/run/sv08-recovery/targets/target'
    profile=dict(recovery=identity(recovery,0,0,RECOVERY_BYTES//512,RECOVERY_UUID),recovery_path='/',media=sorted(topology,key=stable_key),boot=boot,
        archives=dict(backup=dict(label='Reviewed disposable archive',mount=archive_mount,path=archive_mount+'/backup.tar',identity=identity(archive,1,SOURCE_START,SOURCE_SECTORS,SOURCE_UUID))),
        targets=dict(target=dict(label='Reviewed disposable target',mount=target_mount,root=target_mount+'/restored',fresh_root=target_mount+'/fresh',identity=identity(target,1,SOURCE_START,SOURCE_SECTORS,TARGET_UUID))))
    (work/'restore-profile.json').write_text(json.dumps(profile,sort_keys=True,indent=2)+'\n')
    (work/'fixture.json').write_text(json.dumps(dict(boot=boot,normal_release_sha256=sha(release),archive_sha256=sha(work/'archive.raw'),target_sha256=sha(work/'target.raw'),boot_sha256=sha(work/'boot.raw')),indent=2)+'\n')
    return profile


def command(candidate,fixture,qmp,normal=None,expected='restored'):
    build=json.loads((candidate/'build.json').read_text())
    result = ['qemu-system-aarch64','-machine','virt','-cpu','cortex-a53','-accel','tcg,thread=multi','-smp','2','-m','768',
        '-kernel',str(candidate/'vmlinuz'),'-initrd',str(candidate/'initrd.img'),
        '-append','console=tty0 console=ttyAMA0 root=/dev/vda ro sv08.envelope='+build['manifest_sha256']+' sv08.recovery='+build['provider_manifest_sha256']+' systemd.debug_shell=ttyAMA0 systemd.mask=serial-getty@ttyAMA0.service systemd.log_target=console',
        '-drive',f'if=none,id=recovery,format=raw,file={candidate}/recovery.ext4,readonly=on','-device','virtio-blk-pci,drive=recovery,serial=SV08-RECOVERY',
        '-device','virtio-scsi-pci,id=scsi0',
        '-drive',f'if=none,id=archive,format=raw,file={fixture}/archive.raw,readonly=on','-device','scsi-hd,drive=archive,serial=SV08-ARCHIVE,bus=scsi0.0,wwn=0x5000000000000001',
        '-drive',f'if=none,id=target,format=raw,file={fixture}/target.raw','-device','scsi-hd,drive=target,serial=SV08-TARGET,bus=scsi0.0,wwn=0x5000000000000003',
        '-device','virtio-gpu-pci,id=video0,xres=1024,yres=768','-device','qemu-xhci,id=usb0','-device','usb-kbd','-device','usb-tablet',
        '-nic','none','-display','none','-serial','mon:stdio','-qmp',f'unix:{qmp},server=on,wait=off','-no-reboot']

    # The extra paired boot drive is part of the reviewed complete inventory.
    result += ['-drive',f'if=none,id=boot,format=raw,file={fixture}/boot.raw,readonly=on',
               '-device','scsi-hd,drive=boot,serial=SV08-BOOT,bus=scsi0.0,wwn=0x5000000000000004']
    if normal is not None:
        result[result.index('-initrd')+1]=str(normal/'normal-initrd.img')
        result[result.index('-append')+1]=(result[result.index('-append')+1].replace('root=/dev/vda ','root=/dev/vda1 ')+
            ' rauc.slot=A sv08.e2e.expect='+expected)
        for i,value in enumerate(result):
            if value.startswith('if=none,id=recovery,'):
                result[i]=f'if=none,id=recovery,format=raw,file={normal}/normal-root.raw,readonly=on'
    return result


def stage_seed(rootfs,fixture):
    rootfs=safe_regular(rootfs);fixture=fixture_path(fixture)
    runtime=rootfs/'usr/lib/sv08'
    if not (runtime/'sv08_boot.py').is_file():raise ValueError('Use the private installed runtime root')
    if not (rootfs/'usr/bin/ssh-keygen').is_file():raise ValueError('Actual normal boot needs installed ARM64 ssh-keygen closure')
    boot=json.loads((fixture/'fixture.json').read_text())['boot']
    device=lambda value:'/dev/disk/by-partuuid/'+value
    # Unused B/recovery roles are explicit fixture identifiers, never hardware facts.
    release=dict(release=boot['release'],state_schema=boot['state_schema'],release_revision=boot['release_revision'],deployable=False,
        devices={'root-a':device(NORMAL_ROOT_PARTUUID),'data':device(TARGET_PARTUUID),'boot-a':device(BOOT_PARTUUID),
                 'root-b':device('0b20b8a1-cac2-4ff3-a2e6-f9e802214824'),
                 'boot-b':device('cf648ae0-d2c7-4c59-820c-561a858b7a9c'),
                 'recovery':device('0b20b8a1-cac2-4ff3-a2e6-f9e802214825')})
    (runtime/'release.json').write_text(json.dumps(release,indent=2)+'\n')
    (runtime/'seed/config').mkdir(parents=True,exist_ok=True)
    (runtime/'seed/authorized_keys').write_text('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFixtureOnlyNoAuthenticationAllowed sv08-disposable-fixture\n')
    (runtime/'seed/authorized_keys').chmod(0o644)
    shutil.copyfile(Path(__file__).with_name('recovery_restore_e2e.py'),runtime/'recovery_restore_e2e.py')
    (runtime/'e2e-disposable').write_text('sv08-disposable-restore-e2e-v1\n')
    return release


def prepare_normal(candidate,rootfs,work,fixture):
    candidate=safe_regular(candidate);rootfs=safe_regular(rootfs);work=safe_regular(work,fresh=True);fixture=fixture_path(fixture)
    work.mkdir(mode=0o700)
    tree=work/'envelope';shutil.copytree(candidate/'envelope',tree,symlinks=True)
    # Replace only recovery's volatile links with real normal-boot mount targets.
    directories=('var/log','var/tmp','var/cache','var/lib/systemd','var/lib/dbus','data','boot','home/sv08',
        'etc/NetworkManager/system-connections','var/lib/NetworkManager','var/lib/rauc','var/lib/systemd/timesync',
        'var/lib/systemd/rfkill','var/lib/systemd/linger')
    for name in directories:
        path=tree/name
        if path.is_symlink():path.unlink()
        path.mkdir(parents=True,exist_ok=True)
    for name in ('etc/machine-id','etc/hostname','etc/hosts','var/lib/systemd/random-seed'):
        path=tree/name
        if path.is_symlink():path.unlink()
        if not path.exists():path.touch()
    units=tree/'etc/systemd/system'
    default=units/'default.target';default.unlink(missing_ok=True);default.symlink_to('sv08-e2e-normal.target')
    (units/'sv08-e2e-normal.target').write_text('[Unit]\nDescription=Disposable actual SV08 normal boot entry\nRequires=sysinit.target basic.target sv08-prepare.service sv08-e2e-normal-assert.service\nAfter=sv08-prepare.service\nAllowIsolate=yes\n')
    shutil.copyfile(Path(__file__).resolve().parents[1]/'configs/host-os/systemd/sv08-prepare.service',units/'sv08-prepare.service')
    dropin=units/'sv08-prepare.service.d';dropin.mkdir(exist_ok=True)
    (dropin/'e2e.conf').write_text('[Unit]\nFailureAction=none\n')
    (units/'data.mount').write_text('[Unit]\nDescription=Disposable data prepared before PID 1\n[Mount]\nWhat=/dev/disk/by-partuuid/'+TARGET_PARTUUID+'\nWhere=/data\nType=ext4\nOptions=rw,nodev,nosuid\n')
    (units/'sv08-e2e-normal-assert.service').write_text('[Unit]\nRequires=sv08-prepare.service\nAfter=sv08-prepare.service\n[Service]\nType=oneshot\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nExecStart=/usr/bin/python3 /usr/lib/sv08/recovery_restore_e2e.py --phase normal-assert --disposable-marker /usr/lib/sv08/e2e-disposable\nRemainAfterExit=yes\nStandardOutput=journal+console\nStandardError=journal+console\n')
    # A fresh image receives a GPT root partition; verify_devices is unmodified.
    partition=work/'normal-root.ext4'
    partition_image(partition,RECOVERY_BYTES,'ext4',RECOVERY_UUID,tree)
    gpt(work/'normal-root.raw',RECOVERY_BYTES+4*1024**2,[(SOURCE_START,RECOVERY_BYTES//512,LINUX_GUID,NORMAL_ROOT_PARTUUID)])
    embed(work/'normal-root.raw',partition,SOURCE_START);partition.unlink()
    unpack=work/'initramfs';unpack.mkdir()
    _unpack_initrd(candidate/'initrd.img',unpack)
    # Copy the existing ARM64 fsck executable and its actual ELF dependency closure.
    pending=[rootfs/'usr/sbin/e2fsck'];seen=set()
    while pending:
        source=pending.pop();source=source.resolve()
        if source in seen:continue
        if not source.is_relative_to(rootfs.resolve()):raise ValueError('ELF dependency escaped private installed root')
        seen.add(source)
        relative=source.relative_to(rootfs.resolve());destination=unpack/relative
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        deps=run(['readelf','-d',source],capture=True).stdout
        import re
        for dependency in re.findall(r'\(NEEDED\).*?\[(.*?)\]',deps):
            matches=[path for directory in ('usr/lib/aarch64-linux-gnu','lib/aarch64-linux-gnu') for path in [rootfs/directory/dependency] if path.exists()]
            if not matches:raise ValueError('Missing installed fsck dependency: '+dependency)
            selected=matches[0].resolve();pending.append(selected)
            # Preserve SONAME lookup even when the installed source is a symlink.
            link=unpack/'usr/lib/aarch64-linux-gnu'/dependency;link.parent.mkdir(parents=True,exist_ok=True)
            if not link.exists():shutil.copyfile(selected,link)
    shutil.copyfile(rootfs/'usr/sbin/e2fsck',unpack/'sbin/fsck.ext4');(unpack/'sbin/fsck.ext4').chmod(0o755)
    scripts=unpack/'scripts';scripts.mkdir(exist_ok=True)
    shutil.copyfile(rootfs/'usr/share/initramfs-tools/scripts/functions',scripts/'functions')
    hook=Path(__file__).resolve().parents[1]/'configs/host-os/initramfs/sv08-data'
    (scripts/'sv08-data').write_text(hook.read_text().replace('@DATA_DEVICE@','/dev/disk/by-partuuid/'+TARGET_PARTUUID))
    (scripts/'sv08-data').chmod(0o755)
    kernel=next((rootfs/'usr/lib/modules').iterdir()).name
    for module in ('virtio_scsi','sd_mod','vfat'):
        depends=run(['modprobe','-d',rootfs,'-S',kernel,'--show-depends',module],capture=True).stdout
        for line in depends.splitlines():
            if line.startswith('insmod '):
                source=Path(line.split()[1]);destination=unpack/source.relative_to(rootfs)
                destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
    for applet in ('mktemp','chmod','mv','fsck','halt'):
        path=unpack/'bin'/applet
        if not path.exists():path.symlink_to('busybox')
    init=(unpack/'init').read_text()
    init=init.replace('root=/dev/vda','root=/dev/vda1').replace('/dev/vda','/dev/vda1').replace('/sys/class/block/vda/','/sys/class/block/vda1/')
    # First replacement changed root= twice; retain the exact partition name.
    init=init.replace('root=/dev/vda11','root=/dev/vda1')
    init=init.replace('squashfs; do','squashfs virtio_scsi sd_mod vfat; do')
    insertion="""
mkdir -p /dev/disk/by-partuuid
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    for block in /sys/class/block/*; do
        node=/dev/$(basename "$block")
        [ -b "$node" ] || continue
        partuuid=$(blkid -s PARTUUID -o value "$node")
        [ -z "$partuuid" ] || [ -e "/dev/disk/by-partuuid/$partuuid" ] || ln -s "$node" "/dev/disk/by-partuuid/$partuuid"
    done
    [ -b /dev/disk/by-partuuid/@TARGET_PARTUUID@ ] && break
    sleep 1
done
export rootmnt=/newroot quiet=y panic=-1
/scripts/sv08-data || fail 'normal data/identity hook refused'
echo 'SV08_NORMAL_PRE_PID1_IDENTITY: actual sv08-data completed' >/dev/console
"""
    insertion=insertion.replace('@TARGET_PARTUUID@',TARGET_PARTUUID)
    init=init.replace('mount --move /run /newroot/run',insertion+'\nmount --move /run /newroot/run')
    # Marker is recovery-specific and must not admit recovery services in this role.
    init=init.replace('echo "$expected" >/run/sv08/recovery-verified','echo normal-role >/run/sv08/e2e-normal-role')
    init=init.replace('SV08_RECOVERY_VERIFIED:', 'SV08_NORMAL_ROOT_VERIFIED:').replace('SV08_RECOVERY_REFUSED:', 'SV08_NORMAL_ROOT_REFUSED:')
    (unpack/'init').write_text(init)
    # Extra busybox applets used by the unmodified identity hook and PARTUUID mapping.
    for applet in ('basename','ln'):
        path=unpack/'bin'/applet
        if not path.exists():path.symlink_to('busybox')
    files=sorted(['.',*(str(path.relative_to(unpack)) for path in unpack.rglob('*'))])
    packed=subprocess.run(['cpio','--null','-o','--format=newc','--owner=0:0','--quiet'],cwd=unpack,input=('\0'.join(files)+'\0').encode(),capture_output=True,check=True,timeout=30).stdout
    with gzip.GzipFile(filename='',mode='wb',fileobj=(work/'normal-initrd.img').open('wb'),mtime=0) as stream:stream.write(packed)
    receipt=dict(normal_root_sha256=sha(work/'normal-root.raw'),initrd_sha256=sha(work/'normal-initrd.img'),hook_source_sha256=sha(hook),boot_runtime_sha256=sha(rootfs/'usr/lib/sv08/sv08_boot.py'),release_sha256=sha(rootfs/'usr/lib/sv08/release.json'),functions_sha256=sha(scripts/'functions'))
    (work/'normal-fixture.json').write_text(json.dumps(receipt,indent=2)+'\n')
    shutil.rmtree(unpack)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare');p.add_argument('--work',type=Path,required=True);p.add_argument('--normal-release',type=Path,required=True)
    p=sub.add_parser('command');p.add_argument('--candidate',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--qmp',type=Path,required=True);p.add_argument('--normal',type=Path);p.add_argument('--expected',choices=('restored','previous'),default='restored')
    p=sub.add_parser('stage-seed');p.add_argument('--rootfs',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True)
    p=sub.add_parser('prepare-normal');p.add_argument('--candidate',type=Path,required=True);p.add_argument('--rootfs',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='prepare': print(json.dumps(prepare(args.work,args.normal_release)))
    elif args.action=='stage-seed':print(json.dumps(stage_seed(args.rootfs,args.fixture)))
    elif args.action=='prepare-normal':print(json.dumps(prepare_normal(args.candidate,args.rootfs,args.work,args.fixture)))
    else: print(json.dumps(command(safe_regular(args.candidate),fixture_path(args.fixture),args.qmp,safe_regular(args.normal) if args.normal else None,args.expected)))

if __name__=='__main__': main()
