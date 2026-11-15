#!/usr/bin/env python3
"""Coordinator-executed regular-file installed stack fixture; never deployable.

Recipe (each role returns JSON evidence): prepare, stage the current production
integration/UI with its generated public owner key, stage, provision through a
private ARM64 chroot, build-normal, build-data --state restored, build-archive
(empty), command --role normal --expected restored; inspect guest/browser PASS
and power off. Mount only that regular data image read-only, export-source,
then rebuild that same data disk from previous state with --replace recorded,
build-archive --replace. Build current recovery with restore-profile.json.
Recovery command -> guest --phase restore then --phase activate; normal boot
restored + browser; a distinct normal reboot restored + browser; recovery
rollback; normal previous + browser. Preserve every result and failure.

Root/image/VM/chroot execution belongs to the coordinator, not unit checks.
All UUIDs/MACs below describe disposable QEMU devices, never printer facts.
"""
import argparse
from contextlib import contextmanager
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'runtime'),str(Path(__file__).parent)]
from recovery_restore_stack import MARKER, MAC, BOOTSTRAP_FILES, private_fixture, require, sha, write_json
from recovery_export_vm import partition_image, gpt, embed, media, part, identity, stable_key, LINUX_GUID, FAT_GUID, RECOVERY_BYTES, RECOVERY_UUID, _unpack_initrd, run
from recovery_restore_e2e_vm import TARGET_UUID, TARGET_PARTUUID, NORMAL_ROOT_PARTUUID, BOOT_PARTUUID, BOOT_UUID

REPO=Path(__file__).resolve().parents[1]
START=2048
DATA_BYTES=1536*1024**2
ARCHIVE_BYTES=256*1024**2
NORMAL_BYTES=768*1024**2
BOOT_BYTES=64*1024**2
ARCHIVE_UUID='7e25af9a-f646-4bc8-bd63-2884902365fa'
ARCHIVE_PARTUUID='a223ce55-fc0e-4933-a522-f19c769cd870'
KERNEL='6.12.107+deb13-arm64'


def regular(path):
    path=Path(path).absolute()
    require(all(not p.is_symlink() for p in (path,*path.parents)), 'Real fixture paths required')
    info=path.stat(); require(stat.S_ISREG(info.st_mode) and info.st_nlink==1,'Single-link regular fixture required')
    return path


def prepare(work, release):
    work=Path(work).absolute()
    require(not work.exists() and work.parent.stat().st_uid==os.geteuid() and
            stat.S_IMODE(work.parent.stat().st_mode)==0o700,'Fresh work beneath private owned parent required')
    require(all(not p.is_symlink() for p in work.parents),'No fixture ancestry links')
    manifest=json.loads(regular(release).read_text()); require(manifest.get('deployable') is False,'Nondeployable release required')
    work.mkdir(mode=0o700); (work/'disposable-marker').write_text(MARKER)
    credentials={'owner':dict(username='sv08',password=__import__('secrets').token_urlsafe(32))}
    write_json(work/'credentials.json',credentials)
    subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(work/'owner-key')],check=True,timeout=20)
    release_value={**manifest,'devices':{
        'root-a':'/dev/disk/by-partuuid/'+NORMAL_ROOT_PARTUUID,'data':'/dev/disk/by-partuuid/'+TARGET_PARTUUID,
        'boot-a':'/dev/disk/by-partuuid/'+BOOT_PARTUUID,
        'root-b':'/dev/disk/by-partuuid/0b20b8a1-cac2-4ff3-a2e6-f9e802214824',
        'boot-b':'/dev/disk/by-partuuid/cf648ae0-d2c7-4c59-820c-561a858b7a9c',
        'recovery':'/dev/disk/by-partuuid/0b20b8a1-cac2-4ff3-a2e6-f9e802214825'}}
    write_json(work/'release.json',release_value)
    write_json(work/'prepare.json',dict(format_version=1,deployable=False,input_release_sha256=sha(release),
        data_bytes=DATA_BYTES,normal_bytes=NORMAL_BYTES,archive_bytes=ARCHIVE_BYTES,mac=MAC,
        pam_password_scope='synthetic paired immutable OS only; not in exported user data',physical_hardware=False))
    (work/'archive-tree').mkdir(mode=0o700)
    return release_value


def installed_root(rootfs):
    rootfs=Path(rootfs).absolute()
    require(rootfs == REPO/'build/recovery-stack-assembly/rootfs' and
            all(not path.is_symlink() for path in (rootfs,*rootfs.parents)),
            'Only the assigned derived installed root is writable')
    return rootfs


def stage(rootfs, fixture):
    fixture=private_fixture(fixture); rootfs=installed_root(rootfs)
    require(os.geteuid()==0 and rootfs.is_dir() and not rootfs.is_symlink(),'Private root fixture stage required')
    runtime=rootfs/'usr/lib/sv08'; require((runtime/'sv08_boot.py').is_file(),'Stage current production integration first')
    require(json.loads((runtime/'release.json').read_text())==json.loads((fixture/'release.json').read_text()),'Installed fixture release differs')
    account=[line.split(':') for line in (rootfs/'etc/passwd').read_text().splitlines() if line.startswith('sv08:')]
    require(len(account)==1 and account[0][2:4]==['1000','1000'],'Exact native owner UID/GID required')
    credentials=json.loads((fixture/'credentials.json').read_text())['owner']
    subprocess.run(['chroot',str(rootfs),'chpasswd'],input='sv08:'+credentials['password']+'\n',text=True,check=True,timeout=20,capture_output=True)
    subprocess.run(['chroot',str(rootfs),'usermod','-aG','sudo','sv08'],check=True,timeout=20,capture_output=True)
    subprocess.run(['chroot',str(rootfs),'passwd','-l','root'],check=True,timeout=20,capture_output=True)
    # Delete inherited host key artifacts by name without reading their bytes.
    for path in (rootfs/'etc/ssh').glob('ssh_host_*'): path.unlink()
    shutil.copyfile(Path(__file__).with_name('recovery_restore_stack.py'),runtime/'recovery_restore_stack.py')
    (runtime/'stack-disposable').write_text(MARKER)
    # One immutable userspace serves bootstrap and all qualification boots.
    # The public, source-bound expectations accompany each data-tree parent.
    expectations=runtime/'stack-expectations.json'
    if expectations.is_symlink():
        require(os.readlink(expectations)=='/data/stack-expectations.json','Unexpected fixture expectations link')
    else:
        expectations.unlink(missing_ok=True); expectations.symlink_to('/data/stack-expectations.json')
    bootstrap=runtime/'stack-bootstrap'; bootstrap.mkdir(mode=0o700,exist_ok=True)
    require(not bootstrap.is_symlink() and bootstrap.stat().st_uid==0,'Real root-owned bootstrap directory required')
    bootstrap.chmod(0o700)
    require(set(path.name for path in bootstrap.iterdir()) <= set(BOOTSTRAP_FILES),'Unexpected bootstrap assets preserved')
    for name in BOOTSTRAP_FILES:
        source=regular(fixture/name); info=source.stat()
        require(info.st_uid==0 and not info.st_mode & 0o022,'Known root-owned generated fixture assets required')
        destination=bootstrap/name
        require(not destination.is_symlink(),'Bootstrap destination link refused')
        shutil.copyfile(source,destination); destination.chmod(0o600); os.chown(destination,0,0)
    units=rootfs/'etc/systemd/system'
    default=units/'default.target';default.unlink(missing_ok=True);default.symlink_to('multi-user.target')
    # Keep original service commands/physical conditions. Only failure reboot is
    # suppressed in this diagnostic guest so a failed gate remains inspectable.
    dropin=units/'sv08-prepare.service.d';dropin.mkdir(exist_ok=True)
    (dropin/'stack-fixture.conf').write_text('[Unit]\nFailureAction=none\n')
    unit=units/'sv08-stack-assert.service'
    unit.write_text('[Unit]\nDescription=Disposable full installed stack assertions\nConditionKernelCommandLine=!sv08.stack.bootstrap=1\nAfter=sv08-mainsail.service NetworkManager.service cockpit.socket ssh.service\n[Service]\nType=oneshot\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nExecStart=/usr/bin/python3 /usr/lib/sv08/recovery_restore_stack.py --phase normal-assert --disposable-marker /usr/lib/sv08/stack-disposable\nTimeoutStartSec=600\nRemainAfterExit=yes\nStandardOutput=journal+console\nStandardError=journal+console\n[Install]\nWantedBy=multi-user.target\n')
    subprocess.run(['systemctl','--root',str(rootfs),'enable','NetworkManager.service','ssh.service','cockpit.socket','sv08-stack-assert.service'],check=True,timeout=20,capture_output=True)
    return dict(staged=True,deployable=False,pam_scope='paired immutable synthetic OS',runtime_sha256=sha(runtime/'recovery_restore_stack.py'))


def profile(fixture):
    boot=json.loads((fixture/'stack-expectations.json').read_text())['boot']
    recovery={'serial':'SV08-RECOVERY'}; archive={'device/wwid':'naa.5000000000000001'}; target={'device/wwid':'naa.5000000000000003'}
    sectors=lambda size:(size-4*1024**2)//512
    topology=[media(recovery,RECOVERY_BYTES//512,False,'virtio',[],'ext4',RECOVERY_UUID),
        media(archive,ARCHIVE_BYTES//512,False,'scsi',[part(1,START,sectors(ARCHIVE_BYTES),ARCHIVE_UUID,'ext4',ARCHIVE_PARTUUID)]),
        media(target,DATA_BYTES//512,False,'scsi',[part(1,START,sectors(DATA_BYTES),TARGET_UUID,'ext4',TARGET_PARTUUID)]),
        media({'device/wwid':'naa.5000000000000004'},BOOT_BYTES//512,False,'scsi',[part(1,START,sectors(BOOT_BYTES),BOOT_UUID,'vfat',BOOT_PARTUUID)])]
    archive_mount='/run/sv08-recovery/archives/backup'; target_mount='/run/sv08-recovery/targets/target'
    return dict(recovery=identity(recovery,0,0,RECOVERY_BYTES//512,RECOVERY_UUID),recovery_path='/',media=sorted(topology,key=stable_key),boot=boot,
        archives={'backup':dict(label='Synthetic booted source archive',mount=archive_mount,path=archive_mount+'/backup.tar',identity=identity(archive,1,START,sectors(ARCHIVE_BYTES),ARCHIVE_UUID))},
        targets={'target':dict(label='Disposable paired data',mount=target_mount,root=target_mount+'/restored',fresh_root=target_mount+'/fresh',identity=identity(target,1,START,sectors(DATA_BYTES),TARGET_UUID))})


def bootstrap_tree(fixture):
    """Seed owned directory metadata only; real PID 1 creates all state/identity."""
    fixture=private_fixture(fixture); tree=fixture/'bootstrap-tree'
    if not tree.exists():
        tree.mkdir(mode=0o700); (tree/'sv08').mkdir(mode=0o700)
    require(not tree.is_symlink() and set(path.name for path in tree.iterdir())=={'sv08'},
            'Bootstrap seed must contain only its real state directory')
    state=tree/'sv08'
    for path in (tree,state):
        info=path.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.geteuid() and
                stat.S_IMODE(info.st_mode)==0o700,'Owned private bootstrap directory metadata required')
    require(not any(state.iterdir()), 'Bootstrap state seed must be empty; preserve existing state')
    return tree


def image(fixture,name,tree,size,fsuuid,partuuid,filesystem='ext4',replace=False):
    fixture=private_fixture(fixture); disk=fixture/(name+'.raw'); old=None
    if disk.exists():
        require(replace,'Image exists; explicit recorded replacement required'); old=sha(regular(disk))
        if name in ('target','archive'):
            export=fixture/'booted-source-export.json'
            require(export.is_file() and (fixture/'archive-tree/backup.tar').is_file(),
                    'Preserve the actual booted source archive before replacing media')
            require(sha(fixture/'archive-tree/backup.tar')==json.loads(export.read_text())['sha256'],
                    'Booted source archive differs from its publication receipt')
    temporary=fixture/(name+'.partition'); require(not temporary.exists(),'Unreconciled partition file retained')
    sectors=(size-4*1024**2)//512
    partition_image(temporary,sectors*512,filesystem,fsuuid,tree)
    try:
        if disk.exists(): disk.unlink()
        gpt(disk,size,[(START,sectors,LINUX_GUID if filesystem=='ext4' else FAT_GUID,partuuid)])
        embed(disk,temporary,START)
    finally: temporary.unlink()
    receipt=dict(name=name,bytes=size,before_sha256=old,sha256=sha(disk),partuuid=partuuid,
                 generated_bytes=size+sectors*512,deployable=False)
    suffix=__import__('uuid').uuid4().hex
    write_json(fixture/(name+'-'+suffix+'.json'),receipt)
    return receipt


def export_source(fixture, source):
    from sv08_export import Export
    fixture=private_fixture(fixture); source=Path(source).absolute()
    expected=sha(fixture/'stack-expectations.json')
    def recheck():
        row=subprocess.check_output(['findmnt','-n','-o','UUID,FSTYPE,OPTIONS','--mountpoint',str(source)],text=True,timeout=5).split()
        require(len(row)==3 and row[0]==TARGET_UUID and row[1]=='ext4' and 'ro' in row[2].split(','),'Actual booted data requires read-only explicit fixture mount')
        require(sha(fixture/'stack-expectations.json')==expected,'Fixture expectations changed')
        receipts=list((source/'stack-receipts').glob('restored-*.json'))
        require(any(json.loads(p.read_text()).get('result')=='PASS' for p in receipts),'Actual provisioned source normal boot receipt required')
    class Guard:
        fingerprint='read-only-booted-source-'+expected
        def recheck(self): recheck()
    @contextmanager
    def admitted(target): recheck(); yield Guard()
    exporter=Export(source,{'archive':dict(path=fixture/'archive-tree')},admitted)
    result=exporter.execute(exporter.prepare('archive'))
    archive=fixture/'archive-tree'/result['filename']; destination=archive.with_name('backup.tar')
    require(not destination.exists(),'Existing booted-source archive preserved')
    archive.rename(destination)
    write_json(fixture/'booted-source-export.json',dict(result,archive_path=str(destination),source_booted=True,
        source_uuid=TARGET_UUID,source_read_only=True,physical_hardware=False))
    write_json(fixture/'restore-profile.json',profile(fixture))
    return result


def normal_initrd(candidate, rootfs, work):
    """PR16 diagnostic gate adaptation with the unchanged current data hook."""
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
    kernel=KERNEL
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
    init=init.replace('1048576',str(NORMAL_BYTES//512)).replace('536870912',str(NORMAL_BYTES))
    (unpack/'init').write_text(init)
    # Extra busybox applets used by the unmodified identity hook and PARTUUID mapping.
    for applet in ('basename','ln'):
        path=unpack/'bin'/applet
        if not path.exists():path.symlink_to('busybox')
    files=sorted(['.',*(str(path.relative_to(unpack)) for path in unpack.rglob('*'))])
    packed=subprocess.run(['cpio','--null','-o','--format=newc','--owner=0:0','--quiet'],cwd=unpack,input=('\0'.join(files)+'\0').encode(),capture_output=True,check=True,timeout=30).stdout
    with gzip.GzipFile(filename='',mode='wb',fileobj=(work/'normal-initrd.img').open('wb'),mtime=0) as stream:stream.write(packed)
    receipt=dict(initrd_sha256=sha(work/'normal-initrd.img'),hook_source_sha256=sha(hook),functions_sha256=sha(scripts/'functions'),diagnostic_adaptation='PR16 normal GPT gate; current unchanged data hook; explicit normal capacity')
    shutil.rmtree(unpack)
    return receipt


def build_normal(fixture,rootfs,candidate,work):
    fixture=private_fixture(fixture); rootfs=installed_root(rootfs); candidate=Path(candidate).absolute(); work=Path(work).absolute()
    require(os.geteuid()==0 and not work.exists(),'Root/fresh normal fixture required')
    require((rootfs/'usr/lib/sv08/stack-disposable').read_text()==MARKER,'Stage full normal fixture first')
    require((rootfs/'usr/lib/modules'/KERNEL).is_dir(),'Matching installed kernel modules required')
    work.mkdir(mode=0o700); envelope=work/'envelope'; envelope.mkdir()
    # The root is an already derived private input, never the historical source.
    # Keep the actual installed /opt venv/source payload in the normal envelope.
    for source in rootfs.iterdir():
        destination=envelope/source.name
        if source.name in ('usr','boot','proc','sys','dev','run','tmp','data'):
            destination.mkdir(); continue
        subprocess.run(['cp','-a',str(source),str(destination)],check=True,timeout=180)
    with (work/'squashfs.log').open('x') as log:
        subprocess.run(['mksquashfs',str(rootfs/'usr'),str(envelope/'usr.squashfs'),'-noappend','-comp','xz','-b','1M','-processors','2','-mem','256M','-all-time','1609459200','-mkfs-time','1609459200'],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    (envelope/'usr.squashfs').chmod(0o644)
    manifest=('format=sv08-recovery-usr-v1\nroot_uuid='+RECOVERY_UUID+'\nroot_bytes='+str(NORMAL_BYTES)+
        '\nusr_path=/usr.squashfs\nusr_bytes='+str((envelope/'usr.squashfs').stat().st_size)+
        '\nusr_sha256='+sha(envelope/'usr.squashfs')+'\n')
    (envelope/'etc/sv08/recovery-envelope.manifest').write_text(manifest)
    partition=work/'normal-root.partition'
    partition_image(partition,NORMAL_BYTES,'ext4',RECOVERY_UUID,envelope)
    gpt(work/'normal-root.raw',NORMAL_BYTES+4*1024**2,[(START,NORMAL_BYTES//512,LINUX_GUID,NORMAL_ROOT_PARTUUID)])
    embed(work/'normal-root.raw',partition,START);partition.unlink()
    initrd=normal_initrd(candidate,rootfs,work)
    receipt=dict(format_version=1,deployable=False,normal_root_sha256=sha(work/'normal-root.raw'),normal_root_bytes=(work/'normal-root.raw').stat().st_size,
        manifest_sha256=hashlib.sha256(manifest.encode()).hexdigest(),usr_sha256=sha(envelope/'usr.squashfs'),
        kernel_sha256=sha(candidate/'vmlinuz'),candidate_initrd_sha256=sha(candidate/'initrd.img'),**initrd)
    write_json(work/'normal-fixture.json',receipt)
    return receipt


def verify_backend(client, execution_backend, argv):
    """Observe active QMP state, never infer activation from generated argv."""
    require(execution_backend in ('tcg','arm64-kvm'),'Known execution backend required')
    version=client.call('query-version')
    try:
        observed=client.call('query-accelerators'); query='query-accelerators'
        require(isinstance(observed,dict) and observed.get('enabled')==('kvm' if execution_backend=='arm64-kvm' else 'tcg'),
                'Active accelerator differs from requested backend')
    except RuntimeError as error:
        payload=error.args[0] if error.args else None
        require(isinstance(payload,dict) and payload.get('error',{}).get('class')=='CommandNotFound',
                'Accelerator query failed; fallback refused')
        observed=client.call('query-kvm');query='query-kvm'
        require(isinstance(observed,dict) and observed.get('enabled') is (execution_backend=='arm64-kvm') and
                (execution_backend!='arm64-kvm' or observed.get('present') is True),'Active accelerator differs from requested backend')
    return dict(execution_backend=execution_backend,active_backend_verified=True,qmp_command=query,
                qmp_observation=observed,qemu_version=version,argv=argv,physical_hardware=False,printing_ready=False)


def kvm_preflight():
    """Initialize the requested native machine with no media or networking."""
    import platform
    require(platform.system()=='Linux' and platform.machine().lower() in ('aarch64','arm64'),
            'arm64-kvm requires a native Linux ARM64 host')
    argv=['qemu-system-aarch64','-machine','virt,gic-version=host','-accel','kvm','-cpu','host',
          '-smp','2','-m','1024','-S','-nodefaults','-nic','none','-display','none','-qmp','stdio']
    request=''.join(json.dumps(dict(execute=cmd))+'\n' for cmd in ('qmp_capabilities','query-status','quit'))
    result=subprocess.run(argv,input=request,text=True,capture_output=True,timeout=15)
    require(result.returncode==0,'Native KVM initialization failed; no TCG fallback')
    responses=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    require(not any('error' in row for row in responses) and any(row.get('return',{}).get('status') in ('prelaunch','paused') for row in responses if isinstance(row.get('return'),dict)),
            'Native KVM initialization was not observed')
    return dict(initialization_verified=True,argv=argv)


def command(candidate,fixture,qmp,normal=None,expected='restored',bootstrap=False,functional_clock=False,execution_backend='tcg'):
    require(execution_backend in ('tcg','arm64-kvm'),'Known execution backend required')
    require(execution_backend!='arm64-kvm' or not functional_clock,'KVM cannot use functional clock/icount')
    fixture=private_fixture(fixture); candidate=Path(candidate).absolute(); qmp=Path(qmp).absolute()
    require(expected in ('previous','restored') and not qmp.exists(),'Valid role and fresh owned QMP endpoint required')
    require(not bootstrap or normal is not None,'Bootstrap requires the complete installed normal image')
    require(not functional_clock or normal is not None,'Functional clock requires the complete installed normal image')
    require(qmp.parent.is_relative_to(fixture) or (normal and qmp.parent.is_relative_to(Path(normal))),'QMP must remain inside assigned fixture')
    build=json.loads((candidate/'build.json').read_text())
    kernel=regular(candidate/'vmlinuz'); initrd=regular(candidate/'initrd.img')
    root=regular(candidate/'recovery.ext4')
    append='console=ttyAMA0 root=/dev/vda ro sv08.envelope='+build['manifest_sha256']+' sv08.recovery='+build['provider_manifest_sha256']+' systemd.debug_shell=ttyAMA0 systemd.mask=serial-getty@ttyAMA0.service systemd.log_target=console'
    if normal:
        normal=Path(normal); receipt=json.loads((normal/'normal-fixture.json').read_text())
        root=regular(normal/'normal-root.raw');initrd=regular(normal/'normal-initrd.img')
        require(sha(root)==receipt['normal_root_sha256'] and sha(initrd)==receipt['initrd_sha256'] and sha(kernel)==receipt['kernel_sha256'],'Normal boot source hashes changed')
        role='sv08.stack.bootstrap=1' if bootstrap else 'sv08.stack.expect='+expected
        append='console=ttyAMA0 root=/dev/vda1 ro rauc.slot=A sv08.envelope='+receipt['manifest_sha256']+' '+role+' systemd.debug_shell=ttyAMA0 systemd.mask=serial-getty@ttyAMA0.service systemd.log_target=console'
    # Opt-in instruction-count time supports bounded software semantics under
    # emulation. It is not H616 timing/performance/CPU-budget qualification.
    accelerator='tcg,thread=single' if functional_clock else 'tcg,thread=multi'
    if execution_backend=='arm64-kvm':accelerator='kvm'
    result=['qemu-system-aarch64','-machine','virt,gic-version=host' if execution_backend=='arm64-kvm' else 'virt','-cpu','host' if execution_backend=='arm64-kvm' else 'cortex-a53','-accel',accelerator,'-smp','2','-m','1024','-kernel',str(kernel),'-initrd',str(initrd),'-append',append,
        '-drive',f'if=none,id=recovery,format=raw,file={root},readonly=on','-device','virtio-blk-pci,drive=recovery,serial=SV08-RECOVERY',
        '-device','virtio-scsi-pci,id=scsi0']
    if functional_clock: result+=['-icount','shift=0,align=off,sleep=off']
    for name,wwn,readonly in (('archive',1,True),('target',3,False),('boot',4,True)):
        image_path=regular(fixture/(name+'.raw'))
        result+=['-drive',f'if=none,id={name},format=raw,file={image_path}'+(',readonly=on' if readonly else ''),
            '-device',f'scsi-hd,drive={name},serial=SV08-{name.upper()},bus=scsi0.0,wwn=0x500000000000000{wwn}']
    if normal:
        result+=['-netdev','user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:19090-:9090,hostfwd=tcp:127.0.0.1:18443-:8443,hostfwd=tcp:127.0.0.1:12222-:22',
                 '-device','virtio-net-pci,netdev=net0,mac='+MAC]
    else: result+=['-nic','none']
    result+=['-display','none','-serial','mon:stdio','-qmp','unix:'+str(qmp)+',server=on,wait=off','-no-reboot']
    if execution_backend=='arm64-kvm':kvm_preflight()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('prepare');q.add_argument('--work',type=Path,required=True);q.add_argument('--release',type=Path,required=True)
    q=sub.add_parser('stage');q.add_argument('--fixture',type=Path,required=True);q.add_argument('--rootfs',type=Path,required=True)
    q=sub.add_parser('build-normal');q.add_argument('--fixture',type=Path,required=True);q.add_argument('--rootfs',type=Path,required=True);q.add_argument('--candidate',type=Path,required=True);q.add_argument('--work',type=Path,required=True)
    for action in ('build-data','build-archive','build-boot'):
        q=sub.add_parser(action);q.add_argument('--fixture',type=Path,required=True);q.add_argument('--replace',action='store_true')
        if action=='build-data':q.add_argument('--state',choices=('previous','restored','bootstrap'),required=True)
    q=sub.add_parser('export-source');q.add_argument('--fixture',type=Path,required=True);q.add_argument('--source-mount',type=Path,required=True)
    q=sub.add_parser('command');q.add_argument('--fixture',type=Path,required=True);q.add_argument('--candidate',type=Path,required=True);q.add_argument('--qmp',type=Path,required=True);q.add_argument('--normal',type=Path);q.add_argument('--expected',choices=('previous','restored'),default='restored');q.add_argument('--bootstrap',action='store_true');q.add_argument('--functional-clock',action='store_true',help='Instruction-count virtual time for semantic/software tests only; no H616 timing/performance/CPU-budget qualification')
    q.add_argument('--execution-backend',choices=('tcg','arm64-kvm'),default='tcg')
    q=sub.add_parser('verify-backend');q.add_argument('--qmp',type=Path,required=True);q.add_argument('--fixture',type=Path,required=True);q.add_argument('--execution-backend',choices=('tcg','arm64-kvm'),required=True);q.add_argument('--argv-json',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.action=='prepare': result=prepare(a.work,a.release)
    elif a.action=='stage':result=stage(a.rootfs,a.fixture)
    elif a.action=='build-normal':result=build_normal(a.fixture,a.rootfs,a.candidate,a.work)
    elif a.action=='export-source':result=export_source(a.fixture,a.source_mount)
    elif a.action=='command':result=command(a.candidate,a.fixture,a.qmp,a.normal,a.expected,a.bootstrap,a.functional_clock,a.execution_backend)
    elif a.action=='verify-backend':
        from recovery_export_vm import QMP
        fixture=private_fixture(a.fixture);require(a.qmp.absolute().parent.is_relative_to(fixture),'Owned QMP endpoint required')
        require(a.output.absolute().parent.is_relative_to(fixture),'Private receipt destination required')
        require(a.argv_json.absolute().is_relative_to(fixture),'Assigned command receipt required')
        for path in (a.qmp.absolute(),a.output.absolute(),a.argv_json.absolute()):
            require(all(not item.is_symlink() for item in (path,*path.parents)),'Real owned QMP/receipt paths required')
        client=QMP(a.qmp)
        try:result=verify_backend(client,a.execution_backend,json.loads(regular(a.argv_json).read_text()))
        finally:client.file.close();client.socket.close()
        write_json(a.output,result)
    else:
        if a.action=='build-data':
            if a.state=='bootstrap':
                require(not a.replace and not (a.fixture/'target.raw').exists(), 'Fresh metadata-only bootstrap data required')
                tree=bootstrap_tree(a.fixture)
            else:
                tree=a.fixture/('target-tree' if a.state=='previous' else 'export-tree')
                # Fixture bookkeeping is a regular public sibling, not a state link.
                source=regular(a.fixture/'stack-expectations.json')
                shutil.copyfile(source,tree/'stack-expectations.json')
            result=image(a.fixture,'target',tree,DATA_BYTES,TARGET_UUID,TARGET_PARTUUID,replace=a.replace)
        elif a.action=='build-archive':result=image(a.fixture,'archive',a.fixture/'archive-tree',ARCHIVE_BYTES,ARCHIVE_UUID,ARCHIVE_PARTUUID,replace=a.replace)
        else:result=image(a.fixture,'boot',None,BOOT_BYTES,BOOT_UUID,BOOT_PARTUUID,filesystem='vfat',replace=a.replace)
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
