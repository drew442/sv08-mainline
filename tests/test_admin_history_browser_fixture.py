"""Localhost browser shim + separate real Controller/Transaction worker fixture."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import subprocess
import sys
from test_data_budget import fixture_budget
from test_admin_history import receipt, disposed
from admin_jobs_fixture import initialize_resolution, make_controller
from sv08_state import Store, atomic_json
from sv08_boot import prepare_permissions
from unittest.mock import patch


def serve(work):
    work.mkdir(mode=0o700)
    store=Store(work/'state',reserve_bytes=0,budget=fixture_budget(work/'state'));store.initialize()
    boot=store.prepare_boot('A','0.1.0-ui-fixture');boot['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    (work/'ui-fixture.json').write_text(json.dumps(boot));initialize_resolution(work,boot,budget_root=work/'state')
    with patch('sv08_boot.os.chown'):
        prepare_permissions(store.root,boot['generation'])
    assert store.root.stat().st_mode & 0o777 == 0o711
    controller=make_controller(work,resolution=True,budget_root=work/'state')
    def history_fault(point):
        if (work/'history-recovery-failure').exists() and point == 'recovery-directory-fsync':
            raise OSError('Injected persistent history recovery failure')
    controller.jobs.history_fault=history_fault
    rows=[receipt(i) for i in range(128)];rows[0]=disposed(0)
    atomic_json(controller.jobs.root/'jobs.json',rows)
    (work/'originals.json').write_text(json.dumps(rows))
    def launcher(identity):
        with (work/'worker.log').open('ab') as log:
            child=subprocess.Popen([sys.executable,'-B',__file__,str(work),identity],stdout=log,stderr=log)
        (work/'worker-pid').write_text(str(child.pid))
    controller.jobs.launcher=launcher
    ui=Path(__file__).resolve().parents[1]/'ui/host'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def response(self,body,kind='application/json'):
            body=body.encode() if isinstance(body,str) else body
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/base1/cockpit.js':
                return self.response("window.cockpit={logout:()=>{},dbus:()=>({addEventListener:()=>{},proxy:()=>({valid:true,Current:'root',Bridges:['sudo'],Start:()=>{},Answer:()=>{},Stop:()=>{},addEventListener:()=>{},wait:cb=>cb()})}),spawn:()=>({input:async data=>(await fetch('/request',{method:'POST',body:data})).text()})};",'text/javascript')
            name='index.html' if self.path=='/' else self.path[1:]
            if name not in ('index.html','app.js','style.css','session.js','upload.js'):self.send_error(404);return
            return self.response((ui/name).read_bytes(), 'text/html' if name.endswith('.html') else 'text/css' if name.endswith('.css') else 'text/javascript')
        def do_POST(self):
            try:
                size=int(self.headers['Content-Length'])
                if not 0<size<=16384:raise ValueError('Invalid fixture request bound')
                request=json.loads(self.rfile.read(size));result=controller.request(request)
                if 'capabilities' in result:result['fixture']=True
                response=dict(ok=True,result=result)
            except (ValueError,OSError,KeyError,TypeError) as error:response=dict(ok=False,error=str(error))
            self.response(json.dumps(response))
    with ThreadingHTTPServer(('127.0.0.1',0),Handler) as server:
        (work/'server.json').write_text(json.dumps(dict(url=f'http://127.0.0.1:{server.server_port}')))
        server.serve_forever()


if __name__=='__main__':
    work=Path(sys.argv[1])
    if len(sys.argv)>2:
        c=make_controller(work,resolution=True,budget_root=work/'state');c.jobs.work(lambda:make_controller(work,resolution=True,budget_root=work/'state'),sys.argv[2])
    else:serve(work)
