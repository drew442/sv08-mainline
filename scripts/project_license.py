#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Exact project notices and offline build provenance; never image qualification."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess

REPO = Path(__file__).resolve().parents[1]
DOC = 'usr/share/doc/sv08-mainline/'
PACKAGES = ('usr/share/cockpit/sv08-host/', 'usr/share/cockpit/sv08-printer/')
PREFIXES = ('usr/lib/sv08/', 'usr/share/sv08/printer/', *PACKAGES)
SOURCE_DIRS = ('runtime', 'ui', 'scripts', 'configs', 'catalog', 'patches', 'extensions',
               'profiles', 'schemas', 'examples', 'tests', 'docs/development')
SOURCE_ROOTS = ('LICENSE', 'LICENSING.md', 'upstream-lock.json', '.gitmodules')
EXTRA_FILES = ('etc/cockpit/cockpit.conf','etc/sudoers.d/sv08-view',
    'etc/dbus-1/system.d/zz-sv08-rauc.conf','etc/systemd/system/rauc.service.d/sv08.conf',
    'etc/systemd/system/cockpit.socket.d/sv08-identity.conf',
    'usr/lib/systemd/system/sv08-admin-image-worker@.service',
    'usr/lib/systemd/system/sv08-software-worker@.service',
    'usr/lib/systemd/system/sv08-feed.service','usr/lib/systemd/system/sv08-feed.timer',
    'usr/lib/systemd/system/sv08-recovery-display.service',
    'usr/share/xsessions/sv08-recovery.desktop')
GENERATED = ('project-source.json', 'project-LICENSE.txt', 'project-NOTICE.txt')
NOTICE_PATHS = {base+name for base in (DOC,*PACKAGES) for name in GENERATED}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def checked(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Unsafe project provenance path')
    path = Path(root) / relative
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink(): raise ValueError('Symlink in project provenance path: ' + name)
        if ancestor == Path(root): break
    if path.exists() and not path.is_file(): raise ValueError('Expected regular project file: ' + name)
    return path


def source_state(repo):
    """Read-only Git identity; unavailable identity is explicitly development-only."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    try:
        revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                                           env=env, stderr=subprocess.DEVNULL, timeout=10).decode().strip()
        dirty = bool(subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain',
                    '--untracked-files=normal'], env=env, stderr=subprocess.DEVNULL, timeout=10))
        return revision, dirty
    except (OSError, subprocess.SubprocessError):
        return None, True


def source_files(repo):
    names = set(SOURCE_ROOTS)
    for directory in SOURCE_DIRS:
        base = repo / directory
        if base.is_symlink(): raise ValueError('Symlink in project source')
        for path in base.rglob('*'):
            if '__pycache__' in path.parts or path.suffix == '.pyc': continue
            if path.is_symlink(): raise ValueError('Symlink in project source: ' + str(path.relative_to(repo)))
            if path.is_file(): names.add(path.relative_to(repo).as_posix())
    result = {}
    for name in sorted(names):
        path = checked(repo, name)
        if not path.is_file(): raise ValueError('Missing project source: ' + name)
        result[name] = digest(path.read_bytes())
    return result


def installed_files(root, overrides=None, replaced=()):
    result = {}
    for prefix in PREFIXES:
        base = root / prefix
        if base.is_symlink(): raise ValueError('Symlink in project staging directory')
        for path in base.rglob('*'):
            name = path.relative_to(root).as_posix()
            if any(name.startswith(p) for p in replaced): continue
            if name in NOTICE_PATHS or name == 'usr/lib/sv08/release.json': continue
            if path.is_symlink(): raise ValueError('Symlink in staged project files')
            if path.is_file(): result[name] = checked(root, name).read_bytes()
    for name in EXTRA_FILES:
        path = checked(root, name)
        if path.is_file(): result[name] = path.read_bytes()
    branding = root/'usr/share/cockpit/branding/debian'
    if branding.is_symlink(): raise ValueError('Symlink in project branding')
    for path in branding.glob('*'):
        if path.is_file():
            name = path.relative_to(root).as_posix(); result[name] = checked(root,name).read_bytes()
    result.update(overrides or {})
    return {n: raw for n, raw in result.items() if n not in NOTICE_PATHS}


def generated_recipe(root, name, raw, repo):
    """Recognize only exact supported outputs; unknown bytes never become source-bound."""
    recipes = ['scripts/project_license.py', 'scripts/stage_admin_ui.py', 'scripts/stage_printer_ui.py']
    if name == 'usr/share/cockpit/sv08-host/index.html':
        from stage_printer_ui import compose_host, NAV
        original = (repo/'ui/host/index.html').read_bytes()
        if raw == original.replace(NAV,b''):
            return 'generated', recipes + ['ui/host/index.html']
        panel = repo/'ui/printer/panel.html'
        if panel.is_file() and raw == compose_host(original,panel.read_bytes()):
            return 'generated', recipes + ['ui/host/index.html','ui/printer/panel.html']
    elif name == 'usr/lib/sv08/admin-context.json':
        try: context = json.loads(raw)
        except (ValueError,UnicodeError): return None
        if context in ({'format_version':1,'context':'host'}, {'format_version':1,'context':'recovery'}):
            return 'generated', recipes
    elif name == 'usr/lib/sv08/rauc-service-policy.json':
        from stage_admin_ui import package_service_policy
        try:
            if json.loads(raw) == package_service_policy(root):
                return 'generated', recipes + ['configs/host-os/rauc-service-policy.json','configs/host-os/rauc-package.json']
        except (ValueError,OSError,UnicodeError): return None
    elif name == 'etc/cockpit/cockpit.conf' and raw == b'[WebService]\nShell=/sv08-host/index.html\n':
        return 'generated', recipes
    elif name == 'etc/systemd/system/cockpit.socket.d/sv08-identity.conf' and raw == b'[Unit]\nRequires=sv08-identity.service\nAfter=sv08-identity.service\n':
        return 'generated', recipes
    elif name.startswith('usr/share/cockpit/sv08-printer/'):
        from definition_repository_template import archive, FILENAME, schema_archive, SCHEMA_FILENAME
        filename = Path(name).name
        if filename == FILENAME and raw == archive(repo):
            return 'generated', recipes + ['scripts/definition_repository_template.py']
        if filename == SCHEMA_FILENAME and raw == schema_archive(repo):
            return 'generated', recipes + ['scripts/definition_repository_template.py']
    elif name == 'usr/share/sv08/printer/validation/klipper.dict' and digest(raw) == '86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b':
        return 'upstream-pinned-artifact', ['scripts/stage_printer_ui.py','upstream-lock.json']
    return None


def prepare(root, overrides=None, replaced=(), public_source=None, repo=None):
    """Prepare all bytes before publication. A failed public check cannot write root."""
    repo = Path(repo or REPO); root = Path(root)
    sources = source_files(repo)
    revision, dirty = source_state(repo)
    reverse = {}
    for name, sha in sources.items(): reverse.setdefault(sha, []).append(name)
    files = installed_files(root, overrides, replaced)
    staged = {}; unmatched = []
    for name, raw in sorted(files.items()):
        checked(root, name)
        sha = digest(raw)
        matches = reverse.get(sha, [])
        recipe = generated_recipe(root, name, raw, repo) if not matches else None
        if not matches and recipe is None: unmatched.append(name)
        staged[name] = dict(sha256=sha, sources=matches or (recipe[1] if recipe else []),
                            origin='copied' if matches else recipe[0] if recipe else 'unmatched')
    release = checked(root, 'usr/lib/sv08/release.json')
    release_record = None
    if release.is_file():
        raw = release.read_bytes()
        if len(raw) > 65536: raise ValueError('Release provenance exceeds its bound')
        value = json.loads(raw)
        if not isinstance(value, dict): raise ValueError('Invalid release provenance')
        release_record = dict(sha256=digest(raw), identity=value)
    record = dict(format_version=1, scope='project-source-only', overall_release_qualified=False,
                  source_revision=revision, development=dirty or revision is None or bool(unmatched),
                  unmatched_original_files=unmatched,
                  source_files=sources, staged_files=staged, release=release_record,
                  license='AGPL-3.0-or-later', notices={n:sources[n] for n in ('LICENSE','LICENSING.md')},
                  limitations=['Third-party corresponding-source and notice obligations remain separate.',
                               'Captured vendor kernel/bootloader source reproduction is not established.'])
    record['build_id'] = build_id(record)
    record['public_source'] = dict(qualified=False, reason='Development output; public matching source not qualified')
    if public_source is not None:
        from qualify_project_source import verify_public
        record['public_source'] = verify_public(record, public_source)
    payload = {}
    bases = [DOC]
    for prefix in PACKAGES:
        if (root/prefix).is_dir() or any(n.startswith(prefix) for n in files): bases.append(prefix)
    for base in bases:
        for filename, raw in [('project-LICENSE.txt', (repo/'LICENSE').read_bytes()),
                              ('project-NOTICE.txt', (repo/'LICENSING.md').read_bytes()),
                              ('project-source.json', encoded(record))]:
            name = base + filename; path = checked(root, name)
            if filename != 'project-source.json' and path.is_file() and path.read_bytes() != raw:
                raise ValueError('Existing project notice differs from source grant/license')
            payload[name] = raw
    return payload, record


def build_id(record):
    return digest(encoded({k:v for k,v in record.items() if k not in ('build_id','public_source')}))


def validate(root):
    root = Path(root)
    path = checked(root, DOC+'project-source.json')
    if not path.is_file(): raise ValueError('Missing staged project provenance')
    if path.stat().st_size > 4*1024*1024: raise ValueError('Project provenance exceeds bound')
    record = json.loads(path.read_bytes())
    if record.get('format_version') != 1 or record.get('scope') != 'project-source-only' or record.get('overall_release_qualified') is not False:
        raise ValueError('Invalid source qualification scope')
    if record.get('build_id') != build_id(record): raise ValueError('Project build identity mismatch')
    actual = installed_files(root)
    if set(actual) != set(record['staged_files']): raise ValueError('Staged project file inventory mismatch')
    for name, raw in actual.items():
        if digest(raw) != record['staged_files'][name]['sha256']: raise ValueError('Staged project file mismatch: '+name)
    release = checked(root, 'usr/lib/sv08/release.json')
    expected = record['release']
    if (expected is None and release.exists()) or (expected is not None and
            (not release.is_file() or digest(release.read_bytes()) != expected['sha256'])):
        raise ValueError('Stale installed release provenance')
    for base in [DOC, *(p for p in PACKAGES if (root/p).is_dir())]:
        for filename, source in [('project-LICENSE.txt','LICENSE'), ('project-NOTICE.txt','LICENSING.md')]:
            notice = checked(root, base+filename)
            if not notice.is_file() or digest(notice.read_bytes()) != record['notices'][source]:
                raise ValueError('Missing or changed project notice')
        if checked(root, base+'project-source.json').read_bytes() != path.read_bytes():
            raise ValueError('Project provenance copies differ')
    return record


def publish(root, payload):
    """Caller preflights and owns publication; fixed notices have ordinary file modes."""
    for name, raw in payload.items():
        path = checked(root, name); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw); path.chmod(0o644)
