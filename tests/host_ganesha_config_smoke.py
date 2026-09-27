#!/usr/bin/env python3
"""Start the generated NFS config only inside a disposable private namespace.

Run as root after `unshare -n -m --`. No printer connection or image transfer.
The extracted package root is an offline test fixture, not a production path.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.serve_h616_reimage_job import ganesha_config  # noqa: E402


def run(work: Path, packages: Path) -> dict:
    if os.geteuid() != 0 or any(
            os.readlink(f'/proc/self/ns/{name}') == os.readlink(f'/proc/1/ns/{name}')
            for name in ('net', 'mnt')):
        raise ValueError('Root in separate network and mount namespaces required')
    work = Path(os.path.abspath(work))
    packages = Path(os.path.abspath(packages))
    if work.exists() or work.is_symlink() or not packages.is_dir():
        raise ValueError('Fresh work directory and extracted package root required')
    work.mkdir(mode=0o700)
    export = work / 'export'
    export.mkdir(mode=0o755)
    (export / 'image.bin').write_bytes(b'synthetic-only\n')
    (work / 'recovery').mkdir()
    (work / 'idmap.conf').write_text('[General]\nDomain = localdomain\n')
    prefix = packages / 'usr/lib/x86_64-linux-gnu'
    config = ganesha_config(export_dir=export, pseudo='/srv/sv08-sd-nfs',
                            bind='192.0.2.10', printer_ip='192.0.2.11',
                            recovery_dir=work / 'recovery')
    config = config.replace('NFS_CORE_PARAM {',
                            f'NFS_CORE_PARAM {{ Plugins_Dir = "{prefix / "ganesha"}";')
    (work / 'ganesha.conf').write_text(config)
    env = dict(os.environ, LD_LIBRARY_PATH=':'.join((str(packages / 'usr/lib/ganesha'),
                                                      str(prefix), str(prefix / 'ganesha'))))
    subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', '/run'], check=True)
    Path('/run/ganesha').mkdir()
    subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True)
    subprocess.run(['ip', 'addr', 'add', '192.0.2.10/32', 'dev', 'lo'], check=True)
    children = []
    try:
        children.append(subprocess.Popen([str(packages / 'sbin/rpcbind'), '-f', '-s'], env=env))
        children.append(subprocess.Popen([str(packages / 'usr/bin/ganesha.nfsd'), '-F',
                                          '-f', str(work / 'ganesha.conf'),
                                          '-L', str(work / 'ganesha.log'),
                                          '-p', '/run/ganesha.pid'], env=env))
        for _ in range(100):
            if any(child.poll() is not None for child in children):
                raise RuntimeError('NFS service exited before readiness')
            try:
                with socket.create_connection(('192.0.2.10', 2049), timeout=.2):
                    report = {'status': 'ganesha-config-startup-pass',
                              'config_sha256': hashlib.sha256(config.encode()).hexdigest(),
                              'network_namespace': 'private', 'mount_namespace': 'private',
                              'source_bytes': len(b'synthetic-only\n')}
                    (work / 'result.json').write_text(json.dumps(report, sort_keys=True) + '\n')
                    return report
            except OSError:
                time.sleep(.1)
        raise TimeoutError('NFS service did not listen')
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--package-root', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.work, args.package_root), sort_keys=True))
