"""Static context-entry contracts, not proof of runtime loading, caching or savings.

These limits guard small navigation surfaces, not the amount of evidence an agent
may inspect. Raise a limit explicitly when correctness needs a larger entry.
"""
from pathlib import Path
import re
import tomllib
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def text(relative):
    return (ROOT / relative).read_text(encoding='utf-8')


def role_instructions():
    for path in sorted((ROOT / '.codex/agents').glob('*.toml')):
        yield path, tomllib.loads(path.read_text(encoding='utf-8'))['developer_instructions']


class AgentContextTests(unittest.TestCase):
    def test_entry_size_budgets_do_not_become_task_context_caps(self):
        for relative, budget in {'AGENTS.md': 7600, '.codex/README.md': 2200,
                                 '.codex/agent-guide.md': 13000}.items():
            with self.subTest(path=relative):
                self.assertLessEqual(len((ROOT / relative).read_bytes()), budget)
        for path, _ in role_instructions():
            self.assertLessEqual(path.stat().st_size, 3500, path.name)
        self.assertIn('Expand retrieval', text('AGENTS.md'))
        self.assertIn('never a token cap', text('docs/context-map.md'))

    def test_profiles_do_not_require_coordinator_or_history_onboarding(self):
        for path, instructions in role_instructions():
            first_paragraph = instructions.strip().split('\n\n', 1)[0]
            with self.subTest(profile=path.name):
                self.assertIn('Read AGENTS.md', first_paragraph)
                self.assertNotIn('.codex/agent-guide.md', first_paragraph)
                self.assertNotIn('.codex/README.md', first_paragraph)
                self.assertNotIn('docs/context-map.md', first_paragraph)
                self.assertNotIn('feature-workflow-pilot', instructions)
                self.assertIn('only for a routing or execution rule', instructions)
                self.assertIn('not as another required read', instructions)

    def test_no_global_queue_selection_by_children(self):
        for _, instructions in role_instructions():
            self.assertNotIn('feature_workflow.py next', instructions)
        entry = text('.codex/README.md')
        self.assertIn('**Coordinator:**', entry)
        self.assertIn('**Delegated worker:**', entry)
        self.assertIn('Do not select from the global queue', entry)
        self.assertIn('only when auditing', entry)

    def test_root_routes_by_relevance_instead_of_a_required_document_stack(self):
        root = text('AGENTS.md')
        self.assertNotIn('Read `README.md`, `docs/project.md`, `docs/roadmap.md`', root)
        self.assertIn('applicable accepted requirements', root)
        self.assertIn('only when relevant sources are unclear', root)
        self.assertIn('every applicable acceptance check', root)
        self.assertIn('not new authorization', root)

    def test_completion_does_not_stop_at_patch_or_loop_after_success(self):
        root = ' '.join(text('AGENTS.md').split())
        for phrase in ('a first patch is not completion', 'same unresolved failure',
                       'distinct defects', 'primary-task allowance',
                       'broader/repeated tests need changed inputs',
                       'Never remove a check to pass'):
            self.assertIn(phrase, root)
        instructions = dict((p.stem, s) for p, s in role_instructions())
        self.assertIn('fix in-scope failures within the primary-task allowance',
                      instructions['project-implementer'])
        self.assertIn('Do not repair', instructions['feature-verifier'])

    def test_slow_tools_and_changed_direction_preserve_state(self):
        guide = ' '.join(text('.codex/agent-guide.md').split())
        for phrase in ('do not relaunch after a timeout', 'actual results',
                       'active handles, pending results', 'budgets',
                       'does not undo', 'steering cancels a running tool'):
            # 'does not undo' is in the root; both shared surfaces are checked.
            self.assertIn(phrase, guide + ' ' + ' '.join(text('AGENTS.md').split()))
        self.assertIn('Do not assume steering cancels', guide)

    def test_narrower_reads_do_not_narrow_formal_verification(self):
        for path, instructions in role_instructions():
            if path.stem.startswith('feature-verifier'):
                with self.subTest(role=path.name):
                    for phrase in ('complete delivery diff', 'every acceptance criterion',
                                   'entire diff', 'unlisted files', 'decision_sha256',
                                   'evidence_sha256', 'separate session'):
                        self.assertIn(phrase, instructions)

    def test_worker_visible_authority_and_incidental_limits_are_retained(self):
        root = ' '.join(text('AGENTS.md').replace('**', '').split())
        for phrase in ('two experiments', '300 seconds cumulative elapsed process runtime',
                       '256 MiB cumulative generated data',
                       'Primary builds/tests have separate budgets',
                       'Even read-only printer access is coordinator-owned',
                       'standing authorization to push every project commit',
                       'without force pushes', 'cannot grant hardware authority'):
            self.assertIn(phrase, root)

    def test_optional_context_map_links_are_relative_and_stay_in_repository(self):
        # Existence is checked separately against the pinned remote tree during
        # a reconstructed-fixture audit; in a full checkout use ordinary link checks.
        for relative in ('AGENTS.md', '.codex/README.md', '.codex/agent-guide.md',
                         'docs/context-map.md'):
            source = ROOT / relative
            for href in re.findall(r'\]\(([^)]+)\)', text(relative)):
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc:
                    continue
                target = (source.parent / unquote(parsed.path)).resolve()
                with self.subTest(source=relative, href=href):
                    self.assertTrue(target.is_relative_to(ROOT))
                    self.assertNotIn('local', target.relative_to(ROOT).parts)
        context = text('docs/context-map.md')
        for anchor in ('project.md', 'current-goals.md', 'coordinated-human-tasks.md',
                       'feature-workflow.md', '0010-host-administration-and-recovery-ui.md'):
            self.assertIn(anchor, context)


if __name__ == '__main__':
    unittest.main()
