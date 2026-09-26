#!/usr/bin/python3
"""Bind QEMU-only test devices before production RAUC health observation."""
import os
from pathlib import Path
import subprocess


def serial_devices():
    found = {}
    for path in Path('/sys/block').glob('*/serial'):
        value = path.read_text().strip()
        if value:
            if value in found:
                raise ValueError('Duplicate QEMU block-device serial')
            found[value] = path.parent.name
    return found


def main():
    if subprocess.check_output(['/usr/bin/systemd-detect-virt', '--vm'], text=True).strip() != 'qemu':
        raise ValueError('QEMU environment setup ran outside QEMU')
    if 'sv08.test=rauc-backend' not in Path('/proc/cmdline').read_text().split():
        raise ValueError('QEMU environment setup lacks the fixture boot marker')
    devices = serial_devices()
    if set(devices) != {'SV08-QEMU-TARGET', 'SV08-QEMU-FEED'}:
        raise ValueError('Unexpected QEMU fixture devices: ' + repr(devices))
    root = os.stat('/')
    node = Path('/sys/dev/block') / f'{os.major(root.st_dev)}:{os.minor(root.st_dev)}'
    resolved = node.resolve(strict=True)
    target = resolved.parent.name
    if devices['SV08-QEMU-TARGET'] != target:
        raise ValueError('Mounted root is not on the identified disposable target disk')
    fixture = '/dev/' + devices['SV08-QEMU-FEED']
    Path('/run/sv08').mkdir(mode=0o700, parents=True, exist_ok=True)
    env_config = Path('/run/sv08/qemu-fw-env.config')
    env_config.write_text(f'/dev/{target} 0x400000 0x10000\n/dev/{target} 0x800000 0x10000\n')
    env_config.chmod(0o600)
    subprocess.run(['/usr/bin/mount', '--bind', str(env_config), '/etc/fw_env.config'], check=True)
    subprocess.run(['/usr/bin/mount', '-o', 'remount,bind,ro', '/etc/fw_env.config'], check=True)
    if not os.statvfs('/etc/fw_env.config').f_flag & os.ST_RDONLY:
        raise ValueError('Disposable U-Boot environment config is unexpectedly writable')
    feed_mount = Path('/run/sv08/fixture-feed')
    feed_mount.mkdir(mode=0o700)
    subprocess.run(['/usr/bin/mount', '-t', 'ext4', '-o', 'ro', fixture, str(feed_mount)], check=True)
    try:
        subprocess.run(['/usr/bin/systemctl', 'start', 'rauc.service'], check=True, timeout=45)
        status = subprocess.run(['/usr/bin/rauc', 'status', '--output-format=json'], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False, timeout=8)
        print('SV08_QEMU_RAUC_STATUS rc=' + str(status.returncode) + ' output=' + status.stdout, flush=True)
        if status.returncode:
            raise RuntimeError('RAUC status command failed')
    except subprocess.TimeoutExpired as error:
        print('SV08_QEMU_RAUC_STATUS_TIMEOUT ' + repr(error), flush=True)
        result = subprocess.run(['/usr/bin/journalctl', '-b', '-u', 'rauc.service', '--no-pager'],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False, timeout=15)
        print('SV08_QEMU_RAUC_JOURNAL ' + result.stdout, flush=True)
        raise
    except BaseException:
        for command in (['/usr/bin/systemctl', 'status', '--no-pager', 'rauc.service'],
                        ['/usr/bin/journalctl', '-b', '-u', 'rauc.service', '--no-pager']):
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, check=False, timeout=15)
            print('SV08_QEMU_RAUC_DIAGNOSTIC_BEGIN ' + ' '.join(command), flush=True)
            print(result.stdout, flush=True)
        raise


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        print('SV08_QEMU_ENV_SETUP_FAILURE ' + repr(error), flush=True)
        subprocess.run(['/usr/bin/systemctl', 'poweroff'], check=False, timeout=20)
        raise
