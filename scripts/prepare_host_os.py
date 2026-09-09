#!/usr/bin/env python3
"""Offline A/B package baseline. No bootloader, disk assembly or activation.

Custom gap: profile/size validation and staged Debian baseline inventory.
Uses debootstrap/apt; retire bootstrap duplication if the image builders converge.
See docs/hardware/host-ab-build.md and tests/test_prepare_host_os.py.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]
MIB = 1024 * 1024


def layout(c):
    if c['architecture'] != 'arm64' or c['suite'] != 'trixie':
        raise ValueError('Only the reviewed trixie/arm64 baseline is supported')
    if not re.fullmatch(r'\d{8}T\d{6}Z', c['snapshot']):
        raise ValueError('Invalid snapshot')
    if c['components'] != ['main', 'non-free-firmware']:
        raise ValueError('Unexpected repository components')
    if not isinstance(c['packages'], list) or not c['packages'] or any(not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*', p)
                                for p in c['packages']):
        raise ValueError('Invalid package names')
    if c['default_mode'] != 'immutable' or c['supported_modes'] != ['immutable', 'writable']:
        raise ValueError('Operating modes disagree with decision 0004')
    if c['leading_reservation_mib'] != 16 or c['tail_reservation_mib'] != 1:
        raise ValueError('Boot reservations require separate review')
    expected = ['boot-a', 'root-a', 'boot-b', 'root-b', 'recovery', 'data']
    if [p['name'] for p in c['partitions']] != expected:
        raise ValueError('Unexpected partitions')
    offset = c['leading_reservation_mib'] * MIB
    result = []
    for p in c['partitions']:
        if type(p['mib']) is not int or p['mib'] <= 0:
            raise ValueError('Invalid partition size')
        result.append(dict(name=p['name'], offset_bytes=offset, size_bytes=p['mib'] * MIB))
        offset += p['mib'] * MIB
    if offset + c['tail_reservation_mib'] * MIB != c['image_bytes']:
        raise ValueError('Partitions do not fit the declared media')
    for a, b in [(0, 2), (1, 3)]:
        if result[a]['size_bytes'] != result[b]['size_bytes']:
            raise ValueError('A/B slots must be symmetric')
    for budget, index in [('root_content_budget_mib', 1), ('boot_content_budget_mib', 0)]:
        if not 0 < c[budget] * MIB < result[index]['size_bytes']:
            raise ValueError('Content budget must leave filesystem/headroom space')
    return result


def run(*args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def work_path(path):
    # Never follow an alias into an existing tree, device or outside build/.
    raw = Path(os.path.abspath(path))
    for p in (raw, *raw.parents):
        if p.is_symlink():
            raise ValueError('Symlink work paths are not supported')
    resolved = raw.resolve()
    if not resolved.is_relative_to(REPO / 'build') or resolved == REPO / 'build':
        raise ValueError('Work directory must be below repository build/')
    return resolved


def digest(c):
    return hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()


def bootstrap(c, work):
    if work.exists():
        raise ValueError('Bootstrap requires a new work directory')
    work.mkdir(parents=True)
    (work / 'profile.json').write_text(json.dumps(c, indent=2) + '\n')
    mirror = f"https://snapshot.debian.org/archive/debian/{c['snapshot']}/"
    run('debootstrap', '--foreign', '--arch=arm64', '--variant=minbase',
        '--include=ca-certificates', c['suite'], work / 'rootfs', mirror)
    # Workstation binfmt registration must supply qemu-aarch64 for the second stage.
    run('chroot', work / 'rootfs', '/debootstrap/debootstrap', '--second-stage')
    (work / 'bootstrap-complete').write_text(digest(c) + '\n')


def packages(c, work):
    if (work / 'bootstrap-complete').read_text().strip() != digest(c):
        raise ValueError('Bootstrap/profile mismatch')
    if (work / 'packages-started').exists():
        raise ValueError('Package stage already attempted; inspect and use a fresh build')
    root = work / 'rootfs'
    (work / 'packages-started').touch()
    (root / 'usr/sbin/policy-rc.d').write_text('#!/bin/sh\nexit 101\n')
    (root / 'usr/sbin/policy-rc.d').chmod(0o755)
    comp = ' '.join(c['components'])
    (root / 'etc/apt/sources.list').write_text(
        f"deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/{c['snapshot']}/ {c['suite']} {comp}\n"
        f"deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/{c['snapshot']}/ {c['suite']}-security {comp}\n")
    shutil.copyfile('/etc/resolv.conf', root / 'etc/resolv.conf')
    # This isolated package baseline is deliberately not a deployable system.
    run('mount', '-t', 'proc', 'proc', root / 'proc')
    try:
        run('chroot', root, 'apt-get', 'update')
        run('chroot', root, 'env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get',
            'install', '-y', '--no-install-recommends', *c['packages'])
        run('chroot', root, 'dpkg', '--audit')
        run('chroot', root, 'apt-get', 'check')
        run('chroot', root, 'apt-get', 'clean')
        for p in (root / 'etc/ssh').glob('ssh_host_*'):
            p.unlink()
        (root / 'etc/machine-id').write_text('')
        (work / 'packages-complete').write_text(digest(c) + '\n')
    finally:
        run('umount', root / 'proc')


def refresh(c, work):
    """Align bootstrap packages with the same pinned security snapshot."""
    if (work / 'packages-complete').read_text().strip() != digest(c):
        raise ValueError('No complete matching package stage')
    if (work / 'refresh-started').exists():
        raise ValueError('Refresh already attempted; inspect and use a fresh build')
    (work / 'refresh-started').touch()
    root = work / 'rootfs'
    run('mount', '-t', 'proc', 'proc', root / 'proc')
    try:
        run('chroot', root, 'env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get',
            'full-upgrade', '-y', '--no-install-recommends')
        run('chroot', root, 'apt-get', 'check')
        run('chroot', root, 'apt-get', 'clean')
        (work / 'refresh-complete').write_text(digest(c) + '\n')
    finally:
        run('umount', root / 'proc')


def inspect(c, work):
    if (work / 'packages-complete').read_text().strip() != digest(c):
        raise ValueError('No complete matching package baseline')
    if (work / 'refresh-complete').read_text().strip() != digest(c):
        raise ValueError('Refresh base packages before inspection')
    root = work / 'rootfs'
    states = subprocess.check_output(
        ['chroot', str(root), 'dpkg-query', '-W', '-f=${db:Status-Status}\n'], text=True)
    if any(state != 'installed' for state in states.splitlines()):
        raise ValueError('Package baseline contains non-installed package states')
    inventory = subprocess.check_output(
        ['chroot', str(root), 'dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\n'], text=True)
    (work / 'packages.tsv').write_text(inventory)
    # Apparent bytes deliberately include apt indexes; excludes only separate /boot.
    total = int(subprocess.check_output(['du', '-sbx', str(root)], text=True).split()[0])
    boot = int(subprocess.check_output(['du', '-sbx', str(root / 'boot')], text=True).split()[0])
    installed = {line.split('\t', 1)[0] for line in inventory.splitlines()}
    missing_apps = [name for name in ('sv08-klipper', 'sv08-moonraker', 'sv08-mainsail', 'sv08-klipperscreen') if name not in installed]
    report = dict(status='package-baseline-only-not-bootable', profile_sha256=digest(c),
                  layout=layout(c), package_count=len(inventory.splitlines()),
                  package_inventory_sha256=hashlib.sha256(inventory.encode()).hexdigest(),
                  root_apparent_bytes=total-boot, boot_apparent_bytes=boot,
                  boot_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted((root / 'boot').iterdir())
                               if p.is_file() and not p.is_symlink()},
                  root_budget_pass=total-boot <= c['root_content_budget_mib']*MIB,
                  boot_budget_pass=boot <= c['boot_content_budget_mib']*MIB,
                  tools={name: subprocess.check_output(cmd, text=True).splitlines()[0]
                         for name, cmd in {'debootstrap': ['debootstrap', '--version'],
                                           'qemu': ['qemu-aarch64-static', '--version']}.items()},
                  kernel_versions=sorted(p.name for p in (root / 'usr/lib/modules').iterdir()),
                  missing=['board bootloader/DTB', 'verified Wi-Fi/display drivers',
                           'application service integration', 'A/B integration',
                           'operating modes/persistence', 'recovery image'] +
                          ['application package: ' + name for name in missing_apps])
    (work / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if not report['root_budget_pass'] or not report['boot_budget_pass']:
        raise ValueError('Baseline exceeds content budget')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', type=Path, default=REPO / 'configs/images/host-ab.json')
    p.add_argument('--work', type=Path, default=REPO / 'build/host-ab-baseline-v1')
    p.add_argument('--stage', choices=['bootstrap', 'packages', 'refresh', 'inspect'], required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    c = json.loads(a.profile.read_text())
    plan = layout(c)
    work = work_path(a.work)
    if not a.execute:
        print(json.dumps(dict(stage=a.stage, work=str(work), execute=False, layout=plan), indent=2))
        return
    if os.geteuid() != 0:
        p.error('Execution requires root for the isolated chroot')
    globals()[a.stage](c, work)


if __name__ == '__main__':
    main()
