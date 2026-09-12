from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from feature_workflow import Workflow, WorkflowError, atomic_json, digest_bytes, digest_json, file_hash, main, read_json, snapshot, scope_digest, check_review_cases


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run_git('init', '-q')
        (self.root / '.gitignore').write_text('/local/\n')
        (self.root / 'requirements.md').write_text('Preserve data, default immutable, factory storage.\n')
        (self.root / 'human.md').write_text('# Physical acceptance\nKeep the printer offline.\n')
        self.workflow = Workflow(self.root)

    def run_git(self, *args, root=None):
        return subprocess.check_output(['git', '-C', str(root or self.root), *args], text=True,
                                       stderr=subprocess.DEVNULL).strip()

    def commit(self, root=None):
        self.run_git('add', '.', root=root)
        self.run_git('-c', 'user.name=Workflow Test', '-c', 'user.email=test@example.invalid',
                     'commit', '-qm', 'fixture', '--allow-empty', root=root)
        return self.run_git('rev-parse', 'HEAD', root=root)

    def feature(self, name='export', *, hardware=False, approved=True):
        directory = self.root / 'docs/features' / name
        directory.mkdir(parents=True)
        (directory / 'proposal.md').write_text('Complete an accepted export workflow.\n')
        (self.root / (name + '.py')).write_text('value = 1\n')
        (self.root / (name + '-evidence.md')).write_text('Offline fixture preserves the source.\n')
        environment = 'hardware' if hardware else 'offline'
        record = {'format_version': 1, 'id': name, 'kind': 'feature', 'title': 'Export user data',
                  'author': 'suggester', 'created': '2026-09-11', 'priority': 2,
                  'proposal': f'docs/features/{name}/proposal.md', 'requirements': ['requirements.md'],
                  'owner_decision_required': False, 'decision': None,
                  'checks': [{'id': 'preserves-data', 'description': 'Source remains unchanged', 'environment': environment}],
                  'tasks': [{'id': 'implement', 'title': 'Complete export fixture', 'status': 'pending',
                             'environment': environment, 'depends_on': [], 'checks': ['preserves-data'],
                             'human_task': 'human.md' if hardware else None, 'blocker': None,
                             'implementation': None, 'evidence': [], 'verification': None,
                             'repeats': 0, 'resumption': None}]}
        if approved:
            record['decision'] = self.decision(record)
        self.workflow.save(record)
        return record

    def decision(self, record):
        return {'outcome': 'approved', 'reviewer': 'approver', 'session': 'review-1', 'authority': 'delegated',
                'rationale': 'Bounded accepted export behavior with preservation checks.',
                'proposal_sha256': file_hash(self.root, record['proposal']),
                'scope_sha256': scope_digest(record),
                'requirements_sha256': snapshot(self.root, record['requirements']), 'constraints': []}

    def tree(self, name='worker'):
        path = self.workflow.state / 'worktrees' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self.run_git('worktree', 'add', '-q', '-b', name, str(path))
        return path

    def claim(self, records, key='export:implement', tree=None):
        tree = tree or self.tree()
        with self.workflow.locked():
            packet = self.workflow.claim(records, key, 'implementer', 'implementation-session', tree)
        return tree, packet

    def evidence(self, tree, name='export'):
        return [{'check': 'preserves-data', 'environment': 'offline', 'document': name + '-evidence.md',
                 'document_sha256': file_hash(tree, name + '-evidence.md'),
                 'source_sha256': snapshot(tree, [name + '.py']),
                 'source_commit': self.run_git('rev-parse', 'HEAD', root=tree),
                 'method': 'Disposable filesystem fixture', 'limitations': 'No physical printer used.',
                 'profile': None, 'board_revision': None}]

    def verification(self, evidence, *, outcome='passed'):
        return {'outcome': outcome, 'reviewer': 'verifier', 'session': 'verification-session',
                'rationale': 'Independent fixture evidence inspected.', 'evidence_sha256': digest_json(evidence),
                'decision_sha256': digest_json(self.workflow.load()['export']['decision'])}

    def submitted(self):
        self.feature(); self.commit()
        records = self.workflow.load(); tree, _ = self.claim(records)
        evidence = self.evidence(tree)
        self.workflow.submit(records, 'export:implement', 'implementation-session', evidence)
        return self.workflow.load(), tree, evidence

    def test_hardware_dependency_does_not_stop_independent_offline_work(self):
        physical = self.feature('physical', hardware=True)
        offline = self.feature()
        records = self.workflow.load()
        self.assertEqual(self.workflow.select(records)['task'], 'export:implement')
        offline['tasks'][0]['depends_on'] = ['physical:implement']
        self.workflow.save(offline)
        self.assertIsNone(self.workflow.select(self.workflow.load()))
        physical['tasks'][0].update(status='blocked', blocker='Await owner availability; human.md')
        self.workflow.save(physical)
        another = self.feature('other')
        self.assertEqual(self.workflow.select(self.workflow.load())['task'], 'other:implement')

    def test_missing_stale_and_self_approval_do_not_dispatch(self):
        record = self.feature(approved=False)
        self.assertIsNone(self.workflow.select(self.workflow.load()))
        record['decision'] = self.decision(record); self.workflow.save(record)
        (self.root / record['proposal']).write_text('Changed proposal scope')
        self.assertIsNone(self.workflow.select(self.workflow.load()))
        record['decision'] = self.decision(record); self.workflow.save(record)
        (self.root / 'requirements.md').write_text('Changed accepted requirement')
        self.assertIsNone(self.workflow.select(self.workflow.load()))
        record['decision'] = self.decision(record); record['decision']['reviewer'] = record['author']
        self.workflow.save(record)
        with self.assertRaisesRegex(WorkflowError, 'Author'):
            self.workflow.load()

    def test_decision_import_rejects_stale_output_and_owner_scope(self):
        record = self.feature(approved=False)
        result = self.decision(record); result['proposal_sha256'] = '0' * 64
        with self.assertRaisesRegex(WorkflowError, 'stale'):
            self.workflow.decide(self.workflow.load(), 'export', result)
        record['owner_decision_required'] = True; self.workflow.save(record)
        with self.assertRaisesRegex(WorkflowError, 'owner decision'):
            self.workflow.decide(self.workflow.load(), 'export', self.decision(record))
        self.assertIsNone(self.workflow.load()['export']['decision'])

    def test_constraints_need_real_acceptance_checks(self):
        record = self.feature(); record['decision']['outcome'] = 'approved-with-constraints'
        self.workflow.save(record)
        with self.assertRaisesRegex(WorkflowError, 'observable constraints'):
            self.workflow.load()
        record['decision']['constraints'] = [{'text': 'Preserve source', 'checks': ['missing']}]
        self.workflow.save(record)
        with self.assertRaisesRegex(WorkflowError, 'unknown acceptance'):
            self.workflow.load()

    def test_cycle_and_unknown_dependency_are_rejected(self):
        first = self.feature('first'); second = self.feature('second')
        first['tasks'][0]['depends_on'] = ['missing:implement']; self.workflow.save(first)
        with self.assertRaisesRegex(WorkflowError, 'Unknown task dependency'):
            self.workflow.load()
        first['tasks'][0]['depends_on'] = ['second:implement']
        second['tasks'][0]['depends_on'] = ['first:implement']
        self.workflow.save(first); self.workflow.save(second)
        with self.assertRaisesRegex(WorkflowError, 'cycle'):
            self.workflow.load()

    def test_queue_cap_and_oldest_within_priority(self):
        for name in ('a', 'b', 'c', 'd'):
            self.feature(name)
        with self.assertRaisesRegex(WorkflowError, 'capacity'):
            self.workflow.select(self.workflow.load())
        records = self.workflow.load(); records['d']['decision']['outcome'] = 'deferred'
        self.workflow.save(records['d'])
        records['c']['created'] = '2026-09-01'; self.workflow.save(records['c'])
        records['c']['decision'] = self.decision(records['c']); self.workflow.save(records['c'])
        self.assertEqual(self.workflow.select(self.workflow.load())['task'], 'c:implement')

    def test_primary_checkout_cannot_be_claimed_and_other_task_waits(self):
        self.feature(); self.feature('other'); self.commit()
        records = self.workflow.load()
        with self.assertRaisesRegex(WorkflowError, 'separate worktree'):
            self.workflow.claim(records, 'export:implement', 'worker', 'session', self.root)
        tree, packet = self.claim(records)
        self.assertEqual(packet['task']['status'], 'running')
        self.assertEqual(Workflow(tree).load()['export']['tasks'][0]['status'], 'running')
        self.assertIsNone(self.workflow.select(self.workflow.load()))
        with self.assertRaisesRegex(WorkflowError, 'not ready'):
            self.workflow.claim(self.workflow.load(), 'other:implement', 'another', 'another-session', tree)

    def test_coordinator_lock_is_exclusive_and_shared_worktree_cannot_mutate(self):
        self.feature(); self.commit()
        with self.workflow.locked():
            with self.assertRaisesRegex(WorkflowError, 'Another coordinator'):
                with Workflow(self.root).locked():
                    self.fail('second coordinator entered')
        tree = self.tree()
        with self.assertRaisesRegex(WorkflowError, 'primary checkout'):
            with Workflow(tree).locked():
                self.fail('worktree changed primary queue')

    def test_wrong_session_cannot_submit_or_block(self):
        self.feature(); self.commit(); records = self.workflow.load()
        tree, _ = self.claim(records)
        for action in (lambda: self.workflow.submit(records, 'export:implement', 'wrong', self.evidence(tree)),
                       lambda: self.workflow.block(records, 'export:implement', 'wrong', 'blocked')):
            with self.assertRaisesRegex(WorkflowError, 'Another session'):
                action()

    def test_round_trip_independent_verification_and_committed_completion(self):
        records, tree, evidence = self.submitted()
        self.workflow.verify(records, 'export:implement', self.verification(evidence))
        self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')
        records = self.workflow.load()
        self.assertEqual(records['export']['tasks'][0]['status'], 'done')
        self.assertTrue(self.workflow.status(records)[0]['evidence_matches_checkout'])

    def test_author_verification_and_stale_evidence_are_rejected(self):
        records, tree, evidence = self.submitted()
        result = self.verification(evidence); result['session'] = 'implementation-session'
        with self.assertRaisesRegex(WorkflowError, 'separate verifier'):
            self.workflow.verify(records, 'export:implement', result)
        result = self.verification(evidence); result['evidence_sha256'] = '0' * 64
        with self.assertRaisesRegex(WorkflowError, 'stale'):
            self.workflow.verify(self.workflow.load(), 'export:implement', result)
        (tree / 'export.py').write_text('unreviewed = True\n')
        with self.assertRaisesRegex(WorkflowError, 'source changed'):
            self.workflow.verify(self.workflow.load(), 'export:implement', self.verification(evidence))

    def test_failed_verifier_keeps_task_open_and_unblocks_other_work(self):
        records, tree, evidence = self.submitted()
        self.feature('other'); records = self.workflow.load()
        self.workflow.verify(records, 'export:implement', self.verification(evidence, outcome='failed'))
        records = self.workflow.load()
        self.assertEqual(records['export']['tasks'][0]['status'], 'blocked')
        self.assertEqual(self.workflow.select(records)['task'], 'other:implement')
        with self.assertRaisesRegex(WorkflowError, 'not active'):
            self.workflow.complete(records, 'export:implement', 'implementation-session')

    def test_no_partial_or_uncommitted_completion(self):
        self.feature(); self.commit(); records = self.workflow.load(); tree, _ = self.claim(records)
        with self.assertRaisesRegex(WorkflowError, 'required evidence'):
            self.workflow.submit(records, 'export:implement', 'implementation-session', [])
        records = self.workflow.load()
        (tree / 'export.py').write_text('value = 2\n'); commit = self.commit(tree)
        evidence = self.evidence(tree)
        self.workflow.submit(records, 'export:implement', 'implementation-session', evidence)
        self.workflow.verify(self.workflow.load(), 'export:implement', self.verification(evidence))
        with self.assertRaisesRegex(WorkflowError, 'source changed'):
            self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')
        (self.root / 'export.py').write_text('value = 2\n')
        with self.assertRaisesRegex(WorkflowError, 'Preserve the reviewed'):
            self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')
        self.commit()
        self.run_git('-c', 'user.name=Workflow Test', '-c', 'user.email=test@example.invalid',
                     'merge', '--no-ff', '-m', 'integrate reviewed commit', 'worker')
        self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')

    def test_completed_evidence_is_historical_when_later_code_changes(self):
        records, tree, evidence = self.submitted()
        self.workflow.verify(records, 'export:implement', self.verification(evidence))
        self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')
        (self.root / 'export.py').write_text('later_change = True\n'); self.commit()
        status = self.workflow.status(self.workflow.load())[0]
        self.assertEqual(status['status'], 'done')
        self.assertFalse(status['evidence_matches_checkout'])

    def test_recovery_preserves_work_and_needs_explicit_stopped_session(self):
        self.feature(); self.feature('other'); self.commit(); records = self.workflow.load()
        tree, _ = self.claim(records); (tree / 'export.py').write_text('unfinished = True\n')
        with self.assertRaisesRegex(WorkflowError, 'stop the previous'):
            self.workflow.recover(records, 'export:implement', 'inspected')
        run = records['export']['tasks'][0]['implementation']['run']
        with self.assertRaisesRegex(WorkflowError, 'another run'):
            self.workflow.recover(records, 'export:implement', 'stopped', True, 'wrong-run')
        result = self.workflow.recover(records, 'export:implement', 'previous session stopped; work inspected', True, run)
        self.assertEqual((tree / 'export.py').read_text(), 'unfinished = True\n')
        self.assertEqual(result['next']['task'], 'other:implement')
        self.assertTrue((self.workflow.state / 'runs' / (result['preserved_run'] + '.json')).exists())

    def test_private_symlink_and_duplicate_json_inputs_are_rejected(self):
        record = self.feature(); record['requirements'] = ['local/private.txt']
        self.workflow.save(record)
        with self.assertRaisesRegex(WorkflowError, 'public repository'):
            self.workflow.load()
        (self.root / 'alias').symlink_to(self.root / 'requirements.md')
        with self.assertRaisesRegex(WorkflowError, 'Symlink'):
            file_hash(self.root, 'alias')
        with self.assertRaisesRegex(WorkflowError, 'Private Codex'):
            file_hash(self.root, '.codex/auth.json')
        duplicate = self.root / 'duplicate.json'; duplicate.write_text('{"a": 1, "a": 2}')
        with self.assertRaisesRegex(WorkflowError, 'Duplicate JSON'):
            read_json(duplicate)

    def test_offline_evidence_cannot_satisfy_hardware_check(self):
        records, tree, evidence = self.submitted()
        records['export']['checks'][0]['environment'] = 'hardware'
        self.workflow.save(records['export'])
        with self.assertRaisesRegex(WorkflowError, 'environment'):
            self.workflow.load()

    def test_task_scope_mutation_requires_renewed_approval(self):
        record = self.feature()
        for target, field, value in ((record['checks'][0], 'description', 'Weaker condition'),
                                     (record['tasks'][0], 'title', 'Different implementation')):
            old = target[field]; target[field] = value; self.workflow.save(record)
            self.assertIsNone(self.workflow.select(self.workflow.load()))
            target[field] = old

    def test_obsolete_worktree_cannot_claim_current_dependencies(self):
        self.feature(); self.commit(); tree = self.tree()
        (self.root / 'new-dependency.py').write_text('ready = True\n'); self.commit()
        with self.assertRaisesRegex(WorkflowError, 'current integration commit'):
            self.claim(self.workflow.load(), tree=tree)

    def test_unlisted_change_after_review_cannot_complete(self):
        records, tree, evidence = self.submitted()
        self.workflow.verify(records, 'export:implement', self.verification(evidence))
        (self.root / 'unreviewed.py').write_text('new_behavior = True\n'); self.commit()
        with self.assertRaisesRegex(WorkflowError, 'source tree differs'):
            self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')

    def test_untracked_source_after_review_cannot_complete(self):
        records, tree, evidence = self.submitted()
        self.workflow.verify(records, 'export:implement', self.verification(evidence))
        (self.root / 'untracked.py').write_text('new_behavior = True\n')
        with self.assertRaisesRegex(WorkflowError, 'Uncommitted integration'):
            self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')

    def test_new_scope_cannot_reuse_old_completion_verification(self):
        records, tree, evidence = self.submitted()
        self.workflow.verify(records, 'export:implement', self.verification(evidence))
        self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')
        records = self.workflow.load(); record = records['export']
        record['checks'][0]['description'] = 'A different acceptance criterion'
        self.workflow.save(record)
        with self.assertRaisesRegex(WorkflowError, 'different approved decision'):
            self.workflow.decide(self.workflow.load(), 'export', self.decision(record))

    def test_changed_proposal_requirements_or_constraints_cannot_reuse_verification(self):
        records, tree, evidence = self.submitted()
        self.workflow.verify(records, 'export:implement', self.verification(evidence))
        self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')
        for name in ('requirements.md', 'docs/features/export/proposal.md'):
            path = self.root / name; original = path.read_text()
            path.write_text(original + 'Changed acceptance basis.\n')
            record = self.workflow.load()['export']
            with self.assertRaisesRegex(WorkflowError, 'different approved decision'):
                self.workflow.decide(self.workflow.load(), 'export', self.decision(record))
            path.write_text(original)
        record = self.workflow.load()['export']; decision = self.decision(record)
        decision['constraints'] = [{'text': 'A new mandatory check', 'checks': ['preserves-data']}]
        with self.assertRaisesRegex(WorkflowError, 'different approved decision'):
            self.workflow.decide(self.workflow.load(), 'export', decision)

    def test_committed_change_after_submission_requires_new_verification(self):
        records, tree, evidence = self.submitted()
        (tree / 'unlisted.py').write_text('new_behavior = True\n'); self.commit(tree)
        with self.assertRaisesRegex(WorkflowError, 'complete implementation commit'):
            self.workflow.verify(records, 'export:implement', self.verification(evidence))

    def test_mutating_cli_defaults_to_inspection_and_has_no_side_effects(self):
        self.feature(); self.commit()
        before = (self.root / 'docs/features/export/record.json').read_bytes()
        stream = io.StringIO()
        with redirect_stdout(stream), redirect_stderr(io.StringIO()):
            result = main(['--repo', str(self.root), 'block', 'export:implement', '--reason', 'example'])
        self.assertEqual(result, 0); self.assertTrue(json.loads(stream.getvalue())['inspection_only'])
        self.assertEqual(before, (self.root / 'docs/features/export/record.json').read_bytes())
        self.assertFalse(self.workflow.state.exists())

    def test_structurally_valid_empty_or_rubber_stamp_evaluation_fails(self):
        with self.assertRaisesRegex(WorkflowError, 'every case'):
            check_review_cases({'results': []})
        results = [{'id': name, 'outcome': 'approved', 'owner_required': False, 'rationale': 'Approve all'}
                   for name in ('useful-improvement', 'duplicate', 'hardware-assumption', 'owner-conflict', 'offline-despite-hardware')]
        with self.assertRaisesRegex(WorkflowError, 'expected policy'):
            check_review_cases({'results': results})

    def test_failed_repeats_need_changed_resumption_method(self):
        record = self.feature(); task = record['tasks'][0]
        task.update(status='blocked', blocker='Repeated fixture failure', repeats=2, resumption='same diagnosis')
        self.workflow.save(record)
        self.workflow.resume(self.workflow.load(), 'export:implement', 'same diagnosis')
        self.assertIsNone(self.workflow.select(self.workflow.load()))
        self.workflow.block(self.workflow.load(), 'export:implement', '', 'Need a new method')
        self.workflow.resume(self.workflow.load(), 'export:implement', 'Trace the changed syscall boundary')
        self.assertEqual(self.workflow.select(self.workflow.load())['task'], 'export:implement')


if __name__ == '__main__':
    unittest.main()
