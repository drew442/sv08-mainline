// Real installed guest routes only. Strict TLS evidence is produced first by
// recovery_restore_stack.py host-assert; Chromium trusts only that leaf SPKI.
import fs from 'node:fs';
import path from 'node:path';
import {createHash, randomUUID} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';
import {startBrowser} from './browser_runtime.mjs';

const [fixture, output, chrome, expected] = process.argv.slice(2);
assert(fixture && output && chrome && ['previous','restored'].includes(expected));
assert.equal(fs.readFileSync(path.join(fixture,'disposable-marker'),'utf8'),'sv08-disposable-recovery-stack-v1\n');
const strict=JSON.parse(fs.readFileSync(path.join(output,'host-assert.json')));
assert.equal(strict.result,'PASS'); assert.equal(strict.strict_ca_and_hostname,true); assert.equal(strict.expected,expected);
const credentials=JSON.parse(fs.readFileSync(path.join(fixture,'credentials.json')));
const gateway=credentials[expected], owner=credentials.owner;
const publicKey=execFileSync('openssl',['x509','-in',path.join(output,'service-public.crt'),'-pubkey','-noout']);
const der=execFileSync('openssl',['pkey','-pubin','-outform','DER'],{input:publicKey});
const spki=createHash('sha256').update(der).digest('base64');
const browser=startBrowser({chrome,output,args:['--ignore-certificate-errors-spki-list='+spki]});
let socket; const pending=new Map(); const result={expected,physical_hardware:false,printing_ready:false,strict_tls_receipt:'host-assert.json',browser_trust:'verified current synthetic leaf SPKI only'};
try {
 const port=await browser.ready;
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject});
 let id=0; let origin='https://127.0.0.1:18443';
 const send=(method,params={})=>new Promise((resolve,reject)=>{
  const key=++id;const timer=setTimeout(()=>{pending.delete(key);reject(Error('Bounded browser command failed: '+method))},30000);
  pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params}));
 });
 socket.onmessage=({data})=>{
  const event=JSON.parse(data);
  if(event.id&&pending.has(event.id)){const p=pending.get(event.id);pending.delete(event.id);clearTimeout(p.timer);event.error?p.reject(Error('Browser protocol failed')):p.resolve(event.result)}
  if(event.method==='Fetch.authRequired'){
   const {requestId,request}=event.params;
   const auth=request.url.startsWith('https://127.0.0.1:18443/')?{response:'ProvideCredentials',username:gateway.username,password:gateway.password}:{response:'CancelAuth'};
   send('Fetch.continueWithAuth',{requestId,authChallengeResponse:auth}).catch(()=>{});
  }
  if(event.method==='Fetch.requestPaused'){
   const {requestId,request}=event.params;const allowed=request.url.startsWith(origin+'/');
   send(allowed?'Fetch.continueRequest':'Fetch.failRequest',allowed?{requestId}:{requestId,errorReason:'BlockedByClient'}).catch(()=>{});
  }
 };
 const evaluate=async expression=>{const response=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(response.exceptionDetails)throw Error('Installed browser evaluation failed');return response.result.value};
 const until=async expression=>{const end=Date.now()+120000;while(Date.now()<end){if(await evaluate(expression))return;await delay(250)}throw Error('Installed route readiness deadline')};
 const navigate=async url=>{const marker=randomUUID();await evaluate(`window.sv08StackDocument=${JSON.stringify(marker)}`);await send('Page.navigate',{url});await until(`location.href.startsWith(${JSON.stringify(url)}) && document.readyState==='complete' && window.sv08StackDocument!==${JSON.stringify(marker)}`)};
 const capture=async filename=>{const image=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(output,filename),Buffer.from(image.data,'base64'),{mode:0o600})};
 await send('Runtime.enable');await send('Page.enable');await send('Network.enable');
 await send('Fetch.enable',{patterns:[{urlPattern:'*'}],handleAuthRequests:true});
 await navigate(origin+'/');
 await until('Boolean(document.querySelector("[data-app=true]")?.__vue__?.$store)');
 await until('(()=>{const state=document.querySelector("[data-app=true]").__vue__.$store.state;return state.socket.isConnected && !!state.server.moonraker_version && state.socket.initializationList.length===0})()');
 result.mainsail=await evaluate('(()=>{const s=document.querySelector("[data-app=true]").__vue__.$store.state;return {mounted:true,websocket_connected:s.socket.isConnected,moonraker_version:s.server.moonraker_version,klippy_state:s.server.klippy_state}})()');
 assert(['disconnected','startup','error','shutdown'].includes(result.mainsail.klippy_state));await capture('mainsail-installed.png');
 origin='https://127.0.0.1:19090';
 await send('Fetch.disable');await send('Fetch.enable',{patterns:[{urlPattern:'*'}],handleAuthRequests:true});
 await navigate(origin+'/');
 const login=async password=>evaluate(`fetch('/cockpit/login',{headers:{Authorization:'Basic '+btoa(${JSON.stringify(owner.username+':')}+${JSON.stringify(password)}),'X-Superuser':'none'}}).then(response=>response.status)`);
 assert.equal(await login('deliberately-invalid'),401);assert.equal(await login(owner.password),200);
 // Enter the installed plugin document explicitly, regardless of outer shell
 // framing/default-shell configuration. Helpers use its real Cockpit bridge.
 await navigate(origin+'/cockpit/@localhost/sv08-host/index.html');
 await until('!!window.sv08Session && typeof window.sv08View === "function"');
 for(const area of ['host','printer','network','identity','mainsail-access']){
  const response=await evaluate(`sv08View(${JSON.stringify(area)},'status').then(result=>({ok:true,valid:!!result&&typeof result==='object'}),()=>({ok:false}))`);
  assert.equal(response.ok,true,'Actual read helper failed: '+area);assert.equal(response.valid,true);
 }
 await until('!document.querySelector("#authorize").disabled');
 // Start clears stale input in both supported Cockpit sudo flows. The shipped
 // owner policy can elevate without emitting the session Prompt event.
 await evaluate('document.querySelector("#authorization-password").value="synthetic-stale-authorization-input";document.querySelector("#authorize").click()');
 await until('sv08Session.elevated===true || document.querySelector("#authorization").open');
 const authorizationPrompted=await evaluate('document.querySelector("#authorization").open && !sv08Session.elevated');
 if(authorizationPrompted){
  await evaluate(`(()=>{const field=document.querySelector('#authorization-password');field.value=${JSON.stringify(owner.password)};field.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#answer-authorization').click()})()`);
 }
 await until('sv08Session.elevated===true && !document.querySelector("#authorization").open');
 assert.equal(await evaluate('document.querySelector("#authorization-password").value'),'');
 assert.equal(await evaluate('document.querySelector("#authorization-prompt").textContent'),'');
 assert.equal(await evaluate(`cockpit.spawn(['id','-u'],{superuser:'require'}).then(value=>value.trim())`),'0');
 const helper=await evaluate(`cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_admin.py'],{superuser:'require',err:'message'}).input(JSON.stringify({action:'status'})).then(raw=>({ok:JSON.parse(raw).ok}),()=>({ok:false}))`);
 assert.equal(helper.ok,true,'Real elevated host helper failed');
 await evaluate('sv08Navigation.go("identity")');await until('!document.querySelector("#identity").hidden');
 await capture('cockpit-owner-identity.png');
 await evaluate('document.querySelector("#stop-authorization").click()');await until('!sv08Session.elevated');
 assert.equal(await evaluate('document.querySelector("#authorization-password").value'),'');
 const storage=await evaluate('JSON.stringify({local:{...localStorage},session:{...sessionStorage}})');
 for(const entry of Object.values(credentials))assert(!storage.includes(entry.password),'Synthetic password persisted in browser storage');
 result.cockpit={pam_owner_login:true,wrong_password_refused:true,real_finite_helpers:true,real_sudo_authorization:true,authorization_prompted:authorizationPrompted,passwordless_sudo:!authorizationPrompted,elevated_host_helper:true,authorization_cleared:true};
 result.result='PASS'; fs.writeFileSync(path.join(output,'browser-assert.json'),JSON.stringify(result,null,2)+'\n',{mode:0o600});
 console.log(JSON.stringify(result));
} finally {
 for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser stopped'))}pending.clear();socket?.close();await browser.stop();
}
