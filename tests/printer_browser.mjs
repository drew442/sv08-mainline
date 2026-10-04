// Actual Chromium + real generation-local Python Store. Cockpit session/RPC shim.
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';
const [chrome,fixture,output]=process.argv.slice(2);
const {url}=JSON.parse(fs.readFileSync(fixture+'/server.json'));
assert.match(url,/^http:\/\/127\.0\.0\.1:\d+$/);
fs.mkdirSync(output);const profile=fs.mkdtempSync((process.env.SV08_BROWSER_PROFILE_ROOT??output)+'/profile-');fs.chmodSync(profile,0o700);const log=fs.openSync(output+'/browser.log','w');
const child=spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-background-networking','--disable-component-update','--disable-sync','--disable-default-apps','--disable-quic','--proxy-server=http://127.0.0.1:9','--proxy-bypass-list=127.0.0.1;localhost','--no-first-run','--disk-cache-size=1','--media-cache-size=1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{detached:true,stdio:['ignore',log,log]});
let socket,secondSocket,secondTarget;
try {
 let port;
 for(let i=0;i<100;i++){try{port=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];break;}catch{await delay(100);}}
 assert(port);const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let dirtyReloadDialogs=0;let id=0;const pending=new Map(),errors=[];
 function send(method,params={}){return new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>reject(Error('CDP timeout '+method)),10000);pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params}));});}
 socket.onmessage=({data})=>{const e=JSON.parse(data);if(e.id){const p=pending.get(e.id);if(p){clearTimeout(p.timer);pending.delete(e.id);e.error?p.reject(e.error):p.resolve(e.result);}}if(e.method==='Page.javascriptDialogOpening'){assert.equal(e.params.type,'beforeunload');dirtyReloadDialogs++;void send('Page.handleJavaScriptDialog',{accept:true});}if(e.method==='Runtime.exceptionThrown')errors.push(e.params);};
 await send('Runtime.enable');await send('Page.enable');
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const until=async expression=>{for(let i=0;i<100;i++){try{if(await evaluate(expression))return;}catch(error){if(error.code!==-32000 || !/navigated|context/i.test(error.message))throw error;}await delay(100);}throw Error('Timeout: '+expression+' '+await evaluate(`JSON.stringify({notice:document.querySelector('#printer-notice')?.textContent,session:document.querySelector('#session-status')?.textContent})`));};
 const click=async selector=>{if(selector==='#authorize')await until(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);return evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);};
 const set=async(selector,value)=>evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw Error('Missing field');e.value=${JSON.stringify(String(value))};e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 const key=async key=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:{Tab:9,Enter:13,Escape:27}[key],text:key==='Enter'?'\r':undefined});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});};
 let statepath=JSON.parse(fs.readFileSync(fixture+'/fixture.json')).state;
 const state=()=>JSON.parse(fs.readFileSync(statepath));
 const screenshot=async name=>{await evaluate('scrollTo(0,0)');const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(r.data,'base64'));};
 const ready=()=>until(`document.querySelector('#printer-boards fieldset') && !document.querySelector('#printer-save').disabled && !document.querySelector('#printer-candidate-review').open`);
 const reloadDocument=async()=>{const origin=await evaluate('performance.timeOrigin');await send('Page.reload');await until(`performance.timeOrigin!==${origin} && window.sv08Session?.available===true && document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);};
 const reload=async()=>{await click('#printer-reload');if(await evaluate("!document.querySelector('#printer-reconciliation').hidden")){await send('Page.handleJavaScriptDialog',{accept:true}).catch(()=>{});await click('#printer-reconcile');}await ready();};
 await send('Emulation.setDeviceMetricsOverride',{width:1024,height:600,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:url+'/cockpit/@localhost/sv08-host/index.html'});await until(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);
 await evaluate('window.documentIdentity=document; window.sessionIdentity=sv08Session');
 // Elevation starts background status at Overview; route changes must not lose it.
 const initialBytes=fs.existsSync(statepath)?fs.readFileSync(statepath):null;
 for(const from of ['overview','printer']) {
  await click('[data-page='+from+']');await evaluate('window.fixtureHoldStatus=true');
  await click('#authorize');await until('window.fixtureStatusWaiting');
  await click('[data-page='+(from==='overview'?'printer':'overview')+']');
  await evaluate('window.fixtureReleaseStatus()');await ready();
  assert.equal(await evaluate(`document.querySelector('#printer-reconciliation').hidden`),true);
  assert.match(await evaluate(`document.querySelector('#printer-notice').textContent`),/Saved configuration loaded/);
  assert.deepEqual(await evaluate('window.fixtureRequests.map(r=>r.request.action)'),['status']);
  assert.equal(await evaluate('document===window.documentIdentity && sv08Session===window.sessionIdentity'),true);
  if(initialBytes)assert.deepEqual(fs.readFileSync(statepath),initialBytes);else assert.equal(fs.existsSync(statepath),false);
  if(from==='overview') {
   await reloadDocument();
   await evaluate('window.documentIdentity=document; window.sessionIdentity=sv08Session');
  }
 }
 // Stop/logout/disconnect invalidate delayed status even if authority is later restored.
 for(const transition of ['stop','logout','disconnect']) {
  await reloadDocument();
  await evaluate('window.fixtureHoldStatus=true');await click('#authorize');await until('window.fixtureStatusWaiting');
  if(transition==='stop')await click('#stop-authorization');else if(transition==='logout')await click('#logout');else await evaluate('window.fixtureDisconnect()');
  await until('!sv08Session.elevated');
  if(transition==='stop'){await until(`!document.querySelector('#authorize').disabled`);await click('#authorize');await until('sv08Session.elevated');}
  await evaluate('window.fixtureReleaseStatus()');
  await until(`document.querySelector('#printer-notice').textContent.includes('Session or selections changed')`);
  assert.equal(await evaluate(`document.querySelectorAll('#printer-boards fieldset').length`),0);
  assert.deepEqual(await evaluate('window.fixtureRequests.map(r=>r.request.action)'),['status']);
 }
 await reloadDocument();
 await evaluate('window.documentIdentity=document; window.sessionIdentity=sv08Session');
 await click('[data-page=printer]');await click('#authorize');await ready();
 assert.equal(await evaluate('new Set([...document.querySelectorAll("[id]")].map(e=>e.id)).size===document.querySelectorAll("[id]").length'),true);
 assert.match(await evaluate('location.pathname'),/sv08-host\/index.html$/);
 // Shared document/history and editable host values survive route changes.
 await set('#hostname','retained-host-draft');
 await click('[data-page=settings]');await click('[data-page=printer]');
 await evaluate('history.back()');await until(`location.hash==='#settings'`);
 await evaluate('history.forward()');await until(`location.hash==='#printer'`);
 assert.equal(await evaluate(`document.querySelector('#hostname').value`),'retained-host-draft');
 assert.equal(await evaluate('document===window.documentIdentity && sv08Session===window.sessionIdentity'),true);
 assert.equal(await evaluate(`document.querySelector('[data-host-status]').hidden`),true);
 await evaluate('window.fixtureHostFailure=true; refresh()');await until(`document.querySelector('#connection').textContent==='Host unavailable'`);assert.equal(await evaluate(`document.querySelector('#printer-save').disabled`),false);
 // Host upload review opens on successful plan, navigation invalidates late plans.
 await evaluate('window.fixtureHostFailure=false; refresh()');await click('[data-page=images]');await evaluate('uploadListing()');
 await evaluate(`(()=>{const dt=new DataTransfer();dt.items.add(new File(['fixture'],'fixture.raucb'));document.querySelector('#bundle-file').files=dt.files;})()`);
 await click('#review-upload');await until(`document.querySelector('#upload-review').open`);
 await click('[data-page=printer]');assert.equal(await evaluate(`document.querySelector('#upload-review').open`),false);
 await click('[data-page=images]');await evaluate('window.fixtureHostHold="upload.plan"');await click('#review-upload');await until('window.fixtureHostWaiting');
 await click('[data-page=printer]');await evaluate('window.fixtureHostRelease()');await until('!window.fixtureHostWaiting');
 assert.equal(await evaluate(`document.querySelector('#upload-review').open`),false);
 assert.equal(await evaluate(`document.querySelector('#bundle-file').files[0].name`),'fixture.raucb');
 await click('[data-page=settings]');await evaluate('window.fixtureHostHold="plan"');await click('#save-hostname');await until('window.fixtureHostWaiting');
 await click('[data-page=printer]');await evaluate('window.fixtureHostRelease()');await until('!window.fixtureHostWaiting');assert.equal(await evaluate(`document.querySelector('#review').open`),false);
 await evaluate(`document.querySelector('.skip').click()`);assert.equal(await evaluate('location.hash'),'#printer');assert.equal(await evaluate('document.activeElement.id'),'main');
 // Select board and incomplete device through native forms, without JSON editor.
 await set('#printer-boards fieldset:nth-child(1) select','sv08-main');await click('#printer-confirm-board');
 const boardField=(text)=>`(()=>{const box=document.querySelector('#printer-boards fieldset');return [...box.querySelectorAll('label')].find(e=>e.firstChild.textContent===${JSON.stringify(text)}).querySelector('input,select');})()`;
 const fieldSet=async(expr,value)=>evaluate(`(()=>{const e=${expr};e.value=${JSON.stringify(String(value))};e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 await fieldSet(boardField('Transport'),'serial');await fieldSet(boardField('Private MCU identity'),'/dev/null');await fieldSet(boardField('Use this reference provisionally'),'true');
 await set('#printer-device-preset','bed_sensor');
 assert.match(await evaluate(`document.querySelector('#printer-preset-preview').textContent`),/PC5/);
 assert.match(await evaluate(`document.querySelector('#printer-preset-preview').textContent`),/physically measured/);
 await click('#printer-add-preset');await until(`document.querySelector('#printer-devices fieldset') && !document.querySelector('#printer-save').disabled`);
 await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);assert.equal(state().draft.devices[0].settings.pin,'PC5');
 await reloadDocument();await click('#authorize');await ready();assert.equal(state().draft.devices[0].name,'bed_sensor');
 const deviceField=text=>`(()=>{const box=document.querySelector('#printer-devices fieldset');return [...box.querySelectorAll('label')].find(e=>e.firstChild.textContent===${JSON.stringify(text)}).querySelector('input,select');})()`;
 await fieldSet(deviceField('max temp'),105);
 await click('[data-page=overview]');await click('[data-page=printer]');
 assert.equal(await evaluate(`(()=>{const b=document.querySelector('#printer-devices fieldset');return [...b.querySelectorAll('label')].find(e=>e.firstChild.textContent==='max temp').querySelector('input').value;})()`),'105');

 assert.equal(await evaluate(`document.querySelector('#printer-review').disabled`),true);
 await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);assert.equal(state().draft.devices[0].settings.pullup_resistor,4700);
 assert.match(await evaluate(`document.querySelector('#printer-devices').textContent`),/PC5/);
 await send('Emulation.setTouchEmulationEnabled',{enabled:true});
 await evaluate(`document.querySelector('#printer-reload').scrollIntoView()`);
 const touch=await evaluate(`(()=>{const r=document.querySelector('#printer-reload').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
 await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[touch]});await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await ready();
 await send('Emulation.setTouchEmulationEnabled',{enabled:false});
 await screenshot('sensor-1024x600');assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
 // Default focus and real Escape cancellation; no state publication.
 let before=state().revision;await click('#printer-review');await until(`document.querySelector('#printer-candidate-review').open`);
 assert.equal(await evaluate(`document.activeElement.id`),'printer-cancel-review');await key('Escape');assert.equal(state().revision,before);
 await click('#printer-review');await until(`document.querySelector('#printer-candidate-review').open`);await click('#printer-apply');await until(`document.querySelector('#printer-notice').textContent.includes('commissioning handoff') && !document.querySelector('#printer-save').disabled`);assert.equal(state().current.mode,'sensors');assert.match(state().current.text,/\[temperature_sensor bed_sensor\]/);
 // A pending printer review response cannot reopen a dialog after navigation.
 before=state().revision;await evaluate('window.fixtureHoldReview=true');await click('#printer-review');await until('window.fixtureReviewWaiting');
 await click('[data-page=overview]');await evaluate('window.fixtureReleaseReview()');await until(`document.querySelector('#printer-notice').textContent.includes('Session or selections changed') && !document.querySelector('#printer-reconcile').disabled`);
 assert.equal(await evaluate(`document.querySelector('#printer-candidate-review').open`),false);assert.equal(state().revision,before);
 await click('[data-page=printer]');await click('#printer-reconcile');await ready();
 await click('#printer-review');await until(`document.querySelector('#printer-candidate-review').open`);await click('[data-page=settings]');assert.equal(await evaluate(`document.querySelector('#printer-candidate-review').open`),false);await click('[data-page=printer]');
 // A stale read-only response cannot overwrite retained edits after Stop/re-authorize.
 await set('#printer-geometry-fields input',123);await click('#printer-reload');
 await evaluate('window.fixtureHoldStatus=true');await click('#printer-reconcile');await until('window.fixtureStatusWaiting');
 await click('#stop-authorization');await until('!sv08Session.elevated');
 await until(`!document.querySelector('#authorize').disabled`);await click('#authorize');await until('sv08Session.elevated');await evaluate('window.fixtureReleaseStatus()');
 await until(`document.querySelector('#printer-notice').textContent.includes('Session or selections changed') && !document.querySelector('#printer-reconcile').disabled`);
 assert.equal(await evaluate(`document.querySelector('#printer-geometry-fields input').value`),'123');
 await evaluate('window.fixtureHoldStatus=true');await click('#printer-reconcile');await until('window.fixtureStatusWaiting');
 await click('[data-page=overview]');await evaluate('window.fixtureReleaseStatus()');await ready();await click('[data-page=printer]');
 assert.equal(await evaluate(`document.querySelector('#printer-geometry-fields input').value`),'123');
 assert.equal(await evaluate(`document.querySelector('#printer-reconciliation').hidden`),true);
 // Board change cancel preserves settings; confirmation clears only affected assignments.
 // Actual Chromium: dirty selections survive unsupported status reconciliation.
 await send('Page.setDownloadBehavior',{behavior:'allow',downloadPath:output+'/recovery'});
 for(const unsupported of ['catalog','state','draft']) {
  await set('#printer-geometry-fields input',123);
  await click('#stop-authorization');await until('!sv08Session.elevated');
  await evaluate('window.fixtureUnsupported='+JSON.stringify(unsupported));
  await click('#authorize');await until(`!document.querySelector('#printer-reconcile').disabled`);
  const requestCount=await evaluate('window.fixtureRequests.length');
  await click('#printer-reconcile');await until(`document.querySelector('#printer-notice').textContent.includes('Unsupported stored') && !document.querySelector('#printer-reconcile').disabled`);
  for(const id of ['save','review','restore','add','add-preset','apply','import'])assert.equal(await evaluate(`document.querySelector('#printer-${id}').disabled`),true);
  assert.equal(await evaluate(`document.querySelector('#printer-geometry-fields input').disabled`),true);
  const requests=await evaluate('window.fixtureRequests.slice('+requestCount+')');assert.deepEqual(requests.map(r=>r.request.action),['status']);
  await click('#printer-export');
  const recovery=output+'/recovery/printer-hardware-draft.json';
  for(let n=0;n<100&&!fs.existsSync(recovery);n++)await delay(50);
  const recovered=JSON.parse(fs.readFileSync(recovery));assert.equal(recovered.geometry.max_velocity,123);assert.equal(recovered.format_version,1);fs.renameSync(recovery,output+'/recovery/'+unsupported+'-draft.json');
  await evaluate('window.fixtureUnsupported=null');await click('#printer-reconcile');await ready();
  assert.equal(await evaluate(`document.querySelector('#printer-geometry-fields input').value`),'123');
 }
 // Explicit choice alone discards the retained local draft.
 await click('#printer-reload');await until(`!document.querySelector('#printer-reconciliation').hidden`);
 await evaluate('window.confirm=()=>true');await click('#printer-discard');await ready();
 assert.equal(await evaluate(`document.querySelector('#printer-geometry-fields input').value`),String(state().draft.geometry.max_velocity??''));
 await set('#printer-boards fieldset:nth-child(1) select','octopus-v1.1-non-pro');await key('Escape');assert.equal(await evaluate(`document.querySelector('#printer-boards select').value`),'sv08-main');
 // Import explicit before/after comparison and cancellation. Private data stays in-memory.
 const imported=structuredClone(state().draft);imported.devices[0].settings.max_temp=100;
 const injectFile=async d=>evaluate(`(()=>{const dt=new DataTransfer();dt.items.add(new File([${JSON.stringify(JSON.stringify(d))}],'draft.json',{type:'application/json'}));const e=document.querySelector('#printer-import');e.files=dt.files;e.dispatchEvent(new Event('change'));})()`);
 // Real tab B loads A's revision, edits its native form and saves independently.
 const staleA=structuredClone(state().draft),revisionA=state().revision;
 await injectFile(staleA);await until(`!document.querySelector('#printer-import-diff').hidden && !document.querySelector('#printer-save').disabled`);assert.match(await evaluate(`document.querySelector('#printer-import-diff').textContent`),/No changes/); // prior valid comparison must disappear on stale refusal
 secondTarget=await(await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url+'/cockpit/@localhost/sv08-printer/index.html')}`,{method:'PUT'})).json();
 secondSocket=new WebSocket(secondTarget.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{secondSocket.onopen=resolve;secondSocket.onerror=reject;});
 let bid=0;const bpending=new Map();
 const sendB=(method,params={})=>new Promise((resolve,reject)=>{const id=++bid;bpending.set(id,{resolve,reject});secondSocket.send(JSON.stringify({id,method,params}));});
 secondSocket.onmessage=({data})=>{const r=JSON.parse(data);if(r.id){const p=bpending.get(r.id);bpending.delete(r.id);r.error?p.reject(r.error):p.resolve(r.result);}};
 const evalB=async expression=>{const r=await sendB('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const untilB=async expression=>{for(let i=0;i<100;i++){if(await evalB(expression))return;await delay(100);}throw Error('Tab B timeout '+expression);};
 await untilB(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await evalB(`document.querySelector('#authorize').click()`);await untilB(`document.querySelector('#printer-devices fieldset') && !document.querySelector('#printer-save').disabled`);
 await evalB(`(()=>{const e=[...document.querySelector('#printer-devices fieldset').querySelectorAll('label')].find(e=>e.firstChild.textContent==='max temp').querySelector('input');e.value=100;e.dispatchEvent(new Event('change'));document.querySelector('#printer-save').click();})()`);
 await untilB(`document.querySelector('#printer-notice').textContent==='Draft saved'`);assert.equal(state().draft.devices[0].settings.max_temp,100);assert.equal(state().revision,revisionA+1);
 await injectFile(staleA);await until(`document.querySelector('#printer-notice').textContent.includes('refresh before importing') && !document.querySelector('#printer-save').disabled`);
 assert.equal(await evaluate(`document.querySelector('#printer-import-diff').hidden`),true);assert.equal(state().revision,revisionA+1);assert.equal(state().draft.devices[0].settings.max_temp,100);
 await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent.includes('refresh before saving')`);assert.equal(state().revision,revisionA+1);
 await reload();await injectFile(staleA);await until(`!document.querySelector('#printer-import-diff').hidden && !document.querySelector('#printer-save').disabled`);
 assert.match(await evaluate(`document.querySelector('#printer-import-diff').textContent`),/100/);assert.match(await evaluate(`document.querySelector('#printer-import-diff').textContent`),/105/);assert.doesNotMatch(await evaluate(`document.querySelector('#printer-import-diff').textContent`),/No changes/);
 await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);assert.equal(state().draft.devices[0].settings.max_temp,105);secondSocket.close();secondSocket=null;
 await fetch(`http://127.0.0.1:${port}/json/close/${secondTarget.id}`);secondTarget=null;
 await injectFile(imported);await until(`!document.querySelector('#printer-import-diff').hidden && !document.querySelector('#printer-save').disabled`);
 assert.match(await evaluate(`document.querySelector('#printer-import-diff').textContent`),/max temp/);assert.match(await evaluate(`document.querySelector('#printer-import-diff').textContent`),/105/);assert.match(await evaluate(`document.querySelector('#printer-import-diff').textContent`),/100/);
 assert.equal(state().draft.devices[0].settings.max_temp,105);await click('#printer-cancel-import');assert.equal(state().draft.devices[0].settings.max_temp,105);
 await injectFile(imported);await until(`!document.querySelector('#printer-import-diff').hidden && !document.querySelector('#printer-save').disabled`);await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);
 await click('#printer-review');await until(`document.querySelector('#printer-candidate-review').open`);await click('#printer-apply');await until(`document.querySelector('#printer-notice').textContent.includes('commissioning handoff') && !document.querySelector('#printer-save').disabled`);assert.equal(state().previous.draft.devices[0].settings.max_temp,105);
 await click('#printer-restore');await until(`document.querySelector('#printer-notice').textContent.includes('Previous candidate draft restored') && !document.querySelector('#printer-save').disabled`);assert.equal(state().draft.devices[0].settings.max_temp,105);
 await click('#printer-review');await until(`document.querySelector('#printer-candidate-review').open`);
 await evaluate('window.fixtureHoldApply=true');await click('#printer-apply');await until('window.fixtureApplyWaiting');
 const ackRevision=state().revision;await fieldSet(deviceField('max temp'),103);
 await click('[data-page=overview]');await click('#stop-authorization');await until('!sv08Session.elevated');
 await evaluate('window.fixtureReleaseApply()');await until(`document.querySelector('#printer-notice').textContent.includes('acknowledged')`);
 await until(`!document.querySelector('#authorize').disabled`);await click('#authorize');await until('sv08Session.elevated');await click('[data-page=printer]');
 await until(`!document.querySelector('#printer-reconciliation').hidden && !document.querySelector('#printer-reconcile').disabled`);
 assert.equal(await evaluate(`document.querySelector('#printer-save').disabled`),true);await click('#printer-reconcile');await ready();
 assert.equal(state().revision,ackRevision);
 assert.equal(await evaluate(`(()=>{const b=document.querySelector('#printer-devices fieldset');return [...b.querySelectorAll('label')].find(e=>e.firstChild.textContent==='max temp').querySelector('input').value;})()`),'103');
 await fieldSet(deviceField('max temp'),105);
 await reload();assert.equal(state().revision,ackRevision); // reconciliation never blindly retries
 await send('Page.setDownloadBehavior',{behavior:'allow',downloadPath:output});await click('#printer-export');await click('#printer-export-config');
 for(let i=0;i<100 && (!fs.existsSync(output+'/printer-hardware-draft.json')||!fs.existsSync(output+'/inactive-candidate.cfg'));i++)await delay(100);
 assert.equal(JSON.parse(fs.readFileSync(output+'/printer-hardware-draft.json')).devices[0].settings.max_temp,105);assert.match(fs.readFileSync(output+'/inactive-candidate.cfg','utf8'),/kinematics: none/);
 // Friendly X motor / TMC2209 defaults require no raw section-name entry.
 await set('#printer-device-preset','stepper_x');assert.match(await evaluate(`document.querySelector('#printer-device-preset').selectedOptions[0].textContent`),/X axis motor/);
 await click('#printer-add-preset');await until(`document.querySelectorAll('#printer-devices fieldset').length===2 && !document.querySelector('#printer-save').disabled`);
 await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);const motor=state().draft.devices.find(d=>d.kind==='motor');
 assert.equal(motor.name,'stepper_x');assert.equal(motor.settings.microsteps,16);assert.equal(motor.settings.rotation_distance,40);assert.equal(motor.settings.uart_address,3);assert.equal(motor.settings.run_current,1.5);assert.equal(motor.settings.current_rating_rms,undefined);
 before=state().revision;await click('#printer-add-preset');await until(`document.querySelector('#printer-notice').textContent.includes('unique') && !document.querySelector('#printer-save').disabled`);assert.equal(state().revision,before);assert.equal(state().draft.devices.length,2);
 await set('#printer-mode','full');await click('#printer-review');await until(`document.querySelector('#printer-candidate-review').open`);assert.match(await evaluate(`document.querySelector('#printer-review-detail').textContent`),/current_rating_rms/);assert.equal(await evaluate(`document.querySelector('#printer-apply').disabled`),true);await click('#printer-cancel-review');
 await click('#printer-devices fieldset:nth-child(2) button');await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);await set('#printer-mode','sensors');
 // Actual Store copies identical revision into B while this native tab holds A.
 const loadedRevision=state().revision,originalPath=statepath,originalBytes=fs.readFileSync(statepath);
 const swapped=await(await fetch(url+'/swap-generation',{method:'POST',body:'{}'})).json();assert(swapped.ok);statepath=swapped.result.state;
 assert.equal(state().revision,loadedRevision);assert.deepEqual(fs.readFileSync(statepath),originalBytes);
 const staleBytes=fs.readFileSync(statepath);
 await click('#printer-review');await until(`document.querySelector('#printer-notice').textContent.includes('context is stale') && !document.querySelector('#printer-save').disabled`);assert.equal(await evaluate(`document.querySelector('#printer-candidate-review').open`),false);
 await click('#printer-restore');await until(`document.querySelector('#printer-notice').textContent.includes('context is stale') && !document.querySelector('#printer-save').disabled`);
 await injectFile(state().draft);await until(`document.querySelector('#printer-notice').textContent.includes('context is stale') && !document.querySelector('#printer-save').disabled`);assert.equal(await evaluate(`document.querySelector('#printer-import-diff').hidden`),true);
 await set('#printer-device-preset','stepper_x');await click('#printer-add-preset');await until(`document.querySelector('#printer-notice').textContent.includes('context is stale') && !document.querySelector('#printer-save').disabled`);
 await fieldSet(deviceField('max temp'),99);await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent.includes('context is stale') && !document.querySelector('#printer-save').disabled`);
 assert.deepEqual(fs.readFileSync(statepath),staleBytes);assert.deepEqual(fs.readFileSync(originalPath),originalBytes);
 await reload();await fieldSet(deviceField('max temp'),104);await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);assert.equal(state().draft.devices[0].settings.max_temp,104);
 await click('#printer-review');await until(`document.querySelector('#printer-candidate-review').open`);await click('#printer-apply');await until(`document.querySelector('#printer-notice').textContent.includes('commissioning handoff') && !document.querySelector('#printer-save').disabled`);assert.equal(state().current.draft.devices[0].settings.max_temp,104);
 const lineageCalls=[];
 for(const transition of ['logout','disconnect']) {
  await click('#printer-review');await until(`document.querySelector('#printer-candidate-review').open`);
  await evaluate('window.fixtureHoldApply=true');await click('#printer-apply');await until('window.fixtureApplyWaiting');
  const submittedRevision=state().revision;await fieldSet(deviceField('max temp'),102);await click('[data-page=overview]');
  if(transition==='logout')await click('#logout');else await evaluate('window.fixtureDisconnect()');
  await until('!sv08Session.available');await evaluate('window.fixtureReleaseApply()');await until(`document.querySelector('#printer-reconcile').disabled && document.querySelector('#printer-notice').textContent.includes('acknowledged')`);
  await click('[data-page=printer]');assert.equal(await evaluate(`(()=>{const b=document.querySelector('#printer-devices fieldset');return [...b.querySelectorAll('label')].find(e=>e.firstChild.textContent==='max temp').querySelector('input').value;})()`),'102');
  assert.equal(await evaluate(`document.querySelector('#printer-save').disabled`),true);assert.equal(state().revision,submittedRevision);
  lineageCalls.push(...await evaluate('window.fixtureRequests'));await send('Page.reload');
  await until(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await click('#authorize');await ready();
  assert.equal(state().revision,submittedRevision);
 }
 const calls=[...lineageCalls,...await evaluate('window.fixtureRequests')];
 assert(calls.filter(c=>c.request.action!=='status').length>0);
 for(const c of calls)if(c.request.action!=='status'){assert.equal(typeof c.loaded,'string');assert.equal(c.request.expected_identity,c.loaded);}
 // Authority loss cancels review, and backend refuses direct mutations too.
 await click('#printer-review');await until(`document.querySelector('#printer-candidate-review').open`);await click('#stop-authorization');await until(`!document.querySelector('#printer-candidate-review').open && document.querySelector('#printer-save').disabled`);
 before=state().revision;
 const deniedIdentity=await evaluate('window.fixtureLoadedIdentity');
 const denied=await(await fetch(url+'/request',{method:'POST',body:JSON.stringify({action:'save',expected_revision:before,expected_identity:deniedIdentity,draft:state().draft})})).json();assert.equal(denied.ok,false);assert.equal(state().revision,before);
 await click('#authorize');if(await evaluate("!document.querySelector('#printer-reconciliation').hidden"))await click('#printer-reconcile');await ready();
 await set('#printer-boards fieldset:nth-child(1) select','octopus-v1.1-non-pro');await click('#printer-confirm-board');await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);assert.equal(state().draft.devices.length,0);assert.equal(state().draft.boards.main.identity,undefined);assert(state().current);
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});await screenshot('boards-desktop');assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await screenshot('boards-narrow');assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
 const legacyOrigin=await evaluate('performance.timeOrigin');await send('Page.navigate',{url:url+'/cockpit/@localhost/sv08-printer/index.html'});await until(`performance.timeOrigin!==${legacyOrigin} && document.querySelector('#authorize') && !document.querySelector('#authorize').disabled && location.pathname.endsWith('/sv08-host/index.html') && location.hash==='#printer' && document.querySelector('#printer') && !document.querySelector('#printer').hidden`);
 const beforeReloadOrigin=await evaluate('performance.timeOrigin');await send('Page.reload');await until(`performance.timeOrigin!==${beforeReloadOrigin} && location.hash==='#printer' && document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await click('#authorize');await ready();
 await evaluate(`document.querySelector('#printer-save').focus()`);await key('Tab');assert.equal(await evaluate(`document.activeElement.id`),'printer-review');
 await evaluate('window.fixtureDisconnect()');await until(`document.querySelector('#printer-save').disabled`);assert.match(await evaluate(`document.querySelector('#session-status').textContent`),/disconnected/);
 await reloadDocument();await click('#authorize');await ready();await click('#logout');await until(`document.body.dataset.loggedOut==='true'`);assert.equal(await evaluate(`document.querySelector('#printer-save').disabled`),true);
 const generation=JSON.parse(fs.readFileSync(fixture+'/fixture.json')).generation;
 assert.equal(fs.readFileSync(generation+'/config/printer.cfg','utf8'),fs.readFileSync(fixture+'/original-live.txt','utf8'));
 assert.equal(await evaluate(`localStorage.length`),0);assert.equal(errors.length,0,JSON.stringify(errors));
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,authenticated:false,hardware:false,transport:'Cockpit session/RPC shim; actual Store/Budget',viewport_sizes:[[1024,600],[1440,900],[390,844]],unsupported_status_draft_export_recovery:true,shared_panel:true,initial_status_navigation:true,stale_status_authority_rejected:true,printer_review_late_response_ignored:true,host_refresh_failure_isolation:true,incomplete_save_reopen:true,connector_pin_form:true,factory_default:true,sensor_reference_journey:true,motor_reference_journey:true,preset_collision_refused:true,two_real_tab_stale_import_refused:true,generation_swap_refused:true,last_status_identity_carried:true,refresh_generation_edit_apply:true,refresh_exact_import_diff:true,keyboard_escape:true,touch_reload:true,import_diff_cancel_save:true,review_cancel_apply:true,previous_restore:true,lost_ack_reconciled:true,lost_ack_stop_logout_disconnect:true,upload_review_navigation_cancelled:true,host_review_late_response_ignored:true,legacy_deeplink_reload:true,skip_retains_route:true,board_change_clears:true,stop_disconnect_logout:true,live_config_unchanged:true,uncaught_exceptions:errors.length},null,2)+'\n');
 console.log('Printer browser fixture journeys PASS');
} finally {secondSocket?.close();socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);await delay(300);const bytes=path=>fs.readdirSync(path,{withFileTypes:true}).reduce((n,e)=>n+(e.isDirectory()?bytes(path+'/'+e.name):e.isFile()?fs.statSync(path+'/'+e.name).size:0),0);const profileBytes=bytes(profile);fs.writeFileSync(output+'/profile-usage.json',JSON.stringify({profile,bytes:profileBytes}));fs.rmSync(profile,{recursive:true,force:true});assert(profileBytes<24*1024*1024);}
