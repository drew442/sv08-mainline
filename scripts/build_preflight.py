#!/usr/bin/env python3
"""Read-only prerequisite checks before expensive existing image stages.

Floors are invocation estimates, not proof of final image capacity. Never installs
anything, changes mounts, creates output, or grants hardware/release authority.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import stat


def check(work, *, tools=(), min_bytes=0, min_inodes=0, executable=True, device_nodes=False):
    if type(min_bytes) is not int or type(min_inodes) is not int or min_bytes < 0 or min_inodes < 0:
        raise ValueError('Non-negative integer resource floors required')
    path = Path(work).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Build workspace must not be symlink-backed')
    while not path.exists(): path = path.parent
    if not path.is_dir(): raise ValueError('Workspace ancestor must be a directory')
    missing = sorted({name for name in tools if not shutil.which(name)})
    info = os.statvfs(path)
    free_bytes, free_inodes = info.f_bavail * info.f_frsize, info.f_favail
    errors = []
    if missing: errors.append('missing tools: '+', '.join(missing))
    if free_bytes < min_bytes: errors.append('insufficient free bytes')
    if free_inodes < min_inodes: errors.append('insufficient free inodes')
    if info.f_flag & getattr(os, 'ST_RDONLY', 1): errors.append('read-only workspace')
    if executable and info.f_flag & getattr(os, 'ST_NOEXEC', 8): errors.append('noexec workspace: use an authorised private execution mount')
    if device_nodes and info.f_flag & getattr(os, 'ST_NODEV', 4): errors.append('nodev workspace: use an authorised private staging mount')
    if errors: raise ValueError('Build preflight: '+'; '.join(errors))
    return dict(workspace=str(path), free_bytes=free_bytes, free_inodes=free_inodes,
                required_bytes=min_bytes, required_inodes=min_inodes, tools=sorted(set(tools)),
                scope='prerequisites only; final capacity and qualification unestablished')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--min-bytes', type=int, required=True)
    p.add_argument('--min-inodes', type=int, required=True)
    p.add_argument('--tool', action='append', default=[])
    p.add_argument('--device-nodes', action='store_true')
    a = p.parse_args()
    print(json.dumps(check(a.work,tools=a.tool,min_bytes=a.min_bytes,min_inodes=a.min_inodes,device_nodes=a.device_nodes),indent=2))

if __name__ == '__main__': main()
