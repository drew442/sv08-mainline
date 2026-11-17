#!/usr/bin/env python3
"""Stage persistence/service integration into an isolated completed rootfs.

No hardware access; default dry-run. Requires a caller-supplied release/GPT
manifest. This does not supply a board bootloader, DTB or recovery kernel.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import sys
from prepare_host_os import REPO, work_path


def validate(manifest, *, supported=False):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', manifest['release']):
        raise ValueError('Invalid release identifier')
    if manifest['state_schema'] != 1:
        raise ValueError('Unsupported state schema')
    if 'release_revision' in manifest and (type(manifest['release_revision']) is not int or manifest['release_revision'] < 1):
        raise ValueError('Release revision must be an explicit positive integer')
    devices = manifest['devices']
    if set(devices) != {'boot-a','root-a','boot-b','root-b','data','recovery'}:
        raise ValueError('Manifest needs all six explicit GPT partitions')
    for path in devices.values():
        if not path.startswith('/dev/disk/by-partuuid/') or path.rsplit('/', 1)[-1] != str(uuid.UUID(path.rsplit('/', 1)[-1])):
            raise ValueError('Use explicit GPT PARTUUID paths')
    if len(set(devices.values())) != 6:
        raise ValueError('Partitions must be distinct')
    if supported:
        if (manifest.get('deployable') is not True or manifest.get('owner_setup') != 'recovery-v1' or
                manifest.get('commissioning') != 'explicit-v1' or
                manifest.get('hardware_profile') != 'test-sv08-01' or
                type(manifest.get('release_revision')) is not int or manifest['release_revision'] < 1):
            raise ValueError('Explicit supported commissioning/owner profile required')
    elif manifest.get('deployable') is not False:
        raise ValueError('This integration stage is still an offline candidate')


def owner_key_source(root, owner_key):
    source = Path(owner_key) if owner_key is not None else root / 'home/sovol/.ssh/authorized_keys'
    if source.is_symlink() or not source.is_file():
        raise ValueError('Host image must provide a non-empty regular owner authorized-key seed')
    content = source.read_bytes()
    if not content.strip():
        raise ValueError('Host image must provide a non-empty regular owner authorized-key seed')
    return content


def rebuild_initramfs(root):
    """Make the staged identity/data hooks part of every target initramfs."""
    result = subprocess.run(
        ['chroot', str(root), 'update-initramfs', '-u', '-k', 'all'],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=900)
    if result.stdout:
        print(result.stdout, end='')


def admission_subtree(target):
    """Recognize only the exact pinned package payload before touching runtime."""
    extras = target / 'klipper-extras'
    if not extras.exists() and not extras.is_symlink():
        return None
    extension = extras / 'sv08_update.py'
    if (extras.is_symlink() or not extras.is_dir() or
            {path.name for path in extras.iterdir()} != {'sv08_update.py'} or
            extension.is_symlink() or not extension.is_file()):
        raise ValueError('Existing admission extension subtree is unrecognized')
    pin = json.loads((REPO / 'configs/apps/update-admission.json').read_text())
    source = REPO / pin['source']
    if (hashlib.sha256(source.read_bytes()).hexdigest() != pin['source_sha256'] or
            hashlib.sha256(extension.read_bytes()).hexdigest() != pin['source_sha256']):
        raise ValueError('Existing admission extension does not match the pinned source')
    return extras


def firmware_manifest(manifest):
    sys.path.insert(0,str(REPO/'runtime'))
    from sv08_printer_firmware import release_assignment
    from sv08_printer_definitions import builtins
    from sv08_printer_catalog import Catalog
    from sv08_printer_calibration import KLIPPER_REVISION
    if manifest.get('klipper_commit',KLIPPER_REVISION)!=KLIPPER_REVISION:
        raise ValueError('Release host Klipper pin differs from MCU definitions')
    assignment=release_assignment(manifest['release'],KLIPPER_REVISION,builtins(Catalog(REPO/'catalog/printer/catalog.json')))
    if 'mcu_firmware' in manifest and manifest['mcu_firmware']!=assignment:
        raise ValueError('Supplied MCU assignment differs from release definitions')
    manifest={**manifest,'mcu_firmware':assignment}
    if len((json.dumps(manifest,indent=2)+'\n').encode())>65536:
        raise ValueError('Release manifest exceeds the boot metadata bound')
    return manifest


def stage(work, manifest, refresh=False, owner_key=None, *, supported_profile=None, release_certificate=None):
    supported = supported_profile is not None
    validate(manifest, supported=supported)
    if supported:
        from supported_candidate import profile_check, public_certificate, regular
        if manifest != profile_check(supported_profile) or owner_key is not None:
            raise ValueError('Supported integration requires exact profile and no baked owner access key')
        public_certificate(release_certificate)
    manifest=firmware_manifest(manifest)
    root = work / 'rootfs'
    if root.is_symlink() or not root.is_dir() or not (work / 'refresh-complete').is_file():
        raise ValueError('Use an isolated completed baseline copy')
    target = root / 'usr/lib/sv08'
    target_exists = target.exists() or target.is_symlink()
    admission = None
    if target_exists:
        if target.is_symlink() or not target.is_dir():
            raise ValueError('Existing integration target is not a regular directory')
        admission = admission_subtree(target)
        if not refresh and (admission is None or list(target.iterdir()) != [admission]):
            raise ValueError('Integration is already staged or contains unknown files; use a fresh copy')
    command_links = []
    for command, module in [('sv08-state', 'sv08_state.py'), ('sv08-package', 'sv08_package.py')]:
        link = root / 'usr/bin' / command
        if link.exists() or link.is_symlink():
            if not refresh or not link.is_symlink() or os.readlink(link) != '../lib/sv08/' + module:
                raise ValueError('Existing runtime command conflicts with integration: ' + command)
            command_links.append((link, module))
    existing = (root / 'etc/passwd').read_text().splitlines()
    owner = [line.split(':') for line in existing if line.startswith('sv08:')]
    if owner and owner[0][2:4] != ['1000', '1000']:
        raise ValueError('Existing sv08 user must have the reviewed UID/GID 1000')
    if not owner and any(line.split(':')[2] == '1000' for line in existing):
        raise ValueError('UID 1000 is occupied; do not reassign an existing user')
    groups = (root / 'etc/group').read_text().splitlines()
    if not owner and any(line.split(':')[2] == '1000' for line in groups):
        raise ValueError('GID 1000 is occupied; do not reassign an existing group')
    key_seed = b'' if supported else owner_key_source(root, owner_key)
    # All refresh preconditions are checked before replacing the existing runtime.
    if target_exists:
        # The admission Debian package owns this subtree. Preserve its validated
        # bytes and metadata while replacing only integration-owned runtime.
        for child in target.iterdir():
            if child == admission:
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    target.mkdir(parents=True, exist_ok=True)
    for path in (REPO / 'runtime').glob('*.py'):
        shutil.copyfile(path, target / path.name)
    (target / 'sv08_rauc_bootloader.py').chmod(0o755)
    for command, module in [('sv08-state', 'sv08_state.py'), ('sv08-package', 'sv08_package.py')]:
        (target / module).chmod(0o755)
        link = root / 'usr/bin' / command
        if (link, module) in command_links:
            link.unlink()
        link.symlink_to('../lib/sv08/' + module)
    (root / 'etc/default').mkdir(parents=True, exist_ok=True)
    (root / 'etc/default/locale').write_text('LANG=C.UTF-8\n')
    (target / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copyfile(REPO / 'configs/host-os/software-catalog.json', target / 'software-catalog.json')
    seed = target / 'seed/config'
    seed.mkdir(parents=True)
    sys.path.insert(0,str(REPO/'runtime'))
    from sv08_printer_stack import MOONRAKER, NGINX, MAINSail
    (seed/'moonraker.conf').write_text(MOONRAKER)
    (seed/'nginx-mainsail.conf').write_text(NGINX)
    (seed/'mainsail.json').write_text(json.dumps(MAINSail, indent=2)+'\n')
    web_config = root / 'etc/sv08'
    web_config.mkdir(exist_ok=True)
    shutil.copyfile(REPO / 'configs/host-os/nginx-mainsail-service.conf',
                    web_config / 'nginx-mainsail-service.conf')
    units = root / 'etc/systemd/system'
    for path in (REPO / 'configs/host-os/systemd').glob('*.service'):
        shutil.copyfile(path, units / path.name)
    for name in ('sv08-identity.service','sv08-identity.timer'):
        shutil.copyfile(REPO / 'configs/host-os' / name, units / name)
    shutil.copyfile(REPO / 'configs/host-os/systemd/sv08-network-rollback.timer', units / 'sv08-network-rollback.timer')
    network_wants = units / 'timers.target.wants'
    network_wants.mkdir(exist_ok=True)
    network_link = network_wants / 'sv08-network-rollback.timer'
    network_link.unlink(missing_ok=True)
    network_link.symlink_to('/etc/systemd/system/sv08-network-rollback.timer')
    identity_wants = units / 'timers.target.wants'
    identity_wants.mkdir(exist_ok=True)
    link = identity_wants / 'sv08-identity.timer'
    link.unlink(missing_ok=True); link.symlink_to('/etc/systemd/system/sv08-identity.timer')
    # Keep Debian's backup job in writable mode; skip its read-only destination.
    backup_dropin = units / 'dpkg-db-backup.service.d'
    backup_dropin.mkdir(exist_ok=True)
    shutil.copyfile(REPO / 'configs/host-os/systemd/dpkg-db-backup.service.d/20-sv08-readonly.conf',
                    backup_dropin / '20-sv08-readonly.conf')
    # Explicit mount unit so offline unit verification includes the dependency.
    data_device = manifest['devices']['data']
    # initramfs fscks and mounts data before PID 1 needs the persistent machine-id.
    # Do not schedule a second fsck on that already-mounted filesystem.
    (units / 'data.mount').write_text(f'[Unit]\nDescription=SV08 persistent data (prepared by initramfs)\n\n[Mount]\nWhat={data_device}\nWhere=/data\nType=ext4\nOptions=nodev,nosuid\n\n[Install]\nWantedBy=local-fs.target\n')
    for source, destination in [('sv08-data', 'scripts/local-bottom/sv08-data'),
                                ('sv08-tools', 'hooks/sv08-tools')]:
        path = root / 'etc/initramfs-tools' / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (REPO / 'configs/host-os/initramfs' / source).read_text()
        path.write_text(content.replace('@DATA_DEVICE@', data_device))
        path.chmod(0o755)
    (root / 'etc/initramfs-tools/conf.d/sv08-fstype').write_text('FSTYPE=ext4\n')
    (root / 'etc/fstab').write_text('# Root starts read-only via boot arguments; sv08-prepare applies the mode.\n# data.mount and sv08-prepare manage explicit persistent and paired boot mounts.\n')
    for path in ('data','home/sv08','etc/NetworkManager/system-connections','var/lib/NetworkManager','var/lib/rauc','var/lib/systemd/timesync','var/lib/systemd/rfkill','var/lib/systemd/linger','var/cache','var/tmp','var/log','run','tmp','boot'):
        (root / path).mkdir(parents=True, exist_ok=True)
    for path in ('etc/machine-id','etc/hostname','etc/hosts','var/lib/systemd/random-seed'):
        if not (root / path).exists():
            (root / path).touch()
    (root / 'etc/hostname').write_text('sv08\n')
    resolv = root / 'etc/resolv.conf'
    resolv.unlink(missing_ok=True)
    resolv.symlink_to('/run/NetworkManager/resolv.conf')
    (root / 'etc/ssh/sshd_config.d').mkdir(exist_ok=True)
    shutil.copyfile(REPO / 'configs/host-os/sshd.conf', root / 'etc/ssh/sshd_config.d/20-sv08.conf')
    seed_dir = root / 'usr/lib/sv08/seed'
    seed_dir.mkdir(parents=True, exist_ok=True)
    (seed_dir / 'authorized_keys').write_bytes(key_seed)
    (seed_dir / 'authorized_keys').chmod(0o644)
    # Only this final stage adds the apt guard, after image package construction.
    shutil.copyfile(REPO / 'configs/host-os/apt-policy.conf', root / 'etc/apt/apt.conf.d/90sv08-policy')
    shutil.copyfile(REPO / 'configs/host-os/policy-rc.d', root / 'usr/sbin/policy-rc.d')
    (root / 'usr/sbin/policy-rc.d').chmod(0o755)
    journal = root / 'etc/systemd/journald.conf.d'
    journal.mkdir(exist_ok=True)
    (journal / 'sv08.conf').write_text('[Journal]\nStorage=persistent\nSystemMaxUse=64M\nRuntimeMaxUse=16M\nMaxRetentionSec=14day\n')
    if not any(line.startswith('sv08:') for line in existing):
        subprocess.run(['chroot', str(root), 'groupadd', '--gid', '1000', 'sv08'], check=True)
        subprocess.run(['chroot', str(root), 'useradd', '--uid', '1000', '--gid', '1000', '--home-dir', '/home/sv08', '--shell', '/bin/bash', '--groups', 'dialout,video', 'sv08'], check=True)
    if supported:
        # Recovery supplies the owner's hash. Do not force a first-login write
        # to the read-only derived shadow, or ship an inherited owner password.
        policy = (REPO/'configs/host-os/supported/owner-password-policy.conf').read_bytes()
        password_stack = root/'etc/pam.d/common-password'
        vendor = regular(root, 'etc/pam.d/common-password')
        if not vendor.startswith(policy):
            password_stack.write_bytes(policy+vendor)
        shadow = root/'etc/shadow'
        rows = [line.split(':') for line in shadow.read_text().splitlines()]
        if any(len(row) != 9 for row in rows): raise ValueError('Invalid supported slot shadow')
        if sum(row[0] == 'sv08' for row in rows) != 1: raise ValueError('Missing supported owner shadow')
        for row in rows:
            if row[0] == 'sv08': row[:] = ['sv08', '*', '', '0', '99999', '7', '', '', '']
        shadow.write_text(''.join(':'.join(row)+'\n' for row in rows))
    sudoers = root / 'etc/sudoers.d/sv08-owner'
    sudoers.write_text('sv08 ALL=(ALL) NOPASSWD: ALL\n')
    sudoers.chmod(0o440)
    for service in ('NetworkManager.service','ssh.service','systemd-random-seed.service',
                    'systemd-timesyncd.service','systemd-rfkill.service','systemd-logind.service','nginx.service'):
        directory = units / (service + '.d')
        directory.mkdir(exist_ok=True)
        dependency = 'sv08-identity.service' if service in ('ssh.service','nginx.service') else 'sv08-prepare.service'
        (directory / 'sv08-state.conf').write_text('[Unit]\nRequires='+dependency+'\nAfter='+dependency+'\n')
    # NetworkManager's sandbox omits CAP_SYS_ADMIN needed for the kernel name.
    # Prepare is unrestricted and completes before NM and identity take their
    # locks; boot cleanup therefore needs neither NM RPC nor a competing flock.
    network_directory = units / 'sv08-prepare.service.d'
    network_directory.mkdir(exist_ok=True)
    (network_directory/'network-rollback.conf').write_text('[Service]\nExecStartPost=/usr/bin/python3 /usr/lib/sv08/sv08_network.py --recover-boot\n')
    # Debian packages may have enabled nginx already; do not expose its default
    # site while authorization/onboarding integration is still outstanding.
    # machine-id is already persistent, not systemd's transient mount to commit.
    for timer in ('apt-daily.timer','apt-daily-upgrade.timer', 'nginx.service',
                  'systemd-machine-id-commit.service'):
        path = units / timer
        if path.exists() or path.is_symlink():
            path.unlink()
        path.symlink_to('/dev/null')
    # This runs after rendering the data PARTUUID and local-bottom hook. The
    # original package build's initramfs predates these files; using it would
    # leave /etc/machine-id unbound and make sv08-prepare fail on first boot.
    rebuild_initramfs(root)
    # The health handoff must run on each boot, including boots with no printer
    # configuration. Klipper remains gated by its config, trial and health markers.
    health_wants = units / 'multi-user.target.wants'
    health_wants.mkdir(exist_ok=True)
    health_link = health_wants / 'sv08-boot-health.service'
    if health_link.exists() or health_link.is_symlink():
        health_link.unlink()
    health_link.symlink_to('../sv08-boot-health.service')
    for name in ('sv08-printer-api.service', 'sv08-mainsail.service'):
        link = health_wants / name
        link.unlink(missing_ok=True)
        link.symlink_to('../' + name)
    observer_wants=units/'sv08-klipper.service.wants'
    observer_wants.mkdir(exist_ok=True)
    observer_link=observer_wants/'sv08-calibration-reconcile.service'
    observer_link.unlink(missing_ok=True)
    observer_link.symlink_to('../sv08-calibration-reconcile.service')
    if supported:
        from supported_candidate import install_backend, public_account_checks
        install_backend(root, supported_profile, release_certificate)
        public_account_checks(root)
        # Keep package aliases masked. The supported entry remains disabled
        # until a separate, reviewed commissioning operation.
        for name in ('klipper', 'moonraker', 'KlipperScreen'):
            path = units/(name+'.service')
            path.unlink(missing_ok=True); path.symlink_to('/dev/null')
        for name in ('sv08-klipper', 'sv08-moonraker'):
            for directory in units.glob('*.wants'):
                (directory/(name+'.service')).unlink(missing_ok=True)
        (units/'sv08-klipper.service.d').mkdir(exist_ok=True)
        shutil.copyfile(REPO/'configs/host-os/systemd/sv08-klipper.service.d/supported-commissioning.conf',
                        units/'sv08-klipper.service.d/supported-commissioning.conf')
    # Physical printer services remain separately gated; no printer.cfg is seeded.
    (work / 'integration-staged.json').write_text(json.dumps(manifest, indent=2)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--refresh', action='store_true',
                   help='Replace only an already staged runtime in a fresh copied root')
    p.add_argument('--owner-key', type=Path,
                   help='Non-empty regular public-key file to seed on first boot')
    p.add_argument('--supported-profile', type=Path,
                   help='Explicit measured named-printer candidate policy; no owner-key seed')
    p.add_argument('--release-certificate', type=Path,
                   help='Public signed-update authority certificate for supported profile')
    a = p.parse_args()
    manifest = json.loads(a.manifest.read_text())
    profile = json.loads(a.supported_profile.read_text()) if a.supported_profile else None
    validate(manifest, supported=profile is not None)
    if profile is not None:
        from supported_candidate import profile_check, public_certificate
        if manifest != profile_check(profile) or a.owner_key is not None:
            raise ValueError('Supported manifest/profile mismatch or baked owner key')
        public_certificate(a.release_certificate)
    elif a.release_certificate is not None:
        raise ValueError('Release certificate requires explicit supported profile')
    work = work_path(a.work)
    print(json.dumps(dict(execute=a.execute, refresh=a.refresh, work=str(work), release=manifest['release'],
                          owner_key=bool(a.owner_key))))
    if a.execute:
        if os.geteuid() != 0:
            p.error('Staging requires root for filesystem ownership and user creation')
        stage(work, manifest, a.refresh, a.owner_key,
              supported_profile=profile, release_certificate=a.release_certificate)


if __name__ == '__main__':
    main()
