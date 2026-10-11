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
 const until=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await delay(100);}throw new Error('Timeout: '+expression+' '+await evaluate(`JSON.stringify({notice:document.getElementById('notice').textContent,modeDisabled:document.getElementById('save-mode').disabled,cap:state?.capabilities['policy.mode'],busy,jobsBusy,refreshing})`));};
 const click=async selector=>{await until(`document.querySelector(${JSON.stringify(selector)}) && !document.querySelector(${JSON.stringify(selector)}).disabled`);return evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);};
 const key=async key=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:{Tab:9,Enter:13,Escape:27,ArrowDown:40,ArrowUp:38}[key],text:key==='Enter'?'\r':undefined});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});};
 const screenshot=async name=>{const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(r.data,'base64'));};
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url});await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 const edit=async (id,value)=>evaluate(`(()=>{const input=document.querySelector(${JSON.stringify(id)});input.value=${JSON.stringify(value)};input.dispatchEvent(new Event('input',{bubbles:true}));})()`);
 const fresh=async()=>{await until('!refreshing');await evaluate('refresh()');};
 const controls=()=>evaluate(`({mode:document.querySelector('[name=mode]:checked').value,auto:document.querySelector('#auto-update').checked})`);
 const external=(action,args)=>evaluate(`(async()=>{const plan=await request({method:'plan',action:${JSON.stringify(action)},arguments:${JSON.stringify(args)}});await request({method:'apply',plan});while(refreshing)await new Promise(resolve=>setTimeout(resolve,50));await refresh();})()`);
 await external('policy.mode',{mode:'writable'});assert.equal((await controls()).mode,'writable');
 await click('[data-page="settings"]');await click('[name="mode"][value="immutable"]');
 await click('[data-page="images"]');await click('#auto-update');
 const before=await controls();await fresh();const after=await controls();assert.deepEqual(after,before);
 await external('policy.mode',{mode:'immutable'});assert.deepEqual(await controls(),before);
 await click('[data-page="settings"]');await click('#save-mode');await until(`document.querySelector('#review').open`);assert.equal(await evaluate('plan.arguments.mode'),before.mode);await key('Escape');await fresh();assert.deepEqual(await controls(),before);
 // A server revision change rejects a reviewed mutation without discarding its draft.
 await click('#save-mode');await until(`document.querySelector('#review').open`);
 await external('policy.auto',{enabled:!(await evaluate('state.auto_update'))});await click('#confirm');await until(`!busy && document.querySelector('#notice').textContent.includes('state changed')`);assert.deepEqual(await controls(),before);
 await click('#save-mode');await until(`document.querySelector('#review').open`);await click('#confirm');await until(`!busy && document.querySelector('#notice').textContent.startsWith('Saved.')`);assert.deepEqual(await controls(),before);
 // Applied mode is now clean; the separate automatic-update draft is retained.
 await external('policy.mode',{mode:'writable'});assert.equal((await controls()).mode,'writable');assert.equal((await controls()).auto,before.auto);
 await click('[data-page="images"]');await click('#save-auto');await until(`document.querySelector('#review').open`);assert.equal(await evaluate('plan.arguments.enabled'),before.auto);await click('#confirm');await until(`!busy && document.querySelector('#notice').textContent.startsWith('Saved.')`);
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/state/state.json')).auto_update,before.auto);
 // A newer edit made while the save acknowledgment is in flight stays dirty.
 await click('[data-page="settings"]');await click('[name="mode"][value="immutable"]');
 await evaluate(`(()=>{const original=cockpit.spawn;let hold=true;cockpit.spawn=(...args)=>{const process=original(...args);return {input:async data=>{const raw=await process.input(data);if(hold && JSON.parse(data).method==='apply'){hold=false;await new Promise(resolve=>{window.releaseApplyAck=resolve;});}return raw;}};};})()`);
 await click('#save-mode');await until(`document.querySelector('#review').open`);await click('#confirm');await until(`typeof window.releaseApplyAck==='function'`);await click('[name="mode"][value="writable"]');await evaluate('window.releaseApplyAck()');await until('!busy');await fresh();assert.equal((await controls()).mode,'writable');assert.equal(await evaluate('state.requested_mode'),'immutable');
 // Test-only uploaded-image projection exercises native select preservation.
 await evaluate(`(()=>{window.fixtureImages=[{id:'a'.repeat(64),label:'First image'},{id:'b'.repeat(64),label:'Second image'}];const original=cockpit.spawn;cockpit.spawn=(...args)=>{const process=original(...args);return {input:async data=>{const raw=await process.input(data);const result=JSON.parse(raw);if(JSON.parse(data).method==='status' && result.ok){result.result.images=window.fixtureImages;result.result.capabilities['image.stage']={available:true,reason:''};}return JSON.stringify(result);}};};})()`);
 await click('[data-page="images"]');await fresh();await until(`Array.from(document.querySelector('#image-choice').options).filter(o=>o.value).length===2`);
 await evaluate(`(()=>{const select=document.querySelector('#image-choice');select.value='a'.repeat(64);select.dispatchEvent(new Event('change',{bubbles:true}));select.focus();window.retainedOption=select.options[1];})()`);await key('ArrowDown');await fresh();
 assert.equal(await evaluate(`document.querySelector('#image-choice')===document.activeElement`),true);assert.equal(await evaluate(`document.querySelector('#image-choice').options[1]===window.retainedOption`),true);assert.equal(await evaluate(`document.querySelector('#image-choice').value`),'b'.repeat(64));
 await evaluate(`window.fixtureImages=window.fixtureImages.slice(0,1);refresh()`);await until(`document.querySelector('#image-choice').value===''`);assert.match(await evaluate(`document.querySelector('#image-choice').selectedOptions[0].textContent`),/Previous selection is unavailable/);assert.equal(await evaluate(`document.querySelector('#stage-image').disabled`),true);
 await fresh();assert.equal(await evaluate(`document.querySelector('#image-choice').value`),'');
 await evaluate(`document.querySelector('#image-choice').value='a'.repeat(64);document.querySelector('#image-choice').dispatchEvent(new Event('change',{bubbles:true}));`);await fresh();assert.equal(await evaluate(`document.querySelector('#stage-image').disabled`),false);
 assert.equal(errors.length,0);
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,before,after,external_changes_preserve_drafts:true,untouched_controls_follow_server:true,cancel_and_stale_review_preserve_drafts:true,applying_one_preserves_other_drafts:true,reviewed_arguments_match_drafts:true,newer_edits_during_apply_preserved:true,keyboard_selection_and_option_nodes_survive_poll:true,removed_selections_remain_explicitly_invalid:true,transport:'real disposable Controller; image-list projection only',physical_hardware:false},null,2)+'\n');
 console.log('Browser draft and selection tests PASS');
}finally{socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);}
