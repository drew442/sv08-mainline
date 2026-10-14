# SPDX-License-Identifier: AGPL-3.0-or-later
"""Source UI structure tests and an actual disposable host-controller browser fixture.

Run this file with --serve WORK [--composed] for the coordinator-owned browser check.
WORK must be fresh beneath a private assigned ancestor. No hardware is accessed.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'runtime'))
from stage_admin_ui import stage
from stage_printer_ui import compose_host
from sv08_state import Store
from sv08_admin import Controller


class SourcePolicyUITests(unittest.TestCase):
    def test_prominent_source_control_survives_composition(self):
        original=(ROOT/'ui/host/index.html').read_bytes()
        for raw in (original,compose_host(original)):
            text=raw.decode()
            self.assertIn('id="source-open"',text.split('</header>')[0])
            self.assertIn('Source &amp; license</button>',text)
            self.assertIn('aria-controls="project-source"',text)
            self.assertIn('src="source.js"',text)
            self.assertIn('Project source revision',text)
            self.assertIn('Project build identity',text)
            self.assertNotIn('<h2><svg',text)
        self.assertIn('#project-source',(ROOT/'ui/printer/index.html').read_text())

    def test_static_source_reader_has_no_controller_or_elevation_calls(self):
        script=(ROOT/'ui/host/source.js').read_text()
        self.assertIn("fetch('project-source.json'",script)
        for forbidden in ('cockpit.spawn','sv08View','superuser','sv08Session','location.href ='):
            self.assertNotIn(forbidden,script)
        self.assertIn("credentials:'omit'",script)
        self.assertIn('overall_release_qualified === false',script)


def serve(work, composed=False):
    if work.exists():raise ValueError('Use a fresh disposable fixture')
    # Existing product admission examines the private ancestry; no guard relaxation.
    work.mkdir(mode=0o700)
    runtime=work/'rootfs/usr/lib/sv08';runtime.mkdir(parents=True)
    for path in (ROOT/'runtime').glob('*.py'):shutil.copyfile(path,runtime/path.name)
    (runtime/'sv08_rauc_bootloader.py').chmod(0o755)
    (runtime/'release.json').write_text(json.dumps({'release':'source-ui-fixture'}))
    if composed:
        package=work/'rootfs/usr/share/cockpit/sv08-printer';package.parent.mkdir(parents=True)
        shutil.copytree(ROOT/'ui/printer',package)
    result=stage(work,'host',True)
    (work/'staging.json').write_text(json.dumps(result,indent=2))
    data=work/'state';store=Store(data,reserve_bytes=0);store.initialize()
    boot=store.prepare_boot('A','source-ui-fixture',release_revision=1);boot['boot_id']='source-ui-fixture'
    (Path(boot['generation'])/'config/printer.cfg').write_text('# Disposable source fixture configuration\n')
    controller=Controller(store,boot)
    (work/'fixture.json').write_text(json.dumps({'generation':boot['generation']}))
    authority={'elevated':False}
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def respond(self,status,raw,kind='application/json'):
            if isinstance(raw,str):raw=raw.encode()
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':return self.respond(403,b'{}')
            if self.path.endswith('/base1/cockpit.js'):
                return self.respond(200,"""(()=>{const proxy=new EventTarget();Object.assign(proxy,{valid:true,Current:'none',Bridges:['sudo'],wait:cb=>cb(),Start:()=>{window.fixtureStarts++;},Answer:()=>{},Stop:()=>{}});window.fixtureStarts=0;window.fixtureRequests=[];window.cockpit={logout:()=>{},dbus:()=>({addEventListener:()=>{},proxy:()=>proxy}),spawn:(argv,options)=>({input:async data=>{const request=JSON.parse(data);window.fixtureRequests.push(request);const response=await fetch('/request',{method:'POST',body:JSON.stringify(request)});return response.text();}})};})();""",'text/javascript')
            if self.path=='/source-off':authority['source_off']=True;return self.respond(200,b'{}')
            name=self.path.split('?')[0].rsplit('/',1)[-1] or 'index.html'
            if name=='project-source.json' and authority.get('source_off'):return self.respond(404,b'{}')
            if '/sv08-printer/' in self.path:base=work/'rootfs/usr/share/cockpit/sv08-printer'
            else:base=work/'rootfs/usr/share/cockpit/sv08-host'
            if name not in {p.name for p in base.iterdir() if p.is_file()}:return self.respond(404,b'{}')
            raw=(base/name).read_bytes()
            self.respond(200,raw,{'html':'text/html','js':'text/javascript','css':'text/css','json':'application/json','txt':'text/plain'}.get(name.rsplit('.',1)[-1],'application/octet-stream'))
        def do_POST(self):
            try:
                size=int(self.headers.get('Content-Length',0))
                if not 0<size<=65536:raise ValueError('Fixture input bound')
                request=json.loads(self.rfile.read(size));requests.append(request)
                (work/'requests.json').write_text(json.dumps(requests))
                # Finite host status reads use the actual disposable controller.
                if request.get('area')=='host' and request.get('method') in ('status','jobs','upload.list'):
                    result=controller.request({'method':request['method']})
                else:raise ValueError('Fixture supports finite host reads only')
                self.respond(200,json.dumps({'ok':True,'result':result}))
            except (ValueError,KeyError,TypeError) as error:self.respond(200,json.dumps({'ok':False,'error':str(error)}))
    with ThreadingHTTPServer(('127.0.0.1',0),Handler) as server:
        (work/'server.json').write_text(json.dumps({'url':f'http://127.0.0.1:{server.server_port}','composed':composed}))
        server.serve_forever()


if __name__=='__main__':
    if '--serve' in sys.argv:
        parser=argparse.ArgumentParser();parser.add_argument('--serve',type=Path,required=True);parser.add_argument('--composed',action='store_true');args=parser.parse_args();serve(args.serve,args.composed)
    else:unittest.main()
