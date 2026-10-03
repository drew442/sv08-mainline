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
 const stateBefore=fs.readFileSync(fixture+'/state/state.json','utf8'); const transactionBefore=fs.readFileSync(fixture+'/state/update.json','utf8');
 const originals=JSON.parse(fs.readFileSync(fixture+'/originals.json'));
 const rows=()=>{const m=JSON.parse(fs.readFileSync(fixture+'/state/admin-image-jobs/jobs.json'));return Array.isArray(m)?m:[...m.archives,m.active].flatMap(d=>JSON.parse(fs.readFileSync(fixture+'/state/admin-image-jobs/'+d.name)));};
 // Real tmpfs pressure exercises the production 768 MiB floor, within the assigned peak.
 const block=4096;const headroom=2*Math.ceil(2752512/block)*block+1048576;
 const free=Number(fs.statfsSync(fixture).bavail)*Number(fs.statfsSync(fixture).bsize);
 const pressureBytes=Math.ceil((free-(768*1024*1024+headroom-block))/block)*block;
 const allocated=p=>{const st=fs.lstatSync(p);return Number(st.blocks)*512+(st.isDirectory()?fs.readdirSync(p).reduce((n,name)=>n+allocated(p+'/'+name),0):0);};
 const scratch=fixture.substring(0,fixture.lastIndexOf('/'));const priorAllocation=allocated(scratch);
 assert(pressureBytes>0 && pressureBytes<740*1024*1024 && pressureBytes+priorAllocation<=768*1024*1024);
 const pressure=fixture+'/pressure';const pressureFd=fs.openSync(pressure,'wx',0o600);const chunk=Buffer.alloc(1024*1024,1);
 try {for(let remain=pressureBytes;remain>0;) {const size=Math.min(remain,chunk.length);fs.writeSync(pressureFd,chunk,0,size);remain-=size;}}
 finally{fs.closeSync(pressureFd);}
 const pressurePeak=allocated(scratch);
 try {
   await evaluate(`refresh()`);await until(`!refreshing && document.querySelector('#history-maintenance').disabled`);
   assert.match(await evaluate(`document.querySelector('#history-capacity').textContent`),/Insufficient shared data/);
   assert.deepEqual(rows(),originals);
 } finally {fs.unlinkSync(pressure);}
 await evaluate(`refresh()`);await until(`!refreshing && !document.querySelector('#history-maintenance').disabled`);
 await evaluate(`document.querySelector('#hostname').value='unsaved-history-draft';document.querySelector('#hostname').dispatchEvent(new Event('input'))`);
 await click('#history-maintenance');await until(`document.querySelector('#review').open`);
 await evaluate(`window.dispatchEvent(new Event('sv08-authority-changed'))`);await until(`!document.querySelector('#review').open && !refreshing`);
 assert(!fs.existsSync(fixture+'/state/admin-image-jobs/history-format-v2.lock'));
 await click('#history-maintenance');await until(`document.querySelector('#review').open`);await key('Escape');
 assert.equal(rows().length,128);assert(!fs.existsSync(fixture+'/state/admin-image-jobs/history-format-v2.lock'));
 await click('#history-maintenance');await until(`document.querySelector('#review').open`);await click('#confirm');
 await until(`!busy && !refreshing && !document.querySelector('#review').open && !document.querySelector('#history-maintenance').disabled`);
 await evaluate(`(()=>{const original=cockpit.spawn;let lose=true;cockpit.spawn=(...args)=>{const p=original(...args);return {input:async data=>{const r=await p.input(data);if(lose && JSON.parse(data).method==='history.apply'){lose=false;throw new Error('Injected lost maintenance acknowledgement');}return r;}};};})()`);
 await click('#history-maintenance');await until(`document.querySelector('#review').open`);await click('#confirm');
 await until(`!document.querySelector('#review').open && !document.querySelector('#history-retry').hidden`);
 assert.deepEqual(rows(),originals);assert.deepEqual(JSON.parse(fs.readFileSync(fixture+'/backend.json')).calls,[]);
 assert.equal(fs.readFileSync(fixture+'/state/state.json','utf8'),stateBefore);assert.equal(fs.readFileSync(fixture+'/state/update.json','utf8'),transactionBefore);
 assert.equal(await evaluate(`document.querySelector('#hostname').value`),'unsaved-history-draft');
 await send('Page.reload');await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 await click('#history-retry');await until(`document.querySelector('#history-retry').hidden`);
 await evaluate(`localStorage.setItem('sv08-image-submission',JSON.stringify({method:'image.submit',id:'00000000000000000000000000000000',plan:{}}))`);
 await send('Page.reload');await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 assert.equal(await evaluate(`localStorage.getItem('sv08-image-submission')`),null);
 await click('[data-page="images"]');await click('#cancel-image');await until(`document.querySelector('#review').open`);await click('#confirm');
 await until(`!document.querySelector('#review').open`);
 for(let i=0;i<100 && JSON.parse(fs.readFileSync(fixture+'/state/update.json')).phase!=='cancelled';i++)await delay(100);
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/state/update.json')).phase,'cancelled');
 assert.deepEqual(rows().slice(0,128),originals);assert.equal(rows().length,129);
 const backend=JSON.parse(fs.readFileSync(fixture+'/backend.json'));assert.equal(backend.selected,'A');
 for(let i=0;i<100 && rows()[128].phase!=='succeeded';i++)await delay(100);
 assert.equal(rows()[128].phase,'succeeded');
 // Current separate worker holds the real state transaction barrier. Reads still render first.
 await until(`!busy && !refreshing && !document.querySelector('#stage-image').disabled`);
 await click('#stage-image');await until(`document.querySelector('#review').open`);await click('#confirm');
 for(let i=0;i<100 && !fs.existsSync(fixture+'/install-entered');i++)await delay(100);
 assert(fs.existsSync(fixture+'/install-entered'));
 const reconnectStart=Date.now();await send('Page.reload');
 await until(`document.querySelector('#connection')?.textContent==='Image worker status connected'`);
 const reconnectMs=Date.now()-reconnectStart;assert(reconnectMs<2000);
 assert.equal(rows()[129].phase,'running');assert.deepEqual(rows().slice(0,128),originals);
 fs.writeFileSync(fixture+'/release-install','fixture barrier released');
 for(let i=0;i<100 && rows()[129].phase!=='succeeded';i++)await delay(100);
 assert.equal(rows()[129].phase,'succeeded');assert.equal(errors.length,0);

 fs.writeFileSync(output+'/result.json',JSON.stringify({browser_shim:true,separate_worker:true,preserved_originals:128,maintenance_cancel:true,lost_ack_retry:true,archived_pending_recovered:true,cancel_once:true,real_tmpfs_no_space:true,pressure_peak_allocated_bytes:pressurePeak,worker_barrier_reconnect_ms:reconnectMs,authority_changed_review_cancelled:true,maintenance_state_unchanged:true,backend_calls:backend.calls,authenticated:false,hardware:false},null,2));
 console.log('Native browser history journey completed (shim transport).');
}finally{socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);}
