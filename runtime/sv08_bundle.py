#!/usr/bin/env python3
"""Read-only signed-bundle admission checks for the SV08 update coordinator.

RAUC authenticates the manifest. This checks project-specific layout, state and
host/MCU compatibility before installation. It never installs or selects a slot.
See ADR 0006; retire if upstream policy expresses these exact release constraints.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess


def validate(info, policy, bundle_size):
    """Validate authenticated RAUC json-2 output, not arbitrary uploaded JSON."""
    if type(bundle_size) is not int or not 0 < bundle_size <= policy['max_bundle_bytes']:
        raise ValueError('Bundle exceeds the staging budget')
    if info['update']['compatible'] != policy['compatible']:
        raise ValueError('Bundle targets a different hardware profile')
    if info['bundle']['format'] != 'verity':
        raise ValueError('Only signed verity bundles are supported')
    release = info['update']['version']
    if not isinstance(release, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', release):
        raise ValueError('Invalid release identifier')
    metadata = info.get('meta', {}).get('sv08', {})
    expected = {'layout': policy['layout'], 'state-schema': str(policy['state_schema']),
                'klipper-commit': policy['klipper_commit']}
    if metadata != expected:
        raise ValueError('Signed layout/state/Klipper metadata does not match this system')
    if policy['state_schema'] != 1 or not re.fullmatch('[0-9a-f]{40}', policy['klipper_commit']):
        raise ValueError('Unsupported state schema or incomplete Klipper pin')
    images = info['images']
    if len(images) != 2 or {image['slot-class'] for image in images} != {'boot', 'rootfs'}:
        raise ValueError('Expected exactly paired boot/root images')
    for image in images:
        if type(image['size']) is not int or image['size'] != policy['image_bytes'][image['slot-class']]:
            raise ValueError('Image dimensions do not match the slot layout')
        if not re.fullmatch('[0-9a-f]{64}', image['checksum']):
            raise ValueError('Invalid signed image digest')
        if (image.get('variant') or image.get('hooks') or image.get('adaptive') or
                image.get('artifact') or image.get('type', 'raw') != 'raw'):
            raise ValueError('Image variants/hooks/adaptive updates are not admitted by this policy')
    if info.get('hooks') or info.get('handler'):
        raise ValueError('Bundle hooks are not admitted by this policy')
    return dict(release=release, compatible=policy['compatible'], metadata=metadata,
                image_hashes={image['slot-class']: image['checksum'] for image in images})


def inspect(bundle, policy, keyring, rauc='/usr/bin/rauc'):
    if bundle.is_symlink() or not stat.S_ISREG(bundle.stat().st_mode):
        raise ValueError('Inspect a locally staged regular bundle file')
    before = bundle.stat()
    if not 0 < before.st_size <= policy['max_bundle_bytes']:
        raise ValueError('Bundle exceeds the staging budget')
    info = json.loads(subprocess.check_output([str(rauc), 'info', '--output-format=json-2',
                      '--keyring='+str(keyring), str(bundle)], text=True))
    result = validate(info, policy, before.st_size)
    with bundle.open('rb') as stream:
        result['bundle_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = bundle.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError('Bundle changed during inspection')
    result['installs_or_activates'] = False
    # info authenticates the inline manifest, not every payload block. Actual
    # installation must retain RAUC verity verification and recheck admission.
    result['full_payload_verified'] = False
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
    p.add_argument('--policy', type=Path, default=Path('/usr/lib/sv08/update-policy.json'))
    p.add_argument('--keyring', type=Path, default=Path('/etc/rauc/release-keyring.pem'))
    p.add_argument('--rauc', type=Path, default=Path('/usr/bin/rauc'))
    a = p.parse_args()
    print(json.dumps(inspect(a.bundle, json.loads(a.policy.read_text()), a.keyring, a.rauc), indent=2))


if __name__ == '__main__':
    main()
