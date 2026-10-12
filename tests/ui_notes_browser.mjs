// Composed production UI, actual Store/session shim. No submitted mutations.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {setTimeout as delay} from 'node:timers/promises';
import {startBrowser,assertBrowserZoom} from './browser_runtime.mjs';
const [chrome,fixture,output]=process.argv.slice(2),zoom=Number(process.env.SV08_NOTES_ZOOM||1);
const {url}=JSON.parse(fs.readFileSync(fixture+'/server.json'));
assert.match(url,/^http:\/\/127\.0\.0\.1:\d+$/);
const statepath=JSON.parse(fs.readFileSync(fixture+'/fixture.json')).state;
const before=fs.existsSync(statepath)?fs.readFileSync(statepath):null;
const browser=startBrowser({chrome,output,zoom});let socket;
try{
 const port=await browser.ready,tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let id=0;const pending=new Map(),errors=[];
 socket.onmessage=({data})=>{const e=JSON.parse(data);if(e.id){const p=pending.get(e.id);if(p){clearTimeout(p.timer);pending.delete(e.id);e.error?p.reject(e.error):p.resolve(e.result);}}if(e.method==='Runtime.exceptionThrown')errors.push(e.params);};
 const send=(method,params={})=>new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>reject(Error('CDP timeout '+method)),10000);pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params}));});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const until=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await delay(100);}throw Error('Timeout '+expression);};
 const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const key=async value=>{for(const type of ['keyDown','keyUp'])await send('Input.dispatchKeyEvent',{type,key:value,code:value,windowsVirtualKeyCode:{Enter:13,Escape:27}[value],text:type==='keyDown'&&value==='Enter'?'\r':undefined});};
 const screenshot=async name=>{const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(shot.data,'base64'));};
 await send('Runtime.enable');await send('Page.enable');await send('Emulation.setDeviceMetricsOverride',{width:1024,height:600,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:url+'/cockpit/@localhost/sv08-host/index.html'});
 await until(`window.sv08Session?.available && document.querySelector('#printer-cards button') && document.querySelector('#release').textContent==='offline'`);
 await until(`!document.querySelector('#authorize').disabled`);await click('#authorize');await until('sv08Session.elevated');
 const base=await evaluate('JSON.stringify(state)');
 // A stale automatic-restart journal cannot overwrite current terminal failure.
 for(const result of ['reboot-queued','reboot-observed']){
  await evaluate(`state={...JSON.parse(${JSON.stringify(base)}),transaction:{phase:'failed'},feed_status:{result:${JSON.stringify(result)}}};render()`);
  assert.equal(await evaluate(`document.querySelector('#update-status-panel').dataset.tone`),'error');
  assert.equal(await evaluate(`document.querySelector('#update-title').textContent`),'Update failed');
  assert.match(await evaluate(`document.querySelector('#update-feed').textContent`),/^Last automatic check:/);
  assert.doesNotMatch(await evaluate(`document.querySelector('#update-detail').textContent`),/restart requested|health.*failed/i);
  assert.equal(await evaluate(`document.querySelector('#update-status svg')!==null`),true);
  assert.equal(await evaluate(`document.querySelector('#manual-update-step').dataset.tone`),'error');
  assert.match(await evaluate(`document.querySelector('#manual-update-step').textContent`),/^Update failed/);
 }
 await evaluate(`document.querySelector('#update-status-panel').scrollIntoView({block:'start'})`);await screenshot('update-failed');
 for(const [phase,tone] of [['complete','success'],['cancelled','neutral'],['preparing','warning'],['installing','warning'],['staged','warning'],['arming','warning'],['armed','warning'],['confirming','warning'],['unknown','neutral']]){
  await evaluate(`state={...JSON.parse(${JSON.stringify(base)}),transaction:{phase:${JSON.stringify(phase)}},feed_status:{result:'reboot-queued'}};render();renderJobs({jobs:[{id:'old',action:'image.stage',phase:'failed',message:'Historical failure'}],blocked:false,capacity:128,remaining:127})`);
  assert.equal(await evaluate(`document.querySelector('#update-status-panel').dataset.tone`),tone);
 }
 await evaluate(`state={...JSON.parse(${JSON.stringify(base)}),boot:{...state.boot,slot:'B'},pending:{slot:'B',release:'trial',phase:'trial'}};render()`);
 assert.match(await evaluate(`document.querySelector('#update-title').textContent`),/Trial/);
 await evaluate(`state=JSON.parse(${JSON.stringify(base)});render();window.fixtureHostCalls=[];window.fixtureRequests=[]`);
 // Only explicitly unused P2P and loopback disappear; stale saved metadata is insufficient.
 await evaluate(`window.fixtureSettings.network.devices.push({device:'lo',type:'loopback',state:'connected',addresses:['127.0.0.1/8']},{device:'p2p-dev-wlan0',type:'wifi-p2p',state:'disconnected',uuid:'stale',connection:'Saved',addresses:['127.0.0.2/8']},{device:'p2p-dev-wlan1',type:'wifi-p2p',state:'connected',uuid:'p2p-active',connection:'Peer',addresses:['192.0.2.50/24']})`);
 await evaluate(`sv08Navigation.go('network')`);await until(`document.querySelector('#network-status').textContent==='Network settings are ready.'`);
 assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('#network-devices article')).map(e=>e.dataset.device)`),['eth0','p2p-dev-wlan1']);
 assert.doesNotMatch(await evaluate(`document.querySelector('#network-links').textContent`),/127\.0\.0\.[12]/);
 assert.equal(await evaluate(`document.querySelector('#network-device option[value=lo]')!==null`),false);
 await screenshot('network');
 // Refresh cannot silently retarget a retained draft to a now hidden interface.
 await evaluate(`document.querySelector('#network-addresses').value='192.0.2.99/24';document.querySelector('#network-addresses').dispatchEvent(new Event('input',{bubbles:true}));window.fixtureSettings.network.devices=window.fixtureSettings.network.devices.filter(d=>d.device!=='eth0')`);
 await click('#network-refresh');await until(`document.querySelector('#network-status').textContent.includes('Previous network target is unavailable')`);
 assert.equal(await evaluate(`document.querySelector('#network-apply').disabled`),true);
 await click('#network-apply');assert.equal(await evaluate(`window.fixtureHostCalls.some(r=>!['status','jobs','upload.list'].includes(r.method))`),false);
 await evaluate(`sv08Navigation.go('printer')`);await click('[data-category=cooling]');await until(`document.querySelectorAll('#printer-components label').length>0 && Array.from(document.querySelectorAll('#printer-components label')).every(e=>e.querySelector('svg'))`);
 assert.equal(await evaluate(`Array.from(document.querySelectorAll('#printer-components label')).every(e=>e.querySelector('svg')&&e.textContent.trim())`),true);
 await evaluate(`document.querySelector('#printer-components').scrollIntoView({block:'start'})`);await screenshot('components');
 await evaluate(`sv08Navigation.go('printer-connections')`);await until(`document.querySelectorAll('.printer-graph-node').length>0`);
 assert.equal(await evaluate(`document.querySelector('#printer-connection-map').hidden`),false);
 assert.equal(await evaluate(`document.querySelector('#printer-map-toggle').getAttribute('aria-pressed')`),'true');
 await evaluate(`document.querySelector('#printer-table-toggle').focus()`);await key('Enter');
 assert.equal(await evaluate(`document.querySelector('#printer-connection-table').hidden`),false);
 await evaluate(`document.querySelector('#printer-map-toggle').focus()`);await key('Enter');
 assert.equal(await evaluate(`document.querySelector('#printer-connection-map').hidden`),false);
 const spacing=async()=>{
  const boxes=await evaluate(`Array.from(document.querySelectorAll('.printer-graph-node')).map(e=>{const r=e.getBoundingClientRect();return {id:e.dataset.node,left:r.left,right:r.right,top:r.top,bottom:r.bottom};})`);
  for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){
   const a=boxes[i],b=boxes[j];assert.ok(a.right<=b.left+.5||b.right<=a.left+.5||a.bottom<=b.top+.5||b.bottom<=a.top+.5,'Initial graph node overlap: '+a.id+' / '+b.id);
  }

  const gaps=await evaluate(`Array.from(document.querySelectorAll('button+button')).filter(b=>b.getClientRects().length&&b.previousElementSibling.getClientRects().length).map(b=>{const a=b.previousElementSibling.getBoundingClientRect(),r=b.getBoundingClientRect(),gap=r.top>=a.bottom-1?r.top-a.bottom:r.left-a.right;const scene=b.classList.contains('printer-graph-port')?b.closest('#printer-graph-scene'):null,scale=scene?new DOMMatrix(getComputedStyle(scene).transform).a:1;return {text:b.textContent,gap,layoutGap:gap/scale};})`);
  // Diagram terminal controls are deliberately zoomed with the map. Require
  // the same 8 CSS px layout gap and visible separation at the chosen scale;
  // HTML action controls retain an actual untransformed 8 CSS px gap.
  for(const gap of gaps)assert.ok(gap.gap>0&&gap.layoutGap>=7.5,'Adjacent buttons: '+JSON.stringify(gap));
  assert.equal(await evaluate(`document.querySelectorAll('h1 svg,h2 svg,h3 svg,h4 svg,h5 svg,h6 svg').length`),0);
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).every(e=>!e.hasAttribute('data-icon')&&['none','normal'].includes(getComputedStyle(e,'::before').content)&&['none','normal'].includes(getComputedStyle(e,'::after').content))`),true);
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('.printer-card,.printer-definition-card')).every(e=>e.querySelector('svg')&&e.textContent.trim())`),true);
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('[data-page],[data-open],#task-context button,.printer-graph-heading')).every(e=>e.querySelector('svg')&&e.textContent.trim())`),true);
 };
 let zoomResult=null;
 if(zoom===2){zoomResult=await assertBrowserZoom({send,evaluate,zoom});await spacing();await evaluate(`document.querySelector('#printer-graph-controls').scrollIntoView({block:'start'})`);await screenshot('connections-zoom');}
 else for(const [width,height] of [[390,844],[1024,600],[1440,900]]){await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await spacing();assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);await evaluate(`document.querySelector('#printer-graph-controls').scrollIntoView({block:'start'})`);await screenshot('connections-'+width);}
 assert.deepEqual(await evaluate(`window.fixtureRequests.filter(r=>r.request.action!=='status')`),[]);
 assert.equal(await evaluate(`window.fixtureHostCalls.some(r=>!['status','jobs','upload.list'].includes(r.method))`),false);
 if(before)assert.deepEqual(fs.readFileSync(statepath),before);else assert.equal(fs.existsSync(statepath),false);
 assert.deepEqual(errors,[]);
 fs.writeFileSync(output+'/result.json',JSON.stringify({network_filter:true,missing_draft_target:true,status:true,historical_feed:true,icons:true,graph_default:true,list_keyboard:true,spacing:true,no_mutations:true,zoom:zoomResult},null,2)+'\n');
}finally{socket?.close();await browser.stop();}
