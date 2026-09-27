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
import zlib


REPO = Path(__file__).resolve().parents[1]
MARKER = b'SV08-REIMAGE-ONCE\n'
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
    return f'''# Disposable selector: original recovery remains the default.
if test "${{sv08_reimage_arm}}" = "offline-test-job" && test "${{sv08_env_layout}}" = "ab-8gb-v1" && test "${{BOOT_ORDER}}" = "A B" && test "${{BOOT_A_LEFT}}" = "0" && test "${{BOOT_B_LEFT}}" = "0"; then
if load mmc ${{sv08_mmcdev}}:5 0x6200000 sv08-reimage/armed; then
 if test ${{filesize}} = {len(MARKER):x}; then
  if crc32 -v 0x6200000 ${{filesize}} {zlib.crc32(MARKER):08x}; then
   if load mmc ${{sv08_mmcdev}}:5 0x6300000 sv08-reimage/writer.itb; then
    if test ${{filesize}} = {len(payload):x}; then
     if crc32 -v 0x6300000 ${{filesize}} {zlib.crc32(payload):08x}; then
      if iminfo 0x6300000; then
       echo SV08_TEST_WRITER_SELECTED
       exit
      fi
     fi
    fi
   fi
  fi
 fi
fi
fi
if load mmc ${{sv08_mmcdev}}:5 0x7000000 sv08-reimage/recovery-original.scr; then
 source 0x7000000
fi
'''


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

    def install_recovery(marker, image=payload):
        marker_path = recovery_root / 'sv08-reimage/armed'
        if marker is None:
            marker_path.unlink(missing_ok=True)
        else:
            marker_path.write_bytes(marker)
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
    cases = {}
    for name, marker, image, expected in (
        ('armed', MARKER, payload, 'SV08_TEST_WRITER_SELECTED'),
        ('absent', None, payload, 'SV08_TEST_RECOVERY_UI'),
        ('short-marker', b'bad marker\n', payload, 'SV08_TEST_RECOVERY_UI'),
        ('wrong-marker', b'X'+MARKER[1:], payload, 'SV08_TEST_RECOVERY_UI'),
        ('wrong-fit', MARKER, payload[:-1]+bytes([payload[-1] ^ 1]),
         'SV08_TEST_RECOVERY_UI')):
        install_recovery(marker, image)
        output = sandbox(name)
        assert expected in output, (name, output)
        forbidden = ('SV08_TEST_RECOVERY_UI' if expected == 'SV08_TEST_WRITER_SELECTED'
                     else 'SV08_TEST_WRITER_SELECTED')
        assert forbidden not in output, (name, output)
        cases[name] = expected
    install_recovery(MARKER)
    unarmed = sandbox('wrong-arm-token', 'setenv sv08_reimage_arm wrong; ')
    assert 'SV08_TEST_RECOVERY_UI' in unarmed and 'SV08_TEST_WRITER_SELECTED' not in unarmed
    valid = sandbox('valid-slot', 'setenv BOOT_A_LEFT 3; ')
    assert 'SV08_TEST_SLOT_BOOT' in valid and 'SV08_TEST_WRITER_SELECTED' not in valid
    install_recovery(MARKER)
    invalid = sandbox('invalid-order', 'setenv BOOT_ORDER "A A"; ')
    assert 'SV08_TEST_RECOVERY_UI' in invalid and 'SV08_TEST_WRITER_SELECTED' not in invalid
    install_recovery(MARKER)
    for offset in (4*1024*1024, 8*1024*1024):
        with disk.open('r+b') as stream:
            stream.seek(offset+100)
            value = stream.read(1)
            stream.seek(offset+100)
            stream.write(bytes([value[0] ^ 1]))
        if offset == 4*1024*1024:
            one_corrupt = sandbox('one-env-copy-corrupt')
            assert ('SV08_TEST_WRITER_SELECTED' in one_corrupt and
                    'SV08_TEST_RECOVERY_UI' not in one_corrupt)
            install_recovery(MARKER)
    corrupt = sandbox('both-env-copies-corrupt')
    assert 'SV08_TEST_RECOVERY_UI' in corrupt and 'SV08_TEST_WRITER_SELECTED' not in corrupt
    cases.update(valid_slot='SV08_TEST_SLOT_BOOT',
                 wrong_arm_token='SV08_TEST_RECOVERY_UI',
                 invalid_order='SV08_TEST_RECOVERY_UI',
                 one_env_copy_corrupt='SV08_TEST_WRITER_SELECTED',
                 both_env_copies_corrupt='SV08_TEST_RECOVERY_UI')
    result = {'physical_hardware': False, 'exact_dispatcher': True,
              'actual_rauc_bootmeth': True, 'recovery_filesystem': 'ext4',
              'cases': cases, 'uboot_sha256': hashlib.sha256(args.uboot.read_bytes()).hexdigest(),
              'target_is_regular_file': disk.is_file(), 'writer_booted': False}
    (work / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
