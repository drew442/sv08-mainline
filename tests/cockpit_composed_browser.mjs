import { createRequire } from 'node:module';
const WebSocket=createRequire(import.meta.url)('ws');
const uploadCases=async()=>({skipped:'composed backend fixture checks cancellation separately'});
import fs from 'node:fs';import {spawn} from 'node:child_process';import {setTimeout as delay} from 'node:timers/promises';import assert from 'node:assert/strict';
const [W,chrome] = process.argv.slice(2);
assert(W && chrome);const results={scope:'Actual Cockpit 337/PAM/sudo in disposable ARM64 QEMU; HTTP on private namespace loopback',physical_hardware:false,production_tls:false};
const creds=JSON.parse(fs.readFileSync(W+'/credentials.json'));const profile=W+'/browser';
fs.rmSync(profile+'/DevToolsActivePort',{force:true});const child=spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});let socket;
try{
 let port;for(let i=0;i<100;i++){try{port=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];break;}catch{await delay(100);}}
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j});
 let id=0;const pending=new Map(), browserEvents=[];function send(method,params={}){return new Promise((resolve,reject)=>{const key=++id;const timer=setTimeout(()=>reject(Error('CDP timeout '+method)),60000);pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params}))})}
 socket.onmessage=({data})=>{const e=JSON.parse(data);if(['Runtime.consoleAPICalled','Runtime.exceptionThrown','Log.entryAdded'].includes(e.method))browserEvents.push(e);if(e.id){const p=pending.get(e.id);if(p){clearTimeout(p.timer);pending.delete(e.id);e.error?p.reject(Error('CDP error')):p.resolve(e.result)}}};
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error('Browser evaluation failed: '+r.exceptionDetails.text);return r.result.value};
 const until=async expression=>{for(let i=0;i<200;i++){if(await ev(expression))return;await delay(200)}throw Error('Timeout '+expression)};
 const click = async selector => { await until(`!!document.querySelector(${JSON.stringify(selector)}) && !document.querySelector(${JSON.stringify(selector)}).disabled`); return ev(`document.querySelector(${JSON.stringify(selector)}).click()`); };
 const text = selector => ev(`document.querySelector(${JSON.stringify(selector)}).textContent`);
 const field = (selector,value) => ev(`(()=>{const p=document.querySelector(${JSON.stringify(selector)});p.value=${JSON.stringify(value)};p.dispatchEvent(new Event('input',{bubbles:true}));})()`);
 const navigate = async () => { await send('Page.navigate',{url:'http://127.0.0.1:19091/'}); await until('document.readyState==="complete"'); };
 const login = async (name,password) => ev(`fetch('/cockpit/login',{headers:{Authorization:'Basic '+btoa(${JSON.stringify(name+':'+password)}),'X-Superuser':'none'}}).then(r=>r.status)`);
 const loadShell = async () => { await navigate(); await until('!!window.sv08Session'); await until('sv08Session.elevated || !document.querySelector("#authorize").disabled || document.querySelector("#session-status").textContent.includes("unavailable")'); };
 const uid = () => ev(`cockpit.spawn(['id','-u'],{superuser:'require'}).then(x=>x.trim(),e=>e.problem)`);
 const helper = message => ev(`cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_admin.py'],{superuser:'require',err:'message'}).input(${JSON.stringify(JSON.stringify(message))}).then(x=>JSON.parse(x))`);
 const stateHash = () => ev(`cockpit.spawn(['/usr/bin/sha256sum','/data/sv08/state.json'],{superuser:'require'}).then(x=>x.split(' ')[0])`);
 const authorize = async () => { await click('#authorize'); await until('document.querySelector("#authorization").open'); await field('#authorization-password',creds.fixtureadmin); await click('#answer-authorization'); await until('sv08Session.elevated'); console.log('connection='+await text('#connection')); assert.equal(await uid(),'0'); };
 const stopped = async () => { await click('#stop-authorization'); await until('!sv08Session.elevated && !document.querySelector("#authorize").disabled'); assert.equal(await uid(),'access-denied'); };
 const secretsClear = async () => {
   assert.equal(await ev('document.querySelector("#authorization-password").value'),'');
   assert.equal(await ev('document.querySelector("#authorization-prompt").textContent'),'');
   const storage=await ev('JSON.stringify({local:{...localStorage},session:{...sessionStorage}})');
   for(const password of Object.values(creds)) assert(!storage.includes(password));
 };
 await send('Network.clearBrowserCookies');await send('Page.enable');await send('Runtime.enable');await send('Log.enable');await navigate();
 assert.equal(await login('fixtureadmin','deliberately-invalid'),401);results.bad_login_rejected=true;
 assert.equal(await login('fixtureordinary',creds.fixtureordinary),200);await loadShell();
 assert.equal(await uid(),'access-denied');
 results.uid_proof={ordinary_account:await ev(`cockpit.spawn(['id','-u']).then(x=>x.trim())`)};
 const ordinary = await ev(`cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_admin.py']).input('{"method":"status"}').then(x=>JSON.parse(x))`);
 assert.equal(ordinary.ok,false);assert.match(ordinary.error,/Administrator access/);
 const ordinaryUpload=await ev(`(()=>{let output='';const p=cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_admin_upload.py']);p.stream(x=>{output+=x});return p.input('{}\\n').then(()=>output,()=>output)})()`);
 assert.match(ordinaryUpload,/Administrator access/);results.upload_ordinary_denial=true;
 await click('#authorize');await until('document.querySelector("#authorization").open || document.querySelector("#session-status").textContent.includes("failed")');
 if(await ev('document.querySelector("#authorization").open')) { await field('#authorization-password',creds.fixtureordinary);await click('#answer-authorization'); }
 await until('document.querySelector("#session-status").textContent.includes("failed")');assert.equal(await uid(),'access-denied');await secretsClear();results.ordinary_denial=true;console.log('ordinary denial PASS');
 await click('#logout');await until('!window.sv08Session');assert.equal(await login('fixtureadmin',creds.fixtureadmin),200);await loadShell();
 assert.equal(await uid(),'access-denied');await click('#authorize');await until('document.querySelector("#authorization").open');await field('#authorization-password','deliberately-invalid');await click('#answer-authorization');
 await until('document.querySelector("#authorization-prompt").textContent.includes("try again")');assert.equal(await ev('document.querySelector("#authorization-password").value'),'');assert.equal(await ev('sv08Session.elevated'),false);
 await click('#cancel-authorization');await until('!document.querySelector("#authorization").open && !document.querySelector("#authorize").disabled');await secretsClear();assert.equal(await uid(),'access-denied');results.wrong_password_and_cancel=true;console.log('wrong password and cancel PASS');
 results.uid_proof.administrator_unelevated=await ev(`cockpit.spawn(['id','-u']).then(x=>x.trim())`);
 await authorize();await secretsClear();results.uid_proof.elevated=await uid(); const inspected=await helper({method:'image.inspect',id:'dddddddddddddddddddddddddddddddd'});assert.equal(inspected.ok,true);const disposed=await helper({method:'image.dispose',plan:inspected.result.plan});assert.equal(disposed.ok,true);await click('#logout');await until('!window.sv08Session');assert.equal(await login('fixtureadmin',creds.fixtureadmin),200);await loadShell();await authorize();const cancelPlan=await helper({method:'plan',action:'image.cancel',arguments:{}});assert.equal(cancelPlan.ok,true);const submitted=await helper({method:'image.submit',id:'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',plan:cancelPlan.result});assert.equal(submitted.ok,true);for(let i=0;i<100;i++){const h=await helper({method:'jobs'});if(h.result.jobs.find(x=>x.id==='eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')?.phase==='succeeded')break;await delay(200)}const end=await helper({method:'jobs'});assert.equal(end.result.jobs.find(x=>x.id==='eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee').phase,'succeeded');const finalStatus=await helper({method:'status'});assert.equal(finalStatus.result.pending,null);assert.equal(finalStatus.result.boot.slot,'A');assert.equal(finalStatus.result.transaction.previous_slot,'A');const after=await helper({method:'jobs'});assert.equal(after.result.jobs.find(x=>x.id==='dddddddddddddddddddddddddddddddd').disposition.outcome,'unknown');assert.equal(await ev(`cockpit.spawn(['/usr/bin/cat','/data/fixture/user-data-sentinel'],{superuser:'require'}).then(x=>x.trim())`),'preserved fixture data');results.composed={disposition:'unknown',cancellation:'succeeded',reconnect:true,source_slot:'A',data_sentinel_preserved:true};results.passed=true;fs.writeFileSync(W+'/composed-result.json',JSON.stringify(results,null,2)+'\n');console.log('COMPOSED_RESULT '+JSON.stringify(results.composed));

}finally{socket?.close();child.kill()}
