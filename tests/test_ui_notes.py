"""Public-state presentation contracts; browser acceptance is a separate command."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = os.environ.get('SV08_NODE') or shutil.which('node')


class OwnerNotes(unittest.TestCase):
    @unittest.skipUnless(NODE, 'Installed Node tool is required')
    def test_public_state_outcomes(self):
        # Evaluate the same pure production reducers, without a DOM or bridge.
        source = (ROOT / 'ui/host/navigation.js').read_text().split('(() => {', 1)[0]
        cases = r'''
const assert=require('node:assert/strict');
const p=window.sv08Presentation;
for(const d of [{device:'lo'}, {device:'other',type:'loopback'},
 {device:'p2p-dev-wlan0',state:'disconnected',uuid:'stale',connection:'Saved'},
 {device:'p2p-dev-wlan1',state:'unavailable'}, {device:'p2p-dev-wlan2',state:'unmanaged'}])assert.equal(p.visibleDevice(d),false);
for(const d of [{device:'wlan0',state:'disconnected'},{device:'eth0',state:'connected'},
 {device:'p2p-dev-wlan0',state:'connected',uuid:'active'},
 {device:'p2p-dev-wlan0',state:'connecting (prepare)'}, {device:'p2p-dev-wlan0'}])assert.equal(p.visibleDevice(d),true);
for(const result of ['reboot-queued','reboot-observed']){
 const value={transaction:{phase:'failed'},feed_status:{result},pending:{slot:'B',release:'new',phase:'armed'}};
 const before=JSON.stringify(value);const outcome=p.update(value);
 assert.equal(outcome.tone,'error');assert.equal(outcome.title,'Update failed');
 assert.doesNotMatch(outcome.detail,/health.*failed|restart requested/i);assert.equal(JSON.stringify(value),before);
}
for(const [phase,tone] of [['complete','success'],['cancelled','neutral'],['preparing','warning'],['installing','warning'],['staged','warning'],['arming','warning'],['armed','warning'],['confirming','warning'],['alien','neutral']])assert.equal(p.update({transaction:{phase},feed_status:{result:'reboot-queued'}}).tone,tone);
assert.match(p.update({boot:{slot:'B'},pending:{slot:'B',release:'new',phase:'trial'}}).title,/Trial/);
assert.equal(p.update({pending:{slot:'B',release:'new',phase:'armed'}}).tone,'warning');
assert.equal(p.update({feed_status:{result:'reboot-observed'}}).tone,'neutral');
console.log(JSON.stringify({network:true,status:true,no_mutation:true}));
'''
        result = subprocess.run([NODE, '-e', 'global.window={};\n' + source + cases],
                                text=True, capture_output=True, check=True, timeout=10)
        self.assertTrue(json.loads(result.stdout)['no_mutation'])


if __name__ == '__main__':
    unittest.main()
