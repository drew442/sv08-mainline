import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
async function run(fault) {
 const elements=new Map();const el=id=>{if(!elements.has(id))elements.set(id,{textContent:'',value:0,addEventListener(){}});return elements.get(id)};
 let stream, queued=0, total=0, closed=false, slices=0, maxSlice=0, outstanding=0, maxOutstanding=0;
 const done={};const promise=new Promise((resolve,reject)=>Object.assign(done,{resolve,reject}));
 const send=record=>{const bytes=new TextEncoder().encode(JSON.stringify(record)+'\n');for(let i=0;i<bytes.length;i+=3)stream(bytes.slice(i,i+3))};
 promise.stream=fn=>{stream=fn;return promise};promise.close=()=>{closed=true;done.reject(Error('closed'))};
 promise.input=(data,keep)=>{
  if(closed)return promise;
  if(data===null){queueMicrotask(()=>{send({type:'complete',result:{proof:{full_payload_verified:false}}});if(fault==='truncated-utf8')stream(new Uint8Array([0xc3]));done.resolve()});return promise}
  if(!queued++){queueMicrotask(()=>send({type:'ready',chunk:65536}));return promise}
  total+=data.length;outstanding+=data.length;maxOutstanding=Math.max(maxOutstanding,outstanding);
  queueMicrotask(()=>{
   if(fault==='malformed'){stream(new TextEncoder().encode('{bad}\n'));return}
   if(fault==='oversized'){stream(new Uint8Array(16385).fill(120));return}
   outstanding=0;send({type:'ack',received:fault==='wrong-offset'?total+1:total});
  });return promise;
 };
 const context=vm.createContext({$:el,window:{addEventListener(){}},cockpit:{spawn(argv,opts){assert.deepEqual(Array.from(argv),['/usr/bin/python3','/usr/lib/sv08/sv08_admin_upload.py']);assert.equal(opts.binary,true);return promise}},TextEncoder,TextDecoder,Uint8Array,Error,JSON,Number,Promise,setTimeout,clearTimeout,setInterval(){},authorityGeneration:0});
 vm.runInContext(fs.readFileSync(new URL('../ui/host/upload.js',import.meta.url),'utf8'),context);
 context.file={size:3*65536+1,slice(start,end){slices++;maxSlice=Math.max(maxSlice,end-start);return{async arrayBuffer(){return new ArrayBuffer(end-start)}}}};
 const result=vm.runInContext('transferBundle(file,{name:"fixture",size:file.size})',context);
 if(fault)await assert.rejects(result);else{await result;assert.equal(slices,4);assert.equal(total,context.file.size);assert(maxSlice<=65536);assert(maxOutstanding<=65536)}
 return {fault:fault||'fragmented-valid',slices,maxSlice,maxOutstanding};
}
console.log(JSON.stringify({passed:await Promise.all([run(),run('malformed'),run('oversized'),run('wrong-offset'),run('truncated-utf8')]),scope:'Node VM transport algorithm; no authentication or RAUC substitution evidence'}));
