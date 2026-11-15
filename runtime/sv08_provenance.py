#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only local project-record consistency, not publisher or OS authenticity."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath

DOC = 'usr/share/doc/sv08-mainline/'
PACKAGES = ('usr/share/cockpit/sv08-host/', 'usr/share/cockpit/sv08-printer/')
PREFIXES = ('usr/lib/sv08/', 'usr/share/sv08/printer/', *PACKAGES)
EXTRA_FILES = ('etc/cockpit/cockpit.conf','etc/sudoers.d/sv08-view',
    'etc/systemd/system/sv08-calibration-reconcile.service',
    'etc/dbus-1/system.d/zz-sv08-rauc.conf','etc/systemd/system/rauc.service.d/sv08.conf',
    'etc/systemd/system/cockpit.socket.d/sv08-identity.conf',
    'usr/lib/systemd/system/sv08-admin-image-worker@.service',
    'usr/lib/systemd/system/sv08-software-worker@.service',
    'usr/lib/systemd/system/sv08-feed.service','usr/lib/systemd/system/sv08-feed.timer',
    'usr/lib/systemd/system/sv08-recovery-display.service',
    'usr/share/xsessions/sv08-recovery.desktop')
GENERATED = ('project-source.json', 'project-LICENSE.txt', 'project-NOTICE.txt')
NOTICE_PATHS = {base+name for base in (DOC,*PACKAGES) for name in GENERATED}
# The owner public key is an image build input, not project corresponding source.
NON_CODE_BUILD_INPUTS = {'usr/lib/sv08/seed/authorized_keys':'owner-public-key'}
NON_CODE_INPUT_LIMIT = 65536
# Only these branding assets belong to this project. Other files in Debian's
# shared branding directory (including its favicon/logo symlinks) belong to the
# vendor package, outside the project-source-only inventory.
BRANDING_FILES = ('badge.svg', 'branding.css')


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

def non_code_build_inputs(root):
    """Hash only the fixed public-key input; never publish its bytes or source map."""
    result = {}
    for name, kind in NON_CODE_BUILD_INPUTS.items():
        path = checked(root, name)
        if not path.is_file(): continue
        if path.stat().st_size > NON_CODE_INPUT_LIMIT:
            raise ValueError('Non-code build input exceeds bound: ' + name)
        with path.open('rb') as stream: raw = stream.read(NON_CODE_INPUT_LIMIT+1)
        if len(raw) > NON_CODE_INPUT_LIMIT:
            raise ValueError('Non-code build input exceeds bound: ' + name)
        result[name] = dict(type=kind, sha256=digest(raw))
    return result


def walk_files(base, recursive=True):
    def failed(error):
        raise error
    # stat distinguishes an absent scope from an unreadable one.
    try: base.stat()
    except FileNotFoundError: return
    for directory, directories, files in os.walk(base, onerror=failed):
        for name in directories + files:
            yield Path(directory) / name
        if not recursive: break


def installed_files(root, overrides=None, replaced=()):
    if any(name in NON_CODE_BUILD_INPUTS for name in (overrides or {})):
        raise ValueError('Stage the owner public-key build input before preparing provenance')
    result = {}
    for prefix in PREFIXES:
        base = root / prefix
        if base.is_symlink(): raise ValueError('Symlink in project staging directory')
        for path in walk_files(base):
            name = path.relative_to(root).as_posix()
            if any(name.startswith(p) for p in replaced): continue
            if name in NOTICE_PATHS or name == 'usr/lib/sv08/release.json': continue
            if path.is_symlink(): raise ValueError('Symlink in staged project files')
            if name in NON_CODE_BUILD_INPUTS: continue
            if path.is_file(): result[name] = checked(root, name).read_bytes()
    for name in EXTRA_FILES:
        path = checked(root, name)
        if path.is_file(): result[name] = path.read_bytes()
    branding = root/'usr/share/cockpit/branding/debian'
    if branding.is_symlink(): raise ValueError('Symlink in project branding')
    for filename in BRANDING_FILES:
        name = (branding / filename).relative_to(root).as_posix()
        path = checked(root, name)
        if path.is_file(): result[name] = path.read_bytes()
    result.update(overrides or {})
    return {n: raw for n, raw in result.items() if n not in NOTICE_PATHS}


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
    if non_code_build_inputs(root) != record.get('non_code_build_inputs', {}):
        raise ValueError('Non-code build input inventory mismatch')
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
        copy = checked(root, base+'project-source.json')
        if not copy.is_file() or copy.read_bytes() != path.read_bytes():
            raise ValueError('Project provenance copies differ')
    return record


def status(root):
    """Finite public result; exception details and provenance contents stay private."""
    result = dict(state='unavailable', build_id=None, scope='local-project-record', reason='read-failed')
    try:
        baseline = checked(root, DOC+'project-source.json')
        if not baseline.is_file():
            result['reason'] = 'baseline-missing'
            return result
        record = validate(root)
        result.update(state='intact', build_id=record['build_id'], reason='record-matches')
    except OSError:
        pass
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError):
        result.update(state='tainted', reason='record-mismatch')
    return result


def main():
    # The production command accepts no root/path from callers.
    print(json.dumps({'ok': True, 'result': status(Path('/'))}, sort_keys=True))


if __name__ == '__main__':
    main()
