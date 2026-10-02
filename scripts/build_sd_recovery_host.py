#!/usr/bin/env python3
"""Explicit regular-file SD recovery composer; no deployment or device access.

Reuse recovery envelope/gate and upstream systemd/OpenSSH. Retire when release
recovery supports SD. Source ext4 is the authorized v5 partition only.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import re
import subprocess

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / 'configs/host-os/sd-recovery-host'
SOURCE_SHA = 'c83975508e1cafca51e23c6ad9e19408fa01b5d35be583b39a38c5b13ad2345c'
PARTUUID = 'deaf981d-7441-428c-bf43-ce40bca6ca65'
ROOT_UUID = '27ea34a6-fb05-4814-aaee-251071577ae1'
SIZE = 536870912
EPOCH = 1789257600
MASKS = ('sv08-recovery-prepare', 'sv08-recovery-private-mounts',
         'sv08-boot-health', 'sv08-prepare', 'sv08-klipper', 'klipper',
         'sv08-moonraker', 'moonraker', 'KlipperScreen', 'rauc', 'ssh',
         'ssh.socket', 'apt-daily', 'apt-daily-upgrade')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe(path, regular=False, allow_links=False):
    path = Path(path).absolute()
    if any(c in str(path) for c in ('\n','\r','\0')) or '..' in path.parts:
        raise ValueError('Simple absolute paths required')
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError('Symlink input/output ancestry forbidden')
    if regular and (not stat.S_ISREG(path.stat().st_mode) or (path.stat().st_nlink != 1 and not allow_links)):
        raise ValueError('Single-link regular input required')
    return path


def admitted(source, work):
    source, work = safe(source, True), safe(work)
    if any(not re.fullmatch(r'/[A-Za-z0-9_./@+-]+',str(p)) for p in (source,work)):
        raise ValueError('Simple debugfs source/output paths required')
    if source == work or source in work.parents or work in source.parents:
        raise ValueError('Source/output overlap')
    if work.exists():
        raise ValueError('Fresh output required')
    if sha(source) != SOURCE_SHA or source.stat().st_size != SIZE:
        raise ValueError('Authorized recovery source hash/capacity mismatch')
    return source, work


def run(*args, **kwargs):
    return subprocess.check_output([str(x) for x in args], stderr=subprocess.STDOUT,
                                   timeout=900, **kwargs)


def put(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        path.unlink()
    path.write_text(text)
    path.chmod(mode)


def gate(config_digest=None, links_digest=None):
    text = (REPO / 'configs/host-os/recovery-init').read_text()
    begin = text.index('for module in virtio_pci ')
    end = text.index('manifest=/newroot/')
    selector = (REPO / 'configs/host-os/recovery-board-root').read_text()
    for token, value in {'PARTUUID': PARTUUID, 'UUID': ROOT_UUID,
                         'INDEX': 2, 'SECTORS': SIZE // 512}.items():
        selector = selector.replace('@' + token + '@', str(value))
    selector = "if [ \"$(/bin/busybox uname -r)\" = '6.12.107+deb13-arm64' ]; then\n    for module in virtio_pci virtio_mmio virtio_blk; do modprobe \"$module\" || fail 'VM early driver'; done\nfi\n" + selector
    text = text[:begin] + selector + text[end:]
    old = "= '/dev/vda:ext4:ro,relatime,norecovery'"
    if text.count(old) != 1:
        raise ValueError('Reviewed common recovery mount gate changed')
    text = text.replace(old, '= "${recovery_device}:ext4:ro,relatime,norecovery"')
    text = text.replace('964ed891-6ec4-4a95-8762-e32c91260394', ROOT_UUID)
    # Account home and network lease state are deliberately volatile.
    text = text.replace('# Marker is created',
        'mkdir -p /run/sd-owner /run/recovery-var/lib/private\n'
        '/bin/busybox chown 1000:1000 /run/sd-owner\n'
        '/bin/busybox chmod 0700 /run/sd-owner\n# Marker is created')
    if config_digest is not None:
        check = f"""[ "$(sha256sum /newroot/etc/sv08/sd-envelope.sha256 | cut -d ' ' -f 1)" = '{config_digest}' ] || fail 'changed SD envelope inventory'
(cd /newroot && sha256sum -c etc/sv08/sd-envelope.sha256) || fail 'changed SD envelope files'
"""
        if links_digest is not None:
            check += f"""[ \"$(sha256sum /newroot/etc/sv08/sd-envelope.links | cut -d ' ' -f 1)\" = '{links_digest}' ] || fail 'changed SD link inventory'
while IFS=\"$(printf '\\t')\" read -r target path; do
    [ \"$(readlink /newroot/$path)\" = \"$target\" ] || fail 'changed SD envelope symlink'
done </newroot/etc/sv08/sd-envelope.links
"""
        text = text.replace('manifest=/newroot/', check + 'manifest=/newroot/', 1)
    return text


def boot_script(payloads, binding):
    lines = [f'setenv bootargs "root=PARTUUID={PARTUUID} ro panic=0 console=tty0 console=ttyS0,115200 sv08.envelope={binding}"']
    for name, address in [('Image', '${kernel_addr_r}'), ('initrd.img', '${ramdisk_addr_r}'), ('sv08.dtb', '${fdt_addr_r}')]:
        lines += [f'if load mmc 0:1 {address} {name}; then',
                  f'  hash sha256 {address} ${{filesize}} sv08_digest',
                  f'  if test "${{sv08_digest}}" != "{payloads[name]}"; then reset; fi']
        if name == 'initrd.img':
            lines.append('  setenv sv08_initrd_size ${filesize}')
        lines += ['else', '  reset', 'fi']
    lines += ['booti ${kernel_addr_r} ${ramdisk_addr_r}:${sv08_initrd_size} ${fdt_addr_r}', 'reset']
    return '\n'.join(lines) + '\n'


def packages(path):
    manifest = safe(path, True)
    record = json.loads(manifest.read_text())
    if record.get('files') and isinstance(record.get('packages'), dict):
        return manifest, []
    raise ValueError('Installed package closure manifest required')


def check_cache(record, source, manifest, additional, namespace):
    if record.get('owner_namespace') != namespace:
        raise ValueError('Reuse package ownership namespace differs')
    if record['inputs'].get(str(source)) != SOURCE_SHA:
        raise ValueError('Reuse is not derived from authorized source')
    if bool(additional) != bool(record.get('additional_package_provenance')):
        raise ValueError('Reuse requires identical supplemental package presence')
    if record['inputs'].get(str(manifest)) != sha(manifest) or (additional and record['inputs'].get(str(additional)) != sha(additional)):
        raise ValueError('Reuse package provenance differs')


def preflight_space(free, reuse, execute):
    required=1536*1024**2 if reuse else 3*1024**3
    if execute and free<required:
        raise ValueError(f'Require {required} free bytes; allocated build budget3500MiB')
    return required


def compose(a):
    source, work = admitted(a.source, a.work)
    public = safe(a.public_key, True)
    key = public.read_text().strip()
    fields = key.split()
    if len(fields) < 2 or fields[0] not in ('ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256') or '\n' in key:
        raise ValueError('Exactly one owner public key required')
    run('ssh-keygen', '-lf', public)
    test_public = safe(a.test_public_key, True) if a.test_public_key else None
    if test_public:
        run('ssh-keygen', '-lf', test_public)
        fixture = test_public.read_text().strip()
        if '\n' in fixture or not fixture.startswith('ssh-ed25519 '):
            raise ValueError('Single Ed25519 test fixture public key required')
        key += '\n' + fixture
    package_manifest, closure = packages(a.packages)
    owner_mapping=safe(a.owner_mapping,True)
    namespace=json.loads(owner_mapping.read_text())
    additional = safe(a.additional_packages,True) if a.additional_packages else None
    sudo_pam = [safe(p,True) for p in (a.sudo_pam,a.sudo_i_pam) if p]
    for path in (public, package_manifest, *closure):
        if path == work or work in path.parents or path in work.parents:
            raise ValueError('Input/output overlap')
    inputs = {str(p): sha(p) for p in (source, public, package_manifest, *closure,
              Path(__file__), *sorted(CONFIG.iterdir()), REPO/'configs/host-os/recovery-init', REPO/'configs/host-os/recovery-board-root')}
    for path in [owner_mapping,*sudo_pam,*([additional] if additional else [])]:
        inputs[str(path)]=sha(path)
    if test_public:
        inputs[str(test_public)] = sha(test_public)
    reuse = safe(a.reuse) if a.reuse else None
    reuse_record = json.loads((reuse/'composition.json').read_text()) if reuse else None
    if reuse:
        check_cache(reuse_record,source,package_manifest,additional,namespace)
        cache = safe(reuse/'envelope/usr.squashfs',True)
        cache_manifest = (reuse/'envelope/etc/sv08/recovery-envelope.manifest').read_text()
        if hashlib.sha256(cache_manifest.encode()).hexdigest()!=reuse_record['manifest_sha256']:
            raise ValueError('Reuse manifest changed')
        expected_cache = dict(line.split('=',1) for line in cache_manifest.splitlines())['usr_sha256']
        if sha(cache) != expected_cache:
            raise ValueError('Reused compressed userspace changed')
        for name,expected in [('vm-vmlinuz',reuse_record['vm_kernel_sha256']),('boot/initrd.img',reuse_record['payloads']['initrd.img']['sha256'])]:
            path=safe(reuse/name,True)
            if sha(path)!=expected:
                raise ValueError('Changed reused kernel/initramfs')
            inputs[str(path)]=expected
        for path in (safe(reuse/'composition.json',True),safe(reuse/'envelope/etc/sv08/recovery-envelope.manifest',True),cache):
            inputs[str(path)]=sha(path)
        if work in reuse.parents or reuse in work.parents:
            raise ValueError('Reuse/output overlap')
    parent = work.parent
    while not parent.exists():
        parent = parent.parent
    free = shutil.disk_usage(parent).free
    required_free=preflight_space(free,bool(reuse),a.execute)
    print(json.dumps({'execute': a.execute, 'source_sha256': SOURCE_SHA, 'free_bytes': free,'required_free_bytes':required_free,
                      'deployable': False, 'partition_index': 2}), flush=True)
    if not a.execute:
        return
    if os.geteuid() != 0:
        raise ValueError('Root required to preserve envelope ownership; regular files only')
    work.mkdir(parents=True, mode=0o700)
    peak_allocated = 0
    def measure():
        nonlocal peak_allocated
        amount = sum(p.lstat().st_blocks*512 for p in work.rglob('*'))
        peak_allocated = max(peak_allocated, amount)
        if amount > 3500*1024**2:
            raise ValueError('Additional allocated build budget exceeded')
    envelope = work / 'envelope'
    envelope.mkdir()
    # debugfs is userspace-only; no source mounts, loops or hardware discovery.
    run('debugfs', '-R', f'rdump / {envelope}', source)
    compressed = envelope / 'usr.squashfs'
    if reuse:
        compressed.unlink()
        shutil.copyfile(cache,compressed)
        payload_before={};overlays=reuse_record.get('package_overlay_changes',{})
    else:
        run('unsquashfs', '-f', '-d', envelope / 'usr', compressed)
        compressed.unlink()
        measure()
        for package in closure:
            run('dpkg-deb', '-x', package, envelope)
        imported = json.loads(package_manifest.read_text())
        if additional:
            extra=json.loads(additional.read_text())
            imported['files']={**imported['files'],**extra['files']}
            imported['packages']={**imported['packages'],**extra['packages']}
        payload_before = {}
        overlays = {}
        payload = safe(package_manifest.parent / 'ssh-installed-payload')
        for name, item in imported['files'].items():
            if str(item['uid']) not in namespace['users'] or str(item['gid']) not in namespace['groups']:
                raise ValueError('Undeclared package ownership namespace')
            rel = Path(name)
            if rel.is_absolute() or '..' in rel.parts:
                raise ValueError('Unsafe installed package path')
            if rel.parts[0] in ('lib', 'bin', 'sbin'):
                rel = Path('usr') / rel
            if rel.parts[0] != 'usr':
                continue  # Package metadata belongs in provenance, not runtime.
            from_extra = additional and name in extra['files']
            source_file = (additional.parent/'sudo-installed-payload' if from_extra else payload) / name
            target = envelope / rel
            for ancestor in target.parents:
                if ancestor == envelope:
                    break
                if ancestor.is_symlink():
                    raise ValueError('Payload target symlink ancestry')
            target.parent.mkdir(parents=True, exist_ok=True)
            if item['type'] == 'symlink':
                link = item['target']
                resolved = (envelope / link.lstrip('/')).resolve() if link.startswith('/') else (target.parent / link).resolve()
                if link != '/dev/null' and not resolved.is_relative_to(envelope):
                    raise ValueError('Payload symlink escapes envelope')
                if not source_file.is_symlink() or os.readlink(source_file) != link:
                    raise ValueError('Payload link mismatch')
                target.unlink(missing_ok=True)
                target.symlink_to(link)
                os.chown(target,item['uid'],item['gid'],follow_symlinks=False)
            elif item['type'] == 'file':
                source_file = safe(source_file, True, allow_links=True)
                if sha(source_file) != item['sha256']:
                    raise ValueError('Installed package file mismatch')
                if target.is_symlink():
                    target.unlink()
                payload_before[str(source_file)] = item['sha256']
                if target.is_file():
                    previous = sha(target)
                    if previous != item['sha256']:
                        overlays[str(rel)] = {'before':previous,'after':item['sha256']}
                shutil.copyfile(source_file, target)
                os.chown(target,item['uid'],item['gid'])
                target.chmod(item['mode'])
            else:
                raise ValueError('Unsupported installed package node')

        measure()
    group_path=envelope/'etc/group'
    group_lines=group_path.read_text().splitlines()
    for gid,item in namespace['groups'].items():
        name=item['name']
        clashes=[line for line in group_lines if line.split(':')[2]==gid or line.split(':')[0]==name]
        if clashes and any((line.split(':')[0],line.split(':')[2]) != (name,gid) for line in clashes):
            raise ValueError('Package group namespace conflict')
        if not clashes:group_lines.append(f'{name}:x:{gid}:')
    put(group_path,'\n'.join(group_lines)+'\n')
    units = envelope / 'etc/systemd/system'
    # Never carry a reviewed eMMC media-provider configuration into SD startup.
    for name in ('recovery-media-policy.json', 'recovery-image.json'):
        (envelope / 'etc/sv08' / name).unlink(missing_ok=True)
    for name in MASKS:
        unit = name if name.endswith('.socket') else name + '.service'
        target = units / unit
        if target.exists() and not target.is_symlink():
            target.unlink()
        elif target.is_symlink():
            target.unlink()
        target.symlink_to('/dev/null')
    for name in ('systemd-networkd.service', 'systemd-networkd.socket'):
        (units / name).unlink(missing_ok=True)
    generators=envelope/'etc/systemd/system-generators'
    generators.mkdir(exist_ok=True)
    generator=generators/'systemd-ssh-generator'
    generator.unlink(missing_ok=True)
    generator.symlink_to('/dev/null')
    wants = units / 'sv08-recovery.target.wants'
    wants.mkdir(exist_ok=True)
    for name in ('systemd-networkd.service', 'sd-host-ssh.service'):
        (wants / name).unlink(missing_ok=True)
        (wants / name).symlink_to('../sd-host-ssh.service' if name.startswith('sd-') else '/usr/lib/systemd/system/'+name)
    put(units / 'sd-host-ssh.service', (CONFIG / 'sd-host-ssh.service').read_text())
    put(units / 'sd-host-keys.service', (CONFIG / 'sd-host-keys.service').read_text())
    put(envelope / 'etc/systemd/network/20-wired.network', (CONFIG / '20-wired.network').read_text())
    put(envelope / 'etc/ssh/sshd_config', (CONFIG / 'sshd_config').read_text())
    put(envelope / 'etc/sv08/sd-host-authorized_keys', key + '\n')
    put(envelope / 'etc/pam.d/sshd', 'auth required pam_deny.so\naccount required pam_permit.so\nsession required pam_permit.so\n')
    put(envelope/'etc/passwd', (envelope/'etc/passwd').read_text().rstrip()+'\nsshd:x:991:65534:SSH privilege separation:/run/sshd:/usr/sbin/nologin\n')
    for name, line in [('passwd', 'recovery:x:1000:1000:SD recovery:/run/sd-owner:/bin/bash'),
                       ('group', 'recovery:x:1000:'), ('shadow', 'recovery:*:20000:0:99999:7:::')]:
        target = envelope / 'etc' / name
        current = target.read_text()
        if any(x.startswith('recovery:') for x in current.splitlines()):
            raise ValueError('Source already contains recovery account')
        put(target, current.rstrip() + '\n' + line + '\n', 0o640 if name == 'shadow' else 0o644)
    groups = (envelope/'etc/group').read_text().splitlines()
    groups = [line+(',recovery' if line.split(':')[-1] else 'recovery') if line.startswith(('adm:', 'systemd-journal:')) else line for line in groups]
    put(envelope/'etc/group','\n'.join(groups)+'\n')
    for path,name in zip(sudo_pam,('sudo','sudo-i')):
        put(envelope/'etc/pam.d'/name,path.read_text())
    put(envelope/'etc/sudoers','Defaults env_reset\nDefaults secure_path="/usr/sbin:/usr/bin:/sbin:/bin"\nroot ALL=(ALL:ALL) ALL\nrecovery ALL=(ALL:ALL) NOPASSWD: ALL\n',0o440)
    put(envelope / 'etc/hostname', 'sv08-sd-recovery-test\n')
    put(envelope / 'etc/hosts', '127.0.0.1 localhost\n127.0.1.1 sv08-sd-recovery-test\n::1 localhost ip6-localhost ip6-loopback\n')
    # SSH private identity is generated into tmpfs each boot: explicit re-enrollment.
    (envelope / 'etc/ssh').mkdir(exist_ok=True)
    for candidate in (envelope / 'etc/ssh').glob('ssh_host_*'):
        candidate.unlink()
    licenses = {'libgcc-s1':'usr/share/doc/gcc-14-base/copyright','libncursesw6':'usr/share/doc/libtinfo6/copyright','openssh-server':'usr/share/doc/openssh-client/copyright','openssh-sftp-server':'usr/share/doc/openssh-client/copyright'}
    runtime_dependencies = {}
    if not reuse:
        license_hashes = {name:{'path':path,'sha256':sha(envelope/path)} for name,path in licenses.items()}
        for name in ('usr/sbin/sshd','usr/lib/openssh/sshd-session','usr/bin/ssh-keygen','usr/lib/systemd/systemd-networkd','usr/bin/sudo'):
            runtime_dependencies[name]=run(shutil.which('qemu-aarch64-static') or 'qemu-aarch64','-L',envelope,envelope/'usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1','--list',envelope/name).decode()
        run('mksquashfs', envelope / 'usr', compressed, '-noappend', '-comp', 'zstd', '-Xcompression-level','10',
            '-b', '1M', '-processors', '2', '-mem', '256M', '-all-time', EPOCH, '-mkfs-time', EPOCH)
        measure()
        # Keep the single extracted /usr until the VM dependency closure is staged.
    if reuse:
        license_hashes=reuse_record['shared_license_notices']
        runtime_dependencies=reuse_record['runtime_loader_dependencies']
    manifest = (f'format=sv08-recovery-usr-v1\nroot_uuid={ROOT_UUID}\nroot_bytes={SIZE}\n'
                f'usr_path=/usr.squashfs\nusr_bytes={compressed.stat().st_size}\nusr_sha256={sha(compressed)}\n')
    put(envelope / 'etc/sv08/recovery-envelope.manifest', manifest)
    boot = work / 'boot'
    boot.mkdir()
    for name in ('Image', 'sv08.dtb'):
        shutil.copyfile(envelope / 'boot' / name, boot / name)
    spec = json.loads((REPO/'configs/host-os/sv08-sd-network-inputs.json').read_text())
    for name, expected in [('Image', spec['kernel_raw_sha256']), ('sv08.dtb', spec['dtb_sha256'])]:
        if sha(boot/name) != expected:
            raise ValueError('Source kernel/DT differs from pin')
    links = ''.join(f'{os.readlink(path)}\t{path.relative_to(envelope)}\n'
                    for path in sorted(envelope.rglob('*')) if path.is_symlink() and not path.is_relative_to(envelope/'usr') and not path.is_relative_to(envelope/'boot'))
    put(envelope/'etc/sv08/sd-envelope.links',links)
    links_digest=sha(envelope/'etc/sv08/sd-envelope.links')
    inventory = ''.join(f'{sha(path)}  {path.relative_to(envelope)}\n'
                        for path in sorted((envelope/'etc').rglob('*'))
                        if path.is_file() and not path.is_symlink())
    put(envelope/'etc/sv08/sd-envelope.sha256', inventory)
    config_digest = sha(envelope/'etc/sv08/sd-envelope.sha256')
    init = work / 'initramfs'
    init.mkdir()
    with gzip.open(reuse/'boot/initrd.img' if reuse else envelope/'boot/initrd-recovery.img', 'rb') as stream:
        run('cpio', '-idmu', '--no-absolute-filenames', cwd=init, input=stream.read())
    vm_release='6.12.107+deb13-arm64'
    if reuse:
        shutil.copyfile(reuse/'vm-vmlinuz',work/'vm-vmlinuz')
        module_root=work/'vm-modules'
        run('unsquashfs','-d',module_root,compressed,'lib/modules/'+vm_release)
    else:
        shutil.copyfile(envelope/'boot'/('vmlinuz-'+vm_release),work/'vm-vmlinuz')
        module_root=envelope
    vm_module_hashes={}
    for module in ('virtio_pci','virtio_blk','virtio_mmio','ext4','loop','squashfs'):
        depends=run('modprobe','-d',module_root,'-S',vm_release,'--show-depends',module).decode()
        for line in depends.splitlines():
            if line.startswith('insmod '):
                path=Path(line.split()[1]).relative_to(module_root)
                relative=Path('usr')/path if path.parts[0]=='lib' else path
                target=init/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(module_root/path,target)
                vm_module_hashes[str(relative)]=sha(target)
    metadata=module_root/('lib/modules' if reuse else 'usr/lib/modules')/vm_release
    dest=init/'usr/lib/modules'/vm_release
    dest.mkdir(parents=True,exist_ok=True)
    for path in metadata.glob('modules.*'):
        if path.is_file():shutil.copyfile(path,dest/path.name)
    if reuse:
        shutil.rmtree(module_root)
    else:
        shutil.rmtree(envelope/'usr')
        (envelope/'usr').mkdir()
    put(init / 'init', gate(config_digest,links_digest), 0o755)
    names = sorted(str(p.relative_to(init)) for p in init.rglob('*'))
    archive = run('cpio', '--null', '-o', '--format=newc', '--reproducible', '--owner=0:0',
                  cwd=init, input=('\0'.join(['.', *names])+'\0').encode())
    with (boot / 'initrd.img').open('wb') as stream:
        with gzip.GzipFile(filename='', mode='wb', mtime=EPOCH, fileobj=stream) as out:
            out.write(archive)
    shutil.rmtree(init)
    kernel_compression_support={}
    for release in ('6.18.51-sv08-candidate1','6.12.107+deb13-arm64'):
        config=envelope/'boot'/('config-'+release)
        if 'CONFIG_SQUASHFS_ZSTD=y' not in config.read_text().splitlines():
            raise ValueError('Pinned kernel lacks selected zstd support')
        kernel_compression_support[release]=sha(config)
    # No stale recovery.scr or board boot script is included in SD root.
    shutil.rmtree(envelope / 'boot')
    (envelope / 'boot').mkdir()
    root = work / 'recovery.ext4'
    with root.open('xb') as stream:
        stream.truncate(SIZE)
    for path in [envelope,*envelope.rglob('*')]:
        os.utime(path,(EPOCH,EPOCH),follow_symlinks=False)
    run('mkfs.ext4', '-q', '-F', '-U', ROOT_UUID, '-E', 'hash_seed='+ROOT_UUID+',lazy_itable_init=0,lazy_journal_init=0', '-L', 'SV08_SD_REC', '-d', envelope, root, env=dict(os.environ,E2FSPROGS_FAKE_TIME=str(EPOCH)))
    measure()
    hashes = {p.name: sha(p) for p in boot.iterdir()}
    binding = hashlib.sha256(manifest.encode()).hexdigest()
    put(work / 'boot.cmd', boot_script(hashes, binding))
    run('mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none', '-n', 'SD recovery host test', '-d', work/'boot.cmd', boot/'boot.scr', env=dict(os.environ,SOURCE_DATE_EPOCH=str(EPOCH)))
    from build_sd_network_image import default_environment
    put(work / 'loader-default.env', default_environment(sha(boot/'boot.scr')))
    if any(sha(Path(path)) != digest for path, digest in inputs.items()):
        raise ValueError('Source changed during composition')
    if any(sha(Path(path)) != digest for path,digest in payload_before.items()):
        raise ValueError('Installed payload changed during composition')
    record = dict(format_version=1, deployable=False, hardware_profile='test-sv08-01',
                  physical_boot=False, source_preserved=True, peak_allocated_build_bytes=peak_allocated, inputs=inputs,
                  compression='zstd-level10' if not reuse else reuse_record.get('compression','xz'), usr_sha256=sha(compressed), reused_userspace=bool(reuse), root_sha256=sha(root), root_bytes=SIZE, root_partuuid=PARTUUID,
                  root_uuid=ROOT_UUID, root_index=2, manifest_sha256=binding,
                  boot_gate_sha256=hashlib.sha256(gate(config_digest,links_digest).encode()).hexdigest(),
                  payloads={p.name: {'sha256':sha(p), 'bytes':p.stat().st_size} for p in boot.iterdir()},
                  test_only_authorized_key=bool(test_public), config_inventory_sha256=config_digest,links_inventory_sha256=links_digest,
                  host_keys='volatile Ed25519; re-enroll after every fresh boot; fingerprint on console',
                  authorized_key_fingerprint=run('ssh-keygen', '-lf', public).decode().strip(),
                  vm_initramfs_modules=vm_module_hashes,kernel_compression_support=kernel_compression_support, baseline_virtual_providers={'lsb-base':{'package':'sysvinit-utils','version':'3.14-4','source_lock':'configs/host-os/recovery-packages.json'}}, owner_namespace=namespace, shared_license_notices=license_hashes, runtime_loader_dependencies=runtime_dependencies, package_provenance=json.loads(package_manifest.read_text()), additional_package_provenance=json.loads(additional.read_text()) if additional else None, package_overlay_changes=overlays,
                  vm_kernel_sha256=sha(work/'vm-vmlinuz'), tools={tool: run(tool, '-version' if tool=='mksquashfs' else '--version').decode(errors='replace').splitlines()[0] for tool in ('python3', 'mksquashfs', 'dpkg-deb')})
    shutil.copyfile(Path(__file__),work/'builder-source.py')
    record['builder_source_archive_sha256']=sha(work/'builder-source.py')
    put(work/'composition.json', json.dumps(record, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'packages', 'public-key', 'work'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--owner-mapping',type=Path,required=True)
    parser.add_argument('--additional-packages',type=Path)
    parser.add_argument('--sudo-pam',type=Path)
    parser.add_argument('--sudo-i-pam',type=Path)
    parser.add_argument('--reuse',type=Path,help='Hash-checked compressed userspace cache from identical package manifest')
    parser.add_argument('--test-public-key', type=Path, help='Explicit offline authentication fixture; omit for owner-only candidate')
    parser.add_argument('--execute', action='store_true')
    compose(parser.parse_args())




def assemble(build, loader, receipt_path, output, execute=False):
    """Join a freshly compiled SD-only loader to this host's exact script."""
    build, loader, receipt_path, output = safe(build), safe(loader, True), safe(receipt_path, True), safe(output)
    sidecar=safe(output.parent/(output.name+'.json'))
    fat=safe(output.parent/(output.name+'.fat'))
    for generated in (output,sidecar,fat):
        if generated.exists() or generated in build.parents or build in generated.parents:
            raise ValueError('Fresh separate disk image/receipt/FAT outputs required')
        if generated in (loader,receipt_path):
            raise ValueError('Generated output aliases loader input')
    record = json.loads((build/'composition.json').read_text())
    receipt = json.loads(receipt_path.read_text())
    required = {'deployable':False, 'boot_script_sha256':sha(build/'boot/boot.scr'),
                'loader_sha256':sha(loader), 'environment_sha256':sha(build/'loader-default.env')}
    if any(receipt.get(k) != v for k,v in required.items()):
        raise ValueError('Loader receipt is not bound to this exact script/environment')
    from build_sd_network_image import inspect_config
    config = safe(receipt_path.parent/receipt['config_filename'], True)
    inspect_config(config)
    if sha(config) != receipt.get('config_sha256'):
        raise ValueError('Compiled loader configuration changed')
    if loader.read_bytes()[4:12] != b'eGON.BT0' or loader.stat().st_size+8192 > 1048576:
        raise ValueError('Loader placement/header mismatch')
    if sha(build/'recovery.ext4') != record['root_sha256']:
        raise ValueError('Recovery root changed')
    for name,item in record['payloads'].items():
        if sha(build/'boot'/name) != item['sha256']:
            raise ValueError('Boot payload changed')
    if not execute:
        return dict(execute=False, image_bytes=704*1024**2, root_index=2)
    # All three output paths were admitted before mutation.
    with fat.open('xb') as stream:
        stream.truncate(128*1024**2)
    run('mkfs.vfat', '-F', '32', '-i', '53563038', '-n', 'SV08_SD_REC', fat)
    for path in sorted((build/'boot').iterdir()):
        run('mcopy', '-i', fat, path, '::/'+path.name)
    with output.open('xb') as stream:
        stream.truncate(704*1024**2)
    run('sgdisk', '--clear', '--move-main-table=4096',
        '--disk-guid=0df5e102-4b29-4ac9-a432-e2b8dcd69d7f',
        '--new=1:32768:294911', '--typecode=1:0700', '--change-name=1:sd-boot',
        '--partition-guid=1:91a855d4-e0d7-4bd5-ab68-62c44d36e60f',
        '--new=2:294912:1343487', '--typecode=2:8300', '--change-name=2:sd-recovery',
        '--partition-guid=2:'+PARTUUID, output)
    with output.open('r+b') as target:
        for offset,path in ((8192,loader),(16*1024**2,fat),(144*1024**2,build/'recovery.ext4')):
            target.seek(offset)
            with path.open('rb') as source:
                shutil.copyfileobj(source,target)
        target.flush(); os.fsync(target.fileno())
    run('sgdisk','--verify',output)
    fat.unlink()
    result=dict(deployable=False, image_sha256=sha(output), image_bytes=output.stat().st_size,
                source_composition_sha256=sha(build/'composition.json'), loader_receipt_sha256=sha(receipt_path),
                root_index=2, root_partuuid=PARTUUID, physical_boot=False)
    put(sidecar,json.dumps(result,indent=2)+'\n')
    return result

if __name__ == '__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='assemble':
        parser=argparse.ArgumentParser(description='Regular-file SD disk assembly')
        for name in ('build','loader','loader-receipt','output'):
            parser.add_argument('--'+name,type=Path,required=True)
        parser.add_argument('--execute',action='store_true')
        args=parser.parse_args(sys.argv[2:])
        print(json.dumps(assemble(args.build,args.loader,args.loader_receipt,args.output,args.execute)))
    else:
        main()
