"""Source-only routing contracts and real subprocess tests using disposable doubles.

These tests do not claim installed Cockpit, live Codex or human usability evidence.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_ui', ROOT / 'scripts/check_ui.py')
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


class UiRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        for name in ['scripts', 'tests', 'runtime', 'ui/host']:
            (self.root / name).mkdir(parents=True)
        (self.root / 'scripts/check_ui.py').write_text((ROOT / 'scripts/check_ui.py').read_text())
        (self.root / 'scripts/prepare_host_os.py').write_text('# disposable test double\n')
        (self.root / 'runtime/app.py').write_text('# original source\n')
        (self.root / 'ui/host/index.html').write_text('<button>Test fixture</button>')
        self.preview()
        self.browser()

    def tearDown(self):
        self.tmp.cleanup()

    def preview(self, address='http://127.0.0.1:12345', fail=False):
        (self.root / ui.FIXTURE).write_text(
            'import argparse,json,os,time\nfrom pathlib import Path\n'
            'p=argparse.ArgumentParser();p.add_argument("--work");p.add_argument("--execute",action="store_true")\n'
            'a=p.parse_args();w=Path(a.work);w.mkdir(parents=True)\n'
            '(w/"pid").write_text(str(os.getpid()))\n'
            + ('raise SystemExit(9)\n' if fail else
               f'(w/"server.json").write_text(json.dumps({{"url": {address!r}}}))\ntime.sleep(30)\n'))

    def browser(self, code='pass', result=True):
        (self.root / ui.BROWSER).write_text(
            'import json,os,subprocess,sys,time\nfrom pathlib import Path\n'
            'w=Path(sys.argv[3]);w.mkdir();(w/"pid").write_text(str(os.getpid()))\n'
            + code + '\n'
            + f'(w/"result.json").write_text(json.dumps({{"passed": {result!r}}}))\n'
            '(w/"example.png").write_bytes(b"synthetic evidence, not a rendered image")\n')

    def settings(self, **kwargs):
        return ui.plan(self.root, 'build/run', sys.executable, sys.executable,
                       kwargs.get('timeout', 5), kwargs.get('max_mib', 32))

    def run_check(self, **kwargs):
        return ui.run_checks(self.root, self.settings(**kwargs))

    def test_plan_is_non_mutating_and_uses_argv_not_shell(self):
        settings = self.settings()
        self.assertFalse((self.root / 'build').exists())
        self.assertIsInstance(settings['browser_command'], list)
        self.assertIn('--execute', settings['fixture_command'])

    def test_cli_inspection_does_not_launch_or_create_fixture(self):
        result = subprocess.run([sys.executable, str(self.root / 'scripts/check_ui.py'),
                                 '--work', 'build/run', '--node', sys.executable,
                                 '--chromium', sys.executable], capture_output=True, text=True, check=True)
        self.assertFalse(json.loads(result.stdout)['execute'])
        self.assertFalse((self.root / 'build').exists())

    def test_work_cannot_escape_build_or_reuse_existing_output(self):
        for path in ['build', 'build/../outside', '/tmp/elsewhere']:
            with self.subTest(path=path), self.assertRaises(ui.CheckError):
                ui.work_path(self.root, path)
        (self.root / 'build/run').mkdir(parents=True)
        (self.root / 'build/run/keep').write_text('keep')
        with self.assertRaises(ui.CheckError):
            self.settings()
        self.assertEqual((self.root / 'build/run/keep').read_text(), 'keep')

    def test_symlink_work_is_rejected(self):
        (self.root / 'build').symlink_to(self.root / 'runtime', target_is_directory=True)
        with self.assertRaises(ui.CheckError):
            self.settings()

    def test_execution_rechecks_plan_before_creating_output(self):
        settings = self.settings()
        Path(settings['work']).mkdir(parents=True)
        with self.assertRaises(ui.CheckError):
            ui.run_checks(self.root, settings)

    def test_allowance_and_missing_tool_errors_are_explicit(self):
        for timeout, size in [(0, 1), (1801, 1), (float('nan'), 1), (1, 0), (1, 4097)]:
            with self.subTest(timeout=timeout, size=size), self.assertRaises(ui.CheckError):
                ui.plan(self.root, 'build/run', sys.executable, sys.executable, timeout, size)
        with self.assertRaises(ui.CheckError):
            ui.executable('sv08-nonexistent-test-executable')

    def test_source_snapshot_includes_untracked_source(self):
        before = ui.source_snapshot(self.root)
        (self.root / 'ui/host/extra.js').write_text('new UI source')
        after = ui.source_snapshot(self.root)
        self.assertNotEqual(before['sha256'], after['sha256'])
        self.assertIn('ui/host/extra.js', after['files'])

    def test_source_symlink_and_missing_input_are_rejected(self):
        target = self.root / 'runtime/app.py'
        target.unlink()
        target.symlink_to(self.root / 'ui/host/index.html')
        with self.assertRaises(ui.CheckError):
            ui.source_snapshot(self.root)
        target.unlink()
        (self.root / ui.BROWSER).unlink()
        with self.assertRaises(ui.CheckError):
            ui.source_snapshot(self.root)

    def test_passing_run_records_evidence_not_ux_or_release_approval(self):
        result = self.run_check()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['automated_checks'], 'passed')
        self.assertEqual(result['visual_assessment'], 'not_performed')
        self.assertEqual(result['standard_project_tests'], 'not_run')
        self.assertEqual(result['installed_cockpit'], 'not_tested')
        self.assertFalse(result['physical_hardware'])
        self.assertIn('browser/example.png', result['artifacts'])
        self.assertEqual(len(result['artifacts']['browser/result.json']['sha256']), 64)
        self.assertNotIn('profile', json.dumps(result['artifacts']))
        stored = json.loads((self.root / 'build/run/summary.json').read_text())
        self.assertEqual(stored, result)
        self.assert_stopped(int((self.root / 'build/run/fixture/pid').read_text()))

    def test_browser_failure_retains_logs_without_escalating_a_model(self):
        self.browser('print("specific test failure", flush=True);raise SystemExit(7)')
        result = self.run_check()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['browser_exit_code'], 7)
        self.assertEqual(result['automated_checks'], 'failed')
        self.assertEqual(result['next_action'], 'triage-failure-with-existing-evidence')
        self.assertIn('specific test failure', (self.root / 'build/run/runner.log').read_text())
        self.assertNotIn('model', result)

    def test_false_and_string_results_cannot_pass(self):
        for value in [False, 'true', 1]:
            with self.subTest(value=value):
                self.browser(result=value)
                settings = self.settings()
                settings['work'] += '-' + str(value)
                settings['fixture_command'][-2] = settings['work'] + '/fixture'
                settings['browser_command'][-2:] = [settings['work'] + '/fixture', settings['work'] + '/browser']
                self.assertEqual(ui.run_checks(self.root, settings)['status'], 'failed')

    def test_malformed_result_cannot_pass(self):
        self.browser('(w/"result.json").write_text("{");raise SystemExit(0)')
        self.assertEqual(self.run_check()['status'], 'failed')

    def test_missing_result_cannot_pass(self):
        self.browser('raise SystemExit(0)')
        result = self.run_check()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Missing regular result', result['error'])

    def test_invalid_port_is_rejected(self):
        self.preview(address='http://127.0.0.1:99999')
        self.assertIn('Invalid fixture port', self.run_check()['error'])

    def test_cli_termination_keeps_evidence_and_stops_owned_processes(self):
        self.browser('time.sleep(30)')
        process = subprocess.Popen([sys.executable, str(self.root / 'scripts/check_ui.py'),
                                    '--work', 'build/run', '--node', sys.executable,
                                    '--chromium', sys.executable, '--execute'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            pid_file = self.root / 'build/run/browser/pid'
            deadline = time.monotonic() + 5
            while not pid_file.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(pid_file.exists())
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 1, stderr)
            self.assertEqual(json.loads(stdout)['status'], 'failed')
            summary = json.loads((self.root / 'build/run/summary.json').read_text())
            self.assertIn('Interrupted by signal', summary['error'])
            self.assert_stopped(int(pid_file.read_text()))
            self.assert_stopped(int((self.root / 'build/run/fixture/pid').read_text()))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

    def test_source_mutation_invalidates_otherwise_passing_check(self):
        self.browser('Path("runtime/app.py").write_text("changed while testing")')
        result = self.run_check()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stage'], 'source-consistency')
        self.assertIn('Source changed', result['error'])

    def test_non_loopback_url_is_rejected(self):
        self.preview(address='http://example.com:9090')
        result = self.run_check()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stage'], 'fixture')
        self.assertIn('loopback', result['error'])

    def test_fixture_failure_is_not_reported_as_a_ui_assertion(self):
        self.preview(fail=True)
        result = self.run_check()
        self.assertEqual(result['stage'], 'fixture')
        self.assertEqual(result['automated_checks'], 'not_run')

    def test_timeout_cleans_descendants_but_not_unrelated_process(self):
        child_code = ('import signal,time;from pathlib import Path;'
                      'signal.signal(signal.SIGTERM,signal.SIG_IGN);'
                      'Path("build/run/browser/child-ready").touch();time.sleep(30)')
        self.browser(f'child=subprocess.Popen([sys.executable,"-c",{child_code!r}]);'
                     '(w/"child-pid").write_text(str(child.pid));time.sleep(30)')
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
        clock = time.monotonic
        def deadline_after_ready():
            # Trigger the deadline only after the stubborn descendant is ready.
            # A loaded CI host must not time out before this case reaches its subject.
            ready = self.root / 'build/run/browser/child-ready'
            return clock() + (30 if ready.exists() else 0)
        try:
            with patch.object(ui.time, 'monotonic', side_effect=deadline_after_ready):
                result = self.run_check(timeout=15)
            self.assertEqual(result['status'], 'failed')
            self.assertIn('timeout', result['error'])
            self.assert_stopped(int((self.root / 'build/run/browser/child-pid').read_text()))
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=3)

    def assert_stopped(self, pid):
        # Orphaned terminated children may briefly remain zombies until reaped.
        for _ in range(20):
            stat = Path(f'/proc/{pid}/stat')
            if not stat.exists() or stat.read_text().split()[2] == 'Z':
                return
            time.sleep(0.05)
        self.fail(f'Owned process remains running: {pid}')

    def test_output_allowance_failure_retains_compact_summary(self):
        self.browser('(w/"large").write_bytes(b"x" * (2 * 1024 * 1024));time.sleep(1)')
        result = self.run_check(max_mib=1)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Output allowance', result['error'])
        self.assertLess((self.root / 'build/run/summary.json').stat().st_size, 16384)


class UiContextTests(unittest.TestCase):
    def test_skill_is_explicit_only_and_small(self):
        skill = ROOT / '.agents/skills/sv08-ui-ux'
        body = (skill / 'SKILL.md').read_text()
        self.assertLessEqual(len(body.encode()), 3200)
        description = next(line for line in body.splitlines() if line.startswith('description:'))
        self.assertLessEqual(len(description.encode()), 256)
        self.assertIn('allow_implicit_invocation: false', (skill / 'agents/openai.yaml').read_text())
        self.assertIn('No', (ROOT / 'docs/development/ui-ux-workflow.md').read_text())
        self.assertIn('Do not read both merely because they exist', body)

    def test_shared_entry_budgets_are_not_raised_for_ui(self):
        for name, limit in [('AGENTS.md', 7600), ('.codex/agent-guide.md', 13000)]:
            self.assertLessEqual((ROOT / name).stat().st_size, limit)
        self.assertNotIn('$sv08-ui-ux', (ROOT / 'AGENTS.md').read_text())
        for path in (ROOT / '.codex/agents').glob('*.toml'):
            self.assertNotIn('sv08-ui-ux', path.read_text())

    def test_browser_can_share_only_the_wrapper_owned_process_group(self):
        browser = (ROOT / ui.BROWSER).read_text()
        self.assertIn("process.env.SV08_UI_OWNED_PROCESS_GROUP === '1'", browser)
        self.assertIn('detached:!ownedGroup', browser)
        self.assertIn("ownedGroup?child.kill('SIGTERM'):process.kill(-child.pid,'SIGTERM')", browser)

    def test_workflow_reuses_roles_and_preserves_authority(self):
        guide = (ROOT / 'docs/development/ui-ux-workflow.md').read_text()
        for phrase in ['two-child cap', 'Workers never launch', 'No child acquires Git',
                       'not zero overhead', 'not permission to merge',
                       'standard project tests', 'no silent', 'existing low-effort route']:
            self.assertIn(phrase, guide)
        config_paths = list((ROOT / '.agents/skills/sv08-ui-ux').rglob('*.toml'))
        self.assertEqual(config_paths, [])  # Skills do not masquerade as model settings.


if __name__ == '__main__':
    unittest.main()
