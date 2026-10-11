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
const child=spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-background-networking','--disable-component-update','--disable-sync','--disable-default-apps','--disable-quic','--disable-gpu-shader-disk-cache','--proxy-server=http://127.0.0.1:9','--proxy-bypass-list=127.0.0.1;localhost','--no-first-run','--disk-cache-size=1','--media-cache-size=1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{detached:true,stdio:['ignore',log,log]});
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

 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:url+'/cockpit/@localhost/sv08-host/index.html'});
 await until(`window.sv08Session?.available && document.querySelector('#printer-notice').textContent.startsWith('Saved configuration loaded.')`);
 const snapshot=fs.readFileSync(statepath);
 assert.equal(await evaluate('sv08Session.elevated'),false);
 assert.equal(await evaluate('window.fixtureStarts'),0);
 const navigate=async route=>{await evaluate(`sv08Navigation.go(${JSON.stringify(route)})`);await until(`!document.querySelector('#${route}').hidden`);};
 await navigate('printer');
 assert.match(await evaluate(`document.querySelector('#printer-draft-state').textContent`),/Saved draft/);
 assert.match(await evaluate(`document.querySelector('#printer-candidate-state').textContent`),/inactive candidate.*Setup/);
 assert.match(await evaluate(`document.querySelector('#printer-application-state').textContent`),/Not checked.*unknown/);
 assert.match(await evaluate(`document.querySelector('#printer-access-state').textContent`),/Administrator access/);
 assert.equal(await evaluate(`document.querySelector('#printer-save').closest('details')`),null);
 await screenshot('hardware-overview-state');
 await click('#printer-attention summary');
 const viewCalls=await evaluate('fixtureRequests.length');
 await evaluate(`document.querySelector('[data-attention-category="boards"]').focus()`);await key('Enter');
 assert.equal(await evaluate(`document.activeElement.id`),'printer-detail-title');
 assert.match(await evaluate(`document.querySelector('#printer-selected-definitions').textContent`),/Selected in draft.*Mainboard MCU identity/s);
 assert.equal(await evaluate(`Array.from(document.querySelectorAll('#printer-selected-definitions input, #printer-selected-definitions select, #printer-selected-definitions button')).every(e=>e.disabled)`),true);
 assert.equal(await evaluate(`document.querySelector('#printer-selected-definitions').compareDocumentPosition(document.querySelector('#printer-definition-choices')) & Node.DOCUMENT_POSITION_FOLLOWING`),4);
 assert.equal(await evaluate('fixtureRequests.length'),viewCalls);
 for(const [width,height] of [[1440,900],[1024,600],[390,844]]){
  await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
  await screenshot('hardware-attention-view-'+width);
 }
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await click('[data-category="bed"]');
 assert.match(await evaluate(`document.querySelector('#printer-detail-title').textContent`),/Bed/);
 assert.equal(await evaluate(`document.querySelector('#printer-save').disabled`),true);
 assert.equal(await evaluate(`document.querySelector('#printer-devices input').disabled`),true);
 await click('[data-printer-view="changes"]');
 assert.match(await evaluate(`document.querySelector('#printer-saved-current').textContent`),/Current saved/);
 assert.match(await evaluate(`document.querySelector('#printer-saved-previous').textContent`),/Previous saved/);
 await screenshot('hardware-view');
 await navigate('definitions');await click('[data-definition-group="builtin"]');
 await click('[data-definition-id="sv08.factory"]');
 assert.match(await evaluate(`document.querySelector('#printer-definitions-content').textContent`),/complete factory hardware/);
 assert.equal(await evaluate(`Array.from(document.querySelectorAll('#printer-definitions-content button')).find(b=>b.textContent==='Use this definition in hardware').disabled`),true);
 await screenshot('definitions-view');
 await navigate('definition-sources');
 assert.match(await evaluate(`document.querySelector('#printer-source-list').textContent`),/Fixture definitions/);
 assert.equal(await evaluate(`document.querySelector('#printer-source-list button').disabled`),true);
 await navigate('printer-connections');
 await until(`document.querySelector('#printer-connection-table tbody')?.children.length>0`);
 await evaluate(`document.querySelector('#printer-connection-filter').value='bed';document.querySelector('#printer-connection-filter').dispatchEvent(new Event('input'));`);
 assert.match(await evaluate(`document.querySelector('#printer-connection-table').textContent`),/bed/i);
 await screenshot('connections-view');
 for(const route of ['images','settings','network','software','mainsail-access','identity','recovery']) {
  await navigate(route);
  if(route==='network'){
   await until(`document.querySelector('#network-status').textContent==='Network settings are ready.'`);
   assert.match(await evaluate(`document.querySelector('#network-devices').textContent`),/192\.0\.2\.2/);
   assert.equal(await evaluate(`document.querySelector('#network-device').disabled`),false);
   assert.equal(await evaluate(`document.querySelector('#network-connection').disabled`),false);
   assert.equal(await evaluate(`document.querySelector('#network-apply').disabled`),true);
   await set('#network-connection','wired');
  } else if(route==='software'){
   await until(`document.querySelector('#software-status').textContent==='Software is ready.'`);
   assert.match(await evaluate(`document.querySelector('#software-detail').textContent`),/Installed/);
   assert.equal(await evaluate(`document.querySelector('#software-choice').disabled`),false);
   assert.equal(await evaluate(`document.querySelector('#software-remove').disabled`),true);
   await set('#software-choice','vnstat');
  } else if(route==='identity'){
   await until(`document.querySelector('#identity-status').textContent==='Printer identity is ready.'`);
   assert.equal(await evaluate(`document.querySelector('#identity-ca-fingerprint').textContent`),'public-ca');
   assert.equal(await evaluate(`document.querySelector('#identity-keys').readOnly`),true);
   assert.equal(await evaluate(`document.querySelector('#identity-export').disabled`),true);
  } else if(route==='mainsail-access'){
   await until(`document.querySelector('#access-status').textContent==='Mainsail access settings are ready.'`);
   assert.equal(await evaluate(`document.querySelector('#access-current').textContent`),'Password');
   assert.match(await evaluate(`document.querySelector('#access-certificates').textContent`),/Owner browser/);
   assert.equal(await evaluate(`document.querySelector('#access-apply').disabled`),true);
   assert.equal(await evaluate(`document.querySelector('#access-create').disabled`),true);
  } else if(route==='settings') {
   assert.equal(await evaluate(`document.querySelector('[name=mode]:checked').value`),'immutable');
   assert.equal(await evaluate(`document.querySelector('#save-mode').disabled`),true);
  } else if(route==='images') {
   assert.equal(await evaluate(`document.querySelector('#auto-update').checked`),false);
   assert.equal(await evaluate(`document.querySelector('#save-auto').disabled`),true);
   assert.match(await evaluate(`document.querySelector('#stage-reason').textContent`),/Administrator access/);
   await evaluate(`(()=>{const original=state.capabilities['image.stage'];try{state.capabilities['image.stage']={available:false,reason:'Fixture staging is unavailable.'};capability('image.stage','stage-image','stage-reason');}finally{window.fixtureOriginalStageCapability=original;}})()`);
   assert.match(await evaluate(`document.querySelector('#stage-reason').textContent`),/Fixture staging is unavailable\..*Administrator access/);
   assert.equal(await evaluate(`document.querySelector('#stage-image').disabled`),true);
   await evaluate(`state.capabilities['image.stage']=window.fixtureOriginalStageCapability;delete window.fixtureOriginalStageCapability;capability('image.stage','stage-image','stage-reason');`);
   assert.equal(await evaluate(`document.querySelector('#stage-image').disabled`),true);
  }
  await screenshot(route+'-view');
 }
 // RP1–11: every remaining route stays usable and non-mutating in ordinary view.
 for(const route of ['overview','images','settings','software','identity','mainsail-access','recovery','definitions','definition-sources','printer-connections']) {
  await navigate(route);assert.equal(await evaluate(`document.activeElement.closest('.page')?.id`),route);
  if(route==='images')assert.equal(await evaluate(`document.querySelector('#image-history').closest('.page').id`),'images');
  if(route==='settings')assert.match(await evaluate(`document.querySelector('#settings-current-mode').textContent`),/Immutable/);
  if(route==='recovery')assert.equal(await evaluate(`document.querySelector('#recovery .card h2').textContent`),'Recovery boot entry is not enabled here');
  for(const [width,height] of [[1440,900],[1024,600],[390,844]]){await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true,route+' at '+width);}
  // Equivalent to browser 200% at 1024×600: halve CSS viewport, retain physical pixels. CSS body zoom does not change media queries.
  await send('Emulation.setDeviceMetricsOverride',{width:512,height:300,deviceScaleFactor:2,mobile:false});assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true,route+' at equivalent 200%');
 }
 assert.equal(await evaluate('window.fixtureStarts'),0);
 // Elevation ends without deleting readable views, while reviews/secrets expire.
 await navigate('network');await until(`document.querySelector('#network-status').textContent==='Network settings are ready.'`);
 await click('#authorize');await until('sv08Session.elevated');
 await evaluate(`document.querySelector('#network-password').value='private-test-value';`);
 await click('#stop-authorization');await until(`!sv08Session.elevated && document.querySelector('#network-status').textContent==='Network settings are ready.'`);
 assert.equal(await evaluate(`document.querySelector('#network-password').value`),'');
 assert.equal(await evaluate(`document.querySelector('#network-connection').disabled`),false);
 assert.equal(await evaluate(`document.querySelector('#network-apply').disabled`),true);
 await send('Emulation.setDeviceMetricsOverride',{width:480,height:800,deviceScaleFactor:1,mobile:true});
 await screenshot('network-mobile-view');
 assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
 assert.deepEqual(fs.readFileSync(statepath),snapshot);
 assert.equal(errors.length,0);
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,ordinary_read_without_start:true,hardware_journey_read_only_state_attention:true,populated_hardware:true,saved_previous_view:true,definitions_sources_connections:true,remaining_pages_read_only_heading_focus_reflow_zoom:true,settings:['images','settings','network','software','mainsail-access','identity','recovery'],writes_disabled:true,end_access_retains_view:true,secrets_cleared:true,unchanged_state:true,uncaught_exceptions:0,physical_hardware:false},null,2)+'\n');
 console.log('Configuration view browser tests PASS');
} finally {socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);}
