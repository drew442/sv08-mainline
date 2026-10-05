"""Executable version-2 development routes against disposable real Git worktrees."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import unittest
import test_feature_workflow as legacy
from feature_workflow import Workflow, WorkflowError, digest_json, file_hash, main


class DevelopmentWorkflowTests(unittest.TestCase):
    setUp = legacy.WorkflowTests.setUp
    run_git = legacy.WorkflowTests.run_git
    commit = legacy.WorkflowTests.commit
    tree = legacy.WorkflowTests.tree
    claim = legacy.WorkflowTests.claim
    evidence = legacy.WorkflowTests.evidence

    def feature(self, name='export', policy='self', hazards=None, owner=False, authorize=True):
        record = legacy.WorkflowTests.feature(self, name, approved=False)
        (self.root / 'authority.md').write_text('Owner requests development within the selected scope.\n')
        record.update(format_version=2, authorization=None, requirement_rechecks=[],
                      requirements=['requirements.md', 'authority.md'], owner_decision_required=owner)
        task = record['tasks'][0]
        task.update(review_policy=policy, review_reason='Disposable development; restore with Git.',
                    hazards=hazards or [], owned_paths=[name + '.py', name + '-evidence.md'],
                    input_paths=[], validation=None)
        self.workflow.save(record)
        self.commit()
        if authorize:
            self.authorize(name, 'owner-request' if owner else 'standing')
        return self.workflow.load()[name]

    def authorize(self, name='export', basis='standing'):
        return self.workflow.authorize(self.workflow.load(), name, 'coordinator', 'coord-session',
                                       basis, 'authority.md', 'Actual owner request/standing scope inspected.')

    def submitted(self, policy='self', hazards=None):
        self.feature(policy=policy, hazards=hazards)
        self.commit()
        records = self.workflow.load()
        tree, _ = self.claim(records)
        evidence = self.evidence(tree)
        self.workflow.submit(records, 'export:implement', 'implementation-session', evidence,
                             True, 'Observed fixture checks passed; evidence records commands and limitations.')
        return self.workflow.load(), tree, evidence

    def verification(self, evidence, outcome='passed'):
        return {'outcome': outcome, 'reviewer': 'reviewer', 'session': 'review-session',
                'rationale': 'Checked the named concern; no new requirements.',
                'basis_sha256': self.workflow.basis_digest(self.workflow.load()['export']),
                'evidence_sha256': digest_json(evidence)}

    def complete(self):
        return self.workflow.complete(self.workflow.load(), 'export:implement', 'implementation-session')

    def test_substantive_self_validated_work_completes_without_second_agent(self):
        records, tree, evidence = self.submitted()
        task = records['export']['tasks'][0]
        self.assertIsNone(records['export']['decision'])
        self.assertEqual(task['status'], 'validated')
        self.assertEqual(task['validation']['actor'], 'implementer')
        self.assertIsNone(task['verification'])
        self.assertEqual(self.complete()['status'], 'done')
        self.assertEqual(self.workflow.status(self.workflow.load())[0]['completion_basis'], 'self')

    def test_missing_authorization_and_owner_boundary_block_dispatch(self):
        self.feature(authorize=False, owner=True)
        self.assertIsNone(self.workflow.select(self.workflow.load()))
        with self.assertRaisesRegex(WorkflowError, 'owner request'):
            self.authorize()
        self.authorize(basis='owner-request')
        self.assertEqual(self.workflow.select(self.workflow.load())['task'], 'export:implement')

    def test_no_implicit_passing_checks_or_partial_evidence(self):
        self.feature(); self.commit(); tree, _ = self.claim(self.workflow.load())
        with self.assertRaisesRegex(WorkflowError, 'Attest actual'):
            self.workflow.submit(self.workflow.load(), 'export:implement', 'implementation-session', self.evidence(tree))
        with self.assertRaises(WorkflowError):
            self.workflow.submit(self.workflow.load(), 'export:implement', 'implementation-session', [], True, 'ran tests')
        self.assertEqual(self.workflow.load()['export']['tasks'][0]['status'], 'running')

    def test_targeted_review_is_opt_in_but_blocks_completion_when_selected(self):
        records, tree, evidence = self.submitted('targeted')
        with self.assertRaisesRegex(WorkflowError, 'independent verification'):
            self.complete()
        self.workflow.verify(records, 'export:implement', self.verification(evidence))
        self.assertEqual(self.complete()['status'], 'done')

    def test_consequential_review_cannot_be_replaced_by_self_validation(self):
        records, tree, evidence = self.submitted('consequential', ['irreplaceable-data'])
        with self.assertRaisesRegex(WorkflowError, 'independent verification'):
            self.complete()
        task = records['export']['tasks'][0]
        task['status'] = 'validated'
        self.workflow.save(records['export'])
        with self.assertRaisesRegex(WorkflowError, 'cannot be bypassed'):
            self.workflow.load()

    def test_declared_hazards_cannot_use_self_or_targeted_route(self):
        for policy in ('self', 'targeted'):
            with self.subTest(policy=policy):
                record = self.feature(name=policy)
                record['tasks'][0]['hazards'] = ['hardware-damage']
                record['tasks'][0]['review_policy'] = policy
                with self.assertRaises(WorkflowError):
                    self.workflow.save(record)

    def test_review_policy_and_hazard_changes_invalidate_existing_validation(self):
        records, tree, evidence = self.submitted('consequential', ['physical-harm'])
        task = records['export']['tasks'][0]
        task.update(review_policy='self', hazards=[], status='validated')
        self.workflow.save(records['export'])
        with self.assertRaisesRegex(WorkflowError, 'scope or review policy'):
            self.workflow.load()

    def test_missing_or_unknown_route_is_not_interpreted_as_self(self):
        record = self.feature()
        task = record['tasks'][0]
        del task['review_policy']
        with self.assertRaises(WorkflowError):
            self.workflow.save(record)
        task['review_policy'] = 'skip'
        with self.assertRaises(WorkflowError):
            self.workflow.save(record)

    def test_reviewer_identity_cannot_alias_the_implementation_session(self):
        records, tree, evidence = self.submitted('targeted')
        result = self.verification(evidence)
        result.update(reviewer='a different label', session='implementation-session')
        with self.assertRaisesRegex(WorkflowError, 'separate verifier'):
            self.workflow.verify(records, 'export:implement', result)

    def test_same_optional_approver_may_review_delivery_without_authorship(self):
        record = self.feature()
        decision = legacy.WorkflowTests.decision(self, record)
        # .decision helper uses the complete scope, including review classification.
        record['tasks'][0]['review_policy'] = 'targeted'
        self.workflow.save(record); self.commit(); self.authorize()
        record = self.workflow.load()['export']
        decision = legacy.WorkflowTests.decision(self, record)
        self.workflow.decide(self.workflow.load(), 'export', decision)
        self.commit(); records = self.workflow.load(); tree, _ = self.claim(records)
        evidence = self.evidence(tree)
        self.workflow.submit(records, 'export:implement', 'implementation-session', evidence, True, 'Checks passed')
        result = self.verification(evidence)
        result.update(reviewer=decision['reviewer'], session=decision['session'])
        self.workflow.verify(self.workflow.load(), 'export:implement', result)
        self.assertEqual(self.complete()['status'], 'done')

    def test_failed_review_blocks_and_same_reviewer_can_check_repair(self):
        records, tree, evidence = self.submitted('targeted')
        self.workflow.verify(records, 'export:implement', self.verification(evidence, 'failed'))
        with self.assertRaisesRegex(WorkflowError, 'not active'):
            self.complete()
        self.workflow.resume(self.workflow.load(), 'export:implement', 'Fix the demonstrated defect; retain reviewer')
        self.assertIsNone(self.workflow.load()['export']['tasks'][0]['validation'])
        self.commit(); replacement = self.tree('repair'); records = self.workflow.load()
        self.claim(records, tree=replacement)
        evidence = self.evidence(replacement)
        self.workflow.submit(records, 'export:implement', 'implementation-session', evidence, True, 'Repair checked')
        self.workflow.verify(self.workflow.load(), 'export:implement', self.verification(evidence))
        self.complete()

    def test_unrelated_work_can_run_while_a_candidate_waits_for_review(self):
        self.feature(); self.feature('other')
        record = self.workflow.load()['export']; record['tasks'][0]['review_policy'] = 'targeted'
        self.workflow.save(record); self.commit(); self.authorize(); self.commit()
        records = self.workflow.load(); tree, _ = self.claim(records)
        self.workflow.submit(records, 'export:implement', 'implementation-session', self.evidence(tree), True, 'Checks passed')
        records = self.workflow.load()
        self.assertEqual(self.workflow.select(records)['task'], 'other:implement')
        other = self.tree('other-worker')
        self.workflow.claim(records, 'other:implement', 'other-worker', 'other-session', other)
        self.assertIsNone(self.workflow.select(self.workflow.load()))

    def test_overlapping_outputs_and_input_subtrees_remain_reserved(self):
        self.feature(); self.feature('other')
        record = self.workflow.load()['export']
        record['tasks'][0]['input_paths'] = ['shared/']
        self.workflow.save(record); self.commit(); self.authorize(); self.commit()
        records = self.workflow.load(); tree, _ = self.claim(records)
        self.workflow.submit(records, 'export:implement', 'implementation-session', self.evidence(tree), True, 'Passed')
        other = self.workflow.load()['other']
        for output in ('export.py', 'shared/new-file.py'):
            other['tasks'][0]['owned_paths'] = [output]
            self.workflow.save(other)
            status = {r['task']: r for r in self.workflow.status(self.workflow.load())}
            self.assertIn('reservation overlaps', status['other:implement']['reason'])

    def test_frozen_worktree_cannot_be_reused(self):
        self.feature(); self.feature('other'); self.commit()
        records = self.workflow.load(); tree, _ = self.claim(records)
        self.workflow.submit(records, 'export:implement', 'implementation-session', self.evidence(tree), True, 'Passed')
        with self.assertRaisesRegex(WorkflowError, 'Worktree is reserved'):
            self.workflow.claim(self.workflow.load(), 'other:implement', 'other', 'other-session', tree)

    def test_completion_allows_unrelated_committed_changes(self):
        records, tree, evidence = self.submitted()
        (self.root / 'unrelated.py').write_text('unrelated = True\n'); self.commit()
        self.assertEqual(self.complete()['status'], 'done')

    def test_relevant_dependency_change_blocks_completion(self):
        self.feature()
        (self.root / 'dependency.py').write_text('api = 1\n')
        record = self.workflow.load()['export']; record['tasks'][0]['input_paths'] = ['dependency.py']
        self.workflow.save(record); self.commit(); self.authorize(); self.commit()
        records = self.workflow.load(); tree, _ = self.claim(records)
        self.workflow.submit(records, 'export:implement', 'implementation-session', self.evidence(tree), True, 'Passed')
        (self.root / 'dependency.py').write_text('api = 2\n'); self.commit()
        with self.assertRaisesRegex(WorkflowError, 'Relevant integrated source'):
            self.complete()

    def test_mode_change_is_not_hidden_by_equal_content_hash(self):
        records, tree, evidence = self.submitted()
        (self.root / 'export.py').chmod(0o755); self.commit()
        with self.assertRaisesRegex(WorkflowError, 'Relevant integrated source'):
            self.complete()

    def test_unowned_candidate_change_is_rejected(self):
        self.feature(); self.commit(); records = self.workflow.load(); tree, _ = self.claim(records)
        (tree / 'surprise.py').write_text('not_owned = True\n'); self.commit(tree)
        with self.assertRaisesRegex(WorkflowError, 'outside assigned ownership'):
            self.workflow.submit(records, 'export:implement', 'implementation-session', self.evidence(tree), True, 'Passed')

    def test_committed_mutation_of_frozen_candidate_is_rejected(self):
        records, tree, evidence = self.submitted()
        (tree / 'export.py').write_text('changed = True\n'); self.commit(tree)
        with self.assertRaisesRegex(WorkflowError, 'complete implementation commit'):
            self.complete()

    def test_self_validation_hash_and_identity_must_match(self):
        records, tree, evidence = self.submitted()
        for field, value in (('session', 'other'), ('basis_sha256', '0'*64), ('evidence_sha256', '0'*64)):
            record = deepcopy(records['export']); record['tasks'][0]['validation'][field] = value
            self.workflow.save(record)
            with self.assertRaises(WorkflowError):
                self.workflow.load()
        self.workflow.save(records['export'])

    def test_nonmaterial_requirement_recheck_preserves_prior_review(self):
        records, tree, evidence = self.submitted('targeted')
        self.workflow.verify(records, 'export:implement', self.verification(evidence))
        original = deepcopy(self.workflow.load()['export'])
        (self.root / 'requirements.md').write_text('Preserve data, default immutable, factory storage.\n\nTypo fixed in unrelated note.\n')
        self.commit()
        with self.assertRaisesRegex(WorkflowError, 'Approval changed'):
            self.complete()
        self.workflow.recheck_requirements(self.workflow.load(), 'export', 'coordinator', 'coord-session',
                                          digest_json(original['authorization']['requirements_sha256']),
                                          'Inspected exact diff: only an unrelated note; requirements for this task unchanged.')
        current = self.workflow.load()['export']
        self.assertEqual(current['authorization'], original['authorization'])
        self.assertEqual(current['tasks'][0]['verification'], original['tasks'][0]['verification'])
        self.complete()

    def test_recheck_cannot_hide_changes_to_a_test_input(self):
        self.feature()
        record = self.workflow.load()['export']; record['tasks'][0]['input_paths'] = ['requirements.md']
        self.workflow.save(record); self.commit(); self.authorize(); self.commit()
        records = self.workflow.load(); tree, _ = self.claim(records)
        self.workflow.submit(records, 'export:implement', 'implementation-session', self.evidence(tree), True, 'Passed')
        old = self.workflow.effective_requirements(records['export'])
        (self.root / 'requirements.md').write_text('Changed fixture input\n'); self.commit()
        self.workflow.recheck_requirements(self.workflow.load(), 'export', 'coordinator', 'coord-session',
                                          digest_json(old), 'Claimed nonmaterial')
        with self.assertRaisesRegex(WorkflowError, 'Relevant integrated source'):
            self.complete()

    def test_recheck_cannot_change_authority_reference(self):
        record = self.feature()
        (self.root / 'authority.md').write_text('Changed owner authority\n'); self.commit()
        with self.assertRaisesRegex(WorkflowError, 'authorization reference'):
            self.workflow.recheck_requirements(self.workflow.load(), 'export', 'coordinator', 'coord-session',
                digest_json(record['authorization']['requirements_sha256']), 'Not permitted')

    def test_uncommitted_and_stale_rechecks_are_rejected(self):
        record = self.feature()
        (self.root / 'requirements.md').write_text('Uncommitted change\n')
        for expected in ('0'*64, digest_json(record['authorization']['requirements_sha256'])):
            with self.assertRaises(WorkflowError):
                self.workflow.recheck_requirements(self.workflow.load(), 'export', 'coordinator', 'coord-session',
                                                  expected, 'Checked')
        self.assertFalse(self.workflow.load()['export']['requirement_rechecks'])

    def test_hardware_tasks_still_never_dispatch(self):
        record = self.feature()
        record['tasks'][0].update(environment='hardware', human_task='human.md')
        record['checks'][0]['environment'] = 'hardware'
        self.workflow.save(record); self.commit(); self.authorize()
        self.assertIsNone(self.workflow.select(self.workflow.load()))

    def test_version_one_still_requires_real_independent_verification(self):
        legacy.WorkflowTests.feature(self, approved=False)
        record = self.workflow.load()['export']
        record['decision'] = legacy.WorkflowTests.decision(self, record)
        self.workflow.save(record); self.commit(); records = self.workflow.load(); tree, _ = self.claim(records)
        with self.assertRaisesRegex(WorkflowError, 'legacy'):
            self.workflow.submit(records, 'export:implement', 'implementation-session', self.evidence(tree), True, 'Passed')

    def test_real_candidate_change_cli_submission_and_integration(self):
        self.feature(); self.commit(); records = self.workflow.load(); tree, _ = self.claim(records)
        (tree / 'export.py').write_text('value = 2\n'); candidate = self.commit(tree)
        path = self.workflow.state / 'evidence.json'
        path.write_text(json.dumps(self.evidence(tree)))
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            rc = main(['--repo', str(self.root), '--execute', 'submit', 'export:implement',
                       '--session', 'implementation-session', '--evidence', str(path),
                       '--checks-passed', '--reason', 'Ran the supplied checks; inspected output'])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'validated')
        with self.assertRaises(WorkflowError):
            self.complete()
        self.commit()
        self.run_git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                     'merge', '--no-ff', '-m', 'Integrate candidate', 'worker')
        (self.root / 'unrelated.md').write_text('Other work\n'); self.commit()
        self.assertEqual(self.complete()['status'], 'done')
        self.assertEqual(self.workflow.load()['export']['tasks'][0]['validation']['source_commit'], candidate)

    def test_new_mutating_cli_commands_are_inspection_only_by_default(self):
        self.feature(authorize=False)
        before = (self.root / 'docs/features/export/record.json').read_bytes()
        for argv in (['authorize', 'export', '--basis', 'standing', '--reference', 'authority.md'],
                     ['recheck-requirements', 'export', '--expected-sha256', '0'*64]):
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(io.StringIO()):
                rc = main(['--repo', str(self.root), *argv, '--actor', 'coordinator',
                           '--session', 'coord', '--reason', 'Requested operation'])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(output.getvalue())['inspection_only'])
        self.assertEqual(before, (self.root / 'docs/features/export/record.json').read_bytes())



    def test_deleting_a_declared_input_prevents_completion(self):
        self.feature()
        (self.root / 'dependency.txt').write_text('required input\n')
        record = self.workflow.load()['export']
        record['tasks'][0]['input_paths'] = ['dependency.txt']
        self.workflow.save(record); self.commit(); self.authorize(); self.commit()
        records = self.workflow.load(); tree, _ = self.claim(records)
        self.workflow.submit(records, 'export:implement', 'implementation-session',
                             self.evidence(tree), True, 'Checks passed with dependency')
        (self.root / 'dependency.txt').unlink(); self.commit()
        with self.assertRaisesRegex(WorkflowError, 'Relevant integrated source changed'):
            self.complete()

    def test_changed_input_gitlink_prevents_completion(self):
        self.feature()
        first = self.run_git('rev-parse', 'HEAD')
        record = self.workflow.load()['export']
        record['tasks'][0]['input_paths'] = ['vendor/module']
        self.workflow.save(record); self.commit(); self.authorize(); self.commit()
        self.run_git('update-index', '--add', '--cacheinfo', '160000', first, 'vendor/module')
        self.run_git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                     'commit', '-qm', 'Pin fixture gitlink')
        second = self.run_git('rev-parse', 'HEAD')
        records = self.workflow.load(); tree, _ = self.claim(records)
        self.workflow.submit(records, 'export:implement', 'implementation-session',
                             self.evidence(tree), True, 'Checks passed at pin')
        self.run_git('update-index', '--cacheinfo', '160000', second, 'vendor/module')
        self.run_git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                     'commit', '-qm', 'Change fixture gitlink')
        with self.assertRaisesRegex(WorkflowError, 'Relevant integrated source changed'):
            self.complete()


if __name__ == '__main__':
    unittest.main()
