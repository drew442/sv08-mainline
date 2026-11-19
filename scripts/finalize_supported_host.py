#!/usr/bin/env python3
"""Finalize a clean supported candidate root; not release/printing qualification."""
import argparse
import json
import os
from pathlib import Path

from finalize_diagnostic_host import fresh_provenance, initramfs_entries, WIFI_FILES
from integrate_host_os import firmware_manifest
from prepare_host_os import REPO, work_path
from recovery_image import inventory
from supported_candidate import backend_documents, profile_check, public_account_checks, public_certificate, rauc_configuration, regular


def source_check(profile):
    from project_license import source_state
    revision, dirty = source_state(REPO)
    if dirty or revision != profile['project_source_revision']:
        raise ValueError('Freeze clean matching project source before supported composition')


def checks(root, data, profile):
    expected = firmware_manifest(profile_check(profile))
    if json.loads(regular(root, 'usr/lib/sv08/release.json')) != expected:
        raise ValueError('Supported release/profile/MCU assignment differs')
    for name, value in backend_documents(profile).items():
        if name != 'release.json' and json.loads(regular(root, 'usr/lib/sv08/'+name)) != value:
            raise ValueError('Supported backend binding differs: '+name)
    if regular(root, 'etc/rauc/system.conf').decode() != rauc_configuration(profile):
        raise ValueError('Supported RAUC configuration differs')
    certificate = root/'etc/rauc/release-keyring.pem'
    public_certificate(certificate)
    public = public_account_checks(root)
    password_policy = (REPO/'configs/host-os/supported/owner-password-policy.conf').read_bytes()
    if not regular(root, 'etc/pam.d/common-password').startswith(password_policy):
        raise ValueError('Supported recovery-only owner password policy is missing or reordered')
    if data.is_symlink() or not data.is_dir() or any(data.iterdir()):
        raise ValueError('Supported image data seed must be empty; enroll state/identity in recovery')
    units = root/'etc/systemd/system'
    for name in ('sv08-boot-health', 'sv08-klipper', 'sv08-moonraker', 'sv08-commissioned-start'):
        path = units/(name+'.service')
        if path.is_symlink() or not path.is_file(): raise ValueError('Supported current service is missing or masked: '+name)
        source = REPO/'configs/host-os/systemd'/(name+'.service')
        if path.read_bytes() != source.read_bytes(): raise ValueError('Supported service differs from current source: '+name)
    for name in ('klipper', 'moonraker', 'KlipperScreen'):
        path = units/(name+'.service')
        if not path.is_symlink() or os.readlink(path) != '/dev/null': raise ValueError('Uncontrolled hardware service alias: '+name)
    for directory in units.glob('*.wants'):
        if any((directory/(name+'.service')).exists() or (directory/(name+'.service')).is_symlink()
               for name in ('sv08-klipper','sv08-moonraker')):
            raise ValueError('Uncommissioned physical services must not autostart')
    guard = regular(root, 'etc/systemd/system/sv08-klipper.service.d/supported-commissioning.conf').decode()
    if guard != '[Service]\nExecStartPre=+/usr/bin/python3 /usr/lib/sv08/sv08_commissioning.py check\n':
        raise ValueError('Supported commissioning guard is missing')
    if not (units/'multi-user.target.wants/sv08-boot-health.service').is_symlink():
        raise ValueError('Supported real OS-health handoff is not enabled')
    activation = units/'multi-user.target.wants/sv08-commissioned-start.service'
    if not activation.is_symlink() or os.readlink(activation) != '../sv08-commissioned-start.service':
        raise ValueError('Supported guarded boot activation is not enabled with its exact unit binding')
    for name in WIFI_FILES:
        path = root/name
        if path.is_symlink() or not path.is_file(): raise ValueError('Supported Wi-Fi userspace is missing: '+name)
    hook = regular(root, 'etc/initramfs-tools/scripts/local-bottom/sv08-data').decode()
    if "DATA_DEVICE='"+expected['devices']['data']+"'" not in hook:
        raise ValueError('Supported persistent identity hook differs')
    initrds = sorted((root/'boot').glob('initrd.img-*'))
    if not initrds: raise ValueError('Supported image has no kernel initramfs')
    for path in initrds:
        if 'scripts/local-bottom/sv08-data' not in initramfs_entries(path):
            raise ValueError('Supported initramfs omits persistent identity')
    from project_license import validate
    provenance = validate(root)
    if provenance['development'] or provenance['source_revision'] != profile['project_source_revision']:
        raise ValueError('Supported project notices/source provenance are incomplete')
    return dict(release=expected['release'], candidate=True, deployable=True,
                physical_services_enabled=False, health='production', owner=public,
                measured_medium_binding=True, printing_qualified=False, release_qualified=False)


def finalize(work, data, profile, execute=False):
    profile_check(profile)
    source_check(profile)
    root = work/'rootfs'; receipt = work/'supported-finalized.json'
    if root.is_symlink() or not root.is_dir() or receipt.exists() or receipt.is_symlink():
        raise ValueError('Use a fresh completed supported root and receipt')
    provenance = fresh_provenance(work, root, REPO/'configs/images/host-ab.json')
    result = dict(schema=1, kind='supported-configured-printer-candidate',
                  profile=profile, root=inventory(root), checks=checks(root, data, profile),
                  provenance=provenance)
    if execute: receipt.write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('work','data','profile'): parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text())
    print(json.dumps(finalize(work_path(args.work), work_path(args.data), profile, args.execute), indent=2))


if __name__ == '__main__': main()
