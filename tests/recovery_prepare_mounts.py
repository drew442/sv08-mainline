#!/usr/bin/env python3
"""Disposable proof that whole-disk/partition RO precedes a no-replay mount.

Run with:
  sudo unshare --mount --propagation private python3 tests/recovery_prepare_mounts.py \
      --work build/recovery-prepare-mounts --execute
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'runtime'))
from sv08_recovery_media import mount_table
from sv08_recovery_prepare import PreparationKernel


def run(*args, **kwargs):
    return subprocess.run([str(value) for value in args], check=True, text=True,
                          capture_output=kwargs.pop('capture_output', False), **kwargs)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    work = args.work.resolve()
    if not work.is_relative_to(REPO / 'build') or work.exists():
        parser.error('Use a fresh disposable directory under this checkout build/')
    if not args.execute:
        print(json.dumps(dict(execute=False, work=str(work))))
        return
    if os.geteuid() != 0 or os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
        parser.error('Use root in a private mount namespace')
    for tool in ('sfdisk', 'losetup', 'mkfs.ext4', 'mount', 'umount', 'blockdev'):
        if shutil.which(tool) is None: parser.error('Missing fixture tool: '+tool)
    work.mkdir(mode=0o700)
    image = work / 'source.img'
    with image.open('xb') as stream: stream.truncate(96 * 1024**2)
    run('sfdisk', image, input='label: gpt\nsize=65536, type=L\n')
    loop = subprocess.check_output(['losetup', '--find', '--show', '--partscan', str(image)], text=True).strip()
    partition = Path(loop+'p1')
    mountpoint = work / 'source'
    events = []
    try:
        run('blockdev', '--setrw', loop)
        run('blockdev', '--setrw', partition)
        run('mkfs.ext4', '-q', '-F', partition)
        before = sha(image)
        kernel = PreparationKernel()
        identity = kernel._identity((Path('/sys/class/block') / partition.name).resolve())
        original = subprocess.run
        def observed(command, *positional, **keywords):
            if command[0].endswith('blockdev'):
                events.append('setro:'+command[-1])
            elif command[0].endswith('mount'):
                events.append('mount:'+command[-1])
            return original(command, *positional, **keywords)
        with patch('sv08_recovery_prepare.subprocess.run', observed):
            kernel.set_readonly(identity)
            kernel.mount(identity, mountpoint, 'ro,noload,nosuid,nodev,noexec', 'ext4')
        line = next(line for line in Path('/proc/self/mountinfo').read_text().splitlines()
                    if line.split()[4] == str(mountpoint))
        row = mount_table(line+'\n')[0]
        assert events[:2] == ['setro:'+loop, 'setro:'+str(partition)], events
        assert events[2] == 'mount:'+str(mountpoint), events
        assert 'ro' in row['options'] and 'ro' in row['super_options']
        assert 'norecovery' in row['super_options'] or 'noload' in row['super_options']
        kernel.unmount(mountpoint)
        assert sha(image) == before
        print(json.dumps(dict(passed=True, source_image_unchanged=True,
                              whole_before_partition_before_mount=True,
                              ext4_no_replay=True, events=events), indent=2))
    finally:
        if mountpoint.is_mount(): run('umount', mountpoint)
        run('losetup', '-d', loop)


if __name__ == '__main__': main()
