#!/usr/bin/env python3
"""Populate and fsck a regular-file ext4 slot for offline capacity validation.

Gap: apparent-byte budgets do not account for ext4 metadata. Uses e2fsprogs,
not a custom filesystem implementation. Retire into the final image assembler.
This capacity fixture retains an unfinalized rootfs; it is not a boot image.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from prepare_host_os import REPO, work_path, run


def check_source(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Source must be a real rootfs directory')
    root = root.resolve()
    # mountinfo escapes whitespace with octal sequences.
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        mount = line.split()[4]
        for octal, char in [('040', ' '), ('011', '\t'), ('012', '\n'), ('134', '\\')]:
            mount = mount.replace('\\' + octal, char)
        path = Path(mount)
        if path == root or root in path.parents:
            raise ValueError('Unmount nested filesystems before measuring the rootfs')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    work = work_path(a.work)
    output = work_path(a.output)
    root = work / 'rootfs'
    check_source(root)
    if output.exists() or output.is_symlink() or root in output.parents:
        raise ValueError('Use a new output outside the source rootfs')
    profile = json.loads((REPO / 'configs/images/host-ab.json').read_text())
    mib = next(x['mib'] for x in profile['partitions'] if x['name'] == 'root-a')
    print(json.dumps(dict(source=str(root), output=str(output), slot_mib=mib, execute=a.execute)))
    if not a.execute:
        return
    if os.geteuid() != 0:
        p.error('Run as root to preserve rootfs ownership and device nodes')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as f:
        f.truncate(mib * 1024 * 1024)
    run('mkfs.ext4', '-q', '-F', '-L', 'SV08_CAPACITY', '-m', '1',
        '-E', 'lazy_itable_init=0,lazy_journal_init=0', '-d', root, output)
    run('e2fsck', '-f', '-n', output)
    details = subprocess.check_output(['dumpe2fs', '-h', str(output)], text=True, stderr=subprocess.DEVNULL)
    values = dict(line.split(':', 1) for line in details.splitlines() if ':' in line)
    block_size = int(values['Block size'])
    h = hashlib.sha256()
    with output.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    report = dict(status='capacity-fixture-not-bootable', image_bytes=output.stat().st_size,
                  sha256=h.hexdigest(), filesystem_uuid=values['Filesystem UUID'].strip(),
                  block_size=block_size, free_bytes=int(values['Free blocks']) * block_size,
                  reserved_bytes=int(values['Reserved block count']) * block_size,
                  fsck_pass=True, hardware_access=False)
    output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
