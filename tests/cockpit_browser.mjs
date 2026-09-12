import {uploadCases} from './cockpit_upload_cases.mjs';
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
 const navigate = async () => { await send('Page.navigate',{url:'http://127.0.0.1:19090/'}); await until('document.readyState==="complete"'); };
 const login = async (name,password) => ev(`fetch('/cockpit/login',{headers:{Authorization:'Basic '+btoa(${JSON.stringify(name+':'+password)}),'X-Superuser':'none'}}).then(r=>r.status)`);
 const loadShell = async () => { await navigate(); await until('!!window.sv08Session'); await until('sv08Session.elevated || !document.querySelector("#authorize").disabled || document.querySelector("#session-status").textContent.includes("unavailable")'); };
 const uid = () => ev(`cockpit.spawn(['id','-u'],{superuser:'require'}).then(x=>x.trim(),e=>e.problem)`);
 const helper = message => ev(`cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_admin.py'],{superuser:'require',err:'message'}).input(${JSON.stringify(JSON.stringify(message))}).then(x=>JSON.parse(x))`);
 const stateHash = () => ev(`cockpit.spawn(['/usr/bin/sha256sum','/data/sv08/state.json'],{superuser:'require'}).then(x=>x.split(' ')[0])`);
 const authorize = async () => { await click('#authorize'); await until('document.querySelector("#authorization").open'); await field('#authorization-password',creds.fixtureadmin); await click('#answer-authorization'); await until('sv08Session.elevated'); await until('document.querySelector("#connection").textContent==="Host connected"'); assert.equal(await uid(),'0'); };
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
 await authorize();await secretsClear();results.uid_proof.elevated=await uid();
 // Reset only finite disposable policy between development reruns.
 for(const [action,args] of [['policy.auto',{enabled:true}],['policy.mode',{mode:'immutable'}]]) { const p=await helper({method:'plan',action,arguments:args});assert.equal((await helper({method:'apply',plan:p.result})).ok,true); }
 await ev('refresh()');
 if (fs.existsSync(W+'/signed.raucb')) { results.upload=await uploadCases({W,ev,send,until,click,helper,stateHash,loadShell,authorize}); console.log('real upload cases PASS'); }

 const originalHash=await stateHash();const status=await helper({method:'status'});assert.equal(status.ok,true);assert.equal(status.result.auto_update,true);
 const jobs=await helper({method:'jobs'});assert.equal(jobs.ok,true);assert.deepEqual(jobs.result.jobs,[]);
 const plan=await helper({method:'plan',action:'policy.auto',arguments:{enabled:false}});assert.equal(plan.ok,true);assert.equal(await stateHash(),originalHash);results.status_review_jobs_no_state_mutation=true;
 await click('[data-page="images"]');await click('#auto-update');await click('#save-auto');await until('document.querySelector("#review").open');await ev('document.querySelector("#review").close("cancel")');assert.equal(await stateHash(),originalHash);results.cancel_preserves_state=true;
 // Stop invalidates an open review; later authentication must not confirm it.
 await click('#save-auto');await until('document.querySelector("#review").open');await ev('document.querySelector("#stop-authorization").click()');await until('!sv08Session.elevated && !document.querySelector("#authorize").disabled');assert.equal(await ev('document.querySelector("#review").open'),false);await authorize();assert.equal(await stateHash(),originalHash);assert.equal(await ev('document.querySelector("#review").open'),false);results.authentication_never_confirms=true;
 // A review based on old policy must be refused by the real installed helper.
 await click('#save-auto');await until('document.querySelector("#review").open');
 const other=await helper({method:'plan',action:'policy.mode',arguments:{mode:'writable'}});assert.equal((await helper({method:'apply',plan:other.result})).ok,true);
 await click('#confirm');await until('document.querySelector("#notice").textContent.toLowerCase().includes("changed")');assert.equal((await helper({method:'status'})).result.auto_update,true);results.stale_review_refused=true;
 await click('#save-auto');await until('document.querySelector("#review").open');await click('#confirm');await until('document.querySelector("#notice").textContent.startsWith("Saved.")');assert.equal((await helper({method:'status'})).result.auto_update,false);results.confirmed_helper_apply=true;console.log('real helper review/apply PASS');
 // Hold a real response locally to reproduce authority-transition races without
 // replacing the authenticated transport or helper's result.
 await ev(`window.realRequest=request;window.delayedReady=false;request=async message=>{const result=await realRequest(message);if(message.method==='plan'){window.delayedReady=true;await new Promise(resolve=>window.releaseDelayed=resolve);}return result;}`);
 await click('#auto-update');await click('#save-auto');await until('window.delayedReady');await stopped();await ev('window.releaseDelayed();request=window.realRequest');await delay(200);assert.equal(await ev('document.querySelector("#review").open'),false);results.delayed_review_after_stop_discarded=true;await authorize();
 await ev(`window.delayedReady=false;request=async message=>{const result=await realRequest(message);if(message.method==='apply'){window.delayedReady=true;await new Promise(resolve=>window.releaseDelayed=resolve);}return result;}`);
 await click('#save-auto');await until('document.querySelector("#review").open');await click('#confirm');await until('window.delayedReady');await stopped();await ev('window.releaseDelayed();request=window.realRequest');await delay(200);assert(!String(await text('#notice')).includes('null'));await authorize();assert.equal((await helper({method:'status'})).result.auto_update,true);results.delayed_apply_after_stop_preserved=true;
 // Selected packages must expose no alternate unguarded stock applications.
 const manifests=await ev(`fetch('/cockpit/@localhost/manifests.json').then(r=>r.json())`);
 for(const name of ['shell','system','storage','packagekit','terminal'])assert(!(name in manifests));
 for(const name of ['shell','system','storage','packagekit'])assert.equal(await ev(`fetch('/cockpit/@localhost/${name}/index.html').then(r=>r.status)`),404);
 results.stock_packages_unavailable=true;
 const journal=await ev(`cockpit.spawn(['journalctl','--no-pager','--output=short','-b'],{superuser:'require'}).then(x=>x)`);
 const forbidden=Object.entries(creds).flatMap(([name,password])=>[password,Buffer.from(name+':'+password).toString('base64')]);
 for(const value of forbidden)assert(!journal.includes(value),'Credential found in guest journal');
 results.guest_journal_secret_scan=true;
 const serviceState=await ev(`cockpit.spawn(['systemctl','show','cockpit.socket','cockpit.service','cockpit-session.socket','cockpit-fixture.service','-p','Id','-p','ActiveState','-p','SubState'],{superuser:'require'}).then(x=>x)`);
 assert.equal((serviceState.match(/ActiveState=active/g)||[]).length,4);fs.writeFileSync(W+'/guest-service-state.txt',serviceState);
 const cookie=(await send('Network.getCookies',{urls:['http://127.0.0.1:19090/']})).cookies.map(c=>c.name+'='+c.value).join(';');assert(cookie);
 await stopped();await secretsClear();results.explicit_stop_denies_helper=true;await click('#logout');await until('!window.sv08Session');
 assert.equal((await fetch('http://127.0.0.1:19090/cockpit/login',{headers:{Cookie:cookie}})).status,401);
 assert.equal(await ev(`fetch('/cockpit/login').then(r=>r.status)`),401);results.logout_invalidates_old_session=true;
 assert.equal(await login('fixtureadmin',creds.fixtureadmin),200);await loadShell();assert.equal(await uid(),'access-denied');await authorize();assert.equal((await helper({method:'status'})).result.auto_update,true);results.authenticated_reconnect_persistence=true;
 // API absence is a controlled browser fault, not real authorization evidence.
 const injected=await send('Page.addScriptToEvaluateOnNewDocument',{source:`Object.defineProperty(window,'cockpit',{configurable:true,set(value){value.dbus=undefined;Object.defineProperty(window,'cockpit',{value,writable:true,configurable:true});}});`});
 await loadShell();assert.match(await text('#session-status'),/required Cockpit 337 session API/);assert.equal(await ev('sv08Session.available'),false);assert.equal(await ev('document.querySelector("#authorize").disabled'),true);results.missing_api_fails_closed=true;
 await send('Page.removeScriptToEvaluateOnNewDocument',{identifier:injected.identifier});
 // Failed Stop diagnostic regression uses an explicit controlled proxy fault.
 const fault=await send('Page.addScriptToEvaluateOnNewDocument',{source:`Object.defineProperty(window,'cockpit',{configurable:true,set(value){value.dbus=()=>({addEventListener:()=>{},proxy:()=>({valid:true,Current:'sudo',Bridges:['sudo'],Start:()=>{},Answer:()=>{},Stop:()=>Promise.reject(Error('fixture')),addEventListener:()=>{},wait:cb=>cb()})});Object.defineProperty(window,'cockpit',{value,writable:true,configurable:true});}});`});
 await navigate();await until('!!window.sv08Session && sv08Session.elevated');await click('#stop-authorization');await until('document.querySelector("#session-status").textContent.includes("Could not stop")');assert.equal(await ev('sv08Session.elevated'),false);await secretsClear();results.controlled_stop_failure_visible_and_closed=true;
 await send('Page.removeScriptToEvaluateOnNewDocument',{identifier:fault.identifier});
 const scanned=[];
 function scanFile(path){const bytes=fs.readFileSync(path);for(const value of forbidden)assert(!bytes.includes(Buffer.from(value)),'Credential found in private log/evidence');scanned.push(path);}
 for(const name of ['guest.log','package-install.log','apt-simulation.txt','units.txt','prepare.json','guest-service-state.txt'])scanFile(W+'/'+name);
 for(const value of forbidden)assert(!JSON.stringify(browserEvents).includes(value),'Credential found in browser console/error');
 for(const value of forbidden)assert(!JSON.stringify(results).includes(value),'Credential found in report');
 results.secret_scan={guest_journal:true,browser_console_and_errors:true,private_log_and_evidence_files:scanned.length,violations:0};
 results.passed=true;fs.writeFileSync(W+'/browser-result.json',JSON.stringify(results,null,2)+'\n');console.log('Actual Cockpit authentication, helper/session and transition tests PASS');
}finally{socket?.close();child.kill()}
