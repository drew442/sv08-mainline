#!/usr/bin/env python3
"""Build pinned Mainsail static assets into a deb; default dry-run.

Gap: upstream ZIP releases do not provide this image's dpkg-owned source build.
Only recorded build/dependency patches. Retire when upstream supplies an equivalent pinned deb.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
from prepare_host_os import REPO, work_path, run


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_member(root, relative):
    """Require ordinary, contained source members, including all parent paths."""
    parts = PurePosixPath(relative)
    if not parts.parts or parts.is_absolute() or '..' in parts.parts or '\\' in relative:
        raise ValueError('Unsafe authored package path')
    current = Path(root)
    for part in parts.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink in authored package path')
    return current


def authored_archive_bytes(source, spec):
    """Build an independently authored npm archive with fixed tar/gzip metadata.

    Both packaging and notice accounting use the same source-bound bytes. No npm
    lifecycle, supplier archive rewriting, or wall-clock metadata is involved.
    """
    directory = source_member(source, spec['source_directory'])
    files = spec['files']
    if set(files) != {'LICENSE', 'README.md', 'index.js', 'package.json'}:
        raise ValueError('Unexpected authored package source members')
    if {p.name for p in directory.iterdir()} != set(files):
        raise ValueError('Unexpected authored package directory contents')
    contents = {}
    for name, expected in sorted(files.items()):
        member = source_member(directory, name)
        if not member.is_file() or member.stat().st_size > 1024 * 1024 or digest(member) != expected:
            raise ValueError('Authored package source hash mismatch')
        contents[name] = member.read_bytes()
    metadata = json.loads(contents['package.json'])
    if (metadata.get('name'), metadata.get('version'), metadata.get('license'), metadata.get('main')) != (
            spec['name'], spec['version'], 'AGPL-3.0-or-later', 'index.js'):
        raise ValueError('Authored package identity mismatch')
    if contents['LICENSE'] != (REPO / 'LICENSE').read_bytes():
        raise ValueError('Authored package requires the complete project notice')
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode='wb', filename='', mtime=0, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as tar:
            for name, raw in sorted(contents.items()):
                member = tarfile.TarInfo('package/' + name)
                member.size = len(raw)
                member.mode = 0o644
                member.uid = member.gid = member.mtime = 0
                member.uname = member.gname = ''
                tar.addfile(member, io.BytesIO(raw))
    return output.getvalue()


def prepare_authored_archives(source, config):
    for spec in config.get('authored_npm_replacements', {}).values():
        raw = authored_archive_bytes(source, spec)
        if hashlib.sha256(raw).hexdigest() != spec['archive_sha256']:
            raise ValueError('Authored package archive hash mismatch')
        target = source_member(source, spec['archive_path'])
        if target.exists():
            raise ValueError('Authored package archive already exists')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


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
    if digest(src / 'package-lock.json') != c.get('patched_package_lock_sha256', c['package_lock_sha256']):
        raise ValueError('Patched dependency lock hash mismatch')
    prepare_authored_archives(src, c)
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
