#!/usr/bin/env python3
"""Post-deployment functional checks. No apply/restart/reboot or private output.

Run as root on the installed host with the compiled static-asset manifest.
Status helpers may acquire normal locks/initialize metadata. This is not an
identity backup, authenticated browser check or printing qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

HELPERS = {'hardware': ('sv08_printer_helper.py', 'action'),
           'updates': ('sv08_admin.py', 'method'),
           'software': ('sv08_software.py', 'method'),
           'network': ('sv08_network.py', 'method'),
           'identity': ('sv08_identity.py', 'method'),
           'mainsail': ('sv08_mainsail_access.py', 'method')}


def probe(root, name, key):
    result = subprocess.run(['/usr/bin/python3', str(root / 'usr/lib/sv08' / name)],
                            input=json.dumps({key: 'status'}), text=True,
                            capture_output=True, timeout=30,
                            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    if result.returncode or len(result.stdout.encode()) > 4 * 1024 * 1024:
        raise ValueError('Status helper execution failed')
    reply = json.loads(result.stdout)
    if not isinstance(reply, dict) or reply.get('ok') is not True or not isinstance(reply.get('result'), dict):
        raise ValueError('Status helper refused or returned an invalid envelope')
    return reply['result']


def check(root, manifest, run_probe=probe, baseline=None):
    root = Path(root)
    report = {'passed': True, 'assets': {}, 'helpers': {}, 'storage': {}}
    files = manifest.get('files') if isinstance(manifest, dict) else None
    if not isinstance(files, dict) or not files:
        raise ValueError('Expected compiled static-asset manifest')
    for name, expected in files.items():
        relative = Path(name)
        if (relative.is_absolute() or '..' in relative.parts or
                relative.parts[:3] != ('usr', 'share', 'cockpit') or
                len(relative.parts) != 5 or relative.parts[3] not in ('sv08-host', 'sv08-printer') or
                not isinstance(expected, str) or len(expected) != 64):
            raise ValueError('Unsupported asset manifest path or hash')
        path = root / relative
        try:
            info = path.lstat()
            good = (not any(p.is_symlink() for p in (path, *path.parents)) and
                    stat.S_ISREG(info.st_mode) and info.st_uid == 0 and
                    info.st_nlink == 1 and not info.st_mode & 0o022 and
                    hashlib.sha256(path.read_bytes()).hexdigest() == expected)
        except OSError: good = False
        report['assets'][name] = good
        report['passed'] &= good
    for label, (name, key) in HELPERS.items():
        try:
            result = run_probe(root, name, key)
            if label == 'hardware':
                state = result['state']
                if not (state['format_version'] == 1 and result.get('catalog_supported', True) and
                        type(state['revision']) is int and isinstance(state['draft']['devices'], list) and
                        isinstance(result['definitions'], list) and result['definitions'] and isinstance(result['sources'], dict)):
                    raise ValueError('Unsupported hardware status')
                report['hardware'] = {'revision': state['revision'],
                                      'devices': len(state['draft']['devices']),
                                      'definitions': len(result['definitions']),
                                      'sources': len(result['sources']),
                                      'current': state.get('current') is not None,
                                      'previous': state.get('previous') is not None}
            report['helpers'][label] = True
        except (ValueError, OSError, KeyError, TypeError, AssertionError, subprocess.SubprocessError):
            report['helpers'][label] = False
            report['passed'] = False
    # Publication previews do not enforce managed-directory ownership; check it
    # before allowing deployment to be reported functional, without applying.
    try:
        boot = json.loads((root / 'run/sv08/boot.json').read_text())
        generation = Path(boot['generation'])
        if not generation.is_absolute() or '..' in generation.parts or generation.parts[:4] != ('/', 'data', 'sv08', 'generations'):
            raise ValueError('Invalid generation')
        config = root / str(generation).lstrip('/') / 'config'
        if any(p.is_symlink() for p in (config, *config.parents)):
            raise ValueError('Unexpected generation link')
        for name, mode, gid in (('printer-hardware', 0o700, 0), ('printer-managed', 0o750, 1000)):
            directory = config / name
            good = True
            if directory.exists() or directory.is_symlink():
                for path in (directory, *directory.rglob('*')):
                    st = path.lstat()
                    expected_mode = mode if path.is_dir() else (0o640 if name == 'printer-managed' and path.suffix == '.cfg' else 0o600)
                    good &= (not path.is_symlink() and (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)) and
                             st.st_uid == 0 and (st.st_gid == gid if path.is_dir() or name == 'printer-hardware' or path.suffix == '.cfg' else True) and
                             stat.S_IMODE(st.st_mode) == expected_mode)
            report['storage'][name] = bool(good)
            report['passed'] &= bool(good)
    except (OSError, ValueError, KeyError, TypeError):
        report['storage']['context'] = False
        report['passed'] = False
    if baseline is not None:
        report['preserved_hardware_summary'] = (isinstance(baseline, dict) and
                                                isinstance(baseline.get('hardware'), dict) and
                                                report.get('hardware') == baseline['hardware'])
        report['passed'] &= report['preserved_hardware_summary']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, help='Prior readiness receipt; require identical hardware summary')
    args = parser.parse_args()
    if os.geteuid() != 0: parser.error('Administrator execution is required')
    try:
        result = check(Path('/'), json.loads(args.manifest.read_text()),
                       baseline=json.loads(args.baseline.read_text()) if args.baseline else None)
    except (OSError, ValueError, TypeError):
        result = {'passed': False, 'error': 'Invalid or unavailable deployment manifest'}
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
