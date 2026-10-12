// Composed factory fixture: local appearance, real retained draft and rendered palettes.
// node tests/theme_browser.mjs CHROME FIXTURE OUTPUT [1|2]
// Run separately at 1 and 2; startBrowser supplies persisted actual browser zoom.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {setTimeout as delay} from 'node:timers/promises';
import {startBrowser,assertBrowserZoom} from './browser_runtime.mjs';
const [chrome,fixture,output,zoomArg='1']=process.argv.slice(2), zoom=Number(zoomArg);
const {url}=JSON.parse(fs.readFileSync(fixture+'/server.json'));
assert.match(url,/^http:\/\/127\.0\.0\.1:\d+$/);
const {state:statePath}=JSON.parse(fs.readFileSync(fixture+'/fixture.json'));
const initialState=fs.existsSync(statePath)?fs.readFileSync(statePath):null;
const browser=startBrowser({chrome,output,zoom,args:['--proxy-server=http://127.0.0.1:9','--proxy-bypass-list=127.0.0.1;localhost']});
const results={zoom,screenshots:[],checks:[]};let socket;
try {
 const port=await browser.ready;
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 socket=new WebSocket(tabs.find(tab=>tab.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let id=0;const pending=new Map(),errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{const key=++id,timer=setTimeout(()=>{pending.delete(key);reject(Error('CDP timeout '+method));},10000);pending.set(key,{resolve,reject,timer});socket.send(JSON.stringify({id:key,method,params}));});
 socket.onmessage=({data})=>{const event=JSON.parse(data);if(event.id){const p=pending.get(event.id);if(p){clearTimeout(p.timer);pending.delete(event.id);event.error?p.reject(event.error):p.resolve(event.result);}}if(event.method==='Runtime.exceptionThrown')errors.push(event.params);if(event.method==='Page.javascriptDialogOpening'){assert.equal(event.params.type,'beforeunload','Only explicit dirty-draft discard is accepted');results.discarded_draft_dialogs=(results.discarded_draft_dialogs??0)+1;void send('Page.handleJavaScriptDialog',{accept:true});}};
 const ev=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;};
 const until=async expression=>{for(let attempt=0;attempt<100;attempt++){try{if(await ev(expression))return;}catch(error){if(error.code!==-32000)throw error;}await delay(100);}throw Error('Timeout: '+expression);};
 const click=selector=>ev(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const key=async value=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key:value,code:value,windowsVirtualKeyCode:{ArrowDown:40,ArrowUp:38,Enter:13,Escape:27,Tab:9}[value]});await send('Input.dispatchKeyEvent',{type:'keyUp',key:value,code:value});};
 const route=async name=>{await ev(`sv08Navigation.go(${JSON.stringify(name)});scrollTo(0,0)`);await until(`!document.getElementById(${JSON.stringify(name)}).hidden`);};
 const choose=async theme=>{await route('settings');await ev(`document.getElementById('appearance-theme').focus()`);await key(theme==='dark'?'ArrowDown':'ArrowUp');await key('Enter');await until(`document.documentElement.dataset.theme===${JSON.stringify(theme)}`);};
 const capture=async(name,selector)=>{await ev(selector?`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'start'})`:'scrollTo(0,0)');const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(output+'/'+name+'.png',Buffer.from(r.data,'base64'));results.screenshots.push(name+'.png');};
 const reload=async()=>{const origin=await ev('performance.timeOrigin');await send('Page.reload');await until(`performance.timeOrigin!==${origin} && window.sv08Session?.available && document.querySelector('#printer-notice').textContent.startsWith('Saved configuration loaded.') && document.querySelector('#connection').textContent==='Host connected'`);};
 const noMutations=async()=>{assert.deepEqual(await ev(`fixtureRequests.filter(row=>row.request.action!=='status').map(row=>row.request.action)`),[]);assert.deepEqual(await ev(`fixtureHostCalls.filter(row=>!['status','jobs','upload.list','plan'].includes(row.method)).map(row=>row.method)`),[]);if(initialState)assert.deepEqual(fs.readFileSync(statePath),initialState);else assert.equal(fs.existsSync(statePath),false);};
 // Compute contrast from rendered, opaque surfaces, not token names or screenshots.
 const readable=async selectors=>{
  const values=await ev(`(()=>{
   const rgb=color=>color.match(/[\\d.]+/g).slice(0,3).map(Number);
   const luminance=color=>rgb(color).map(n=>{n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;}).reduce((v,n,i)=>v+n*[.2126,.7152,.0722][i],0);
   return ${JSON.stringify(selectors)}.flatMap(selector=>[...document.querySelectorAll(selector)].filter(e=>e.getClientRects().length&&e.textContent.trim()).map(e=>{
    let surface=e;while(surface.parentElement&&getComputedStyle(surface).backgroundColor==='rgba(0, 0, 0, 0)')surface=surface.parentElement;
    const fg=getComputedStyle(e).color,bg=getComputedStyle(surface).backgroundColor,a=luminance(fg),b=luminance(bg);
    return {selector,text:e.textContent.trim().slice(0,70),fg,bg,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
   }));
  })()`);
  assert.ok(values.length,'Rendered text was checked');for(const value of values)assert.ok(value.ratio>=4.5,JSON.stringify(value));return values;
 };
 await send('Runtime.enable');await send('Page.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:1024,height:600,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:url+'/cockpit/@localhost/sv08-host/index.html'});
 await until(`window.sv08Session?.available && document.querySelector('#printer-notice').textContent.startsWith('Saved configuration loaded.') && document.querySelector('#connection').textContent==='Host connected'`);
 if(zoom===2)results.actual_zoom=await assertBrowserZoom({send,evaluate:ev,zoom});
 assert.equal(await ev('sv08Session.elevated'),false);assert.equal(await ev('document.documentElement.dataset.theme'),'light');
 await route('settings');assert.equal(await ev("document.getElementById('appearance-theme').disabled"),false);
 assert.equal(await ev("document.getElementById('save-mode').disabled"),true);
 await capture('light-settings','#appearance');
 await choose('dark');assert.match(await ev("document.getElementById('appearance-status').textContent"),/Saved in this browser/);
 await readable(['#appearance h2','#appearance p','#appearance label']);
 await reload();assert.equal(await ev('document.documentElement.dataset.theme'),'dark');
 await ev('window.fixtureHostCalls=[];window.fixtureRequests=[]');
 await click('#authorize');await until('sv08Session.elevated && !document.getElementById("printer-save").disabled');
 await route('printer');await click('[data-category=cooling]');
 const draftSelector='[data-print-fan=part_cooling_front]';
 await until(`document.querySelector(${JSON.stringify(draftSelector)}) && !document.querySelector(${JSON.stringify(draftSelector)}).disabled`);
 const old=await ev(`document.querySelector(${JSON.stringify(draftSelector)}).checked`);
 assert.equal(await ev(`document.querySelector(${JSON.stringify(draftSelector)}).disabled`),false,'Existing draft edit requires administrator access');
 await click(draftSelector);await until(`document.getElementById('printer-draft-state').textContent.startsWith('Unsaved selections')`);
 const draftText=await ev("document.getElementById('printer-draft-state').textContent");
 await click('#stop-authorization');await until('!sv08Session.elevated');
 await choose('light');await choose('dark');await route('printer');
 assert.equal(await ev(`document.querySelector(${JSON.stringify(draftSelector)}).checked`),!old);
 assert.equal(await ev("document.getElementById('printer-draft-state').textContent"),draftText);
 await noMutations();results.checks.push('ordinary keyboard choice, reload persistence, retained changed draft, no backend mutations');
 // Authority changes may refresh read state; they must retain a dirty local draft.
 await click('#authorize');await until('sv08Session.elevated');await choose('light');await choose('dark');
 await click('#stop-authorization');await until('!sv08Session.elevated');await route('printer');
 assert.equal(await ev("document.getElementById('printer-draft-state').textContent"),draftText);
 assert.equal(await ev(`document.querySelector(${JSON.stringify(draftSelector)}).checked`),!old);
 await route('settings');await ev('window.fixtureHostFailure=true;refresh()');await until("document.getElementById('connection').textContent==='System status unavailable'");
 await choose('light');await choose('dark');assert.equal(await ev("document.getElementById('appearance-theme').disabled"),false);
 await ev('window.fixtureHostFailure=false;refresh()');await until("document.getElementById('connection').textContent==='Host connected'");
 results.checks.push('session changes and unavailable host status preserve local appearance');
 // Existing review flow, cancelled with Escape: no apply is submitted.
 await click('#authorize');await until('sv08Session.elevated && !document.getElementById("save-mode").disabled');
 await click('#save-mode');await until('document.getElementById("review").open');
 await readable(['#review h2','#review p','#review pre','#review button']);await capture('dark-review');await key('Escape');await until('!document.getElementById("review").open');
 await click('#stop-authorization');await until('!sv08Session.elevated');
 // Factory components, catalogue, sources, graph and host tasks at supported widths.
 for(const width of (zoom===2?[1024]:[390,1024,1440])) {
  await send('Emulation.setDeviceMetricsOverride',{width,height:width===390?844:900,deviceScaleFactor:1,mobile:false});
  if(zoom===2)await assertBrowserZoom({send,evaluate:ev,zoom});
  for(const name of ['settings','network','printer','definitions','definition-sources','printer-connections','images']) {
   await route(name);
   assert.equal(await ev('document.documentElement.scrollWidth<=innerWidth'),true,`${name} overflow at ${width}, zoom ${zoom}`);
   assert.equal(await ev('document.querySelectorAll("h1 > svg,h2 > svg,h3 > svg").length'),0);
   await readable([`#${name} h1`,`#${name} h2`,`#${name} .intro`,`#${name} .printer-card strong`,`#${name} .printer-card small`,`#${name} .printer-status`,`#${name} .printer-journey`,`#${name} .printer-state dt`,`#${name} .printer-state dd`,`#${name} a`,`#${name} label small`,`#${name} .source`,`#${name} .reason`,`#${name} [data-tone]`]);
   await capture(`dark-${name}-${width}-zoom${zoom}`);
  }
 }
 await route('printer-connections');await until('document.querySelector(".printer-graph-node")');
 const graph=await readable(['.printer-graph-heading','.printer-graph-port','.printer-graph-node > small']);
 assert.ok(graph.length>5);assert.ok(await ev('document.querySelectorAll(".printer-graph-wire").length>0'));
 // Render actual host status components through their existing reducer/render path.
 await route('overview');
 for(const phase of ['failed','armed','complete']){
  await ev(`state={...state,transaction:{phase:${JSON.stringify(phase)}}};render()`);
  await readable(['#update-title','#update-detail','#update-status']);await capture('dark-update-'+phase,'#update-status-panel');
 }
 await noMutations();results.checks.push('responsive host/printer/catalogue/source/graph surfaces, review cancellation, red/amber/green readable');
 // Write denial leaves the current page changed and old persisted value intact.
 await choose('light');
 const writeFault=await send('Page.addScriptToEvaluateOnNewDocument',{source:`const original=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(key==='sv08.appearance')throw Error('Injected full storage');return original.call(this,key,value);};`});
 await reload();await choose('dark');assert.match(await ev("document.getElementById('appearance-status').textContent"),/storage is unavailable.*reload/);
 await route('network');assert.equal(await ev('document.documentElement.dataset.theme'),'dark');await reload();assert.equal(await ev('document.documentElement.dataset.theme'),'light');
 await send('Page.removeScriptToEvaluateOnNewDocument',{identifier:writeFault.identifier});
 const readFault=await send('Page.addScriptToEvaluateOnNewDocument',{source:`const original=Storage.prototype.getItem;window.fixtureReadAppearance=()=>original.call(localStorage,'sv08.appearance');Storage.prototype.getItem=function(key){if(key==='sv08.appearance')throw Error('Injected denied appearance storage');return original.call(this,key);};`});
 await reload();await route('settings');assert.match(await ev("document.getElementById('appearance-status').textContent"),/storage is unavailable/);
 await choose('dark');assert.match(await ev("document.getElementById('appearance-status').textContent"),/could not be read.*may reset.*reload/);
 assert.equal(await ev('window.fixtureReadAppearance()'),'dark','Read denial does not imply write denial; feedback stays honest after a successful write');
 await route('network');assert.equal(await ev('document.documentElement.dataset.theme'),'dark');await route('settings');await capture('storage-unavailable','#appearance');
 await reload();assert.equal(await ev('document.documentElement.dataset.theme'),'light');
 await send('Page.removeScriptToEvaluateOnNewDocument',{identifier:readFault.identifier});
 await noMutations();assert.deepEqual(errors,[]);results.checks.push('appearance-key read and write storage faults: honest feedback, navigation works, reload resets safely');
 // Representative clean factory state after the adversarial dirty-draft journey.
 await reload();await choose('dark');await route('printer');
 await capture('dark-hardware-ready');await readable(['#printer .printer-card strong','#printer .printer-card small','#printer .printer-status']);
 await route('network');await capture('dark-network-ready');await route('printer-connections');await capture('dark-graph-ready','#printer-connection-map');
 await noMutations();
 results.result='pass';fs.writeFileSync(output+'/results.json',JSON.stringify(results,null,2)+'\n');
} catch(error) {
 fs.writeFileSync(output+'/results.json',JSON.stringify({...results,result:'fail',error:String(error.stack??error)},null,2)+'\n');throw error;
} finally {socket?.close();await browser.stop();}
