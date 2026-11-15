#!/usr/bin/env python3
"""Create a receipt for a fresh or copied non-deployable diagnostic host root.

This does not install packages, generate credentials, alter a printer, or make
an image deployable. It binds a refreshed host runtime seed to the separately
preserved data-tree owner key before composition.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

from integrate_host_os import validate
from prepare_host_os import REPO, digest, layout, work_path
from recovery_image import inventory, sha

MASKS = ('sv08-klipper', 'sv08-moonraker', 'klipper', 'moonraker', 'KlipperScreen', 'rauc', 'sv08-boot-health')
WIFI_FILES = ('usr/sbin/wpa_supplicant',
              'usr/share/dbus-1/system.d/wpa_supplicant.conf',
              'usr/share/dbus-1/system-services/fi.w1.wpa_supplicant1.service')


def initramfs_entries(path):
    result = subprocess.run(['lsinitramfs', str(path)], check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=120)
    return set(result.stdout.splitlines())


def checks(root, data):
    release = json.loads((root / 'usr/lib/sv08/release.json').read_text())
    validate(release)
    host_key = root / 'usr/lib/sv08/seed/authorized_keys'
    data_key = data / 'sv08/users/sv08/.ssh/authorized_keys'
    for key in (host_key, data_key):
        if key.is_symlink() or not key.is_file() or not key.read_bytes().strip():
            raise ValueError('Missing non-empty regular owner authorized-key seed')
    if host_key.read_bytes() != data_key.read_bytes():
        raise ValueError('Host and data owner authorized-key seeds differ')
    for name in MASKS:
        link = root / 'etc/systemd/system' / (name + '.service')
        if not link.is_symlink() or os.readlink(link) != '/dev/null':
            raise ValueError('Diagnostic service is not masked: ' + name)
    for name in WIFI_FILES:
        if not (root / name).is_file():
            raise ValueError('Diagnostic host is missing Wi-Fi userspace: ' + name)
    hook = root / 'etc/initramfs-tools/scripts/local-bottom/sv08-data'
    expected_hook_line = "DATA_DEVICE='" + release['devices']['data'] + "'"
    if hook.is_symlink() or not hook.is_file() or expected_hook_line not in hook.read_text():
        raise ValueError('Host image is missing the rendered persistent identity hook')
    initrds = sorted((root / 'boot').glob('initrd.img-*'))
    if not initrds:
        raise ValueError('Host image has no kernel initramfs')
    for initrd in initrds:
        if 'scripts/local-bottom/sv08-data' not in initramfs_entries(initrd):
            raise ValueError('Kernel initramfs omits the persistent identity hook: ' + initrd.name)
    if (root / 'usr/lib/sv08/qemu-probe.py').exists() or (root / 'etc/systemd/system/qemu-probe.service').exists():
        raise ValueError('QEMU fixture must not be finalized')
    return dict(release=release['release'], deployable=False,
                owner_key_seeded=True, printer_services_masked=True,
                boot_health_masked=True, wifi_userspace_present=True,
                qemu_fixture_absent=True)


def fresh_provenance(work, root, profile):
    paths = {'profile': work / 'profile.json',
             **{stage: work / stage for stage in
                ('bootstrap-complete', 'packages-complete', 'refresh-complete')}}
    for path in (profile, *paths.values()):
        if path.is_symlink() or not path.is_file():
            raise ValueError('Fresh finalization requires regular profile/stage files: ' + str(path))
    reviewed = json.loads(profile.read_text())
    layout(reviewed)
    profile_digest = digest(reviewed)
    if digest(json.loads(paths['profile'].read_text())) != profile_digest:
        raise ValueError('Fresh staged profile differs from reviewed profile')
    for stage, path in paths.items():
        if stage != 'profile' and path.read_text().strip() != profile_digest:
            raise ValueError('Fresh stage/profile mismatch: ' + stage)
    package_checks = {}
    for name, command in (('dpkg_audit', ['dpkg', '--audit']),
                          ('apt_dependency_check', ['apt-get', 'check'])):
        result = subprocess.run(['chroot', str(root), *command], check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=120)
        if name == 'dpkg_audit' and (result.stdout.strip() or result.stderr.strip()):
            raise ValueError('Fresh root dpkg audit is not clean')
        package_checks[name] = True
    return dict(mode='fresh', profile_digest=profile_digest,
                reviewed_profile_sha256=sha(profile),
                staged_profile_sha256=sha(paths['profile']),
                stage_marker_sha256={name: sha(path) for name, path in paths.items()
                                     if name != 'profile'},
                package_checks=package_checks)


def finalize(work, data, source_receipt=None, execute=False, *, fresh=False,
             profile=None):
    if fresh == (source_receipt is not None):
        raise ValueError('Choose exactly one of fresh or source receipt')
    root = work / 'rootfs'
    receipt = work / 'finalized.json'
    if root.is_symlink() or not root.is_dir() or not (work / 'refresh-complete').is_file():
        raise ValueError('Use an isolated completed root copy')
    if receipt.exists() or receipt.is_symlink():
        raise ValueError('A finalization receipt already exists; use a fresh copied work directory')
    if data.is_symlink() or not data.is_dir():
        raise ValueError('Expected an isolated preserved data tree')
    if fresh:
        provenance = fresh_provenance(work, root, profile or REPO / 'configs/images/host-ab.json')
        origin = dict(provenance=provenance)
    else:
        source = json.loads(source_receipt.read_text())
        if not isinstance(source.get('root'), dict) or source['root'].get('schema') != 2:
            raise ValueError('Source finalization receipt is invalid')
        origin = dict(source_finalization_sha256=sha(source_receipt))
    result = dict(schema=3, root=inventory(root), checks=checks(root, data), **origin)
    if execute:
        receipt.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source-receipt', type=Path)
    mode.add_argument('--fresh', action='store_true')
    parser.add_argument('--profile', type=Path, default=REPO / 'configs/images/host-ab.json',
                        help='Reviewed baseline profile for --fresh')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(finalize(work_path(args.work), work_path(args.data), args.source_receipt, args.execute,
                              fresh=args.fresh, profile=args.profile), indent=2))


if __name__ == '__main__':
    main()
