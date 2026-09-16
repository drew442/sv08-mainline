// Browser composition for an unknown receipt. The controller/backend fixture is
// disposable; service-side exclusion is separately exercised by ARM64 QEMU.
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';
const [chrome, fixture, output] = process.argv.slice(2);
const {url} = JSON.parse(fs.readFileSync(fixture+'/server.json'));
assert.match(url, /^http:\/\/127\.0\.0\.1:\d+$/);
fs.mkdirSync(output); const profile = output+'/profile', log = fs.openSync(output+'/browser.log','w');
const child = spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-background-networking','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{detached:true,stdio:['ignore',log,log]});
let socket;
try {
 let port; for(let i=0;i<100;i++){try{port=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];break;}catch{await delay(100);}} assert(port);
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json(); socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl); await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let id=0; const pending=new Map(), errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>reject(new Error('CDP timeout: '+method)),10000);pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params}));});
 socket.onmessage=({data})=>{const value=JSON.parse(data);if(value.id){const item=pending.get(value.id);if(item){clearTimeout(item.timer);pending.delete(value.id);value.error?item.reject(value.error):item.resolve(value.result);}}if(value.method==='Runtime.exceptionThrown')errors.push(value.params);};
 await send('Runtime.enable'); await send('Page.enable');
 const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value;};
 const until=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await delay(100);}throw new Error('Timeout: '+expression);};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 await send('Page.navigate',{url}); await until(`document.querySelector('#connection')?.textContent==='Image worker status connected'`);
 const receipt='d'.repeat(32); await until(`document.querySelector('[data-inspect-job="${receipt}"]')`);
 await click(`[data-inspect-job="${receipt}"]`); await until(`document.querySelector('#review').open`);
 assert.equal(await evaluate(`document.querySelector('#review-title').textContent`),'Retain unknown outcome');
 assert.match(await evaluate(`document.querySelector('#review-arguments').textContent`),/GetSlotStatus/);
 await click('#confirm'); await until(`!document.querySelector('#review').open && document.querySelector('#connection')?.textContent==='Host connected'`);
 let jobs=JSON.parse(fs.readFileSync(fixture+'/state/admin-image-jobs/jobs.json')); assert.equal(jobs[0].phase,'interrupted'); assert.equal(jobs[0].disposition.outcome,'unknown');
 // A reopened page sees the same retained outcome and never makes a new image job.
 await send('Page.reload'); await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 jobs=JSON.parse(fs.readFileSync(fixture+'/state/admin-image-jobs/jobs.json')); assert.equal(jobs.length,1); assert.equal(jobs[0].disposition.outcome,'unknown');
 await click('[data-page="images"]'); await until(`!document.querySelector('#cancel-image').disabled`);
 await click('#cancel-image'); await until(`document.querySelector('#review').open`); await click('#confirm'); await until(`!document.querySelector('#review').open && document.querySelector('#connection')?.textContent==='Host connected'`);
 for(let i=0;i<100 && JSON.parse(fs.readFileSync(fixture+'/state/update.json')).phase!=='cancelled';i++) await delay(100);
 const transaction=JSON.parse(fs.readFileSync(fixture+'/state/update.json')); const state=JSON.parse(fs.readFileSync(fixture+'/state/state.json'));
 assert.equal(transaction.phase,'cancelled'); assert.equal(state.pending,null); assert.equal(JSON.parse(fs.readFileSync(fixture+'/backend.json')).selected,'A');
 assert.equal(fs.existsSync(fixture+'/release-install'),false); assert.equal(errors.length,0);
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,interrupted_receipt_inspected:true,unknown_disposition_retained_after_reload:true,separately_reviewed_cancelled:true,source_selected:'A',pending_cleared_after_disarm:true,new_installations:0,physical_hardware:false},null,2)+'\n');
 console.log('Browser image resolution PASS');
} finally { socket?.close(); try{process.kill(-child.pid,'SIGTERM');}catch{} fs.closeSync(log); }
