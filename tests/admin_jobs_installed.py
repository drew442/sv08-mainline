#!/usr/bin/env python3
"""Fixed ARM64 installed-entry diagnostics in a disposable private overlay.

Run with sudo unshare --mount --propagation private. No service is started and
no source root is written. Supply the already selected ARM64 baseline rootfs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prepare_host_os import REPO, work_path


def check(lower, work):
    if os.geteuid() != 0 or os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
        raise ValueError('Use root in a private mount namespace')
    if not (lower / 'usr/bin/python3').is_file(): raise ValueError('Selected baseline Python is missing')
    if work.exists(): raise ValueError('Use a fresh disposable directory')
    work.mkdir(parents=True)
    for name in ('upper', 'overlay-work', 'rootfs'): (work / name).mkdir()
    merged = work / 'rootfs'; results = []
    subprocess.run(['mount', '-t', 'overlay', 'overlay', '-o',
                    f'lowerdir={lower},upperdir={work / "upper"},workdir={work / "overlay-work"}', str(merged)], check=True)
    try:
        runtime = merged / 'usr/lib/sv08'; runtime.mkdir(parents=True, exist_ok=True)
        for path in (REPO / 'runtime').glob('*.py'): shutil.copyfile(path, runtime / path.name)
        unit = REPO / 'configs/host-os/sv08-admin-image-worker@.service'
        shutil.copyfile(unit, merged / 'usr/lib/systemd/system' / unit.name)
        def call(case, expected, identity='0'*32):
            result = subprocess.run(['chroot', str(merged), '/usr/bin/python3', '-B',
                                     '/usr/lib/sv08/sv08_admin_jobs.py', identity],
                                    capture_output=True, text=True, timeout=20)
            if result.returncode != 1 or expected not in result.stderr:
                raise AssertionError((case, result.returncode, result.stdout, result.stderr))
            results.append(dict(case=case, returncode=result.returncode, diagnostic=result.stderr.strip()))
        call('missing-context', '/usr/lib/sv08/admin-context.json')
        (runtime / 'admin-context.json').write_text('{broken')
        call('malformed-context', 'Expecting property name')
        (runtime / 'admin-context.json').write_text('{"format_version":1,"context":"recovery"}')
        call('recovery-context', 'context is not supported')
        (runtime / 'admin-context.json').write_text('{"format_version":1,"context":"host"}')
        call('missing-boot', '/run/sv08/boot.json')
        call('invalid-receipt', 'validated receipt identity', '../bad')
        if (merged / 'data/sv08/admin-image-jobs').exists(): raise AssertionError('Diagnostics initialized job data')
        result = dict(scope='selected ARM64 chroot; private overlay; no service or hardware', cases=results,
                      runtime_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in runtime.glob('*.py')},
                      unit_sha256=hashlib.sha256(unit.read_bytes()).hexdigest())
        (work / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
    finally: subprocess.run(['umount', str(merged)], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lower', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    check(args.lower.resolve(), work_path(args.work))
