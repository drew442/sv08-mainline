#!/usr/bin/env python3
"""Assemble a private host-only image using standard tools; never flash hardware.

See docs/decisions/0002-first-emmc-image.md for scope and retirement plan.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile

REPO = Path(__file__).resolve().parents[1]
PACKAGES = ('systemd-sysv', 'systemd-resolved', 'systemd-timesyncd', 'dbus', 'udev', 'openssh-server',
            'sudo', 'ca-certificates', 'curl', 'git', 'python3', 'python3-venv',
            'python3-dev', 'build-essential', 'libffi-dev', 'libusb-1.0-0',
            'usbutils', 'initramfs-tools', 'kmod', 'iproute2', 'iputils-ping',
            'e2fsprogs', 'dosfstools', 'wireless-regdb')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def regular(path):
    path = Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f'Expected regular file, not symlink/device: {path}')
    return path


def layout(c):
    size = c['image_bytes']
    boot = c['boot_start_sector'] * 512
    root = c['root_start_sector'] * 512
    if not (boot == 4194304 and root == boot + c['boot_sectors'] * 512
            and size > root and size % 512 == 0):
        raise ValueError('Invalid or overlapping image layout')
    return boot, root, size - root


def run(*args, **kwargs):
    print('+', ' '.join(str(a) for a in args), flush=True)
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def write(root, name, text, mode=0o644):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    p.chmod(mode)


def unpack_support(archive, target):
    # Only regular boot/module/firmware files; no archive-controlled links/devices.
    with tarfile.open(archive) as t:
        for member in t:
            p = Path(member.name)
            if p.is_absolute() or '..' in p.parts:
                raise ValueError('Unsafe archive path')
            if not member.isfile() or p.parts[:1] not in (('boot',), ('lib',)):
                continue
            if p.parts[0] == 'lib' and p.parts[1:2] not in (('modules',), ('firmware',)):
                continue
            dest = target / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            with t.extractfile(member) as src, dest.open('xb') as out:
                shutil.copyfileobj(src, out)
            dest.chmod(member.mode & 0o777)


def configure(c, work, archive, keys):
    root = work / 'rootfs'
    if not (root / 'debootstrap/debootstrap').is_file():
        raise ValueError('Run bootstrap first; configure requires an unused foreign bootstrap')
    run('chroot', root, '/debootstrap/debootstrap', '--second-stage')
    write(root, 'usr/sbin/policy-rc.d', '#!/bin/sh\nexit 101\n', 0o755)
    mirror = f"https://snapshot.debian.org/archive/debian/{c['snapshot']}/"
    security = f"https://snapshot.debian.org/archive/debian-security/{c['snapshot']}/"
    write(root, 'etc/apt/sources.list',
          f"deb [check-valid-until=no] {mirror} {c['suite']} main\n"
          f"deb [check-valid-until=no] {security} {c['suite']}-security main\n")
    # Snapshot URLs are immutable inputs; release/package signatures remain required.
    shutil.copyfile('/etc/resolv.conf', root / 'etc/resolv.conf')
    (root / 'etc/ssl/certs').mkdir(parents=True, exist_ok=True)
    shutil.copyfile('/etc/ssl/certs/ca-certificates.crt', root / 'etc/ssl/certs/ca-certificates.crt')
    run('mount', '-t', 'proc', 'proc', root / 'proc')
    try:
        run('chroot', root, 'apt-get', 'update')
        run('chroot', root, '/usr/bin/env', 'DEBIAN_FRONTEND=noninteractive',
            'apt-get', 'install', '-y', '--no-install-recommends', *PACKAGES)
        support = work / 'support'
        support.mkdir()
        unpack_support(archive, support)
        k = c['kernel']
        shutil.copytree(support / 'lib/modules' / k, root / 'usr/lib/modules' / k)
        for name in ('Image', 'boot.cmd', f'config-{k}'):
            shutil.copyfile(support / 'boot' / name, root / 'boot' / name)
        shutil.copytree(support / 'boot/dtb', root / 'boot/dtb')
        # Preserve hardware-related environment lines, including duplicate overlays;
        # root identity and boot presentation are explicitly selected for this image.
        allowed = {'overlay_prefix', 'fdtfile', 'overlays', 'user_overlays',
                   'param_spidev_spi_bus', 'param_spidev_spi_cs'}
        env = [line for line in (support / 'boot/BoardEnv.txt').read_text().splitlines()
               if line.partition('=')[0] in allowed]
        if f"fdtfile={c['dtb']}" not in env:
            raise ValueError('Captured DTB selection does not match profile')
        env += [f"rootdev=UUID={c['root_uuid']}", 'rootfstype=ext4',
                'console=detail', 'bootlogo=false', 'docker_optimizations=off']
        write(root, 'boot/BoardEnv.txt', '\n'.join(env) + '\n')
        run('chroot', root, 'depmod', '-a', k)
        write(root, 'etc/initramfs-tools/conf.d/sv08', 'COMPRESS=gzip\nMODULES=most\n')
        run('chroot', root, 'update-initramfs', '-c', '-k', k)
        run('mkimage', '-A', 'arm', '-O', 'linux', '-T', 'ramdisk', '-C', 'gzip',
            '-n', 'SV08 host bring-up', '-d', root / f'boot/initrd.img-{k}', root / 'boot/uInitrd')
        run('mkimage', '-A', 'arm', '-T', 'script', '-C', 'none', '-d',
            root / 'boot/boot.cmd', root / 'boot/boot.scr')
        write(root, 'etc/fstab',
              f"UUID={c['root_uuid']} / ext4 defaults,noatime,errors=remount-ro 0 1\n"
              f"UUID={c['fat_id'][:4]}-{c['fat_id'][4:]} /boot vfat defaults 0 2\n")
        write(root, 'etc/hostname', 'sv08-mainline\n')
        write(root, 'etc/hosts', '127.0.0.1 localhost\n127.0.1.1 sv08-mainline\n::1 localhost ip6-localhost\n')
        write(root, 'etc/systemd/network/20-wired.network',
              '[Match]\nType=ether\nName=eth* en*\n\n[Network]\nDHCP=yes\n')
        run('chroot', root, 'useradd', '-m', '-s', '/bin/bash', '-G', 'sudo,dialout', 'sovol')
        write(root, 'etc/sudoers.d/sovol', 'sovol ALL=(ALL) NOPASSWD: ALL\n', 0o440)
        write(root, 'home/sovol/.ssh/authorized_keys', keys.read_text(), 0o600)
        (root / 'home/sovol/.ssh').chmod(0o700)
        run('chroot', root, 'chown', '-R', 'sovol:sovol', '/home/sovol/.ssh')
        write(root, 'etc/ssh/sshd_config.d/10-sv08.conf',
              'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\n')
        for p in (root / 'etc/ssh').glob('ssh_host_*'):
            p.unlink()
        write(root, 'etc/systemd/system/sv08-ssh-host-keys.service',
              '[Unit]\nDescription=Generate SSH host keys for this module\nBefore=ssh.service\n'
              '[Service]\nType=oneshot\nExecStart=/usr/bin/ssh-keygen -A\nRemainAfterExit=yes\n'
              '[Install]\nWantedBy=multi-user.target\n')
        write(root, 'etc/systemd/system/ssh.service.d/host-keys.conf',
              '[Unit]\nRequires=sv08-ssh-host-keys.service\nAfter=sv08-ssh-host-keys.service\n')
        for svc in ('systemd-networkd', 'systemd-resolved', 'systemd-timesyncd', 'ssh', 'sv08-ssh-host-keys'):
            run('systemctl', '--root', root, 'enable', svc)
        (root / 'etc/resolv.conf').unlink()
        (root / 'etc/resolv.conf').symlink_to('/run/systemd/resolve/stub-resolv.conf')
        lock = json.loads((REPO / 'upstream-lock.json').read_text())
        klipper = next(x for x in lock['submodules'] if x['path'] == 'upstream/klipper')
        actual = subprocess.check_output(['git', '-C', str(REPO / klipper['path']), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != klipper['commit']:
            raise ValueError('Klipper source is not at selected pin')
        source = root / 'opt/sv08-mainline/klipper'
        source.parent.mkdir(parents=True, exist_ok=True)
        run('git', '-C', REPO / klipper['path'], 'archive', '--format=tar',
            '--output=' + str(work / 'klipper.tar'), actual)
        source.mkdir()
        run('tar', '-xf', work / 'klipper.tar', '-C', source)
        write(root, 'opt/sv08-mainline/SOURCE_COMMIT', actual + '\n')
        write(root, 'etc/motd', 'SV08 host bring-up candidate: printer services are not installed.\n'
              'Validate storage/network first. No MCU firmware has been changed.\n')
        finalize(work)
    finally:
        run('umount', root / 'proc')


def finalize(work):
    root = work / 'rootfs'
    with (work / 'packages.tsv').open('w') as out:
        run('chroot', root, 'dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\n', stdout=out)
    run('chroot', root, 'dpkg', '--audit')
    run('chroot', root, 'visudo', '-c')
    run('chroot', root, 'apt-get', 'clean')
    (root / 'usr/sbin/policy-rc.d').unlink(missing_ok=True)
    for p in (root / 'etc/ssh').glob('ssh_host_*'):
        p.unlink()
    write(root, 'etc/machine-id', '')
    dbus_id = root / 'var/lib/dbus/machine-id'
    if dbus_id.exists() or dbus_id.is_symlink():
        dbus_id.unlink()
    dbus_id.symlink_to('/etc/machine-id')
    for p in (root / 'var/log').rglob('*'):
        if p.is_file() and not p.is_symlink():
            p.write_bytes(b'')
    (work / 'configured').write_text('complete\n')


def assemble(c, work, prefix, output):
    for candidate in (output, output.with_suffix('.json'), output.with_suffix('.sha256'),
                      output.with_suffix('.packages.tsv')):
        if candidate.exists() or candidate.is_symlink():
            raise ValueError(f'Output must not exist: {candidate}')
    if not (work / 'configured').is_file():
        raise ValueError('Configure rootfs first')
    boot_offset, root_offset, root_bytes = layout(c)
    root = work / 'rootfs'
    fat = work / 'boot.fat'
    ext = work / 'root.ext4'
    for p, size in ((fat, c['boot_sectors'] * 512), (ext, root_bytes)):
        with p.open('xb') as f:
            f.truncate(size)
    run('mkfs.vfat', '-F', '16', '-i', c['fat_id'], '-n', 'SV08BOOT', fat)
    run('mcopy', '-s', '-i', fat, *sorted((root / 'boot').iterdir()), '::/')
    run('mkfs.ext4', '-F', '-U', c['root_uuid'], '-L', 'sv08-root',
        '-O', '^metadata_csum_seed,^orphan_file', '-d', root, ext)
    run('fsck.vfat', '-n', fat)
    run('e2fsck', '-f', '-n', ext)
    with output.open('xb') as f:
        output.chmod(0o600)
        f.truncate(c['image_bytes'])
        with prefix.open('rb') as inp:
            shutil.copyfileobj(inp, f)
    table = (f"label: dos\nlabel-id: {c['disk_id']}\nunit: sectors\n\n"
             f"start={c['boot_start_sector']}, size={c['boot_sectors']}, type=e\n"
             f"start={c['root_start_sector']}, size={root_bytes // 512}, type=83\n")
    # sfdisk is restricted to the new regular file, preserving bytes after the MBR.
    regular(output)
    run('sfdisk', '--no-reread', '--no-tell-kernel', output, input=table, text=True)
    with output.open('r+b') as f:
        for part, offset in ((fat, boot_offset), (ext, root_offset)):
            f.seek(offset)
            with part.open('rb') as src:
                shutil.copyfileobj(src, f, 4 * 1024 * 1024)
    with output.open('rb') as f, prefix.open('rb') as src:
        f.seek(512); src.seek(512)
        if f.read(boot_offset - 512) != src.read(boot_offset - 512):
            raise ValueError('Bootloader prefix changed outside partition table sector')
    table_readback = json.loads(subprocess.check_output(['sfdisk', '--json', str(output)], text=True))['partitiontable']
    expected = [(c['boot_start_sector'], c['boot_sectors'], 'e'),
                (c['root_start_sector'], root_bytes // 512, '83')]
    actual = [(p['start'], p['size'], p['type']) for p in table_readback['partitions']]
    if actual != expected:
        raise ValueError('Assembled partition table mismatch')
    with output.open('rb') as f:
        for part, offset in ((fat, boot_offset), (ext, root_offset)):
            f.seek(offset)
            h = hashlib.sha256()
            remaining = part.stat().st_size
            while remaining:
                data = f.read(min(4 * 1024 * 1024, remaining))
                if not data:
                    raise ValueError('Truncated image partition')
                h.update(data)
                remaining -= len(data)
            if h.hexdigest() != sha(part):
                raise ValueError('Assembled partition content mismatch')
    tools = {}
    for name, command in {
        'debootstrap': ['debootstrap', '--version'],
        'qemu': ['qemu-aarch64-static', '--version'],
        'mkfs.ext4': ['mkfs.ext4', '-V'],
        'mkimage': ['mkimage', '-V'],
        'sfdisk': ['sfdisk', '--version'],
        'mcopy': ['mcopy', '-V'],
    }.items():
        r = subprocess.run(command, capture_output=True, text=True, check=True)
        tools[name] = (r.stdout + r.stderr).strip()
    result = dict(profile=c, tools=tools, recipe_sha256=sha(Path(__file__)),
                  source_klipper_commit=(root / 'opt/sv08-mainline/SOURCE_COMMIT').read_text().strip(),
                  kernel_sha256=sha(root / 'boot/Image'),
                  dtb_sha256=sha(root / f"boot/dtb/allwinner/{c['dtb']}.dtb"),
                  authorized_keys_sha256=sha(root / 'home/sovol/.ssh/authorized_keys'),
                  image=output.name, bytes=output.stat().st_size,
                  sha256=sha(output), packages_sha256=sha(work / 'packages.tsv'),
                  hardware_tested=False, mcu_firmware_included=False,
                  limitations=['Captured vendor kernel/bootloader, not source-reproduced',
                               'Host bring-up only; printer services absent',
                               'Byte-identical rebuild not established'])
    shutil.copyfile(work / 'packages.tsv', output.with_suffix('.packages.tsv'))
    output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    output.with_suffix('.sha256').write_text(f"{result['sha256']}  {output.name}\n")
    for artifact in (output, output.with_suffix('.json'), output.with_suffix('.sha256'),
                     output.with_suffix('.packages.tsv')):
        artifact.chmod(0o600)
        if os.environ.get('SUDO_UID') and os.environ.get('SUDO_GID'):
            os.chown(artifact, int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID']))
    print(json.dumps(result, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', type=Path, default=REPO / 'configs/images/test-sv08-01-host.json')
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--stage', choices=('bootstrap', 'configure', 'assemble'), required=True)
    p.add_argument('--vendor-archive', type=Path)
    p.add_argument('--prefix', type=Path)
    p.add_argument('--authorized-keys', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    c = json.loads(args.profile.read_text())
    layout(c)
    work = args.work.resolve()
    if not work.is_relative_to(REPO / 'build') or work == REPO / 'build':
        p.error('Work directory must be a dedicated directory below repository build/')
    if args.output and (not args.output.resolve().is_relative_to(REPO / 'artifacts')
                        or args.output.exists() or args.output.is_symlink()):
        p.error('Output must be a new file below repository artifacts/')
    for path, field in ((args.vendor_archive, 'vendor_archive_sha256'), (args.prefix, 'prefix_sha256')):
        if path and sha(regular(path)) != c[field]:
            p.error(f'Input hash does not match profile: {path}')
    if args.authorized_keys:
        regular(args.authorized_keys)
        if not args.authorized_keys.read_text().strip():
            p.error('Authorized keys must not be empty')
    print(f"{args.stage}: {c['profile']}; work={work}; execute={args.execute}")
    if not args.execute:
        return
    if os.geteuid() != 0:
        p.error('Build execution needs root for debootstrap/chroot and ownership')
    os.umask(0o022)
    work.mkdir(parents=True, exist_ok=True)
    work.chmod(0o700)
    if args.stage == 'bootstrap':
        if (work / 'rootfs').exists():
            p.error('Bootstrap rootfs must not already exist')
        run('debootstrap', '--arch=arm64', '--foreign', '--variant=minbase',
            '--force-check-gpg', c['suite'], work / 'rootfs',
            f"https://snapshot.debian.org/archive/debian/{c['snapshot']}/")
    elif args.stage == 'configure':
        if not args.vendor_archive or not args.authorized_keys:
            p.error('Configure needs --vendor-archive and --authorized-keys')
        configure(c, work, args.vendor_archive.resolve(), args.authorized_keys.resolve())
    else:
        if not args.prefix or not args.output:
            p.error('Assemble needs --prefix and --output')
        assemble(c, work, args.prefix.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
