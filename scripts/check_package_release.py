#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline package/release regression gate; evidence is not release qualification.

Run from a checkout with only upstream/mainsail prepared at its gitlink. Uses
stdlib plus existing git, patch and dpkg-deb. Logs retain at most 128 KiB each.
The exact supplier archive is supplied via SV08_GCODEVIEWER_ARCHIVE.
Every skip, empty selection and discovery error fails the gate.
"""
import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import unittest

SUITES = (
    'test_package_klipper.py', 'test_package_policy.py', 'test_package_rauc.py',
    'test_package_update_admission_license.py', 'test_python_app_package.py',
    'test_klipper_build_inputs.py', 'test_prepare_release.py',
    'test_image_license_inventory.py', 'test_license_inventory.py',
    'test_project_license.py', 'test_resolve_npm_notices.py',
    'test_mainsail_notice_dependencies.py', 'test_package_release_ci.py',
)
LOG_LIMIT = 128 * 1024


class BoundedLog(io.TextIOBase):
    """Keep the latest diagnostics when noisy tests exceed the artifact limit."""
    marker = b'[earlier log output truncated; retaining tail]\n'

    def __init__(self):
        self.tail = b''
        self.truncated = False

    def write(self, text):
        raw = self.tail + text.encode('utf-8')
        capacity = LOG_LIMIT - len(self.marker)
        self.truncated = self.truncated or len(raw) > capacity
        self.tail = raw[-capacity:]
        return len(text)

    def getvalue(self):
        return (self.marker if self.truncated else b'').decode() + self.tail.decode('utf-8', errors='ignore')


def source_metadata(root):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    return {'revision': git('rev-parse', 'HEAD'),
            'mainsail_gitlink': git('ls-tree', 'HEAD', 'upstream/mainsail'),
            'dirty': bool(git('status', '--porcelain', '--untracked-files=normal'))}


def run(root, output, selections=SUITES):
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {'scope': 'offline fixtures; no image/build/hardware/release qualification',
              'suites': [], 'errors': []}
    try:
        report['source'] = source_metadata(root)
    except Exception as error:
        report['errors'].append('source metadata: ' + str(error))
    if not selections or len(set(selections)) != len(selections):
        report['errors'].append('empty or duplicate suite selection')
    for name in selections:
        log = BoundedLog()
        entry = {'suite': name, 'tests': 0, 'passed': False, 'skips': []}
        try:
            if Path(name).name != name or not (root / 'tests' / name).is_file():
                raise ValueError('missing or invalid selected suite: ' + name)
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                loader = unittest.TestLoader()
                suite = loader.discover(str(root / 'tests'), pattern=name)
                if loader.errors or suite.countTestCases() == 0:
                    raise ValueError('discovery failed or selected zero tests: ' + '\n'.join(loader.errors))
                result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
            entry.update(tests=result.testsRun,
                         skips=[{'test': test.id(), 'reason': reason} for test, reason in result.skipped])
            entry['passed'] = result.wasSuccessful() and not result.skipped
        except Exception as error:
            log.write(f'Gate error: {type(error).__name__}: {error}\n')
        entry['log'] = name + '.log'
        (output / entry['log']).write_text(log.getvalue(), encoding='utf-8')
        report['suites'].append(entry)
    report['passed'] = bool(report['suites']) and not report['errors'] and all(e['passed'] for e in report['suites'])
    (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    lines = [f"Package/release offline gate: {'PASS' if report['passed'] else 'FAIL'}",
             f"Source: {report.get('source', {}).get('revision', 'UNAVAILABLE')}", report['scope']]
    lines += [f"{e['suite']}: {'PASS' if e['passed'] else 'FAIL'}; {e['tests']} tests; {len(e['skips'])} skips" for e in report['suites']]
    lines += report['errors']
    (output / 'summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(Path(__file__).resolve().parents[1], args.output))
