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
 const key=async key=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:{Tab:9,Enter:13,Escape:27}[key],text:key==='Enter'?'\r':undefined});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});};
 const screenshot=async name=>{const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(r.data,'base64'));};
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url});await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 assert.equal(await evaluate(`document.querySelector('#fixture').hidden`),false);
 await screenshot('overview');
 // Navigate with keyboard; native button Enter semantics must activate a page.
 await evaluate(`document.querySelector('[data-page="overview"]').focus()`);
 await key('Tab');assert.equal(await evaluate(`document.activeElement.dataset.page`),'images');await key('Enter');
 await until(`!document.querySelector('#images').hidden`);
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
 assert.equal(await evaluate(`document.querySelector('#mode').textContent`),'Immutable'); // Request does not remount root.
 await click('[data-page="images"]');assert.equal(await evaluate(`document.querySelector('#stage-image').disabled`),true);await screenshot('images');
 await send('Emulation.setDeviceMetricsOverride',{width:480,height:800,deviceScaleFactor:1,mobile:true});
 await send('Emulation.setTouchEmulationEnabled',{enabled:true});
 await evaluate(`document.querySelector('[data-page="recovery"]').scrollIntoView()`);
 const rect=await evaluate(`(()=>{const r=document.querySelector('[data-page="recovery"]').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
 await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[rect]});await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 await until(`!document.querySelector('#recovery').hidden`);await screenshot('touch-recovery');
 assert.equal(await evaluate(`document.documentElement.scrollWidth<=window.innerWidth`),true);
 assert.equal(errors.length,0);
 fs.writeFileSync(output+'/result.json',JSON.stringify({passed:true,physical_hardware:false,transport:'test Cockpit bridge shim; real disposable Controller',keyboard_navigation:true,escape_cancels:true,policy_persistence:true,mode_applies_only_on_boot:true,touch_navigation:true,unavailable_installer_disabled:true,uncaught_exceptions:0},null,2)+'\n');
 console.log('Browser administration tests PASS');
}finally{socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);}
