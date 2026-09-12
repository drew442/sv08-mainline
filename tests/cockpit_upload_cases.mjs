import fs from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {setTimeout as delay} from 'node:timers/promises';
export async function uploadCases({W,ev,send,until,click,helper,stateHash,loadShell,authorize}) {
 const results={real_signature_tool:'guest /usr/bin/rauc 1.13', hardware:false, slot_adapter:false};
 const sources=['sv08_admin_upload.py','sv08_admin.py','sv08_admin_images.py','sv08_staging.py','sv08_bundle.py','sv08_boot.py','sv08_rauc.py'];
 const installed=[...sources.map(name=>'/usr/lib/sv08/'+name),'/usr/share/cockpit/sv08-host/upload.js'];
 const hashes=await ev(`cockpit.spawn(['/usr/bin/sha256sum',...${JSON.stringify(installed)}],{superuser:'require'}).then(x=>x)`);
 results.installed_sources={};
 for(const line of hashes.trim().split('\n')){const [hash,target]=line.split(/\s+/);const local=target.endsWith('/upload.js')?'../ui/host/upload.js':'../runtime/'+target.split('/').at(-1);assert.equal(hash,createHash('sha256').update(fs.readFileSync(new URL(local,import.meta.url))).digest('hex'));results.installed_sources[target]=hash;}
 const file=W+'/signed.raucb';
 const original=await stateHash();
 const choose=async(selected=file)=>{
  await click('[data-page="images"]');
  const doc=await send('DOM.getDocument');const found=await send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'#bundle-file'});
  await send('DOM.setFileInputFiles',{nodeId:found.nodeId,files:[selected]});
 };
 const remove=async()=>{
  await ev('uploadListing()');await until('document.querySelector("#upload-list button") && !document.querySelector("#upload-list button").disabled');
  await click('#upload-list button');await until('document.querySelector("#upload-review").open');
  await click('#confirm-upload');await until('!uploadActive');
  assert.equal((await helper({method:'upload.list'})).result.objects.length,0);
 };
 const prior=(await helper({method:'upload.list'})).result.objects;
 if(prior.length){await remove();results.prior_fixture_object_removed_by_explicit_review=true;}
 await choose();await click('#review-upload');await until('document.querySelector("#upload-review").open');
 await ev('document.querySelector("#upload-review").close("cancel")');
 assert.equal((await helper({method:'upload.list'})).result.objects.length,0);results.review_cancel_no_transfer=true;
 await click('#review-upload');await until('document.querySelector("#upload-review").open');await click('#confirm-upload');
 await until('!uploadActive && document.querySelector("#upload-status").textContent.includes("SHA-256:")');
 const message=await ev('document.querySelector("#upload-status").textContent');assert.match(message,/Full payload verification occurs during installation/);
 assert.equal(await ev('document.querySelector("#upload-progress").value'),1);
 const published=(await helper({method:'upload.list'})).result.objects[0];assert.equal(published.mode&511,256);assert.equal(published.bytes,fs.statSync(file).size);
 assert.equal(await stateHash(),original);results.normal_review_progress_private_publish=true;console.log('signed upload and private publication PASS');results.manifest_result=message;
 await ev('uploadListing()');await click('#upload-list button');await until('document.querySelector("#upload-review").open');
 await ev('document.querySelector("#upload-review").close("cancel")');assert.equal((await helper({method:'upload.list'})).result.objects.length,1);results.cleanup_cancel_preserves=true;
 await remove();
 const corrupt=W+'/corrupt.raucb';const bytes=fs.readFileSync(file);bytes[bytes.length-100]^=1;fs.writeFileSync(corrupt,bytes);
 await choose(corrupt);await click('#review-upload');await until('document.querySelector("#upload-review").open');await click('#confirm-upload');
 await until('!uploadActive && document.querySelector("#upload-status").textContent.includes("authentication failed")');
 assert.equal((await helper({method:'upload.list'})).result.objects.length,0);results.real_signature_failure_no_publication=true;fs.unlinkSync(corrupt);
 // Pause real helper before its first chunk; this is an explicit transport fault,
 // not a replacement signature/authentication implementation.
 const pause=async()=>{
  const plan=await helper({method:'upload.plan',name:'paused.raucb',size:70000});assert.equal(plan.ok,true);
  await ev(`window.paused=cockpit.spawn(['/usr/bin/python3','/usr/lib/sv08/sv08_admin_upload.py'],{superuser:'require',binary:true,err:'message'});window.pausedLines='';paused.stream(x=>{window.pausedLines+=new TextDecoder().decode(new Uint8Array(x))});paused.catch(()=>{});paused.input(new TextEncoder().encode(${JSON.stringify(JSON.stringify(plan.result)+'\n')}),true);void 0`);
  await until('window.pausedLines.includes("ready")');
  await until(`request({method:'upload.list'}).then(x=>x.busy && x.objects.length===1)`);
 };
 await pause();
 const start=Date.now();assert.equal((await helper({method:'status'})).ok,true);assert.equal((await helper({method:'jobs'})).ok,true);
 const policy=await helper({method:'plan',action:'policy.auto',arguments:{enabled:false}});assert.equal((await helper({method:'apply',plan:policy.result})).ok,true);assert(Date.now()-start<10000);
 assert.equal((await helper({method:'upload.plan',name:'second',size:70000})).ok,false);
 const partial=(await helper({method:'upload.list'})).result.objects[0];assert.equal((await helper({method:'upload.cleanup-plan',name:partial.name})).ok,false);
 results.paused_responsive_exclusion=true;console.log('paused real helper responsiveness PASS');
 await ev('paused.close("terminated");void 0');await until(`request({method:'upload.list'}).then(x=>!x.busy)`);
 const afterCancel=(await helper({method:'upload.list'})).result;results.cancellation_observed_objects=afterCancel.objects.length;
 if(afterCancel.objects.length)await remove();
 // UI cancellation using a large synthetic File whose first slice is held.
 await ev(`window.originalSlice=File.prototype.slice;File.prototype.slice=function(...args){const blob=originalSlice.apply(this,args);return {arrayBuffer:()=>new Promise(resolve=>window.releaseSlice=()=>resolve(blob.arrayBuffer()))};}`);
 await choose();await click('#review-upload');await until('document.querySelector("#upload-review").open');await click('#confirm-upload');await until('uploadActive && !!window.releaseSlice');await click('#cancel-upload');await until('!uploadActive');
 await ev('File.prototype.slice=window.originalSlice;window.releaseSlice()');await until(`request({method:'upload.list'}).then(x=>!x.busy)`);
 if((await helper({method:'upload.list'})).result.objects.length)await remove();results.browser_cancel=true;console.log('browser cancellation PASS');
 // SIGKILL leaves the current unpublished partial for explicit exact-object removal.
 await pause();
 const killCode = `import os,pathlib,signal
count=0
for entry in pathlib.Path('/proc').iterdir():
 if not entry.name.isdigit():continue
 try:
  args=(entry/'cmdline').read_bytes().split(bytes([0]))
  if args[:2]==[b'/usr/bin/python3',b'/usr/lib/sv08/sv08_admin_upload.py']:
   os.kill(int(entry.name),signal.SIGKILL);count+=1
 except OSError:pass
print(count)
`;
 const kill=await ev(`cockpit.spawn(['/usr/bin/python3','-c',${JSON.stringify(killCode)}],{superuser:'require',err:'message'}).then(x=>x.trim(),e=>({error:e.message}))`);assert.equal(kill,'1');
 await loadShell();if(!await ev('sv08Session.elevated'))await authorize();
 const lost=(await helper({method:'upload.list'})).result;assert.equal(lost.busy,false);assert.equal(lost.objects.length,1);assert.match(lost.objects[0].state,/interrupted/);results.process_death_reconnect_retained_partial=true;await remove();
 // Filter only the final real response to model lost completion ACK. Every byte
 // still traverses the real bridge and the real verifier publishes privately.
 await ev(`window.actualSpawn=cockpit.spawn;cockpit.spawn=function(argv,options){const p=actualSpawn(argv,options);if(argv[1]==='/usr/lib/sv08/sv08_admin_upload.py'){const stream=p.stream; p.stream=function(cb){let pending='';return stream.call(p,x=>{pending+=new TextDecoder().decode(new Uint8Array(x));let n;while((n=pending.indexOf('\\n'))>=0){const line=pending.slice(0,n+1);pending=pending.slice(n+1);if(JSON.parse(line).type!=='complete')cb(new TextEncoder().encode(line));}})}}return p;}`);
 await choose();await click('#review-upload');await until('document.querySelector("#upload-review").open');await click('#confirm-upload');await until('!uploadActive && document.querySelector("#upload-status").textContent.includes("Completion not acknowledged")');
 assert.equal((await helper({method:'upload.list'})).result.objects.length,1);
 await loadShell();if(!await ev('sv08Session.elevated'))await authorize();await delay(500);
 assert.equal(await ev('uploadActive'),false);assert.equal((await helper({method:'upload.list'})).result.objects.length,1);results.lost_completion_reconnect_no_replay=true;await remove();
 const restore=await helper({method:'plan',action:'policy.auto',arguments:{enabled:true}});assert.equal((await helper({method:'apply',plan:restore.result})).ok,true);
 assert.equal(await stateHash(),original);results.no_upload_slot_boot_or_state_mutation=true;
 return results;
}
