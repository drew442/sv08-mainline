#!/usr/bin/env python3
"""Build inputs for the disposable Cockpit/RAUC composition guest.

This is deliberately separate from the existing regular-file-slot service
fixture.  The composed fixture must start from a fresh six-partition disk so
the privileged helper reaches the same partition identity checks as the RAUC
backend.  It never accepts an existing image or a block device.
"""
import json
from pathlib import Path
import shutil
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


def format_media(image, parts=None):
    """Format only the reviewed extents of a verified disposable GPT file."""
    image = Path(image)
    parts = partition_layout() if parts is None else parts
    if image.is_symlink() or not image.is_file() or image.stat().st_size != LAYOUT['image_bytes']:
        raise ValueError('Expected the fresh disposable fixture image')
    by_name = {part['name']: part for part in parts}
    for name in ('boot-a', 'boot-b'):
        part = by_name[name]
        subprocess.run(['mkfs.vfat', '-F', '16', '--offset', str(part['offset_bytes'] // 512),
                        '-n', name.upper(), image, str(part['size_bytes'] // 512)],
                       check=True, capture_output=True, text=True)
    for name in ('root-a', 'root-b', 'recovery', 'data'):
        part = by_name[name]
        subprocess.run(['mkfs.ext4', '-q', '-F', '-E', 'offset='+str(part['offset_bytes']),
                        '-L', name, image, str(part['size_bytes'] // 4096)],
                       check=True, capture_output=True, text=True)
    return {part['name']: dict(offset_bytes=part['offset_bytes'], size_bytes=part['size_bytes'])
            for part in parts}


def filesystem_types(image, parts=None):
    """Read only bounded filesystem signatures from the disposable image."""
    image = Path(image)
    parts = partition_layout() if parts is None else parts
    result = {}
    for part in parts:
        output = subprocess.check_output(['blkid', '-p', '-o', 'export', '-O', str(part['offset_bytes']),
                                          '-S', str(part['size_bytes']), image], text=True)
        values = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
        result[part['name']] = values.get('TYPE')
    return result


def populate_ext4_partition(image, name, source, work, parts=None):
    """Copy a regular source tree into one bounded ext4 fixture partition.

    The intermediate is a sparse regular file. ``dd`` is given a fixed count
    and seek, so it cannot affect the GPT, raw environment reservations or an
    adjacent partition.
    """
    image, source, work = Path(image), Path(source), Path(work)
    parts = partition_layout() if parts is None else parts
    part = next((item for item in parts if item['name'] == name), None)
    if part is None or name not in ('root-a', 'root-b', 'recovery', 'data'):
        raise ValueError('Expected one reviewed ext4 fixture partition')
    if image.is_symlink() or not image.is_file() or image.stat().st_size != LAYOUT['image_bytes']:
        raise ValueError('Expected the fresh disposable fixture image')
    if source.is_symlink() or not source.is_dir() or work.is_symlink():
        raise ValueError('Source and work must be regular fixture directories')
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    intermediate = work / (name + '.ext4')
    if intermediate.exists() or intermediate.is_symlink():
        raise ValueError('Use a fresh partition work file')
    with intermediate.open('xb') as stream:
        stream.truncate(part['size_bytes'])
    try:
        subprocess.run(['mkfs.ext4', '-q', '-F', '-d', source, '-L', name, intermediate],
                       check=True, capture_output=True, text=True)
        if filesystem_types(intermediate, [dict(part, offset_bytes=0)]) != {name: 'ext4'}:
            raise ValueError('Intermediate filesystem creation failed')
        if part['offset_bytes'] % MIB or part['size_bytes'] % MIB:
            raise ValueError('Fixture partition is not MiB aligned')
        subprocess.run(['dd', 'if='+str(intermediate), 'of='+str(image), 'bs=1M',
                        'seek='+str(part['offset_bytes'] // MIB),
                        'count='+str(part['size_bytes'] // MIB), 'conv=notrunc,sparse', 'status=none'],
                       check=True)
        return dict(name=name, source_files=sum(1 for item in source.rglob('*') if item.is_file()),
                    partition_offset_bytes=part['offset_bytes'], partition_size_bytes=part['size_bytes'])
    finally:
        intermediate.unlink(missing_ok=True)


def copy_guest_root(source, destination):
    """Copy a source root without importing host runtime mounts or devices."""
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or not source.is_dir() or destination.exists() or destination.is_symlink():
        raise ValueError('Use a regular source root and fresh destination')
    ignored = {'dev', 'proc', 'sys', 'run', 'tmp'}
    shutil.copytree(source, destination, symlinks=True,
                    ignore=lambda directory, names: ignored if Path(directory) == source else set())
    for name in sorted(ignored):
        (destination / name).mkdir()
    return destination
