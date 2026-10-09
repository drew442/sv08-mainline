#!/usr/bin/env python3
"""Bounded ARM/systemd/RAUC execution evidence on assigned synthetic media.

Use --manifest PATH with one operation. Filesystem operations build-media,
refresh, bundle and recover-source require an already authorized private mount
namespace: sudo unshare --mount --propagation private python3 RUNNER ... .
No host package installation, service changes, networking or physical media.
The script expects installed QEMU, qemu-img, e2fsprogs, mtools, OpenSSL,
ssh-keygen, libubootenv tools and a public pinned native RAUC builder.

Manifest format_version=1 requires:
  scratch: existing absolute private directory outside the clean candidate;
  base/kernel/initrd/native_rauc: {path: absolute public path, sha256: digest};
  candidate: {path: absolute clean checkout, revision: exact commit,
              hash_manifest: public source receipt, hash_manifest_sha256: digest};
  packages: ordered [{path: public deb, filename: safe input name, sha256: digest}];
  limits: {live_bytes, cumulative_bytes, free_floor_bytes, log_bytes,
           runtime_seconds}, all explicit positive allowances.
Optional max_boots=12, install_boot_seconds=600, health_boot_seconds=180,
construction_seconds=300 bound each operation. Explicit counter_decrease_boot=10
reduces healthy B attempts from 3 to 1 before the host consumes its last attempt,
recording A0/B0 production normal-health recovery without manually refilling. For a continued lineage,
prior_runtime_seconds and retired_before_ledger_bytes record only history not
already in its ledgers; existing ledger counts are always retained. Fresh
ledgers initialize at zero. Never reset a lineage after retiring artifacts.
The source_exhaustion_recovery object {source_slot: "A", transaction_id: id}
authorizes only the explicit, recorded recover-source operation for an existing
interrupted-install fixture with both attempts exhausted. It is not normal
production boot health and is never called automatically by journey.

Fresh sequence: prepare-inputs, construct, export-template, build-media,
bundle --release reliability-good --source-slot A,
bundle --release reliability-bad --source-slot A --fail-health, journey.
Construction installs only manifest-pinned public packages in the isolated
ARM guest. export-template hashes its one raw template before retiring its
qcow2 overlay. build-media populates intrinsic A/B geometry and then retires
the template. Bundle preparation uses exactly one temporary root at a time.
For a corrected frozen candidate, refresh updates the existing source root;
retire obsolete goal bundles only after retaining their signed hashes/receipts
and confirming no active consumer, then create the two replacement bundles.

The guest uses production state/update/admission/health code, real signed RAUC
writes and fresh synthetic identity. Printer services and idle ACK are explicitly
simulated. Host-selected QEMU slots consume real redundant environment attempts;
U-Boot, MCU/hardware support and printing release readiness are not proven.
"""
import argparse, fcntl, hashlib, json, os, re, select, shutil, stat, subprocess, time
from pathlib import Path

# Every path, expected digest and allowance is supplied by an explicit manifest.
CONFIG={}
SCRATCH=BASE=KERNEL=INITRD=BUILDER=None
BASE_HASH=KERNEL_HASH=INITRD_HASH=BUILDER_HASH=None
LIMIT=CUMULATIVE_LIMIT=RESERVE=LOG_LIMIT=0


def configure(manifest):
    global CONFIG,SCRATCH,BASE,KERNEL,INITRD,BUILDER,BASE_HASH,KERNEL_HASH,INITRD_HASH,BUILDER_HASH,LIMIT,CUMULATIVE_LIMIT,RESERVE,LOG_LIMIT
    CONFIG=json.loads(Path(manifest).read_text())
    if CONFIG.get('format_version')!=1:raise ValueError('Unsupported fixture manifest')
    SCRATCH=Path(CONFIG['scratch']).absolute()
    if SCRATCH.is_symlink() or not SCRATCH.is_dir() or SCRATCH.stat().st_mode&0o077:raise ValueError('Existing private scratch directory required')
    for key in ('base','kernel','initrd','native_rauc'):
        entry=CONFIG[key];path=Path(entry['path']).absolute()
        if not path.is_file() or not re.fullmatch('[0-9a-f]{64}',entry['sha256']) or digest(path)!=entry['sha256']:raise ValueError('Manifest input differs: '+key)
    BASE=Path(CONFIG['base']['path']).absolute();BASE_HASH=CONFIG['base']['sha256']
    if BASE.is_symlink() or BASE.stat().st_size!=2147483648:raise ValueError('Assigned regular 2GiB synthetic base required')
    KERNEL=Path(CONFIG['kernel']['path']).resolve();KERNEL_HASH=CONFIG['kernel']['sha256']
    INITRD=Path(CONFIG['initrd']['path']).resolve();INITRD_HASH=CONFIG['initrd']['sha256']
    BUILDER=Path(CONFIG['native_rauc']['path']).resolve();BUILDER_HASH=CONFIG['native_rauc']['sha256']
    limits=CONFIG['limits'];LIMIT=int(limits['live_bytes']);CUMULATIVE_LIMIT=int(limits['cumulative_bytes']);RESERVE=int(limits['free_floor_bytes']);LOG_LIMIT=int(limits['log_bytes'])
    if min(LIMIT,CUMULATIVE_LIMIT,RESERVE,LOG_LIMIT,int(limits['runtime_seconds']))<=0:raise ValueError('Positive explicit allowances required')
    candidate=Path(CONFIG['candidate']['path']).absolute()
    if candidate==SCRATCH or candidate in SCRATCH.parents or SCRATCH in candidate.parents:raise ValueError('Candidate and disposable scratch must be separate')


def frozen_source(candidate, revision):
    candidate=Path(candidate)
    if subprocess.check_output(['git','-C',str(candidate),'rev-parse','HEAD'],text=True).strip()!=revision or subprocess.check_output(['git','-C',str(candidate),'status','--porcelain'],text=True).strip():raise ValueError('Clean frozen source required')
    expected=CONFIG['candidate']
    if candidate.absolute()!=Path(expected['path']).absolute() or revision!=expected['revision']:raise ValueError('Candidate differs from explicit manifest')
    if 'hash_manifest' in expected:
        source=Path(expected['hash_manifest']);receipt=json.loads(source.read_text())
        if digest(source)!=expected['hash_manifest_sha256']:raise ValueError('Source manifest changed')
        entries=receipt.get('files',receipt) if isinstance(receipt,dict) else {row['path']:row['sha256'] for row in receipt}
        for name,value in entries.items():
            if isinstance(value,dict):value=value['sha256']
            if digest(candidate/name)!=value:raise ValueError('Frozen source file changed: '+name)


def source_inputs(candidate):
    candidate=Path(candidate)
    files=list((candidate/'runtime').glob('*.py'))+list((candidate/'configs/host-os/systemd').glob('*.service'))
    names=('environment-layout.json','rauc-service-policy.json','rauc-system.conf.in','sv08-rauc-policy.conf','sv08-rauc-service.conf')
    files += [candidate/'configs/host-os'/name for name in names]
    files += [candidate/'configs/images/host-ab.json',candidate/'tests/host_qemu_rauc_composed.py',candidate/'tests/host_qemu_unattended_update.py']
    return files


def host_preflight():
    memory={line.split(':',1)[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapFree:'))}
    if memory['MemAvailable']<2*1024**3:raise RuntimeError('Insufficient available memory for assigned guest')
    versions={name:subprocess.check_output([name,'--version'],text=True,stderr=subprocess.STDOUT,timeout=10).splitlines()[0] for name in ('qemu-system-aarch64','qemu-img')}
    receipt={'memory':memory,'versions':versions,'network':'QEMU -nic none; no forwarding or physical passthrough','ports':[],'allocation':guard()}
    (SCRATCH/'host-preflight.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt


def charge_runtime(seconds, command):
    path=SCRATCH/'runtime-ledger.json'
    ledger=json.loads(path.read_text()) if path.exists() else {'prior_seconds':float(CONFIG.get('prior_runtime_seconds',0)),'runs':[]}
    ledger['runs'].append({'seconds':seconds,'command':command})
    ledger['total_seconds']=ledger['prior_seconds']+sum(row['seconds'] for row in ledger['runs'])
    path.write_text(json.dumps(ledger,indent=2)+'\n')
    if ledger['total_seconds']>CONFIG['limits']['runtime_seconds']:raise RuntimeError('Cumulative runtime allowance exhausted')


def runtime_remaining():
    path=SCRATCH/'runtime-ledger.json'
    total=json.loads(path.read_text())['total_seconds'] if path.exists() else float(CONFIG.get('prior_runtime_seconds',0))
    remaining=CONFIG['limits']['runtime_seconds']-total
    if remaining<=0:raise RuntimeError('Cumulative runtime allowance exhausted')
    return remaining

def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def usage():
    return sum(path.stat().st_blocks*512 for path in SCRATCH.rglob('*') if path.is_file() and not path.is_symlink())

def guard():
    free=shutil.disk_usage(SCRATCH).free
    path=SCRATCH/'allocation-ledger.json'
    ledger=json.loads(path.read_text()) if path.exists() else {'retired_before_ledger_bytes':int(CONFIG.get('retired_before_ledger_bytes',0)),'files':{}}
    seen=set()
    for file in SCRATCH.rglob('*'):
        if file.is_symlink() or not file.is_file() or file==path: continue
        info=file.stat();identity=f'{info.st_dev}:{info.st_ino}'
        row=ledger['files'].get(identity)
        if row and row.get('retired'):
            identity+=f':{info.st_ctime_ns}'
            row=ledger['files'].get(identity)
        seen.add(identity)
        if row is None: row={'peak_allocated_bytes':0,'paths':[]};ledger['files'][identity]=row
        row['peak_allocated_bytes']=max(row['peak_allocated_bytes'],info.st_blocks*512)
        row['retired']=False
        name=str(file.relative_to(SCRATCH))
        if name not in row['paths']: row['paths'].append(name)
    for identity,row in ledger['files'].items():
        if identity not in seen: row['retired']=True
    cumulative=ledger['retired_before_ledger_bytes']+sum(row['peak_allocated_bytes'] for row in ledger['files'].values())
    ledger['cumulative_generated_allocated_bytes']=cumulative
    path.write_text(json.dumps(ledger,indent=2)+'\n')
    current=usage()
    if free<RESERVE or current>LIMIT or cumulative>CUMULATIVE_LIMIT: raise RuntimeError('Assigned disk allowance/reserve exhausted')
    return {'free_bytes':free,'generated_allocated_bytes':current,'cumulative_generated_allocated_bytes':cumulative}

def bounded_logged_command(command, log_path, seconds):
    """Bound an owned builder's output, time and live allocation while it runs."""
    started=time.monotonic();process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    reason='completed';total=0
    with log_path.open('xb') as log:
        try:
            while time.monotonic()-started<min(seconds,runtime_remaining()):
                if select.select([process.stdout],[],[],1)[0]:
                    block=os.read(process.stdout.fileno(),65536)
                    if not block:break
                    total+=len(block)
                    if total>LOG_LIMIT:reason='log-bound';break
                    log.write(block);log.flush()
                guard()
                if process.poll() is not None:break
            else:reason='deadline'
        finally:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=15)
    charge_runtime(time.monotonic()-started,command)
    if process.returncode or reason!='completed':raise RuntimeError('Owned builder failed: '+reason+' status '+str(process.returncode))


def private_mount(image, directory, *, offset=0, size=None, readonly=False):
    """Owned regular-file loop mounts, only inside the assigned private namespace."""
    from contextlib import contextmanager
    @contextmanager
    def mounted():
        if os.geteuid()!=0: raise ValueError('Assigned sudo execution required')
        if Path('/proc/self/ns/mnt').readlink()==Path('/proc/1/ns/mnt').readlink():
            raise ValueError('Host-global mount namespace refused')
        target_image=Path(image)
        if target_image.is_symlink() or not stat.S_ISREG(target_image.stat().st_mode): raise ValueError('Regular assigned image required')
        allowed={BASE,SCRATCH/'target-root.ext4',SCRATCH/'guest.img',SCRATCH/'source-template.ext4'}
        if target_image not in allowed: raise ValueError('Unassigned mount image')
        if target_image==BASE and (not readonly or offset or size is not None or digest(BASE)!=BASE_HASH):raise ValueError('Immutable assigned base mount required')
        if target_image==SCRATCH/'guest.img':
            boundaries={(218103808,2147483648),(2566914048,2147483648),(4714397696,536870912),(5251268608,2565865472)}
            if target_image.stat().st_size!=7818182656 or (offset,size) not in boundaries:raise ValueError('Assigned GPT partition write boundary differs')
        elif offset or size is not None:raise ValueError('Standalone filesystem mount requires zero offset')
        identity=(target_image.stat().st_dev,target_image.stat().st_ino,target_image.stat().st_size)
        directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        options=['loop',f'offset={offset}']
        if size is not None: options.append(f'sizelimit={size}')
        if readonly: options.extend(['ro','noload'])
        subprocess.run(['mount','-t','ext4','-o',','.join(options),str(target_image),str(directory)],check=True,timeout=30)
        try:
            if identity!=(target_image.stat().st_dev,target_image.stat().st_ino,target_image.stat().st_size): raise ValueError('Image identity changed')
            yield directory
        finally:
            subprocess.run(['umount',str(directory)],check=True,timeout=30)
    return mounted()

def configure_root(root, candidate, release):
    """Configure only owned filesystem copies after the coordinator freezes source."""
    import uuid
    root, candidate=Path(root),Path(candidate)
    runtime=root/'usr/lib/sv08';runtime.mkdir(parents=True,exist_ok=True)
    for source in (candidate/'runtime').glob('*.py'): shutil.copy2(source,runtime/source.name)
    (runtime/'sv08_rauc_bootloader.py').chmod(0o755)
    config=candidate/'configs/host-os'
    uuids={'boot-a':'ba55a9b4-7969-423b-a739-db62e231b7a1','root-a':'26c68198-9248-47af-bbd3-643f1b604ef5','boot-b':'7b6e5211-6c5f-432f-9afc-2ac7e4f80b04','root-b':'d8d04a9a-f51f-41b3-a474-e079efe97186','recovery':'b28438ed-f895-4b93-9bad-d27d3890ccd3','data':'4773f966-0678-4cf5-bb83-8ee6fb11d8eb'}
    manifest={'release':release,'state_schema':1,'deployable':False,'devices':{name:'/dev/disk/by-partuuid/'+value for name,value in uuids.items()}}
    policy={'compatible':'sv08-offline-test-only','layout':'ab-8gb-v1','state_schema':1,'klipper_commit':'f0892d82b0f1c1228454f09eb508eddde2250f4b','max_bundle_bytes':1073741824,'image_bytes':{'boot':201326592,'rootfs':2147483648}}
    environment=json.loads((config/'environment-layout.json').read_text());environment['board_mmc_device_index']=10
    for name,value in {'release.json':manifest,'update-policy.json':policy,'environment.json':environment,'layout.json':json.loads((candidate/'configs/images/host-ab.json').read_text())}.items():
        (runtime/name).write_text(json.dumps(value)+'\n')
    shutil.copy2(config/'rauc-service-policy.json',runtime/'rauc-service-policy.json')
    text=(config/'rauc-system.conf.in').read_text().replace('@COMPATIBLE@',policy['compatible'])
    for role in ('root-a','root-b','boot-a','boot-b'): text=text.replace('@'+role.upper().replace('-','_')+'@',manifest['devices'][role])
    (root/'etc/rauc').mkdir(parents=True,exist_ok=True);(root/'etc/rauc/system.conf').write_text(text)
    shutil.copy2(SCRATCH/'fixture-cert.pem',root/'etc/rauc/release-keyring.pem')
    (root/'etc/fw_env.config').write_text('/dev/vda 0x400000 0x10000\n/dev/vda 0x800000 0x10000\n')
    (root/'etc/fstab').write_text('rootfs / ext4 ro 0 1\n')
    for name in ('sv08-prepare.service','sv08-boot-health.service','sv08-klipper.service','sv08-moonraker.service','sv08-mainsail.service','sv08-printer-api.service','sv08-web-auth.service','sv08-web-prepare.service'):
        destination=root/'etc/systemd/system'/name
        if destination.is_symlink():destination.unlink()
        shutil.copy2(config/'systemd'/name,root/'etc/systemd/system'/name)
    for unit,command in [('sv08-klipper.service','/usr/bin/python3 -u /input/guest.py --printer'),('sv08-moonraker.service','/usr/bin/sleep infinity')]:
        dropin=root/'etc/systemd/system'/(unit+'.d');dropin.mkdir(parents=True,exist_ok=True)
        (dropin/'simulation.conf').write_text('[Unit]\nConditionPathExists=\nConditionPathExists=!/run/sv08/trial\nConditionPathExists=/run/sv08/os-health-ready\n[Service]\nUser=root\nGroup=root\nSupplementaryGroups=\nExecStart=\nExecStart='+command+'\nRestart=no\n')
    for source,dest in [(config/'sv08-rauc-policy.conf',root/'etc/dbus-1/system.d/zz-sv08-rauc.conf'),(config/'sv08-rauc-service.conf',root/'etc/systemd/system/rauc.service.d/sv08.conf')]:
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    (root/'usr/lib/systemd/system/rauc.service').write_text('[Unit]\nAfter=dbus.service\n[Service]\nType=dbus\nBusName=de.pengutronix.rauc\nExecStart=/usr/bin/rauc --mount=/run/rauc service\n')
    for source,dest in {'system/machine-id':'etc/machine-id','system/hostname':'etc/hostname','system/hosts':'etc/hosts','system/network-connections':'etc/NetworkManager/system-connections','system/network-state':'var/lib/NetworkManager','system/rauc':'var/lib/rauc','system/random-seed':'var/lib/systemd/random-seed','system/timesync':'var/lib/systemd/timesync','system/rfkill':'var/lib/systemd/rfkill','system/linger':'var/lib/systemd/linger','shared/logs':'var/log','users/sv08':'home/sv08'}.items():
        path=root/dest
        if path.is_symlink(): path.unlink()
        if dest in ('etc/machine-id','etc/hostname','etc/hosts','var/lib/systemd/random-seed'):
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text('')
        else: path.mkdir(parents=True,exist_ok=True)
    (runtime/'seed').mkdir(exist_ok=True)
    shutil.copy2(SCRATCH/'fixture-owner.pub',runtime/'seed/authorized_keys')
    (runtime/'seed/config').mkdir(parents=True,exist_ok=True)
    for path in (root/'etc/ssh').glob('ssh_host_*'): path.unlink()
    for directory in ('tmp','var/tmp','var/cache','data','input'): (root/directory).mkdir(parents=True,exist_ok=True)
    (root/'etc/systemd/system/data.mount').write_text('[Mount]\nWhat='+manifest['devices']['data']+'\nWhere=/data\nType=ext4\nOptions=nodev,nosuid\n')
    (root/'etc/systemd/system/fixture.target').write_text('[Unit]\nRequires=basic.target sv08-prepare.service\nAfter=basic.target sv08-boot-health.service\nWants=fixture.service\nAllowIsolate=yes\n')
    (root/'etc/systemd/system/fixture.service').write_text('[Unit]\nWants=sv08-boot-health.service\nAfter=sv08-boot-health.service\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 -u /input/guest.py\nStandardOutput=journal+console\nStandardError=journal+console\n')
    (root/'etc/systemd/system/sv08-boot-health.service.d').mkdir(parents=True,exist_ok=True)
    (root/'etc/systemd/system/sv08-boot-health.service.d/fixture.conf').write_text('[Unit]\nRequires=rauc.service\nAfter=rauc.service\n[Service]\nTimeoutStartSec=240\nStandardOutput=journal+console\nStandardError=journal+console\n')
    # Explicit synthetic dependency failure; production health callback remains unchanged.
    testbin=runtime/'fixture-bin';testbin.mkdir(exist_ok=True)
    wrapper=testbin/'systemctl'
    wrapper.write_text('#!/usr/bin/python3\nimport os,sys\nfrom pathlib import Path\nif sys.argv[1:] == ["is-active","sv08-prepare.service"] and Path("/data/normal-health-failure").exists():\n print("inactive");sys.exit(3)\nos.execv("/usr/bin/systemctl",["systemctl",*sys.argv[1:]])\n');wrapper.chmod(0o755)
    (root/'etc/systemd/system/sv08-boot-health.service.d/normal-health-fixture.conf').write_text('[Service]\nEnvironment="PATH=/usr/lib/sv08/fixture-bin:/usr/bin:/bin"\n')
    return manifest,policy

def build_media(candidate, expected_revision):
    """Run with sudo unshare --mount --propagation private after stable freeze."""
    import sys
    candidate=Path(candidate)
    frozen_source(candidate,expected_revision)
    if subprocess.check_output(['git','-C',str(candidate),'status','--porcelain'],text=True).strip(): raise ValueError('Freeze requires clean submitted revision')
    lock=(SCRATCH/'resource.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if subprocess.run(['pgrep','-f','^qemu-system-aarch64'],stdout=subprocess.DEVNULL).returncode==0: raise RuntimeError('Shared QEMU resource occupied')
    source=SCRATCH/'source-template.ext4'
    template_receipt=json.loads((SCRATCH/'source-template.json').read_text())
    expected_source=template_receipt['sha256']
    if digest(source)!=expected_source: raise ValueError('Source template changed')
    preflight=guard()
    checked=subprocess.run(['e2fsck','-p',str(source)],timeout=60)
    if checked.returncode not in (0,1): raise ValueError('Constructed filesystem check failed')
    files=source_inputs(candidate)
    hashes={str(p.relative_to(candidate)):digest(p) for p in files}
    (SCRATCH/'source-freeze.json').write_text(json.dumps({'revision':expected_revision,'dirty':False,'files':hashes,'preflight':preflight},indent=2)+'\n')
    inputs=SCRATCH/'input/runtime';inputs.mkdir(exist_ok=True)
    for source_file in (candidate/'runtime').glob('*.py'): shutil.copy2(source_file,inputs/source_file.name)
    sys.path.insert(0,str(candidate/'tests'))
    from host_qemu_rauc_composed import create_media, format_media, partition_layout
    from host_qemu_unattended_update import PARTUUIDS
    guard(); disk=SCRATCH/'guest.img'
    if disk.exists():raise ValueError('Existing media must be reconciled, not overwritten')
    create_media(disk,PARTUUIDS);format_media(disk)
    parts={p['name']:p for p in partition_layout()}
    # The shared formatter's block-count default is overwritten by its usual
    # intermediate-image path. Direct mounted copies require explicit 4 KiB.
    for role in ('root-a','root-b','recovery','data'):
        part=parts[role]
        subprocess.run(['mkfs.ext4','-q','-F','-b','4096','-E','offset='+str(part['offset_bytes']),'-L',role,str(disk),str(part['size_bytes']//4096)],check=True,timeout=30)
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(SCRATCH/'fixture-key.pem'),'-out',str(SCRATCH/'fixture-cert.pem'),'-days','2','-subj','/CN=SV08 disposable reliability'],check=True,capture_output=True,timeout=30)
    (SCRATCH/'fixture-key.pem').chmod(0o600)
    subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(SCRATCH/'fixture-owner')],check=True,capture_output=True,timeout=30)
    root=parts['root-a']
    with private_mount(source,SCRATCH/'mount-source',readonly=True) as src:
        with private_mount(disk,SCRATCH/'mount-a',offset=root['offset_bytes'],size=root['size_bytes']) as dst:
            subprocess.run(['cp','-a',str(src)+'/.',str(dst)],check=True,timeout=180)
            configure_root(dst,candidate,'reliability-source')
            subprocess.run(['sync'],check=True)
    guard()
    for name in ('boot-a','boot-b'):
        part=parts[name]
        subprocess.run(['mcopy','-i',f'{disk}@@{part["offset_bytes"]}',str(KERNEL),str(INITRD),'::/'],check=True,timeout=30)
    env=SCRATCH/'fw_env.config';env.write_text(f'{disk} 0x400000 0x10000\n{disk} 0x800000 0x10000\n')
    seed=SCRATCH/'fw-seed';seed.write_text('sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A\nBOOT_A_LEFT=3\nBOOT_B_LEFT=0\n')
    subprocess.run(['fw_setenv','-c',str(env),'-f',str(seed),'-s',str(seed)],check=True,capture_output=True,timeout=30)
    result={'source_revision':expected_revision,'source_template_sha256_after_fsck':digest(source),'disk_sha256':digest(disk),'allocated_bytes':disk.stat().st_blocks*512,'postflight':guard(),'physical_hardware':False}
    (SCRATCH/'media-build.json').write_text(json.dumps(result,indent=2)+'\n')
    source.unlink()
    print(json.dumps(result,indent=2))

def build_bundle(candidate, release, source_slot, fail_health=False):
    """Exactly one sequential target filesystem, signed with owned fixture keys."""
    import sys
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,127}',release):raise ValueError('Invalid fixture release')
    lock=(SCRATCH/'resource.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if subprocess.run(['pgrep','-f','^qemu-system-aarch64'],stdout=subprocess.DEVNULL).returncode==0:raise RuntimeError('Shared QEMU resource occupied')
    candidate=Path(candidate);frozen_source(candidate,CONFIG['candidate']['revision']);freeze=json.loads((SCRATCH/'source-freeze.json').read_text())
    for name,expected in freeze['files'].items():
        if digest(candidate/name)!=expected: raise ValueError('Frozen runtime inputs changed')
    if subprocess.check_output([str(BUILDER),'--version'],text=True,timeout=10).strip()!='rauc 1.15.2':raise ValueError('Native RAUC version differs')
    if any((SCRATCH/path).exists() for path in (f'{release}-bundle.log',f'{release}-bundle.json',f'input/{release}.raucb')):raise ValueError('Retain/archive canonical bundle evidence before replacing a release')
    guard(); image=SCRATCH/'target-root.ext4'
    if image.exists(): raise ValueError('Existing target construction must be reconciled')
    with image.open('xb') as stream: stream.truncate(2147483648)
    subprocess.run(['mkfs.ext4','-q','-F','-b','4096',str(image)],check=True,timeout=30)
    sys.path.insert(0,str(candidate/'tests'))
    from host_qemu_rauc_composed import partition_layout
    part=next(p for p in partition_layout() if p['name']=='root-'+source_slot.lower())
    with private_mount(SCRATCH/'guest.img',SCRATCH/'mount-slot-source',offset=part['offset_bytes'],size=part['size_bytes'],readonly=True) as src:
        with private_mount(image,SCRATCH/'mount-target') as dst:
            subprocess.run(['cp','-a',str(src)+'/.',str(dst)],check=True,timeout=180)
            configure_root(dst,candidate,release)
            if fail_health:
                testbin=dst/'usr/lib/sv08/fixture-bin';testbin.mkdir(exist_ok=True)
                wrapper=testbin/'systemctl'
                wrapper.write_text('#!/usr/bin/python3\nimport os,sys\nif sys.argv[1:] == ["is-active","sv08-prepare.service"]:\n print("inactive");sys.exit(3)\nos.execv("/usr/bin/systemctl",["systemctl",*sys.argv[1:]])\n');wrapper.chmod(0o755)
                (dst/'etc/systemd/system/sv08-boot-health.service.d/fail-health.conf').write_text('[Service]\nEnvironment="PATH=/usr/lib/sv08/fixture-bin:/usr/bin:/bin"\n')
            subprocess.run(['sync'],check=True)
    guard()
    content=SCRATCH/'bundle-content';content.mkdir(mode=0o700)
    image.rename(content/'rootfs.img')
    boot=content/'boot.img'
    with boot.open('xb') as stream:stream.truncate(201326592)
    subprocess.run(['mkfs.vfat','-F','16',str(boot)],check=True,capture_output=True,timeout=30)
    subprocess.run(['mcopy','-i',str(boot),str(KERNEL),str(INITRD),'::/'],check=True,timeout=30)
    (content/'manifest.raucm').write_text(f'[update]\ncompatible=sv08-offline-test-only\nversion={release}\n[bundle]\nformat=verity\n[image.rootfs]\nfilename=rootfs.img\n[image.boot]\nfilename=boot.img\n[meta.sv08]\nlayout=ab-8gb-v1\nstate-schema=1\nklipper-commit=f0892d82b0f1c1228454f09eb508eddde2250f4b\n')
    builder=BUILDER
    if digest(builder)!=BUILDER_HASH:raise ValueError('Native RAUC builder changed')
    bundle=SCRATCH/'input'/f'{release}.raucb'
    guard()
    command=[str(builder),'bundle','--cert='+str(SCRATCH/'fixture-cert.pem'),'--key='+str(SCRATCH/'fixture-key.pem'),'--signing-keyring='+str(SCRATCH/'fixture-cert.pem'),str(content),str(bundle)]
    started=time.monotonic()
    bounded_logged_command(command,SCRATCH/f'{release}-bundle.log',180)
    guard()
    result={'release':release,'bundle_sha256':digest(bundle),'bundle_bytes':bundle.stat().st_size,'root_sha256':digest(content/'rootfs.img'),'boot_sha256':digest(boot),'builder_sha256':digest(builder),'builder_version':'1.15.2','elapsed_seconds':time.monotonic()-started,'allocated':guard()}
    (SCRATCH/f'{release}-bundle.json').write_text(json.dumps(result,indent=2)+'\n')
    shutil.rmtree(content)
    print(json.dumps(result,indent=2))

def refresh_source(candidate, revision):
    """Replace small candidate inputs, preserving constructed package/media data."""
    candidate=Path(candidate)
    frozen_source(candidate,revision)
    lock=(SCRATCH/'resource.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if subprocess.run(['pgrep','-f','^qemu-system-aarch64'],stdout=subprocess.DEVNULL).returncode==0:raise RuntimeError('Shared QEMU resource occupied')
    files=source_inputs(candidate)
    hashes={str(p.relative_to(candidate)):digest(p) for p in files}
    inputs=SCRATCH/'input/runtime';inputs.mkdir(exist_ok=True)
    for source in (candidate/'runtime').glob('*.py'):shutil.copy2(source,inputs/source.name)
    with private_mount(SCRATCH/'guest.img',SCRATCH/'mount-a',offset=218103808,size=2147483648) as dst:
        configure_root(dst,candidate,'reliability-source')
        installed={name:digest(dst/name.replace('runtime/','usr/lib/sv08/')) for name in hashes if name.startswith('runtime/')}
        for name,value in installed.items():
            if value!=hashes[name]:raise ValueError('Installed runtime hash differs')
        subprocess.run(['sync'],check=True)
    previous=SCRATCH/'source-freeze.json'
    if previous.exists():previous.rename(SCRATCH/('source-freeze.superseded-'+json.loads(previous.read_text())['revision']+'.json'))
    previous.write_text(json.dumps({'revision':revision,'dirty':False,'files':hashes,'installed_runtime_files':installed,'allocation':guard()},indent=2)+'\n')
    print(json.dumps({'revision':revision,'installed_runtime_count':len(installed),'allocation':guard()}))

def hash_region(path, offset, length):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        stream.seek(offset)
        while length:
            block=stream.read(min(length,8*1024**2))
            if not block:raise ValueError('Short assigned-media read')
            result.update(block);length-=len(block)
    return result.hexdigest()

def run_boot(slot, number, attempts_before=None):
    disk=SCRATCH/'guest.img';guard()
    if any((SCRATCH/f'boot-{number}-{slot}.{suffix}').exists() for suffix in ('log','json')):raise ValueError('Retain/archive canonical boot evidence before another attempt')
    if disk.is_symlink() or not stat.S_ISREG(disk.stat().st_mode) or disk.stat().st_size!=7818182656:raise ValueError('Assigned regular GPT media identity differs')
    command=['qemu-system-aarch64','-machine','virt','-accel','tcg,thread=multi','-cpu','cortex-a57','-smp','4','-m','1536','-nographic','-monitor','none','-no-reboot','-nic','none','-kernel',str(KERNEL),'-initrd',str(INITRD),
        '-append',f'root=/dev/vda{2 if slot=="A" else 4} ro rootwait console=ttyAMA0 init=/bin/bash panic=-1 rauc.slot={slot} sv08.test=rauc-backend sv08.fixture.attempts_before={attempts_before} sv08.fixture.boot_number={number}',
        '-drive',f'file={disk},format=raw,if=none,id=disk','-device','virtio-blk-device,drive=disk,serial=SV08-QEMU-DISPOSABLE',
        '-virtfs',f'local,path={SCRATCH}/input,mount_tag=input,security_model=none,readonly=on']
    started=time.monotonic();process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (SCRATCH/'active-vm.pid').write_text(str(process.pid))
    log_path=SCRATCH/f'boot-{number}-{slot}.log';sent=False;tail=b'';total=0;reason='deadline';markers=[]
    with log_path.open('xb') as log:
        try:
            while time.monotonic()-started<min(runtime_remaining(),int(CONFIG.get('install_boot_seconds',600) if number in (1,2) else CONFIG.get('health_boot_seconds',180))):
                if select.select([process.stdout],[],[],1)[0]:
                    block=os.read(process.stdout.fileno(),65536)
                    if not block:reason='guest-eof';break
                    total+=len(block)
                    if total>LOG_LIMIT:reason='log-bound';break
                    log.write(block);log.flush();tail=(tail+block)[-131072:]
                    if not sent and (b'bash: cannot set terminal' in tail or b'bash-5' in tail):
                        process.stdin.write(b'mount -t 9p -o trans=virtio,version=9p2000.L input /input; exec bash /input/setup.sh\n');process.stdin.flush();sent=True
                guard()
                if process.poll() is not None:reason='guest-exited';break
        finally:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=15)
    charge_runtime(time.monotonic()-started,command)
    output=log_path.read_text(errors='replace')
    for line in output.splitlines():
        match=re.search(r'(RELIABILITY_[A-Z_]+.*)',line)
        if match:markers.append(match.group(1))
    passed=process.returncode==0 and reason in ('guest-eof','guest-exited') and any(line.startswith(('RELIABILITY_PHASE_RESULT ','RELIABILITY_FAILED_TARGET_RESULT ','RELIABILITY_JOURNEY_PASS')) for line in markers) and not any('RELIABILITY_FAILURE' in line or 'CONSTRUCTION_FAILURE' in line for line in output.splitlines())
    result={'number':number,'slot':slot,'command':command,'exit_status':process.returncode,'reason':reason,'elapsed_seconds':time.monotonic()-started,'log_sha256':digest(log_path),'markers':markers,'passed':passed,'allocation':guard()}
    (SCRATCH/f'boot-{number}-{slot}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));print(output[-5000:])
    if not passed:raise RuntimeError('Actual installed boot journey did not pass: '+str(log_path))
    return result

def journey():
    lock=(SCRATCH/'resource.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if subprocess.run(['pgrep','-f','^qemu-system-aarch64'],stdout=subprocess.DEVNULL).returncode==0:raise RuntimeError('Shared QEMU resource occupied')
    if any((SCRATCH/name).exists() for name in ('executed-fixture-hashes.json','preservation-before.json','result.json')):raise ValueError('Retain/archive canonical journey evidence before another attempt')
    executed={str(path):digest(path) for path in [Path(__file__),SCRATCH/'input/guest.py',SCRATCH/'input/setup.sh',SCRATCH/'input/slot_driver.py']}
    (SCRATCH/'executed-fixture-hashes.json').write_text(json.dumps(executed,indent=2)+'\n')
    host_preflight();guard();disk=SCRATCH/'guest.img';env=SCRATCH/'fw_env.config'
    before={'primary_header':hash_region(disk,0,34*512),'primary_table':hash_region(disk,4096*512,32*512),'backup_gpt':hash_region(disk,disk.stat().st_size-33*512,33*512),'recovery':hash_region(disk,4714397696,536870912)}
    (SCRATCH/'preservation-before.json').write_text(json.dumps(before,indent=2)+'\n')
    results=[]
    for number in range(1,int(CONFIG.get('max_boots',12))+1):
        output=subprocess.check_output(['fw_printenv','-c',str(env),'sv08_env_layout','BOOT_ORDER','BOOT_A_LEFT','BOOT_B_LEFT'],text=True)
        values=dict(line.split('=',1) for line in output.splitlines())
        if number==CONFIG.get('counter_decrease_boot'):
            intervention=SCRATCH/'normal-counter-decrease.json'
            if intervention.exists() or values['BOOT_ORDER']!='B' or values['BOOT_A_LEFT']!='0' or values['BOOT_B_LEFT']!='3':raise ValueError('Explicit counter-decrease predecessor differs')
            before=dict(values)
            subprocess.run(['fw_setenv','-c',str(env),'BOOT_B_LEFT','1'],check=True,capture_output=True,timeout=30)
            values=dict(line.split('=',1) for line in subprocess.check_output(['fw_printenv','-c',str(env),'sv08_env_layout','BOOT_ORDER','BOOT_A_LEFT','BOOT_B_LEFT'],text=True).splitlines())
            if values!={**before,'BOOT_B_LEFT':'1'}:raise ValueError('Fixture counter decrease changed another boot field')
            intervention.write_text(json.dumps({'reason':'Explicit fixture counter DECREASE, never refill; next host consumption yields A0/B0 before actual production normal health','boot_number':number,'environment_before':before,'environment_after_decrease':values},indent=2)+'\n')
        slot=next((s for s in values['BOOT_ORDER'].split() if int(values['BOOT_'+s+'_LEFT'])>0),None)
        if slot is None:raise ValueError('No environment boot attempts remain')
        subprocess.run(['fw_setenv','-c',str(env),'BOOT_'+slot+'_LEFT',str(int(values['BOOT_'+slot+'_LEFT'])-1)],check=True,capture_output=True,timeout=30)
        result=run_boot(slot,number,int(values['BOOT_'+slot+'_LEFT']));result['environment_before_attempt']=values;results.append(result)
        (SCRATCH/f'boot-{number}-{slot}.json').write_text(json.dumps(result,indent=2)+'\n')
        if any('RELIABILITY_JOURNEY_PASS' in line for line in result['markers']):break
    if not any('RELIABILITY_JOURNEY_PASS' in line for line in results[-1]['markers']):raise RuntimeError('Complete sequence not reached')
    after={'primary_header':hash_region(disk,0,34*512),'primary_table':hash_region(disk,4096*512,32*512),'backup_gpt':hash_region(disk,disk.stat().st_size-33*512,33*512),'recovery':hash_region(disk,4714397696,536870912)}
    if after!=before or digest(BASE)!=BASE_HASH:raise RuntimeError('Preserved region/base changed')
    receipt={'status':'PASS','source':json.loads((SCRATCH/'source-freeze.json').read_text()),'boots':results,'preserved_regions':after,'base_sha256_after':digest(BASE),'actual_signed_rauc_installation':True,'actual_production_prepare_and_health':True,'printer':'simulated service and idle ACK','boot_selection':'host model consumes real redundant environment, no U-Boot execution','physical_hardware':False,'allocation':guard()}
    (SCRATCH/'result.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':'PASS','boots':len(results),'allocation':receipt['allocation']}))

def construction():
    if os.geteuid()!=0: raise ValueError('Assigned sudo execution required')
    lock=(SCRATCH/'resource.lock').open('w'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if subprocess.run(['pgrep','-f','^qemu-system-aarch64'],stdout=subprocess.DEVNULL).returncode==0: raise RuntimeError('Shared QEMU resource occupied')
    assert stat.S_ISREG(BASE.stat().st_mode) and not BASE.is_symlink() and BASE.stat().st_size==2147483648
    assert digest(BASE)==BASE_HASH
    assert digest(KERNEL)==KERNEL_HASH
    assert digest(INITRD)==INITRD_HASH
    if any((SCRATCH/name).exists() for name in ('construction.log','construction-result.json')):raise ValueError('Retain/archive canonical construction evidence before another attempt')
    preflight=host_preflight()
    overlay=SCRATCH/'construction.qcow2'
    if overlay.exists():raise ValueError('Existing construction overlay must be reconciled')
    subprocess.run(['qemu-img','create','-f','qcow2','-F','raw','-b',str(BASE),str(overlay)],check=True,capture_output=True)
    command=['qemu-system-aarch64','-machine','virt','-cpu','cortex-a57','-smp','2','-m','1536','-nographic','-monitor','none','-no-reboot','-nic','none',
        '-kernel',str(KERNEL),'-initrd',str(INITRD),'-append','root=/dev/vda rw console=ttyAMA0 init=/bin/bash panic=-1',
        '-drive',f'file={overlay},format=qcow2,if=virtio',
        '-virtfs',f'local,path={SCRATCH}/input,mount_tag=input,security_model=none,readonly=on']
    started=time.monotonic(); guest=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (SCRATCH/'construction.pid').write_text(str(guest.pid))
    sent=False; tail=b''; reason='deadline'; passed=False; total=0
    with (SCRATCH/'construction.log').open('xb') as log:
        try:
            while time.monotonic()-started<min(runtime_remaining(),int(CONFIG.get('construction_seconds',300))):
                if select.select([guest.stdout],[],[],1)[0]:
                    block=os.read(guest.stdout.fileno(),65536)
                    if not block: reason='guest-eof';break
                    total+=len(block)
                    if total>LOG_LIMIT: reason='log-bound'; break
                    log.write(block); log.flush(); tail=(tail+block)[-131072:]
                    if not sent and (b'bash: cannot set terminal' in tail or b'bash-5' in tail):
                        guest.stdin.write(b'mkdir -p /input; mount -t 9p -o trans=virtio,version=9p2000.L input /input; python3 -u /input/slot_driver.py\n');guest.stdin.flush();sent=True
                    if b'CONSTRUCTION_PASS' in tail: passed=True
                    if b'CONSTRUCTION_FAILURE' in tail: reason='guest-failure'
                guard()
                if guest.poll() is not None: reason='guest-exited'; break
        finally:
            if guest.poll() is None: guest.terminate()
            try: guest.wait(timeout=15)
            except subprocess.TimeoutExpired: guest.kill(); guest.wait(timeout=15)
    charge_runtime(time.monotonic()-started,command)
    result={'command':command,'elapsed_seconds':time.monotonic()-started,'exit_status':guest.returncode,'reason':reason,'pass_marker':passed,
        'base_sha256_after':digest(BASE),'overlay_sha256':digest(overlay),'preflight':preflight,'postflight':guard(),'log_sha256':digest(SCRATCH/'construction.log')}
    (SCRATCH/'construction-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    print(tail.decode(errors='replace')[-4000:])
    if not passed or reason not in ('guest-eof','guest-exited') or 'CONSTRUCTION_FAILURE' in (SCRATCH/'construction.log').read_text(errors='replace') or guest.returncode!=0 or result['base_sha256_after']!=BASE_HASH: raise RuntimeError('Construction did not pass')

def export_template():
    lock=(SCRATCH/'resource.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    receipt=json.loads((SCRATCH/'construction-result.json').read_text());overlay=SCRATCH/'construction.qcow2';target=SCRATCH/'source-template.ext4'
    if not receipt['pass_marker'] or receipt['exit_status']!=0 or digest(overlay)!=receipt['overlay_sha256']:raise ValueError('Successful immutable construction receipt required')
    if target.exists():raise ValueError('Existing source template must be reconciled')
    guard();started=time.monotonic();command=['qemu-img','convert','-f','qcow2','-O','raw',str(overlay),str(target)]
    subprocess.run(command,check=True,timeout=min(180,runtime_remaining()));charge_runtime(time.monotonic()-started,command)
    result={'sha256':digest(target),'logical_bytes':target.stat().st_size,'allocated_bytes':target.stat().st_blocks*512,'construction_receipt_sha256':digest(SCRATCH/'construction-result.json'),'allocation':guard()}
    (SCRATCH/'source-template.json').write_text(json.dumps(result,indent=2)+'\n');overlay.unlink();guard()


def install_inputs():
    """Stage public fixture code and exact public package artifacts, never credentials."""
    lock=(SCRATCH/'resource.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if subprocess.run(['pgrep','-f','^qemu-system-aarch64'],stdout=subprocess.DEVNULL).returncode==0:raise RuntimeError('Shared QEMU resource occupied')
    destination=SCRATCH/'input';destination.mkdir(mode=0o700,exist_ok=True)
    fixtures=Path(__file__).parent/'fixtures/reliability'
    for name in ('guest.py','setup.sh','slot_driver.py'):
        shutil.copy2(fixtures/name,destination/name)
    packages=[]
    for entry in CONFIG['packages']:
        source=Path(entry['path'])
        if digest(source)!=entry['sha256'] or Path(entry['filename']).name!=entry['filename']:raise ValueError('Exact public package mismatch')
        target=destination/entry['filename']
        if target.exists():
            if digest(target)!=entry['sha256']:raise ValueError('Conflicting existing input')
        else:shutil.copy2(source,target)
        packages.append({'filename':entry['filename'],'sha256':entry['sha256']})
    (destination/'packages.json').write_text(json.dumps({'packages':packages})+'\n');guard()


def recover_source():
    """Explicit one-time recovery of the source exhausted by superseded runs."""
    expected=CONFIG.get('source_exhaustion_recovery')
    if not expected or expected['source_slot']!='A':raise ValueError('Explicit assigned recovery receipt required')
    receipt_path=SCRATCH/'source-exhaustion-recovery.json'
    if receipt_path.exists():raise ValueError('One-time source rearm already recorded')
    frozen_source(CONFIG['candidate']['path'],CONFIG['candidate']['revision'])
    lock=(SCRATCH/'resource.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if subprocess.run(['pgrep','-f','^qemu-system-aarch64'],stdout=subprocess.DEVNULL).returncode==0:raise RuntimeError('Shared QEMU resource occupied')
    disk=SCRATCH/'guest.img';guard()
    env=SCRATCH/'fw_env.config'
    values=dict(line.split('=',1) for line in subprocess.check_output(['fw_printenv','-c',str(env),'BOOT_ORDER','BOOT_A_LEFT','BOOT_B_LEFT'],text=True).splitlines())
    if values!={'BOOT_ORDER':'A','BOOT_A_LEFT':'0','BOOT_B_LEFT':'0'}:raise ValueError('Source exhaustion predecessor differs')
    with private_mount(disk,SCRATCH/'recovery-check-data',offset=5251268608,size=2565865472,readonly=True) as data:
        tx=json.loads((data/'sv08/update.json').read_text());state=json.loads((data/'sv08/state.json').read_text())
        if tx['id']!=expected['transaction_id'] or tx['phase']!='installing' or state['pending'] is not None or set(state['slots'])!={'A'}:raise ValueError('Interrupted-install predecessor differs')
        state_hash=digest(data/'sv08/state.json')
    subprocess.run(['fw_setenv','-c',str(env),'BOOT_A_LEFT','3'],check=True,capture_output=True,timeout=30)
    after=subprocess.check_output(['fw_printenv','-c',str(env),'BOOT_ORDER','BOOT_A_LEFT','BOOT_B_LEFT'],text=True)
    receipt={'reason':'One-time source exhaustion caused by retained superseded fixture runs; never a production normal-boot refresh','environment_before':values,'environment_after':after,'transaction_id':tx['id'],'registry_sha256':state_hash,'source_revision':CONFIG['candidate']['revision'],'allocation':guard()}
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True,type=Path,help='Explicit paths, expected hashes, candidate revision and allocated/runtime limits')
    sub=parser.add_subparsers(dest='operation',required=True)
    for operation in ('prepare-inputs','construct','export-template','build-media','refresh','recover-source','journey'):sub.add_parser(operation)
    bundle=sub.add_parser('bundle');bundle.add_argument('--release',required=True);bundle.add_argument('--source-slot',choices=('A','B'),required=True);bundle.add_argument('--fail-health',action='store_true')
    args=parser.parse_args();configure(args.manifest);guard();runtime_remaining()
    candidate=CONFIG['candidate']['path'];revision=CONFIG['candidate']['revision']
    started=time.monotonic();remaining_before=runtime_remaining()
    try:
        if args.operation=='prepare-inputs':install_inputs()
        elif args.operation=='construct':construction()
        elif args.operation=='export-template':export_template()
        elif args.operation=='build-media':build_media(candidate,revision)
        elif args.operation=='refresh':refresh_source(candidate,revision)
        elif args.operation=='recover-source':recover_source()
        elif args.operation=='bundle':build_bundle(candidate,args.release,args.source_slot,args.fail_health)
        elif args.operation=='journey':frozen_source(candidate,revision);journey()

    finally:
        charged=remaining_before-runtime_remaining()
        uncharged=max(0,time.monotonic()-started-charged)
        charge_runtime(uncharged,['fixture-cli',args.operation,'preparation-and-cleanup'])

if __name__=='__main__':main()
