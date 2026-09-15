#!/usr/bin/env python3
"""Create a receipt for a copied, non-deployable diagnostic host root.

This does not install packages, generate credentials, alter a printer, or make
an image deployable. It binds a refreshed host runtime seed to the separately
preserved data-tree owner key before composition.
"""
import argparse
import json
import os
from pathlib import Path

from integrate_host_os import validate
from prepare_host_os import work_path
from recovery_image import inventory, sha

MASKS = ('sv08-klipper', 'sv08-moonraker', 'klipper', 'moonraker', 'KlipperScreen', 'rauc')


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
            raise ValueError('Printer/RAUC service is not masked: ' + name)
    if (root / 'usr/lib/sv08/qemu-probe.py').exists() or (root / 'etc/systemd/system/qemu-probe.service').exists():
        raise ValueError('QEMU fixture must not be finalized')
    return dict(release=release['release'], deployable=False,
                owner_key_seeded=True, printer_services_masked=True,
                qemu_fixture_absent=True)


def finalize(work, data, source_receipt, execute=False):
    root = work / 'rootfs'
    receipt = work / 'finalized.json'
    if root.is_symlink() or not root.is_dir() or not (work / 'refresh-complete').is_file():
        raise ValueError('Use an isolated completed root copy')
    if receipt.exists() or receipt.is_symlink():
        raise ValueError('A finalization receipt already exists; use a fresh copied work directory')
    if data.is_symlink() or not data.is_dir():
        raise ValueError('Expected an isolated preserved data tree')
    source = json.loads(source_receipt.read_text())
    if not isinstance(source.get('root'), dict) or source['root'].get('schema') != 2:
        raise ValueError('Source finalization receipt is invalid')
    result = dict(schema=3, root=inventory(root), checks=checks(root, data),
                  source_finalization_sha256=sha(source_receipt))
    if execute:
        receipt.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--source-receipt', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(finalize(work_path(args.work), work_path(args.data), args.source_receipt, args.execute), indent=2))


if __name__ == '__main__':
    main()
