#!/usr/bin/env python3
"""Build inputs for the disposable Cockpit/RAUC composition guest.

This is deliberately separate from the existing regular-file-slot service
fixture.  The composed fixture must start from a fresh six-partition disk so
the privileged helper reaches the same partition identity checks as the RAUC
backend.  It never accepts an existing image or a block device.
"""
import json
from pathlib import Path
import subprocess
import uuid


REPO = Path(__file__).resolve().parents[1]
LAYOUT = json.loads((REPO / 'configs/images/host-ab.json').read_text())
MIB = 1024 * 1024
ROLES = ('boot-a', 'root-a', 'boot-b', 'root-b', 'recovery', 'data')


def partition_layout(layout=LAYOUT):
    """Return exact GPT extents without opening a device or image."""
    if layout['image_bytes'] != 7818182656 or layout['leading_reservation_mib'] != 16:
        raise ValueError('Unexpected reviewed fixture image layout')
    parts = layout['partitions']
    if tuple(part['name'] for part in parts) != ROLES:
        raise ValueError('Expected the reviewed six-partition A/B layout')
    offset = layout['leading_reservation_mib'] * MIB
    result = []
    for number, part in enumerate(parts, 1):
        size = part['mib'] * MIB
        if size <= 0 or offset % 512:
            raise ValueError('Invalid reviewed partition extent')
        result.append(dict(number=number, name=part['name'], offset_bytes=offset,
                           size_bytes=size, end_bytes=offset + size))
        offset += size
    if offset + layout['tail_reservation_mib'] * MIB != layout['image_bytes']:
        raise ValueError('Reviewed partition layout does not fit its image')
    return result


def fixture_manifest(partuuids, *, release='qemu-rauc-composed-source'):
    """Create the exact non-deployable identity document for one fresh guest."""
    if set(partuuids) != set(ROLES):
        raise ValueError('Fixture needs one PARTUUID for every reviewed partition')
    canonical = {name: str(uuid.UUID(value)) for name, value in partuuids.items()}
    if len(set(canonical.values())) != len(canonical):
        raise ValueError('Fixture PARTUUIDs must be distinct')
    return dict(format_version=1, deployable=False, release=release, state_schema=1,
                devices={name: '/dev/disk/by-partuuid/' + canonical[name] for name in ROLES})


def sgdisk_arguments(image, parts, partuuids):
    """Return an explicit regular-file-only GPT creation command."""
    image = Path(image)
    if image.exists() or image.is_symlink() or image.parent == Path('/dev'):
        raise ValueError('Fixture target must be a new regular file outside /dev')
    command = ['sgdisk', '--clear']
    for part in parts:
        start, end = part['offset_bytes'] // 512, part['end_bytes'] // 512 - 1
        command.extend([f"--new={part['number']}:{start}:{end}",
                        f"--change-name={part['number']}:{part['name']}",
                        f"--partition-guid={part['number']}:{partuuids[part['name']]}",
                        f"--typecode={part['number']}:8300"])
    return [*command, image]


def create_media(image, partuuids, layout=LAYOUT):
    """Create and immediately read back a sparse disposable GPT image."""
    image = Path(image)
    parts = partition_layout(layout)
    command = sgdisk_arguments(image, parts, partuuids)
    image.parent.mkdir(parents=True, exist_ok=True)
    with image.open('xb') as stream:
        stream.truncate(layout['image_bytes'])
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        observed = json.loads(subprocess.check_output(['sfdisk', '--json', image], text=True))
        rows = observed['partitiontable']['partitions']
        expected = [(part['number'], part['name'], part['offset_bytes'] // 512,
                     part['size_bytes'] // 512, str(uuid.UUID(partuuids[part['name']])))
                    for part in parts]
        actual = [(index, row['name'], row['start'], row['size'], row['uuid'])
                  for index, row in enumerate(rows, 1)]
        if actual != expected:
            raise ValueError('Disposable GPT readback differs from the reviewed layout')
        return dict(image_bytes=image.stat().st_size, partitions=actual)
    except BaseException:
        image.unlink(missing_ok=True)
        raise
