#!/usr/bin/env python3
"""Validate and dispatch approved feature tasks; never execute record commands.

Custom gap: durable dependency/evidence gates and exclusive coordination around
Codex's existing tools. Decision 0011 records scope, provenance and retirement.
All mutations require --execute. This tool neither starts agents nor schedules
work, operates hardware, merges branches or publishes to a remote.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

try:
    from jsonschema import Draft202012Validator
except ImportError:
    raise SystemExit('Install the workstation dependency python3-jsonschema; see .codex/README.md')


REPO = Path(__file__).resolve().parents[1]
APPROVED = {'approved', 'approved-with-constraints'}
ACTIVE = {'running', 'review'}
PRIVATE = {'local', 'backups', 'artifacts', 'build', 'dist', '.git', '.venv'}


class WorkflowError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise WorkflowError(message)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest_json(value):
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def scope_digest(record):
    """Bind approved scope while allowing execution/evidence metadata to change."""
    scope = {key: value for key, value in record.items() if key not in {'decision', 'tasks'}}
    scope['tasks'] = [{key: task[key] for key in
                      ('id', 'title', 'environment', 'depends_on', 'checks', 'human_task')}
                     for task in record['tasks']]
    return digest_json(scope)


def read_json(path):
    require(path.stat().st_size <= 2 * 1024 * 1024, f'Oversize JSON: {path.name}')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(WorkflowError('Non-finite JSON')))


def public_path(root, name, *, exists=True):
    require(isinstance(name, str) and name and '\\' not in name, 'Invalid evidence path')
    relative = Path(name.split('#', 1)[0])
    require(not relative.is_absolute() and '..' not in relative.parts and
            relative.parts and relative.parts[0] not in PRIVATE, 'Use a public repository path')
    require(not any(part.startswith('.env') for part in relative.parts), 'Private environment path')
    if relative.parts[0] == '.codex':
        require(str(relative) == '.codex/README.md' or len(relative.parts) == 3 and
                relative.parts[1] in {'agents', 'schemas', 'templates'}, 'Private Codex configuration path')
    path = root / relative
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != root.parent),
            'Symlink evidence paths are not accepted')
    require(path.resolve().is_relative_to(root.resolve()), 'Evidence escapes repository')
    if exists:
        require(path.is_file(), f'Missing public evidence: {name}')
    return path


def file_hash(root, name):
    path = public_path(root, name)
    require(path.stat().st_size <= 32 * 1024 * 1024, 'Evidence input is too large')
    return digest_bytes(path.read_bytes())


def snapshot(root, names):
    return {name: file_hash(root, name) for name in sorted(set(names))}


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def check_review_cases(result):
    """Reject incomplete or policy-incompatible live evaluation responses."""
    schema = read_json(REPO / '.codex/schemas/review-cases.schema.json')
    errors = list(Draft202012Validator(schema).iter_errors(result))
    require(not errors, errors[0].message if errors else '')
    expected = {'useful-improvement': APPROVED, 'duplicate': {'rejected', 'deferred'},
                'hardware-assumption': {'rejected', 'needs-research'},
                'owner-conflict': {'rejected', 'needs-research', 'deferred'},
                'offline-despite-hardware': APPROVED}
    rows = result['results']
    require(len(rows) == len(expected) and {r['id'] for r in rows} == set(expected),
            'Evaluation must cover every case exactly once')
    for row in rows:
        require(row['outcome'] in expected[row['id']] and row['rationale'].strip(),
                'Evaluation conflicts with expected policy: ' + row['id'])
        if row['id'] == 'owner-conflict':
            require(row['owner_required'] is True, 'Owner requirements cannot be waived')
    return {'passed': True, 'cases': len(rows)}


class Workflow:
    def __init__(self, root=REPO):
        self.root = Path(root).resolve()
        self.checkout = self.root
        common = Path(git(self.root, 'rev-parse', '--git-common-dir'))
        if not common.is_absolute():
            common = self.root / common
        self.common = common.resolve()
        self.primary = self.common.parent
        require(self.common.name == '.git', 'Use a normal repository or its worktree')
        # Read one authoritative queue even when this tool runs in a worktree.
        self.root = self.primary
        self.state = self.primary / 'local/feature-workflow'
        schema = read_json(REPO / '.codex/schemas/feature-record.schema.json')
        Draft202012Validator.check_schema(schema)
        self.validator = Draft202012Validator(schema)

    @contextmanager
    def locked(self):
        require(self.checkout == self.primary, 'Mutate queue records from the primary checkout only')
        self.state.mkdir(parents=True, exist_ok=True)
        require(not self.state.is_symlink() and not self.state.parent.is_symlink(), 'Unsafe local state path')
        fd = os.open(self.state / 'coordinator.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise WorkflowError('Another coordinator owns the queue') from None
            yield
        finally:
            os.close(fd)

    def load(self):
        records = {}
        for path in sorted((self.root / 'docs/features').glob('*/record.json')):
            require(not path.is_symlink() and not path.parent.is_symlink(), 'Symlink feature record')
            record = read_json(path)
            errors = sorted(self.validator.iter_errors(record), key=lambda e: str(e.path))
            require(not errors, f'{path.parent.name}: {errors[0].message if errors else ""}')
            require(record['id'] == path.parent.name, 'Feature ID and directory differ')
            require(record['id'] not in records, 'Duplicate feature ID')
            records[record['id']] = record
        self.validate(records)
        return records

    def save(self, record):
        errors = list(self.validator.iter_errors(record))
        require(not errors, errors[0].message if errors else '')
        atomic_json(self.root / 'docs/features' / record['id'] / 'record.json', record)

    @staticmethod
    def task_map(records):
        return {f'{r["id"]}:{t["id"]}': (r, t) for r in records.values() for t in r['tasks']}

    def validate(self, records):
        tasks = self.task_map(records)
        active = []
        for record in records.values():
            public_path(self.root, record['proposal'])
            require(record['proposal'] == f'docs/features/{record["id"]}/proposal.md', 'Unexpected proposal path')
            for reference in record['requirements']:
                public_path(self.root, reference)
            require(len({t['id'] for t in record['tasks']}) == len(record['tasks']), 'Duplicate task ID')
            checks = {c['id']: c for c in record['checks']}
            require(len(checks) == len(record['checks']), 'Duplicate acceptance check ID')
            owners = [c for t in record['tasks'] for c in t['checks']]
            require(set(owners) == set(checks) and len(owners) == len(set(owners)),
                    'Every acceptance check must belong to exactly one task')
            decision = record['decision']
            if decision:
                require(decision['reviewer'] != record['author'], 'Author cannot approve own proposal')
                require(set(decision['requirements_sha256']) == set(record['requirements']),
                        'Decision must bind all requirement references')
                require(decision['authority'] != 'delegated' or not record['owner_decision_required'],
                        'This scope needs an owner decision')
                for constraint in decision['constraints']:
                    require(set(constraint['checks']) <= set(checks), 'Constraint refers to unknown acceptance check')
                if decision['outcome'] == 'approved-with-constraints':
                    require(decision['constraints'], 'Constrained approval needs observable constraints')
            for task in record['tasks']:
                key = record['id'] + ':' + task['id']
                require(set(task['checks']) <= set(checks), 'Unknown task acceptance check')
                require(all(dep in tasks for dep in task['depends_on']), 'Unknown task dependency')
                require(key not in task['depends_on'], 'Task depends on itself')
                if task['environment'] != 'offline':
                    require(task['human_task'] is not None, 'Physical task needs a canonical human task reference')
                if task['human_task']:
                    public_path(self.root, task['human_task'])
                if task['status'] == 'blocked':
                    require(task['blocker'], 'Blocked task needs a reason')
                else:
                    require(task['blocker'] is None, 'Only blocked tasks may have a blocker')
                if task['status'] in ACTIVE:
                    active.append(key)
                    require(task['implementation'] is not None, 'Active task has no owner')
                    require(decision and decision['outcome'] in APPROVED, 'Active task lacks approval')
                for evidence in task['evidence']:
                    require(evidence['check'] in task['checks'], 'Evidence belongs to another task')
                    check = checks[evidence['check']]
                    require(evidence['environment'] == check['environment'], 'Evidence environment does not meet acceptance')
                    public_path(self.root, evidence['document'], exists=False)
                    for name in evidence['source_sha256']:
                        public_path(self.root, name, exists=False)
                    if evidence['environment'] == 'hardware':
                        require(evidence['profile'] and evidence['board_revision'], 'Hardware evidence needs profile/revision or explicit unknown')
                        public_path(self.root, evidence['profile'])
                if task['verification']:
                    require(decision and task['verification']['decision_sha256'] == digest_json(decision),
                            'Verification belongs to a different approved decision')
                    require(task['implementation'] and task['verification']['reviewer'] != task['implementation']['actor']
                            and task['verification']['session'] != task['implementation']['session'],
                            'Implementation needs a separate verifier session')
                    require(task['verification']['evidence_sha256'] == digest_json(task['evidence']),
                            'Verification is stale for the submitted evidence')
                if task['status'] == 'done':
                    require(task['verification'] and task['verification']['outcome'] == 'passed', 'Done task lacks passing independent review')
                    require({e['check'] for e in task['evidence']} == set(task['checks']), 'Done task lacks required evidence')
                    require(all(tasks[d][1]['status'] == 'done' for d in task['depends_on']), 'Done task has unfinished dependency')
                    # Completed tasks retain evidence of their integrated
                    # revision. Later approved work may change those files;
                    # status reports that evidence as historical, never current.
                    self.check_committed_evidence(task)
        require(len(active) <= 1, 'Only one active implementation/review is allowed')
        visiting, visited = set(), set()
        def visit(key):
            require(key not in visiting, 'Task dependency cycle')
            if key in visited:
                return
            visiting.add(key)
            for dependency in tasks[key][1]['depends_on']:
                visit(dependency)
            visiting.remove(key)
            visited.add(key)
        for key in tasks:
            visit(key)

    def decision_problem(self, record):
        decision = record['decision']
        if not decision or decision['outcome'] not in APPROVED:
            return 'Awaiting approved decision'
        if decision['proposal_sha256'] != file_hash(self.root, record['proposal']):
            return 'Proposal changed since approval'
        if decision['scope_sha256'] != scope_digest(record):
            return 'Task or acceptance scope changed since approval'
        if decision['requirements_sha256'] != snapshot(self.root, record['requirements']):
            return 'Requirement sources changed since approval'
        return None

    def status(self, records):
        tasks = self.task_map(records)
        result = []
        active = any(t['status'] in ACTIVE for _, t in tasks.values())
        for key, (record, task) in tasks.items():
            reason = None
            if task['status'] != 'pending':
                reason = task['blocker'] or task['status']
            elif task['environment'] != 'offline':
                reason = 'Human/hardware task: ' + task['human_task']
            elif active:
                reason = 'Another task is active'
            elif self.decision_problem(record):
                reason = self.decision_problem(record)
            elif any(tasks[d][1]['status'] != 'done' for d in task['depends_on']):
                reason = 'Unfinished dependency'
            elif task['repeats'] >= 2:
                reason = 'Repeated failure: change diagnosis/inputs before retrying'
            current_evidence = None
            if task['status'] == 'done':
                try:
                    self.check_evidence(task, self.root)
                    current_evidence = True
                except (WorkflowError, OSError):
                    current_evidence = False
            result.append({'task': key, 'title': task['title'], 'status': task['status'],
                           'ready': reason is None, 'reason': reason, 'priority': record['priority'],
                           'created': record['created'], 'evidence_matches_checkout': current_evidence})
        return sorted(result, key=lambda x: (x['priority'], x['created'], x['task']))

    def select(self, records):
        ready = [entry for entry in self.status(records) if entry['ready']]
        require(len({e['task'].split(':')[0] for e in ready}) <= 3,
                'Ready proposal capacity exceeded; defer or finish existing work')
        return ready[0] if ready else None

    def lookup(self, records, key):
        require(key in self.task_map(records), 'Unknown task')
        return self.task_map(records)[key]

    def packet(self, records, key):
        record, task = self.lookup(records, key)
        return {'feature': record['id'], 'kind': record['kind'], 'task': task,
                'proposal': record['proposal'], 'requirements': record['requirements'],
                'decision': record['decision'], 'checks': [c for c in record['checks'] if c['id'] in task['checks']],
                'instruction': 'Read .codex/README.md. Implement only this approved offline task; '
                'return evidence for independent review. Do not contact hardware or publish. '
                'After completion/blocking, the coordinator selects the next ready task.'}

    def worktree(self, path):
        path = Path(path).resolve()
        require(path != self.primary, 'Implementation requires a separate worktree')
        require(path.is_relative_to(self.state / 'worktrees'), 'Use local/feature-workflow/worktrees/')
        common = Path(git(path, 'rev-parse', '--git-common-dir'))
        if not common.is_absolute():
            common = path / common
        require(common.resolve() == self.common, 'Worktree belongs to a different repository')
        return path

    def lease(self, task):
        require(task['implementation'], 'Task has no implementation owner')
        path = self.state / 'runs' / (task['implementation']['run'] + '.json')
        require(path.is_file() and not path.is_symlink(), 'Missing run ownership; inspect before recovery')
        lease = read_json(path)
        require(lease['session'] == task['implementation']['session'], 'Ownership mismatch')
        return lease

    def claim(self, records, key, actor, session, worktree):
        require(actor.strip() and session.strip(), 'Implementation actor and session are required')
        entries = {e['task']: e for e in self.status(records)}
        require(key in entries and entries[key]['ready'], 'Task is not ready')
        self.select(records)  # Enforce queue capacity even when selecting a specific task.
        tree = self.worktree(worktree)
        require(not git(tree, 'status', '--porcelain'), 'Start from a clean implementation worktree')
        require(git(tree, 'rev-parse', 'HEAD') == git(self.primary, 'rev-parse', 'HEAD'),
                'Start from the current integration commit, including completed dependencies')
        record, task = self.lookup(records, key)
        run = uuid.uuid4().hex
        # A crash after the lease write preserves an orphan for inspection; it
        # cannot claim a task until the authoritative record is durably updated.
        lease = {'run': run, 'task': key, 'actor': actor, 'session': session,
                 'worktree': str(tree), 'base_commit': git(tree, 'rev-parse', 'HEAD')}
        atomic_json(self.state / 'runs' / (run + '.json'), lease)
        task.update(status='running', implementation={'actor': actor, 'session': session, 'run': run},
                    evidence=[], verification=None)
        self.save(record)
        return self.packet(records, key)

    def own(self, task, session):
        require(task['implementation'] and task['implementation']['session'] == session, 'Another session owns this task')
        require(task['status'] in ACTIVE, 'Task is not active')

    def decide(self, records, feature, result):
        require(feature in records, 'Unknown feature')
        record = records[feature]
        require(not any(t['status'] in ACTIVE for t in record['tasks']), 'Cannot replace an active decision')
        require(result['proposal_sha256'] == file_hash(self.root, record['proposal']), 'Review used a stale proposal')
        require(result['scope_sha256'] == scope_digest(record), 'Review used stale task/acceptance scope')
        require(result['requirements_sha256'] == snapshot(self.root, record['requirements']), 'Review used stale requirements')
        record['decision'] = result
        self.validate_schema_and_records(records)
        self.save(record)
        return result

    def validate_schema_and_records(self, records):
        for record in records.values():
            errors = list(self.validator.iter_errors(record))
            require(not errors, errors[0].message if errors else '')
        self.validate(records)

    def submit(self, records, key, session, evidence):
        record, task = self.lookup(records, key)
        self.own(task, session)
        require(task['status'] == 'running', 'Only running work can be submitted')
        require(not self.decision_problem(record), 'Approval changed during implementation')
        tree = self.worktree(self.lease(task)['worktree'])
        task.update(evidence=evidence, verification=None, status='review')
        self.validate_schema_and_records(records)
        self.check_evidence(task, tree)
        require({e['check'] for e in evidence} == set(task['checks']), 'Submission lacks required evidence')
        self.review_tree(task, tree)
        self.save(record)
        return {'task': key, 'status': 'review', 'evidence_sha256': digest_json(evidence)}

    @staticmethod
    def check_evidence(task, root):
        for evidence in task['evidence']:
            require(evidence['document_sha256'] == file_hash(root, evidence['document']), 'Evidence document changed/missing')
            require(evidence['source_sha256'] == snapshot(root, evidence['source_sha256']), 'Verified source changed/missing')

    def check_committed_evidence(self, task):
        for evidence in task['evidence']:
            for name, sha in {evidence['document']: evidence['document_sha256'], **evidence['source_sha256']}.items():
                blob = subprocess.check_output(['git', '-C', str(self.root), 'show', evidence['source_commit'] + ':' + name])
                require(digest_bytes(blob) == sha, 'Historical evidence does not match its recorded commit')

    def review_tree(self, task, tree):
        require(not git(tree, 'status', '--porcelain'), 'Commit the complete implementation before review')
        commit = git(tree, 'rev-parse', 'HEAD')
        require(all(e['source_commit'] == commit for e in task['evidence']),
                'Evidence must bind the complete implementation commit')
        self.check_committed_evidence(task)
        return commit

    def verify(self, records, key, result):
        record, task = self.lookup(records, key)
        require(task['status'] == 'review', 'Task is not awaiting verification')
        require(not self.decision_problem(record), 'Approval changed before verification')
        tree = self.worktree(self.lease(task)['worktree'])
        self.check_evidence(task, tree)
        self.review_tree(task, tree)
        task['verification'] = result
        self.validate_schema_and_records(records)
        if result['outcome'] == 'failed':
            task['status'] = 'blocked'
            task['blocker'] = result['rationale']
            task['repeats'] += 1
        self.save(record)
        return {'task': key, 'verification': result['outcome']}

    def complete(self, records, key, session):
        record, task = self.lookup(records, key)
        self.own(task, session)
        require(task['status'] == 'review' and task['verification'] and
                task['verification']['outcome'] == 'passed', 'Passing independent verification required')
        require(not self.decision_problem(record), 'Approval changed before integration')
        self.check_evidence(task, self.root)
        self.check_committed_evidence(task)
        reviewed = task['evidence'][0]['source_commit']
        require(subprocess.run(['git', '-C', str(self.root), 'merge-base', '--is-ancestor',
                                reviewed, 'HEAD'], check=False).returncode == 0,
                'Preserve the reviewed commit in integration history; otherwise review the replacement commit')
        changed = subprocess.check_output(['git', '-C', str(self.root), 'diff', '--name-only',
                                           '--no-renames', '-z', reviewed, 'HEAD']).decode().split('\0')
        require(all(not name or re.fullmatch(r'docs/features/[^/]+/record\.json', name) for name in changed),
                'Integrated source tree differs from reviewed commit outside workflow bookkeeping')
        dirty = subprocess.check_output(['git', '-C', str(self.root), 'diff', '--name-only',
                                         '--no-renames', '-z', 'HEAD']).decode().split('\0')
        dirty += subprocess.check_output(['git', '-C', str(self.root), 'ls-files', '--others',
                                          '--exclude-standard', '-z']).decode().split('\0')
        require(all(not name or re.fullmatch(r'docs/features/[^/]+/record\.json', name) for name in dirty),
                'Uncommitted integration changes require review')
        # Completed evidence must be in the integrated commit, not only in a dirty
        # worktree or an ignored report that disappears in the next checkout.
        for evidence in task['evidence']:
            for name, sha in {evidence['document']: evidence['document_sha256'], **evidence['source_sha256']}.items():
                blob = subprocess.check_output(['git', '-C', str(self.root), 'show', 'HEAD:' + name])
                require(digest_bytes(blob) == sha, 'Commit reviewed source/evidence before completion')
        task['status'] = 'done'
        self.validate_schema_and_records(records)
        self.save(record)
        return {'task': key, 'status': 'done', 'next': self.select(records)}

    def block(self, records, key, session, reason):
        require(reason.strip(), 'A blocking reason is required')
        record, task = self.lookup(records, key)
        require(task['status'] != 'done', 'Completed work cannot be blocked')
        if task['status'] in ACTIVE:
            self.own(task, session)
        task.update(status='blocked', blocker=reason)
        self.save(record)
        return {'task': key, 'status': 'blocked', 'next': self.select(records)}

    def resume(self, records, key, reason):
        record, task = self.lookup(records, key)
        require(task['status'] == 'blocked', 'Only blocked tasks can resume')
        require(task['environment'] == 'offline', 'Physical tasks use the canonical human workflow')
        require(reason.strip(), 'Record changed evidence or method before resuming')
        repeats = 0 if reason != task['resumption'] else task['repeats']
        task.update(status='pending', blocker=None, repeats=repeats, evidence=[], verification=None,
                    implementation=None, resumption=reason)
        self.save(record)
        return {'task': key, 'status': 'pending', 'next': self.select(records)}

    def recover(self, records, key, reason, previous_session_stopped=False, expected_run=None):
        record, task = self.lookup(records, key)
        require(task['status'] in ACTIVE, 'Only interrupted active work needs recovery')
        require(previous_session_stopped is True and reason.strip(),
                'Inspect and stop the previous session, then attest --previous-session-stopped with a reason')
        require(task['implementation']['run'] == expected_run, 'Recovery attestation belongs to another run')
        # Deliberately never use a timeout/PID as permission to steal work.
        # Operator must inspect/stop the previous session before --execute.
        task.update(status='blocked', blocker='Interrupted run: ' + reason)
        self.save(record)
        return {'task': key, 'status': 'blocked', 'preserved_run': task['implementation']['run'],
                'next': self.select(records)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=REPO)
    parser.add_argument('--execute', action='store_true', help='Apply the explicitly requested record mutation')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'status', 'next', 'runs'):
        sub.add_parser(name)
    packet = sub.add_parser('packet'); packet.add_argument('task')
    context = sub.add_parser('review-context'); context.add_argument('feature')
    evaluation = sub.add_parser('check-review-cases'); evaluation.add_argument('--result', type=Path, required=True)
    hashes = sub.add_parser('hash'); hashes.add_argument('paths', nargs='+')
    decision = sub.add_parser('decide'); decision.add_argument('feature'); decision.add_argument('--result', type=Path, required=True)
    claim = sub.add_parser('claim'); claim.add_argument('task'); claim.add_argument('--actor', required=True)
    claim.add_argument('--session', required=True); claim.add_argument('--worktree', type=Path, required=True)
    submit = sub.add_parser('submit'); submit.add_argument('task'); submit.add_argument('--session', required=True)
    submit.add_argument('--evidence', type=Path, required=True)
    verify = sub.add_parser('verify'); verify.add_argument('task'); verify.add_argument('--result', type=Path, required=True)
    complete = sub.add_parser('complete'); complete.add_argument('task'); complete.add_argument('--session', required=True)
    block = sub.add_parser('block'); block.add_argument('task'); block.add_argument('--session', default='')
    block.add_argument('--reason', required=True)
    resume = sub.add_parser('resume'); resume.add_argument('task'); resume.add_argument('--reason', required=True)
    recover = sub.add_parser('recover'); recover.add_argument('task'); recover.add_argument('--reason', required=True)
    recover.add_argument('--previous-session-stopped', action='store_true')
    recover.add_argument('--expected-run', required=True)
    args = parser.parse_args(argv)
    try:
        workflow = Workflow(args.repo)
        if args.command == 'check-review-cases':
            output = check_review_cases(read_json(args.result))
        elif args.command == 'hash':
            output = snapshot(workflow.checkout, args.paths)
        elif args.command in ('validate', 'status', 'next', 'packet', 'runs', 'review-context'):
            records = workflow.load()
            if args.command == 'validate':
                output = {'valid': True, 'features': len(records), 'tasks': len(workflow.task_map(records)),
                          'next': workflow.select(records)}
            elif args.command == 'status':
                output = workflow.status(records)
            elif args.command == 'next':
                output = workflow.select(records)
            elif args.command == 'runs':
                active = {t['implementation']['run'] for _, t in workflow.task_map(records).values()
                          if t['status'] in ACTIVE}
                output = [{'lease': read_json(p), 'active': p.stem in active}
                          for p in sorted((workflow.state / 'runs').glob('*.json')) if not p.is_symlink()]
            elif args.command == 'review-context':
                require(args.feature in records, 'Unknown feature')
                record = records[args.feature]
                output = {'feature': record['id'], 'author': record['author'],
                          'scope_sha256': scope_digest(record),
                          'proposal_sha256': file_hash(workflow.root, record['proposal']),
                          'requirements_sha256': snapshot(workflow.root, record['requirements'])}
            else:
                output = workflow.packet(records, args.task)
        elif not args.execute:
            output = {'inspection_only': True, 'action': args.command,
                      'instruction': 'Review inputs, then repeat with --execute before the subcommand.'}
        else:
            with workflow.locked():
                records = workflow.load()
                if args.command == 'decide':
                    output = workflow.decide(records, args.feature, read_json(args.result))
                elif args.command == 'claim':
                    output = workflow.claim(records, args.task, args.actor, args.session, args.worktree)
                elif args.command == 'submit':
                    output = workflow.submit(records, args.task, args.session, read_json(args.evidence))
                elif args.command == 'verify':
                    output = workflow.verify(records, args.task, read_json(args.result))
                elif args.command == 'complete':
                    output = workflow.complete(records, args.task, args.session)
                elif args.command == 'block':
                    output = workflow.block(records, args.task, args.session, args.reason)
                elif args.command == 'resume':
                    output = workflow.resume(records, args.task, args.reason)
                else:
                    output = workflow.recover(records, args.task, args.reason, args.previous_session_stopped, args.expected_run)
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (WorkflowError, OSError, json.JSONDecodeError, subprocess.CalledProcessError, KeyError, TypeError) as exc:
        print(f'feature-workflow: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
