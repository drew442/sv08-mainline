#!/usr/bin/env python3
"""Prove a private mount namespace keeps the admitted recovery mount stable."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.live_h616_recovery_stage import isolate_mounts_for_write


def run(*args):
    subprocess.run(args, check=True, capture_output=True, timeout=15)


def main():
    if os.geteuid() != 0:
        raise ValueError('Root required for disposable mount test')
    with tempfile.TemporaryDirectory() as temporary:
        mountpoint = Path(temporary) / 'recovery'
        mountpoint.mkdir()
        run('mount', '-t', 'tmpfs', '-o', 'size=4m', 'tmpfs', str(mountpoint))
        try:
            (mountpoint / 'identity').write_text('original')
            ready_read, ready_write = os.pipe()
            go_read, go_write = os.pipe()
            pid = os.fork()
            if pid == 0:
                try:
                    os.close(ready_read); os.close(go_write)
                    isolate_mounts_for_write()
                    os.write(ready_write, b'R')
                    if os.read(go_read, 1) != b'G':
                        raise AssertionError('Parent did not replace mount')
                    if (mountpoint / 'identity').read_text() != 'original':
                        raise AssertionError('Private recovery mount changed')
                    os._exit(0)
                except BaseException:
                    os._exit(1)
            os.close(ready_write); os.close(go_read)
            if os.read(ready_read, 1) != b'R':
                raise AssertionError('Child failed to isolate')
            run('umount', str(mountpoint))
            run('mount', '-t', 'tmpfs', '-o', 'size=4m', 'tmpfs', str(mountpoint))
            (mountpoint / 'identity').write_text('replacement')
            os.write(go_write, b'G')
            _, status = os.waitpid(pid, 0)
            if status != 0:
                raise AssertionError('Isolated process observed replacement mount')
            print(json.dumps({'status': 'PASS', 'external_mount_replaced': True,
                              'isolated_mount_remained_original': True,
                              'physical_emmc_tested': False}, sort_keys=True))
        finally:
            run('umount', str(mountpoint))


if __name__ == '__main__':
    main()
