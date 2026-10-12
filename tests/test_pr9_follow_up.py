"""Source manifest for installed PR9 checks and focused navigation contract tests.

The installed runner invokes --manifest to compare guest public assets/runtime to
these candidate bytes, including the upstream staging composition of index.html.
This command reads project sources only; it provisions nothing.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from stage_printer_ui import compose_host


def installed_source_manifest():
    files = {}
    def add(target, raw):
        files[target] = hashlib.sha256(raw).hexdigest()
    for area in ('host', 'printer'):
        for source in sorted((REPO / 'ui' / area).rglob('*')):
            if source.is_file() and not source.is_symlink() and not (area == 'printer' and source.name == 'session.js'):
                raw = source.read_bytes()
                if area == 'host' and source.name == 'index.html':
                    raw = compose_host(raw)
                add('/usr/share/cockpit/sv08-'+area+'/'+source.relative_to(REPO/'ui'/area).as_posix(), raw)
    # Optional runtime files are compared if installed; these entry points and
    # their safety/read contracts are mandatory for this composed journey.
    mandatory = ['sv08_admin.py', 'sv08_admin_upload.py', 'sv08_view.py', 'sv08_state.py',
                 'sv08_admin_images.py', 'sv08_admin_jobs.py', 'sv08_admin_history.py',
                 'sv08_admin_resolution.py', 'sv08_staging.py', 'sv08_bundle.py',
                 'sv08_boot.py', 'sv08_rauc.py', 'sv08_update_policy.py', 'sv08_identity.py',
                 'sv08_network.py', 'sv08_software.py', 'sv08_mainsail_access.py',
                 'sv08_printer_helper.py', 'sv08_printer_store.py', 'sv08_printer_catalog.py', 'sv08_admission.py']
    runtime = {'/usr/lib/sv08/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((REPO/'runtime').glob('sv08_*.py')) if not p.is_symlink()}
    return {'assets':files, 'runtime':runtime,
            'required_runtime':['/usr/lib/sv08/'+name for name in mandatory],
            'runner_sources':{name:hashlib.sha256((REPO/name).read_bytes()).hexdigest()
                              for name in ('tests/cockpit_composed_browser.mjs',
                                           'tests/cockpit_upload_cases.mjs',
                                           'tests/browser_runtime.mjs',
                                           'tests/test_pr9_follow_up.py',
                                           'scripts/stage_printer_ui.py')}}


class PR9FollowUpTests(unittest.TestCase):
    def test_back_focus_finishes_after_native_restoration_without_stale_focus(self):
        source = (REPO/'ui/host/navigation.js').read_text()
        start = source.index("    window.addEventListener('popstate', () => {")
        end = source.index('\n    });', start)+8
        listener = source[start:end]
        program = """
import assert from 'node:assert/strict';
let callback;let timers=[];let current='images';let focus='indicator';let dialog=false;
const window={addEventListener:(_,fn)=>callback=fn};
const document={querySelector:()=>dialog};
const paint=shouldFocus=>{assert.equal(shouldFocus,false);current='settings'};
const focusPage=()=>{focus=current+' heading'};
const setTimeout=fn=>timers.push(fn);
"""+listener+"""
callback();focus='indicator'; // Native restore occurs after the event.
timers.shift()();assert.equal(focus,'settings heading');
callback();current='network';focus='network control';
timers.shift()();assert.equal(focus,'network control');
callback();dialog=true;focus='dialog control';
timers.shift()();assert.equal(focus,'dialog control');
"""
        result = subprocess.run(['node', '--input-type=module', '-e', program],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_manifest_uses_real_composition_and_current_sources(self):
        manifest = installed_source_manifest()
        self.assertEqual(manifest['assets']['/usr/share/cockpit/sv08-host/index.html'],
                         hashlib.sha256(compose_host((REPO/'ui/host/index.html').read_bytes())).hexdigest())
        self.assertGreater(len(manifest['assets']), 15)
        for target in manifest['required_runtime']:
            self.assertIn(target, manifest['runtime'])

    def test_indicator_selects_pending_or_active_operation_without_request(self):
        # Execute the actual listener with a minimal DOM, asserting the observable
        # navigation/focus/scroll order and that no RPC is available to mutate.
        source = (REPO/'ui/host/app.js').read_text()
        start = source.index("$('operation-indicator').addEventListener('click', () => {")
        end = source.index('\n});', start)+4
        listener = source[start:end]
        program = """
import assert from 'node:assert/strict';
let callback;let trace=[];let pending={id:'wanted'};
const item=(id,phase)=>({dataset:{jobId:id,phase},focus:()=>trace.push('focus '+id),scrollIntoView:()=>trace.push(id)});
let items=[item('old','succeeded'),item('active','running'),item('wanted','failed')];
const elements={'operation-indicator':{addEventListener:(_,cb)=>callback=cb},
 'jobs':{querySelectorAll:()=>items},'image-history-title':{focus:()=>trace.push('focus'),scrollIntoView:()=>trace.push('history')},
 'image-history':{scrollIntoView:()=>trace.push('history')}};
const $=id=>elements[id];const page=name=>trace.push(name);
const localStorage={getItem:()=>JSON.stringify(pending)};
"""+listener+"""
callback();assert.deepEqual(trace,['images','focus wanted','wanted']);trace=[];
pending=null;callback();assert.deepEqual(trace,['images','focus active','active']);trace=[];
items=[];callback();assert.deepEqual(trace,['images','focus','history']);
"""
        result = subprocess.run(['node', '--input-type=module', '-e', program],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    if sys.argv[1:] == ['--manifest']:
        print(json.dumps(installed_source_manifest(), sort_keys=True))
    else:
        unittest.main()
