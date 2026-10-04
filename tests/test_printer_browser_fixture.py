"""Loopback Cockpit transport/session shim and actual disposable Store/Budget.

This is browser fixture evidence, never authenticated Cockpit/ARM64 evidence.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
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
 window.fixtureLoseAck=false;
 window.fixtureRequests=[];window.fixtureLoadedIdentity=null;
 window.cockpit={dbus:()=>client,logout:()=>{void change('none');document.body.dataset.loggedOut='true';},spawn:(argv,options)=>{
   if(JSON.stringify(argv)!==JSON.stringify(['/usr/bin/python3','/usr/lib/sv08/sv08_printer_helper.py'])||options.superuser!=='require')throw Error('Unexpected fixture helper invocation');
   let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});
   promise.input=data=>{window.fixtureRequests.push({request:JSON.parse(data),loaded:window.fixtureLoadedIdentity});fetch('/request',{method:'POST',body:data}).then(r=>r.text()).then(raw=>{const reply=JSON.parse(raw);if(JSON.parse(data).action==='status'&&reply.ok)window.fixtureLoadedIdentity=reply.result.loaded_identity;if(window.fixtureLoseAck&&JSON.parse(data).action==='apply'){window.fixtureLoseAck=false;reject(Error('Injected lost acknowledgment'));}else resolve(raw);},reject);};return promise;
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
    service=PrinterStore(store,bootfile,view,Catalog(ROOT/'catalog/printer/catalog.json'),privileged=lambda:authority['elevated'])
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
            if name not in ('index.html','app.js','style.css','session.js','manifest.json','upload.js'):return self.send_error(404)
            path=ROOT/'ui'/('host' if package=='sv08-host' else 'printer')/name
            raw=path.read_bytes()
            if package=='sv08-host' and name=='index.html':
                # Navigation fixture: existing host operation implementation has its
                # own tests. Do not submit unrelated host RPC to printer controller.
                raw=raw.replace(b'<script defer src="app.js"></script>',b'').replace(b'<script defer src="upload.js"></script>',b'')
            self.response(raw,'text/html' if name.endswith('.html') else 'text/css' if name.endswith('.css') else 'text/javascript')
        def do_POST(self):
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=135168:raise ValueError('Fixture input size bound')
                request=strict_json(self.rfile.read(size),135168)
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
