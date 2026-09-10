#!/usr/bin/env python3
"""Build the pinned RAUC replacement in a disposable Debian ARM64 compiler root.

Gap: tested distro RAUC predates the newer dm-verity status format. Use unmodified
upstream Meson/Ninja and dpkg, no upstream installer on the printer. Retire when
the selected Debian package provides and passes the required behavior. This only
creates a package; it does not install/activate it. Default inspection.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from prepare_host_os import REPO, work_path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(config, archive):
    sources = json.loads((REPO / 'configs/host-os/offline-tool-sources.json').read_text())['sources']
    if config['source'] not in sources or config['architecture'] != 'arm64' or config['name'] != 'rauc':
        raise ValueError('Unreviewed package/source identity')
    if archive.is_symlink() or not archive.is_file() or digest(archive) != config['source']['archive_sha256']:
        raise ValueError('Source archive differs from the recorded hash')


def build(config, archive, builder, work):
    root = builder / 'rootfs'
    if root.is_symlink() or not (root / 'usr/bin/gcc').exists():
        raise ValueError('Use the isolated compiler root with documented build dependencies')
    arch = subprocess.check_output(['chroot', str(root), 'dpkg', '--print-architecture'], text=True).strip()
    if arch != 'arm64':
        raise ValueError('Compiler root must be ARM64')
    inside = '/tmp/sv08-rauc-' + work.name
    base = root / inside.lstrip('/')
    if work.exists() or base.exists() or base.is_symlink():
        raise ValueError('Use new build/output paths')
    work.mkdir()
    source = base / 'source'
    source.mkdir(parents=True)
    with tarfile.open(archive) as tar:
        prefix = tar.getmembers()[0].name.split('/')[0] + '/'
        for member in tar.getmembers():
            if not member.name.startswith(prefix):
                continue
            member.name = member.name[len(prefix):]
            if member.name:
                tar.extract(member, source, filter='data')
    (source / '.tarball-version').write_text(config['source']['tag'].removeprefix('v')+'\n')
    env = ['env', 'SOURCE_DATE_EPOCH='+str(config['source_date_epoch']),
           'GIT_CEILING_DIRECTORIES='+inside]
    def run(*args, output=False):
        command = ['chroot', str(root), *env, *map(str, args)]
        if output:
            return subprocess.check_output(command, text=True)
        with (work / 'build.log').open('a') as log:
            subprocess.run(command, stdout=log, stderr=log, check=True)
    run('meson', 'setup', inside+'/build', inside+'/source', '--prefix=/usr',
        '--libdir=lib/aarch64-linux-gnu', '--buildtype=release', '-Dtests=false',
        '-Dnetwork=true', '-Dstreaming=true', '-Dsystemdunitdir=/usr/lib/systemd/system',
        '-Dsystemdcatalogdir=/usr/lib/systemd/catalog',
        '-Dc_args=-ffile-prefix-map='+inside+'=/usr/src/rauc')
    run('ninja', '-C', inside+'/build', '-j', '2')
    version = run(inside+'/build/rauc', '--version', output=True).strip()
    if version != 'rauc '+config['source']['tag'].removeprefix('v'):
        raise ValueError('Built version differs from pinned source: '+version)
    run('env', 'DESTDIR='+inside+'/package', 'ninja', '-C', inside+'/build', 'install')
    package = base / 'package'
    docs = package / 'usr/share/doc/rauc'
    docs.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / 'COPYING', docs / 'copyright')
    shutil.copytree(source / 'LICENSES', docs / 'LICENSES')
    (docs / 'sv08-source.json').write_text(json.dumps(config, indent=2)+'\n')
    # dpkg-shlibdeps needs a source control file in its current working directory.
    debian = base / 'debian'
    debian.mkdir()
    (debian / 'control').write_text('Source: rauc\nSection: admin\nPriority: optional\nMaintainer: SV08 Mainline contributors\n\nPackage: rauc\nArchitecture: arm64\nDescription: RAUC candidate for SV08 image integration\n')
    with (work / 'build.log').open('a') as log:
        dependencies = subprocess.check_output(['chroot', str(root), *env, 'sh', '-c',
            'cd "$1" && exec dpkg-shlibdeps -O package/usr/bin/rauc', 'sh', inside], text=True, stderr=log).strip()
    if not dependencies.startswith('shlibs:Depends='):
        raise ValueError('Could not derive binary dependencies')
    dependencies = dependencies.split('=', 1)[1] + ', dbus, squashfs-tools, util-linux, u-boot-tools, libubootenv-tool, e2fsprogs, dosfstools'
    meta = package / 'DEBIAN'
    meta.mkdir()
    size = sum(p.stat().st_size for p in package.rglob('*') if p.is_file() and not p.is_symlink())
    (meta / 'control').write_text(f"Package: rauc\nVersion: {config['version']}\nArchitecture: arm64\nMaintainer: SV08 Mainline contributors\nSection: admin\nPriority: optional\nInstalled-Size: {(size+1023)//1024}\nDepends: {dependencies}\nDescription: Pinned RAUC candidate for SV08 transactional host updates\n Unmodified upstream build; activation and hardware validation are separate.\n")
    for path in sorted(package.rglob('*'), reverse=True):
        os.utime(path, (config['source_date_epoch'],)*2, follow_symlinks=False)
    os.utime(package, (config['source_date_epoch'],)*2)
    filename = f"rauc_{config['version']}_arm64.deb"
    run('dpkg-deb', '--root-owner-group', '--build', inside+'/package', inside+'/'+filename)
    shutil.copyfile(base / filename, work / filename)
    report = dict(package=filename, sha256=digest(work / filename), version=version,
                  binary_sha256=digest(package / 'usr/bin/rauc'), config=config,
                  installed=False, hardware_validated=False,
                  toolchain=run('dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\n', output=True).splitlines())
    (work / 'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('package','sha256','version','installed','hardware_validated')}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--builder', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    config = json.loads((REPO / 'configs/host-os/rauc-package.json').read_text())
    verify(config, args.archive)
    builder, work = work_path(args.builder), work_path(args.work)
    print(json.dumps(dict(execute=args.execute, source=config['source']['commit'], work=str(work))))
    if args.execute:
        if os.geteuid() != 0:
            parser.error('Compiler chroot execution requires root')
        build(config, args.archive.resolve(), builder, work)


if __name__ == '__main__':
    main()
