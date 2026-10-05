#!/usr/bin/env python3
"""Read-only adoption inventory, not a dispatcher or evidence validator.

Summarize recorded task state even when historical Git objects or local leases are
unavailable. Never infer authorization, cancellation or migration from prose.
Use feature_workflow.py validate/status for the actual workflow checks.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 2 * 1024 * 1024
STATUSES = {'pending', 'running', 'review', 'blocked', 'done'}
ENVIRONMENTS = {'offline', 'hardware', 'human'}
ROUTES = {'self', 'targeted', 'consequential'}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def load_records(root):
    """Read only canonical public record files; do not follow evidence paths."""
    directory = root / 'docs/features'
    if any(p.is_symlink() for p in (root / 'docs', directory)):
        raise ValueError('Symlink feature directory is not supported')
    if not directory.is_dir():
        raise ValueError('Missing docs/features directory; not an empty queue')
    records, hashes = {}, {}
    for folder in sorted(directory.iterdir()):
        if folder.is_symlink():
            raise ValueError(f'Symlink feature directory: {folder.name}')
        if not folder.is_dir():
            continue
        path = folder / 'record.json'
        if path.is_symlink():
            raise ValueError(f'Symlink record: {folder.name}')
        if not path.exists():
            continue  # Some source/evidence folders are not workflow records.
        with path.open('rb') as stream:
            raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError(f'Oversize record: {folder.name}')
        record = json.loads(raw, object_pairs_hook=unique_object,
                            parse_constant=lambda x: (_ for _ in ()).throw(
                                ValueError(f'Non-finite JSON value: {x}')))
        if not isinstance(record, dict) or record.get('id') != folder.name:
            raise ValueError(f'Feature ID/directory mismatch: {folder.name}')
        records[folder.name] = record
        hashes[folder.name] = hashlib.sha256(raw).hexdigest()
    return records, hashes


def summarize(records, hashes=None):
    """Validate inventory fields, not complete schemas or historical evidence."""
    hashes = hashes or {}
    tasks = {}
    for feature, record in sorted(records.items()):
        version = record.get('format_version')
        if type(version) is not int or version not in (1, 2):
            raise ValueError(f'Unsupported record version: {feature}')
        if record.get('id') != feature or not isinstance(record.get('tasks'), list):
            raise ValueError(f'Invalid record identity/tasks: {feature}')
        for task in record['tasks']:
            if not isinstance(task, dict) or not isinstance(task.get('id'), str) or not task['id']:
                raise ValueError(f'Invalid task: {feature}')
            key = f"{feature}:{task['id']}"
            allowed = STATUSES | ({'validated'} if version == 2 else set())
            if task.get('status') not in allowed or task.get('environment') not in ENVIRONMENTS:
                raise ValueError(f'Unknown status/environment: {key}')
            if key in tasks:
                raise ValueError(f'Duplicate task: {key}')
            deps = task.get('depends_on')
            if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
                raise ValueError(f'Invalid dependencies: {key}')
            if version == 2 and task.get('review_policy') not in ROUTES:
                raise ValueError(f'Unknown review route: {key}')
            blocker = task.get('blocker')
            if blocker is not None and not isinstance(blocker, str):
                raise ValueError(f'Invalid blocker: {key}')
            if task['status'] == 'blocked' and not blocker:
                raise ValueError(f'Missing blocked-task reason: {key}')
            tasks[key] = (feature, version, task)
    reverse = {key: [] for key in tasks}
    for key, (_, _, task) in tasks.items():
        for dependency in task['depends_on']:
            if dependency in reverse:
                reverse[dependency].append(key)
    rows = []
    for key, (feature, version, task) in sorted(tasks.items()):
        state = task['status']
        if state == 'done':
            action = 'preserve_history'
        elif state in {'running', 'review', 'validated'}:
            action = 'reconcile_active_assignment'
        elif state == 'blocked':
            action = 'respect_existing_blocker'
        elif task['environment'] != 'offline':
            action = 'manual_hardware_or_human_queue'
        elif version == 1:
            action = 'assess_remaining_scope_for_v2'
        else:
            action = 'use_v2_after_workflow_checks'
        rows.append({
            'task': key, 'format_version': version, 'recorded_status': state,
            'environment': task['environment'],
            'review_policy': task.get('review_policy') if version == 2 else 'legacy',
            'blocker': task.get('blocker'), 'inspection_action': action,
            'dependencies': [{'task': d,
                              'recorded_status': tasks[d][2]['status'] if d in tasks else 'missing'}
                             for d in task['depends_on']],
            'referenced_by': sorted(reverse[key]),
            'record_path': f'docs/features/{feature}/record.json',
            'record_sha256': hashes.get(feature),
        })
    return {
        'report_version': 1, 'inventory_only': True,
        'limits': 'Not readiness, authorization, full-schema, lease, or historical-evidence validation. '
                  'No records changed. Pending is not permission; blocked is not cancelled.',
        'feature_count': len(records), 'task_count': len(rows),
        'versions': dict(sorted(Counter(str(v['format_version']) for v in records.values()).items())),
        'recorded_status_counts': dict(sorted(Counter(r['recorded_status'] for r in rows).items())),
        'inspection_action_counts': dict(sorted(Counter(r['inspection_action'] for r in rows).items())),
        'tasks': rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    try:
        records, hashes = load_records(root)
        report = summarize(records, hashes)
        try:
            revision = subprocess.check_output(
                ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True,
                stderr=subprocess.DEVNULL,
                env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}).strip()
        except (OSError, subprocess.CalledProcessError):
            revision = None
        report['checkout_head'] = revision
        report['checkout_note'] = 'Record hashes describe bytes read; HEAD does not prove a clean checkout.'
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f'workflow-inventory: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
