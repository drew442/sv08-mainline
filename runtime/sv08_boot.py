#!/usr/bin/env python3
"""Early-boot persistence integration. Hardware mounts require explicit execution.

Device paths come from the image's reviewed GPT manifest. No device inference or
partition writes. This prepares state/mounts before application services start.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import uuid
from sv08_state import Store, fsync_dir
from sv08_mounts import apply


def slot_from_cmdline(cmdline):
    slots = [x.split('=', 1)[1] for x in cmdline.split() if x.startswith('rauc.slot=')]
    if len(slots) != 1 or slots[0] not in ('A', 'B'):
        raise ValueError('Boot must identify exactly one RAUC slot A or B')
    return slots[0]


def device_number(path):
    if not re.fullmatch(r'/dev/disk/by-partuuid/[0-9a-fA-F-]{36}', path):
        raise ValueError('Expected an explicit GPT PARTUUID device')
    st = os.stat(path)
    if not stat.S_ISBLK(st.st_mode):
        raise ValueError('Configured source is not a block device')
    return f'{os.major(st.st_rdev)}:{os.minor(st.st_rdev)}'


def verify_devices(config, slot, read_command=None):
    expected_root = device_number(config['devices']['root-' + slot.lower()])
    expected_data = device_number(config['devices']['data'])
    expected_boot = device_number(config['devices']['boot-' + slot.lower()])
    if len({expected_root, expected_data, expected_boot}) != 3:
        raise ValueError('Root, boot and data must be different partitions')
    for mount, expected in (('/', expected_root), ('/data', expected_data)):
        actual = (read_command or subprocess.check_output)(['findmnt', '-n', '-o', 'MAJ:MIN', '--mountpoint', mount], text=True).strip()
        if actual != expected:
            raise ValueError('Mounted device differs from release manifest: ' + mount)


def initialize_identity(data):
    system = data / 'system'
    for name in ('machine-id', 'hostname', 'hosts', 'ssh', 'ssh/ssh_host_ed25519_key',
                 'ssh/ssh_host_ed25519_key.pub', 'random-seed'):
        path = system / name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Persistent identity must not contain symlinks')
    seed = system / 'random-seed'
    if not seed.exists():
        # systemd fills/rotates this on the device; never ship a cloned seed.
        with seed.open('xb') as stream:
            os.chmod(seed, 0o600)
            os.fsync(stream.fileno())
    machine_id = system / 'machine-id'
    if not machine_id.exists():
        with machine_id.open('x') as stream:
            stream.write(uuid.uuid4().hex + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    if not re.fullmatch('[0-9a-f]{32}\n?', machine_id.read_text()):
        raise ValueError('Invalid persistent machine identity; do not regenerate silently')
    for filename, content in [('hostname', 'sv08\n'), ('hosts', '127.0.0.1 localhost\n127.0.1.1 sv08\n::1 localhost ip6-localhost\n')]:
        path = system / filename
        if not path.exists():
            with path.open('x') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
    key = system / 'ssh/ssh_host_ed25519_key'
    if not key.exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
        with key.open('rb') as stream:
            os.fsync(stream.fileno())
    subprocess.run(['ssh-keygen', '-y', '-P', '', '-f', str(key)], check=True,
                   stdout=subprocess.DEVNULL)
    key.chmod(0o600)
    fsync_dir(system / 'ssh')
    fsync_dir(system)


def prepare_permissions(data, generation, uid=1000, gid=1000):
    # Traverse-only parents; registry, host keys and network credentials stay root-owned.
    for path in (data, data / 'generations', Path(generation), data / 'shared', data / 'users'):
        os.chmod(path, 0o711)
    for name in ('config', 'database', 'ui'):
        directory = Path(generation) / name
        # copytree/copy2 preserve mode and times, but not ownership. Repair only
        # this generation, never the fallback generation or shared system state.
        for path in (directory, *directory.rglob('*')):
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise ValueError('Application state contains an unsupported file type')
            os.chown(path, uid, gid)
    for path in [Path(generation) / n for n in ('config', 'database', 'ui')] + [data / 'shared' / n for n in ('gcodes', 'timelapse')] + [data / 'users/sv08']:
        os.chown(path, uid, gid)
        os.chmod(path, 0o750)
    os.chmod(data / 'shared/logs', 0o755)
    logs = data / 'shared/logs/printer'
    logs.mkdir(exist_ok=True)
    os.chown(logs, uid, gid)
    os.chmod(logs, 0o750)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    config = json.loads(Path('/usr/lib/sv08/release.json').read_text())
    slot = slot_from_cmdline(Path('/proc/cmdline').read_text())
    verify_devices(config, slot)
    if not args.execute:
        print(json.dumps(dict(execute=False, slot=slot, release=config['release'])))
        return
    if os.geteuid() != 0:
        parser.error('Early-boot execution requires root')
    data = Path('/data/sv08')
    store = Store(data)
    store.initialize()
    initialize_identity(data)
    if Path('/etc/machine-id').read_text().strip() != (data / 'system/machine-id').read_text().strip():
        raise ValueError('Initramfs must prepare persistent identity before systemd starts')
    boot = store.prepare_boot(slot, config['release'], config['state_schema'])
    generation = Path(boot['generation'])
    if not store.load()['slots'][slot]['parent_generation']:
        for seed in Path('/usr/lib/sv08/seed/config').glob('*'):
            dest = generation / 'config' / seed.name
            if not dest.exists():
                shutil.copyfile(seed, dest)
                os.chown(dest, 1000, 1000)
    prepare_permissions(data, boot['generation'])
    # /boot is paired with the actual root device; never mount the other slot here.
    subprocess.run(['mount', '-t', 'vfat', '-o', 'ro' if boot['mode'] == 'immutable' else 'rw',
                    config['devices']['boot-' + slot.lower()], '/boot'], check=True)
    apply(Path('/'), data, boot)
    if boot['trial']:
        # Fail closed until OS health confirmation is implemented and validated.
        Path('/run/sv08/trial').touch()
    runtime = Path('/run/sv08/printer_data')
    os.chown(runtime, 1000, 1000)
    os.chown(runtime / 'comms', 1000, 1000)


if __name__ == '__main__':
    main()
