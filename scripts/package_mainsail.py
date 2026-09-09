#!/usr/bin/env python3
"""Build pinned Mainsail static assets into a deb; default dry-run.

Gap: upstream ZIP releases do not provide this image's dpkg-owned source build.
Only recorded build-configuration patches. Retire when upstream supplies an equivalent pinned deb.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from prepare_host_os import REPO, work_path, run


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--node-archive', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    a = parser.parse_args()
    c = json.loads((REPO / 'configs/apps/mainsail.json').read_text())
    source = REPO / c['source_path']
    work = work_path(a.work)
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    selected = next(x for x in json.loads((REPO / 'upstream-lock.json').read_text())['submodules'] if x['path'] == c['source_path'])
    if head != c['source_commit'] or selected['commit'] != head:
        raise ValueError('Source pin mismatch')
    if digest(source / 'package-lock.json') != c['package_lock_sha256'] or digest(a.node_archive) != c['node_sha256']:
        raise ValueError('Build input hash mismatch')
    for patch in c.get('source_patches', []):
        if digest(REPO / patch['path']) != patch['sha256']:
            raise ValueError('Source patch hash mismatch')
    if work.exists():
        raise ValueError('Use a fresh work directory')
    print(json.dumps(dict(work=str(work), execute=a.execute, profile=c)))
    if not a.execute:
        return
    work.mkdir(parents=True)
    with tarfile.open(a.node_archive) as t:
        t.extractall(work, filter='data')
    src = work / 'source'
    src.mkdir()
    archive = work / 'source.tar'
    run('git', '-C', source, 'archive', '--output=' + str(archive), head)
    with tarfile.open(archive) as t:
        t.extractall(src, filter='data')
    for patch in c.get('source_patches', []):
        run('patch', '--batch', '--forward', '--dry-run', '-d', src, '-p1', '-i', REPO / patch['path'])
        run('patch', '--batch', '--forward', '-d', src, '-p1', '-i', REPO / patch['path'])
    epoch = int(subprocess.check_output(['git', '-C', str(source), 'show', '-s', '--format=%ct', head], text=True))
    env = dict(os.environ, PATH=str(work / ('node-v' + c['node_version'] + '-linux-x64/bin')) + ':' + os.environ['PATH'], SOURCE_DATE_EPOCH=str(epoch))
    run('npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund', cwd=src, env=env)
    # The upstream build script adds an optional zip; the deb consumes dist directly.
    run('npm', 'exec', '--', 'vite', 'build', cwd=src, env=env)
    if not (src / 'dist/index.html').is_file() or not (src / 'dist/sw.js').is_file():
        raise ValueError('Incomplete web payload')
    pkg = work / 'package'
    shutil.copytree(src / 'dist', pkg / 'usr/share/sv08-mainline/mainsail')
    doc = pkg / 'usr/share/doc/sv08-mainsail'
    doc.mkdir(parents=True)
    shutil.copyfile(src / 'LICENSE', doc / 'copyright')
    (doc / 'release.json').write_text(json.dumps(c, indent=2) + '\n')
    meta = pkg / 'DEBIAN'
    meta.mkdir()
    size = sum(p.stat().st_size for p in pkg.rglob('*') if p.is_file())
    (meta / 'control').write_text(f"Package: sv08-mainsail\nVersion: {c['package_version']}\nArchitecture: all\nMaintainer: SV08 Mainline project <noreply@localhost>\nSection: web\nPriority: optional\nInstalled-Size: {(size+1023)//1024}\nDescription: Pinned Mainsail web assets (no activation)\n")
    for p in list(pkg.rglob('*')) + [pkg]:
        os.utime(p, (epoch, epoch), follow_symlinks=False)
    output = work / f"sv08-mainsail_{c['package_version']}_all.deb"
    run('dpkg-deb', '--root-owner-group', '--build', pkg, output, env=env)
    report = dict(profile=c, package=output.name, sha256=digest(output), bytes=output.stat().st_size,
                  payload_bytes=size, source_date_epoch=epoch, source_patches=c.get('source_patches', []), activation_included=False)
    (work / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
