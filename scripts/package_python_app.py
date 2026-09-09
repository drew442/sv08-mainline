#!/usr/bin/env python3
"""Assemble reviewed Moonraker/KlipperScreen runtime debs in an isolated rootfs.

Gap: matched image releases need dpkg-owned source and locked virtualenvs without
upstream installers. Retire with an equivalent upstream/distro package. Profiles
carry provenance; no services, device access, firmware or activation is included.
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


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(c, wheelhouse):
    if c['app'] not in ('moonraker', 'klipperscreen'):
        raise ValueError('Unsupported app')
    source = REPO / ('upstream/' + c['app'])
    selected = next(x for x in json.loads((REPO / 'upstream-lock.json').read_text())['submodules'] if x['path'] == 'upstream/' + c['app'])
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if head != c['source_commit'] or selected['commit'] != head:
        raise ValueError('Source pin mismatch')
    for patch in c.get('source_patches', []):
        if sha(REPO / patch['path']) != patch['sha256']:
            raise ValueError('Source patch hash mismatch')
    lock = REPO / c['runtime_lock']
    if sha(lock) != c['runtime_lock_sha256']:
        raise ValueError('Runtime lock mismatch')
    expected = {x.split('--hash=sha256:')[1].strip() for x in lock.read_text().splitlines() if x and not x.startswith('#')}
    wheels = sorted(wheelhouse.glob('*.whl'))
    if any(p.is_symlink() for p in wheels) or len(wheels) != len(expected) or {sha(p) for p in wheels} != expected:
        raise ValueError('Wheelhouse differs from exact lock')
    return source, lock, wheels


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app', choices=('moonraker', 'klipperscreen'), required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--wheelhouse', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    c = json.loads((REPO / f'configs/apps/{a.app}.json').read_text())
    if c['app'] != a.app:
        raise ValueError('App identity mismatch')
    source, lock, wheels = verify(c, a.wheelhouse)
    work = work_path(a.work)
    root = work / 'rootfs'
    prefix = '/opt/sv08-mainline/' + a.app
    venv = '/opt/sv08-mainline/venvs/' + a.app + '-' + c['source_commit'][:7]
    pkg = work / (a.app + '-package')
    scratch = root / ('tmp/' + a.app + '-wheels')
    output = work / f"sv08-{a.app}_{c['package_version']}_arm64.deb"
    created = [root / prefix.lstrip('/'), root / venv.lstrip('/'), pkg, scratch, output]
    if root.is_symlink() or not (work / 'refresh-complete').is_file():
        raise ValueError('Use an isolated completed baseline copy')
    if any(x.exists() or x.is_symlink() for x in created):
        raise ValueError('Refusing existing app/build paths')
    print(json.dumps(dict(app=a.app, work=str(work), execute=a.execute)))
    if not a.execute:
        return
    if os.geteuid() != 0:
        p.error('Execution requires root for ARM64 chroot')
    epoch = int(subprocess.check_output(['git', '-C', str(source), 'show', '-s', '--format=%ct', c['source_commit']], text=True))
    archive = work / (a.app + '-source.tar')
    run('git', '-C', source, 'archive', '--output=' + str(archive), c['source_commit'], *c['source_paths'])
    created[0].mkdir(parents=True)
    with tarfile.open(archive) as t:
        t.extractall(created[0], filter='data')
    for patch in c.get('source_patches', []):
        run('patch', '--batch', '--forward', '--dry-run', '-d', created[0], '-p1', '-i', REPO / patch['path'])
        run('patch', '--batch', '--forward', '-d', created[0], '-p1', '-i', REPO / patch['path'])
    if a.app == 'klipperscreen':
        (created[0] / '.version').write_text(c['source_commit'][:7] + '\n')
    if a.app == 'moonraker':
        (created[0] / 'moonraker/.version').write_text(c['source_commit'][:7] + '\n')
    scratch.mkdir()
    for w in wheels:
        shutil.copyfile(w, scratch / w.name)
    shutil.copyfile(lock, scratch / 'requirements.lock')
    args = ['chroot', root, 'python3', '-m', 'venv']
    if c.get('system_site_packages'):
        args.append('--system-site-packages')
    run(*args, venv)
    run('chroot', root, venv + '/bin/python', '-m', 'pip', 'install', '--no-index', '--no-cache-dir', '--no-compile', '--require-hashes', '--find-links=/tmp/' + a.app + '-wheels', '-r', '/tmp/' + a.app + '-wheels/requirements.lock')
    run('chroot', root, venv + '/bin/python', '-m', 'pip', 'check')
    for src, dst in [(created[0], prefix), (created[1], venv)]:
        shutil.copytree(src, pkg / dst.lstrip('/'), symlinks=True)
    for cache in list(pkg.rglob('__pycache__')):
        shutil.rmtree(cache)
    doc = pkg / ('usr/share/doc/sv08-' + a.app)
    doc.mkdir(parents=True)
    shutil.copyfile(created[0] / c['license_file'], doc / 'copyright')
    shutil.copyfile(lock, doc / 'requirements.lock')
    (doc / 'release.json').write_text(json.dumps(c, indent=2) + '\n')
    size = sum(x.stat().st_size for x in pkg.rglob('*') if x.is_file() and not x.is_symlink())
    meta = pkg / 'DEBIAN'
    meta.mkdir()
    (meta / 'control').write_text(f"Package: sv08-{a.app}\nVersion: {c['package_version']}\nArchitecture: arm64\nMaintainer: SV08 Mainline project <noreply@localhost>\nSection: misc\nPriority: optional\nDepends: {', '.join(c['deb_dependencies'])}\nInstalled-Size: {(size+1023)//1024}\nDescription: Pinned {a.app} runtime (no activation)\n")
    for x in list(pkg.rglob('*')) + [pkg]:
        os.utime(x, (epoch, epoch), follow_symlinks=False)
    run('dpkg-deb', '--root-owner-group', '--build', pkg, output, env=dict(os.environ, SOURCE_DATE_EPOCH=str(epoch)))
    (work / (a.app + '-package.json')).write_text(json.dumps(dict(profile=c, package=output.name, sha256=sha(output), bytes=output.stat().st_size, payload_bytes=size, source_date_epoch=epoch, activation_included=False), indent=2) + '\n')
    for x in (created[0], created[1], scratch):
        shutil.rmtree(x)


if __name__ == '__main__':
    main()
