#!/usr/bin/env python3
"""Pinned offline recovery assembly; inspection unless --execute is explicit.

Custom gap: compressed-/usr integration and independently checked boot envelope.
See ADR 0014. No device writing, activation, package resolution or network service.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import re
import urllib.request
import time
import signal
import uuid

REPO = Path(__file__).resolve().parents[1]
KERNEL = '6.12.107+deb13-arm64'
SIZE = 512 * 1024**2
UUID = '964ed891-6ec4-4a95-8762-e32c91260394'
EPOCH = 1788220800


def board_profile(path):
    if path is None:return None
    def unique(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate board profile field')
            result[key]=value
        return result
    value=json.loads(clean_path(path).read_text(),object_pairs_hook=unique)
    if set(value)!={'format_version','kernel_release','recovery','partitions','artifacts','packages'} or value['format_version']!=1:
        raise ValueError('Invalid board profile schema')
    if value['kernel_release']!='6.18.51-sv08-candidate1':raise ValueError('Unreviewed board kernel')
    def canonical(value):
        if not isinstance(value,str) or str(uuid.UUID(value))!=value or uuid.UUID(value).int==0:raise ValueError('Invalid canonical partition UUID')
    recovery=value['recovery']
    if set(recovery)!={'partuuid','filesystem_uuid','bytes','index'} or recovery['filesystem_uuid']!=UUID or recovery['bytes']!=SIZE or recovery['index']!=5:
        raise ValueError('Invalid recovery identity/capacity')
    canonical(recovery['partuuid'])
    partitions=value['partitions']
    if len(partitions)!=6 or {p['index'] for p in partitions}!=set(range(1,7)) or len({p['partuuid'] for p in partitions})!=6 or len({p['role'] for p in partitions})!=6:
        raise ValueError('Six distinct partition identities required')
    for p in partitions:
        if set(p)!={'role','index','partuuid'} or type(p['index']) is not int:raise ValueError('Invalid partition schema')
        canonical(p['partuuid'])
    if [p['role'] for p in sorted(partitions,key=lambda p:p['index'])]!=['boot-a','root-a','boot-b','root-b','recovery','data']:raise ValueError('Unexpected partition roles/order')
    if [p for p in partitions if p['role']=='recovery']!=[dict(role='recovery',index=5,partuuid=recovery['partuuid'])]:raise ValueError('Recovery partition role mismatch')
    artifacts=value['artifacts']
    if set(artifacts)!={'image','config','dtb','modules'}:raise ValueError('Missing board artifacts')
    for name,item in artifacts.items():
        digest='inventory_sha256' if name=='modules' else 'sha256'
        if set(item)!={'path',digest} or not re.fullmatch('[0-9a-f]{64}',item[digest]):raise ValueError('Invalid artifact digest')
        relative=Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:raise ValueError('Invalid artifact path')
    release=value['kernel_release']
    for name,path in [('image','boot/vmlinuz-'+release),('config','boot/config-'+release),('modules','usr/lib/modules/'+release)]:
        if artifacts[name]['path']!=path:raise ValueError('Unexpected kernel artifact path')
    packages=value['packages']
    expected={'linux-image-'+release,'sv08-board-support-'+release}
    if len(packages)!=2:raise ValueError('Exactly two reviewed packages required')
    for p in packages:
        if set(p)!={'filename','sha256','bytes'} or Path(p['filename']).name!=p['filename'] or not re.fullmatch('[0-9a-f]{64}',p['sha256']) or type(p['bytes']) is not int or p['bytes']<=0:raise ValueError('Invalid package identity')
    if {p['filename'].split('_')[0] for p in packages}!=expected:raise ValueError('Unexpected board package set')
    return value


def check_board_artifacts(root, profile):
    for name,item in profile['artifacts'].items():
        path=clean_path(root/item['path'])
        actual=inventory(path)['sha256'] if name=='modules' else sha(path)
        if actual!=item.get('sha256',item.get('inventory_sha256')):raise ValueError('Changed board artifact: '+name)
    config=(root/profile['artifacts']['config']['path']).read_text().splitlines()
    for symbol in ('CONFIG_MMC','CONFIG_MMC_SUNXI','CONFIG_SERIAL_8250','CONFIG_SERIAL_8250_CONSOLE','CONFIG_SERIAL_8250_DW','CONFIG_PINCTRL_SUN50I_H616','CONFIG_SUN50I_H616_CCU','CONFIG_MFD_AXP20X_I2C','CONFIG_I2C_MV64XXX','CONFIG_REGULATOR_AXP20X'):
        if symbol+'=y' not in config:raise ValueError('Missing built-in board startup dependency: '+symbol)


def boot_gate(profile=None):
    content=(REPO/'configs/host-os/recovery-init').read_text()
    if profile is None:return content
    start=content.index('for module in virtio_pci ')
    end=content.index('manifest=/newroot/')
    selector=(REPO/'configs/host-os/recovery-board-root').read_text()
    for key,value in {'PARTUUID':profile['recovery']['partuuid'],'INDEX':5,'SECTORS':SIZE//512,'UUID':UUID}.items():selector=selector.replace('@'+key+'@',str(value))
    content=content[:start]+selector+content[end:]
    old="= '/dev/vda:ext4:ro,relatime,norecovery'"
    if content.count(old)!=1:raise ValueError('Common mount gate changed; review required')
    return content.replace(old,'= "${recovery_device}:ext4:ro,relatime,norecovery"')


def run(args, **kw):
    timeout=kw.pop('timeout',900);data=kw.pop('input',None)
    if kw.pop('capture_output',False):kw['stdout']=subprocess.PIPE;kw['stderr']=subprocess.PIPE
    if data is not None:kw['stdin']=subprocess.PIPE
    with subprocess.Popen([str(x) for x in args],start_new_session=True,**kw) as child:
        try:out,err=child.communicate(data,timeout=timeout)
        except BaseException:
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            child.wait(timeout=10)
            raise
        if child.returncode:raise subprocess.CalledProcessError(child.returncode,args,out,err)
        return subprocess.CompletedProcess(args,child.returncode,out,err)


def integration_inputs():
    paths=[Path(__file__),REPO/'scripts/stage_admin_ui.py',REPO/'scripts/prepare_host_os.py',REPO/'configs/host-os/recovery-init',REPO/'configs/host-os/sv08-recovery-display.service',REPO/'configs/host-os/recovery-session.desktop',*(REPO/'runtime').glob('*.py')]
    paths.append(REPO/'configs/host-os/recovery-board-root')
    return {str(p.relative_to(REPO)):sha(p) for p in paths}


def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def clean_path(path, *, output=False):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Symlink paths are refused')
    if path.exists() and not (path.is_file() or path.is_dir()):
        raise ValueError('Only regular files/directories are accepted; no raw devices')
    if output and (not path.is_relative_to(REPO / 'build') or path == REPO / 'build'):
        raise ValueError('Output must be a fresh path inside repository build/')
    return path


def separate(output, *inputs):
    for source in inputs:
        if output == source or output in source.parents or source in output.parents:
            raise ValueError('Input/output overlap refused')


def private():
    if os.geteuid() != 0: raise ValueError('Preparation requires root in private namespaces')
    for kind in ('mnt', 'pid', 'net'):
        if os.readlink('/proc/self/ns/'+kind) == os.readlink('/proc/1/ns/'+kind):
            raise ValueError('Private mount/PID/network namespaces required before private /proc mount')
    run(['mount', '--make-rprivate', '/'])


def write(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content); path.chmod(mode)


def inventory(root, *, empty_xattr_reference=None):
    """Identity excludes timestamps normalized by packaging, never ownership/xattrs.

    Readback may accept an unsupported xattr API only against an explicitly
    supplied same-path source whose attribute set is proven empty.
    """
    import errno
    h = hashlib.sha256(); files = size = unsupported = 0; links = {}
    for p in [root, *sorted(root.rglob('*'))]:
        s=p.lstat();relative=str(p.relative_to(root))
        try: attrs=sorted((name,os.getxattr(p,name,follow_symlinks=False).hex()) for name in os.listxattr(p,follow_symlinks=False))
        except OSError as error:
            reference=empty_xattr_reference / relative if empty_xattr_reference is not None else None
            if error.errno!=errno.EOPNOTSUPP or reference is None or os.listxattr(reference,follow_symlinks=False):raise
            attrs=[];unsupported+=1
        value=os.readlink(p) if stat.S_ISLNK(s.st_mode) else sha(p) if stat.S_ISREG(s.st_mode) else ''
        topology=None
        if stat.S_ISREG(s.st_mode):
            topology=[s.st_nlink,links.setdefault((s.st_dev,s.st_ino),relative)]
            files+=1;size+=s.st_size
        h.update(json.dumps([relative,s.st_mode,s.st_uid,s.st_gid,value,attrs,topology],separators=(',',':')).encode())
    return dict(schema=2,sha256=h.hexdigest(),files=files,bytes=size)


def intake(a):
    work=clean_path(a.work,output=True);lock=clean_path(a.lock);separate(work,lock)
    packages=json.loads(lock.read_text())['packages']
    if work.exists():raise ValueError('Intake requires a fresh output')
    if not a.execute:return dict(execute=False,stage='intake',packages=len(packages),bytes=sum(p['bytes'] for p in packages))
    if os.geteuid()==0:raise ValueError('Network intake runs unprivileged')
    work.mkdir(parents=True,mode=0o700)
    for p in packages:
        if not re.fullmatch('[0-9a-f]{64}',p['sha256']) or not p['url'].startswith('https://snapshot.debian.org/archive/'):
            raise ValueError('Invalid locked intake identity')
        target=work/(p['sha256']+'.deb')
        for attempt in range(3):
            try:
                with urllib.request.urlopen(p['url'],timeout=60) as response,target.open('wb') as output:
                    remaining=p['bytes']+1
                    while remaining:
                        data=response.read(min(1024*1024,remaining))
                        if not data:break
                        output.write(data);remaining-=len(data)
                if target.stat().st_size!=p['bytes'] or sha(target)!=p['sha256']:raise ValueError('Archive size/hash mismatch')
                break
            except Exception:
                target.unlink(missing_ok=True)
                if attempt==2:raise
    return dict(stage='intake',packages=len(packages),lock_sha256=sha(lock))


def assemble(a):
    inputs=integration_inputs()
    work=clean_path(a.work,output=True); intake=clean_path(a.intake); lock=clean_path(a.lock)
    separate(work,intake,lock)
    if work.exists(): raise ValueError('Assembly requires a fresh output')
    lock_hash=sha(lock)
    packages=json.loads(lock.read_text())['packages']
    if not packages or any(not re.fullmatch('[0-9a-f]{64}',p['sha256']) or type(p['bytes']) is not int or p['bytes']<=0 for p in packages):
        raise ValueError('Invalid archive identity')
    for p in packages:
        f=clean_path(intake/(p['sha256']+'.deb'))
        if not f.is_file() or f.stat().st_size != p['bytes'] or sha(f)!=p['sha256']:
            raise ValueError('Missing/changed archive: '+p['package'])
        control=run(['dpkg-deb','-f',f,'Package','Version','Architecture'],capture_output=True,text=True).stdout
        fields=dict(line.split(': ',1) for line in control.splitlines())
        if fields!={'Package':p['package'],'Version':p['version'],'Architecture':p['architecture']}:raise ValueError('Archive control differs from lock')
    if not a.execute:return dict(execute=False,stage='assemble',packages=len(packages),work=str(work))
    private(); work.mkdir(parents=True,mode=0o700);root=work/'rootfs';root.mkdir()
    # Populate the entire dependency closure before executing maintainer scripts.
    # dpkg subsequently unpacks and configures the same archives to own all metadata.
    for name in ('bin','sbin','lib'):
        (root/'usr'/name).mkdir(parents=True,exist_ok=True);(root/name).symlink_to('usr/'+name)
    for p in packages:run(['dpkg-deb','--extract',intake/(p['sha256']+'.deb'),root])
    for name in ('run','tmp','dev','proc','sys','var/lib/dpkg/updates'):(root/name).mkdir(parents=True,exist_ok=True)
    write(root/'var/lib/dpkg/status','')
    write(root/'usr/sbin/policy-rc.d','#!/bin/sh\nexit 101\n',0o755)
    mounts=[]
    def mount(args,target):run(args);mounts.append(target)
    try:
        for name in ('run','tmp','dev'):
            mount(['mount','-t','tmpfs','-o','size=256m,nosuid','tmpfs',root/name],root/name)
        mount(['mount','-t','proc','proc',root/'proc'],root/'proc')
        for name,major,minor in [('null',1,3),('zero',1,5),('random',1,8),('urandom',1,9)]:
            run(['mknod','-m','666',root/'dev'/name,'c',major,minor])
        (root/'run/debs').mkdir()
        mount(['mount','--bind',intake,root/'run/debs'],root/'run/debs')
        run(['mount','-o','remount,bind,ro',root/'run/debs'])
        env=dict(os.environ,DEBIAN_FRONTEND='noninteractive',LC_ALL='C',SOURCE_DATE_EPOCH=str(EPOCH))
        with (work/'dpkg.log').open('w') as log:
            run(['chroot',root,'dpkg','--force-depends','--unpack',*['/run/debs/'+p['sha256']+'.deb' for p in packages]],env=env,stdout=log,stderr=subprocess.STDOUT)
            write(root/'etc/initramfs-tools/update-initramfs.conf','update_initramfs=no\nbackup_initramfs=no\n')
            run(['chroot',root,'dpkg','--force-confold','--configure','-a'],env=env,stdout=log,stderr=subprocess.STDOUT)
        result=run(['chroot',root,'dpkg','--audit'],capture_output=True,text=True)
        write(work/'dpkg-audit.txt',result.stdout+result.stderr)
        if result.stdout or result.stderr:raise ValueError('dpkg audit is not clean')
        installed=run(['chroot',root,'dpkg-query','-W','-f=${Package}\t${Version}\t${db:Status-Status}\n'],capture_output=True,text=True).stdout
        write(work/'installed-packages.tsv',installed)
        expected={(p['package'],p['version'],'installed') for p in packages}
        if {tuple(line.split('\t')) for line in installed.splitlines()}!=expected:raise ValueError('Installed closure differs')
        imports=run(['chroot',root,'python3','-c',"import gi,sqlite3,tarfile,ctypes; gi.require_version('Gtk','3.0'); from gi.repository import Gtk,Gdk,GLib,Atk; import cairo; print(Gtk.get_major_version())"],capture_output=True,text=True)
        write(work/'imports.txt',imports.stdout+imports.stderr)
    finally:
        for target in reversed(mounts):run(['umount',target])
    # Fixed appliance identity and no account, persistent state or networking.
    write(root/'etc/machine-id','22b4cce916f7480c96d96e970828c018\n')
    write(root/'etc/hostname','sv08-recovery-vm\n')
    write(root/'etc/hosts','127.0.0.1 localhost\n::1 localhost\n')
    write(root/'etc/fstab','')
    write(root/'etc/default/locale','LANG=C.UTF-8\n')
    write(root/'etc/sv08-recovery-image','Independent offline recovery diagnostics; no media preparer\n')
    runtime=root/'usr/lib/sv08';runtime.mkdir(parents=True,exist_ok=True)
    for p in (REPO/'runtime').glob('*.py'):shutil.copyfile(p,runtime/p.name)
    from stage_admin_ui import stage
    stage(work,'recovery',True)
    units=root/'etc/systemd/system';units.mkdir(parents=True,exist_ok=True)
    write(units/'sv08-recovery-display.service.d/independent.conf','[Unit]\nWants=systemd-udev-settle.service\nConditionPathExists=/run/sv08/recovery-verified\n[Service]\nEnvironment=HOME=/run/recovery-home\nEnvironment=LANG=C.UTF-8\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nEnvironment=LIBGL_ALWAYS_SOFTWARE=1\nEnvironment=XDG_CACHE_HOME=/run/recovery-home/cache\nEnvironment=XDG_RUNTIME_DIR=/run/recovery-home\n')
    # Exact image uses a focused boot target, eliminating unrelated boot jobs.
    write(units/'sv08-recovery.target','[Unit]\nDescription=Independent recovery diagnostic target\nRequires=sysinit.target basic.target dbus.service sv08-recovery-display.service\nWants=sv08-recovery-report.service\nAfter=sysinit.target basic.target\nAllowIsolate=yes\n')
    write(units/'sv08-recovery-report.service','[Unit]\nDescription=Read-only recovery startup report\nAfter=sv08-recovery-display.service\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /usr/lib/sv08/sv08_recovery_boot_report.py\nStandardOutput=journal+console\nTimeoutStartSec=45\n')
    p=units/'default.target';p.unlink(missing_ok=True);p.symlink_to('sv08-recovery.target')
    for name in ('systemd-remount-fs.service','systemd-machine-id-commit.service','systemd-random-seed.service','systemd-pstore.service','systemd-update-utmp.service','systemd-update-utmp-runlevel.service','systemd-journal-flush.service','getty.target','serial-getty@ttyAMA0.service','console-getty.service','systemd-networkd.service','systemd-networkd.socket','systemd-resolved.service','e2scrub_all.timer','e2scrub_reap.service','fstrim.timer','dpkg-db-backup.timer','dpkg-db-backup.service','systemd-hostnamed.socket','systemd-hostnamed.service'):
        p=units/name;p.unlink(missing_ok=True);p.symlink_to('/dev/null')
    write(units/'systemd-tmpfiles-setup.service.d/recovery.conf','[Service]\nExecStart=\nExecStart=systemd-tmpfiles --create --remove --boot --prefix=/run --prefix=/tmp --prefix=/var/log --prefix=/var/cache --prefix=/var/lib/systemd --prefix=/var/lib/dbus\n')
    write(root/'etc/systemd/journald.conf.d/recovery.conf','[Journal]\nStorage=volatile\nRuntimeMaxUse=16M\nForwardToConsole=yes\n')
    # /var writes are volatile under /run; /etc, root and /usr remain read-only.
    for name in ('log','tmp','cache','lib/systemd','lib/dbus'):
        p=root/'var'/name
        if p.is_symlink() or p.is_file():p.unlink()
        elif p.exists():shutil.rmtree(p)
        p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to('/run/recovery-var/'+name)
    write(root/'etc/X11/xorg.conf.d/10-recovery-vm.conf','Section "Device"\n Identifier "virtio"\n Driver "modesetting"\n Option "AccelMethod" "none"\nEndSection\n')
    # Keep every package runtime, translation, manual and copyright file.
    # Exclude only generated machine/runtime state and the unused generated initrd.
    for p in (root/'boot').glob('initrd.img*'):p.unlink()
    for name in ('initrd.img','initrd.img.old'):
        (root/name).unlink(missing_ok=True)
    (root/'initrd.img').symlink_to('boot/initrd-recovery.img')
    copyrights={}
    def candidate_path(relative):
        parts=list(Path(relative).parts);resolved=[];links=0
        while parts:
            part=parts.pop(0)
            if part in ('','/','.'):continue
            if part=='..':
                if not resolved:raise ValueError('License path escapes root')
                resolved.pop();continue
            item=root.joinpath(*resolved,part)
            if item.is_symlink():
                links+=1
                if links>40:raise ValueError('License symlink cycle')
                target=Path(os.readlink(item))
                if target.is_absolute():resolved=[]
                parts=list(target.parts)+parts
            else:resolved.append(part)
        return root.joinpath(*resolved)
    for p in packages:
        relative=Path('usr/share/doc')/p['package']/'copyright';doc=candidate_path(relative)
        if not doc.is_file():raise ValueError('Missing package copyright: '+p['package'])
        text=doc.read_text(errors='replace')
        refs=sorted(set(re.findall(r'/usr/share/common-licenses/([A-Za-z0-9.+_-]+)',text)))
        common={}
        for name in refs:
            license_path=candidate_path('usr/share/common-licenses/'+name)
            if license_path.is_file():common[name]=sha(license_path)
            else:common[name]='textual-reference-not-a-shipped-filename'
        copyrights[p['package']]=dict(path=str(relative),resolved_path=str(doc.relative_to(root)),sha256=sha(doc),common_license_references=common)
    write(work/'copyrights.json',json.dumps(copyrights,indent=2)+'\n')
    if integration_inputs()!=inputs or sha(lock)!=lock_hash:raise ValueError('Integration inputs changed during assembly')
    write(work/'assembly.json',json.dumps(dict(lock_sha256=lock_hash,root=inventory(root),integration_inputs=inputs),indent=2)+'\n')
    return dict(stage='assemble',packages=len(packages),root=str(root))


def initramfs(root, output, profile=None):
    initroot=output.parent/'initramfs-tree'
    if initroot.exists():raise ValueError('Fresh initramfs tree required')
    initroot.mkdir()
    for name in ('bin','sbin','proc','sys','dev','run','newroot','usr/lib/modules'):(initroot/name).mkdir(parents=True,exist_ok=True)
    shutil.copyfile(root/'usr/bin/busybox',initroot/'bin/busybox');(initroot/'bin/busybox').chmod(0o755)
    for name in ['sh','mount','umount','mkdir','cat','sleep','switch_root','sha256sum','stat','readlink','modprobe','losetup','grep','awk','wc','cut','tr','sync','reboot']:(initroot/'bin'/name).symlink_to('busybox')
    (initroot/'lib').symlink_to('usr/lib')
    (initroot/'sbin/modprobe').symlink_to('../bin/busybox')
    os.mknod(initroot/'dev/null',stat.S_IFCHR|0o666,os.makedev(1,3))
    os.mknod(initroot/'dev/console',stat.S_IFCHR|0o600,os.makedev(5,1))
    for name in ('usr/sbin/blkid','usr/lib/aarch64-linux-gnu/libblkid.so.1','usr/lib/aarch64-linux-gnu/libc.so.6','usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1'):
        target=initroot/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/name,target);target.chmod(0o755)
    (initroot/'usr/lib/ld-linux-aarch64.so.1').symlink_to('aarch64-linux-gnu/ld-linux-aarch64.so.1')
    (initroot/'sbin/blkid').symlink_to('../usr/sbin/blkid')
    kernel=profile['kernel_release'] if profile else KERNEL
    moddir=Path('usr/lib/modules')/kernel
    (initroot/moddir).mkdir(parents=True,exist_ok=True)
    needed=set()
    modules=('ext4','loop','squashfs') if profile else ('ext4','loop','squashfs','virtio_pci','virtio_blk','virtio_mmio')
    for module in modules:
        result=run(['modprobe','-d',root,'-S',kernel,'--show-depends',module],capture_output=True,text=True).stdout
        if not any(line.startswith(('insmod ','builtin ')) for line in result.splitlines()):raise ValueError('Missing early module: '+module)
        for line in result.splitlines():
            if line.startswith('insmod '):needed.add(Path(line.split()[1]).relative_to(root))
    for p in needed:
        (initroot/p).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/p,initroot/p)
    for p in (root/moddir).glob('modules.*'):
        if p.is_file():shutil.copyfile(p,initroot/moddir/p.name)
    if profile:
        help_text=run(['chroot',root,'/usr/bin/busybox','blockdev','--help'],capture_output=True,text=True)
        if not all(flag in help_text.stdout+help_text.stderr for flag in ('--setro','--getro')):raise ValueError('Busybox lacks partition protection')
    write(initroot/'init',boot_gate(profile),0o755)
    for p in [initroot,*initroot.rglob('*')]:os.utime(p,(EPOCH,EPOCH),follow_symlinks=False)
    names=sorted(str(p.relative_to(initroot)) for p in initroot.rglob('*'))
    cpio=run(['cpio','--null','-o','--format=newc','--reproducible','--owner=0:0'],cwd=initroot,input=('\0'.join(['.',*names])+'\0').encode(),capture_output=True).stdout
    with output.open('wb') as f:
        with gzip.GzipFile(filename='',mode='wb',compresslevel=9,mtime=EPOCH,fileobj=f) as g:g.write(cpio)
    write(output.parent/'initramfs-modules.json',json.dumps(sorted(str(p) for p in needed),indent=2)+'\n')
    shutil.rmtree(initroot)


def prepare_derived_runtime(root):
    # The authoritative recovery root redirects these paths into volatile /run.
    # Populate their targets after mounting the private runtime, before dpkg or
    # mkinitramfs opens /var/log or creates /var/tmp/mkinitramfs_*.
    for relative in ('log','tmp','cache','lib/systemd','lib/dbus'):
        target=root/'run/recovery-var'/relative
        target.mkdir(parents=True,exist_ok=True)
        target.chmod(0o1777 if relative=='tmp' else 0o755)


def select_upstream_regdb(root):
    target='/lib/firmware/regulatory.db-upstream'
    # The offline recovery closure currently has no wireless-regdb package.
    # Never silently resolve/install another package to make this choice exist.
    if not (root/'usr/lib/firmware/regulatory.db-upstream').is_file():
        return dict(status='not-installed',selected=False)
    query=run(['chroot',root,'update-alternatives','--query','regulatory.db'],capture_output=True,text=True).stdout
    if 'Alternative: '+target not in query.splitlines():raise ValueError('Upstream regulatory database is not registered')
    run(['chroot',root,'update-alternatives','--set','regulatory.db',target])
    query=run(['chroot',root,'update-alternatives','--query','regulatory.db'],capture_output=True,text=True).stdout
    if 'Value: '+target not in query.splitlines():raise ValueError('Upstream regulatory database selection failed')
    return dict(status='selected-upstream',selected=True,sha256=sha(root/'usr/lib/firmware/regulatory.db-upstream'))


def normalize_board_module_directory(root, profile):
    """Normalize only the shared package directory, then require exact inventory.

    The two reviewed packages share this directory with 0755/0775 metadata.
    dpkg's installation order can retain either. The reviewed installed artifact
    uses 0755. No file bytes, child metadata or generated depmod files are exempt.
    """
    item=profile['artifacts']['modules'];directory=clean_path(root/item['path'])
    before=inventory(directory);mode=stat.S_IMODE(directory.stat().st_mode)
    if mode not in (0o755,0o775):raise ValueError('Unexpected shared module directory mode')
    try:
        directory.chmod(0o755)
        after=inventory(directory)
        if after['sha256']!=item['inventory_sha256']:raise ValueError('Module inventory differs beyond reviewed directory mode')
    except BaseException:
        directory.chmod(mode)
        raise
    return dict(path=item['path'],before_mode=oct(mode),after_mode='0o755',before=before,after=after,exact_reviewed_inventory=True)


def derive(a):
    """Install the reviewed board pair into a private COPY, never the source."""
    inputs=integration_inputs();profile=board_profile(a.board_profile)
    if profile is None:raise ValueError('Derivation requires a board profile')
    source=clean_path(a.assembly);work=clean_path(a.work,output=True);packages=clean_path(a.packages)
    separate(work,source,packages)
    if work.exists():raise ValueError('Derivation requires a fresh output')
    original=clean_path(source/'rootfs');receipt=clean_path(source/'assembly.json')
    receipt_hash=sha(receipt);recorded=json.loads(receipt.read_text());before=inventory(original)
    if before!=recorded['root']:raise ValueError('Assembly source changed since completion')
    for package in profile['packages']:
        archive=clean_path(packages/package['filename'])
        if not archive.is_file() or archive.stat().st_size!=package['bytes'] or sha(archive)!=package['sha256']:raise ValueError('Missing/changed board package')
        control=run(['dpkg-deb','-f',archive,'Package','Architecture'],capture_output=True,text=True).stdout
        if dict(line.split(': ',1) for line in control.splitlines())!={'Package':package['filename'].split('_')[0],'Architecture':'arm64'}:raise ValueError('Unexpected package control')
    if not a.execute:return dict(stage='derive',execute=False,source=before,board_profile=profile)
    private();work.mkdir(parents=True,mode=0o700);root=work/'rootfs'
    run(['cp','-a',original,root])
    shutil.copyfile(receipt,work/'parent-assembly.json')
    mounts=[]
    try:
        for name in ('run','tmp','dev'):
            run(['mount','-t','tmpfs','-o','size=256m,nosuid','tmpfs',root/name]);mounts.append(root/name)
        prepare_derived_runtime(root)
        run(['mount','-t','proc','proc',root/'proc']);mounts.append(root/'proc')
        for name,major,minor in [('null',1,3),('zero',1,5),('random',1,8),('urandom',1,9)]:run(['mknod','-m','666',root/'dev'/name,'c',major,minor])
        (root/'run/debs').mkdir()
        # Expose only checked archives, not the package directory or host devices.
        for package in profile['packages']:
            staged=root/'run/debs'/package['filename']
            shutil.copyfile(packages/package['filename'],staged)
            if staged.stat().st_size!=package['bytes'] or sha(staged)!=package['sha256']:raise ValueError('Changed staged board package')
        write(root/'etc/initramfs-tools/update-initramfs.conf','update_initramfs=no\nbackup_initramfs=no\n')
        write(root/'usr/sbin/policy-rc.d','#!/bin/sh\nexit 101\n',0o755)
        env=dict(os.environ,DEBIAN_FRONTEND='noninteractive',LC_ALL='C',SOURCE_DATE_EPOCH=str(EPOCH))
        with (work/'dpkg.log').open('w') as log:
            run(['chroot',root,'dpkg','--force-confold','--install',*['/run/debs/'+p['filename'] for p in profile['packages']]],env=env,stdout=log,stderr=subprocess.STDOUT)
        regulatory=select_upstream_regdb(root)
        audit=run(['chroot',root,'dpkg','--audit'],capture_output=True,text=True)
        if audit.stdout or audit.stderr:raise ValueError('Derived dpkg audit is not clean')
        write(work/'dpkg-audit.txt',audit.stdout+audit.stderr)
        write(work/'installed-packages.tsv',run(['chroot',root,'dpkg-query','-W','-f=${Package}\t${Version}\t${db:Status-Status}\n'],capture_output=True,text=True).stdout)
    finally:
        for target in reversed(mounts):run(['umount',target])
        after=inventory(original)
        write(work/'parent-preservation.json',json.dumps(dict(before=before,after=after,preserved=before==after,assembly_sha256=sha(receipt)),indent=2)+'\n')
        if after!=before or sha(receipt)!=receipt_hash or sha(work/'parent-assembly.json')!=receipt_hash:raise ValueError('Authoritative parent changed during derivation')
    module_normalization=normalize_board_module_directory(root,profile)
    check_board_artifacts(root,profile)
    # update_initramfs=no suppresses updates, not the kernel postinst's create.
    # Let the shipped postinst finish normally, then omit its unused generated
    # initrd: the separately built, reviewed recovery gate is the boot artifact.
    generated=root/'boot'/('initrd.img-'+profile['kernel_release'])
    if generated.exists():
        if generated.is_symlink() or not generated.is_file():raise ValueError('Unexpected generated initramfs identity')
        generated.unlink()
    recovery_link=root/'initrd.img'
    if recovery_link.is_symlink():recovery_link.unlink()
    elif recovery_link.exists():raise ValueError('Unexpected recovery initrd link identity')
    recovery_link.symlink_to('boot/initrd-recovery.img')
    # Existing generic modesetting/no-acceleration policy is retained; name is
    # descriptive only. Both kernel versions stay package-owned in the copy.
    write(root/'etc/hostname','sv08-recovery\n')
    record=dict(root=inventory(root),board_profile=profile,parent_assembly_sha256=sha(receipt),parent_root=before,parent_preserved=True,integration_inputs=inputs,regulatory_database=regulatory,module_directory_normalization=module_normalization)
    if integration_inputs()!=inputs:raise ValueError('Integration inputs changed during derivation')
    write(work/'assembly.json',json.dumps(record,indent=2)+'\n')
    return dict(stage='derive',root=str(root),parent_preserved=True)


def build(a):
    inputs=integration_inputs()
    work=clean_path(a.work,output=True); source=clean_path(a.assembly);separate(work,source)
    root=clean_path(source/'rootfs')
    profile=board_profile(getattr(a,'board_profile',None))
    kernel=profile['kernel_release'] if profile else KERNEL
    if not root.is_dir() or not (source/'assembly.json').is_file():raise ValueError('Complete assembly required')
    for name in ['usr','boot','boot/vmlinuz-'+kernel,'usr/bin/busybox']:
        clean_path(root/name)
    recorded=json.loads((source/'assembly.json').read_text())
    if work.exists():raise ValueError('Build requires a fresh output')
    if not a.execute:return dict(execute=False,stage='build',work=str(work),bytes=SIZE)
    private()
    before=inventory(root)
    if before != recorded['root']:raise ValueError('Assembly source changed since completion')
    if profile:
        if recorded.get('board_profile')!=profile:raise ValueError('Assembly was not derived for this board profile')
        check_board_artifacts(root,profile)
    work.mkdir(parents=True,mode=0o700)
    envelope=work/'envelope';envelope.mkdir()
    for p in root.iterdir():
        target=envelope/p.name
        if p.name=='usr':target.mkdir();continue
        if p.is_symlink():target.symlink_to(os.readlink(p))
        elif p.is_dir():run(['cp','-a',p,target])
        elif p.is_file():run(['cp','-a',p,target])
    reuse=getattr(a,'reuse_usr',None)
    if reuse:
        reuse=clean_path(reuse);separate(work,reuse)
        cached=json.loads((reuse/'build.json').read_text());image=clean_path(reuse/'envelope/usr.squashfs')
        if cached['source']!=before or sha(image)!=cached['usr_sha256']:raise ValueError('Compressed cache differs from source')
        run(['cp','-a',image,envelope/'usr.squashfs'])
        write(work/'squashfs.log','Hash-verified identical source compressed cache: '+str(reuse)+'\n')
    else:
        with (work/'squashfs.log').open('w') as log:
            run(['mksquashfs',root/'usr',envelope/'usr.squashfs','-noappend','-comp','xz','-b','1M','-processors','2','-mem','256M','-all-time',str(EPOCH),'-mkfs-time',str(EPOCH)],stdout=log,stderr=subprocess.STDOUT)
    (envelope/'boot').mkdir(exist_ok=True)
    initramfs(root,envelope/'boot/initrd-recovery.img',profile)
    usr=envelope/'usr.squashfs'
    # Line-oriented fixed manifest is parseable by the self-contained busybox gate.
    manifest=f'format=sv08-recovery-usr-v1\nroot_uuid={UUID}\nroot_bytes={SIZE}\nusr_path=/usr.squashfs\nusr_bytes={usr.stat().st_size}\nusr_sha256={sha(usr)}\n'
    write(envelope/'etc/sv08/recovery-envelope.manifest',manifest)
    for p in [envelope,*envelope.rglob('*')]:os.utime(p,(EPOCH,EPOCH),follow_symlinks=False)
    disk=work/'recovery.ext4'
    with disk.open('xb') as f:f.truncate(SIZE)
    run(['mkfs.ext4','-q','-F','-b','4096','-I','256','-m','0','-U',UUID,'-L','SV08_RECOVERY','-E','lazy_itable_init=0,lazy_journal_init=0,hash_seed='+UUID,'-d',envelope,disk],env=dict(os.environ,E2FSPROGS_FAKE_TIME=str(EPOCH)))
    fsck=run(['e2fsck','-fn',disk],capture_output=True,text=True)
    write(work/'fsck.txt',fsck.stdout+fsck.stderr)
    usage=run(['dumpe2fs','-h',disk],capture_output=True,text=True).stdout
    write(work/'filesystem.txt',usage)
    for source_path,name in [(envelope/'boot'/('vmlinuz-'+kernel),'vmlinuz'),(envelope/'boot/initrd-recovery.img','initrd.img')]:shutil.copyfile(source_path,work/name)
    after=inventory(root)
    if before!=after:raise ValueError('Assembly source changed during build')
    result=dict(format_version=1,status='offline-vm-candidate',image_bytes=SIZE,image_sha256=sha(disk),allocated_bytes=disk.stat().st_blocks*512,manifest_sha256=hashlib.sha256(manifest.encode()).hexdigest(),usr_bytes=usr.stat().st_size,usr_sha256=sha(usr),source=before,source_preserved=before==after,kernel_sha256=sha(work/'vmlinuz'),initrd_sha256=sha(work/'initrd.img'),envelope=inventory(envelope),boot_gate_sha256=sha(REPO/'configs/host-os/recovery-init'),builder_sha256=sha(Path(__file__)),assembly_record_sha256=sha(source/'assembly.json'))
    if integration_inputs()!=inputs:raise ValueError('Integration inputs changed during build')
    result['integration_inputs']=inputs
    if profile:
        result.update(status='offline-board-candidate',board_profile=profile,boot_gate_sha256=hashlib.sha256(boot_gate(profile).encode()).hexdigest())
    write(work/'build.json',json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['intake','assemble','derive','build'])
    p.add_argument('--work',type=Path,required=True);p.add_argument('--execute',action='store_true')
    p.add_argument('--intake',type=Path);p.add_argument('--lock',type=Path,default=REPO/'configs/host-os/recovery-packages.json');p.add_argument('--assembly',type=Path);p.add_argument('--reuse-usr',type=Path)
    p.add_argument('--board-profile',type=Path);p.add_argument('--packages',type=Path)
    a=p.parse_args();print(json.dumps(globals()[a.stage](a),indent=2))
if __name__=='__main__':main()
