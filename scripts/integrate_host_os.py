#!/usr/bin/env python3
"""Stage persistence/service integration into an isolated completed rootfs.

No hardware access; default dry-run. Requires a caller-supplied release/GPT
manifest. This does not supply a board bootloader, DTB or recovery kernel.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from prepare_host_os import REPO, work_path


def validate(manifest):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', manifest['release']):
        raise ValueError('Invalid release identifier')
    if manifest['state_schema'] != 1:
        raise ValueError('Unsupported state schema')
    devices = manifest['devices']
    if set(devices) != {'boot-a','root-a','boot-b','root-b','data','recovery'}:
        raise ValueError('Manifest needs all six explicit GPT partitions')
    for path in devices.values():
        if not path.startswith('/dev/disk/by-partuuid/') or path.rsplit('/', 1)[-1] != str(uuid.UUID(path.rsplit('/', 1)[-1])):
            raise ValueError('Use explicit GPT PARTUUID paths')
    if len(set(devices.values())) != 6:
        raise ValueError('Partitions must be distinct')
    if manifest.get('deployable') is not False:
        raise ValueError('This integration stage is still an offline candidate')


def stage(work, manifest):
    validate(manifest)
    root = work / 'rootfs'
    if root.is_symlink() or not (work / 'refresh-complete').is_file():
        raise ValueError('Use an isolated completed baseline copy')
    target = root / 'usr/lib/sv08'
    if target.exists():
        raise ValueError('Integration is already staged; use a fresh copy')
    existing = (root / 'etc/passwd').read_text().splitlines()
    owner = [line.split(':') for line in existing if line.startswith('sv08:')]
    if owner and owner[0][2:4] != ['1000', '1000']:
        raise ValueError('Existing sv08 user must have the reviewed UID/GID 1000')
    if not owner and any(line.split(':')[2] == '1000' for line in existing):
        raise ValueError('UID 1000 is occupied; do not reassign an existing user')
    groups = (root / 'etc/group').read_text().splitlines()
    if not owner and any(line.split(':')[2] == '1000' for line in groups):
        raise ValueError('GID 1000 is occupied; do not reassign an existing group')
    target.mkdir(parents=True)
    for path in (REPO / 'runtime').glob('*.py'):
        shutil.copyfile(path, target / path.name)
    for command, module in [('sv08-state', 'sv08_state.py'), ('sv08-package', 'sv08_package.py')]:
        (target / module).chmod(0o755)
        (root / 'usr/bin' / command).symlink_to('../lib/sv08/' + module)
    (target / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n')
    seed = target / 'seed/config'
    seed.mkdir(parents=True)
    shutil.copyfile(REPO / 'configs/host-os/moonraker.conf', seed / 'moonraker.conf')
    units = root / 'etc/systemd/system'
    for path in (REPO / 'configs/host-os/systemd').glob('*.service'):
        shutil.copyfile(path, units / path.name)
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
    sudoers = root / 'etc/sudoers.d/sv08-owner'
    sudoers.write_text('sv08 ALL=(ALL) NOPASSWD: ALL\n')
    sudoers.chmod(0o440)
    for service in ('NetworkManager.service','ssh.service','systemd-random-seed.service',
                    'systemd-timesyncd.service','systemd-rfkill.service','systemd-logind.service'):
        directory = units / (service + '.d')
        directory.mkdir(exist_ok=True)
        (directory / 'sv08-state.conf').write_text('[Unit]\nRequires=sv08-prepare.service\nAfter=sv08-prepare.service\n')
    # Debian packages may have enabled nginx already; do not expose its default
    # site while authorization/onboarding integration is still outstanding.
    # machine-id is already persistent, not systemd's transient mount to commit.
    for timer in ('apt-daily.timer','apt-daily-upgrade.timer', 'nginx.service',
                  'systemd-machine-id-commit.service'):
        path = units / timer
        if path.exists() or path.is_symlink():
            path.unlink()
        path.symlink_to('/dev/null')
    # No printer config is seeded, and no unit is enabled by this staging tool.
    (work / 'integration-staged.json').write_text(json.dumps(manifest, indent=2)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    manifest = json.loads(a.manifest.read_text())
    validate(manifest)
    work = work_path(a.work)
    print(json.dumps(dict(execute=a.execute, work=str(work), release=manifest['release'])))
    if a.execute:
        if os.geteuid() != 0:
            p.error('Staging requires root for filesystem ownership and user creation')
        stage(work, manifest)


if __name__ == '__main__':
    main()
