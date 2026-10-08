import base64
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'runtime'))
from sv08_identity import Identity, AUTHORITY, public_keys, publish_cockpit
from test_data_budget import fixture_root, fixture_budget


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sv08-identity-test-', dir=fixture_root())
        self.root = Path(self.temp.name)
        self.data = self.root/'data'
        (self.data/'system/ssh').mkdir(parents=True)
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(self.data/'system/ssh/ssh_host_ed25519_key')],check=True)
        self.user_key = self.root/'user-key'
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(self.user_key)],check=True)
        directory=self.data/'users/sv08/.ssh';directory.mkdir(parents=True)
        self.public = self.user_key.with_suffix('.pub').read_text()
        (directory/'authorized_keys').write_text(self.public)
        self.data.chmod(0o700)
        self.identity = Identity(self.data,os.getuid(),os.getgid(),os.getuid(),budget=fixture_budget(self.data))
        self.initial = self.identity.ensure(['printer.test','192.0.2.3'])

    def tearDown(self): self.temp.cleanup()

    def test_ca_and_ssh_stable_across_boot_and_leaf_renewal(self):
        first=self.identity.current();leaf=(first/'services/server.crt').read_bytes()
        same=self.identity.ensure(['printer.test','192.0.2.3'])
        self.assertEqual(same,self.initial)
        renewed=self.identity.ensure(['printer.test','192.0.2.3'],renew=True)
        self.assertEqual(renewed['ca_fingerprint'],self.initial['ca_fingerprint'])
        self.assertEqual(renewed['ssh_fingerprint'],self.initial['ssh_fingerprint'])
        self.assertNotEqual((self.identity.current()/'services/server.crt').read_bytes(),leaf)
        self.assertEqual((first/'ssh/ssh_host_ed25519_key').read_bytes(),(self.data/'system/ssh/ssh_host_ed25519_key').read_bytes())
        self.assertEqual(len(list((self.identity.root/'generations').iterdir())),2)

    def test_real_tls_client_trusts_ca_after_server_certificate_replacement(self):
        ca=self.identity.current()/'ca/ca.crt'
        client=ssl.create_default_context(cafile=str(ca))
        for renew in [False,True]:
            if renew:self.identity.ensure(['printer.test'],renew=True)
            generation=self.identity.current()
            server=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server.load_cert_chain(generation/'services/server.crt',generation/'services/server.key')
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1)
            errors=[]
            def serve():
                try:
                    connection,_=listener.accept()
                    with server.wrap_socket(connection,server_side=True) as channel:
                        self.assertEqual(channel.recv(4),b'ping');channel.sendall(b'pong')
                except BaseException as error:errors.append(error)
                finally:listener.close()
            thread=threading.Thread(target=serve);thread.start()
            with client.wrap_socket(socket.create_connection(listener.getsockname()),server_hostname='printer.test') as channel:
                channel.sendall(b'ping');self.assertEqual(channel.recv(4),b'pong')
            thread.join(timeout=5);self.assertFalse(thread.is_alive());self.assertEqual(errors,[])

    def test_public_ca_export_and_private_bundle_round_trip(self):
        cert=self.identity.request({'method':'ca.download'})['content']
        self.assertIn('BEGIN CERTIFICATE',cert);self.assertNotIn('PRIVATE KEY',cert)
        bundle=self.identity.request({'method':'bundle.export'})['content']
        with ZipFile(BytesIO(base64.b64decode(bundle))) as archive:self.assertEqual(set(archive.namelist()),set(AUTHORITY)|{'manifest.json'})
        before=self.identity.current()
        preview=self.identity.request({'method':'bundle.preview','bundle':bundle})
        self.assertEqual(self.identity.current(),before)
        self.assertEqual(preview['ca_fingerprint'],self.initial['ca_fingerprint'])
        restored=self.identity.request({'method':'bundle.restore','bundle':bundle,'revision':self.initial['revision']})
        self.assertEqual(restored['ssh_fingerprint'],self.initial['ssh_fingerprint'])
        self.assertEqual(restored['ca_fingerprint'],self.initial['ca_fingerprint'])
        self.assertTrue(restored['services_restart_required'])

    def test_invalid_bundles_do_not_change_selected_identity(self):
        original=self.identity.current()
        bundle=base64.b64decode(self.identity.request({'method':'bundle.export'})['content'])
        for mode in ['extra','duplicate','manifest','mismatched-key']:
            buffer=BytesIO()
            with ZipFile(BytesIO(bundle)) as source,ZipFile(buffer,'w') as target:
                for name in source.namelist():
                    data=source.read(name)
                    if mode=='manifest' and name=='manifest.json':data=b'{}'
                    if mode=='mismatched-key' and name=='ssh/ssh_host_ed25519_key.pub':data=self.public.encode()
                    target.writestr(name,data)
                if mode=='extra':target.writestr('../outside',b'x')
                if mode=='duplicate':target.writestr('ca/ca.crt',source.read('ca/ca.crt'))
            with self.assertRaises(ValueError):self.identity.request({'method':'bundle.restore','bundle':base64.b64encode(buffer.getvalue()).decode(),'revision':self.initial['revision']})
            self.assertEqual(self.identity.current(),original)
        with self.assertRaises(ValueError):self.identity.request({'method':'bundle.preview','bundle':'x'*1400000})

    def test_allocation_refusal_preserves_identity(self):
        before = self.identity.current()
        with patch.object(self.identity.budget, 'check', side_effect=ValueError('Insufficient shared data space')):
            with self.assertRaisesRegex(ValueError, 'Insufficient shared data'):
                self.identity.ensure(['printer.test'], renew=True)
        self.assertEqual(before, self.identity.current())
        self.assertEqual(self.initial['ca_fingerprint'], self.identity.request({'method':'status'})['ca_fingerprint'])

    def test_failure_before_atomic_selection_preserves_working_identity(self):
        before=self.identity.current()
        with patch.object(self.identity,'sign',side_effect=OSError('fixture failure')):
            with self.assertRaises(OSError):self.identity.request({'method':'keys.replace','keys':self.public,'revision':self.initial['revision']})
        self.assertEqual(self.identity.current(),before)
        self.assertEqual(len(list((self.identity.root/'generations').iterdir())),1)
        with self.assertRaises(ValueError):self.identity.request({'method':'keys.replace','keys':self.public,'revision':'0'*32})
        self.assertEqual(self.identity.current(),before)

    def test_ssh_public_key_management_and_storage_bounds(self):
        second=self.root/'second'
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(second)],check=True)
        public=second.with_suffix('.pub').read_text()
        for _ in range(4):
            revision=self.identity.request({'method':'status'})['revision']
            result=self.identity.request({'method':'keys.replace','keys':self.public+public+public,'revision':revision})
            self.assertEqual(len(result['authorized_keys'].splitlines()),2)
            self.assertEqual(result['ssh_fingerprint'],self.initial['ssh_fingerprint'])
            self.assertEqual(result['ca_fingerprint'],self.initial['ca_fingerprint'])
            self.assertLessEqual(len(list((self.identity.root/'generations').iterdir())),2)
        for invalid in ['',self.user_key.read_text(),'command="bad" '+self.public,'ssh-ed25519 !invalid!','x'*65537]:
            with self.assertRaises(ValueError):public_keys(invalid)

    def test_symlink_and_corrupt_authority_refused_without_regeneration(self):
        path=self.identity.current();original=(path/'ca/ca.key').read_bytes()
        (path/'ca/ca.key').unlink();(path/'ca/ca.key').symlink_to(self.user_key)
        with self.assertRaises(ValueError):self.identity.ensure(['printer.test'])
        self.assertEqual(self.identity.current(),path)
        (path/'ca/ca.key').unlink();(path/'ca/ca.key').write_bytes(original)
        (path/'ca/ca.crt').write_bytes(b'invalid')
        with self.assertRaises(ValueError):self.identity.ensure(['printer.test'])
        self.assertEqual(self.identity.current(),path)

    def test_cockpit_combined_certificate_is_private_and_ca_signed(self):
        self.assertTrue(publish_cockpit(self.identity));self.assertFalse(publish_cockpit(self.identity))
        cert=self.data/'system/cockpit/ws-certs.d/zz-printer.cert'
        self.assertEqual(cert.stat().st_mode&0o777,0o600)
        self.assertIn(b'PRIVATE KEY',cert.read_bytes())
        subprocess.run(['openssl','verify','-CAfile',str(self.identity.current()/'ca/ca.crt'),str(cert)],check=True,stdout=subprocess.DEVNULL)

    def test_explicit_restore_recovers_corrupt_authority_without_silent_regeneration(self):
        bundle=self.identity.request({'method':'bundle.export'})['content']
        current=self.identity.current();(current/'ca/ca.key').write_bytes(b'invalid')
        status=self.identity.request({'method':'status'});self.assertFalse(status['healthy'])
        with self.assertRaises(ValueError):self.identity.ensure(['printer.test'])
        self.assertEqual(self.identity.current(),current)
        restored=self.identity.request({'method':'bundle.restore','bundle':bundle,'revision':status['revision']})
        self.assertEqual(restored['ca_fingerprint'],self.initial['ca_fingerprint'])
        self.assertTrue(self.identity.request({'method':'status'})['healthy'])

    def test_generated_mainsail_uses_persistent_ca_certificate(self):
        from sv08_printer_stack import NGINX
        self.assertIn("listen 8443 ssl;", NGINX)
        self.assertIn("return 301 https://$host:8443$request_uri;", NGINX)
        self.assertIn("ssl_certificate /data/sv08/system/identity/current/services/server.crt;", NGINX)
        self.assertIn("ssl_certificate_key /data/sv08/system/identity/current/services/server.key;", NGINX)

    def test_unrelated_host_failure_does_not_disable_identity_controls(self):
        for name in ("ui/host/app.js", "scripts/stage_printer_ui.py"):
            self.assertIn(":not(#identity button)", (REPO/name).read_text())

    def test_identity_staging_and_recovery_password_policy(self):
        sys.path.insert(0,str(REPO/'scripts'))
        from recovery_image import configure_recovery_password
        root=self.root/'recovery';(root/'etc').mkdir(parents=True)
        (root/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/bash\n')
        (root/'etc/group').write_text('root:x:0:\n');(root/'etc/shadow').write_text('root:*:20000:0:99999:7:::\n')
        configure_recovery_password(root)
        policy=json.loads((REPO/'configs/host-os/recovery-password.json').read_text())
        hashed=subprocess.run(['openssl','passwd','-6','-salt','sv08recovery','-stdin'],input=b'recovery\n',capture_output=True,check=True).stdout.decode().strip()
        self.assertEqual(policy['password_hash'],hashed)
        self.assertIn('recovery:'+hashed+':',(root/'etc/shadow').read_text())
        self.assertIn('PasswordAuthentication yes',(REPO/'configs/host-os/sd-recovery-host/sshd_config').read_text())
        self.assertIn('PasswordAuthentication no',(REPO/'configs/host-os/sshd.conf').read_text())
        self.assertIn('identity/current/ssh/ssh_host_ed25519_key',(REPO/'configs/host-os/sshd.conf').read_text())
        self.assertIn('Requires=sv08-prepare.service',(REPO/'configs/host-os/sv08-identity.service').read_text())


def ssh_namespace_fixture():
    """Real sshd/client only in private mount/PID/network namespaces."""
    from sv08_identity import run
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    subprocess.run(['ip','link','set','lo','up'],check=True)
    with tempfile.TemporaryDirectory(prefix='sv08-ssh-identity-', dir=fixture_root()) as temporary:
        root=Path(temporary);root.chmod(0o711)
        policy=json.loads((REPO/'configs/host-os/recovery-password.json').read_text())
        files={
            'passwd':'root:x:0:0:root:/root:/bin/sh\nsshd:x:991:65534:sshd:/run/sshd:/usr/sbin/nologin\nsv08:x:1000:1000:fixture:'+str(root)+':/bin/sh\nrecovery:x:1001:1001:recovery:'+str(root)+':/bin/sh\n',
            'group':'root:x:0:\nsv08:x:1000:\nrecovery:x:1001:\nnogroup:x:65534:\n',
            'shadow':'root:*:20000:0:99999:7:::\nsshd:*:20000:0:99999:7:::\nsv08:'+policy['password_hash']+':20000:0:99999:7:::\nrecovery:'+policy['password_hash']+':20000:0:99999:7:::\n',
        }
        for name,text in files.items():
            path=root/name;path.write_text(text);path.chmod(0o600 if name=='shadow' else 0o644)
            subprocess.run(['mount','--bind',str(path),'/etc/'+name],check=True)
        pam=root/'pam-sshd';pam.write_text('auth required pam_unix.so\naccount required pam_unix.so\nsession required pam_permit.so\n')
        subprocess.run(['mount','--bind',str(pam),'/etc/pam.d/sshd'],check=True)
        subprocess.run(['mount','-t','tmpfs','tmpfs','/run'],check=True)
        Path('/run').chmod(0o755)
        Path('/run/sshd').mkdir(mode=0o755)
        data=root/'data';(data/'system/ssh').mkdir(parents=True)
        host=data/'system/ssh/ssh_host_ed25519_key'
        run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(host))
        clients=[]
        for n in ['first','second']:
            key=root/n;run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(key));clients.append(key)
        keys=data/'users/sv08/.ssh';keys.mkdir(parents=True)
        (keys/'authorized_keys').write_text(clients[0].with_suffix('.pub').read_text())
        data.chmod(0o711);identity=Identity(data,budget=fixture_budget(data));before=identity.ensure(['localhost'])
        bundle=identity.request({'method':'bundle.export'})['content']
        known=root/'known_hosts';known.write_text('[127.0.0.1]:2222 '+host.with_suffix('.pub').read_text())
        alias=Path('/run/identity-fixture');alias.mkdir()
        subprocess.run(['mount','--bind',str(data),str(alias)],check=True)
        ssh_root=alias/'system/identity'
        configuration=root/'sshd_config'
        configuration.write_text('Port 2222\nListenAddress 127.0.0.1\nHostKey '+str(ssh_root/'current/ssh/ssh_host_ed25519_key')+'\nAuthorizedKeysFile '+str(ssh_root/'current/users/%u/authorized_keys')+'\nUsePAM yes\nStrictModes yes\nPermitRootLogin no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nAllowUsers sv08\nPidFile /run/sshd.pid\nLogLevel ERROR\n')
        error=root/'sshd.log'
        with error.open('wb') as log:
            daemon=subprocess.Popen(['/usr/sbin/sshd','-D','-e','-f',str(configuration)],stdout=subprocess.DEVNULL,stderr=log)
            try:
                import time
                for _ in range(40):
                    try:
                        with socket.create_connection(('127.0.0.1',2222),timeout=.2):break
                    except OSError:time.sleep(.05)
                else:raise AssertionError('Fixture sshd did not listen')
                def ssh(key,success):
                    result=subprocess.run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known),'-o','IdentitiesOnly=yes','-p','2222','-i',str(key),'sv08@127.0.0.1','true'],capture_output=True,timeout=10)
                    assert (result.returncode==0)==success,'Fixture SSH authentication did not match expected trust: '+error.read_text()
                ssh(clients[0],True);ssh(clients[1],False)
                identity.request({'method':'keys.replace','keys':clients[1].with_suffix('.pub').read_text(),'revision':before['revision']})
                ssh(clients[1],True);ssh(clients[0],False)
                status=identity.request({'method':'status'})
                identity.request({'method':'bundle.restore','bundle':bundle,'revision':status['revision']})
                ssh(clients[0],True);ssh(clients[1],False)
                assert identity.request({'method':'status'})['ssh_fingerprint']==before['ssh_fingerprint']
                configuration.write_text(configuration.read_text().replace('PasswordAuthentication no','PasswordAuthentication yes').replace('AllowUsers sv08','AllowUsers sv08 recovery'))
                daemon.send_signal(__import__('signal').SIGHUP);time.sleep(.2)
                askpass=root/'askpass';askpass.write_text('#!/bin/sh\nprintf "recovery\\n"\n');askpass.chmod(0o700)
                env=dict(os.environ,DISPLAY=':fixture',SSH_ASKPASS=str(askpass),SSH_ASKPASS_REQUIRE='force')
                result=subprocess.run(['ssh','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known),'-p','2222','recovery@127.0.0.1','true'],stdin=subprocess.DEVNULL,capture_output=True,env=env,timeout=10)
                assert result.returncode==0,'Default recovery password did not authenticate in isolated PAM/SSH fixture'
                print(json.dumps({'real_ssh_key_add_remove_restore':True,'host_identity_preserved':True,'default_recovery_password_verified':True,'private_namespaces':True}))
            finally:
                daemon.terminate();daemon.wait(timeout=5)


class IdentitySSHIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.geteuid()==0,'Run explicitly with sudo in disposable namespaces')
    def test_real_ssh_identity_and_recovery_password(self):
        code='import sys;sys.path[:0]='+repr([str(REPO/'tests'),str(REPO/'runtime')])+';from test_identity import ssh_namespace_fixture;ssh_namespace_fixture()'
        result=subprocess.run(['unshare','--mount','--pid','--fork','--net','--mount-proc','python3','-c',code],capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['real_ssh_key_add_remove_restore'])


def browser_fixture_server():
    """Exact identity component with a simulated privileged Cockpit transport."""
    from http.server import HTTPServer,BaseHTTPRequestHandler
    import re
    with tempfile.TemporaryDirectory(prefix='sv08-identity-browser-', dir=fixture_root()) as temporary:
        root=Path(temporary);data=root/'data'
        keys=data/'users/sv08/.ssh';keys.mkdir(parents=True)
        for name in ['first','second']:
            subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(root/name)],check=True)
        (keys/'authorized_keys').write_text((root/'first.pub').read_text())
        data.chmod(0o700);identity=Identity(data,os.getuid(),os.getgid(),os.getuid(),budget=fixture_budget(data));identity.ensure(['localhost'])
        host=(REPO/'ui/host/index.html').read_text()
        section=re.search(r'<section id="identity".*?</section>',host,re.S).group().replace('class="page" hidden','class="page"')
        dialog=re.search(r'<dialog id="identity-review".*?</dialog>',host,re.S).group()
        html='<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/style.css"></head><body><button id="fixture-authorize">Authorize fixture</button><main>'+section+'</main>'+dialog+'''<script>
window.sv08Session={elevated:false,ready:Promise.resolve()};
window.cockpit={spawn(){return {input(body){return fetch('/rpc',{method:'POST',headers:{'Content-Type':'application/json','X-Fixture-Authorized':String(sv08Session.elevated)},body}).then(r=>r.text())}}}};
document.getElementById('fixture-authorize').onclick=()=>{sv08Session.elevated=!sv08Session.elevated;window.dispatchEvent(new Event('sv08-authority-changed'));};
</script><script src="/identity.js"></script></body></html>'''
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if self.path.startswith('/#') or self.path=='/':raw=html.encode();kind='text/html'
                elif self.path in ['/identity.js','/style.css']:
                    raw=(REPO/'ui/host'/self.path[1:]).read_bytes();kind='application/javascript' if self.path.endswith('.js') else 'text/css'
                else:self.send_error(404);return
                self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Security-Policy',"style-src 'self'");self.end_headers();self.wfile.write(raw)
            def do_POST(self):
                size=int(self.headers.get('Content-Length','0'))
                if self.path!='/rpc' or size>2*1024**2:self.send_error(413);return
                if self.headers.get('X-Fixture-Authorized')!='true':self.send_error(403);return
                try:result=dict(ok=True,result=identity.request(json.loads(self.rfile.read(size))))
                except Exception:result=dict(ok=False,error='Identity operation failed. Reload before retrying.')
                raw=json.dumps(result).encode();self.send_response(200);self.end_headers();self.wfile.write(raw)
        server=HTTPServer(('127.0.0.1',0),Handler)
        import signal
        def stop(_signal,_frame):raise SystemExit
        signal.signal(signal.SIGTERM,stop)
        print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_port)+'/#identity','work':str(root),'second_public_key':str(root/'second.pub')}),flush=True)
        try:server.serve_forever()
        finally:server.server_close()


if __name__=='__main__':unittest.main()
