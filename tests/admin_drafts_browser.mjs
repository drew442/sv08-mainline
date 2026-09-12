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
 const key=async key=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:{Tab:9,Enter:13,Escape:27,ArrowDown:40,ArrowUp:38}[key],text:key==='Enter'?'\r':undefined});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});};
 const screenshot=async name=>{const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(r.data,'base64'));};
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url});await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 const edit=async (id,value)=>evaluate(`(()=>{const input=document.querySelector(${JSON.stringify(id)});input.value=${JSON.stringify(value)};input.dispatchEvent(new Event('input',{bubbles:true}));})()`);
 const controls=()=>evaluate(`({hostname:document.querySelector('#hostname').value,mode:document.querySelector('[name=mode]:checked').value,auto:document.querySelector('#auto-update').checked})`);
 const serverName=name=>evaluate(`(async()=>{const plan=await request({method:'plan',action:'config.hostname',arguments:{hostname:${JSON.stringify(name)}}});return await request({method:'apply',plan});})()`);
 await serverName('server-before');await delay(1800);
 assert.equal((await controls()).hostname,'server-before'); // Untouched controls follow the host.
 await click('[data-page="settings"]');
 await edit('#hostname','owner-draft');await click('[name="mode"][value="writable"]');
 await click('[data-page="images"]');await click('#auto-update');
 const before=await controls();await delay(3400);const after=await controls();
 assert.deepEqual(after,before);assert.deepEqual(before,{hostname:'owner-draft',mode:'writable',auto:false});
 await serverName('server-other');await delay(3400);
 assert.deepEqual(await controls(),before);assert.equal(await evaluate('state.hostname'),'server-other');
 await click('[data-page="settings"]');await click('#save-hostname');await until(`document.querySelector('#review').open`);
 assert.equal(await evaluate('plan.arguments.hostname'),'owner-draft');await key('Escape');await delay(1800);
 assert.deepEqual(await controls(),before);
 await click('#save-hostname');await until(`document.querySelector('#review').open`);await click('#confirm');
 await until(`!busy && document.querySelector('#notice').textContent.startsWith('Saved.')`);
 assert.deepEqual(await controls(),before); // Applying one control preserves the other drafts.
 await serverName('server-after');await delay(1800);
 assert.equal((await controls()).hostname,'server-after'); // Applied draft is now clean.
 assert.equal((await controls()).mode,'writable');assert.equal((await controls()).auto,false);
 // A changed revision rejects the reviewed mutation but retains the draft.
 await click('#save-mode');await until(`document.querySelector('#review').open`);
 assert.equal(await evaluate('plan.arguments.mode'),'writable');
 await serverName('invalidate-review');await click('#confirm');
 await until(`!busy && document.querySelector('#notice').textContent.includes('state changed')`);await delay(1800);
 assert.equal((await controls()).mode,'writable');assert.equal(JSON.parse(fs.readFileSync(fixture+'/state/state.json')).requested_mode,'immutable');
 await click('#save-mode');await until(`document.querySelector('#review').open`);await click('#confirm');
 await until(`!busy && document.querySelector('#notice').textContent.startsWith('Saved.')`);
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/state/state.json')).requested_mode,'writable');
 assert.equal((await controls()).auto,false);
 await click('[data-page="images"]');await click('#save-auto');await until(`document.querySelector('#review').open`);
 assert.equal(await evaluate('plan.arguments.enabled'),false);await click('#confirm');
 await until(`!busy && document.querySelector('#notice').textContent.startsWith('Saved.')`);
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/state/state.json')).auto_update,false);
 // A newer edit made while the saved response is in flight is not cleared.
 await click('[data-page="settings"]');await edit('#hostname','submitted-name');
 await evaluate(`(()=>{const original=cockpit.spawn;let hold=true;cockpit.spawn=(...args)=>{const process=original(...args);return {input:async data=>{const raw=await process.input(data);if(hold && JSON.parse(data).method==='apply'){hold=false;await new Promise(resolve=>{window.releaseApplyAck=resolve;});}return raw;}};};})()`);
 await click('#save-hostname');await until(`document.querySelector('#review').open`);await click('#confirm');
 await until(`typeof window.releaseApplyAck==='function'`);await edit('#hostname','newer-draft');
 await evaluate('window.releaseApplyAck()');await until('!busy');await delay(1800);
 assert.equal((await controls()).hostname,'newer-draft');assert.equal(await evaluate('state.hostname'),'submitted-name');
 // List changes are test-only status projections; no image/package mutation is simulated.
 await evaluate(`(()=>{window.fixtureImages=[{id:'a'.repeat(64),label:'First image'},{id:'b'.repeat(64),label:'Second image'}];window.fixturePackages=[{id:'first',label:'First package'},{id:'second',label:'Second package'}];const original=cockpit.spawn;cockpit.spawn=(...args)=>{const process=original(...args);return {input:async data=>{const raw=await process.input(data);const result=JSON.parse(raw);if(JSON.parse(data).method==='status' && result.ok){result.result.images=window.fixtureImages;result.result.catalog=window.fixturePackages;for(const action of ['image.stage','software.install','software.remove'])result.result.capabilities[action]={available:true,reason:''};}return JSON.stringify(result);}};};})()`);
 await delay(1800);
 for(const [id,value] of [['image-choice','b'.repeat(64)],['package-choice','second']])await evaluate(`(()=>{const input=document.getElementById(${JSON.stringify(id)});input.value=${JSON.stringify(value)};input.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 await click('[data-page="software"]');
 await evaluate(`(()=>{const select=document.querySelector('#package-choice');select.value='first';select.dispatchEvent(new Event('change',{bubbles:true}));select.focus();window.retainedOption=select.options[1];})()`);
 await key('ArrowDown');await delay(3400);
 assert.equal(await evaluate(`document.querySelector('#package-choice')===document.activeElement`),true);
 assert.equal(await evaluate(`document.querySelector('#package-choice').options[1]===window.retainedOption`),true);
 assert.equal(await evaluate(`document.querySelector('#image-choice').value`),'b'.repeat(64));
 assert.equal(await evaluate(`document.querySelector('#package-choice').value`),'second');
 await evaluate(`window.fixtureImages=window.fixtureImages.slice(0,1);window.fixturePackages=window.fixturePackages.slice(0,1)`);
 await delay(3400);
 for(const id of ['image-choice','package-choice']) {
   assert.equal(await evaluate(`document.getElementById('${id}').value`),'');
   assert.match(await evaluate(`document.getElementById('${id}').selectedOptions[0].textContent`),/Previous selection is unavailable/);
 }
 for(const id of ['stage-image','install-package','remove-package'])assert.equal(await evaluate(`document.getElementById('${id}').disabled`),true);
 await delay(1800); // Another poll must not silently choose the remaining item.
 assert.equal(await evaluate(`document.querySelector('#image-choice').value`),'');
 assert.equal(await evaluate(`document.querySelector('#package-choice').value`),'');
 for(const [id,value] of [['image-choice','a'.repeat(64)],['package-choice','first']])await evaluate(`(()=>{const input=document.getElementById(${JSON.stringify(id)});input.value=${JSON.stringify(value)};input.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 await delay(1800);
 for(const id of ['stage-image','install-package','remove-package'])assert.equal(await evaluate(`document.getElementById('${id}').disabled`),false);
 assert.equal(errors.length,0);
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,before,after,dwell_ms:3400,external_changes_preserve_drafts:true,untouched_controls_follow_server:true,cancel_and_stale_review_preserve_drafts:true,applying_one_preserves_other_drafts:true,reviewed_arguments_match_drafts:true,newer_edits_during_apply_preserved:true,keyboard_selection_and_option_nodes_survive_poll:true,valid_selections_survive_poll:true,removed_selections_remain_explicitly_invalid:true,explicit_reselection_required:true,transport:'real disposable Controller via test Cockpit bridge',list_projection:'test-only image/package status lists; no adapter mutation',physical_hardware:false},null,2)+'\n');
 console.log('Browser draft and selection tests PASS');
}finally{socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);}
