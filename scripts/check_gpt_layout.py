#!/usr/bin/env python3
"""Read-only GPT/SPL collision audit for regular-file image candidates.

Gap: the H616 SPL placement and normal primary GPT array overlap. Check actual
headers/CRCs and both arrays, not just partition offsets. This supplements sgdisk;
retire when the image builder's selected boot backend enforces these invariants.
It does not establish Boot ROM/U-Boot compatibility or a flashable image.
"""
import argparse
import json
from pathlib import Path
import stat
import struct
import uuid
import zlib

SECTOR = 512


def inspect(path, spl_start=8192, spl_limit=1048576, environment_regions=()):
    if not stat.S_ISREG(path.stat().st_mode) or path.is_symlink():
        raise ValueError('Inspect only a regular image file')
    size = path.stat().st_size
    if size % SECTOR or not 1024 <= spl_start < spl_limit < size:
        raise ValueError('Invalid image or SPL reservation')
    with path.open('rb') as f:
        arrays = []
        metadata = [(0, SECTOR)]  # Preserve the protective MBR as well as GPT.
        geometry = []
        for lba in (1, size // SECTOR - 1):
            f.seek(lba * SECTOR)
            h = bytearray(f.read(SECTOR))
            if h[:8] != b'EFI PART':
                raise ValueError('Missing GPT header')
            length, crc = struct.unpack_from('<II', h, 12)
            if not 92 <= length <= SECTOR:
                raise ValueError('Invalid header length')
            struct.pack_into('<I', h, 16, 0)
            if zlib.crc32(h[:length]) != crc:
                raise ValueError('GPT header CRC mismatch')
            current, other, first, last = struct.unpack_from('<QQQQ', h, 24)
            if current != lba or other != (size // SECTOR - 1 if lba == 1 else 1):
                raise ValueError('GPT header location mismatch')
            if not 2 <= first <= last < size // SECTOR - 1:
                raise ValueError('Invalid usable sector bounds')
            table, count, entry_size, entries_crc = struct.unpack_from('<QIII', h, 72)
            geometry.append((first, last, bytes(h[56:72]), count, entry_size))
            length = count * entry_size
            if entry_size < 128 or entry_size & (entry_size - 1) or length > 16 * 1024 * 1024 or not count:
                raise ValueError('Invalid GPT entry dimensions')
            begin, end = table * SECTOR, table * SECTOR + length
            if begin < 2 * SECTOR or end > size - SECTOR:
                raise ValueError('GPT array outside disk')
            if lba == 1 and end > first * SECTOR or lba != 1 and begin < (last + 1) * SECTOR:
                raise ValueError('GPT array overlaps usable sectors')
            f.seek(begin)
            entries = f.read(length)
            if len(entries) != length or zlib.crc32(entries) != entries_crc:
                raise ValueError('GPT array CRC mismatch')
            arrays.append(entries)
            metadata += [(lba * SECTOR, (lba + 1) * SECTOR), (begin, end)]
        if geometry[0] != geometry[1]:
            raise ValueError('GPT headers disagree on geometry/identity')
        if arrays[0] != arrays[1]:
            raise ValueError('GPT arrays disagree')
        partitions = []
        partition_records = []
        for offset in range(0, len(entries), entry_size):
            e = entries[offset:offset + entry_size]
            if e[:16] == bytes(16):
                continue
            start, stop = struct.unpack_from('<QQ', e, 32)
            if not first <= start <= stop <= last:
                raise ValueError('Partition outside usable sectors')
            partitions.append((start * SECTOR, (stop + 1) * SECTOR))
            partition_records.append(dict(number=offset // entry_size + 1,
                name=e[56:128].decode('utf-16le').rstrip('\0'),
                partuuid=str(uuid.UUID(bytes_le=e[16:32])),
                offset_bytes=start * SECTOR, size_bytes=(stop-start+1) * SECTOR))
        occupied = sorted(metadata + partitions)
        for begin, end in occupied:
            if max(begin, spl_start) < min(end, spl_limit):
                raise ValueError('SPL reservation overlaps GPT or a partition')
        for left, right in zip(occupied, occupied[1:]):
            if left[1] > right[0]:
                raise ValueError('Overlapping metadata/partitions')
        environments = []
        for offset, length in environment_regions:
            if (type(offset) is not int or type(length) is not int or
                    offset < 0 or length <= 0 or offset % SECTOR or length % SECTOR):
                raise ValueError('Environment regions must use positive aligned byte lengths')
            region = (offset, offset + length)
            if not partitions or region[1] > min(p[0] for p in partitions):
                raise ValueError('Environment must fit before the first partition')
            for begin, end in occupied + [(spl_start, spl_limit)] + environments:
                if max(begin, region[0]) < min(end, region[1]):
                    raise ValueError('Environment overlaps GPT, SPL, a partition or another copy')
            environments.append(region)
    return dict(image_bytes=size, partitions=len(partitions), gpt_crc_valid=True,
                partition_records=partition_records,
                spl_reserved_bytes=[spl_start, spl_limit], collision_free=True,
                environment_reserved_bytes=environments,
                hardware_boot_validated=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path)
    p.add_argument('--environment-layout', type=Path)
    a = p.parse_args()
    regions = []
    if a.environment_layout:
        layout = json.loads(a.environment_layout.read_text())
        if layout['format_version'] != 1 or len(layout['copy_offsets_bytes']) != 2:
            raise ValueError('Expected the reviewed two-copy environment layout')
        regions = [(offset, layout['size_bytes']) for offset in layout['copy_offsets_bytes']]
    print(json.dumps(inspect(a.image, environment_regions=regions), indent=2))


if __name__ == '__main__':
    main()
