#!/usr/bin/env python3
"""Test redundant raw MMC environment with real sandbox, libubootenv and RAUC.

Only newly copied regular-file fixtures below build/ are mutated. No physical
hardware, installation, or production environment configuration is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import time
import zlib

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from check_gpt_layout import inspect


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs).stdout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('uboot', 'dtb', 'image', 'rauc', 'work'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    a.uboot, a.dtb, a.image, a.rauc, work = (v.resolve() for v in
        (a.uboot, a.dtb, a.image, a.rauc, a.work))
    if work.exists() or not work.is_relative_to(REPO / 'build') or work == REPO / 'build':
        p.error('Use a new disposable directory below build/')
    layout = json.loads((REPO / 'configs/host-os/environment-layout.json').read_text())
    size = layout['size_bytes']
    offsets = layout['copy_offsets_bytes']
    regions = [(off, size) for off in offsets]
    geometry = inspect(a.image, environment_regions=regions)
    if [v['name'] for v in geometry['partition_records']] != [
            'boot-a', 'root-a', 'boot-b', 'root-b', 'recovery', 'data']:
        p.error('Expected six-partition offline layout fixture')
    print(json.dumps({'execute': a.execute, 'work': str(work)}), flush=True)
    if not a.execute:
        return
    work.mkdir(mode=0o700)
    disk = work / 'mmc10.img'
    run(['cp', '--reflink=auto', '--sparse=always', a.image, disk])
    shutil.copyfile(a.dtb, work / 'test.dtb')
    config = work / 'fw_env.config'
    config.write_text(''.join(f'{disk} {off:#x} {size:#x}\n' for off in offsets))
    toolpaths = {name: shutil.which(name) for name in ('fw_printenv', 'fw_setenv')}
    if not all(toolpaths.values()):
        raise RuntimeError('Install libubootenv-tool')

    def sandbox(commands, name):
        result = run([a.uboot, '-d', 'test.dtb', '-c', commands], cwd=work)
        (work / (name+'.log')).write_text(result)
        return result

    def linux(name):
        return run([toolpaths['fw_printenv'], '-c', config, '-n', name]).strip()

    def setenv(name, value):
        run([toolpaths['fw_setenv'], '-c', config, name, value])

    # Build safe scripts ourselves: boot slots only print a marker and return.
    # The recovery marker is not a recovery OS or evidence of a Linux boot.
    for label, source in [('boot', 'echo SV08_TEST_BOOT ${raucargs} rootpart=${distro_rootpart}\n'),
                          ('recovery', 'echo SV08_TEST_RECOVERY\n'),
                          ('dispatch', (REPO / 'configs/host-os/boot-dispatch.cmd').read_text())]:
        (work / (label+'.cmd')).write_text(source)
        run(['mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none', '-n', 'offline-test-only',
             '-d', work / (label+'.cmd'), work / (label+'.scr')])
    with disk.open('r+b') as target:
        for part in geometry['partition_records']:
            if part['name'] not in ('boot-a', 'boot-b', 'recovery'):
                continue
            fs = work / (part['name']+'.fat')
            with fs.open('xb') as stream:
                stream.truncate(part['size_bytes'])
            run(['mkfs.vfat', '-F', '32', fs])
            label = 'recovery' if part['name'] == 'recovery' else 'boot'
            run(['mcopy', '-i', fs, work / (label+'.scr'), '::'+label+'.scr'])
            if part['name'] == 'boot-a':
                run(['mcopy', '-i', fs, work / 'dispatch.scr', '::dispatch.scr'])
            target.seek(part['offset_bytes'])
            with fs.open('rb') as stream:
                shutil.copyfileobj(stream, target)

    def outside_hash():
        digest = hashlib.sha256()
        with disk.open('rb') as stream:
            start = 0
            for end, length in regions + [(disk.stat().st_size, 0)]:
                stream.seek(start)
                remaining = end - start
                while remaining:
                    block = stream.read(min(8*1024*1024, remaining))
                    if not block:
                        raise RuntimeError('Unexpected end of disk')
                    digest.update(block)
                    remaining -= len(block)
                start = end + length
        return digest.hexdigest()

    original = outside_hash()
    sandbox('env select MMC; setenv BOOT_ORDER A B; setenv BOOT_A_LEFT 3; '
            'setenv BOOT_B_LEFT 0; setenv sv08_env_layout ab-8gb-v1; env save; '
            'setenv BOOT_ORDER B A; setenv BOOT_B_LEFT 3; env save', 'seed')
    assert linux('BOOT_ORDER') == 'B A'
    setenv('BOOT_ORDER', 'A B')
    assert 'BOOT_ORDER=A B' in sandbox('env select MMC; env load; printenv BOOT_ORDER', 'linux-to-uboot')

    # Every RAUC subprocess is forced to the disposable file configuration.
    wrappers = work / 'bin'
    wrappers.mkdir()
    for name, executable in toolpaths.items():
        wrapper = wrappers / name
        wrapper.write_text('#!/bin/sh\nexec '+shlex.quote(executable)+' -c '+
                           shlex.quote(str(config))+' "$@"\n')
        wrapper.chmod(0o700)
    rauc_config = work / 'system.conf'
    (work / 'state').mkdir()
    content = f'''[system]
compatible=sv08-offline-test-only
bootloader=uboot
activate-installed=false
data-directory={work / 'state'}
'''
    for i, slot in enumerate(('A', 'B')):
        slotfile = work / (slot+'.raw')
        slotfile.write_bytes(b'offline-slot-placeholder')
        content += f'\n[slot.rootfs.{i}]\ndevice={slotfile}\ntype=raw\nbootname={slot}\n'
    rauc_config.write_text(content)
    bus = subprocess.Popen(['dbus-daemon', '--session', '--nofork', '--print-address=1'],
                           stdout=subprocess.PIPE, text=True)
    service = None
    try:
        env = dict(os.environ, DBUS_SYSTEM_BUS_ADDRESS=bus.stdout.readline().strip(),
                   PATH=str(wrappers)+os.pathsep+os.environ['PATH'])
        with (work / 'rauc-service.log').open('w') as log:
            service = subprocess.Popen([str(a.rauc), '--conf='+str(rauc_config),
                'service', '--override-boot-slot=A'], env=env, stdout=log, stderr=log)
            for attempt in range(100):
                result = subprocess.run([str(a.rauc), '--conf='+str(rauc_config), 'status'],
                                        env=env, capture_output=True)
                if result.returncode == 0:
                    break
                if service.poll() is not None:
                    raise RuntimeError((work / 'rauc-service.log').read_text())
                time.sleep(.1)
            else:
                raise RuntimeError('RAUC did not start')
            def status(action):
                output = run([a.rauc, '--conf='+str(rauc_config), 'status', action, 'rootfs.1'], env=env)
                (work / (action+'.log')).write_text(output)
            status('mark-active')
            assert linux('BOOT_ORDER') == 'B A' and linux('BOOT_B_LEFT') == '3'
            output = sandbox('env select MMC; env load; bootmeth order rauc; bootflow scan -b', 'trial-b')
            assert 'SV08_TEST_BOOT rauc.slot=B rootpart=4' in output, output
            assert linux('BOOT_B_LEFT') == '2'
            status('mark-bad')
            assert linux('BOOT_B_LEFT') == '0' and linux('BOOT_ORDER') == 'A'
            output = sandbox('env select MMC; env load; bootmeth order rauc; bootflow scan -b', 'fallback-a')
            assert 'SV08_TEST_BOOT rauc.slot=A rootpart=2' in output, output
            assert linux('BOOT_A_LEFT') == '2'
            status('mark-active')
            status('mark-good')
            assert linux('BOOT_B_LEFT') == '3'
    finally:
        for process in (service, bus):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    # Two writes guarantee different recent valid copies. Corrupt the latest
    # data CRC, rather than assuming a particular redundancy flag ordering.
    setenv('sv08_test_sequence', 'older')
    setenv('sv08_test_sequence', 'newer')
    banks = []
    with disk.open('r+b') as stream:
        for off in offsets:
            stream.seek(off)
            bank = stream.read(size)
            assert struct.unpack('<I', bank[:4])[0] == zlib.crc32(bank[5:])
            banks.append(bank)
        latest = next(i for i, bank in enumerate(banks) if b'sv08_test_sequence=newer\0' in bank)
        stream.seek(offsets[latest]+100)
        stream.write(bytes([banks[latest][100] ^ 1]))
    assert linux('sv08_test_sequence') == 'older'
    assert 'sv08_test_sequence=older' in sandbox(
        'env select MMC; env load; printenv sv08_test_sequence', 'one-copy-corrupt')
    with disk.open('r+b') as stream:
        other = 1-latest
        stream.seek(offsets[other]+100)
        stream.write(bytes([banks[other][100] ^ 1]))
    invalid = subprocess.run([toolpaths['fw_printenv'], '-c', str(config)], capture_output=True)
    assert invalid.returncode != 0
    dispatch = 'setenv sv08_mmcdev a; load mmc a:1 ${scriptaddr} dispatch.scr; source ${scriptaddr}'
    output = sandbox('env select MMC; env load; '+dispatch, 'both-copies-corrupt')
    assert 'SV08_TEST_RECOVERY' in output and 'SV08_TEST_BOOT' not in output, output
    with disk.open('r+b') as stream:
        for off, bank in zip(offsets, banks):
            stream.seek(off)
            stream.write(bank)
    setenv('BOOT_A_LEFT', '0')
    setenv('BOOT_B_LEFT', '0')
    output = sandbox('env select MMC; env load; '+dispatch, 'exhausted')
    assert 'SV08_TEST_RECOVERY' in output and 'SV08_TEST_BOOT' not in output, output
    assert linux('BOOT_A_LEFT') == linux('BOOT_B_LEFT') == '0'
    rejection_cases = {
        'excluded-slot-has-attempts': {'BOOT_ORDER': 'A', 'BOOT_A_LEFT': '0', 'BOOT_B_LEFT': '3'},
        'invalid-counter': {'BOOT_ORDER': 'A B', 'BOOT_A_LEFT': '4'},
        'invalid-order': {'BOOT_ORDER': 'A A', 'BOOT_A_LEFT': '3'},
        'empty-order': {'BOOT_ORDER': ''},
        'wrong-layout': {'BOOT_ORDER': 'A B', 'sv08_env_layout': 'other-layout'},
    }
    for name, changes in rejection_cases.items():
        for key, value in changes.items():
            setenv(key, value)
        output = sandbox('env select MMC; env load; '+dispatch, name)
        assert 'SV08_TEST_RECOVERY' in output and 'SV08_TEST_BOOT' not in output, output
    assert outside_hash() == original, 'Writes escaped the two environment reservations'
    inspect(disk, environment_regions=regions)
    report = dict(physical_hardware=False, bidirectional_environment=True,
        rauc_backend='uboot with real libubootenv and sandbox raw MMC',
        trial_b_decrement=True, fallback_a_decrement=True, single_corrupt_copy_fallback=True,
        both_corrupt_copies_recovery_dispatch=True, exhausted_recovery_dispatch=True,
        outside_environment_unchanged=True, recovery_os_booted=False,
        invalid_environment_cases=list(rejection_cases),
        uboot_sha256=hashlib.file_digest(a.uboot.open('rb'), 'sha256').hexdigest(),
        environment_layout=layout)
    (work / 'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
