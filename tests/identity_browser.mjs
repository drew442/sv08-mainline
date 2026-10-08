import fs from 'node:fs';import path from 'node:path';import {spawn} from 'node:child_process';import {setTimeout as delay} from 'node:timers/promises';import assert from 'node:assert/strict';
const repo=path.resolve(new URL('..',import.meta.url).pathname);const chrome='/home/drew/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome';
const server=spawn('python3',['-c',`import sys;sys.path[:0]=${JSON.stringify([repo+'/tests',repo+'/runtime'])};from test_identity import browser_fixture_server;browser_fixture_server()`],{stdio:['ignore','pipe','inherit']});
let config;let buffer='';server.stdout.on('data',chunk=>{buffer+=chunk;if(buffer.includes('\n')){try{config=JSON.parse(buffer.split('\n')[0])}catch{}}});
let child,socket,profile;
try{
 for(let n=0;n<100&&!config;n++)await delay(100);assert(config,'Fixture startup failed');
 profile=fs.mkdtempSync('/dev/shm/sv08-identity-browser-');const downloads=path.join(profile,'downloads');fs.mkdirSync(downloads);
 child=spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-background-networking','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore',detached:true});
 let port;for(let n=0;n<80;n++){try{port=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];break}catch{await delay(100)}}assert(port);
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j});
 let id=0;const pending=new Map();const send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;const timer=setTimeout(()=>reject(Error('Browser command timeout')),15000);pending.set(n,{resolve,reject,timer});socket.send(JSON.stringify({id:n,method,params}))});
 socket.onmessage=({data})=>{const e=JSON.parse(data);if(e.id&&pending.has(e.id)){const p=pending.get(e.id);pending.delete(e.id);clearTimeout(p.timer);e.error?p.reject(Error('Browser command failed')):p.resolve(e.result)}};
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error('Browser evaluation failed');return r.result.value};
 const until=async expression=>{for(let n=0;n<100;n++){if(await ev(expression))return;await delay(100)}throw Error('Browser condition timeout')};
 const click=selector=>ev(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const rpc=request=>ev(`cockpit.spawn([]).input(${JSON.stringify(JSON.stringify(request))}).then(x=>JSON.parse(x))`);
 await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloads});await send('Page.navigate',{url:config.url});
 await until('!!document.querySelector("#identity-export")');assert(await ev('document.querySelector("#identity-export").disabled'));
 await click('#fixture-authorize');await until('!document.querySelector("#identity-export").disabled');
 const original=(await rpc({method:'status'})).result;
 await click('#identity-download-ca');for(let n=0;n<100&&!fs.existsSync(downloads+'/sv08-printer-ca.crt');n++)await delay(100);
 const ca=fs.readFileSync(downloads+'/sv08-printer-ca.crt','utf8');assert(ca.includes('BEGIN CERTIFICATE')&&!ca.includes('PRIVATE KEY'));
 await send('DOM.enable');let document=await send('DOM.getDocument');let element=await send('DOM.querySelector',{nodeId:document.root.nodeId,selector:'#identity-key-file'});
 await send('DOM.setFileInputFiles',{nodeId:element.nodeId,files:[config.second_public_key]});await until('document.querySelector("#identity-status").textContent.includes("added")');
 await click('#identity-save-keys');await until('document.querySelector("#identity-review").open');await ev('document.querySelector("#identity-review").close("cancel")');assert.equal((await rpc({method:'status'})).result.revision,original.revision);
 await click('#identity-save-keys');await ev('document.querySelector("#identity-review").close("confirm")');await until('document.querySelector("#identity-status").textContent.includes("saved")');
 const afterKeys=(await rpc({method:'status'})).result;assert.equal(afterKeys.authorized_keys.trim().split('\n').length,2);assert.equal(afterKeys.ca_fingerprint,original.ca_fingerprint);assert.equal(afterKeys.ssh_fingerprint,original.ssh_fingerprint);
 await click('#identity-export');await until('document.querySelector("#identity-review").open');await ev('document.querySelector("#identity-review").close("confirm")');
 for(let n=0;n<100&&!fs.existsSync(downloads+'/sv08-printer-identity.zip');n++)await delay(100);assert(fs.statSync(downloads+'/sv08-printer-identity.zip').size>1000);
 const bad=path.join(config.work,'bad.zip');fs.writeFileSync(bad,'invalid');document=await send('DOM.getDocument');element=await send('DOM.querySelector',{nodeId:document.root.nodeId,selector:'#identity-bundle-file'});
 await send('DOM.setFileInputFiles',{nodeId:element.nodeId,files:[bad]});await click('#identity-import');await until('document.querySelector("#identity-status").textContent.includes("failed")');assert.equal((await rpc({method:'status'})).result.revision,afterKeys.revision);
 await send('DOM.setFileInputFiles',{nodeId:element.nodeId,files:[downloads+'/sv08-printer-identity.zip']});await click('#identity-import');await until('document.querySelector("#identity-review").open');
 await ev('document.querySelector("#identity-review").close("cancel")');assert.equal((await rpc({method:'status'})).result.revision,afterKeys.revision);
 await click('#identity-import');await until('document.querySelector("#identity-review").open');await ev('document.querySelector("#identity-review").close("confirm")');await until('document.querySelector("#identity-status").textContent.includes("restored")');
 const restored=(await rpc({method:'status'})).result;assert.equal(restored.ca_fingerprint,original.ca_fingerprint);assert.equal(restored.authorized_keys,afterKeys.authorized_keys);
 await click('#identity-refresh');await until('!document.querySelector("#identity-export").disabled');await click('#identity-export');await until('document.querySelector("#identity-review").open');await click('#fixture-authorize');assert(!(await ev('document.querySelector("#identity-review").open')));assert(await ev('document.querySelector("#identity-export").disabled'));
 await click('#fixture-authorize');await until('!document.querySelector("#identity-export").disabled');assert.equal((await rpc({method:'status'})).result.revision,restored.revision);
 for(const width of [390,1024,1440]){await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});assert(await ev('document.documentElement.scrollWidth <= innerWidth'),'Responsive overflow');}
 console.log(JSON.stringify({ca_download:true,public_key_upload_review_cancel_apply:true,identity_backup_download:true,invalid_restore_refused:true,restore_preview_cancel_apply:true,authority_loss_closes_pending_review:true,viewports:[390,1024,1440],backend:'real Identity class',cockpit_transport:'simulated fixture',physical_hardware:false}));
}finally{
 socket?.close();server.kill('SIGTERM');
 if(child){try{process.kill(-child.pid,'SIGTERM')}catch{}if(child.exitCode===null)await new Promise(r=>{child.once('exit',r);setTimeout(r,3000)});try{process.kill(-child.pid,'SIGKILL')}catch{}}
 if(server.exitCode===null)await new Promise(r=>{server.once('exit',r);setTimeout(r,2000)});
 await delay(100);if(profile)fs.rmSync(profile,{recursive:true,force:true,maxRetries:10,retryDelay:200});
}
