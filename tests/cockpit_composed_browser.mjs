// General: node tests/cockpit_composed_browser.mjs W CHROME installed
// W holds coordinator-generated ephemeral credentials.json and public signed.raucb.
// Assign SV08_BROWSER_PROFILE_ROOT to a short owned scratch directory; no downloads.
// Cancellation retains the historical seeded backend only with explicit mode.
import {randomUUID} from 'node:crypto';
import {request as httpsRequest} from 'node:https';import {request as httpRequest} from 'node:http';
import {uploadCases} from './cockpit_upload_cases.mjs';
import fs from 'node:fs';import {execFileSync} from 'node:child_process';import {startBrowser,assertBrowserZoom,finiteStatusDiagnostic} from './browser_runtime.mjs';import {setTimeout as delay} from 'node:timers/promises';import assert from 'node:assert/strict';
const [W,chrome,mode='installed'] = process.argv.slice(2);
assert(['installed','cancellation'].includes(mode));
const baseURL=process.env.SV08_COCKPIT_URL || 'https://127.0.0.1:19091';
assert.match(baseURL,/^https?:\/\/127\.0\.0\.1:\d+$/);
const zoom=mode==='installed'?2:1;
assert(W && chrome);
if(typeof WebSocket!=='function')throw Error('Installed browser requires Node 22 native WebSocket');
const results={scope:'Actual installed Cockpit/PAM/sudo in disposable guest on private loopback',mode,base_url:baseURL,adapter_limits:'Disposable slot/service adapters; no printer or physical outputs',physical_hardware:false,production_tls:false};
const creds=JSON.parse(fs.readFileSync(W+'/credentials.json'));const browser=startBrowser({chrome,output:W,args:['--ignore-certificate-errors'],zoom});let socket;
try{
 const port=await browser.ready;
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j});
 let id=0;const pending=new Map(), browserEvents=[];function send(method,params={}){return new Promise((resolve,reject)=>{const key=++id;const timer=setTimeout(()=>reject(Error('CDP timeout '+method)),60000);pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params}))})}
 socket.onmessage=({data})=>{const e=JSON.parse(data);if(['Runtime.consoleAPICalled','Runtime.exceptionThrown','Log.entryAdded'].includes(e.method))browserEvents.push(e);if(e.id){const p=pending.get(e.id);if(p){clearTimeout(p.timer);pending.delete(e.id);e.error?p.reject(Error('CDP error')):p.resolve(e.result)}}};
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error('Browser evaluation failed: '+r.exceptionDetails.text);return r.result.value};
 const until=async expression=>{
  for(let i=0;i<200;i++){if(await ev(expression))return;await delay(200)}
  const failure=Error('Timeout '+expression);
  try{
   // Public feedback and boolean guards only: no inputs, plans, bodies or DOM.
   const snapshot=await ev(`({texts:Object.fromEntries(['notice','upload-status','upload-storage','connection','session-status'].map(id=>[id,document.getElementById(id)?.textContent?.slice(0,2048)??''])),flags:{busy:typeof busy==='boolean'?busy:null,jobs_busy:typeof jobsBusy==='boolean'?jobsBusy:null,refreshing:typeof refreshing==='boolean'?refreshing:null,state_present:typeof state!=='undefined'&&!!state,elevated:window.sv08Session?.elevated===true,review_open:document.getElementById('review')?.open===true,upload_review_open:document.getElementById('upload-review')?.open===true,upload_active:typeof uploadActive==='boolean'?uploadActive:null},disabled:Object.fromEntries(['save-auto','stage-image','review-upload','confirm-upload','cancel-upload','authorize','stop-authorization'].map(id=>[id,document.getElementById(id)?.disabled??null]))})`);
   const secrets=Object.entries(creds).flatMap(([account,password])=>[password,Buffer.from(account+':'+password).toString('base64')]);
   secrets.push('ephemeral-draft-secret');
   const diagnostic={texts:Object.fromEntries(Object.entries(snapshot.texts).map(([id,value])=>[id,finiteStatusDiagnostic('host',{message:value},secrets).message])),flags:snapshot.flags,disabled:snapshot.disabled};
   fs.writeFileSync(W+'/journey-timeout.json',JSON.stringify(diagnostic,null,2)+'\n',{mode:0o600});
  }catch{/* Preserve the original timeout if diagnostic capture itself fails. */}
  throw failure;
 };
 const click = async selector => { await until(`!!document.querySelector(${JSON.stringify(selector)}) && !document.querySelector(${JSON.stringify(selector)}).disabled`); return ev(`document.querySelector(${JSON.stringify(selector)}).click()`); };
 const text = selector => ev(`document.querySelector(${JSON.stringify(selector)}).textContent`);
 const field = (selector,value) => ev(`(()=>{const p=document.querySelector(${JSON.stringify(selector)});p.value=${JSON.stringify(value)};p.dispatchEvent(new Event('input',{bubbles:true}));})()`);
 const key=async(key,shift=false)=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,modifiers:shift?8:0,windowsVirtualKeyCode:{Tab:9,Enter:13,Escape:27}[key],text:key==='Enter'?'\r':undefined});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key,modifiers:shift?8:0});};
 const capture=async name=>{const image=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(W+'/'+name+'.png',Buffer.from(image.data,'base64'));};
 // Observe the page's own finite reads. Return the original promise unchanged;
 // this probe adds no RPC, lock contender, retry, authentication or mock result.
 const installStatusObserver=()=>{
  let implementation,epoch=0,authorityEpoch=0,sequence=0;
  window.sv08StatusReads=[];
  window.addEventListener('sv08-navigation-changed',()=>{epoch++});
  window.addEventListener('sv08-authority-changed',()=>{epoch++;authorityEpoch++});
  Object.defineProperty(window,'sv08View',{configurable:true,get:()=>implementation,set:original=>{
   implementation=function(...args){
    const promise=original.apply(this,args),[area,method='status']=args;
    if(method==='status'&&['host','printer','network','software','identity','mainsail-access'].includes(area)){
     const record={sequence:++sequence,area,method,epoch,authority_epoch:authorityEpoch,route:location.hash.slice(1),elevated:window.sv08Session?.elevated===true,completed:false};
     window.sv08StatusReads.push(record);if(window.sv08StatusReads.length>128)window.sv08StatusReads.shift();
     promise.then(result=>{record.completed=true;record.ok=true;record.valid_result=!!result&&typeof result==='object'&&!Array.isArray(result);record.revision=result?.revision??result?.state?.revision??null;},error=>{record.completed=true;record.ok=false;record.error={message:typeof error?.message==='string'?error.message:'Finite read failed',problem:error?.problem,exit_status:error?.exit_status,exit_signal:error?.exit_signal};});
    }
    return promise;
   };
  }});
  window.sv08ObservedStatus=(area,name)=>window.sv08StatusReads.findLast(record=>record.area===area&&record.method==='status'&&record.completed&&!record.elevated&&record.authority_epoch===authorityEpoch&&(area==='printer'||record.epoch===epoch&&record.route===name));
 };
 const recordedReadErrors=new Set();results.ui_read_errors=[];
 const retainReadErrors=async()=>{
  const failures=await ev(`window.sv08StatusReads.filter(record=>record.completed&&!record.ok)`);
  const secrets=Object.entries(creds).flatMap(([account,password])=>[password,Buffer.from(account+':'+password).toString('base64')]);
  for(const record of failures){
   if(recordedReadErrors.has(record.sequence))continue;recordedReadErrors.add(record.sequence);
   results.ui_read_errors.push({sequence:record.sequence,epoch:record.epoch,authority_epoch:record.authority_epoch,read_route:record.route,elevated:record.elevated,...finiteStatusDiagnostic(record.area,record.error,secrets)});
  }
 };
 const observedStatus=async(area,name=area,ready='true')=>{
  // Wait only for the page's existing reads/polls and its rendered readiness.
  // Printer subroutes reuse the current ordinary session's loaded snapshot.
  try{
   await until(`(()=>{const record=window.sv08ObservedStatus(${JSON.stringify(area)},${JSON.stringify(name)});return record?.ok===true&&record.valid_result&&(${ready})})()`);
  }catch{
   await retainReadErrors();
   const diagnostic={route:name,area,method:'status',observed_ui_read:true,message:'Actual UI did not reach a successful current finite read and rendered ready state within the existing timeout.',ui_read_errors:results.ui_read_errors};
   try{await capture('installed-'+name+'-finite-status-failed');diagnostic.screenshot='installed-'+name+'-finite-status-failed.png';}catch{diagnostic.screenshot='unavailable';}
   fs.writeFileSync(W+'/finite-status-error.json',JSON.stringify(diagnostic,null,2)+'\n',{mode:0o600});
   throw Error('Actual UI finite status remained unavailable: '+area+' / '+name+'; inspect finite-status-error.json');
  }
  await retainReadErrors();
  const record=await ev(`window.sv08ObservedStatus(${JSON.stringify(area)},${JSON.stringify(name)})`);
  assert.equal(record.ok,true,name+' actual UI read');assert.equal(record.valid_result,true,name+' real UI finite result');return record;
 };
 const route=async name=>{await ev(`sv08Navigation.go(${JSON.stringify(name)})`);await until(`!document.querySelector('#${name}').hidden`);};
 const navigate = async () => {
  // Page.navigate can resolve while the previous document is still complete.
  // A per-document marker also distinguishes reconnects to the same URL.
  const previousDocument=randomUUID();
  await ev(`window.sv08NavigationProbe=${JSON.stringify(previousDocument)}`);
  await send('Page.navigate',{url:baseURL+'/'});
  await until(`location.origin===${JSON.stringify(new URL(baseURL).origin)} && document.readyState==='complete' && window.sv08NavigationProbe!==${JSON.stringify(previousDocument)}`);
 };
 const login = async (name,password) => ev(`fetch('/cockpit/login',{headers:{Authorization:'Basic '+btoa(${JSON.stringify(name+':'+password)}),'X-Superuser':'none'}}).then(r=>r.status)`);
 const loadShell = async () => { await navigate(); await until('!!window.sv08Session'); await until('sv08Session.elevated || !document.querySelector("#authorize").disabled || document.querySelector("#session-status").textContent.includes("unavailable")'); };
 const uid = () => ev(`cockpit.spawn(['id','-u'],{superuser:'require'}).then(x=>x.trim(),e=>e.problem)`);
 const helper = message => ev(`cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_admin.py'],{superuser:'require',err:'message'}).input(${JSON.stringify(JSON.stringify(message))}).then(x=>JSON.parse(x))`);
 const stateHash = () => ev(`cockpit.spawn(['/usr/bin/sha256sum','/data/sv08/state.json'],{superuser:'require'}).then(x=>x.split(' ')[0])`);
 const assertHelperOk=(response,label)=>{
  if(response?.ok!==true){
   const secrets=Object.entries(creds).flatMap(([account,password])=>[password,Buffer.from(account+':'+password).toString('base64')]);
   const diagnostic={operation:label,...finiteStatusDiagnostic('host',{message:response?.error||'Helper returned no successful result'},secrets)};
   (results.helper_errors??=[]).push(diagnostic);
   fs.writeFileSync(W+'/helper-errors.json',JSON.stringify(results.helper_errors,null,2)+'\n',{mode:0o600});
  }
  assert.equal(response?.ok,true,label+' failed; inspect helper-errors.json');
 };

 const authorize = async () => { await click('#authorize'); await until('document.querySelector("#authorization").open'); await field('#authorization-password',creds.fixtureadmin); await click('#answer-authorization'); await until('sv08Session.elevated'); await until('document.querySelector("#connection").textContent==="Host connected"'); assert.equal(await uid(),'0'); };
 const stopped = async () => { await click('#stop-authorization'); await until('!sv08Session.elevated && !document.querySelector("#authorize").disabled'); assert.equal(await uid(),'access-denied'); };
 const secretsClear = async () => {
   assert.equal(await ev('document.querySelector("#authorization-password").value'),'');
   assert.equal(await ev('document.querySelector("#authorization-prompt").textContent'),'');
   const storage=await ev('JSON.stringify({local:{...localStorage},session:{...sessionStorage}})');
   for(const password of Object.values(creds)) assert(!storage.includes(password));
 };
 await send('Network.clearBrowserCookies');await send('Page.enable');await send('Runtime.enable');await send('Log.enable');
 if(mode==='installed')await send('Page.addScriptToEvaluateOnNewDocument',{source:'('+installStatusObserver.toString()+')()'});
 await navigate();
 assert.equal(await login('fixtureadmin','deliberately-invalid'),401);results.bad_login_rejected=true;
 assert.equal(await login('fixtureordinary',creds.fixtureordinary),200);await loadShell();
 assert.equal(await uid(),'access-denied');
 if(mode==='installed') {
  const manifest=JSON.parse(execFileSync('python3',[new URL('./test_pr9_follow_up.py',import.meta.url).pathname,'--manifest'],{encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}}));
  const installedRuntime=await ev(`cockpit.spawn(['/usr/bin/find','/usr/lib/sv08','-maxdepth','1','-type','f','-name','sv08_*.py']).then(x=>x.trim().split('\\n'))`);
  for(const required of manifest.required_runtime)assert(installedRuntime.includes(required),'Missing installed runtime '+required);
  const expected={...manifest.assets};
  for(const target of installedRuntime){assert(target in manifest.runtime,'Unexpected installed runtime '+target);expected[target]=manifest.runtime[target];}
  const hashes=await ev(`cockpit.spawn(['/usr/bin/sha256sum',...${JSON.stringify(Object.keys(expected))}]).then(x=>x)`);
  const actual={};for(const line of hashes.trim().split('\n')){const [hash,target]=line.split(/\s+/);assert.equal(hash,expected[target],target+' source mismatch');actual[target]=hash;}
  assert.deepEqual(Object.keys(actual).sort(),Object.keys(expected).sort());
  fs.writeFileSync(W+'/installed-source.json',JSON.stringify({installed:actual,runner_sources:manifest.runner_sources},null,2)+'\n');
  results.installed_sources=actual;results.runner_sources=manifest.runner_sources;
  results.ordinary_routes=[];
  const areas={overview:'host',images:'host',settings:'host',recovery:'host',printer:'printer',definitions:'printer','definition-sources':'printer','printer-connections':'printer',network:'network',software:'software',identity:'identity','mainsail-access':'mainsail-access'};
  for(const [name,area] of Object.entries(areas)){
   await route(name);
   const ready=area==='host'?`document.querySelector('#connection').textContent==='Host connected'`:area==='printer'?`document.querySelector('#printer-notice').textContent.startsWith('Saved configuration loaded.')`:name==='network'?`document.querySelector('#network-status').textContent==='Network settings are ready.'`:name==='software'?`document.querySelector('#software-status').textContent==='Software is ready.'`:name==='identity'?`document.querySelector('#identity-status').textContent==='Printer identity is ready.'`:`!document.querySelector('#access-status').textContent.startsWith('Loading')`;
   const status=await observedStatus(area,name,ready);assert(status&&typeof status==='object',name+' real UI finite read');
   assert.equal(await ev('sv08Session.elevated'),false);
   if(name==='images')assert(await ev('document.querySelector("#save-auto").disabled && document.querySelector("#stage-image").disabled'));
   if(name==='settings')assert(await ev('document.querySelector("#save-mode").disabled'));
   if(name==='printer')assert(await ev('document.querySelector("#printer-save").disabled'));
   if(name==='network')assert(await ev('document.querySelector("#network-apply").disabled'));
   if(name==='software')assert(await ev('document.querySelector("#software-install").disabled'));
   if(name==='identity')assert(await ev('document.querySelector("#identity-keys").readOnly && document.querySelector("#identity-save-keys").disabled'));
   if(name==='mainsail-access')assert(await ev('document.querySelector("#access-apply").disabled'));
   if(name==='recovery')assert.equal(await text('#recovery .card h2'),'Recovery boot entry is not enabled here');
   const metrics=await assertBrowserZoom({send,evaluate:ev,zoom});
   await ev('scrollTo(0,0)');await capture('installed-'+name+'-browser-200');
   results.ordinary_routes.push({route:name,area,real_read:true,observed_ui_read:{sequence:status.sequence,epoch:status.epoch,authority_epoch:status.authority_epoch,read_route:status.route,elevated:status.elevated,revision:status.revision,cached_subroute:area==='printer'},zoom:metrics});
  }
  await route('overview');
  const before=(await observedStatus('host','overview',`document.querySelector('#connection').textContent==='Host connected'`)).revision;
  const denied=await ev(`cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_admin.py']).input(JSON.stringify({method:'plan',action:'policy.auto',arguments:{enabled:false}})).then(x=>JSON.parse(x))`);
  assert.equal(denied.ok,false);assert.match(denied.error,/Administrator access/);
  await route('images');
  assert.equal((await observedStatus('host','images',`document.querySelector('#connection').textContent==='Host connected'`)).revision,before);
  results.ordinary_write_denial_no_revision_change=true;
  await route('overview');
 }
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
 if(mode==='cancellation'){ const inspected=await helper({method:'image.inspect',id:'dddddddddddddddddddddddddddddddd'});assert.equal(inspected.ok,true);const disposed=await helper({method:'image.dispose',plan:inspected.result.plan});assert.equal(disposed.ok,true);await click('#logout');await until('!window.sv08Session');assert.equal(await login('fixtureadmin',creds.fixtureadmin),200);await loadShell();await authorize();const cancelPlan=await helper({method:'plan',action:'image.cancel',arguments:{}});assert.equal(cancelPlan.ok,true);const submitted=await helper({method:'image.submit',id:'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',plan:cancelPlan.result});assert.equal(submitted.ok,true);for(let i=0;i<100;i++){const h=await helper({method:'jobs'});if(h.result.jobs.find(x=>x.id==='eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')?.phase==='succeeded')break;await delay(200)}const end=await helper({method:'jobs'});assert.equal(end.result.jobs.find(x=>x.id==='eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee').phase,'succeeded');const finalStatus=await helper({method:'status'});assert.equal(finalStatus.result.pending,null);assert.equal(finalStatus.result.boot.slot,'A');assert.equal(finalStatus.result.transaction.previous_slot,'A');const after=await helper({method:'jobs'});assert.equal(after.result.jobs.find(x=>x.id==='dddddddddddddddddddddddddddddddd').disposition.kind,'retain-unknown-v1');assert.equal(await ev(`cockpit.spawn(['/usr/bin/cat','/data/fixture/user-data-sentinel'],{superuser:'require'}).then(x=>x.trim())`),'preserved fixture data');results.composed={disposition:'unknown',cancellation:'succeeded',reconnect:true,source_slot:'A',data_sentinel_preserved:true};
 } else {
 // Run the real installed checker through this authenticated elevated bridge.
 const installedCheck=await ev(`(async()=>{let output='';const p=cockpit.spawn(['/usr/bin/python3','/payload/source/scripts/check_installed_cockpit.py','--manifest','/data/pr9-assets.json'],{superuser:'require',err:'message'});p.stream(chunk=>{output+=chunk;if(output.length>65536)p.close('terminated')});try{await p;return {exit_status:0,output}}catch(error){return {exit_status:Number.isInteger(error.exit_status)?error.exit_status:null,output}}})()`);
 assert(installedCheck.output.length<=65536,'Installed checker report exceeded bound');
 let installedReport;try{installedReport=JSON.parse(installedCheck.output)}catch{throw Error('Installed checker returned an invalid public result')}
 fs.writeFileSync(W+'/installed-checker-result.json',JSON.stringify({exit_status:installedCheck.exit_status,result:installedReport},null,2)+'\n',{mode:0o600});
 assert.equal(installedCheck.exit_status,0,'Installed checker exit failed; inspect installed-checker-result.json');
 assert.equal(installedReport.passed,true,'Installed checker failed; inspect installed-checker-result.json');
 results.installed_checker=installedReport;

 // Preserve unfinished non-secret network input across navigation and End access.
 await route('network');await until(`document.querySelector('#network-status').textContent==='Network settings are ready.'`);
 const draftBefore=await stateHash();
 await field('#network-hostname','pr9-unsaved-draft');await field('#network-password','ephemeral-draft-secret');
 await route('overview');await route('network');await until(`document.querySelector('#network-status').textContent==='Network settings are ready.'`);
 assert.equal(await ev(`document.querySelector('#network-hostname').value`),'pr9-unsaved-draft');
 await stopped();
 // End access must clear sensitive input and disable writes immediately. Observe
 // the page's authority-change read before choosing any visible recovery action.
 assert.equal(await ev(`document.querySelector('#network-hostname').value`),'pr9-unsaved-draft');
 assert.equal(await ev(`document.querySelector('#network-password').value`),'');
 assert(await ev(`document.querySelector('#network-apply').disabled`));
 const transition={explicit_refresh:false,observations:[]};
 const transitionSnapshot=async()=>{
  await retainReadErrors();
  const snapshot=await ev(`({status:document.querySelector('#network-status').textContent,read:window.sv08ObservedStatus('network','network')??null})`);
  const secrets=[...Object.values(creds),'ephemeral-draft-secret'];
  const read=snapshot.read;
  transition.observations.push({status:finiteStatusDiagnostic('network',{message:snapshot.status},secrets).message,
   read:read?{sequence:read.sequence,epoch:read.epoch,authority_epoch:read.authority_epoch,route:read.route,elevated:read.elevated,completed:read.completed,ok:read.ok,valid_result:read.valid_result??false,...(!read.ok?{error:finiteStatusDiagnostic('network',read.error,secrets)}:{})}:null});
  results.end_access_network_transition=transition;
  fs.writeFileSync(W+'/end-access-network-transition.json',JSON.stringify(transition,null,2)+'\n',{mode:0o600});
  return read;
 };
 try{
  await until(`!!window.sv08ObservedStatus('network','network')`);
  const firstRead=await transitionSnapshot();
  let minimumSequence=firstRead.sequence;
  if(firstRead.ok===false){
   // One existing user-visible Refresh, only for a demonstrated failed read.
   // A successful read reporting an unavailable draft target cannot recover here.
   transition.explicit_refresh=true;
   await click('#network-refresh');
  }else minimumSequence--;
  await observedStatus('network','network',`document.querySelector('#network-status').textContent==='Network settings are ready.' && window.sv08ObservedStatus('network','network').sequence>${minimumSequence}`);
 }finally{await transitionSnapshot();}
 assert.equal(await ev(`document.querySelector('#network-hostname').value`),'pr9-unsaved-draft');
 assert.equal(await ev(`document.querySelector('#network-password').value`),'');
 assert(await ev(`document.querySelector('#network-apply').disabled`));
 // Network recovery is complete. Leave its preserved draft intact and continue
 // the independent history journey on Settings before changing authority.
 await route('settings');await authorize();assert.equal(await stateHash(),draftBefore);
 results.end_access_preserves_draft_clears_secret=true;
 // A retained maintenance receipt exposes the global indicator; activation is navigation only.
 await ev(`localStorage.setItem('sv08-history-maintenance',JSON.stringify({method:'history.apply'}));refresh()`);
 await until(`!document.querySelector('#operation-indicator').hidden`);await route('settings');
 const navigationBefore=await stateHash();
 await stopped(); // Navigation remains usable immediately after real End access.
 assert.equal(await ev(`document.querySelector('#operation-indicator').disabled`),false);
 assert.equal(await ev(`sv08Session.elevated`),false);
 await ev(`document.querySelector('#operation-indicator').focus()`);await key('Enter');
 await until(`document.activeElement.id==='image-history-title'`);
 assert(await ev(`(()=>{const r=document.querySelector('#image-history-title').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight})()`));
 await capture('installed-indicator-history-browser-200');await ev('history.back()');await until(`location.hash==='#settings' && document.activeElement.matches('#settings h1')`);
 await delay(100); // Require settled heading focus, not a transient popstate focus.
 assert.equal(await ev(`document.activeElement.closest('.page')?.id`),'settings');
 assert.equal(await ev(`sv08Session.elevated`),false);assert.equal(await uid(),'access-denied');
 await authorize();assert.equal(await stateHash(),navigationBefore);
 results.indicator_ordinary_end_access_navigation=true;
 await ev(`localStorage.removeItem('sv08-history-maintenance');refresh()`);results.indicator_keyboard_back_no_mutation=true;
 await route('images');await until(`!document.querySelector('#save-auto').disabled`);
 const reviewBefore=await stateHash();
 // Observe the existing policy-plan request and guard state without another RPC.
 const policyMessages=new Set(['Review the change before applying.']);
 for(const source of ['../ui/host/app.js','../runtime/sv08_admin.py','../runtime/sv08_state.py','../runtime/sv08_data_budget.py']){
  const body=fs.readFileSync(new URL(source,import.meta.url),'utf8');
  for(const match of body.matchAll(/(?:Error|ValueError|BusyError)\('([^'\n]+)'\)/g))policyMessages.add(match[1]);
 }
 const installPolicyProbe=messages=>{
  const original=request,allowed=new Set(messages),records=[];
  const sanitize=value=>typeof value==='string'&&allowed.has(value)?value.slice(0,512):value?'Unrecognized public message withheld.':'';
  const snapshot=()=>({busy,jobs_busy:jobsBusy,state_present:!!state,refreshing,elevated:sv08Session.elevated===true,authority_generation:authorityGeneration,button_disabled:document.querySelector('#save-auto').disabled,review_open:document.querySelector('#review').open,notice:sanitize(document.querySelector('#notice').textContent)});
  const before=snapshot();
  const wrapped=function(...args){
   const promise=original.apply(this,args);
   if(args[0]?.method==='plan'){
    const record={method:'plan',completed:false,authority_generation:authorityGeneration};records.push(record);
    promise.then(()=>{record.completed=true;record.ok=true;},error=>{record.completed=true;record.ok=false;record.error={message:sanitize(error?.message),acknowledged:error?.acknowledged===true,exit_status:Number.isInteger(error?.exit_status)?error.exit_status:null,problem:['access-denied','disconnected','terminated','timeout','not-found'].includes(error?.problem)?error.problem:null};});
   }
   return promise;
  };
  request=wrapped;
  window.pr9PolicyReviewProbe={snapshot:()=>({before,after:snapshot(),plan_reads:records.slice(-4)}),restore:()=>{if(request!==wrapped)throw Error('Policy observer ownership changed');request=original;delete window.pr9PolicyReviewProbe;}};
 };
 await ev(`(${installPolicyProbe.toString()})(${JSON.stringify([...policyMessages])})`);
 try{await click('#save-auto');await until(`document.querySelector('#review').open`);}
 finally{
  const diagnostic=await ev('window.pr9PolicyReviewProbe.snapshot()');
  fs.writeFileSync(W+'/policy-review-boundary.json',JSON.stringify(diagnostic,null,2)+'\n',{mode:0o600});
  results.policy_review_boundary=diagnostic;
  await ev('window.pr9PolicyReviewProbe.restore()');
 }

 await ev(`document.querySelector('#review button[value="cancel"]').focus()`);await key('Tab');
 assert.equal(await ev('document.activeElement.id'),'confirm');await key('Tab',true);
 assert.equal(await ev('document.activeElement.value'),'cancel');
 const readable=await ev(`Array.from(document.querySelectorAll('#review button')).every(b=>{const r=b.getBoundingClientRect();return r.width>0&&r.height>0&&r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight})`);
 assert(readable,'Modal actions remain visible at actual browser 200%');await capture('installed-review-keyboard-browser-200');
 await key('Escape');await until(`!document.querySelector('#review').open && document.activeElement.id==='save-auto'`);
 assert.equal(await stateHash(),reviewBefore);results.actual_zoom_keyboard_modal_focus_return_no_mutation=true;
 // The fresh guest seeds this baseline; acceptance must not repair its inputs.
 const baseline=await helper({method:'status'});assertHelperOk(baseline,'fixture baseline status');
 assert.equal(baseline.result.auto_update,true,'Fresh fixture automatic-update baseline');
 assert.equal(baseline.result.requested_mode,'immutable','Fresh fixture mode baseline');
 results.fixture_baseline={auto_update:baseline.result.auto_update,requested_mode:baseline.result.requested_mode};
 // Export only this named public bundle. The signing key never leaves the guest.
 if(!fs.existsSync(W+'/signed.raucb')) {
  const encoded=await ev(`cockpit.spawn(['/usr/bin/base64','/data/pr9-signer/signed.raucb'],{superuser:'require',err:'message'}).then(x=>x)`);
  assert(/^[A-Za-z0-9+/=\s]+$/.test(encoded),'Invalid public bundle encoding');
  const bundle=Buffer.from(encoded,'base64');assert(bundle.length>0 && bundle.length<=32*1024*1024,'Public fixture bundle exceeds assigned export bound');
  fs.writeFileSync(W+'/signed.raucb',bundle,{flag:'wx',mode:0o600});
 }
 assert(fs.existsSync(W+'/signed.raucb'),'Installed acceptance requires the guest-generated public signed bundle at W/signed.raucb');
 results.upload=await uploadCases({W,ev,send,until,click,helper,stateHash,loadShell,authorize}); console.log('real upload cases PASS');

 const originalHash=await stateHash();const status=await helper({method:'status'});assert.equal(status.ok,true);assert.equal(status.result.auto_update,true);
 const jobs=await helper({method:'jobs'});assert.equal(jobs.ok,true);assert.deepEqual(jobs.result.jobs,[]);
 const plan=await helper({method:'plan',action:'policy.auto',arguments:{enabled:false}});assert.equal(plan.ok,true);assert.equal(await stateHash(),originalHash);results.status_review_jobs_no_state_mutation=true;
 await click('[data-page="images"]');await click('#auto-update');await click('#save-auto');await until('document.querySelector("#review").open');await ev('document.querySelector("#review").close("cancel")');assert.equal(await stateHash(),originalHash);results.cancel_preserves_state=true;
 // Stop invalidates an open review; later authentication must not confirm it.
 await click('#save-auto');await until('document.querySelector("#review").open');await ev('document.querySelector("#stop-authorization").click()');await until('!sv08Session.elevated && !document.querySelector("#authorize").disabled');assert.equal(await ev('document.querySelector("#review").open'),false);await authorize();assert.equal(await stateHash(),originalHash);assert.equal(await ev('document.querySelector("#review").open'),false);results.authentication_never_confirms=true;
 // A review based on old policy must be refused by the real installed helper.
 await click('#save-auto');await until('document.querySelector("#review").open');
 const other=await helper({method:'plan',action:'policy.mode',arguments:{mode:'writable'}});assertHelperOk(other,'stale-review policy.mode plan');const otherApplied=await helper({method:'apply',plan:other.result});assertHelperOk(otherApplied,'stale-review policy.mode apply');
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
 const serviceState=await ev(`cockpit.spawn(['systemctl','show','cockpit.socket','cockpit.service','-p','Id','-p','ActiveState','-p','SubState'],{superuser:'require'}).then(x=>x)`);
 assert.equal((serviceState.match(/ActiveState=active/g)||[]).length,2);fs.writeFileSync(W+'/guest-service-state.txt',serviceState);
 const cookie=(await send('Network.getCookies',{urls:[baseURL+'/']})).cookies.map(c=>c.name+'='+c.value).join(';');assert(cookie);
 await stopped();await secretsClear();results.explicit_stop_denies_helper=true;await click('#logout');await until('!window.sv08Session');
 assert.equal(await new Promise((resolve,reject)=>{const req=(baseURL.startsWith('https:')?httpsRequest:httpRequest)(baseURL+'/cockpit/login',{rejectUnauthorized:false,headers:{Cookie:cookie}},r=>{r.resume();resolve(r.statusCode)});req.on('error',reject);req.setTimeout(10000,()=>req.destroy(Error('Session check timeout')));req.end();}),401);
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
 for(const name of ['guest.log','package-install.log','apt-simulation.txt','units.txt','prepare.json','guest-service-state.txt','browser.log'])if(fs.existsSync(W+'/'+name))scanFile(W+'/'+name);
 for(const value of forbidden)assert(!JSON.stringify(browserEvents).includes(value),'Credential found in browser console/error');
 for(const value of forbidden)assert(!JSON.stringify(results).includes(value),'Credential found in report');
 results.secret_scan={guest_journal:true,browser_console_and_errors:true,private_log_and_evidence_files:scanned.length,violations:0};
 }
 results.passed=true;fs.writeFileSync(W+'/composed-result.json',JSON.stringify(results,null,2)+'\n');console.log('Actual Cockpit authentication, helper/session and transition tests PASS');
}finally{socket?.close();await browser.stop();}
