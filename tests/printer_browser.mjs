// Actual Chromium + real generation-local Python Store. Cockpit session/RPC shim.
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';
const [chrome,fixture,output]=process.argv.slice(2);
const {url}=JSON.parse(fs.readFileSync(fixture+'/server.json'));
assert.match(url,/^http:\/\/127\.0\.0\.1:\d+$/);
fs.mkdirSync(output);const profile=output+'/profile',log=fs.openSync(output+'/browser.log','w');
const child=spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking','--disable-component-update','--disable-sync','--disable-default-apps','--disable-quic','--proxy-server=http://127.0.0.1:9','--proxy-bypass-list=127.0.0.1;localhost','--no-first-run','--disk-cache-size=1','--media-cache-size=1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{detached:true,stdio:['ignore',log,log]});
let socket;
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
 const statepath=JSON.parse(fs.readFileSync(fixture+'/fixture.json')).state;
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
 await set('#device-kind','sensor');await set('#device-name','bed_check');await click('#add');
 await click('#save');await ready();assert.equal(state().draft.devices[0].settings.pin,undefined);
 await send('Page.reload');await until(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await click('#authorize');await ready();assert.equal(state().draft.devices[0].name,'bed_check');
 const deviceField=text=>`(()=>{const box=document.querySelector('#devices fieldset');return [...box.querySelectorAll('label')].find(e=>e.firstChild.textContent===${JSON.stringify(text)}).querySelector('input,select');})()`;
 await fieldSet(deviceField('Connection / pin'),'PC5');await fieldSet(deviceField('curve'),'sovol-bed');
 await click('#devices fieldset button:last-child');await fieldSet(deviceField('min temp'),5);await fieldSet(deviceField('max temp'),105);
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
 await click('#review');await until(`document.querySelector('#candidate-review').open`);await click('#apply');await ready();assert.equal(state().current.mode,'sensors');assert.match(state().current.text,/\[temperature_sensor bed_check\]/);
 // Board change cancel preserves settings; confirmation clears only affected assignments.
 await set('#boards fieldset:nth-child(1) select','octopus-v1.1-non-pro');await key('Escape');assert.equal(await evaluate(`document.querySelector('#boards select').value`),'sv08-main');
 // Import explicit before/after comparison and cancellation. Private data stays in-memory.
 const imported=structuredClone(state().draft);imported.devices[0].settings.max_temp=100;
 const injectFile=async d=>evaluate(`(()=>{const dt=new DataTransfer();dt.items.add(new File([${JSON.stringify(JSON.stringify(d))}],'draft.json',{type:'application/json'}));const e=document.querySelector('#import');e.files=dt.files;e.dispatchEvent(new Event('change'));})()`);
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
 // Authority loss cancels review, and backend refuses direct mutations too.
 await click('#review');await until(`document.querySelector('#candidate-review').open`);await click('#stop-authorization');await until(`!document.querySelector('#candidate-review').open && document.querySelector('#save').disabled`);
 before=state().revision;
 const denied=await(await fetch(url+'/request',{method:'POST',body:JSON.stringify({action:'save',expected_revision:before,draft:state().draft})})).json();assert.equal(denied.ok,false);assert.equal(state().revision,before);
 await click('#authorize');await ready();
 await set('#boards fieldset:nth-child(1) select','octopus-v1.1-non-pro');await click('#confirm-board');await click('#save');await ready();assert.equal(state().draft.devices.length,0);assert.equal(state().draft.boards.main.identity,undefined);assert(state().current);
 await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});await screenshot('boards-desktop');assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true);
 await evaluate(`document.querySelector('#save').focus()`);await key('Tab');assert.equal(await evaluate(`document.activeElement.id`),'review');
 await evaluate('window.fixtureDisconnect()');await until(`document.querySelector('#save').disabled`);assert.match(await evaluate(`document.querySelector('#session-status').textContent`),/disconnected/);
 await send('Page.reload');await until(`document.querySelector('#authorize') && !document.querySelector('#authorize').disabled`);await click('#authorize');await ready();await click('#logout');await until(`document.body.dataset.loggedOut==='true'`);assert.equal(await evaluate(`document.querySelector('#save').disabled`),true);
 const generation=JSON.parse(fs.readFileSync(fixture+'/fixture.json')).generation;
 assert.equal(fs.readFileSync(generation+'/config/printer.cfg','utf8'),fs.readFileSync(fixture+'/original-live.txt','utf8'));
 assert.equal(await evaluate(`localStorage.length`),0);assert.equal(errors.length,0,JSON.stringify(errors));
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,authenticated:false,hardware:false,transport:'Cockpit session/RPC shim; actual Store/Budget',viewport_sizes:[[1024,600],[1440,900]],second_package_link:true,incomplete_save_reopen:true,connector_pin_form:true,factory_default:true,keyboard_escape:true,touch_reload:true,import_diff_cancel_save:true,review_cancel_apply:true,previous_restore:true,lost_ack_reconciled:true,board_change_clears:true,stop_disconnect_logout:true,live_config_unchanged:true,uncaught_exceptions:errors.length},null,2)+'\n');
 console.log('Printer browser fixture journeys PASS');
} finally {socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);}
