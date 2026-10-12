// Actual browser + disposable Python controller. No printer or network service.
import fs from 'node:fs';
import {startBrowser} from './browser_runtime.mjs';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';
const [chrome, fixture, output] = process.argv.slice(2);
const {url} = JSON.parse(fs.readFileSync(fixture+'/server.json'));
assert.match(url, /^http:\/\/127\.0\.0\.1:\d+$/);
fs.mkdirSync(output);
const browser = startBrowser({chrome, output});
let socket;
try {
 const port = await browser.ready;
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
 const key=async key=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:{Tab:9,Enter:13,Escape:27}[key],text:key==='Enter'?'\r':undefined});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});};
 const screenshot=async name=>{const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(r.data,'base64'));};
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url});await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 assert.equal(await evaluate(`document.querySelector('#fixture').hidden`),false);
 assert.match(await evaluate(`document.querySelector('#overview').textContent`),/Recovery boot entry is not enabled/);
 assert.equal(await evaluate(`document.querySelector('#overview [data-open=printer]').textContent`),'Open Hardware');
 await screenshot('overview');
 // Navigate with keyboard; native button Enter semantics must activate a page.
 await evaluate(`document.querySelector('[data-page="overview"]').focus()`);
 await key('Tab');await key('Tab');assert.equal(await evaluate(`document.activeElement.dataset.page`),'images');await key('Enter');
 await until(`!document.querySelector('#images').hidden`);
 assert.equal(await evaluate(`document.querySelector('#image-history').closest('.page').id`),'images');
 assert.equal(await evaluate(`document.querySelector('#images h1').compareDocumentPosition(document.querySelector('#image-history')) & Node.DOCUMENT_POSITION_FOLLOWING`),4);
 assert.match(await evaluate(`document.querySelector('#images').textContent`),/full payload.*separate reviewed action/s);
 // Global indicator: keyboard navigation reveals history without writing policy.
 const beforeJump=fs.readFileSync(fixture+'/state/state.json');
 await evaluate(`localStorage.setItem('sv08-history-maintenance',JSON.stringify({method:'history.apply'}));`);
 await evaluate('refresh()');await until(`!document.querySelector('#operation-indicator').hidden`);
 await click('[data-page="settings"]');
 await evaluate(`document.querySelector('#operation-indicator').focus()`);await key('Enter');
 await until(`!document.querySelector('#images').hidden`);
 assert.equal(await evaluate('document.activeElement.id'),'image-history-title');
 assert.equal(await evaluate(`(()=>{const r=document.querySelector('#image-history-title').getBoundingClientRect();return r.top>=0 && r.bottom<=innerHeight;})()`),true);
 await evaluate('history.back()');await until(`!document.querySelector('#settings').hidden && document.activeElement.matches('#settings h1')`);
 await delay(100); // Focus must remain after native history restoration finishes.
 assert.equal(await evaluate(`document.activeElement.closest('.page')?.id`),'settings');
 assert.deepEqual(fs.readFileSync(fixture+'/state/state.json'),beforeJump);
 // Controlled finite-read failure exercises the real app's error disabling guard.
 await evaluate(`window.pr9OriginalView=window.sv08View;window.sv08View=(area,...args)=>area==='host'?Promise.reject(Error('Controlled status unavailable')):window.pr9OriginalView(area,...args);refresh()`);
 await until(`document.querySelector('#connection').textContent==='System status unavailable'`);
 assert.equal(await evaluate(`document.querySelector('#operation-indicator').disabled`),false);
 await evaluate(`document.querySelector('#operation-indicator').focus()`);await key('Enter');
 await until(`document.activeElement.id==='image-history-title'`);
 assert.deepEqual(fs.readFileSync(fixture+'/state/state.json'),beforeJump);
 await evaluate(`window.sv08View=window.pr9OriginalView;delete window.pr9OriginalView;refresh()`);
 await until(`document.querySelector('#connection').textContent==='Host connected' && !document.querySelector('#save-auto').disabled`);
 await evaluate(`localStorage.removeItem('sv08-history-maintenance')`);
 await click('[data-page="images"]');
 // Cancel with Escape does not publish a policy change.
 await click('#auto-update');await click('#save-auto');await until(`document.querySelector('#review').open`);await key('Escape');
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/state/state.json')).auto_update,true);
 await click('#save-auto');await until(`document.querySelector('#review').open`);await click('#confirm');
 await until(`document.querySelector('#notice').textContent.startsWith('Saved.')`);
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/state/state.json')).auto_update,false);
 await click('[data-page="settings"]');await click('[name="mode"][value="writable"]');await click('#save-mode');await until(`document.querySelector('#review').open`);await key('Escape');
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/state/state.json')).requested_mode,'immutable');
 await click('#save-mode');await until(`document.querySelector('#review').open`);await click('#confirm');
 await until(`document.querySelector('#notice').textContent.startsWith('Saved.') && !document.querySelector('#review').open`);
 for(let i=0;i<50 && JSON.parse(fs.readFileSync(fixture+'/state/state.json')).requested_mode!=='writable';i++)await delay(100);
 assert.equal(JSON.parse(fs.readFileSync(fixture+'/state/state.json')).requested_mode,'writable');
 assert.equal(await evaluate(`document.querySelector('#settings-current-mode').textContent`),'Immutable');
 assert.match(await evaluate(`document.querySelector('#settings-next-mode').textContent`),/Writable.*after restart/);
 assert.equal(await evaluate(`document.querySelector('#overview-next-mode').textContent`),'Next boot: Writable');
 assert.equal(await evaluate(`document.querySelector('#mode').textContent`),'Immutable'); // Request does not remount root.
 await click('[data-page="images"]');assert.equal(await evaluate(`document.querySelector('#stage-image').disabled`),true);await screenshot('images');
 await send('Emulation.setDeviceMetricsOverride',{width:480,height:800,deviceScaleFactor:1,mobile:true});
 await send('Emulation.setTouchEmulationEnabled',{enabled:true});
 await click('#navigation-toggle');await click('#task-navigation [data-page="settings"]');await evaluate(`document.querySelector('#task-context [data-page="recovery"]').scrollIntoView()`);
 const rect=await evaluate(`(()=>{const r=document.querySelector('#task-context [data-page="recovery"]').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
 await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[rect]});await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 await until(`!document.querySelector('#recovery').hidden`);assert.equal(await evaluate(`document.querySelector('#recovery .card h2').textContent`),'Recovery boot entry is not enabled here');assert.match(await evaluate(`document.querySelector('#recovery').textContent`),/cannot start recovery or restore an OS/);await screenshot('touch-recovery');
 assert.equal(await evaluate(`document.documentElement.scrollWidth<=window.innerWidth`),true);
 assert.equal(errors.length,0);
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,physical_hardware:false,transport:'test Cockpit bridge shim; real disposable Controller',keyboard_navigation:true,indicator_history_focus_back_no_mutation:true,escape_cancels:true,policy_persistence:true,mode_applies_only_on_boot:true,touch_navigation:true,unavailable_installer_disabled:true,uncaught_exceptions:0},null,2)+'\n');
 console.log('Browser administration tests PASS');
}finally{socket?.close();await browser.stop();}
