#!/usr/bin/env python3
"""Package pinned Klipper for an isolated Debian ARM64 image; default dry-run.

Integration gap: upstream has no project release package combining our matched
host revision, runtime lock and prebuilt helper. No source patches or installers.
Retire when an upstream/distro package provides this exact release composition.
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
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verified_inputs(c, wheelhouse, helper):
    lock = REPO / c['runtime_lock']
    if sha(lock) != c['runtime_lock_sha256'] or sha(helper) != c['helper_sha256']:
        raise ValueError('Runtime lock or helper does not match the reviewed hash')
    expected = {line.split('--hash=sha256:')[1].strip()
                for line in lock.read_text().splitlines() if line and not line.startswith('#')}
    wheels = sorted(Path(wheelhouse).glob('*.whl'))
    if any(p.is_symlink() or not p.is_file() for p in wheels):
        raise ValueError('Wheel inputs must be regular files')
    if len(wheels) != len(expected) or {sha(p) for p in wheels} != expected:
        raise ValueError('Wheelhouse must contain exactly the locked runtime wheels')
    if c['source_prefix'] != '/opt/sv08-mainline/klipper' or c['venv_prefix'] != '/opt/sv08-mainline/venvs/klipper-f0892d8':
        raise ValueError('Unreviewed installation prefix')
    if c['name'] != 'sv08-klipper' or c['version'] != '0.0+gitf0892d82-1' or c['architecture'] != 'arm64':
        raise ValueError('Unreviewed package identity')
    selected = next(x for x in json.loads((REPO / 'upstream-lock.json').read_text())['submodules']
                    if x['path'] == c['source_path'])
    source = REPO / c['source_path']
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if head != c['source_commit'] or head != selected['commit']:
        raise ValueError('Host revision must match the selected MCU source')
    return lock, wheels, source


def assemble(c, work, lock, wheels, source, helper):
    root = work / 'rootfs'
    if root.is_symlink() or not (work / 'refresh-complete').is_file() or not (root / 'usr/bin/python3.13').is_file():
        raise ValueError('Use an isolated copy of a completed Debian ARM64 baseline')
    prefix = root / c['source_prefix'].lstrip('/')
    venv = root / c['venv_prefix'].lstrip('/')
    pkg = work / 'klipper-package'
    output = work / f"{c['name']}_{c['version']}_arm64.deb"
    if any(p.exists() or p.is_symlink() for p in (prefix, venv, pkg, output)):
        raise ValueError('Use fresh application paths; refusing to overwrite an existing installation')
    epoch = subprocess.check_output(['git', '-C', str(source), 'show', '-s', '--format=%ct', c['source_commit']], text=True).strip()
    epoch = int(epoch)
    archive = work / 'klipper-runtime.tar'
    run('git', '-C', source, 'archive', '--format=tar', '--output=' + str(archive),
        c['source_commit'], 'klippy', 'COPYING')
    prefix.mkdir(parents=True)
    with tarfile.open(archive) as t:
        t.extractall(prefix, filter='data')
    (prefix / 'klippy/.version').write_text(c['source_commit'][:7] + '\n')
    shutil.copyfile(helper, prefix / 'klippy/chelper/c_helper.so')
    venv.parent.mkdir(parents=True, exist_ok=True)
    wheel_temp = root / 'tmp/sv08-runtime-wheels'
    wheel_temp.mkdir()
    for p in wheels:
        shutil.copyfile(p, wheel_temp / p.name)
    shutil.copyfile(lock, wheel_temp / 'requirements.lock')
    run('chroot', root, 'python3', '-m', 'venv', '--copies', c['venv_prefix'])
    python = c['venv_prefix'] + '/bin/python'
    run('chroot', root, python, '-m', 'pip', 'install', '--no-index', '--no-cache-dir',
        '--no-compile', '--require-hashes', '--find-links=/tmp/sv08-runtime-wheels',
        '-r', '/tmp/sv08-runtime-wheels/requirements.lock')
    run('chroot', root, python, '-m', 'pip', 'check')
    shutil.rmtree(wheel_temp)
    for original, relative in [(prefix, c['source_prefix']), (venv, c['venv_prefix'])]:
        shutil.copytree(original, pkg / relative.lstrip('/'), symlinks=True)
    for p in list(pkg.rglob('__pycache__')):
        if p.is_dir():
            shutil.rmtree(p)
    meta = pkg / 'DEBIAN'
    meta.mkdir()
    size = sum(p.stat().st_size for p in pkg.rglob('*') if p.is_file() and not p.is_symlink())
    (meta / 'control').write_text(
        f"Package: {c['name']}\nVersion: {c['version']}\nArchitecture: arm64\n"
        "Maintainer: SV08 Mainline project <noreply@localhost>\n"
        "Section: misc\nPriority: optional\n"
        "Depends: python3 (>= 3.13), python3 (<< 3.14), libc6 (>= 2.39), libffi8\n"
        f"Installed-Size: {(size + 1023)//1024}\n"
        "Description: Pinned SV08 Klipper host runtime (no activation)\n"
        " Includes the matching ARM64 helper and locked Python dependencies.\n"
        " No printer configuration, service activation or MCU firmware writes.\n")
    doc = pkg / 'usr/share/doc/sv08-klipper'
    doc.mkdir(parents=True)
    shutil.copyfile(prefix / 'COPYING', doc / 'copyright')
    (doc / 'release.json').write_text(json.dumps(c, indent=2) + '\n')
    shutil.copyfile(lock, doc / 'requirements.lock')
    # Include documentation in the declared installed payload size.
    size = sum(p.stat().st_size for p in pkg.rglob('*')
               if p.is_file() and not p.is_symlink() and meta not in p.parents)
    control = (meta / 'control').read_text().splitlines()
    (meta / 'control').write_text('\n'.join(
        f'Installed-Size: {(size + 1023)//1024}' if line.startswith('Installed-Size:')
        else line for line in control) + '\n')
    # Equal source/helper mtimes prevent upstream chelper requesting a compiler.
    for p in sorted(pkg.rglob('*'), reverse=True):
        os.utime(p, (epoch, epoch), follow_symlinks=False)
    os.utime(pkg, (epoch, epoch))
    output = work / f"{c['name']}_{c['version']}_arm64.deb"
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
    run('dpkg-deb', '--root-owner-group', '--build', pkg, output, env=env)
    manifest = dict(status='offline-package-no-hardware-activation', source_commit=c['source_commit'],
                    package=output.name, sha256=sha(output), bytes=output.stat().st_size,
                    source_date_epoch=epoch, runtime_lock_sha256=sha(lock), helper_sha256=sha(helper),
                    wheels={p.name: sha(p) for p in wheels}, source_patches=[],
                    activation_included=False, firmware_included=False)
    (work / 'klipper-package.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))
    # These paths were created above in this isolated build, not user installations.
    shutil.rmtree(prefix)
    shutil.rmtree(venv)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--wheelhouse', type=Path, default=REPO / 'artifacts/test-sv08-01-host-python-v1/wheelhouse')
    p.add_argument('--helper', type=Path, default=REPO / 'artifacts/test-sv08-01-mcu-usb-v1/c_helper-aarch64.so')
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    c = json.loads((REPO / 'configs/apps/klipper.json').read_text())
    work = work_path(a.work)
    lock, wheels, source = verified_inputs(c, a.wheelhouse, a.helper)
    print(json.dumps(dict(work=str(work), package=c['name'], execute=a.execute)))
    if a.execute:
        if os.geteuid() != 0:
            p.error('Execution requires root for the isolated ARM64 chroot')
        assemble(c, work, lock, wheels, source, a.helper)


if __name__ == '__main__':
    main()
