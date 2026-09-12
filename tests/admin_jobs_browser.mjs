// Actual browser + disposable Python controller. No printer or network service.
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';
const [chrome, fixture, output] = process.argv.slice(2);
const {url} = JSON.parse(fs.readFileSync(fixture+'/server.json'));
assert.match(url, /^http:\/\/127\.0\.0\.1:\d+$/);
fs.mkdirSync(output); const profile = output+'/profile';
const log = fs.openSync(output+'/browser.log','w');
const child = spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{detached:true,stdio:['ignore',log,log]});
let socket;
try {
 let port;
 for(let i=0;i<100;i++){try{port=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];break;}catch{await delay(100);}}
 assert(port);
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let id=0;const pending=new Map(),errors=[];
 function send(method,params={}){return new Promise((resolve,reject)=>{const key=++id; const timer=setTimeout(()=>reject(new Error('CDP timeout: '+method)),10000);pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params}));});}
 socket.onmessage=({data})=>{const e=JSON.parse(data);if(e.id){const p=pending.get(e.id);if(p){clearTimeout(p.timer);pending.delete(e.id);e.error?p.reject(e.error):p.resolve(e.result);}}if(e.method==='Runtime.exceptionThrown')errors.push(e.params);};
 await send('Runtime.enable');await send('Page.enable');
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const until=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await delay(100);}throw new Error('Timeout: '+expression);};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const key=async key=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:{Tab:9,Enter:13,Escape:27}[key],text:key==='Enter'?'\r':undefined});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});};
 const screenshot=async name=>{const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(r.data,'base64'));};
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url});await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 await click('[data-page="images"]');
 await click('#stage-image');await until(`document.querySelector('#review').open`);await key('Escape');
 assert(!fs.existsSync(fixture+'/state/admin-image-jobs/jobs.json'));
 // Lose the acknowledgement only after the actual helper has admitted staging.
 await evaluate(`(()=>{const original=cockpit.spawn;let lose=true;cockpit.spawn=(...args)=>{const process=original(...args);return {input:async data=>{const result=await process.input(data);if(lose && JSON.parse(data).method==='image.submit'){lose=false;throw new Error('Injected lost acknowledgement');}return result;}};};})()`);
 await click('#stage-image');await until(`document.querySelector('#review').open`);await click('#confirm');
 for(let i=0;i<100 && !fs.existsSync(fixture+'/install-entered');i++)await delay(100);
 assert(fs.existsSync(fixture+'/install-entered'));
 const receipt=JSON.parse(fs.readFileSync(fixture+'/state/admin-image-jobs/jobs.json'))[0];
 assert.equal(receipt.phase,'running');
 // Destroy the real browser target and reconnect in a newly created target.
 const old=tabs.find(t=>t.type==='page');
 await fetch(`http://127.0.0.1:${port}/json/close/${old.id}`);socket.close();
 const reopened=await(await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
 socket=new WebSocket(reopened.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 socket.onmessage=({data})=>{const e=JSON.parse(data);if(e.id){const p=pending.get(e.id);if(p){clearTimeout(p.timer);pending.delete(e.id);e.error?p.reject(e.error):p.resolve(e.result);}}if(e.method==='Runtime.exceptionThrown')errors.push(e.params);};
 await send('Runtime.enable');await send('Page.enable');
 const started=Date.now();await send('Page.navigate',{url});
 await until(`document.querySelector('[data-job-id="${receipt.id}"]')?.dataset.phase==='running'`);
 const reconnectMs=Date.now()-started;assert(reconnectMs<3000);
 assert(!fs.existsSync(fixture+'/release-install'));
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/backend.json')).calls.filter(x=>x==='install').length,0);
 const retry=await evaluate(`request(${JSON.stringify({method:'image.submit',id:receipt.id,plan:receipt.plan})})`);
 assert.equal(retry.id,receipt.id);assert.equal(retry.phase,'running');
 const unit=fs.readFileSync(fixture+'/units.log','utf8').trim().split('\n')[0];
 const {execFileSync}=await import('node:child_process');
 const unitState=execFileSync('/usr/bin/systemctl',['--user','show',unit,'--property=ActiveState,MainPID,ExecStart'],{encoding:'utf8'});
 assert.match(unitState,/ActiveState=active/);assert.match(unitState,/admin_jobs_fixture.py/);
 fs.writeFileSync(fixture+'/release-install','release');
 await until(`document.querySelector('[data-job-id="${receipt.id}"]')?.dataset.phase==='succeeded'`);
 await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/backend.json')).calls.filter(x=>x==='install').length,1);
 await click('[data-page="images"]');
 for(const [button,selected] of [['#arm-image','B'],['#cancel-image','A']]) {
   await until(`!document.querySelector('${button}').disabled`);
   await click(button);await until(`document.querySelector('#review').open`);await click('#confirm');
   await until(`document.querySelector('#connection')?.textContent==='Host connected' && !document.querySelector('#review').open`);
   for(let i=0;i<100 && JSON.parse(fs.readFileSync(fixture+'/backend.json')).selected!==selected;i++)await delay(100);
   assert.equal(JSON.parse(fs.readFileSync(fixture+'/backend.json')).selected,selected);
 }
 for(let i=0;i<100 && JSON.parse(fs.readFileSync(fixture+'/state/admin-image-jobs/jobs.json')).some(r=>r.phase!=='succeeded');i++)await delay(100);
 const rows=JSON.parse(fs.readFileSync(fixture+'/state/admin-image-jobs/jobs.json'));
 assert.deepEqual(rows.map(r=>r.plan.action),['image.stage','image.arm','image.cancel']);
 assert(rows.every(r=>r.phase==='succeeded'));assert.equal(errors.length,0);
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,reconnect_ms:reconnectMs,stage_installations:1,lost_acknowledgement_retry_same_identity:true,closed_and_reopened_browser_target:true,real_systemd_user_worker:true,unit_state:unitState,transport:'test Cockpit bridge shim',real_controller_staging_transaction:true,backend:'disposable disk double, fixture signature verifier',authenticated_cockpit:false,physical_hardware:false,jobs:rows.map(({id,phase,plan})=>({id,phase,action:plan.action}))},null,2)+'\n');
 console.log('Browser image jobs PASS; reconnect '+reconnectMs+' ms');
}finally{socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);}
