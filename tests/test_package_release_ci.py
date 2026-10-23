# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gate failures must retain evidence and cannot hide later suite results."""
import contextlib
import fnmatch
import importlib.util
import io
import os
import subprocess
import textwrap
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('package_release_gate', ROOT / 'scripts/check_package_release.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tests').mkdir()
        self.output = self.root / 'evidence'
        self.addCleanup(lambda: [sys.modules.pop(n, None) for n in list(sys.modules) if n.startswith('test_gate_fixture_')])

    def fixture(self, name, body):
        name = 'test_gate_fixture_' + name + '.py'
        (self.root / 'tests' / name).write_text('import unittest\nclass Fixture(unittest.TestCase):\n' + body)
        return name

    def run_gate(self, names, metadata_error=False):
        with patch.object(gate, 'source_metadata', side_effect=RuntimeError('git failed') if metadata_error else None,
                          return_value={'revision': 'a' * 40}), contextlib.redirect_stdout(io.StringIO()):
            code = gate.run(self.root, self.output, names)
        report = json.loads((self.output / 'summary.json').read_text())
        return code, report

    def test_failure_preserves_later_suite_logs_revision_and_summary(self):
        bad = self.fixture('bad', '    def test_bad(self):\n        print("failure diagnostic")\n        self.fail("deliberate failure")\n')
        good = self.fixture('good', '    def test_good(self):\n        print("later suite ran")\n')
        code, report = self.run_gate([bad, good])
        self.assertEqual(code, 1)
        self.assertEqual([e['tests'] for e in report['suites']], [1, 1])
        self.assertTrue(report['suites'][1]['passed'])
        self.assertIn('failure diagnostic', (self.output / (bad + '.log')).read_text())
        self.assertIn('later suite ran', (self.output / (good + '.log')).read_text())
        self.assertIn('a' * 40, (self.output / 'summary.txt').read_text())

    def test_missing_empty_discovery_errors_and_skips_fail(self):
        empty = self.fixture('empty', '    pass\n')
        broken = self.fixture('broken', '    invalid python syntax\n')
        skipped = self.fixture('skip', '    @unittest.skip("unexpected")\n    def test_skip(self): pass\n')
        for names in ([], ['missing.py'], [empty], [broken], [skipped]):
            with self.subTest(names=names):
                code, report = self.run_gate(names)
                self.assertEqual(code, 1)
                self.assertFalse(report['passed'])
                self.assertTrue((self.output / 'summary.txt').is_file())

    def test_bounded_log_and_metadata_failure(self):
        noisy = self.fixture('noisy', '    def test_noise(self):\n        print("雪" * 150000)\n')
        code, report = self.run_gate([noisy], metadata_error=True)
        self.assertEqual(code, 1)
        self.assertIn('git failed', report['errors'][0])
        self.assertLessEqual((self.output / (noisy + '.log')).stat().st_size, gate.LOG_LIMIT)
        self.assertEqual(report['suites'][0]['tests'], 1)

    def test_late_failure_after_flood_retains_diagnostic_and_failed_outcome(self):
        noisy = self.fixture('late_failure', '    def test_flood(self):\n        print("雪" * 150000)\n        self.fail("late failure diagnostic retained")\n')
        code, report = self.run_gate([noisy])
        self.assertEqual(code, 1)
        self.assertFalse(report['passed'])
        raw = (self.output / (noisy + '.log')).read_bytes()
        self.assertLessEqual(len(raw), gate.LOG_LIMIT)
        self.assertIn(b'earlier log output truncated', raw)
        self.assertIn(b'late failure diagnostic retained', raw)
        self.assertIn(b'FAILED (failures=1)', raw)

    def test_preparation_failures_keep_bounded_error_logs_and_nonzero_status(self):
        text = (ROOT / '.github/workflows/package-release.yml').read_text()
        (self.root / 'package-release-evidence').mkdir()
        for name, log in (('Fetch and verify exact bounded public test input', 'fixture-preparation.log'),
                          ('Prepare only pinned public Mainsail source', 'mainsail-preparation.log')):
            step = text.split('      - name: ' + name + '\n', 1)[1].split('      - name:', 1)[0]
            script = textwrap.dedent(step.split('        run: |\n', 1)[1])
            # Exercise the actual workflow shell wrapper with a failed input
            # command, without network access or mutating any submodule.
            head = script.split('\n', 2)[:2]
            script = '\n'.join(head) + "\npython3 -c 'print(150000 * chr(120))'\necho preparation-diagnostic >&2\nfalse\necho wrongly-continued\nPREP\n"
            result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script],
                                    env={**os.environ, 'RUNNER_TEMP': str(self.root)}, capture_output=True)
            self.assertNotEqual(result.returncode, 0, result.stderr)
            raw = (self.root / 'package-release-evidence' / log).read_bytes()
            self.assertLessEqual(len(raw), gate.LOG_LIMIT)
            self.assertIn(b'preparation-diagnostic', raw)
            self.assertNotIn(b'wrongly-continued', raw)

    def test_workflow_triggers_permissions_inputs_and_failure_artifact(self):
        # No YAML dependency on hosted runners: inspect the deliberately small
        # workflow's event blocks and concrete action contracts.
        text = (ROOT / '.github/workflows/package-release.yml').read_text()
        self.assertIn('pull_request:\n    branches: [main]\n    paths: &inputs', text)
        self.assertIn('push:\n    branches: [main]\n    paths: *inputs', text)
        self.assertIn('workflow_dispatch:', text)
        paths_block = text.split('paths: &inputs\n', 1)[1].split('  push:', 1)[0]
        patterns = [line.strip()[3:-1] for line in paths_block.splitlines() if line.strip().startswith("- '")]
        for changed in ('scripts/package_mainsail.py', 'tests/test_prepare_release.py',
                        'configs/host/npm-standard-license-texts.json', 'patches/mainsail/fix.patch',
                        'runtime/bin/helper', 'ui/cockpit/main.js', 'extensions/helper.py',
                        'upstream/mainsail', '.gitmodules', 'upstream-lock.json',
                        'LICENSE', 'LICENSING.md', 'docs/features/package-release-ci/proposal.md',
                        '.github/workflows/package-release.yml'):
            self.assertTrue(any(fnmatch.fnmatchcase(changed, pattern) for pattern in patterns), changed)
        self.assertFalse(any(fnmatch.fnmatchcase('unrelated.txt', pattern) for pattern in patterns))
        self.assertIn('contents: read', text)
        self.assertIn('persist-credentials: false', text)
        self.assertIn('if: always()', text)
        self.assertIn('if-no-files-found: error', text)
        self.assertIn('actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02', text)
        self.assertIn('SV08_GCODEVIEWER_ARCHIVE:', text)
        self.assertIn('git submodule update --init --depth 1 -- upstream/mainsail', text)


if __name__ == '__main__':
    unittest.main()
