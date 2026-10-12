"""Focused preference behavior without a browser or authority bridge.

Rendered composed checks live in theme_browser.mjs; this unit check executes the
same preference initializer with storage faults and cached pre-feature HTML.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = os.environ.get('SV08_TEST_NODE') or shutil.which('node')


@unittest.skipUnless(NODE, 'Node is required for frontend behavior checks')
class AppearancePreferenceTests(unittest.TestCase):
    def test_preference_and_storage_failures(self):
        source = (ROOT / 'ui/host/navigation.js').read_text()
        start = source.index('// Appearance is ordinary-access')
        end = source.index('\n(() => {', start + source[start:].index('})();') + 5)
        initializer = source[start:end]
        script = r'''
const assert=require('node:assert/strict'), vm=require('node:vm');
const source=SOURCE;
function page(saved, fault, missing=false) {
 const listeners={}, choice={value:'light',addEventListener:(name,fn)=>listeners[name]=fn};
 const status={textContent:'Choose a theme to save it in this browser.'};
 let writes=0;
 const context={document:{documentElement:{dataset:{}},getElementById:id=>missing?null:id==='appearance-theme'?choice:status},
  localStorage:{getItem:()=>{if(['read','read-only'].includes(fault))throw Error('denied');return saved;},setItem:(key,value)=>{assert.equal(key,'sv08.appearance');if(fault && fault!=='read-only')throw Error('full');saved=value;writes++;}}};
 if(fault==='accessor')Object.defineProperty(context,'localStorage',{get(){throw Error('denied accessor');}});
 vm.runInNewContext(source,context);
 return {choice,status,root:context.document.documentElement,choose:value=>{choice.value=value;listeners.change();},saved:()=>saved,writes:()=>writes};
}
const fresh=page(null);assert.equal(fresh.root.dataset.theme,'light');assert.equal(fresh.writes(),0);
fresh.choose('dark');assert.equal(fresh.root.dataset.theme,'dark');assert.equal(fresh.saved(),'dark');assert.match(fresh.status.textContent,/Saved in this browser/);
const reload=page(fresh.saved());assert.equal(reload.choice.value,'dark');assert.equal(reload.root.dataset.theme,'dark');assert.equal(reload.writes(),0);
reload.choose('light');assert.equal(reload.saved(),'light');
const invalid=page('unsupported');assert.equal(invalid.root.dataset.theme,'light');assert.equal(invalid.writes(),0);
for(const fault of ['read','write','accessor']){const failed=page('light',fault);failed.choose('dark');assert.equal(failed.root.dataset.theme,'dark');assert.equal(failed.saved(),'light');assert.match(failed.status.textContent,/storage is unavailable.*reload/);}
const readOnly=page('light','read-only');readOnly.choose('dark');assert.equal(readOnly.root.dataset.theme,'dark');assert.equal(readOnly.saved(),'dark');assert.equal(readOnly.writes(),1);assert.match(readOnly.status.textContent,/could not be read.*may reset.*reload/);
assert.equal(page('dark',null,true).root.dataset.theme,undefined);
'''.replace('SOURCE', json.dumps(initializer))
        result = subprocess.run([NODE, '-e', script], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
