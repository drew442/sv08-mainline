#!/usr/bin/env python3
"""Exercise the exact A/B dispatcher and a fail-closed recovery selector offline.

The target is a new 256 MiB regular file. The boot payload is deliberately a
non-bootable test FIT; selection prints a marker rather than booting Linux.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zlib


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.build_h616_recovery_handoff import (MARKER, script_text, ENV_BYTES,
                                                   ENV_OFFSETS, GATE_NAMES)
PARTITIONS = ((1, 16, 32, 'boot-a'), (2, 48, 16, 'root-a'),
              (3, 64, 32, 'boot-b'), (4, 96, 16, 'root-b'),
              (5, 112, 64, 'recovery'), (6, 176, 32, 'data'))


def run(*args, cwd=None):
    return subprocess.run([str(a) for a in args], cwd=cwd, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, timeout=60).stdout


def put(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def script(work, name, content):
    source = put(work, name+'.cmd', content.encode())
    output = work / (name+'.scr')
    run('mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none',
        '-n', 'SV08 disposable '+name, '-d', source, output)
    return output


def fit(work):
    put(work, 'kernel.bin', bytes(range(256))*16)
    put(work, 'initrd.bin', b'R'*1024)
    put(work, 'board.dtb', b'D'*512)
    its = '''/dts-v1/;
/ { description = "SV08 disposable handoff test"; #address-cells = <1>;
 images {
  kernel { data = /incbin/("kernel.bin"); type = "kernel";
   arch = "arm64"; os = "linux"; compression = "none";
   load = <0x40080000>; entry = <0x40080000>;
   hash { algo = "sha256"; }; };
  ramdisk { data = /incbin/("initrd.bin"); type = "ramdisk";
   arch = "arm64"; os = "linux"; compression = "none";
   hash { algo = "sha256"; }; };
  fdt { data = /incbin/("board.dtb"); type = "flat_dt";
   arch = "arm64"; compression = "none";
   hash { algo = "sha256"; }; };
 };
 configurations { default = "conf"; conf { kernel = "kernel";
  ramdisk = "ramdisk"; fdt = "fdt"; }; };
};
'''
    put(work, 'writer.its', its.encode())
    run('mkimage', '-f', 'writer.its', 'writer.itb', cwd=work)
    return (work / 'writer.itb').read_bytes()


def selector(payload):
    # The sandbox addresses are independent of the physical ARM64 load map.
    # U-Boot's filesize variable is hexadecimal, including for load mmc.
    return script_text('offline-test-job', 'console=ttyS0,115200 rdinit=/init',
                       len(payload), zlib.crc32(payload), fit_addr=0x6300000,
                       marker_addr=0x6200000, original_addr=0x7000000, env_addrs=(0x5000000, 0x5010000),
                       mmcdev="a",
                       boot_command='echo SV08_TEST_WRITER_SELECTED\n        exit')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uboot', type=Path, required=True)
    parser.add_argument('--dtb', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    work = args.work.resolve()
    if work.exists() or not work.is_relative_to(REPO / 'build'):
        parser.error('Use a new disposable directory under build/')
    print(json.dumps({'execute': args.execute, 'work': str(work)}), flush=True)
    if not args.execute:
        return
    work.mkdir(mode=0o700)
    shutil.copyfile(args.dtb, work / 'test.dtb')
    disk = work / 'mmc10.img'
    with disk.open('xb') as stream:
        stream.truncate(256*1024*1024)
    command = ['sgdisk', '-o']
    for number, start, size, label in PARTITIONS:
        command += ['-n', f'{number}:{start*2048}:+{size}M',
                    '-c', f'{number}:{label}']
    run(*command, disk)
    payload = fit(work)
    original = script(work, 'recovery-original', 'echo SV08_TEST_RECOVERY_UI\n')
    wrapper = script(work, 'recovery-selector', selector(payload))
    dispatch = script(work, 'dispatch',
                      (REPO / 'configs/host-os/boot-dispatch.cmd').read_text())
    # A real successful slot boot does not return to the dispatcher.
    boot = script(work, 'boot', 'echo SV08_TEST_SLOT_BOOT\npoweroff\n')
    for name, offset in (('boot-a', 16), ('boot-b', 64)):
        filesystem = work / (name+'.fat')
        with filesystem.open('xb') as stream:
            stream.truncate(32*1024*1024)
        run('mkfs.vfat', '-F', '32', filesystem)
        run('mcopy', '-i', filesystem, boot, '::boot.scr')
        if name == 'boot-a':
            run('mcopy', '-i', filesystem, dispatch, '::dispatch.scr')
        with disk.open('r+b') as target, filesystem.open('rb') as source:
            target.seek(offset*1024*1024)
            shutil.copyfileobj(source, target)

    recovery_root = work / 'recovery-root'
    recovery_root.mkdir()
    for name, content in (('recovery.scr', wrapper.read_bytes()),
                          ('sv08-reimage/recovery-original.scr', original.read_bytes()),
                          ('sv08-reimage/writer.itb', payload)):
        put(recovery_root, name, content)
    recovery = work / 'recovery.ext4'
    with recovery.open('xb') as stream:
        stream.truncate(64*1024*1024)

    def install_recovery(marker, image=payload, *, original_entry=False):
        marker_path = recovery_root / 'sv08-reimage/armed'
        if marker is None:
            marker_path.unlink(missing_ok=True)
        else:
            marker_path.write_bytes(marker)
        put(recovery_root, 'recovery.scr',
            original.read_bytes() if original_entry else wrapper.read_bytes())
        put(recovery_root, 'sv08-reimage/writer.itb', image)
        run('mkfs.ext4', '-q', '-F', '-d', recovery_root, recovery)
        with disk.open('r+b') as target, recovery.open('rb') as source:
            target.seek(112*1024*1024)
            shutil.copyfileobj(source, target)

    def sandbox(name, setup=''):
        command = ('env select MMC; env load; setenv sv08_mmcdev a; '
                   'setenv scriptaddr 0x6000000; '+setup+
                   'load mmc a:1 ${scriptaddr} dispatch.scr; source ${scriptaddr}')
        output = run(args.uboot.resolve(), '-d', 'test.dtb', '-c', command,
                     cwd=work)
        (work / (name+'.log')).write_text(output)
        return output

    install_recovery(MARKER)
    run(args.uboot.resolve(), '-d', 'test.dtb', '-c',
        'env select MMC; setenv BOOT_ORDER A B; setenv BOOT_A_LEFT 0; '
        'setenv BOOT_B_LEFT 0; setenv sv08_env_layout ab-8gb-v1; '
        'setenv sv08_reimage_arm offline-test-job; '
        'env save; env save', cwd=work)
    # Raw reads use the sandbox's regular-file MMC transport. The exact
    # production read/import/predicate/marker/FIT logic runs in actual U-Boot;
    # only the admitted device number, RAM map and boot action are fixtures.
    values = {'sv08_reimage_arm': 'offline-test-job', 'sv08_env_layout': 'ab-8gb-v1',
              'BOOT_ORDER': 'A B', 'BOOT_A_LEFT': '0', 'BOOT_B_LEFT': '0',
              'sv08_mmcdev': 'hostile', 'bootcmd': 'echo HOSTILE_EXECUTED',
              'scriptaddr': 'hostile', 'unrelated': 'hostile'}

    def record(fields, redundant=True):
        data = b'\0'.join(f'{k}={v}'.encode() for k, v in fields.items()) + b'\0\0'
        data = data.ljust(ENV_BYTES - (5 if redundant else 4), b'\0')
        return zlib.crc32(data).to_bytes(4, 'little') + (b'\1' if redundant else b'') + data

    good = record(values)

    def environments(first=good, second=good):
        with disk.open('r+b') as stream:
            for offset, content in zip(ENV_OFFSETS, (first, second)):
                stream.seek(offset)
                stream.write(content)

    def select_case(name, expected, *, first=good, second=good,
                    marker=MARKER, image=payload, route='a', direct=True,
                    selector_override=None, original_available=True):
        environments(first, second)
        if selector_override is not None:
            replacement = script(work, 'fault-selector', selector_override)
            put(recovery_root, 'recovery.scr', replacement.read_bytes())
            saved_wrapper = wrapper.read_bytes()
            wrapper.write_bytes(replacement.read_bytes())
        original_path = recovery_root / 'sv08-reimage/recovery-original.scr'
        if not original_available:
            original_path.unlink()
        install_recovery(marker, image)
        if selector_override is not None:
            wrapper.write_bytes(saved_wrapper)
        if not original_available:
            original_path.write_bytes(original.read_bytes())
        # Begin with SD/default gates, including valid inherited gates in
        # negative cases: resets before each import must remove them.
        setup = ('setenv sv08_mmcdev "' + route + '"; '
                 'setenv scriptaddr 0x6000000; setenv unrelated retained; '
                 'setenv bootcmd "echo RETAINED_BOOTCMD"; '
                 'setenv sv08_reimage_arm offline-test-job; '
                 'setenv sv08_env_layout ab-8gb-v1; setenv BOOT_ORDER "A B"; '
                 'setenv BOOT_A_LEFT 0; setenv BOOT_B_LEFT 0; ')
        if name == 'sd-default-ram':
            setup += ('setenv sv08_reimage_arm; setenv sv08_env_layout default; '
                      'setenv BOOT_A_LEFT 3; setenv BOOT_B_LEFT 3; ')
        command = setup + ('load mmc a:5 ${scriptaddr} recovery.scr; source ${scriptaddr}; '
                           if direct else
                           'load mmc a:1 ${scriptaddr} dispatch.scr; source ${scriptaddr}; ')
        command += ('echo ROUTE=${sv08_mmcdev}; echo SCRIPT=${scriptaddr}; '
                    'echo UNRELATED=${unrelated}; echo BOOTCMD=${bootcmd}')
        output = run(args.uboot.resolve(), '-d', 'test.dtb', '-c', command, cwd=work)
        (work / (name+'.log')).write_text(output)
        assert expected in output, (name, output)
        assert ('SV08_TEST_RECOVERY_UI' if expected == 'SV08_TEST_WRITER_SELECTED'
                else 'SV08_TEST_WRITER_SELECTED') not in output, (name, output)
        for preserved in (f'ROUTE={route}', 'SCRIPT=0x6000000', 'UNRELATED=retained',
                          'BOOTCMD=echo RETAINED_BOOTCMD'):
            assert preserved in output, (name, preserved, output)
        assert 'HOSTILE_EXECUTED' not in output, (name, output)
        return expected

    cases = {}
    for name in ('armed', 'sd-default-ram'):
        cases[name] = select_case(name, 'SV08_TEST_WRITER_SELECTED')
    for copy in range(2):
        for gate in GATE_NAMES:
            missing = dict(values)
            del missing[gate]
            records = [good, good]; records[copy] = record(missing)
            name = f'copy-{copy}-missing-{gate}'
            cases[name] = select_case(name, 'SV08_TEST_RECOVERY_UI',
                                      first=records[0], second=records[1])
        for gate, wrong in (('sv08_reimage_arm', 'wrong'), ('sv08_env_layout', 'wrong'),
                            ('BOOT_ORDER', 'B A'), ('BOOT_A_LEFT', '1'),
                            ('BOOT_B_LEFT', '1')):
            fields = dict(values, **{gate: wrong})
            records = [good, good]; records[copy] = record(fields)
            name = f'copy-{copy}-wrong-{gate}'
            cases[name] = select_case(name, 'SV08_TEST_RECOVERY_UI',
                                      first=records[0], second=records[1])
        for problem, content in (('crc', bytes([good[0] ^ 1]) + good[1:]),
                                 ('ordinary-header', record(values, redundant=False))):
            records = [good, good]; records[copy] = content
            name = f'copy-{copy}-{problem}'
            cases[name] = select_case(name, 'SV08_TEST_RECOVERY_UI',
                                      first=records[0], second=records[1])
    for name, marker, image in (('absent', None, payload),
                                ('short-marker', b'bad marker\n', payload),
                                ('wrong-marker', b'X'+MARKER[1:], payload),
                                ('wrong-fit', MARKER, payload[:-1] + bytes([payload[-1] ^ 1])),
                                ('short-fit', MARKER, payload[:-1])):
        cases[name] = select_case(name, 'SV08_TEST_RECOVERY_UI', marker=marker, image=image)
    # Changed/unknown routing cannot admit the writer; an unavailable original
    # route retains the independent-rescue stop.
    cases['changed-route'] = select_case('changed-route', 'SV08 recovery unavailable', route='0')
    cases['missing-route'] = select_case('missing-route', 'SV08 recovery unavailable', route='')
    # Transport failure injection changes only the read operand/device hwpart;
    # all subsequent actual U-Boot import and fallback logic stays intact.
    for copy, block in enumerate(('2000', '4000')):
        name = f'copy-{copy}-read-failure'
        command = selector(payload).replace(f'{block} 80; then', '1000000 80; then')
        cases[name] = select_case(name, 'SV08_TEST_RECOVERY_UI', selector_override=command)
    cases['wrong-hardware-partition'] = select_case('wrong-hardware-partition',
        'SV08_TEST_RECOVERY_UI', selector_override=selector(payload).replace('mmc dev 10 0',
                                                                            'mmc dev 10 7'))
    # Recompute the outer CRC only in this fixture to reach iminfo's component
    # hashes, then prove a corrupt member still reaches original recovery.
    corrupted = bytearray(payload)
    offset = payload.index(bytes(range(256)))
    corrupted[offset] ^= 1
    corrupted = bytes(corrupted)
    cases['fit-component-hash'] = select_case('fit-component-hash', 'SV08_TEST_RECOVERY_UI',
        image=corrupted, selector_override=selector(corrupted))
    cases['original-unavailable'] = select_case('original-unavailable',
        'SV08 recovery unavailable', marker=None, original_available=False)
    environments()
    install_recovery(None, original_entry=True)
    output = sandbox('stage-before-wrapper')
    assert 'SV08_TEST_RECOVERY_UI' in output and 'SV08_TEST_WRITER_SELECTED' not in output
    cases['stage-before-wrapper'] = 'SV08_TEST_RECOVERY_UI'
    # Partial arming must fail even with a valid marker, regardless of which
    # copy the ordinary environment loader would select.
    old = record(dict(values, BOOT_A_LEFT='3', sv08_reimage_arm=''))
    for first, second, name in ((old, good, 'mixed-old-new'), (good, old, 'mixed-new-old')):
        cases[name] = select_case(name, 'SV08_TEST_RECOVERY_UI', first=first, second=second)
    # Keep actual dispatcher regressions distinct from direct SD-default entry.
    install_recovery(None)
    environments()
    output = sandbox('stage-both-env-copies-no-marker')
    assert 'SV08_TEST_RECOVERY_UI' in output and 'SV08_TEST_WRITER_SELECTED' not in output
    cases['stage-both-env-copies-no-marker'] = 'SV08_TEST_RECOVERY_UI'
    output = sandbox('valid-slot', 'setenv BOOT_A_LEFT 3; ')
    assert 'SV08_TEST_SLOT_BOOT' in output and 'SV08_TEST_WRITER_SELECTED' not in output
    cases['valid-slot'] = 'SV08_TEST_SLOT_BOOT'
    result = {'physical_hardware': False, 'exact_dispatcher': True,
              'actual_rauc_bootmeth': True, 'recovery_filesystem': 'ext4',
              'cases': cases, 'uboot_sha256': hashlib.sha256(args.uboot.read_bytes()).hexdigest(),
              'target_is_regular_file': disk.is_file(), 'writer_booted': False,
              'environment_import': 'actual CRC-checked redundant env_t whitelist',
              'transport': 'sandbox regular-file MMC reads; no physical MMC',
              'fixture_substitutions': ['device a/user area 0', 'sandbox RAM addresses',
                                        'echo/exit instead of Linux boot',
                                        'invalid block/hwpart operands for read failures',
                                        'recomputed outer CRC for component-hash failure']}
    (work / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
