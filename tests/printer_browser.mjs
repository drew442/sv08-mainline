// Actual Chromium + real generation-local Python Store. Cockpit session/RPC shim.
import fs from 'node:fs';
import {spawn,execFileSync} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
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
 const until=async expression=>{for(let i=0;i<100;i++){try{if(await evaluate(expression))return;}catch(error){if(error.code!==-32000 || !/navigated|context/i.test(error.message))throw error;}await delay(100);}throw Error('Timeout: '+expression+' '+await evaluate(`JSON.stringify({notice:document.querySelector('#printer-notice')?.textContent,session:document.querySelector('#session-status')?.textContent,actions:window.fixtureRequests?.slice(-6).map(r=>r.request.action)})`));};
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
 // Catalogue browsing is read-only, with compact groups and component drill-down.
 const definitionsState=fs.existsSync(statepath)?fs.readFileSync(statepath):null;
 const browseRequests=await evaluate('fixtureRequests.length');await click('[data-page=definitions]');
 await until(`document.querySelector('[data-definition-group="builtin"]')`);
 assert.equal(await evaluate('location.hash'),'#definitions');assert.equal(await evaluate(`document.querySelector('#printer').hidden`),true);
 assert.equal(await evaluate(`document.querySelector('[data-page=definitions]').getAttribute('aria-current')`),'page');
 assert.equal(await evaluate(`!!document.querySelector('#printer-definitions-content dl')`),false);
 await click('[data-definition-group="builtin"]');await until(`document.querySelectorAll('#printer-definitions-content [data-definition-id]').length===25`);
 await click('[data-definition-id="sv08.factory"]');assert.match(await evaluate(`document.querySelector('#printer-definitions-content h2').textContent`),/complete factory/);
 await click('[data-definition-dependency="sv08-main.bed_assembly"]');await click('[data-definition-component="bed_sensor"]');
 assert.match(await evaluate(`document.querySelector('#printer-definitions-content').textContent`),/4700|sovol-bed/);assert.match(await evaluate(`document.querySelector('#printer-definitions-content').textContent`),/Contact|Unknown|sensor_pin/i);
 await click('#printer-definitions-back');assert.match(await evaluate(`document.querySelector('#printer-definitions-content h2').textContent`),/Bed heater/);
 await click('#printer-definitions-back');assert.match(await evaluate(`document.querySelector('#printer-definitions-content h2').textContent`),/complete factory/);
 assert.equal(await evaluate(`document.querySelectorAll('#printer-definitions-content details[open]').length`),0);
 await click('#printer-definitions-by-category');assert(await evaluate(`document.querySelectorAll('[data-definition-group]').length>1`));await click('[data-definition-group="bed"]');
 assert(await evaluate(`document.querySelectorAll('#printer-definitions-content [data-definition-id]').length>0`));assert.equal(await evaluate(`!!document.querySelector('#printer-definitions-content dl')`),false);
 await evaluate(`document.querySelector('#printer-definitions-search').value='no-such-definition';document.querySelector('#printer-definitions-search').dispatchEvent(new Event('input'))`);assert.match(await evaluate(`document.querySelector('#printer-definitions-content').textContent`),/No matching/);
 await evaluate(`document.querySelector('#printer-definitions-search').value='';document.querySelector('#printer-definitions-search').dispatchEvent(new Event('input'))`);await click('#printer-definitions-by-source');
 await evaluate(`document.querySelector('[data-definition-group="builtin"]').focus()`);await key('Enter');await until(`!!document.querySelector('[data-definition-id="sv08.factory"]')`);
 await evaluate(`document.querySelector('[data-definition-id="sv08.factory"]').focus()`);await key('Enter');assert.match(await evaluate(`document.querySelector('#printer-definitions-content h2').textContent`),/complete factory/);
 await evaluate('window.fixtureHostFailure=true;refresh()');await until(`document.querySelector('#connection').textContent==='Host unavailable'`);assert.equal(await evaluate(`document.querySelector('#printer-definitions-back').disabled`),false);await evaluate('window.fixtureHostFailure=false;refresh()');
 for(const [width,height] of [[1440,900],[1024,600],[390,844]]){await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);await screenshot('definitions-detail-'+width);}
 assert.equal(await evaluate('fixtureRequests.length'),browseRequests);
 if(definitionsState)assert.deepEqual(fs.readFileSync(statepath),definitionsState);else assert.equal(fs.existsSync(statepath),false);
 await evaluate('history.back()');await until(`location.hash==='#printer'`);await evaluate('history.forward()');await until(`location.hash==='#definitions'`);
 await reloadDocument();await click('#authorize');await ready();assert.equal(await evaluate('location.hash'),'#definitions');await until(`document.querySelector('[data-definition-group="builtin"]')`);await evaluate('window.documentIdentity=document;window.sessionIdentity=sv08Session');
 await click('[data-page=printer]');await send('Emulation.setDeviceMetricsOverride',{width:1024,height:600,deviceScaleFactor:1,mobile:false});

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
 await set('#printer-boards fieldset:nth-child(1) select','sv08-main');await click('#printer-confirm-board');await until(`!document.querySelector('#printer-board-change').open && !document.querySelector('#printer-save').disabled`);
 const boardField=(text)=>`(()=>{const box=document.querySelector('#printer-boards fieldset');return [...box.querySelectorAll('label')].find(e=>e.firstChild.textContent===${JSON.stringify(text)}).querySelector('input,select');})()`;
 const fieldSet=async(expr,value)=>evaluate(`(()=>{const e=${expr};e.value=${JSON.stringify(String(value))};e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 await click('#printer-boards fieldset:first-child > details > summary');
 await fieldSet(boardField('Transport'),'serial');assert.equal(await evaluate(`document.querySelector('#printer-boards details[data-role=main]').open`),true);await fieldSet(boardField('Private MCU identity'),'/dev/null');await fieldSet(boardField('Use this reference provisionally'),'true');
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

 assert.equal(await evaluate(`document.querySelector('#printer-review').disabled`),false); // Review remains accessible for incomplete local edits.
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
 await click('#printer-advanced-toggle');await set('#printer-boards fieldset:nth-child(1) select','octopus-v1.1-non-pro');await until(`document.querySelector('#printer-board-change').open && document.querySelector('#printer-board-change p').textContent.includes('bed_sensor Needs connection')`);await key('Escape');await until(`!document.querySelector('#printer-board-change').open && !document.querySelector('#printer-save').disabled`);assert.equal(await evaluate(`document.querySelector('#printer-boards select').value`),'sv08-main');
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
 await evaluate('window.fixtureReleaseApply()');await until(`document.querySelector('#printer-notice').textContent.includes('reconcile')`);
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
  await until('!sv08Session.available');await evaluate('window.fixtureReleaseApply()');await until(`document.querySelector('#printer-reconcile').disabled && document.querySelector('#printer-notice').textContent.includes('reconcile')`);
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
 await click('#printer-advanced-toggle');await set('#printer-boards fieldset:nth-child(1) select','octopus-v1.1-non-pro');await click('#printer-confirm-board');await until(`!document.querySelector('#printer-board-change').open && !document.querySelector('#printer-save').disabled`);await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);assert.equal(state().draft.devices.length,1);assert.equal(state().draft.devices[0].settings.pin,undefined);assert.equal(state().draft.boards.main.identity,undefined);assert(state().current);
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});await screenshot('boards-desktop');assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await screenshot('boards-narrow');assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
 const legacyOrigin=await evaluate('performance.timeOrigin');await send('Page.navigate',{url:url+'/cockpit/@localhost/sv08-printer/index.html'});await until(`performance.timeOrigin!==${legacyOrigin} && document.querySelector('#authorize') && !document.querySelector('#authorize').disabled && location.pathname.endsWith('/sv08-host/index.html') && location.hash==='#printer' && document.querySelector('#printer') && !document.querySelector('#printer').hidden`);
 const beforeReloadOrigin=await evaluate('performance.timeOrigin');await send('Page.reload');await until(`performance.timeOrigin!==${beforeReloadOrigin} && location.hash==='#printer' && document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await click('#authorize');await ready();
 await click('[data-printer-view=changes]');await evaluate(`document.querySelector('#printer-save').focus()`);await key('Tab');assert.equal(await evaluate(`document.activeElement.id`),'printer-show-changes');
 await click('[data-printer-view=components]');await click('[data-category=boards]');
 // Everyday hardware choices do not require entering pins or calibration.
 await set('#printer-boards fieldset:nth-child(1) select','sv08-main');await click('#printer-confirm-board');await until(`!document.querySelector('#printer-board-change').open && !document.querySelector('#printer-save').disabled`);
 await set('#printer-boards fieldset:nth-child(2) select','sv08-tool');await click('#printer-confirm-board');await until(`!document.querySelector('#printer-board-change').open && !document.querySelector('#printer-save').disabled`);
 await set('[data-component=bed][data-board=main]','bed_assembly');await until(`document.querySelector('[data-sensor=bed_sensor]') && !document.querySelector('#printer-save').disabled`);
 await click('[data-component=exhaust_fan][data-board=main]');await until(`document.querySelector('[data-component=exhaust_fan]').checked && !document.querySelector('#printer-save').disabled`);
 await set('[data-component=extruder][data-board=tool]','hotend_assembly');await until(`document.querySelector('[data-sensor=hotend_sensor]') && !document.querySelector('#printer-save').disabled`);
 await set('[data-sensor=hotend_sensor]','pt1000');await set('[data-sensor=bed_sensor]','generic3950');
 assert.equal(await evaluate(`document.querySelector('#printer-advanced').open`),false);
 await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);
 const simple=state().draft;
 assert.equal(simple.devices.find(d=>d.name==='hotend_sensor').settings.pullup_resistor,11500);
 assert.equal(simple.devices.find(d=>d.name==='bed_sensor').settings.pullup_resistor,4700);
 assert.equal(simple.devices.find(d=>d.name==='heater_bed').settings.pid_kp,undefined);
 assert.equal(await evaluate(`document.querySelector('[data-component=bed]').value`),'bed_assembly');
 assert.equal(simple.devices.find(d=>d.name==='extruder').settings.pid_kp,undefined);
 assert.equal(simple.devices.find(d=>d.name==='bed_sensor').settings.max_temp,105);
 assert(simple.devices.some(d=>d.name==='exhaust_fan'));
 await screenshot('simple-hardware');
 await reloadDocument();await click('#authorize');await ready();
 assert.equal(await evaluate(`document.querySelector('[data-sensor=hotend_sensor]').value`),'pt1000');
 await click('[data-component=exhaust_fan][data-board=main]');await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);
 assert(!state().draft.devices.some(d=>d.name==='exhaust_fan'));
 assert(state().draft.devices.some(d=>d.name==='extruder'));
 // Factory choices, shared definition selection and explicit source lifecycle.
 assert.equal(await evaluate(`!!document.querySelector('[data-component=chamber_module]')`),false);
 assert.equal(await evaluate(`!!document.querySelector('[data-component=bed] option[value=funssor_cn3d_bed]')`),false);
 await click('[data-printer-view=components]');await click('[data-category=bed]');
 await set('#printer-definition-search','does not exist');await evaluate(`document.querySelector('#printer-definition-search').dispatchEvent(new Event('input',{bubbles:true}))`);assert.match(await evaluate(`document.querySelector('#printer-definition-choices').textContent`),/No matching/);
 await set('#printer-definition-search','Bed heater');await evaluate(`document.querySelector('#printer-definition-search').dispatchEvent(new Event('input',{bubbles:true}))`);await click('#printer-definition-choices .printer-choice');await until(`document.querySelector('#printer-definition-review').open`);
 const priorRevision=state().revision;await click('#printer-definition-cancel');assert.equal(state().revision,priorRevision);
 await click('#printer-definition-choices .printer-choice');await until(`document.querySelector('#printer-definition-review').open`);await click('#printer-definition-confirm');
 await click('[data-printer-view=changes]');assert.match(await evaluate(`document.querySelector('#printer-semantic-changes').textContent`),/Bed|heated bed/i);
 await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);
 assert(state().draft.definition_plan.selections.some(r=>r.id==='sv08-main.bed_assembly'));
 await click('[data-page=printer-connections]');await click('#printer-table-toggle');assert.match(await evaluate(`document.querySelector('#printer-connection-table').textContent`),/PC5/);await screenshot('connections');
 await click('[data-page=definition-sources]');assert.match(await evaluate(`document.querySelector('#printer-source-list').textContent`),/Built-in/);
 assert.equal(await evaluate(`location.hash`),'#definition-sources');assert.equal(await evaluate(`document.querySelector('#printer').hidden`),true);assert.equal(await evaluate(`document.querySelector('#definition-sources').hidden`),false);
 assert.equal(await evaluate(`document.querySelector('[data-page=definition-sources]').getAttribute('aria-current')`),'page');
 await evaluate('history.back()');await until(`location.hash==='#printer-connections'`);await evaluate('history.forward()');await until(`location.hash==='#definition-sources'`);
 await send('Page.reload');await until(`window.sv08Session?.available && !document.querySelector('#authorize').disabled`);await click('#authorize');await ready();assert.equal(await evaluate(`location.hash`),'#definition-sources');assert.equal(await evaluate(`document.querySelector('#definition-sources').hidden`),false);
 const starterState=state(),starterRequests=await evaluate('window.fixtureRequests.length');
 execFileSync('python3',['scripts/definition_repository_template.py',output+'/expected-starter.zip']);
 await click('#printer-source-template');
 for(let i=0;i<100 && !fs.existsSync(output+'/definition-repository-starter.zip');i++)await delay(100);
 assert.deepEqual(fs.readFileSync(output+'/definition-repository-starter.zip'),fs.readFileSync(output+'/expected-starter.zip'));
 execFileSync('python3',['scripts/definition_repository_template.py','--schemas',output+'/expected-schemas.zip']);
 await click('#printer-source-schema');
 for(let i=0;i<100 && !fs.existsSync(output+'/definition-schema-reference.zip');i++)await delay(100);
 assert.deepEqual(fs.readFileSync(output+'/definition-schema-reference.zip'),fs.readFileSync(output+'/expected-schemas.zip'));
 assert.deepEqual(state(),starterState);assert.equal(await evaluate('window.fixtureRequests.length'),starterRequests);
 await set('#printer-source-url','https://github.com/fixture/bad-mode');await click('#printer-source-preview');
 await until(`document.querySelector('#printer-source-notice').textContent.includes('git update-index --chmod=-x catalog.json') && !document.querySelector('#printer-source-preview').disabled`);
 assert.equal(await evaluate(`document.querySelector('#printer-source-preview-detail').textContent`),'');
 await set('#printer-source-url','https://github.com/fixture/compact-mods');await click('#printer-source-preview');
 await until(`document.querySelector('#printer-source-preview-detail').textContent.includes('1 supported') && !document.querySelector('#printer-source-preview').disabled`);
 assert.match(await evaluate(`document.querySelector('#printer-source-preview-detail').textContent`),/Funssor CN3D heated bed/);assert.deepEqual(state(),starterState);
 await click('#printer-source-confirm');await until(`document.querySelector('#printer-source-list').textContent.includes('Compact modder fixture') && !document.querySelector('#printer-save').disabled`);
 await click('[data-page=printer]');await click('[data-category=bed]');await set('#printer-definition-filter','github:18:.');
 await click('#printer-definition-choices .printer-choice');await until(`document.querySelector('#printer-definition-review').open`);await click('#printer-definition-confirm');
 await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);
 assert.equal(state().draft.devices.find(d=>d.name==='bed_sensor').settings.max_temp,120);assert.equal(state().draft.devices.filter(d=>d.name==='heater_bed').length,1);
 await click('[data-page=definition-sources]');await evaluate(`[...document.querySelectorAll('#printer-source-list button')].find(b=>b.textContent==='Remove').click()`);await until(`!document.querySelector('#printer-source-list').textContent.includes('Compact modder fixture') && !document.querySelector('#printer-save').disabled`);
 assert(state().draft.definition_plan.selections.some(r=>r.id==='funssor-cn3d-hotbed'));assert.equal(state().draft.devices.find(d=>d.name==='bed_sensor').settings.max_temp,120);
 const beforeRichImport=JSON.stringify(state().draft);
 const example=JSON.parse(fs.readFileSync('examples/printer-definitions/catalog.json'));
 const bundle={manifest:example,files:Object.fromEntries(example.definitions.map(r=>[r.path,fs.readFileSync('examples/printer-definitions/'+r.path).toString('base64')]))};
 const future=Buffer.from(JSON.stringify({format_version:'9.0',id:'future-entry',version:'1.0.0'}));example.definitions.push({id:'future-entry',version:'1.0.0',path:'definitions/future.json',sha256:createHash('sha256').update(future).digest('hex')});bundle.files['definitions/future.json']=future.toString('base64');
 const bundlePath=output+'/creator-bundle.json';fs.writeFileSync(bundlePath,JSON.stringify(bundle));
 const doc=await send('DOM.getDocument');const node=await send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'#printer-source-import'});
 await send('DOM.setFileInputFiles',{nodeId:node.nodeId,files:[bundlePath]});await until(`document.querySelector('#printer-source-preview-detail').textContent.includes('SV08 creator starter') && !document.querySelector('#printer-save').disabled`);
 assert.equal(Object.keys(state().sources??{}).length,0);await click('#printer-source-confirm');await until(`Object.keys(window.fixtureRequests.at(-1).request).includes('action') && document.querySelector('#printer-source-list').textContent.includes('SV08 creator starter') && !document.querySelector('#printer-save').disabled`);
 assert.equal(Object.keys(state().sources).length,1);assert.equal(JSON.stringify(state().draft),beforeRichImport);
 const externalSource=Object.keys(state().sources)[0];
 const beforeCatalogue=JSON.stringify(state().draft),beforeCatalogueRequests=await evaluate('fixtureRequests.length');
 await click('[data-page=definitions]');await click('#printer-definitions-by-source');await click(`[data-definition-group="${externalSource}"]`);
 assert.equal(await evaluate(`document.querySelectorAll('#printer-definitions-content [data-definition-id]').length`),5);
 await click('[data-definition-id="sv08-bed-bundle"]');await click('[data-definition-dependency="sv08-bed"]');await click('[data-definition-component="bed_sensor"]');assert.match(await evaluate(`document.querySelector('#printer-definitions-content').textContent`),/4700/);
 await click('#printer-definitions-by-category');await click('[data-definition-group="unavailable"]');await click('[data-definition-id="future-entry"]');assert.match(await evaluate(`document.querySelector('#printer-definitions-content').textContent`),/Unsupported|supported component/);
 assert.equal(await evaluate('fixtureRequests.length'),beforeCatalogueRequests);assert.equal(JSON.stringify(state().draft),beforeCatalogue);
 await click('[data-page=printer]');await click('[data-category=bed]');await set('#printer-definition-filter',externalSource);await set('#printer-definition-search','Bed heater');await evaluate(`document.querySelector('#printer-definition-search').dispatchEvent(new Event('input',{bubbles:true}))`);
 await click('#printer-definition-choices .printer-choice');await until(`document.querySelector('#printer-definition-review').open`);await click('#printer-definition-confirm');await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);
 assert(state().draft.definition_plan.selections.some(r=>r.source===externalSource));await click('[data-page=definition-sources]');
 await evaluate(`[...document.querySelectorAll('#printer-source-list button')].find(b=>b.textContent==='Disable').click()`);await until(`document.querySelector('#printer-source-list').textContent.includes('Disabled') && !document.querySelector('#printer-save').disabled`);
 await click('[data-page=definitions]');await click('#printer-definitions-by-source');await click(`[data-definition-group="${externalSource}"]`);assert.match(await evaluate(`document.querySelector('#printer-definitions-content').textContent`),/Source disabled/);
 await click('[data-definition-id="sv08-bed"]');await click('[data-definition-component="bed_sensor"]');assert.match(await evaluate(`document.querySelector('#printer-definitions-content').textContent`),/4700/);
 await click('[data-page=definition-sources]');
 await evaluate(`[...document.querySelectorAll('#printer-source-list button')].find(b=>b.textContent==='Remove').click()`);await until(`!document.querySelector('#printer-source-list').textContent.includes('SV08 creator starter') && !document.querySelector('#printer-save').disabled`);
 await click('[data-page=definitions]');await click('#printer-definitions-by-source');assert.equal(await evaluate(`document.querySelectorAll('[data-definition-group]').length`),1);
 assert.equal(Object.keys(state().sources).length,0);assert(state().draft.definition_plan.snapshots['builtin::sv08-main.bed_assembly@0.2.0']);assert(state().draft.definition_plan.selections.some(r=>r.source===externalSource));
 await click('[data-page=printer]');
 const factoryRevision=state().revision;await click('#printer-use-factory');await until(`document.querySelector('#printer-definition-review').open`);assert.match(await evaluate(`document.querySelector('#printer-definition-effects').textContent`),/24|adxl345/);await click('#printer-definition-cancel');assert.equal(state().revision,factoryRevision);
 await click('#printer-use-factory');await until(`document.querySelector('#printer-definition-review').open`);await click('#printer-definition-confirm');await click('#printer-save');await until(`document.querySelector('#printer-notice').textContent==='Draft saved' && !document.querySelector('#printer-save').disabled`);
 assert.equal(state().draft.devices.length,24);assert(state().draft.definition_plan.selections.some(r=>r.id==='sv08.factory'));assert.equal(state().draft.devices.find(d=>d.name==='probe').settings.z_offset,undefined);
 await reloadDocument();await click('#authorize');await ready();assert.equal(state().draft.devices.length,24);await screenshot('factory-components');
 // Full factory graph, independent route and event-driven interaction acceptance.
 const graphSaved=JSON.stringify(state().draft);await click('[data-page=printer-connections]');
 await until(`document.querySelectorAll('.printer-graph-node').length===27`);
 assert.equal(await evaluate(`location.hash`),'#printer-connections');assert.equal(await evaluate(`document.querySelector('#printer').hidden`),true);
 assert.equal(await evaluate(`!!document.querySelector('[data-printer-view=connections]')`),false);
 const expectedPins=state().draft.devices.reduce((count,d)=>count+Object.keys(d.settings).filter(f=>['pin','connector','endstop_pin','tachometer_pin','cs_pin','a0_pin','rst_pin','encoder_a','encoder_b','click_pin','miso_pin','mosi_pin','sclk_pin'].includes(f)).length,0);
 const wireCount=await evaluate(`document.querySelectorAll('.printer-graph-wire:not(.reference):not(.internal):not(.transport)').length`);assert.equal(wireCount,expectedPins);
 assert.equal(await evaluate(`document.querySelectorAll('.printer-graph-wire.transport').length`),2);
 assert.equal(await evaluate(`document.querySelectorAll('.printer-graph-wire.internal').length`),2);
 for(const d of state().draft.devices)assert.equal(await evaluate(`!!document.querySelector('[data-node="device:${d.name}"]')`),true,d.name);
 for(const name of ['adxl345','display']){const d=state().draft.devices.find(d=>d.kind===(name==='adxl345'?'accelerometer':'display'));for(const field of ['cs_pin','miso_pin','mosi_pin','sclk_pin'])assert.equal(await evaluate(`document.querySelectorAll('.printer-graph-wire[data-connection="${d.name}:${field}"]').length`),1);}
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});await click('#printer-graph-fit');
 const beforeScale=await evaluate(`document.querySelector('#printer-graph-scale').textContent`);await click('#printer-graph-in');assert.notEqual(await evaluate(`document.querySelector('#printer-graph-scale').textContent`),beforeScale);
 await click('#printer-graph-out');await click('#printer-graph-fit');
 const mouse=async(type,x,y)=>send('Input.dispatchMouseEvent',{type,x,y,button:type==='mouseMoved'?'none':'left',buttons:type==='mouseReleased'?0:1,clickCount:1});
 const area=await evaluate(`(()=>{const r=document.querySelector('#printer-connection-map').getBoundingClientRect();return {x:r.left+8,y:r.top+8};})()`);
 const transform=await evaluate(`document.querySelector('#printer-graph-scene').style.transform`);await mouse('mousePressed',area.x,area.y);await mouse('mouseMoved',area.x+45,area.y+30);await mouse('mouseReleased',area.x+45,area.y+30);assert.notEqual(await evaluate(`document.querySelector('#printer-graph-scene').style.transform`),transform);
 await click('#printer-graph-fit');const heading=await evaluate(`(()=>{const e=document.querySelector('[data-node="host"] .printer-graph-heading'),r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2,left:e.parentElement.style.left};})()`);
 await mouse('mousePressed',heading.x,heading.y);await mouse('mouseMoved',heading.x+25,heading.y+20);await mouse('mouseReleased',heading.x+25,heading.y+20);assert.notEqual(await evaluate(`document.querySelector('[data-node="host"]').style.left`),heading.left);
 await click('#printer-graph-reset');assert.equal(await evaluate(`document.querySelector('[data-node="host"]').style.left`),'20px');
 await evaluate(`document.querySelector('#printer-connection-map').focus()`);const pan=await evaluate(`document.querySelector('#printer-graph-scene').style.transform`);await key('ArrowRight');assert.notEqual(await evaluate(`document.querySelector('#printer-graph-scene').style.transform`),pan);await key('0');
 await click('[data-connection="stepper_x:connector"].printer-graph-port');assert.match(await evaluate(`document.querySelector('#printer-connection-inspector').textContent`),/PE2|PE0/);assert(await evaluate(`document.querySelectorAll('.printer-graph-wire.selected').length>0`));
 // Filtering and table inspection do not submit requests or change the draft.
 await evaluate(`document.querySelector('#printer-connection-filter').value='adxl';document.querySelector('#printer-connection-filter').dispatchEvent(new Event('input'))`);assert.equal(await evaluate(`document.querySelectorAll('.printer-graph-wire:not(.reference)').length`),4);
 await click('#printer-table-toggle');assert.match(await evaluate(`document.querySelector('#printer-connection-table').textContent`),/PB12/);await click('#printer-connection-table button');assert.match(await evaluate(`document.querySelector('#printer-connection-inspector').textContent`),/adxl/i);
 await evaluate(`document.querySelector('#printer-connection-filter').value='no-match';document.querySelector('#printer-connection-filter').dispatchEvent(new Event('input'))`);assert.match(await evaluate(`document.querySelector('#printer-connection-table').textContent`),/No matching/);
 await evaluate(`document.querySelector('#printer-connection-filter').value='';document.querySelector('#printer-connection-filter').dispatchEvent(new Event('input'))`);await click('#printer-map-toggle');
 await evaluate(`window.graphMutations=0;window.graphObserver=new MutationObserver(m=>graphMutations+=m.length);graphObserver.observe(document.querySelector('#printer-connection-map'),{subtree:true,attributes:true,childList:true})`);
 const idleRequests=await evaluate('fixtureRequests.length');await send('Performance.enable');const cpuStart=(await send('Performance.getMetrics')).metrics.find(m=>m.name==='TaskDuration').value;await delay(2000);const cpuEnd=(await send('Performance.getMetrics')).metrics.find(m=>m.name==='TaskDuration').value;
 assert.equal(await evaluate('graphMutations'),0);assert.equal(await evaluate('fixtureRequests.length'),idleRequests);await evaluate('graphObserver.disconnect()');const graphIdleTaskSeconds=cpuEnd-cpuStart;await click('#printer-graph-reset');
 for(const [width,height] of [[1440,900],[1024,600],[390,844]]){await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);await screenshot('factory-graph-'+width);}
 assert.equal(JSON.stringify(state().draft),graphSaved);
 await evaluate('history.back()');await until(`location.hash==='#printer'`);await evaluate('history.forward()');await until(`location.hash==='#printer-connections'`);
 await reloadDocument();await click('#authorize');await ready();await until(`document.querySelectorAll('.printer-graph-node').length===27`);assert.equal(await evaluate(`location.hash`),'#printer-connections');assert.equal(JSON.stringify(state().draft),graphSaved);
 await click('#printer-table-toggle');await click('#printer-connection-table button');await click('#stop-authorization');assert.equal(await evaluate(`document.querySelector('#printer-connection-inspector select')?.disabled`),true);await click('#authorize');await ready();
 await click('[data-page=printer]');

 await send('Emulation.setDeviceMetricsOverride',{width:1024,height:600,deviceScaleFactor:1,mobile:false});await evaluate(`document.body.style.zoom='200%'`);await screenshot('components-200-percent');assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);await evaluate(`document.body.style.zoom=''`);
 await evaluate('window.fixtureDisconnect()');await until(`document.querySelector('#printer-save').disabled`);assert.match(await evaluate(`document.querySelector('#session-status').textContent`),/disconnected/);
 await reloadDocument();await click('#authorize');await ready();await click('#logout');await until(`document.body.dataset.loggedOut==='true'`);assert.equal(await evaluate(`document.querySelector('#printer-save').disabled`),true);
 const generation=JSON.parse(fs.readFileSync(fixture+'/fixture.json')).generation;
 assert.equal(fs.readFileSync(generation+'/config/printer.cfg','utf8'),fs.readFileSync(fixture+'/original-live.txt','utf8'));
 assert.equal(await evaluate(`localStorage.length`),0);assert.equal(errors.length,0,JSON.stringify(errors));
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,authenticated:false,hardware:false,transport:'Cockpit session/RPC shim; actual Store/Budget',viewport_sizes:[[1024,600],[1440,900],[390,844]],unsupported_status_draft_export_recovery:true,shared_panel:true,initial_status_navigation:true,stale_status_authority_rejected:true,printer_review_late_response_ignored:true,host_refresh_failure_isolation:true,incomplete_save_reopen:true,connector_pin_form:true,factory_default:true,simple_assembly_selectors:true,factory_only_choices:true,complete_factory_select_cancel_save_reload:true,definition_preview_cancel_select:true,source_bundle_disable_remove_preserves_selected_snapshot:true,definition_sources_sidebar_route_reload:true,schema_reference_download:true,repository_starter_download:true,repository_starter_static_no_rpc:true,compact_github_preview_selection_save_retention:true,source_executable_file_error_visible:true,definitions_sidebar_route_history_reload:true,definitions_source_category_grouping:true,definitions_builtin_external_disabled_unsupported:true,definitions_dependency_component_drilldown:true,definitions_read_only_no_rpc:true,definitions_search_empty_keyboard_responsive:true,logical_connection_table:true,blueprint_graph:true,connections_sidebar_history_reload:true,complete_factory_graph:true,graph_pan_zoom_drag_filter_highlight:true,graph_idle_dom_mutations:0,graph_idle_rpc_calls:0,graph_idle_task_seconds:graphIdleTaskSeconds,connection_inspector_authority_gated:true,external_selection_offline_retention:true,zoom_200_percent:true,one_click_enclosure_fan:true,ntc_ptc_defaults:true,hardware_save_before_pid:true,advanced_fields_collapsed:true,sensor_reference_journey:true,motor_reference_journey:true,preset_collision_refused:true,two_real_tab_stale_import_refused:true,generation_swap_refused:true,last_status_identity_carried:true,refresh_generation_edit_apply:true,refresh_exact_import_diff:true,keyboard_escape:true,touch_reload:true,import_diff_cancel_save:true,review_cancel_apply:true,previous_restore:true,lost_ack_reconciled:true,lost_ack_stop_logout_disconnect:true,upload_review_navigation_cancelled:true,host_review_late_response_ignored:true,legacy_deeplink_reload:true,skip_retains_route:true,board_remap_preserves_unresolved_devices:true,stop_disconnect_logout:true,live_config_unchanged:true,uncaught_exceptions:errors.length},null,2)+'\n');
 console.log('Printer browser fixture journeys PASS');
} finally {secondSocket?.close();socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);await delay(300);const bytes=path=>fs.readdirSync(path,{withFileTypes:true}).reduce((n,e)=>n+(e.isDirectory()?bytes(path+'/'+e.name):e.isFile()?fs.statSync(path+'/'+e.name).size:0),0);const profileBytes=bytes(profile);fs.writeFileSync(output+'/profile-usage.json',JSON.stringify({profile,bytes:profileBytes}));fs.rmSync(profile,{recursive:true,force:true});assert(profileBytes<24*1024*1024);}
