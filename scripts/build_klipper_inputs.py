#!/usr/bin/env python3
"""Inspect or build the pinned Klipper helper and native MarkupSafe wheel offline.

Execution is intended for coordinator-assigned disposable workspaces only. The
wheel compiler root must be supplied explicitly; this script never prepares roots,
downloads dependencies, or changes upstream source. Retain failed work for diagnosis.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile

REPO = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def output(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def regular(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Input must be a regular non-symlink file: ' + str(path))
    return path


def fresh(path):
    path = Path(path).absolute()
    if path.exists() or path.is_symlink() or path.parent.resolve() != path.parent:
        raise ValueError('Use a fresh path with no symlink ancestors')
    return path


def validate_source(c, kind, source):
    source = Path(source)
    if kind == 'markupsafe':
        if sha(regular(source)) != c[kind]['source_sha256']:
            raise ValueError('MarkupSafe source hash mismatch')
    else:
        pin = next(x for x in json.loads((REPO / 'upstream-lock.json').read_text())['submodules']
                   if x['path'] == 'upstream/klipper')['commit']
        if pin != c[kind]['source_commit'] or output('git', '-C', source, 'rev-parse', 'HEAD') != pin:
            raise ValueError('Klipper helper must match the upstream host/MCU pin')
        if output('git', '-C', source, 'status', '--porcelain', '--untracked-files=no'):
            raise ValueError('Klipper source has tracked modifications')


def helper_command(c, work):
    recipe = c['helper']
    source = work / 'source'
    flags = recipe['flags'] + ['-ffile-prefix-map=' + str(work) + '=/usr/src/sv08-klipper-build',
                               '-fdebug-prefix-map=' + str(work) + '=/usr/src/sv08-klipper-build']
    return [recipe['compiler'], *flags, '-o', str(work / 'c_helper-aarch64.so'),
            *[str(source / 'klippy/chelper' / name) for name in recipe['sources']]]


def build_helper(c, source, work):
    recipe = c['helper']
    for package, version in recipe['packages'].items():
        if output('dpkg-query', '-W', '-f=${Version}', package) != version:
            raise ValueError('Unreviewed helper toolchain package: ' + package)
    if output(recipe['compiler'], '-dumpfullversion') != recipe['compiler_version']:
        raise ValueError('Unreviewed helper compiler')
    work.mkdir()
    archive = work / 'source.tar'
    subprocess.run(['git', '-C', str(source), 'archive', '--format=tar',
                    '--output=' + str(archive), recipe['source_commit'], 'klippy/chelper'], check=True)
    with tarfile.open(archive) as tar:
        tar.extractall(work / 'source', filter='data')
    command = helper_command(c, work)
    subprocess.run(command, check=True, env=build_env(recipe), cwd=work / 'source')
    return {'command': command, 'sha256': sha(work / 'c_helper-aarch64.so'),
            'historical_sha256': recipe['historical_sha256']}


def build_env(recipe):
    # Avoid inherited CFLAGS/LDFLAGS, locale, hash seed or user compiler overrides.
    return {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'TZ': 'UTC',
            'SOURCE_DATE_EPOCH': str(recipe['source_date_epoch']), 'PYTHONHASHSEED': '0'}


def wheel_plan(c, root, work, venv):
    root = Path(root).absolute()
    if root.is_symlink() or root.resolve() != root or not root.is_dir():
        raise ValueError('Use the explicitly assigned compiler root without symlink ancestors')
    if not re.fullmatch(r'/tmp/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*', venv):
        raise ValueError('Use an explicit compiler venv under /tmp')
    if not work.is_relative_to(root / 'tmp') or work == root / 'tmp':
        raise ValueError('Wheel work must be a fresh directory under compiler-root/tmp')
    prefix = '/' + str(work.relative_to(root))
    recipe = c['markupsafe']
    flags = recipe['python_cflags'] + ' ' + ' '.join(
        flag.format(work=prefix, venv=venv) for flag in recipe['additional_cflags'])
    env = build_env(recipe)
    env.update(PATH=venv + '/bin:/usr/bin:/bin', CFLAGS=flags,
               PIP_CONFIG_FILE='/dev/null', PIP_NO_INDEX='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
    command = ['chroot', str(root), '/usr/bin/env', '-i',
               *[key + '=' + value for key, value in sorted(env.items())],
               venv + '/bin/python', '-m', 'pip', 'wheel', '--no-index', '--no-cache-dir',
               '--no-build-isolation', '--no-deps', '--wheel-dir', prefix + '/wheels',
               prefix + '/markupsafe']
    return command


def verify_backends(c, root, venv, wheelhouse):
    site = Path(root) / venv.lstrip('/') / 'lib/python3.13/site-packages'
    for name, pin in c['markupsafe']['backends'].items():
        wheel = regular(Path(wheelhouse) / pin['filename'])
        if sha(wheel) != pin['sha256']:
            raise ValueError('Backend wheel hash mismatch: ' + name)
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.namelist():
                if member.endswith('/') or member.endswith('/RECORD'):
                    continue
                target = site / member
                if Path(member).is_absolute() or '..' in Path(member).parts or not target.resolve().is_relative_to(site.resolve()):
                    raise ValueError('Invalid backend wheel path')
                if not target.is_file() or target.read_bytes() != archive.read(member):
                    raise ValueError('Installed backend differs from pinned wheel: ' + member)


def build_wheel(c, source, root, work, venv, wheelhouse):
    recipe = c['markupsafe']
    command = wheel_plan(c, root, work, venv)
    query = ('import json,sys,sysconfig,platform,importlib.metadata as m;'
             'print(json.dumps(dict(python=list(sys.version_info[:3]),machine=platform.machine(),'
             'cflags=sysconfig.get_config_var("CFLAGS"),'
             'backends={n:m.version(n) for n in ' + repr(list(recipe['backends'])) + '})))')
    actual = json.loads(output('chroot', root, venv + '/bin/python', '-c', query))
    expected = dict(python=recipe['python'], machine='aarch64', cflags=recipe['python_cflags'],
                    backends={name: pin['version'] for name, pin in recipe['backends'].items()})
    if actual != expected:
        raise ValueError('Unreviewed Python, architecture, backend or Python compiler flags')
    verify_backends(c, root, venv, wheelhouse)
    for package, version in recipe['packages'].items():
        if output('chroot', root, 'dpkg-query', '-W', '-f=${Version}', package) != version:
            raise ValueError('Unreviewed native compiler package: ' + package)
    work.mkdir()
    with tarfile.open(source) as tar:
        members = tar.getmembers()
        if any(not Path(m.name).is_relative_to(recipe['source_directory']) for m in members):
            raise ValueError('Source archive has unexpected top-level paths')
        tar.extractall(work, filter='data')
    (work / recipe['source_directory']).rename(work / 'markupsafe')
    subprocess.run(command, check=True)
    wheels = list((work / 'wheels').glob('*.whl'))
    if len(wheels) != 1 or wheels[0].name != recipe['filename']:
        raise ValueError('Expected one native ARM64 MarkupSafe wheel')
    return {'command': command, 'filename': wheels[0].name, 'sha256': sha(wheels[0]),
            'historical_sha256': recipe['historical_sha256'], 'environment': actual}


def save_report(c, kind, work, report):
    selected = c[kind]['selected_sha256']
    report.update(selected_sha256=selected, matches_selected_build=report['sha256'] == selected)
    (work / 'report.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    if not report['matches_selected_build']:
        raise ValueError('Build differs from selected artifact; retain output and report for diagnosis')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=['helper', 'markupsafe'], required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--compiler-root', type=Path)
    parser.add_argument('--build-venv')
    parser.add_argument('--backend-wheelhouse', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    config = REPO / 'configs/host/klipper-build-inputs.json'
    c = json.loads(config.read_text())
    validate_source(c, args.kind, args.source)
    work = fresh(args.work)
    if args.kind == 'markupsafe':
        if not args.compiler_root or not args.build_venv or not args.backend_wheelhouse:
            parser.error('MarkupSafe needs --compiler-root, --build-venv and --backend-wheelhouse')
        command = wheel_plan(c, args.compiler_root, work, args.build_venv)
    else:
        command = helper_command(c, work)
    report = dict(kind=args.kind, execute=args.execute, recipe_sha256=sha(config), command=command)
    if args.execute:
        if args.kind == 'helper':
            report.update(build_helper(c, args.source, work))
        else:
            report.update(build_wheel(c, args.source, args.compiler_root, work, args.build_venv,
                                      args.backend_wheelhouse))
        save_report(c, args.kind, work, report)
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
