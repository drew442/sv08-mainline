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
  await until('!document.querySelector("#review-upload").disabled && !uploadActive && document.querySelector("#bundle-file").files.length===1');
 };
 let cleanupReviewSequence=0;
 const remove=async()=>{
  await ev('uploadListing()');await until('document.querySelector("#upload-list button") && !document.querySelector("#upload-list button").disabled');
  await openUploadReview('cleanup-'+(++cleanupReviewSequence),undefined,true);
  // close() dispatches its handler asynchronously; inactive alone can precede
  // cleanup. Discard stale feedback, then require this removal's acknowledgement
  // and the refreshed empty listing before inspecting the actual helper outcome.
  await ev('document.querySelector("#upload-status").textContent=""');
  await click('#confirm-upload');
  try{
   await until('!uploadActive && document.querySelector("#upload-status").textContent==="Reviewed managed upload removed. No transaction was cancelled." && document.querySelector("#upload-list").children.length===0');
  }catch{
   const diagnostic=await ev('({active:uploadActive,review_open:document.querySelector("#upload-review").open,rendered_objects:document.querySelector("#upload-list").children.length,status:document.querySelector("#upload-status").textContent.replace(/[\\u0000-\\u001f\\u007f]/g," ").slice(0,512)})');
   fs.writeFileSync(W+'/upload-cleanup-error.json',JSON.stringify(diagnostic,null,2)+'\n',{mode:0o600});
   throw Error('Reviewed upload cleanup did not reach acknowledged removal and an empty rendered listing; inspect upload-cleanup-error.json');
  }
  const removed=await helper({method:'upload.list'});assert.equal(removed.ok,true,'Post-cleanup managed listing must succeed');
  assert.equal(removed.result.objects.length,0);
 };
 // Observe each real upload review boundary; no extra RPC or replay.
 // Retain source-literal public errors only; unknown text is withheld so this
 // diagnostic never copies credentials, request bodies or entire plans.
 const publicMessages=new Set();
 for(const source of ['../runtime/sv08_admin.py','../runtime/sv08_staging.py','../runtime/sv08_state.py','../runtime/sv08_data_budget.py','../ui/host/app.js']){
  const body=fs.readFileSync(new URL(source,import.meta.url),'utf8');
  for(const match of body.matchAll(/(?:Error|ValueError|BusyError)\('([^'\n]+)'\)/g))publicMessages.add(match[1]);
 }
 const installPlanObserver=messages=>{
  const original=request,allowed=new Set(messages);
  const sanitize=value=>typeof value==='string'&&allowed.has(value)?value.slice(0,512):value?'Unrecognized public message withheld.':'';
  const records=[];
  const wrapped=function(...args){
   const promise=original.apply(this,args);
   if(['upload.plan','upload.cleanup-plan','status'].includes(args[0]?.method)){
    const record={method:args[0].method,sequence:records.length+1,completed:false,authority_generation:authorityGeneration};records.push(record);
    promise.then(()=>{record.completed=true;record.ok=true;},error=>{record.completed=true;record.ok=false;record.error={message:sanitize(error?.message),acknowledged:error?.acknowledged===true,exit_status:Number.isInteger(error?.exit_status)?error.exit_status:null,problem:['access-denied','disconnected','terminated','timeout','not-found'].includes(error?.problem)?error.problem:null};});
   }
   return promise;
  };
  request=wrapped;
  window.pr9UploadReviewProbe={snapshot:()=>({status:sanitize(document.querySelector('#upload-status').textContent),storage_status:sanitize(document.querySelector('#upload-storage').textContent),button_disabled:document.querySelector('#review-upload').disabled,cleanup_button_disabled:document.querySelector('#upload-list button')?.disabled??true,file_selected:document.querySelector('#bundle-file').files.length===1,file_bytes:document.querySelector('#bundle-file').files[0]?.size??null,upload_active:uploadActive,dialog_open:document.querySelector('#upload-review').open,authority_generation:authorityGeneration,elevated:sv08Session.elevated===true,plan_reads:records.filter(record=>['upload.plan','upload.cleanup-plan'].includes(record.method)).slice(-4),refresh_reads:records.filter(record=>record.method==='status').slice(-4)}),restore:()=>{if(request!==wrapped)throw Error('Upload request observer ownership changed');request=original;delete window.pr9UploadReviewProbe;}};
 };
 const openUploadReview=async(label,selected,cleanup=false)=>{
  const method=cleanup?'upload.cleanup-plan':'upload.plan',selector=cleanup?'#upload-list button':'#review-upload';
  await ev(`(${installPlanObserver.toString()})(${JSON.stringify([...publicMessages])})`);
  let recovery=null;
  try{
   if(selected)await choose(selected);
   await until(`!!document.querySelector(${JSON.stringify(selector)}) && !document.querySelector(${JSON.stringify(selector)}).disabled && !uploadActive ${cleanup?'':'&& document.querySelector("#bundle-file").files.length===1'}`);
   const beforeHash=await stateHash(),beforeList=await helper({method:'upload.list'});
   assert.equal(beforeList.ok,true,'Pre-review managed listing must succeed');
   const start=await ev('window.pr9UploadReviewProbe.snapshot()');
   const reviewOnce=async()=>{
    const previous=await ev('window.pr9UploadReviewProbe.snapshot().plan_reads.at(-1)?.sequence??0');
    await click(selector);
    await until(`(()=>{const p=window.pr9UploadReviewProbe.snapshot().plan_reads.at(-1);return p?.sequence>${previous}&&p.completed})()`);
    return ev('window.pr9UploadReviewProbe.snapshot()');
   };
   let outcome=await reviewOnce(),plan=outcome.plan_reads.at(-1);
   assert.equal(plan.method,method,'Observed the selected review operation');
   if(plan.ok!==true){
    const busyMessage='System state is busy. Image job progress remains available; refresh shortly.';
    assert.equal(plan.error?.acknowledged,true,'Only an acknowledged refusal permits explicit recovery');
    assert.equal(plan.error?.message,busyMessage,'Unexpected upload-plan refusal');
    assert.equal(outcome.status,busyMessage,'Busy refusal must be visible');
    assert.equal(plan.authority_generation,start.authority_generation,'Refusal generation must remain current');
    assert.equal(outcome.authority_generation,start.authority_generation,'Authority changed during review');
    assert.equal(outcome.elevated,true);assert.equal(outcome.dialog_open,false);assert.equal(outcome.upload_active,false);
    recovery={refusal:outcome,explicit_refresh:false,state_unchanged:false,objects_unchanged:false};
    assert.equal(await stateHash(),beforeHash,'Busy refusal changed persistent state');recovery.state_unchanged=true;
    const afterList=await helper({method:'upload.list'});assert.equal(afterList.ok,true,'Post-refusal managed listing must succeed');
    assert.deepEqual(afterList.result.objects,beforeList.result.objects,'Busy refusal changed managed uploads');recovery.objects_unchanged=true;
    const refreshCheckpoint=await ev('window.pr9UploadReviewProbe.snapshot().refresh_reads.at(-1)?.sequence??0');
    recovery.explicit_refresh=true;await click('#refresh');
    await until(`(()=>{const s=window.pr9UploadReviewProbe.snapshot(),r=s.refresh_reads.at(-1);return r?.sequence>${refreshCheckpoint}&&r.completed&&r.ok===true&&r.authority_generation===${start.authority_generation}&&s.authority_generation===${start.authority_generation}&&s.elevated&&!s.${cleanup?'cleanup_button_disabled':'button_disabled'}&&!refreshing&&document.querySelector('#connection').textContent==='Host connected'})()`);
    recovery.refresh=await ev('window.pr9UploadReviewProbe.snapshot()');
    outcome=await reviewOnce();plan=outcome.plan_reads.at(-1);
    assert.equal(plan.method,method,'Recovery must review the same operation');
    assert.equal(plan.ok,true,'Second review must succeed; no further recovery');
    recovery.review=outcome;
   }
   assert.equal(plan.ok,true,'Actual upload plan must succeed');
   assert.equal(plan.authority_generation,start.authority_generation,'Review generation must remain current');
   assert.equal(outcome.authority_generation,start.authority_generation,'Review authority changed');
   await until('document.querySelector("#upload-review").open');
  }finally{
   const diagnostic=await ev('window.pr9UploadReviewProbe.snapshot()');
   if(recovery)diagnostic.busy_refusal_recovery=recovery;
   fs.writeFileSync(W+'/'+label+'-upload-review.json',JSON.stringify(diagnostic,null,2)+'\n',{mode:0o600});
   (results.upload_reviews??={})[label]=diagnostic;
   if(label==='initial')results.initial_upload_review=diagnostic;
   await ev('window.pr9UploadReviewProbe.restore()');
  }
 };
 const prior=(await helper({method:'upload.list'})).result.objects;
 if(prior.length){await remove();results.prior_fixture_object_removed_by_explicit_review=true;}
 await openUploadReview('initial',file);
 await ev('document.querySelector("#upload-review").close("cancel")');
 assert.equal((await helper({method:'upload.list'})).result.objects.length,0);results.review_cancel_no_transfer=true;
 await openUploadReview('normal');await click('#confirm-upload');
 await until('!uploadActive && document.querySelector("#upload-status").textContent.includes("SHA-256:")');
 const message=await ev('document.querySelector("#upload-status").textContent');assert.match(message,/Full payload verification occurs during installation/);
 assert.equal(await ev('document.querySelector("#upload-progress").value'),1);
 const published=(await helper({method:'upload.list'})).result.objects[0];assert.equal(published.mode&511,256);assert.equal(published.bytes,fs.statSync(file).size);
 assert.equal(await stateHash(),original);results.normal_review_progress_private_publish=true;console.log('signed upload and private publication PASS');results.manifest_result=message;
 await ev('uploadListing()');await openUploadReview('cleanup-cancel',undefined,true);
 await ev('document.querySelector("#upload-review").close("cancel")');assert.equal((await helper({method:'upload.list'})).result.objects.length,1);results.cleanup_cancel_preserves=true;
 await remove();
 const corrupt=W+'/corrupt.raucb';const bytes=fs.readFileSync(file);bytes[bytes.length-100]^=1;fs.writeFileSync(corrupt,bytes);
 await openUploadReview('corrupt',corrupt);await click('#confirm-upload');
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
 const start=Date.now();
 const responsiveResult=(response,operation)=>{
  if(response?.ok!==true){
   const message=typeof response?.error==='string'&&publicMessages.has(response.error)?response.error.slice(0,512):'Unrecognized public helper error withheld.';
   const diagnostic={operation,ok:response?.ok===true,message,elapsed_ms:Date.now()-start};
   fs.writeFileSync(W+'/paused-upload-helper-error.json',JSON.stringify(diagnostic,null,2)+'\n',{mode:0o600});
  }
  assert.equal(response?.ok,true,operation+' failed during paused upload; inspect paused-upload-helper-error.json');
  return response.result;
 };
 responsiveResult(await helper({method:'status'}),'status');responsiveResult(await helper({method:'jobs'}),'jobs');
 const policy=await helper({method:'plan',action:'policy.auto',arguments:{enabled:false}});responsiveResult(policy,'policy.auto plan');
 responsiveResult(await helper({method:'apply',plan:policy.result}),'policy.auto apply');assert(Date.now()-start<10000);
 assert.equal((await helper({method:'upload.plan',name:'second',size:70000})).ok,false);
 const partial=(await helper({method:'upload.list'})).result.objects[0];assert.equal((await helper({method:'upload.cleanup-plan',name:partial.name})).ok,false);
 results.paused_responsive_exclusion=true;console.log('paused real helper responsiveness PASS');
 await ev('paused.close("terminated");void 0');await until(`request({method:'upload.list'}).then(x=>!x.busy)`);
 const afterCancel=(await helper({method:'upload.list'})).result;results.cancellation_observed_objects=afterCancel.objects.length;
 if(afterCancel.objects.length)await remove();
 // UI cancellation using a large synthetic File whose first slice is held.
 await ev(`window.originalSlice=File.prototype.slice;File.prototype.slice=function(...args){const blob=originalSlice.apply(this,args);return {arrayBuffer:()=>new Promise(resolve=>window.releaseSlice=()=>resolve(blob.arrayBuffer()))};}`);
 await openUploadReview('cancellation',file);await click('#confirm-upload');await until('uploadActive && !!window.releaseSlice');await click('#cancel-upload');await until('!uploadActive');
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
 await openUploadReview('lost-completion',file);await click('#confirm-upload');await until('!uploadActive && document.querySelector("#upload-status").textContent.includes("Completion not acknowledged")');
 assert.equal((await helper({method:'upload.list'})).result.objects.length,1);
 await loadShell();if(!await ev('sv08Session.elevated'))await authorize();await delay(500);
 assert.equal(await ev('uploadActive'),false);assert.equal((await helper({method:'upload.list'})).result.objects.length,1);results.lost_completion_reconnect_no_replay=true;await remove();
 const restore=await helper({method:'plan',action:'policy.auto',arguments:{enabled:true}});assert.equal((await helper({method:'apply',plan:restore.result})).ok,true);
 assert.equal(await stateHash(),original);results.no_upload_slot_boot_or_state_mutation=true;
 return results;
}
