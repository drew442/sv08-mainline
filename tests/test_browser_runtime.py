"""Exercise real launcher child failure/timeout handling without a browser."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class BrowserRuntimeTests(unittest.TestCase):
    def test_finite_status_diagnostic_redacts_and_retains_exit(self):
        program = f"""
import {{finiteStatusDiagnostic}} from {json.dumps((REPO / 'tests/browser_runtime.mjs').as_uri())};
import assert from 'node:assert/strict';
const report=finiteStatusDiagnostic('host',{{message:'denied synthetic-secret\\nread',
    problem:'access-denied',exit_status:1,exit_signal:null,stack:'private transcript'}},['synthetic-secret']);
assert.deepEqual(report,{{area:'host',method:'status',message:'denied [redacted] read',
    problem:'access-denied',exit_status:1,exit_signal:null}});
assert(!JSON.stringify(report).includes('private transcript'));
assert.throws(()=>finiteStatusDiagnostic('arbitrary',{{}}),/Unsupported/);
assert.equal(finiteStatusDiagnostic('printer',{{message:'x'.repeat(1000)}}).message.length,512);
"""
        result = subprocess.run(['node', '--input-type=module', '-e', program],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_launcher(self, script, assertions):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Use the supported installed Node runtime')
        with tempfile.TemporaryDirectory(prefix='br-') as directory:
            root = Path(directory)
            fake = root / 'fake-browser'
            fake.write_text('#!/usr/bin/env node\n'+script)
            fake.chmod(0o700)
            program = f"""
import {{startBrowser}} from {json.dumps((REPO / 'tests/browser_runtime.mjs').as_uri())};
import fs from 'node:fs';import assert from 'node:assert/strict';
const browser=startBrowser({{chrome:{json.dumps(str(fake))},output:{json.dumps(str(root))},timeoutMs:500}});
try {{ {assertions} }} finally {{ await browser.stop(); }}
const report=JSON.parse(fs.readFileSync(browser.diagnosticPath));
assert.equal(report.cleanup,'complete');assert.equal(fs.existsSync(browser.profile),false);
console.log(JSON.stringify(report));
"""
            result = subprocess.run([node, '--input-type=module', '-e', program],
                                    capture_output=True, text=True, timeout=10,
                                    env={**os.environ, 'SV08_UI_OWNED_PROCESS_GROUP':'0',
                                         'SV08_BROWSER_PROFILE_ROOT':str(root)})
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertIsInstance(report['pid'], int)
            self.assertEqual(report['status'], 'failed')
            self.assertIn('timeout_ms', report)
            self.assertEqual(report['cleanup'], 'complete')
            return report, (root / 'browser.log').read_text()

    def test_early_exit_retains_stderr_and_exit_status(self):
        report, log = self.run_launcher(
            "console.error('fixture startup failure');process.exit(23);",
            "await assert.rejects(browser.ready,/exited before DevTools/);"
            "assert.equal(browser.child.exitCode,23);")
        self.assertEqual(report['exit_code'], 23)
        self.assertIn('fixture startup failure', log)

    def test_timeout_retains_live_handle_until_owned_cleanup(self):
        report, log = self.run_launcher(
            "console.error('fixture never becomes ready');setInterval(()=>{},1000);",
            "await assert.rejects(browser.ready,/handle retained/);"
            "assert.equal(browser.child.exitCode,null);process.kill(browser.child.pid,0);"
            "assert.equal(fs.existsSync(browser.profile),true);")
        self.assertEqual(report['signal'], 'SIGTERM')
        self.assertIn('fixture never becomes ready', log)


if __name__ == '__main__':
    unittest.main()
