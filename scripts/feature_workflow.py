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
ACTIVE = {'running', 'review', 'validated'}
PRIVATE = {'local', 'backups', 'artifacts', 'build', 'dist', '.git', '.venv'}
# These tracked project policies are public evidence, unlike personal Codex state.
PUBLIC_CODEX_FILES = frozenset({
    '.codex/README.md', '.codex/config.toml',
    '.codex/agent-guide.md', '.codex/current-goals.md',
})


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
    excluded = {'decision', 'tasks'}
    fields = ('id', 'title', 'environment', 'depends_on', 'checks', 'human_task')
    if record.get('format_version', 1) == 2:
        excluded |= {'authorization', 'requirement_rechecks'}
        fields += ('review_policy', 'review_reason', 'hazards', 'owned_paths', 'input_paths')
    scope = {key: value for key, value in record.items() if key not in excluded}
    scope['tasks'] = [{key: task[key] for key in fields} for task in record['tasks']]
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
        require(str(relative) in PUBLIC_CODEX_FILES or len(relative.parts) == 3 and
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
        v2 = read_json(REPO / '.codex/schemas/feature-record-v2.schema.json')
        Draft202012Validator.check_schema(v2)
        self.validators = {1: self.validator, 2: Draft202012Validator(v2)}

    def validator_for(self, record):
        version = record.get('format_version')
        require(type(version) is int and version in self.validators, 'Unsupported record version')
        return self.validators[version]

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
            errors = sorted(self.validator_for(record).iter_errors(record), key=lambda e: str(e.path))
            require(not errors, f'{path.parent.name}: {errors[0].message if errors else ""}')
            require(record['id'] == path.parent.name, 'Feature ID and directory differ')
            require(record['id'] not in records, 'Duplicate feature ID')
            records[record['id']] = record
        self.validate(records)
        return records

    def save(self, record):
        errors = list(self.validator_for(record).iter_errors(record))
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
            if record['format_version'] == 2:
                self.validate_development(record)
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
                    if task['status'] == 'running':
                        active.append(key)
                    require(task['implementation'] is not None, 'Active task has no owner')
                    require((record['format_version'] == 2 and record['authorization']) or
                            decision and decision['outcome'] in APPROVED, 'Active task lacks approval')
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
                    if record['format_version'] == 1:
                        require(decision and task['verification']['decision_sha256'] == digest_json(decision),
                                'Verification belongs to a different approved decision')
                    else:
                        require(task['verification']['basis_sha256'] == self.basis_digest(record),
                                'Verification belongs to a different authorization')
                    require(task['implementation'] and task['verification']['reviewer'] != task['implementation']['actor']
                            and task['verification']['session'] != task['implementation']['session'],
                            'Implementation needs a separate verifier session')
                    require(task['verification']['evidence_sha256'] == digest_json(task['evidence']),
                            'Verification is stale for the submitted evidence')
                if task['status'] == 'done':
                    if record['format_version'] == 1 or task['review_policy'] != 'self':
                        require(task['verification'] and task['verification']['outcome'] == 'passed',
                                'Done task lacks passing independent review')
                    require({e['check'] for e in task['evidence']} == set(task['checks']), 'Done task lacks required evidence')
                    require(all(tasks[d][1]['status'] == 'done' for d in task['depends_on']), 'Done task has unfinished dependency')
                    # Completed tasks retain evidence of their integrated
                    # revision. Later approved work may change those files;
                    # status reports that evidence as historical, never current.
                    self.check_committed_evidence(task)
        require(len(active) <= 1, 'Only one running implementation is allowed')
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
        if record.get('format_version', 1) == 2:
            return self.authorization_problem(record)
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
        active = any(t['status'] == 'running' for _, t in tasks.values())
        for key, (record, task) in tasks.items():
            reason = None
            if task['status'] != 'pending':
                reason = task['blocker'] or task['status']
            elif task['environment'] != 'offline':
                reason = 'Human/hardware task: ' + task['human_task']
            elif active:
                reason = 'Another task is active'
            elif self.reservation_problem(records, key):
                reason = self.reservation_problem(records, key)
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
                           'created': record['created'], 'evidence_matches_checkout': current_evidence,
                           'completion_basis': (task['review_policy'] if record['format_version'] == 2
                                                else 'legacy-independent')})
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
                'basis_sha256': self.basis_digest(record),
                'instruction': 'Apply AGENTS.md and the assigned role; read only relevant task evidence. Work on this '
                'authorized offline task within the assigned role and file ownership. '
                'Use bounded self-service diagnostics only in coordinator-assigned scratch '
                'space with the remaining allowance; return actual check results under the recorded review policy. '
                'Do not contact printer hardware, change shared records, commit, publish '
                'or spawn agents. After completion/blocking, the coordinator selects the next ready task.'}

    @staticmethod
    def basis_digest(record):
        if record.get('format_version', 1) == 1:
            return digest_json(record['decision'])
        return digest_json({'authorization': record['authorization'], 'decision': record['decision']})

    @staticmethod
    def covered(name, paths):
        """Exact files or explicitly slash-terminated input subtrees; no glob expansion."""
        return any(name == p.rstrip('/') or p.endswith('/') and name.startswith(p) for p in paths)

    def protected_paths(self, record, task):
        paths = [record['proposal'], *record['requirements']]
        if record['format_version'] == 2:
            paths += task['owned_paths'] + task['input_paths']
        for evidence in task['evidence']:
            paths += [evidence['document'], *evidence['source_sha256']]
        return sorted({p.split('#', 1)[0] for p in paths})

    def reservation_problem(self, records, key):
        record, task = self.lookup(records, key)
        for other_key, (other_record, other) in self.task_map(records).items():
            if other_key == key or other['status'] not in {'review', 'validated'}:
                continue
            # Legacy records have no explicit write/read footprint. Do not silently
            # reinterpret their original whole-tree review contract.
            if record['format_version'] == 1 or other_record['format_version'] == 1:
                return 'Legacy review reserves the source tree: ' + other_key
            if (any(self.covered(p, self.protected_paths(other_record, other)) for p in task['owned_paths']) or
                    any(self.covered(p, self.protected_paths(record, task)) for p in other['owned_paths'])):
                return 'Source/input reservation overlaps frozen candidate: ' + other_key
        return None

    def effective_requirements(self, record):
        """Retain original authorization/decision hashes; replay explicit nonmaterial rechecks."""
        authorization = record['authorization']
        require(authorization is not None, 'Missing development authorization')
        current = authorization['requirements_sha256']
        for entry in record['requirement_rechecks']:
            require(entry['basis_sha256'] == self.basis_digest(record) and entry['from_sha256'] == current,
                    'Requirement recheck belongs to another basis or snapshot')
            require(set(entry['to_sha256']) == set(current), 'Requirement recheck changed reference scope')
            changed = [name for name in current if current[name] != entry['to_sha256'][name]]
            require(changed and all(name.split('#', 1)[0].endswith('.md') for name in changed),
                    'Only nonmaterial requirement-document changes may be rechecked')
            require(authorization['reference'] not in changed, 'Changed authorization reference needs new authorization')
            for name in changed:
                blob = subprocess.check_output(['git', '-C', str(self.root), 'show',
                                                entry['source_commit'] + ':' + name.split('#', 1)[0]])
                require(digest_bytes(blob) == entry['to_sha256'][name], 'Recheck document does not match its commit')
            current = entry['to_sha256']
        return current

    def validate_development(self, record):
        authorization = record['authorization']
        if authorization:
            require(authorization['reference'] in record['requirements'], 'Authorization reference must be a requirement')
            require(authorization['reference_sha256'] == authorization['requirements_sha256'][authorization['reference']],
                    'Authorization reference hash differs')
            require(set(authorization['requirements_sha256']) == set(record['requirements']),
                    'Authorization must bind all requirements')
            require(not record['owner_decision_required'] or authorization['basis'] == 'owner-request',
                    'This scope needs an owner request, not standing authority')
            self.effective_requirements(record)
        else:
            require(not record['requirement_rechecks'], 'Recheck needs authorization')
        checks = {c['id']: c for c in record['checks']}
        for task in record['tasks']:
            require(task['review_reason'].strip(), 'Explain the task review route')
            require(all(checks[c]['environment'] == task['environment'] for c in task['checks'] if c in checks),
                    'Separate offline and physical acceptance tasks')
            require(len(task['evidence']) == len({e['check'] for e in task['evidence']}),
                    'Duplicate acceptance evidence')
            for name in task['owned_paths'] + task['input_paths']:
                public_path(self.root, name, exists=False)
                require(not any(c in name for c in '#*?[]') and name.rstrip('/') == str(Path(name)),
                        'Use canonical source paths without wildcard patterns')
            for name in task['owned_paths']:
                tracked = git(self.root, 'ls-files', '--stage', '--', ':(literal)' + name)
                require(not name.endswith('/') and (not (self.root / name).is_dir() or tracked.startswith('160000 ')),
                        'Owned paths must name files or gitlinks')
                require(not re.fullmatch(r'docs/features/[^/]+/record\.json', name), 'Workers cannot own queue records')
                require(name != record['proposal'], 'Workers cannot change their authorized proposal')
            require(not task['hazards'] or task['review_policy'] == 'consequential',
                    'Declared serious-loss hazards require consequential review')
            if task['validation']:
                result = task['validation']
                require(authorization and authorization['scope_sha256'] == scope_digest(record),
                        'Validated task scope or review policy changed')
                require(result['basis_sha256'] == self.basis_digest(record), 'Validation belongs to another authorization')
                require(task['implementation'] and result['actor'] == task['implementation']['actor'] and
                        result['session'] == task['implementation']['session'], 'Validation must identify the actual implementer')
                require(result['evidence_sha256'] == digest_json(task['evidence']), 'Validation evidence is stale')
                require(task['evidence'] and all(e['source_commit'] == result['source_commit'] for e in task['evidence']),
                        'Validation must bind the complete candidate commit')
            if task['status'] in {'review', 'validated', 'done'}:
                require(task['validation'], 'Submitted task needs actual check validation')
            if task['status'] == 'validated':
                require(task['review_policy'] == 'self' and task['verification'] is None,
                        'Independent review cannot be bypassed with validated status')
            if task['review_policy'] == 'self':
                require(task['verification'] is None, 'Self-validation must not impersonate independent review')

    def authorization_problem(self, record):
        authorization = record['authorization']
        if not authorization:
            return 'Awaiting recorded owner request or standing authorization'
        decision = record['decision']
        if decision and decision['outcome'] not in APPROVED:
            return 'Unresolved requested design review'
        for basis in [authorization] + ([decision] if decision else []):
            if basis['proposal_sha256'] != file_hash(self.root, record['proposal']):
                return 'Proposal changed since authorization'
            if basis['scope_sha256'] != scope_digest(record):
                return 'Task, acceptance or review scope changed since authorization'
        if decision and decision['requirements_sha256'] != authorization['requirements_sha256']:
            return 'Design review and authorization use different requirement snapshots'
        if self.effective_requirements(record) != snapshot(self.root, record['requirements']):
            return 'Requirement sources changed: assess relevance or renew authorization'
        return None

    def authorize(self, records, feature, actor, session, basis, reference, reason):
        require(feature in records, 'Unknown feature')
        record = records[feature]
        require(record['format_version'] == 2, 'Use a version 2 record for development authorization')
        require(actor.strip() and session.strip() and reason.strip(), 'Actor, session and rationale are required')
        require(basis in {'standing', 'owner-request'}, 'Invalid authorization basis')
        require(all(t['status'] == 'pending' and not t['implementation'] and not t['evidence']
                    for t in record['tasks']), 'Do not replace live or historical authorization')
        require(reference in record['requirements'], 'Include the authorization reference in requirements')
        if record['authorization']:
            # Before replacement, the prior basis must have a durable Git record.
            previous = json.loads(subprocess.check_output(['git', '-C', str(self.root), 'show',
                                                          'HEAD:docs/features/' + feature + '/record.json']))
            require(previous['authorization'] == record['authorization'], 'Commit prior authorization before replacing it')
        record['authorization'] = {
            'actor': actor, 'session': session, 'basis': basis, 'reference': reference,
            'reference_sha256': file_hash(self.root, reference), 'rationale': reason,
            'source_commit': git(self.root, 'rev-parse', 'HEAD'),
            'proposal_sha256': file_hash(self.root, record['proposal']),
            'requirements_sha256': snapshot(self.root, record['requirements']), 'scope_sha256': scope_digest(record)}
        record['requirement_rechecks'] = []
        for name, expected in {record['proposal']: record['authorization']['proposal_sha256'],
                               **record['authorization']['requirements_sha256']}.items():
            blob = subprocess.check_output(['git', '-C', str(self.root), 'show',
                                            'HEAD:' + name.split('#', 1)[0]])
            require(digest_bytes(blob) == expected, 'Commit scope and requirement sources before authorization')
        self.validate_schema_and_records(records)
        require(not self.authorization_problem(record), 'Resolve changed or rejected design review before authorization')
        self.save(record)
        return {'feature': feature, 'authorization': record['authorization'], 'basis_sha256': self.basis_digest(record)}

    def recheck_requirements(self, records, feature, actor, session, expected, reason):
        require(feature in records, 'Unknown feature')
        record = records[feature]
        require(record['format_version'] == 2, 'Legacy requirement hashes are not rewritten')
        require(actor.strip() and session.strip() and reason.strip(), 'Record who assessed the change and why it is nonmaterial')
        require(any(t['status'] != 'done' for t in record['tasks']), 'Do not recheck completed historical records')
        old = self.effective_requirements(record)
        require(expected == digest_json(old), 'Stale requirement recheck request')
        require(record['authorization']['scope_sha256'] == scope_digest(record) and
                record['authorization']['proposal_sha256'] == file_hash(self.root, record['proposal']),
                'A requirement recheck cannot change task or proposal scope')
        record['requirement_rechecks'].append({
            'actor': actor, 'session': session, 'rationale': reason, 'basis_sha256': self.basis_digest(record),
            'from_sha256': old, 'to_sha256': snapshot(self.root, record['requirements']),
            'source_commit': git(self.root, 'rev-parse', 'HEAD')})
        self.validate_schema_and_records(records)
        self.save(record)
        return {'feature': feature, 'requirement_recheck': record['requirement_rechecks'][-1]}

    def check_candidate_scope(self, record, task, tree):
        base = self.lease(task)['base_commit']
        require(subprocess.run(['git', '-C', str(tree), 'merge-base', '--is-ancestor', base, 'HEAD'],
                               check=False).returncode == 0, 'Candidate must preserve its assigned base')
        changed = subprocess.check_output(['git', '-C', str(tree), 'diff', '--name-only',
                                           '--no-renames', '-z', base, 'HEAD']).decode().split('\0')
        require(all(not name or name in task['owned_paths'] for name in changed),
                'Candidate changed files outside assigned ownership')

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
        for other_record, other in self.task_map(records).values():
            if other['status'] in ACTIVE:
                require(self.worktree(self.lease(other)['worktree']) != tree,
                        'Worktree is reserved by another task')
        run = uuid.uuid4().hex
        # A crash after the lease write preserves an orphan for inspection; it
        # cannot claim a task until the authoritative record is durably updated.
        lease = {'run': run, 'task': key, 'actor': actor, 'session': session,
                 'worktree': str(tree), 'base_commit': git(tree, 'rev-parse', 'HEAD')}
        atomic_json(self.state / 'runs' / (run + '.json'), lease)
        if record['format_version'] == 2:
            task['validation'] = None
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
            errors = list(self.validator_for(record).iter_errors(record))
            require(not errors, errors[0].message if errors else '')
        self.validate(records)

    def submit(self, records, key, session, evidence, checks_passed=False, reason=''):
        record, task = self.lookup(records, key)
        self.own(task, session)
        require(task['status'] == 'running', 'Only running work can be submitted')
        require(not self.decision_problem(record), 'Approval changed during implementation')
        tree = self.worktree(self.lease(task)['worktree'])
        require(record['format_version'] == 2 or not checks_passed,
                'Self-validation is unavailable for legacy records')
        task.update(evidence=evidence, verification=None, status='review')
        if record['format_version'] == 2:
            require(checks_passed and reason.strip(), 'Attest actual checks with --checks-passed and --reason')
            self.check_candidate_scope(record, task, tree)
            task['validation'] = {
                'actor': task['implementation']['actor'], 'session': session, 'outcome': 'passed',
                'rationale': reason, 'basis_sha256': self.basis_digest(record),
                'evidence_sha256': digest_json(evidence), 'source_commit': git(tree, 'rev-parse', 'HEAD')}
            if task['review_policy'] == 'self':
                task['status'] = 'validated'
        self.validate_schema_and_records(records)
        self.check_evidence(task, tree)
        require({e['check'] for e in evidence} == set(task['checks']), 'Submission lacks required evidence')
        self.review_tree(task, tree)
        self.save(record)
        return {'task': key, 'status': task['status'], 'evidence_sha256': digest_json(evidence)}

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
        if record['format_version'] == 2:
            self.check_candidate_scope(record, task, tree)
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
        if record['format_version'] == 2 and task['review_policy'] == 'self':
            require(task['status'] == 'validated' and task['validation'], 'Passing self-validation required')
        else:
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
        if record['format_version'] == 1:
            require(all(not name or re.fullmatch(r'docs/features/[^/]+/record\.json', name) for name in changed),
                    'Integrated source tree differs from reviewed commit outside workflow bookkeeping')
        else:
            tree = self.worktree(self.lease(task)['worktree'])
            self.review_tree(task, tree)
            self.check_candidate_scope(record, task, tree)
            protected = self.protected_paths(record, task)
            # Only acknowledged, nonmaterial requirement-document changes can be excluded.
            strong = task['owned_paths'] + task['input_paths'] + [record['proposal']]
            for evidence in task['evidence']:
                strong += [evidence['document'], *evidence['source_sha256']]
            rechecked = {name.split('#', 1)[0] for r in record['requirement_rechecks']
                         for name in r['to_sha256'] if r['from_sha256'][name] != r['to_sha256'][name]}
            protected = [p for p in protected if p not in rechecked or self.covered(p, strong)]
            require(not any(name and self.covered(name, protected) for name in changed),
                    'Relevant integrated source changed; rerun affected validation/review')
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
        if record['format_version'] == 2:
            task['validation'] = None
        self.save(record)
        return {'task': key, 'status': 'pending', 'next': self.select(records)}

    def recover(self, records, key, reason, previous_session_stopped=False, expected_run=None):
        record, task = self.lookup(records, key)
        require(task['status'] in ACTIVE, 'Only interrupted active work needs recovery')
        require(previous_session_stopped is True and reason.strip(),
                'Inspect and stop the previous session, then attest --previous-session-stopped with a reason')
        require(task['implementation']['run'] == expected_run, 'Recovery attestation belongs to another run')
        # Deliberately never use a timeout/PID as permission to steal work.
        # Operator must inspect/stop the previous session, then attest --previous-session-stopped with a reason.
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
    submit.add_argument('--checks-passed', action='store_true', help='Attest observed check success; not independent review')
    submit.add_argument('--reason', default='')
    authorize = sub.add_parser('authorize'); authorize.add_argument('feature')
    authorize.add_argument('--actor', required=True); authorize.add_argument('--session', required=True)
    authorize.add_argument('--basis', choices=('standing', 'owner-request'), required=True)
    authorize.add_argument('--reference', required=True); authorize.add_argument('--reason', required=True)
    recheck = sub.add_parser('recheck-requirements'); recheck.add_argument('feature')
    recheck.add_argument('--actor', required=True); recheck.add_argument('--session', required=True)
    recheck.add_argument('--expected-sha256', required=True); recheck.add_argument('--reason', required=True)
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
                          'requirements_sha256': snapshot(workflow.root, record['requirements']),
                          'basis_sha256': workflow.basis_digest(record)}
                if record['format_version'] == 2 and record['authorization']:
                    output['previous_requirements_sha256'] = workflow.effective_requirements(record)
                    output['expected_recheck_sha256'] = digest_json(output['previous_requirements_sha256'])
            else:
                output = workflow.packet(records, args.task)
        elif not args.execute:
            output = {'inspection_only': True, 'action': args.command,
                      'instruction': 'Review inputs, then repeat with --execute before the subcommand.'}
        else:
            with workflow.locked():
                records = workflow.load()
                if args.command == 'authorize':
                    output = workflow.authorize(records, args.feature, args.actor, args.session,
                                                args.basis, args.reference, args.reason)
                elif args.command == 'recheck-requirements':
                    output = workflow.recheck_requirements(records, args.feature, args.actor, args.session,
                                                           args.expected_sha256, args.reason)
                elif args.command == 'decide':
                    output = workflow.decide(records, args.feature, read_json(args.result))
                elif args.command == 'claim':
                    output = workflow.claim(records, args.task, args.actor, args.session, args.worktree)
                elif args.command == 'submit':
                    output = workflow.submit(records, args.task, args.session, read_json(args.evidence), args.checks_passed, args.reason)
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
