// Actual Chromium + real generation-local Python Store. Cockpit session/RPC shim.
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';
const [chrome,fixture,output]=process.argv.slice(2);
const {url}=JSON.parse(fs.readFileSync(fixture+'/server.json'));
assert.match(url,/^http:\/\/127\.0\.0\.1:\d+$/);
fs.mkdirSync(output);const profile=fs.mkdtempSync('/dev/shm/sv08-printer-repair-f2-');fs.chmodSync(profile,0o700);const log=fs.openSync(output+'/browser.log','w');
const child=spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking','--disable-component-update','--disable-sync','--disable-default-apps','--disable-quic','--proxy-server=http://127.0.0.1:9','--proxy-bypass-list=127.0.0.1;localhost','--no-first-run','--disk-cache-size=1','--media-cache-size=1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{detached:true,stdio:['ignore',log,log]});
let socket,secondSocket,secondTarget;
try {
 let port;
 for(let i=0;i<100;i++){try{port=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];break;}catch{await delay(100);}}
 assert(port);const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let id=0;const pending=new Map(),errors=[];
 function send(method,params={}){return new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>reject(Error('CDP timeout '+method)),10000);pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params}));});}
 socket.onmessage=({data})=>{const e=JSON.parse(data);if(e.id){const p=pending.get(e.id);if(p){clearTimeout(p.timer);pending.delete(e.id);e.error?p.reject(e.error):p.resolve(e.result);}}if(e.method==='Runtime.exceptionThrown')errors.push(e.params);};
 await send('Runtime.enable');await send('Page.enable');
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const until=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await delay(100);}throw Error('Timeout: '+expression);};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const set=async(selector,value)=>evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw Error('Missing field');e.value=${JSON.stringify(String(value))};e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 const key=async key=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:{Tab:9,Enter:13,Escape:27}[key],text:key==='Enter'?'\r':undefined});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});};
 let statepath=JSON.parse(fs.readFileSync(fixture+'/fixture.json')).state;
 const state=()=>JSON.parse(fs.readFileSync(statepath));
 const screenshot=async name=>{const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(r.data,'base64'));};
 const ready=()=>until(`document.querySelector('#boards fieldset') && !document.querySelector('#save').disabled`);
 await send('Emulation.setDeviceMetricsOverride',{width:1024,height:600,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:url+'/cockpit/@localhost/sv08-host/index.html'});await until(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);
 await click('a[href="../sv08-printer/index.html"]');await until(`document.querySelector('h1')?.textContent==='Printer hardware'`);
 assert.match(await evaluate('location.pathname'),/sv08-printer\/index.html$/);
 await until(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await click('#authorize');await ready();
 // Select board and incomplete device through native forms, without JSON editor.
 await set('#boards fieldset:nth-child(1) select','sv08-main');await click('#confirm-board');
 const boardField=(text)=>`(()=>{const box=document.querySelector('#boards fieldset');return [...box.querySelectorAll('label')].find(e=>e.firstChild.textContent===${JSON.stringify(text)}).querySelector('input,select');})()`;
 const fieldSet=async(expr,value)=>evaluate(`(()=>{const e=${expr};e.value=${JSON.stringify(String(value))};e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 await fieldSet(boardField('Transport'),'serial');await fieldSet(boardField('Private MCU identity'),'/dev/null');await fieldSet(boardField('Use this reference provisionally'),'true');
 await set('#device-preset','bed_sensor');
 assert.match(await evaluate(`document.querySelector('#preset-preview').textContent`),/PC5/);
 assert.match(await evaluate(`document.querySelector('#preset-preview').textContent`),/physically measured/);
 await click('#add-preset');await until(`document.querySelector('#devices fieldset') && !document.querySelector('#save').disabled`);
 await click('#save');await ready();assert.equal(state().draft.devices[0].settings.pin,'PC5');
 await send('Page.reload');await until(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await click('#authorize');await ready();assert.equal(state().draft.devices[0].name,'bed_sensor');
 const deviceField=text=>`(()=>{const box=document.querySelector('#devices fieldset');return [...box.querySelectorAll('label')].find(e=>e.firstChild.textContent===${JSON.stringify(text)}).querySelector('input,select');})()`;
 await fieldSet(deviceField('max temp'),105);
 assert.equal(await evaluate(`document.querySelector('#review').disabled`),true);
 await click('#save');await ready();assert.equal(state().draft.devices[0].settings.pullup_resistor,4700);
 assert.match(await evaluate(`document.querySelector('#devices').textContent`),/PC5/);
 await send('Emulation.setTouchEmulationEnabled',{enabled:true});
 await evaluate(`document.querySelector('#reload').scrollIntoView()`);
 const touch=await evaluate(`(()=>{const r=document.querySelector('#reload').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
 await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[touch]});await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await ready();
 await send('Emulation.setTouchEmulationEnabled',{enabled:false});
 await screenshot('sensor-1024x600');assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
 // Default focus and real Escape cancellation; no state publication.
 let before=state().revision;await click('#review');await until(`document.querySelector('#candidate-review').open`);
 assert.equal(await evaluate(`document.activeElement.id`),'cancel-review');await key('Escape');assert.equal(state().revision,before);
 await click('#review');await until(`document.querySelector('#candidate-review').open`);await click('#apply');await ready();assert.equal(state().current.mode,'sensors');assert.match(state().current.text,/\[temperature_sensor bed_sensor\]/);
 // Board change cancel preserves settings; confirmation clears only affected assignments.
 await set('#boards fieldset:nth-child(1) select','octopus-v1.1-non-pro');await key('Escape');assert.equal(await evaluate(`document.querySelector('#boards select').value`),'sv08-main');
 // Import explicit before/after comparison and cancellation. Private data stays in-memory.
 const imported=structuredClone(state().draft);imported.devices[0].settings.max_temp=100;
 const injectFile=async d=>evaluate(`(()=>{const dt=new DataTransfer();dt.items.add(new File([${JSON.stringify(JSON.stringify(d))}],'draft.json',{type:'application/json'}));const e=document.querySelector('#import');e.files=dt.files;e.dispatchEvent(new Event('change'));})()`);
 // Real tab B loads A's revision, edits its native form and saves independently.
 const staleA=structuredClone(state().draft),revisionA=state().revision;
 await injectFile(staleA);await until(`!document.querySelector('#import-diff').hidden && !document.querySelector('#save').disabled`);assert.match(await evaluate(`document.querySelector('#import-diff').textContent`),/No changes/); // prior valid comparison must disappear on stale refusal
 secondTarget=await(await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url+'/cockpit/@localhost/sv08-printer/index.html')}`,{method:'PUT'})).json();
 secondSocket=new WebSocket(secondTarget.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{secondSocket.onopen=resolve;secondSocket.onerror=reject;});
 let bid=0;const bpending=new Map();
 const sendB=(method,params={})=>new Promise((resolve,reject)=>{const id=++bid;bpending.set(id,{resolve,reject});secondSocket.send(JSON.stringify({id,method,params}));});
 secondSocket.onmessage=({data})=>{const r=JSON.parse(data);if(r.id){const p=bpending.get(r.id);bpending.delete(r.id);r.error?p.reject(r.error):p.resolve(r.result);}};
 const evalB=async expression=>{const r=await sendB('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const untilB=async expression=>{for(let i=0;i<100;i++){if(await evalB(expression))return;await delay(100);}throw Error('Tab B timeout '+expression);};
 await untilB(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await evalB(`document.querySelector('#authorize').click()`);await untilB(`document.querySelector('#devices fieldset') && !document.querySelector('#save').disabled`);
 await evalB(`(()=>{const e=[...document.querySelector('#devices fieldset').querySelectorAll('label')].find(e=>e.firstChild.textContent==='max temp').querySelector('input');e.value=100;e.dispatchEvent(new Event('change'));document.querySelector('#save').click();})()`);
 await untilB(`document.querySelector('#notice').textContent==='Draft saved'`);assert.equal(state().draft.devices[0].settings.max_temp,100);assert.equal(state().revision,revisionA+1);
 await injectFile(staleA);await until(`document.querySelector('#notice').textContent.includes('refresh before importing') && !document.querySelector('#save').disabled`);
 assert.equal(await evaluate(`document.querySelector('#import-diff').hidden`),true);assert.equal(state().revision,revisionA+1);assert.equal(state().draft.devices[0].settings.max_temp,100);
 await click('#save');await until(`document.querySelector('#notice').textContent.includes('refresh before saving')`);assert.equal(state().revision,revisionA+1);
 await click('#reload');await ready();await injectFile(staleA);await until(`!document.querySelector('#import-diff').hidden && !document.querySelector('#save').disabled`);
 assert.match(await evaluate(`document.querySelector('#import-diff').textContent`),/100/);assert.match(await evaluate(`document.querySelector('#import-diff').textContent`),/105/);assert.doesNotMatch(await evaluate(`document.querySelector('#import-diff').textContent`),/No changes/);
 await click('#save');await ready();assert.equal(state().draft.devices[0].settings.max_temp,105);secondSocket.close();secondSocket=null;
 await fetch(`http://127.0.0.1:${port}/json/close/${secondTarget.id}`);secondTarget=null;
 await injectFile(imported);await until(`!document.querySelector('#import-diff').hidden && !document.querySelector('#save').disabled`);
 assert.match(await evaluate(`document.querySelector('#import-diff').textContent`),/max temp/);assert.match(await evaluate(`document.querySelector('#import-diff').textContent`),/105/);assert.match(await evaluate(`document.querySelector('#import-diff').textContent`),/100/);
 assert.equal(state().draft.devices[0].settings.max_temp,105);await click('#cancel-import');assert.equal(state().draft.devices[0].settings.max_temp,105);
 await injectFile(imported);await until(`!document.querySelector('#import-diff').hidden && !document.querySelector('#save').disabled`);await click('#save');await ready();
 await click('#review');await until(`document.querySelector('#candidate-review').open`);await click('#apply');await ready();assert.equal(state().previous.draft.devices[0].settings.max_temp,105);
 await click('#restore');await ready();assert.equal(state().draft.devices[0].settings.max_temp,105);
 await click('#review');await until(`document.querySelector('#candidate-review').open`);
 await evaluate('window.fixtureLoseAck=true');await click('#apply');await until(`document.querySelector('#notice').textContent.includes('acknowledged')`);const ackRevision=state().revision;
 await click('#reload');await ready();assert.equal(state().revision,ackRevision); // reconciliation never blindly retries
 await send('Page.setDownloadBehavior',{behavior:'allow',downloadPath:output});await click('#export');await click('#export-config');
 for(let i=0;i<100 && (!fs.existsSync(output+'/printer-hardware-draft.json')||!fs.existsSync(output+'/inactive-candidate.cfg'));i++)await delay(100);
 assert.equal(JSON.parse(fs.readFileSync(output+'/printer-hardware-draft.json')).devices[0].settings.max_temp,105);assert.match(fs.readFileSync(output+'/inactive-candidate.cfg','utf8'),/kinematics: none/);
 // Friendly X motor / TMC2209 defaults require no raw section-name entry.
 await set('#device-preset','stepper_x');assert.match(await evaluate(`document.querySelector('#device-preset').selectedOptions[0].textContent`),/X axis motor/);
 await click('#add-preset');await until(`document.querySelectorAll('#devices fieldset').length===2 && !document.querySelector('#save').disabled`);
 await click('#save');await ready();const motor=state().draft.devices.find(d=>d.kind==='motor');
 assert.equal(motor.name,'stepper_x');assert.equal(motor.settings.microsteps,16);assert.equal(motor.settings.rotation_distance,40);assert.equal(motor.settings.uart_address,3);assert.equal(motor.settings.run_current,1.5);assert.equal(motor.settings.current_rating_rms,undefined);
 before=state().revision;await click('#add-preset');await until(`document.querySelector('#notice').textContent.includes('unique') && !document.querySelector('#save').disabled`);assert.equal(state().revision,before);assert.equal(state().draft.devices.length,2);
 await set('#mode','full');await click('#review');await until(`document.querySelector('#candidate-review').open`);assert.match(await evaluate(`document.querySelector('#review-detail').textContent`),/current_rating_rms/);assert.equal(await evaluate(`document.querySelector('#apply').disabled`),true);await click('#cancel-review');
 await click('#devices fieldset:nth-child(2) button');await click('#save');await ready();await set('#mode','sensors');
 // Actual Store copies identical revision into B while this native tab holds A.
 const loadedRevision=state().revision,originalPath=statepath,originalBytes=fs.readFileSync(statepath);
 const swapped=await(await fetch(url+'/swap-generation',{method:'POST',body:'{}'})).json();assert(swapped.ok);statepath=swapped.result.state;
 assert.equal(state().revision,loadedRevision);assert.deepEqual(fs.readFileSync(statepath),originalBytes);
 const staleBytes=fs.readFileSync(statepath);
 await click('#review');await until(`document.querySelector('#notice').textContent.includes('context is stale') && !document.querySelector('#save').disabled`);assert.equal(await evaluate(`document.querySelector('#candidate-review').open`),false);
 await click('#restore');await until(`document.querySelector('#notice').textContent.includes('context is stale') && !document.querySelector('#save').disabled`);
 await injectFile(state().draft);await until(`document.querySelector('#notice').textContent.includes('context is stale') && !document.querySelector('#save').disabled`);assert.equal(await evaluate(`document.querySelector('#import-diff').hidden`),true);
 await set('#device-preset','stepper_x');await click('#add-preset');await until(`document.querySelector('#notice').textContent.includes('context is stale') && !document.querySelector('#save').disabled`);
 await fieldSet(deviceField('max temp'),99);await click('#save');await until(`document.querySelector('#notice').textContent.includes('context is stale') && !document.querySelector('#save').disabled`);
 assert.deepEqual(fs.readFileSync(statepath),staleBytes);assert.deepEqual(fs.readFileSync(originalPath),originalBytes);
 await click('#reload');await ready();await fieldSet(deviceField('max temp'),104);await click('#save');await until(`document.querySelector('#notice').textContent==='Draft saved' && !document.querySelector('#save').disabled`);assert.equal(state().draft.devices[0].settings.max_temp,104);
 await click('#review');await until(`document.querySelector('#candidate-review').open`);await click('#apply');await ready();assert.equal(state().current.draft.devices[0].settings.max_temp,104);
 const calls=await evaluate('window.fixtureRequests');
 assert(calls.filter(c=>c.request.action!=='status').length>0);
 for(const c of calls)if(c.request.action!=='status'){assert.equal(typeof c.loaded,'string');assert.equal(c.request.expected_identity,c.loaded);}
 // Authority loss cancels review, and backend refuses direct mutations too.
 await click('#review');await until(`document.querySelector('#candidate-review').open`);await click('#stop-authorization');await until(`!document.querySelector('#candidate-review').open && document.querySelector('#save').disabled`);
 before=state().revision;
 const deniedIdentity=await evaluate('window.fixtureLoadedIdentity');
 const denied=await(await fetch(url+'/request',{method:'POST',body:JSON.stringify({action:'save',expected_revision:before,expected_identity:deniedIdentity,draft:state().draft})})).json();assert.equal(denied.ok,false);assert.equal(state().revision,before);
 await click('#authorize');await ready();
 await set('#boards fieldset:nth-child(1) select','octopus-v1.1-non-pro');await click('#confirm-board');await click('#save');await ready();assert.equal(state().draft.devices.length,0);assert.equal(state().draft.boards.main.identity,undefined);assert(state().current);
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});await screenshot('boards-desktop');assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
 await evaluate(`document.querySelector('#save').focus()`);await key('Tab');assert.equal(await evaluate(`document.activeElement.id`),'review');
 await evaluate('window.fixtureDisconnect()');await until(`document.querySelector('#save').disabled`);assert.match(await evaluate(`document.querySelector('#session-status').textContent`),/disconnected/);
 await send('Page.reload');await until(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await click('#authorize');await ready();await click('#logout');await until(`document.body.dataset.loggedOut==='true'`);assert.equal(await evaluate(`document.querySelector('#save').disabled`),true);
 const generation=JSON.parse(fs.readFileSync(fixture+'/fixture.json')).generation;
 assert.equal(fs.readFileSync(generation+'/config/printer.cfg','utf8'),fs.readFileSync(fixture+'/original-live.txt','utf8'));
 assert.equal(await evaluate(`localStorage.length`),0);assert.equal(errors.length,0,JSON.stringify(errors));
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,authenticated:false,hardware:false,transport:'Cockpit session/RPC shim; actual Store/Budget',viewport_sizes:[[1024,600],[1440,900]],second_package_link:true,incomplete_save_reopen:true,connector_pin_form:true,factory_default:true,sensor_reference_journey:true,motor_reference_journey:true,preset_collision_refused:true,two_real_tab_stale_import_refused:true,generation_swap_refused:true,last_status_identity_carried:true,refresh_generation_edit_apply:true,refresh_exact_import_diff:true,keyboard_escape:true,touch_reload:true,import_diff_cancel_save:true,review_cancel_apply:true,previous_restore:true,lost_ack_reconciled:true,board_change_clears:true,stop_disconnect_logout:true,live_config_unchanged:true,uncaught_exceptions:errors.length},null,2)+'\n');
 console.log('Printer browser fixture journeys PASS');
} finally {secondSocket?.close();socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);await delay(300);const bytes=path=>fs.readdirSync(path,{withFileTypes:true}).reduce((n,e)=>n+(e.isDirectory()?bytes(path+'/'+e.name):e.isFile()?fs.statSync(path+'/'+e.name).size:0),0);const profileBytes=bytes(profile);fs.writeFileSync(output+'/profile-usage.json',JSON.stringify({profile,bytes:profileBytes}));fs.rmSync(profile,{recursive:true,force:true});assert(profileBytes<24*1024*1024);}
