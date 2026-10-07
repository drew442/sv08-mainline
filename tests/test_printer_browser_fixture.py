"""Loopback Cockpit transport/session shim and actual disposable Store/Budget.

This is browser fixture evidence, never authenticated Cockpit/ARM64 evidence.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import base64
import hashlib
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from stage_printer_ui import compose_host
from definition_repository_template import archive, FILENAME
from sv08_state import Store
from sv08_data_budget import Budget
from sv08_printer_catalog import Catalog, strict_json
from sv08_printer_store import PrinterStore

ROOT=Path(__file__).resolve().parents[1]
SHIM=r'''
(()=>{
 const client=new EventTarget(),proxy=new EventTarget();
 Object.assign(proxy,{valid:true,Current:'none',Bridges:['sudo'],wait:cb=>cb()});
 const change=async current=>{await fetch('/authority',{method:'POST',body:JSON.stringify({elevated:current==='sudo'})});proxy.Current=current;proxy.dispatchEvent(new Event('changed'));};
 Object.assign(proxy,{Start:()=>change('sudo'),Answer:()=>{},Stop:()=>change('none')});
 client.proxy=()=>proxy;
 window.fixtureDisconnect=async()=>{await change('none');client.dispatchEvent(new Event('close'));};
 window.fixtureUnsupported=null;window.fixtureLoseAck=false;window.fixtureHoldApply=false;window.fixtureApplyWaiting=false;
 window.fixtureHoldStatus=false;window.fixtureStatusWaiting=false;
 window.fixtureHoldReview=false;window.fixtureReviewWaiting=false;window.fixtureHostFailure=false;window.fixtureHostCalls=[];window.fixtureHostHold=null;
 const hostState={fixture:true,boot:{release:'offline',slot:'A',mode:'immutable',customized:false},free_bytes:1073741824,slots:{A:{release:'offline',customized:false},B:null},auto_update:false,requested_mode:'immutable',hostname:'fixture',images:[],catalog:[],capabilities:Object.fromEntries(['policy.auto','policy.mode','image.stage','image.arm','image.cancel','config.hostname','software.install','software.remove'].map(k=>[k,{available:true}]))};
 function hostReply(message){
  window.fixtureHostCalls.push(message);
  if(window.fixtureHostFailure)throw Error('Injected host refresh failure');
  if(message.method==='jobs')return {jobs:[],blocked:false,capacity:128,remaining:128,maintenance_available:false};
  if(message.method==='status')return hostState;
  if(message.method==='upload.list')return {objects:[],busy:false,message:'Offline upload fixture'};
  if(message.method==='upload.plan')return {object:{bytes:message.size},name:message.name};
  if(message.method==='plan')return {title:'Offline host review',effect:'Fixture only',arguments:message.arguments,action:message.action};
  throw Error('Unassigned host fixture operation '+message.method);
 }
 window.fixtureRequests=[];window.fixtureLoadedIdentity=null;
 window.cockpit={dbus:()=>client,logout:()=>{void change('none');document.body.dataset.loggedOut='true';},spawn:(argv,options)=>{
   const host=argv[1]==='/usr/lib/sv08/sv08_admin.py';
   if(!host && argv[1]!=='/usr/lib/sv08/sv08_printer_helper.py')throw Error('Unexpected fixture helper invocation');
   let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});
   promise.input=data=>{if(host){try{const message=JSON.parse(data),result=hostReply(message),raw=JSON.stringify({ok:true,result});if(window.fixtureHostHold===message.method){window.fixtureHostWaiting=true;window.fixtureHostRelease=()=>{window.fixtureHostWaiting=false;window.fixtureHostHold=null;resolve(raw);};}else resolve(raw);}catch(error){reject(error);}return promise;}window.fixtureRequests.push({request:JSON.parse(data),loaded:window.fixtureLoadedIdentity});fetch('/request',{method:'POST',body:data}).then(r=>r.text()).then(raw=>{const reply=JSON.parse(raw);if(JSON.parse(data).action==='status'&&reply.ok&&window.fixtureUnsupported){if(window.fixtureUnsupported==='catalog')reply.result.catalog_supported=false;else if(window.fixtureUnsupported==='state')reply.result.state.format_version=99;else reply.result.state.draft.format_version=99;raw=JSON.stringify(reply);}if(JSON.parse(data).action==='status'&&reply.ok)window.fixtureLoadedIdentity=reply.result.loaded_identity;if(window.fixtureHoldStatus&&JSON.parse(data).action==='status'){window.fixtureStatusWaiting=true;window.fixtureReleaseStatus=()=>{window.fixtureHoldStatus=false;window.fixtureStatusWaiting=false;resolve(raw);};return;}if(window.fixtureHoldReview&&JSON.parse(data).action==='review'){window.fixtureReviewWaiting=true;window.fixtureReleaseReview=()=>{window.fixtureHoldReview=false;window.fixtureReviewWaiting=false;resolve(raw);};return;}if(window.fixtureHoldApply&&JSON.parse(data).action==='apply'){window.fixtureApplyWaiting=true;window.fixtureReleaseApply=()=>{window.fixtureHoldApply=false;window.fixtureApplyWaiting=false;reject(Error('Injected lost acknowledgment after submitted apply'));};return;}if(window.fixtureLoseAck&&JSON.parse(data).action==='apply'){window.fixtureLoseAck=false;reject(Error('Injected lost acknowledgment'));}else resolve(raw);},reject);return promise;};return promise;
 }};
})();
'''


def serve(work):
    work.mkdir(mode=0o700)
    data=work/'data';budget=Budget(data,state_reserve=0,copy_limit=8*1024*1024,staging_reserve=0)
    store=Store(data,reserve_bytes=0,copy_limit_bytes=8*1024*1024,budget=budget)
    store.initialize();boot=store.prepare_boot('A','browser-fixture');boot['boot_id']='browser-fixture'
    bootfile=work/'boot.json';bootfile.write_text(json.dumps(boot));view=work/'config-view';view.symlink_to(Path(boot['generation'])/'config')
    authority={'elevated':False}
    compact=dict(id='funssor-cn3d-hotbed',name='Funssor CN3D heated bed',version='1.0.0',extends='sv08.factory.hotbed',heater_bed={'max_temp':120})
    compact_raw=json.dumps(compact).encode();manifest=dict(format_version='0.1',catalog_id='compact-fixture',name='Compact modder fixture',publisher={'name':'Fixture'},license='GPL-3.0-or-later',definitions=[dict(id=compact['id'],version=compact['version'],path='definitions/bed.json',sha256=hashlib.sha256(compact_raw).hexdigest())]);manifest_raw=json.dumps(manifest).encode()
    def source_fetch(path):
        bad='/bad-mode' in path
        root='/repos/fixture/'+('bad-mode' if bad else 'compact-mods');commit='b'*40
        responses={root:dict(id=19 if bad else 18,default_branch='main',full_name='fixture/'+('bad-mode' if bad else 'compact-mods'),private=False),root+'/commits/main':dict(sha=commit),root+'/commits/'+commit:dict(sha=commit),root+'/git/commits/'+commit:dict(tree={'sha':'root'}),root+'/git/trees/root':dict(tree=[dict(path='catalog.json',mode='100755' if bad else '100644',type='blob',sha='manifest',size=len(manifest_raw)),dict(path='definitions',mode='040000',type='tree',sha='defs')]),root+'/git/trees/defs':dict(tree=[dict(path='bed.json',mode='100644',type='blob',sha='bed',size=len(compact_raw))]),root+'/git/blobs/manifest':dict(encoding='base64',size=len(manifest_raw),content=base64.b64encode(manifest_raw).decode()),root+'/git/blobs/bed':dict(encoding='base64',size=len(compact_raw),content=base64.b64encode(compact_raw).decode())}
        if path not in responses:raise ValueError('Unexpected fixture source path')
        return responses[path]
    service=PrinterStore(store,bootfile,view,Catalog(ROOT/'catalog/printer/catalog.json'),privileged=lambda:authority['elevated'],source_fetch=source_fetch)
    # Guards demonstrate that browser save/apply never change unrelated files.
    live=Path(boot['generation'])/'config/printer.cfg';live.write_text('# Existing manual live config, untouched\n')
    (work/'original-live.txt').write_bytes(live.read_bytes())
    (work/'fixture.json').write_text(json.dumps(dict(generation=boot['generation'],state=str(Path(boot['generation'])/'config/printer-hardware/state.json'))))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def response(self,body,kind='application/json'):
            if isinstance(body,str):body=body.encode()
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path.endswith('/base1/cockpit.js'):return self.response(SHIM,'text/javascript')
            package='sv08-host' if '/sv08-host/' in self.path else 'sv08-printer'
            name=self.path.rsplit('/',1)[-1]
            if package=='sv08-printer' and name==FILENAME:return self.response(archive(ROOT),'application/zip')
            if name not in ('index.html','app.js','style.css','session.js','manifest.json','upload.js','navigation.js','redirect.js'):return self.send_error(404)
            path=ROOT/'ui'/('host' if package=='sv08-host' else 'printer')/name
            raw=path.read_bytes()
            if package=='sv08-host' and name=='index.html':
                raw=compose_host(raw)
            self.response(raw,'text/html' if name.endswith('.html') else 'text/css' if name.endswith('.css') else 'text/javascript')
        def do_POST(self):
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=786432:raise ValueError('Fixture input size bound')
                request=strict_json(self.rfile.read(size),786432)
                if self.path=='/authority':
                    if set(request)!={'elevated'} or type(request['elevated']) is not bool:raise ValueError('Invalid fixture authority')
                    authority.update(request);result={}
                elif self.path=='/swap-generation':
                    if request!={}:raise ValueError('Invalid fixture swap')
                    copied=store.prepare_boot('B','browser-fixture')
                    bootfile.write_text(json.dumps(copied));view.unlink();view.symlink_to(Path(copied['generation'])/'config')
                    result=dict(generation=copied['generation'],state=str(Path(copied['generation'])/'config/printer-hardware/state.json'))
                    (work/'fixture.json').write_text(json.dumps(result))
                elif self.path=='/request':result=service.request(request)
                else:raise ValueError('Unknown fixture route')
                self.response(json.dumps(dict(ok=True,result=result)))
            except (ValueError,OSError,KeyError,TypeError) as error:self.response(json.dumps(dict(ok=False,error=str(error))))
    with ThreadingHTTPServer(('127.0.0.1',0),Handler) as server:
        (work/'server.json').write_text(json.dumps(dict(url=f'http://127.0.0.1:{server.server_port}')))
        server.serve_forever()


if __name__=='__main__':serve(Path(sys.argv[1]))
