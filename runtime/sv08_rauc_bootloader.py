#!/usr/bin/python3
"""Fail-closed RAUC custom backend for the reviewed SV08 U-Boot variables.

RAUC's stock U-Boot backend rewrites the redundant environment while marking
an install target bad, even when policy intends staging and arming to be
separate. This backend leaves an already-disabled install target byte-for-byte
untouched and retains normal state changes for explicit arm, confirm, cancel,
and fallback operations issued by the transaction coordinator.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zlib

ENV_CONFIG = Path('/etc/fw_env.config')
OPERATION = Path('/run/sv08/rauc-operation.json')
BOOT = Path('/run/sv08/boot.json')
ENV_NAMES = ('sv08_env_layout', 'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT')
ORDER_VALUES = ('A B', 'B A', 'A', 'B')


def validate_environment(values):
    if (set(values) != set(ENV_NAMES) or values['sv08_env_layout'] != 'ab-8gb-v1' or
            values['BOOT_ORDER'] not in ORDER_VALUES or
            values['BOOT_A_LEFT'] not in ('0', '1', '2', '3') or
            values['BOOT_B_LEFT'] not in ('0', '1', '2', '3')):
        raise ValueError('Unrecognized SV08 redundant boot environment')


def primary(values):
    for slot in values['BOOT_ORDER'].split():
        if values['BOOT_'+slot+'_LEFT'] != '0':
            return slot
    raise ValueError('No bootable primary slot is configured')


def slot_good(values, slot):
    return slot in values['BOOT_ORDER'].split() and values['BOOT_'+slot+'_LEFT'] != '0'


def disabled(values, slot):
    return slot not in values['BOOT_ORDER'].split() and values['BOOT_'+slot+'_LEFT'] == '0'


def parse_values(output):
    values = {}
    for line in output.splitlines():
        if '=' not in line:
            raise ValueError('Malformed fw_printenv response')
        name, value = line.split('=', 1)
        if name in values:
            raise ValueError('Duplicate fw_printenv variable')
        values[name] = value
    validate_environment(values)
    return values


def verify_environment_copies(config=ENV_CONFIG):
    entries = [line.split() for line in Path(config).read_text().splitlines()
               if line.strip() and not line.lstrip().startswith('#')]
    if (len(entries) != 2 or entries[0][0] != entries[1][0] or
            [entry[1:] for entry in entries] != [['0x400000', '0x10000'], ['0x800000', '0x10000']]):
        raise ValueError('Unexpected redundant U-Boot environment map')
    target = Path(entries[0][0])
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        for offset in (0x400000, 0x800000):
            image = os.pread(fd, 0x10000, offset)
            if len(image) != 0x10000 or int.from_bytes(image[:4], 'little') != zlib.crc32(image[5:]):
                raise ValueError('A redundant U-Boot environment copy is unreadable or has a bad CRC')
            fields = {}
            for entry in image[5:].split(b'\0'):
                if not entry:
                    break
                try:
                    name, value = entry.decode('ascii').split('=', 1)
                except (UnicodeDecodeError, ValueError) as error:
                    raise ValueError('Malformed U-Boot environment record') from error
                if name in fields:
                    raise ValueError('Duplicate U-Boot environment variable')
                fields[name] = value
            selected = {name: fields.get(name) for name in ENV_NAMES}
            validate_environment(selected)
    finally:
        os.close(fd)


def current_operation():
    if OPERATION.is_symlink():
        raise ValueError('RAUC operation marker is unsafe')
    if not OPERATION.exists():
        return None
    st = OPERATION.stat()
    if st.st_uid != 0 or st.st_mode & 0o077:
        raise ValueError('RAUC operation marker ownership or permissions are unsafe')
    record = json.loads(OPERATION.read_text())
    if (not isinstance(record, dict) or set(record) != {'format_version', 'action', 'slot', 'boot_id', 'nonce'} or
            record['format_version'] != 1 or record['action'] not in
            ('install', 'set-primary', 'set-good', 'set-bad') or
            record['slot'] not in ('A', 'B') or
            not re.fullmatch('[0-9a-f]{32}', record['nonce']) or
            record['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()):
        raise ValueError('RAUC operation marker is invalid or stale')
    return record


def read_environment():
    output = subprocess.check_output(['/usr/bin/fw_printenv', '-c', str(ENV_CONFIG), *ENV_NAMES],
                                     text=True, timeout=5, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
    return parse_values(output)


def set_value(name, value):
    if name not in ('BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT'):
        raise ValueError('Refusing to change an unreviewed environment variable')
    subprocess.run(['/usr/bin/fw_setenv', '-c', str(ENV_CONFIG), name, value],
                   check=True, timeout=5, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})


def active_slot():
    boot = json.loads(BOOT.read_text())
    if not isinstance(boot, dict) or boot.get('slot') not in ('A', 'B'):
        raise ValueError('Running boot identity is unavailable')
    return boot['slot']


def handle(arguments, *, read=read_environment, write=set_value, operation=current_operation,
           running=active_slot, verify_copies=verify_environment_copies):
    if os.geteuid() != 0:
        raise ValueError('RAUC bootloader handler requires root')
    verify_copies()
    values = read()
    if len(arguments) == 1 and arguments[0] == 'get-primary':
        return primary(values)
    if len(arguments) == 1 and arguments[0] == 'get-current':
        return running()
    if len(arguments) == 2 and arguments[0] == 'get-state' and arguments[1] in ('A', 'B'):
        return 'good' if slot_good(values, arguments[1]) else 'bad'
    if len(arguments) == 3 and arguments[0] == 'set-state' and arguments[1] in ('A', 'B'):
        slot, state = arguments[1:]
        context = operation()
        if state == 'good':
            if not context or context['action'] != 'set-good' or context['slot'] != slot:
                raise ValueError('Good-state changes require the validated confirmation transaction')
            write('BOOT_'+slot+'_LEFT', '3')
            if read()['BOOT_'+slot+'_LEFT'] != '3':
                raise ValueError('U-Boot did not confirm the selected slot')
            return ''
        if state != 'bad':
            raise ValueError('Unsupported RAUC boot state')
        if context and context['action'] == 'install' and context['slot'] == slot:
            source = running()
            if source not in ('A', 'B') or source == slot or not disabled(values, slot) or primary(values) != source:
                raise ValueError('Refusing RAUC slot write unless its inactive target is disabled and source remains selected')
            return ''  # Exact no-op: preserve both redundant environment copies.
        if not context or context['action'] != 'set-bad' or context['slot'] != slot:
            raise ValueError('Bad-state changes require a validated cancel/fallback transaction')
        order = [name for name in values['BOOT_ORDER'].split() if name != slot]
        new_order = ' '.join(order)
        if not new_order:
            raise ValueError('Refusing to disarm the only configured boot slot')
        if values['BOOT_ORDER'] != new_order:
            write('BOOT_ORDER', new_order)
        if values['BOOT_'+slot+'_LEFT'] != '0':
            write('BOOT_'+slot+'_LEFT', '0')
        after = read()
        if slot_good(after, slot) or primary(after) == slot:
            raise ValueError('U-Boot did not disarm the target')
        return ''
    if len(arguments) == 2 and arguments[0] == 'set-primary' and arguments[1] in ('A', 'B'):
        slot = arguments[1]
        context = operation()
        if not context or context['action'] != 'set-primary' or context['slot'] != slot:
            raise ValueError('Primary changes require the validated arm transaction')
        order = [slot] + [name for name in values['BOOT_ORDER'].split() if name != slot]
        write('BOOT_'+slot+'_LEFT', '3')
        write('BOOT_ORDER', ' '.join(order))
        after = read()
        if primary(after) != slot or not slot_good(after, slot):
            raise ValueError('U-Boot did not select the requested primary slot')
        return ''
    raise ValueError('Unsupported RAUC custom bootloader command')


def main():
    try:
        result = handle(sys.argv[1:])
        if result:
            print(result)
    except Exception as error:
        print('sv08-rauc-bootloader: '+str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
