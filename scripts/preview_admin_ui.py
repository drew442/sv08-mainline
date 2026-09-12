#!/usr/bin/env python3
"""Local browser fixture with real disposable policy storage; never a LAN service."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_admin import Controller
from sv08_state import Store
from prepare_host_os import REPO, work_path


def serve(work, image_jobs=False):
    if work.exists(): raise ValueError('Use a fresh disposable build directory')
    work.mkdir(parents=True)
    store = Store(work / 'state', reserve_bytes=0)
    store.initialize(); boot = store.prepare_boot('A', '0.1.0-ui-fixture')
    boot['boot_id'] = 'ui-fixture'
    (work / 'ui-fixture.json').write_text(json.dumps(boot))
    controller = Controller(store, boot)
    if image_jobs:
        sys.path.insert(0, str(REPO / 'tests'))
        from admin_jobs_fixture import initialize, make_controller
        initialize(work, boot)
        controller = make_controller(work)
    token = secrets.token_hex(32)
    root = REPO / 'ui/host'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def respond(self, status, content, kind='application/json'):
            data = content.encode() if isinstance(content, str) else content
            self.send_response(status); self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
                return self.respond(403, b'{}')
            if self.path == '/base1/cockpit.js':
                script = '''// Test-only transport: no authentication coverage. Production uses packaged Cockpit.
window.cockpit={logout:()=>{},dbus:()=>({addEventListener:()=>{},proxy:()=>({valid:true,Current:'root',Bridges:['sudo'],Start:()=>{},Answer:()=>{},Stop:()=>{},addEventListener:()=>{},wait:callback=>callback()})}),spawn:()=>({input:async data=>{
const r=await fetch('/request',{method:'POST',headers:{'Content-Type':'application/json','X-Fixture-Token':TOKEN},body:data});
return await r.text();}})};'''.replace('TOKEN', json.dumps(token))
                return self.respond(200, script, 'text/javascript')
            paths = {'/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js', '/upload.js': 'upload.js', '/session.js': 'session.js', '/style.css': 'style.css'}
            if self.path not in paths: return self.respond(404, b'{}')
            name = paths[self.path]
            self.respond(200, (root / name).read_bytes(), {'html':'text/html','js':'text/javascript','css':'text/css'}[name.split('.')[-1]])

        def do_POST(self):
            self.connection.settimeout(10)
            if (self.path != '/request' or self.headers.get('X-Fixture-Token') != token or
                    self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}'):
                return self.respond(403, b'{}')
            try:
                size = int(self.headers['Content-Length'])
                if not 0 < size <= 16384: raise ValueError('Invalid request size')
                result = controller.request(json.loads(self.rfile.read(size)))
                if 'capabilities' in result: result['fixture'] = True
                response = dict(ok=True, result=result)
            except (ValueError, OSError, KeyError, TypeError) as error:
                response = dict(ok=False, error=str(error))
            self.respond(200, json.dumps(response))

    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        address = f'http://127.0.0.1:{server.server_port}'
        (work / 'server.json').write_text(json.dumps({'url': address}))
        print(address, flush=True)
        server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--image-jobs-fixture', action='store_true', help='Disposable systemd user-worker fixture only')
    args = parser.parse_args()
    work = work_path(args.work)
    if not args.execute: print(json.dumps({'execute': False, 'work': str(work)}))
    else: serve(work, args.image_jobs_fixture)
