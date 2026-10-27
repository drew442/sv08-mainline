// SPDX-License-Identifier: AGPL-3.0-or-later
// Actual disposable controller + staged source UI; injected offers test rendering only.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {setTimeout as delay} from 'node:timers/promises';
import {startBrowser} from './browser_runtime.mjs';
const [chrome, fixture, output] = process.argv.slice(2);
const {url,composed} = JSON.parse(fs.readFileSync(fixture+'/server.json'));
assert.match(url,/^http:\/\/127\.0\.0\.1:\d+$/);
fs.mkdirSync(output,{recursive:true,mode:0o700});
const browser=startBrowser({chrome,output});let socket;
try {
 const port=await browser.ready;
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let id=0;const pending=new Map();
 const send=(method,params={},sessionId)=>new Promise((resolve,reject)=>{const key=++id;const timer=setTimeout(()=>reject(Error('CDP timeout: '+method)),10000);pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params,...(sessionId?{sessionId}:{})}));});
 socket.onmessage=({data})=>{const message=JSON.parse(data);if(message.id){const request=pending.get(message.id);if(request){clearTimeout(request.timer);pending.delete(message.id);message.error?request.reject(message.error):request.resolve(message.result);}}};
 const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;};
 const until=async expression=>{for(let n=0;n<100;n++){if(await evaluate(expression))return;await delay(100);}throw Error('Timeout: '+expression);};
 const key=async key=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key,windowsVirtualKeyCode:{Enter:13,Escape:27,Tab:9}[key],text:key==='Enter'?'\r':undefined});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key});};
 const screenshot=async name=>{const result=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(result.data,'base64'));};
 await send('Runtime.enable');await send('Page.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url});await until(`document.querySelector('#connection')?.textContent==='Host connected'`);
 assert.equal(await evaluate(`sv08Session.elevated`),false);
 // Cockpit package metadata needs the ordinary login cookie, never elevation.
 assert.equal((await fetch(url+'/project-source.json')).status,401);
 assert.equal(await evaluate(`fetch('project-source.json',{credentials:'omit'}).then(response=>response.status)`),401);
 assert.equal(await evaluate(`fetch('project-source.json',{credentials:'same-origin'}).then(response=>response.status)`),401);
 assert.equal((await fetch(url+'/source-file?name='+encodeURIComponent('/usr/share/cockpit/sv08-host/project-source.json'))).status,401);
 assert.equal(await evaluate(`Boolean(document.querySelector('#printer'))`),Boolean(composed));
 const beforeState=fs.readFileSync(fixture+'/state/state.json');
 const beforeConfig=fs.readFileSync(JSON.parse(fs.readFileSync(fixture+'/fixture.json')).generation+'/config/printer.cfg');
 await evaluate(`document.querySelector('#network-ssid').value='Unfinished network draft';document.querySelector('#source-open').focus();`);
 const beforeRequests=await evaluate(`JSON.stringify(window.fixtureRequests.filter(request=>!(request.area==='host'&&['status','jobs','upload.list'].includes(request.method))))`);
 await key('Enter');await until(`document.querySelector('#project-source').open && document.querySelector('#source-status').textContent.includes('unqualified')`);
 assert.match(await evaluate(`document.querySelector('#source-build').textContent`),/^[a-f0-9]{64}$/);
 assert.equal(await evaluate(`document.querySelectorAll('#source-downloads a').length`),0);
 assert.equal(await evaluate(`document.querySelector('#source-open').disabled`),false);
 assert.equal(await evaluate(`window.fixtureStarts`),0);
 assert.equal(await evaluate(`JSON.stringify(window.fixtureRequests.filter(request=>!(request.area==='host'&&['status','jobs','upload.list'].includes(request.method))))`),beforeRequests);
 for(const [element,name] of [['source-license','project-LICENSE.txt'],['source-notice','project-NOTICE.txt'],['source-provenance','project-source.json']]) {
  const href=await evaluate(`document.querySelector('#${element}').href`);assert(href.startsWith('blob:'));
  const expected=fs.readFileSync(fixture+'/rootfs/usr/share/cockpit/sv08-host/'+name,'utf8');
  const before=new Set((await send('Target.getTargets')).targetInfos.map(t=>t.targetId));
  await evaluate(`document.querySelector('#${element}').focus()`);await key('Enter');
  let target;for(let i=0;i<100;i++){target=(await send('Target.getTargets')).targetInfos.find(t=>!before.has(t.targetId)&&t.type==='page'&&t.url===href);if(target)break;await delay(50);}assert(target,'Document opens in a new tab');
  const {sessionId}=await send('Target.attachToTarget',{targetId:target.targetId,flatten:true});
  let body;for(let i=0;i<100;i++){const r=await send('Runtime.evaluate',{expression:'document.readyState==="complete"?document.body.textContent:null',returnByValue:true},sessionId);body=r.result?.value;if(body!==null&&body!==undefined)break;await delay(50);}
  assert.equal(body,expected);await send('Target.closeTarget',{targetId:target.targetId});
 }
 assert.equal(await evaluate(`sv08Session.elevated`),false);
 assert.equal(await evaluate(`window.fixtureSourceFileReads.every(path=>['project-LICENSE.txt','project-NOTICE.txt','project-source.json'].some(name=>path==='/usr/share/cockpit/sv08-host/'+name))`),true);
 await screenshot('source-unqualified');await key('Escape');
 assert.equal(await evaluate(`document.querySelector('#network-ssid').value`),'Unfinished network draft');
 assert.equal(await evaluate(`document.activeElement.id`),'source-open');
 await screenshot('source-overview');
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
 await key('Enter');await until(`document.querySelector('#project-source').open`);
 assert.equal(await evaluate(`document.documentElement.scrollWidth <= innerWidth`),true);
 assert.equal(await evaluate(`(()=>{const r=document.querySelector('#project-source').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth;})()`),true);
 await screenshot('source-narrow');await key('Escape');
 // Controlled display states do not constitute public-availability evidence.
 await evaluate(`(async()=>{const file=cockpit.file('/usr/share/cockpit/sv08-host/project-source.json');try{window.sourceRecord=JSON.parse(await file.read());}finally{file.close();}window.sourceOriginalFile=cockpit.file;cockpit.file=(path,...args)=>{if(path==='/usr/share/cockpit/sv08-host/project-source.json')return {read:async()=>{if(window.sourceFailed)throw Error('controlled unavailable');const data=structuredClone(window.sourceRecord);data.development=false;data.source_revision='a'.repeat(40);data.public_source={qualified:true,scope:'project-source-only',overall_release_qualified:false,build_id:data.build_id,source_revision:data.source_revision,archive:{sha256:'b'.repeat(64),url:'https://public.example/source/'+data.source_revision+'.tar.gz'}};if(window.sourceMalformed){data.source_revision='bad';data.public_source.source_revision='bad';}return JSON.stringify(data);},close:()=>{}};return window.sourceOriginalFile(path,...args);};document.querySelector('#source-open').focus();})()`);
 await key('Enter');await until(`document.querySelectorAll('#source-downloads a').length===1`);
 assert.match(await evaluate(`document.querySelector('#source-downloads a').href`),/a{40}\.tar\.gz$/);
 await screenshot('source-checked-display');
 await evaluate(`window.sourceMalformed=true;document.querySelector('#source-retry').click()`);
 await until(`document.querySelector('#source-status').textContent.includes('unqualified')`);
 assert.equal(await evaluate(`document.querySelectorAll('#source-downloads a').length`),0);
 await evaluate(`window.sourceMalformed=false;document.querySelector('#source-retry').click()`);
 await until(`document.querySelectorAll('#source-downloads a').length===1`);
 await evaluate(`window.sourceFailed=true;document.querySelector('#source-retry').click()`);
 await until(`document.querySelector('#source-status').textContent.includes('unavailable')`);
 assert.equal(await evaluate(`document.querySelectorAll('#source-downloads a').length`),0);
 assert.doesNotMatch(await evaluate(`document.querySelector('#source-public-help').textContent`),/archive includes|checked/);
 assert.equal(await evaluate(`document.querySelector('#source-provenance').hasAttribute('href')`),false);
 assert.equal(await evaluate(`document.querySelector('#source-license').href.startsWith('blob:') && document.querySelector('#source-notice').href.startsWith('blob:')`),true);
 assert.equal(await evaluate(`document.querySelector('#source-documents-status').hidden`),false);
 await screenshot('source-unavailable');await key('Escape');
 assert.equal(await evaluate(`document.querySelector('#network-ssid').value`),'Unfinished network draft');
 assert.equal(await evaluate(`window.fixtureStarts`),0);
 assert.equal(await evaluate(`JSON.stringify(window.fixtureRequests.filter(request=>!(request.area==='host'&&['status','jobs','upload.list'].includes(request.method))))`),beforeRequests);
 assert.deepEqual(fs.readFileSync(fixture+'/state/state.json'),beforeState);
 assert.deepEqual(fs.readFileSync(JSON.parse(fs.readFileSync(fixture+'/fixture.json')).generation+'/config/printer.cfg'),beforeConfig);
 fs.writeFileSync(output+'/summary.json',JSON.stringify({passed:true,composed,widths:[1280,390],controller_mutations:0,administrator_starts:0,metadata_requires_ordinary_session:true,all_three_documents_open_exact_new_tab_contents:true,raw_http_denial_preserved:true,fixed_file_reads_no_elevation:true,partial_document_failure_keeps_other_links:true,unsaved_input_preserved:true,controlled_offer_rendering_only:true},null,2)+'\n');
} finally {socket?.close();await browser.stop();}
