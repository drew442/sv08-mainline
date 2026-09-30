"""Public evidence-path regression cases, not live agent/sandbox enforcement."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from feature_workflow import (Workflow, WorkflowError, digest_bytes, file_hash,
                              main, public_path, snapshot)


class PublicConfigurationPathTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, path, text='fixture\n'):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def test_explicit_versioned_codex_roots_are_hashable(self):
        for name in ('README.md', 'config.toml', 'agent-guide.md', 'current-goals.md'):
            with self.subTest(name=name):
                relative = '.codex/' + name
                path = self.write(relative)
                self.assertEqual(file_hash(self.root, relative), digest_bytes(path.read_bytes()))

    def test_existing_public_profile_schema_and_template_paths_remain_usable(self):
        for relative in ('.codex/agents/reviewer.toml', '.codex/schemas/evidence.json',
                         '.codex/templates/proposal.md'):
            with self.subTest(path=relative):
                self.write(relative)
                self.assertEqual(snapshot(self.root, [relative])[relative],
                                 digest_bytes(b'fixture\n'))

    def test_unlisted_private_codex_roots_and_nested_paths_stay_rejected(self):
        for relative in ('.codex/auth.json', '.codex/config.local.toml',
                         '.codex/local.md', '.codex/other/config.toml',
                         '.codex/agents/nested/key', '.codex/probes/result.json'):
            with self.subTest(path=relative):
                self.write(relative)
                with self.assertRaisesRegex(WorkflowError, 'Private Codex'):
                    file_hash(self.root, relative)

    def test_scratch_and_private_trees_are_not_public_evidence(self):
        for relative in ('local/feature-workflow/probes/task/run/result.json',
                         'backups/config.toml', 'build/result.txt', '.venv/secret'):
            with self.subTest(path=relative):
                self.write(relative)
                with self.assertRaisesRegex(WorkflowError, 'public repository'):
                    file_hash(self.root, relative)

    def test_environment_paths_are_rejected_inside_public_subdirectories(self):
        for relative in ('.codex/agents/.env', '.codex/templates/.env.private'):
            with self.subTest(path=relative):
                self.write(relative)
                with self.assertRaisesRegex(WorkflowError, 'Private environment'):
                    file_hash(self.root, relative)

    def test_absolute_traversal_and_backslash_paths_are_rejected(self):
        for relative in ('/tmp/config.toml', '.codex/../config.toml',
                         '.codex\\config.toml'):
            with self.subTest(path=relative):
                with self.assertRaises(WorkflowError):
                    public_path(self.root, relative, exists=False)

    def test_allowed_file_symlink_is_rejected(self):
        source = self.write('source.txt')
        directory = self.root / '.codex'
        directory.mkdir()
        (directory / 'config.toml').symlink_to(source)
        with self.assertRaisesRegex(WorkflowError, 'Symlink'):
            file_hash(self.root, '.codex/config.toml')

    def test_allowed_ancestor_symlink_is_rejected(self):
        source = self.root / 'actual'
        source.mkdir()
        (source / 'config.toml').write_text('fixture\n')
        (self.root / '.codex').symlink_to(source, target_is_directory=True)
        with self.assertRaisesRegex(WorkflowError, 'Symlink'):
            file_hash(self.root, '.codex/config.toml')

    def test_missing_public_file_and_historical_path_admission_are_distinct(self):
        with self.assertRaisesRegex(WorkflowError, 'Missing public evidence'):
            file_hash(self.root, '.codex/config.toml')
        self.assertEqual(public_path(self.root, '.codex/config.toml', exists=False),
                         self.root / '.codex/config.toml')
        with self.assertRaisesRegex(WorkflowError, 'Private Codex'):
            public_path(self.root, '.codex/auth.json', exists=False)

    def test_configuration_hash_cli_reads_real_content(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.write('.codex/config.toml', 'approval_policy = "never"\n')
        stream = io.StringIO()
        with redirect_stdout(stream):
            result = main(['--repo', str(self.root), 'hash', '.codex/config.toml'])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stream.getvalue()), {
            '.codex/config.toml': digest_bytes(b'approval_policy = "never"\n')})

    def test_changed_public_configuration_still_invalidates_decision(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.write('docs/features/example/proposal.md', 'proposal\n')
        self.write('.codex/agent-guide.md', 'old policy\n')
        from feature_workflow import scope_digest
        record = {'proposal': 'docs/features/example/proposal.md',
                  'requirements': ['.codex/agent-guide.md'], 'tasks': [], 'decision': None}
        record['decision'] = {'outcome': 'approved',
                              'proposal_sha256': file_hash(self.root, record['proposal']),
                              'scope_sha256': scope_digest(record),
                              'requirements_sha256': snapshot(self.root, record['requirements'])}
        workflow = Workflow(self.root)
        self.assertIsNone(workflow.decision_problem(record))
        self.write('.codex/agent-guide.md', 'new policy\n')
        self.assertEqual(workflow.decision_problem(record),
                         'Requirement sources changed since approval')

    def test_packet_preserves_offline_role_and_coordinator_boundaries(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        record = {'id': 'example', 'kind': 'fix', 'proposal': 'proposal.md',
                  'requirements': [], 'decision': None, 'checks': [],
                  'tasks': [{'id': 'task', 'checks': []}]}
        instruction = Workflow(self.root).packet({'example': record}, 'example:task')['instruction']
        for phrase in ('.codex/agent-guide.md', 'approved offline task',
                       'assigned role and file ownership', 'remaining allowance',
                       'coordinator-assigned scratch', 'Do not contact printer hardware',
                       'change shared records, commit, publish', 'spawn agents'):
            self.assertIn(phrase, instruction)


if __name__ == '__main__':
    unittest.main()
