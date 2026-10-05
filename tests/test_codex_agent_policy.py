"""Offline repository contracts; not a Codex launcher, benchmark or sandbox test."""
import csv
from decimal import Decimal
from pathlib import Path
import re
import tomllib
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / '.codex/agents'
SOL = 'gpt-6.1-sol'
LUNA = 'gpt-6-luna'
# None is deliberate: these profiles allow supported spawn-time effort selection.
ROUTES = {
    'project_lookup': (LUNA, 'medium'),
    'project_narrow_implementer': (LUNA, 'medium'),
    'project_researcher': (SOL, None),
    'project_planner': (SOL, 'medium'),
    'project_implementer': (SOL, None),
    'project_integration': (SOL, None),
    'feature_approver': (SOL, 'medium'),
    'feature_verifier': (SOL, 'medium'),
    'feature_verifier_high': (SOL, 'high'),
    'high_consequence_reviewer': (SOL, 'medium'),
    'high_consequence_reviewer_high': (SOL, 'high'),
}
RETIRED = ('feature-suggester', 'project-routine-implementer', 'project-test-runner')


def profiles():
    return [(p, tomllib.loads(p.read_text(encoding='utf-8')))
            for p in sorted(AGENTS.glob('*.toml'))]


def chart_rows():
    path = ROOT / 'docs/development/terminalbench-20260929.csv'
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


class CodexAgentPolicyTests(unittest.TestCase):
    def test_role_inventory_and_fields(self):
        loaded = profiles()
        names = [data['name'] for _, data in loaded]
        self.assertEqual(len(names), len(set(names)), 'duplicate role name')
        self.assertEqual(set(names), set(ROUTES))
        for path, data in loaded:
            with self.subTest(profile=path.name):
                expected = {'name', 'description', 'model', 'agents',
                            'developer_instructions'}
                if ROUTES[data['name']][1] is not None:
                    expected.add('model_reasoning_effort')
                self.assertEqual(set(data), expected)
                self.assertEqual(path.stem.replace('-', '_'), data['name'])
                self.assertTrue(data['description'].strip())
                self.assertIn('AGENTS.md', data['developer_instructions'])
                self.assertIn('.codex/agent-guide.md', data['developer_instructions'])
                self.assertEqual((data['model'], data.get('model_reasoning_effort')),
                                 ROUTES[data['name']])
                self.assertEqual(data['agents'], {'enabled': False})

    def test_child_defaults_without_main_model_or_billing_override(self):
        config = tomllib.loads((ROOT / '.codex/config.toml').read_text())
        self.assertEqual(config, {
            'approval_policy': 'never', 'sandbox_mode': 'danger-full-access',
            'agents': {
                'max_concurrent_threads_per_session': 2,
                'default_subagent_model': SOL,
                'default_subagent_reasoning_effort': 'low',
            }})

    def test_only_intended_workers_have_adjustable_effort(self):
        flexible = {d['name'] for _, d in profiles() if 'model_reasoning_effort' not in d}
        self.assertEqual(flexible, {'project_researcher', 'project_implementer',
                                    'project_integration'})
        for _, data in profiles():
            if data['name'] in flexible:
                self.assertEqual(data['model'], SOL)
                self.assertIn('explicit spawn effort', data['developer_instructions'])

    def test_independent_reviews_keep_routing_and_inherit_execution(self):
        for _, data in profiles():
            if data['name'].startswith(('feature_approver', 'feature_verifier',
                                         'high_consequence_reviewer')):
                with self.subTest(role=data['name']):
                    self.assertEqual(data['model'], SOL)
                    self.assertIn(data['model_reasoning_effort'], ('medium', 'high'))
                    self.assertNotIn('sandbox_mode', data)
                    self.assertNotIn('approval_policy', data)

    def test_high_variants_preserve_the_full_review_contract(self):
        by_name = {d['name']: d for _, d in profiles()}
        for name in ('feature_verifier', 'high_consequence_reviewer'):
            with self.subTest(role=name):
                normal, high = by_name[name], by_name[name + '_high']
                self.assertEqual(normal['developer_instructions'], high['developer_instructions'])
                self.assertEqual(normal['model_reasoning_effort'], 'medium')
                self.assertEqual(high['model_reasoning_effort'], 'high')

    def test_guide_table_matches_defaults_and_adjustability(self):
        text = (ROOT / '.codex/agent-guide.md').read_text()
        rows = re.findall(r'^\| `([a-z_]+)` \| (GPT-[^|]+?) \| '
                          r'(low|medium|high)( \(adjustable\))? \|', text, re.MULTILINE)
        self.assertEqual(len(rows), len(ROUTES))
        actual = {name: (model.lower().replace(' ', '-'),
                         None if adjustable else effort)
                  for name, model, effort, adjustable in rows}
        self.assertEqual(actual, {name: values[:2] for name, values in ROUTES.items()})
        self.assertTrue(all(effort == 'low' for _, _, effort, a in rows if a))

    def test_retired_definitions_are_absent_but_migration_is_documented(self):
        guide = (ROOT / '.codex/agent-guide.md').read_text()
        for name in RETIRED:
            with self.subTest(role=name):
                self.assertFalse((AGENTS / (name + '.toml')).exists())
                self.assertIn(name.replace('-', '_'), guide)

    def test_lookup_and_mechanical_editing_do_not_replace_engineering(self):
        by_name = {d['name']: d['developer_instructions'] for _, d in profiles()}
        for phrase in ('Do not infer root causes', 'Do not modify tracked files',
                       'project_researcher or project_planner'):
            self.assertIn(phrase, by_name['project_lookup'])
        for phrase in ('A small diff alone', 'mechanical', 'project_implementer',
                       'independent review'):
            self.assertIn(phrase, by_name['project_narrow_implementer'])

    def test_substantive_low_work_is_allowed_without_hardware_authority(self):
        text = dict((d['name'], d['developer_instructions']) for _, d in profiles())[
            'project_implementer']
        for phrase in ('Low is normal', 'Offline work in recovery/storage modules',
                       'one bounded repair cycle', 'contact printer hardware',
                       'independent verification'):
            self.assertIn(phrase, text)

    def test_planner_has_no_self_approval_or_production_implementation(self):
        text = dict((d['name'], d['developer_instructions']) for _, d in profiles())[
            'project_planner']
        for phrase in ('plan existing approved work', 'Do not reapprove existing work',
                       'Do not modify tracked files or records', 'feature_approver independently',
                       'grants no execution authority'):
            self.assertIn(phrase, text)

    def test_scripts_and_shared_resource_protections(self):
        text = dict((d['name'], d['developer_instructions']) for _, d in profiles())[
            'project_integration']
        for phrase in ('direct script', 'Do not modify production code',
                       'physical block', 'timeout is not permission to relaunch',
                       'An evidence producer cannot independently verify'):
            self.assertIn(phrase, text)

    def test_root_and_guide_use_proportionate_review_and_hardware_gates(self):
        root = (ROOT / 'AGENTS.md').read_text()
        guide = (ROOT / '.codex/agent-guide.md').read_text()
        for text in (root, guide):
            self.assertIn('owner authorization', text)
            self.assertIn('project_planner', text)
        for phrase in ('high-consequence-reviewer-high.toml', 'self-validated by default',
                       'cannot grant hardware authority'):
            self.assertIn(phrase, root)
        for phrase in ('An approver may review delivery',
                       'not formal reviewers', 'generic workers'):
            # Case-insensitive policy wording check, not enforcement.
            self.assertIn(phrase.lower(), guide.lower())

    def test_shared_diagnostic_allowance_and_no_self_escalation(self):
        guide = ' '.join((ROOT / '.codex/agent-guide.md').read_text().split())
        for phrase in ('300 seconds cumulative', '256 MiB cumulative',
                       '2 total:', 'remaining allowance', 'not native Codex config keys',
                       'same unresolved failure', 'candidate unchanged'):
            self.assertIn(phrase, guide)
        for _, data in profiles():
            text = data['developer_instructions']
            for phrase in ('bounded self-service diagnostics',
                           'Do not change your own model, effort, billing',
                           'launch agents through tools, CLI or API',
                           'do not read or expose credential material'):
                self.assertIn(phrase, text)

    def test_supporting_diagnostics_do_not_expand_role_deliverables(self):
        text = {d['name']: d['developer_instructions'] for _, d in profiles()}
        for name in ('project_lookup', 'project_researcher', 'project_planner'):
            self.assertIn('Do not modify tracked files', text[name])
        self.assertIn('minimal scratch', text['project_researcher'])
        self.assertNotIn('do not run builds or write fixtures', text['project_researcher'])
        self.assertIn('Do not modify production code, tracked tests or requirements',
                      text['project_integration'])
        for name in ('feature_verifier', 'feature_verifier_high'):
            self.assertIn('Do not repair', text[name])
            self.assertIn('separate session from the implementer', text[name])

    def test_execution_decision_and_deployment_guide_are_linked(self):
        decision = ROOT / 'docs/decisions/20260930-agent-execution-and-diagnostics.md'
        runbook = ROOT / 'docs/development/agent-execution.md'
        self.assertTrue(decision.is_file())
        self.assertTrue(runbook.is_file())
        self.assertIn('live role adherence', decision.read_text())
        self.assertIn('not a claim that these live checks have run', runbook.read_text())
        self.assertIn('300 seconds', runbook.read_text())
        self.assertIn('scratch data', decision.read_text().lower())

    def test_benchmark_transcription_shape_and_unknown_times(self):
        rows = chart_rows()
        self.assertEqual(len(rows), 17)
        self.assertEqual(len({(r['model'], r['effort']) for r in rows}), 17)
        for row in rows:
            self.assertEqual(row['model'], row['model'].strip())
            self.assertTrue(0 <= Decimal(row['score_percent']) <= 100)
            self.assertGreater(Decimal(row['cost_per_task_usd']), 0)
            self.assertGreater(int(row['output_tokens_per_task_rounded']), 0)
        unknown = {(r['model'], r['effort']) for r in rows if not r['decode_minutes_per_task']}
        self.assertEqual(unknown, {('gpt-6-sol', 'medium'), ('gpt-6-luna', 'medium')})

    def test_load_bearing_benchmark_values_and_comparison(self):
        rows = {(r['model'], r['effort']): r for r in chart_rows()}
        low = rows[(SOL, 'low')]
        old = rows[('gpt-6-sol', 'medium')]
        self.assertEqual((low['score_percent'], low['cost_per_task_usd']), ('30.8', '0.38'))
        self.assertEqual((old['score_percent'], old['cost_per_task_usd']), ('18.7', '1.12'))
        self.assertEqual(Decimal(low['score_percent']) - Decimal(old['score_percent']), Decimal('12.1'))
        savings = 100 * (1 - Decimal(low['cost_per_task_usd']) / Decimal(old['cost_per_task_usd']))
        self.assertEqual(savings.quantize(Decimal('0.1')), Decimal('66.1'))
        self.assertEqual(rows[(LUNA, 'medium')]['score_percent'], '2.5')
        self.assertEqual(rows[(LUNA, 'high')]['score_percent'], '4.5')

    def test_assessment_local_links_and_provenance_are_explicit(self):
        source = ROOT / 'docs/development/codex-model-routing.md'
        text = source.read_text()
        for link in re.findall(r'\]\(([^)]+)\)', text):
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (source.parent / unquote(parsed.path)).resolve()
            self.assertTrue(target.is_relative_to(ROOT))
            self.assertTrue(target.exists(), link)
        for phrase in ('owner-supplied', 'Values are rounded', 'not zero',
                       'not the expected cost', 'not the user', 'runtime check'):
            self.assertIn(phrase, text)
        self.assertEqual(len(re.findall(r'`[a-f0-9]{64}`', text)), 4)


if __name__ == '__main__':
    unittest.main()
