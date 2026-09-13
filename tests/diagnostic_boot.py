#!/usr/bin/env python3
"""Exercise the one-shot dispatcher in U-Boot sandbox on fresh FAT files only."""
import argparse
import json
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uboot', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    work, uboot = args.work.resolve(), args.uboot.resolve()
    if work.exists() or not work.is_relative_to(REPO / 'build'):
        parser.error('Use a fresh work directory below build/')
    if not args.execute:
        print(json.dumps(dict(work=str(work), execute=False)))
        return
    work.mkdir(parents=True)

    def run(command):
        return subprocess.run([str(v) for v in command], cwd=work, check=True,
                              capture_output=True, text=True, timeout=45).stdout

    template = (REPO / 'configs/host-os/diagnostic-boot.cmd.in').read_text()
    source = template.replace('@TARGET@', 'host 0:0').replace(
        '@ROOT_UUID@', '00000000-0000-4000-8000-000000000001')
    (work / 'trial.cmd').write_text(source)
    run(['mkimage', '-A', 'arm', '-T', 'script', '-C', 'none', '-n',
         'offline diagnostic test', '-d', 'trial.cmd', 'trial.scr'])
    (work / 'payload').write_bytes(bytes(4096))

    def setup(name, marker='file', payload=True):
        disk = work / (name + '.fat')
        with disk.open('xb') as out:
            out.truncate(16 * 1024 * 1024)
        run(['mkfs.vfat', '-F', '16', disk])
        run(['mmd', '-i', disk, '::sv08-trial-61851-c1'])
        run(['mcopy', '-i', disk, 'trial.scr', '::trial.scr'])
        if marker == 'file':
            run(['mcopy', '-i', disk, 'payload', '::sv08-trial-61851-c1/armed'])
        elif marker == 'directory':
            run(['mmd', '-i', disk, '::sv08-trial-61851-c1/armed'])
            run(['mcopy', '-i', disk, 'payload', '::sv08-trial-61851-c1/armed/keep'])
        if payload:
            for target in ('Image', 'board.dtb', 'uInitrd'):
                run(['mcopy', '-i', disk, 'payload', '::sv08-trial-61851-c1/' + target])
        return disk

    def boot(disk, name, devnum='0'):
        commands = (
            f'host bind 0 {disk}; setenv devtype host; setenv devnum {devnum}; '
            'setenv distro_bootpart 0; setenv kernel_addr_r 0x200000; '
            'setenv fdt_addr_r 0x400000; setenv ramdisk_addr_r 0x600000; '
            'load host 0:0 0x100000 /trial.scr; source 0x100000'
        )
        output = run([uboot, '-c', commands])
        (work / (name + '.log')).write_text(output)
        assert 'SV08_TRIAL_RETURN_TO_ORIGINAL' in output, output[-2000:]
        assert 'Unknown command' not in output, output[-2000:]
        return output

    disk = setup('normal')
    output = boot(disk, 'consumed-returned-boot')
    assert output.index('SV08_TRIAL_MARKER_CONSUMED') < output.index('SV08_TRIAL_HANDOFF')
    assert 'SV08_TRIAL_HANDOFF' not in boot(disk, 'second-invocation')
    output = boot(setup('no-marker', marker=None), 'no-marker')
    assert 'SV08_TRIAL_HANDOFF' not in output
    output = boot(setup('missing-image', payload=False), 'missing-image')
    assert 'SV08_TRIAL_MARKER_CONSUMED' in output and 'SV08_TRIAL_HANDOFF' not in output
    output = boot(setup('delete-refusal', marker='directory'), 'delete-refusal')
    assert 'SV08_TRIAL_REFUSED_MARKER_DELETE' in output and 'SV08_TRIAL_HANDOFF' not in output
    disk = setup('wrong-device')
    output = boot(disk, 'wrong-device', devnum='1')
    assert 'SV08_TRIAL_REFUSED_BOOT_TARGET' in output and 'SV08_TRIAL_HANDOFF' not in output
    # Refusing the wrong device must leave its marker available for the right one.
    assert 'SV08_TRIAL_HANDOFF' in boot(disk, 'right-device-after-refusal')
    result = dict(passed=True, invocations=7, actual_fat=True,
                  real_kernel_handoff=False, hardware_validated=False)
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
