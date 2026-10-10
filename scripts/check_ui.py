#!/usr/bin/env python3
"""Run the existing disposable admin-browser check; no model or publication calls.

Inspection is the default. Use an assigned disposable checkout. Execution owns
only a fresh build subdirectory and its process groups. This is fixture evidence, not installed Cockpit or UX approval.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
MIB = 1024 * 1024
FIXTURE = 'scripts/preview_admin_ui.py'
BROWSER = 'tests/admin_browser.mjs'


class CheckError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CheckError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), f'Not a regular input: {path}')
    require(path.stat().st_size <= 32 * MIB, f'Oversize evidence input: {path}')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def work_path(repo, path):
    raw = Path(os.path.abspath(path if Path(path).is_absolute() else repo / path))
    require(not any(p.is_symlink() for p in (raw, *raw.parents)), 'Symlink work path')
    require(raw.is_relative_to(repo / 'build') and raw != repo / 'build',
            'Work must be a fresh directory below repository build/')
    require(not raw.exists(), 'Work already exists; preserve it and choose a fresh directory')
    return raw


def source_snapshot(repo):
    # Include untracked source files as well as tracked files. Never read personal
    # configuration, credentials, build output or the complete conversation.
    names = {FIXTURE, BROWSER, 'scripts/prepare_host_os.py', 'scripts/check_ui.py'}
    for directory, pattern in [('ui/host', '*'), ('runtime', '*.py')]:
        root = repo / directory
        require(root.is_dir() and not root.is_symlink(), f'Missing source directory: {directory}')
        for path in root.rglob(pattern):
            require(not path.is_symlink(), f'Symlink source: {path}')
            if path.is_file() and '__pycache__' not in path.parts:
                names.add(path.relative_to(repo).as_posix())
    files = {name: digest(repo / name) for name in sorted(names)}
    try:
        head = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', 'HEAD'],
                              capture_output=True, text=True, timeout=5, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        head = None
    payload = {'git_head': head, 'files': files}
    payload['sha256'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload


def executable(value):
    found = shutil.which(value)
    require(found is not None, f'Executable not available: {value}; use existing approved tools')
    return str(Path(found).resolve())


def plan(repo, work, node, chromium, timeout, max_mib):
    repo = Path(repo).resolve()
    require(os.name == 'posix', 'This runner requires POSIX process groups')
    require(0 < timeout <= 1800 and 0 < max_mib <= 4096, 'Invalid primary-task allowance')
    work = work_path(repo, work)
    return {'work': str(work), 'timeout_seconds': timeout, 'max_output_mib': max_mib,
            'fixture_command': [sys.executable, str(repo / FIXTURE), '--work', str(work / 'fixture'), '--execute'],
            'browser_command': [executable(node), str(repo / BROWSER), executable(chromium),
                                str(work / 'fixture'), str(work / 'browser')]}


def stop(process):
    # Descendants may outlive their parent. Signal only the session group we
    # created, not a name-based/global browser or fixture process search.
    for sig, grace in [(signal.SIGTERM, 0.5), (signal.SIGKILL, 0)]:
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        if grace:
            time.sleep(grace)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        raise CheckError(f'Owned process did not exit: {process.pid}')


def json_file(path):
    require(path.is_file() and not path.is_symlink(), f'Missing regular result: {path.name}')
    require(path.stat().st_size <= 65536, f'Oversize result: {path.name}')
    return json.loads(path.read_text(encoding='utf-8'))


def run_checks(repo, settings):
    repo, work = Path(repo).resolve(), Path(settings['work'])
    # Recheck at execution, not just when constructing an inspection plan.
    work_path(repo, work)
    before = source_snapshot(repo)
    work.mkdir(parents=True, mode=0o700)
    (work / 'source.json').write_text(json.dumps(before, indent=2) + '\n')
    processes, streams = [], []
    started = time.monotonic()
    summary = {'format_version': 1, 'status': 'failed', 'stage': 'fixture',
               'source_sha256': before['sha256'], 'git_head': before['git_head'],
               'source_manifest': 'source.json', 'commands': settings,
               'automated_checks': 'not_run', 'visual_assessment': 'not_performed',
               'standard_project_tests': 'not_run', 'installed_cockpit': 'not_tested',
               'physical_hardware': False, 'artifacts': {}}

    def guard():
        require(time.monotonic() - started < settings['timeout_seconds'], 'Execution timeout')
        size = sum(p.lstat().st_size for p in work.rglob('*') if not p.is_symlink() and p.is_file())
        require(size <= settings['max_output_mib'] * MIB, 'Output allowance exceeded')

    def start(command, log):
        stream = (work / log).open('wb')
        streams.append(stream)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', SV08_UI_OWNED_PROCESS_GROUP='1')
        process = subprocess.Popen(command, cwd=repo, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(process)
        return process

    try:
        fixture = start(settings['fixture_command'], 'fixture.log')
        ready = work / 'fixture/server.json'
        while True:
            guard()
            require(fixture.poll() is None, 'Fixture exited before readiness')
            if ready.exists():
                try:
                    address = json_file(ready)
                except json.JSONDecodeError:
                    address = None  # Existing fixture writes this small file in place.
                if address is not None:
                    require(isinstance(address, dict) and
                            re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}', str(address.get('url', ''))),
                            'Fixture did not provide a loopback URL')
                    require(0 < int(address['url'].rsplit(':', 1)[1]) <= 65535, 'Invalid fixture port')
                    break
            time.sleep(0.1)
        summary['stage'] = 'browser'
        browser = start(settings['browser_command'], 'runner.log')
        summary['automated_checks'] = 'failed'  # Attempted, until an explicit result passes.
        while browser.poll() is None:
            guard()
            require(fixture.poll() is None, 'Fixture exited during browser checks')
            time.sleep(0.1)
        guard()
        summary['browser_exit_code'] = browser.returncode
        require(browser.returncode == 0, 'Browser command failed; inspect runner.log before assigning repair')
        result = json_file(work / 'browser/result.json')
        require(isinstance(result, dict) and result.get('passed') is True,
                'Browser result missing an explicit passing result')
        summary['automated_checks'] = 'passed'
        summary['stage'] = 'source-consistency'
        after = source_snapshot(repo)
        (work / 'source-after.json').write_text(json.dumps(after, indent=2) + '\n')
        require(before == after, 'Source changed during checks; evidence is not a stable candidate')
        summary.update(status='passed', stage='complete', next_action='assess-rendered-ux')
    except (CheckError, OSError, ValueError, subprocess.SubprocessError) as error:
        summary['error'] = str(error)
        summary['next_action'] = 'triage-failure-with-existing-evidence'
    finally:
        for process in reversed(processes):
            try:
                stop(process)
            except (OSError, CheckError) as error:
                summary.update(status='failed', cleanup_error=str(error), next_action='reconcile-owned-processes')
        for stream in streams:
            stream.close()
        # Publish compact references, not a browser profile or long raw logs.
        paths = [work / 'source.json', work / 'source-after.json', work / 'fixture.log',
                 work / 'runner.log', work / 'browser/result.json', work / 'browser/browser.log']
        paths += sorted((work / 'browser').glob('*.png'))
        for path in paths:
            if path.is_file() and not path.is_symlink() and path.stat().st_size <= 32 * MIB:
                summary['artifacts'][path.relative_to(work).as_posix()] = {
                    'sha256': digest(path), 'bytes': path.stat().st_size}
        summary['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (work / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--node', default='node')
    parser.add_argument('--chromium', default='chromium')
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--max-output-mib', type=int, default=256)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        settings = plan(REPO, args.work, args.node, args.chromium, args.timeout, args.max_output_mib)
        if not args.execute:
            print(json.dumps({'execute': False, **settings}, indent=2))
            return 0
        def interrupted(signum, _frame):
            raise CheckError(f'Interrupted by signal {signum}')
        previous = signal.signal(signal.SIGTERM, interrupted)
        try:
            result = run_checks(REPO, settings)
        finally:
            signal.signal(signal.SIGTERM, previous)
        print(json.dumps({'status': result['status'], 'stage': result['stage'],
                          'summary': str(Path(settings['work']) / 'summary.json'),
                          'visual_assessment': result['visual_assessment'],
                          'standard_project_tests': result['standard_project_tests']}))
        return 0 if result['status'] == 'passed' else 1
    except (CheckError, OSError, ValueError) as error:
        parser.exit(2, f'UI check: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
