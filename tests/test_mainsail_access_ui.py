"""Offline Chromium journeys; Cockpit and access backend are disposable mocks."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
NODE = Path('/home/drew/sv08-mainline/build/mainsail-package-v6/node-v22.23.2-linux-x64/bin/node')
CHROME = Path('/home/drew/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome')
SCRATCH = Path('/home/drew/.sv08-mainsail-access-ui-20261009')

JOURNEYS = r'''
import fs from 'node:fs';import http from 'node:http';import path from 'node:path';import {spawn} from 'node:child_process';import {setTimeout as delay} from 'node:timers/promises';import assert from 'node:assert/strict';
const [repo,chrome,work]=process.argv.slice(2);const profile=path.join(work,'profile');const downloads=path.join(work,'downloads');fs.mkdirSync(downloads);
const mock=`window.sv08Session={elevated:true,ready:Promise.resolve()};window.requests=[];window.mode='password';window.certs=[];window.hold=false;window.holdCreate=false;window.held=[];
window.cockpit={spawn(args,options){if(args.join(' ')!='/usr/bin/python3 /usr/lib/sv08/sv08_mainsail_access.py'||options.superuser!=='require')throw Error('wrong transport');return {input(text){const r=JSON.parse(text);requests.push(r);if((r.method==='status'&&hold)||(r.method==='certificate.create'&&holdCreate))return new Promise(resolve=>held.push(resolve));if(r.method==='settings')mode=r.mode;if(r.method==='certificate.create')certs.push({id:'one',label:r.label,fingerprint:'AA:BB',expires:'2027-10-09',revoked:false});if(r.method==='certificate.revoke')certs[0].revoked=true;return Promise.resolve(JSON.stringify({ok:true,result:r.method==='certificate.create'?{certificate:certs[0],filename:'browser.p12',pkcs12_base64:'cHJpdmF0ZQ=='}:{mode,username:'sv08',certificates:certs}}));}}}};`;
const server=http.createServer((req,res)=>{let name=req.url.split('?')[0];if(name==='/') {res.setHeader('Content-Type','text/html');res.end(fs.readFileSync(repo+'/ui/host/index.html','utf8').replace(/<script[^>]*>.*?<\/script>/g,'') .replace('</head>','<script>'+mock+'</script><script defer src="/navigation.js"></script><script defer src="/mainsail-access.js"></script></head>'));}else if(['/navigation.js','/mainsail-access.js','/style.css'].includes(name)){res.end(fs.readFileSync(repo+'/ui/host'+name));}else{res.statusCode=404;res.end();}});await new Promise(r=>server.listen(0,'0.0.0.0',r));const port=server.address().port;
let child,socket;try{
child=spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-background-networking','--no-proxy-server','--host-resolver-rules=MAP printer.test 127.0.0.1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore',detached:true});let debug;for(let i=0;i<100;i++){try{debug=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];break;}catch{await delay(50)}}assert(debug);
const tabs=await(await fetch('http://127.0.0.1:'+debug+'/json/list')).json();socket=new WebSocket(tabs.find(x=>x.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j});let id=0;const pending=new Map();const send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;const timer=setTimeout(()=>reject(Error('CDP timeout')),10000);pending.set(n,{resolve,reject,timer});socket.send(JSON.stringify({id:n,method,params}));});socket.onmessage=({data})=>{const e=JSON.parse(data),p=pending.get(e.id);if(p){pending.delete(e.id);clearTimeout(p.timer);e.error?p.reject(Error(JSON.stringify(e.error))):p.resolve(e.result)}};
const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value};const until=async expression=>{for(let i=0;i<100;i++){if(await ev(expression))return;await delay(30)}throw Error('condition: '+expression)};const click=id=>ev(`document.getElementById('${id}').click()`);const fill=(id,value)=>ev(`document.getElementById('${id}').value=${JSON.stringify(value)};document.getElementById('${id}').dispatchEvent(new Event('input'))`);const choose=mode=>ev(`document.querySelector('input[name="access-mode"][value="${mode}"]').click()`);const close=value=>ev(`document.getElementById('access-review').close('${value}')`);
await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloads});await send('Page.navigate',{url:'http://localhost:'+port+'/#mainsail-access'});await until(`document.getElementById('access-current')?.textContent==='Password'`);
// Sidebar entry with an already elevated session and a delayed status reply.
await ev(`hold=true;sv08Navigation.go('overview')`);
await ev(`document.querySelector('[data-page="mainsail-access"]').click()`);
await until('held.length===1');
assert(await ev(`sv08Session.elevated && document.getElementById('access-status').textContent.includes('Loading Mainsail access')`));
assert(await ev(`document.getElementById('access-create').disabled && !document.getElementById('access-refresh').disabled`));
await ev(`held.shift()(JSON.stringify({ok:true,result:{mode:'password',username:'sv08',certificates:[]}}));hold=false`);
await until(`!document.getElementById('access-create').disabled`);
// Real denial must still disable controls; reauthorization has a distinct pending state.
await ev(`sv08Session.elevated=false;window.dispatchEvent(new Event('sv08-authority-changed'))`);
assert(await ev(`document.getElementById('access-status').textContent.includes('Administrator access is required') && document.getElementById('access-refresh').disabled`));
await ev(`hold=true;sv08Session.elevated=true;window.dispatchEvent(new Event('sv08-authority-changed'))`);
await until('held.length===1');
assert(await ev(`document.getElementById('access-status').textContent.includes('Loading Mainsail access')`));
await ev(`held.shift()(JSON.stringify({ok:true,result:{mode:'password',username:'sv08',certificates:[]}}));hold=false`);
await until(`!document.getElementById('access-create').disabled`);
assert(await ev(`document.getElementById('access-apply').disabled`));await fill('access-password','new secret');await fill('access-password-confirm','wrong');await click('access-apply');assert(await ev(`document.getElementById('access-status').textContent.includes('match')`));await fill('access-password-confirm','new secret');await click('access-apply');await close('cancel');await delay(50);assert.equal(await ev(`requests.filter(x=>x.method==='settings').length`),0);
await fill('access-password','new secret');await fill('access-password-confirm','new secret');await click('access-apply');await close('confirm');await until(`requests.some(x=>x.method==='settings') && !document.getElementById('access-refresh').disabled`);assert.deepEqual(await ev(`requests.find(x=>x.method==='settings')`),{method:'settings',mode:'password',password:'new secret'});assert.equal(await ev(`document.getElementById('access-password').value`),'');
await choose('none');await click('access-apply');assert(await ev(`document.getElementById('access-review-detail').textContent.includes('Anyone who can reach Mainsail can control the printer')`));await close('confirm');await until(`document.getElementById('access-current').textContent==='No login'`);assert(await ev(`document.getElementById('access-apply').disabled`));
await fill('access-label','My browser');await fill('access-download-password','private pass');await fill('access-download-confirm','private pass');await click('access-create');await close('confirm');await until(`document.getElementById('access-status').textContent.includes('downloaded once')`);assert.equal(await ev('mode'),'none');assert.deepEqual(await ev(`requests.find(x=>x.method==='certificate.create')`),{method:'certificate.create',label:'My browser',password:'private pass'});for(let i=0;i<100&&!fs.existsSync(downloads+'/browser.p12');i++)await delay(30);assert.equal(fs.readFileSync(downloads+'/browser.p12','utf8'),'private');assert(await ev(`document.getElementById('access-certificates').textContent.includes('2027-10-09')&&document.getElementById('access-certificates').textContent.includes('AA:BB')`));
await choose('certificate');await click('access-apply');await close('confirm');await until(`document.getElementById('access-current').textContent==='Client certificate'`);await ev(`document.querySelector('#access-certificates button').click()`);await close('confirm');await until(`document.getElementById('access-certificates').textContent.includes('Revoked')`);assert.deepEqual(await ev(`requests.find(x=>x.method==='certificate.revoke')`),{method:'certificate.revoke',id:'one'});
await choose('none');await click('access-apply');const before=await ev('requests.length');await ev(`sv08Session.elevated=false;window.dispatchEvent(new Event('sv08-authority-changed'))`);assert(!(await ev(`document.getElementById('access-review').open`)));await close('confirm');assert.equal(await ev('requests.length'),before);
await ev(`hold=true;sv08Session.elevated=true;window.dispatchEvent(new Event('sv08-authority-changed'))`);await until('held.length===1');await fill('access-download-password','temporary');await ev(`sv08Navigation.go('overview')`);await ev(`held.shift()(JSON.stringify({ok:true,result:{mode:'none',certificates:[]}}))`);await delay(50);assert.equal(await ev(`document.getElementById('access-current').textContent`),'—');assert.equal(await ev(`document.getElementById('access-download-password').value`),'');
await ev(`hold=false;sv08Navigation.go('mainsail-access')`);await until(`!document.getElementById('access-create').disabled`);await ev(`hold=true`);await click('access-refresh');await click('access-refresh');await until('held.length===2');await ev(`held.pop()(JSON.stringify({ok:true,result:{mode:'password',certificates:[]}}))`);await until(`document.getElementById('access-current').textContent==='Password'`);await ev(`held.pop()(JSON.stringify({ok:true,result:{mode:'none',certificates:[]}}))`);await delay(50);assert.equal(await ev(`document.getElementById('access-current').textContent`),'Password');
await ev(`hold=true`);await click('access-refresh');await until('held.length===1');await ev(`held.shift()(JSON.stringify({ok:true,result:{mode:'certificate',certificates:[],authority_valid:false,warning:'The printer certificate authority changed. Generate and import a new certificate, or switch to password or no login.'}}))`);await until(`document.getElementById('access-status').textContent.includes('certificate authority changed')`);assert(!(await ev(`document.getElementById('access-create').disabled`)));
await ev(`hold=false;holdCreate=true`);await fill('access-label','Abandoned browser');await fill('access-download-password','private pass');await fill('access-download-confirm','private pass');await click('access-create');await close('confirm');await until('held.length===1');await ev(`sv08Navigation.go('overview');held.shift()(JSON.stringify({ok:true,result:{filename:'abandoned.p12',pkcs12_base64:'cHJpdmF0ZQ=='}}))`);await delay(50);assert(!fs.existsSync(downloads+'/abandoned.p12'));assert.equal(await ev(`document.getElementById('access-download-password').value`),'');
for(const width of [390,1024]){await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});assert(await ev('document.documentElement.scrollWidth<=innerWidth'))}
await send('Page.navigate',{url:'http://printer.test:'+port+'/#mainsail-access'});await until(`document.getElementById('access-current')?.textContent==='Password'`);await fill('access-label','remote');await fill('access-download-password','private pass');await fill('access-download-confirm','private pass');await click('access-create');assert(await ev(`document.getElementById('access-status').textContent.includes('Use HTTPS')`));assert.equal(await ev(`requests.filter(x=>x.method==='certificate.create').length`),0);console.log('PASS: password, review/cancel, no-login, certificate download/activate/revoke, authority/navigation epochs, stale refresh/private download, HTTP refusal, responsive views');
}finally{socket?.close();server.close();if(child){try{process.kill(-child.pid,'SIGTERM')}catch{}await delay(100);try{process.kill(-child.pid,'SIGKILL')}catch{}}}
'''


class MainsailAccessBrowserTests(unittest.TestCase):
    def test_mocked_browser_journeys(self):
        self.assertTrue(NODE.exists(), 'Assigned Node tool is required')
        self.assertTrue(CHROME.exists(), 'Assigned Chromium tool is required')
        SCRATCH.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
            script = Path(temporary)/'journeys.mjs'
            script.write_text(JOURNEYS)
            result = subprocess.run([str(NODE),str(script),str(REPO),str(CHROME),temporary],capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            print(result.stdout.strip())


if __name__ == '__main__':
    unittest.main()
