#!/usr/bin/env python3
"""Build, but never write, the reviewed redundant U-Boot environment rearm image.

This is deliberately separate from a block-device writer.  It restores the
diagnostic boot policy to one A-slot trial set with three attempts, no B-slot
trial, and the normal diagnostic service masks.  A target-specific writer must
identify the eMMC and verify both environment regions before using this output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]
ENVIRONMENT_BYTES = 65536
ENVIRONMENT_OFFSETS = (0x400000, 0x800000)
DIAGNOSTIC_MASKS = ('sv08-klipper', 'sv08-moonraker', 'klipper', 'moonraker', 'KlipperScreen')


def environment_text(source=REPO / 'configs/host-os/sv08-default.env'):
    lines = source.read_text(encoding='utf-8').splitlines()
    values = dict(line.split('=', 1) for line in lines)
    if len(lines) != len(values) or any(not key or '\x00' in value for key, value in values.items()):
        raise ValueError('Invalid default environment source')
    protected = {'sv08_env_layout', 'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT'}
    if protected & values.keys():
        raise ValueError('Default environment must not embed mutable A/B state')
    values.update(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A', BOOT_A_LEFT='3', BOOT_B_LEFT='0')
    values['sv08_consoleargs'] += ''.join(' systemd.mask='+name+'.service' for name in DIAGNOSTIC_MASKS)
    return ''.join(key+'='+value+'\n' for key, value in values.items())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def valid_copy(value):
    if len(value) != ENVIRONMENT_BYTES:
        return False
    expected = int.from_bytes(value[:4], 'little')
    actual = __import__('zlib').crc32(value[5:]) & 0xffffffff
    return expected == actual and b'\0\0' in value[5:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='Fresh regular file under build/; no block devices')
    parser.add_argument('--newest-flag', type=int, required=True,
                        help='Observed newest valid target flag plus two; range 1..254')
    parser.add_argument('--execute', action='store_true',
                        help='Create the file; otherwise print the exact plan')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(REPO / 'build') or output.exists() or output.is_symlink():
        raise ValueError('Output must be a fresh regular-file path under build/')
    if not 1 <= args.newest_flag <= 254:
        raise ValueError('Newest flag must be in range 1..254')
    if shutil.which('mkenvimage') is None:
        raise ValueError('mkenvimage is required')
    text = environment_text()
    plan = dict(execute=args.execute, output=str(output), bytes=2 * ENVIRONMENT_BYTES,
                offsets=list(ENVIRONMENT_OFFSETS), values={key: dict(line.split('=', 1) for line in text.splitlines())[key]
                for key in ('sv08_env_layout', 'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT')},
                flags=[args.newest_flag - 1, args.newest_flag])
    if not args.execute:
        print(json.dumps(plan, indent=2))
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    source = output.with_suffix(output.suffix + '.txt')
    if source.exists():
        raise ValueError('Derived text output already exists')
    source.write_text(text, encoding='utf-8')
    try:
        temporary = output.with_suffix(output.suffix + '.single')
        subprocess.run(['mkenvimage', '-r', '-s', str(ENVIRONMENT_BYTES), '-o', str(temporary), str(source)], check=True)
        copy = bytearray(temporary.read_bytes())
        temporary.unlink()
        if not valid_copy(copy):
            raise ValueError('mkenvimage did not produce a valid redundant environment')
        first, second = bytearray(copy), bytearray(copy)
        first[4], second[4] = args.newest_flag - 1, args.newest_flag
        output.write_bytes(first + second)
    finally:
        source.unlink(missing_ok=True)
    pair = output.read_bytes()
    if len(pair) != 2 * ENVIRONMENT_BYTES or not all(valid_copy(pair[offset:offset + ENVIRONMENT_BYTES])
            for offset in (0, ENVIRONMENT_BYTES)):
        raise ValueError('Invalid U-Boot environment pair')
    plan.update(sha256=digest(output), redundant_copies_identical=False)
    print(json.dumps(plan, indent=2))


if __name__ == '__main__':
    main()
