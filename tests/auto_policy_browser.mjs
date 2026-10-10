// Actual browser + disposable Python controller. No printer or network service.
import fs from 'node:fs';
import {createRequire} from 'node:module';
const WebSocket=createRequire(import.meta.url)('undici').WebSocket;
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
 await click('[data-page="images"]');
 assert.equal(await evaluate(`updateOptions('auto').allow_untrusted_provenance`),false);
 await evaluate(`document.querySelector('#auto-check-compatibility').closest('details').open=true`);
 await click('#auto-check-compatibility');await click('#auto-check-customization');await click('#auto-allow-downgrade');
 await delay(1800);
 assert.equal(await evaluate(`document.querySelector('#auto-check-compatibility').checked`),false);
 await click('#save-update-policy');await until(`document.querySelector('#review').open`);
 assert.match(await evaluate(`document.querySelector('#review-arguments').textContent`),/check_compatibility/);
 await click('#confirm');
 await until(`document.querySelector('#notice').textContent.startsWith('Saved.')`);
 const saved=JSON.parse(fs.readFileSync(fixture+'/state/state.json')).update_policy;
 assert.equal(saved.check_compatibility,false);assert.equal(saved.check_customization,false);
 assert.equal(saved.check_version,true);assert.equal(saved.allow_downgrade,true);assert.equal(saved.allow_untrusted_provenance,false);
 await evaluate(`(()=>{const original=request;window.captured=[];request=async m=>{if(m.method==='plan'&&m.action==='image.stage'){captured.push(m);return {action:m.action,arguments:m.arguments,revision:state.revision,title:'Fixture staging review',effect:'Review exact chosen checks',preserves_user_data:true};}if(m.method==='upload.plan'){captured.push(m);return {name:m.name,size:m.size,revision:state.revision,policy:'fixture',options:m.options};}return original(m);};})()`);
 await evaluate(`document.querySelector('#manual-check-version').closest('details').open=true`);
 await click('#manual-allow-untrusted-provenance');await click('#manual-check-version');
 await evaluate(`(()=>{state.images=[{id:'a'.repeat(64),label:'Fixture bundle'}];state.capabilities['image.stage']={available:true,reason:''};render();document.querySelector('#image-choice').value='a'.repeat(64);document.querySelector('#stage-image').disabled=false;})()`);
 await click('#stage-image');await until(`document.querySelector('#review').open`);
 assert.equal(await evaluate(`captured.at(-1).arguments.options.allow_untrusted_provenance`),true);
 assert.equal(await evaluate(`captured.at(-1).arguments.options.check_version`),false);
 assert.equal(await evaluate(`captured.at(-1).arguments.options.check_compatibility`),true);
 await key('Escape');
 await evaluate(`(()=>{const data=new DataTransfer();data.items.add(new File(['fixture'],'manual.raucb'));document.querySelector('#bundle-file').files=data.files;document.querySelector('#review-upload').disabled=false;})()`);
 await click('#review-upload');await until(`document.querySelector('#upload-review').open`);
 assert.equal(await evaluate(`captured.at(-1).options.allow_untrusted_provenance`),true);
 assert.equal(await evaluate(`captured.at(-1).options.check_version`),false);
 await key('Escape');
 await send('Emulation.setDeviceMetricsOverride',{width:480,height:800,deviceScaleFactor:1,mobile:true});
 await screenshot('advanced-checks-mobile');
 assert.equal(errors.length,0,JSON.stringify(errors));
 fs.writeFileSync(output+'/result.json',JSON.stringify({status:'PASS',automatic_policy:saved,manual_review_options_bound:true,upload_review_options_bound:true,draft_survives_poll:true,printer:false},null,2));
 console.log('Automatic policy browser PASS');

}finally{socket?.close();try{process.kill(-child.pid,'SIGTERM');}catch{}fs.closeSync(log);}
