"""Offline managed browser authentication, transaction recovery and real crypto."""
import base64
from contextlib import contextmanager
import copy
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import sv08_mainsail_access as access_module
from sv08_mainsail_access import MainsailAccess, decode, render, validate_policy, secret, MARKER, LIMIT
from sv08_web import Web, password_hash, validate_nginx
from sv08_printer_stack import NGINX
from test_data_budget import fixture_root
from test_web_stack import NativeAPI


class Budget:
    @contextmanager
    def locked(self): yield
    def check(self,*args,**kwargs): pass


class AccessTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=fixture_root());self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.data=self.root/'data';self.data.mkdir(mode=0o711)
        self.config=self.data/'config';self.config.mkdir(mode=0o750)
        self.api=NativeAPI();self.budget=Budget()
        self.web=Web(self.data,self.config,os.getuid(),os.getgid(),self.budget,self.api,root_uid=os.getuid())
        self.web.prepare();self.web.authenticate()
        self.calls=[]
        self.access=MainsailAccess(self.data,self.config,os.getuid(),os.getgid(),os.getuid(),self.budget,self.calls.append,temporary=self.root)
        self.native={p:p.read_bytes() for p in (self.web.login,self.web.auth/'moonraker-proxy.conf')}

    def ca(self,replace=False):
        root=self.data/'system/identity';generation=root/'generations'/('b'*32 if replace else 'a'*32)
        (generation/'ca').mkdir(mode=0o700,parents=True)
        for directory in (self.data/'system',root,root/'generations',generation):directory.chmod(0o711)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-sha256','-days','7300',
                        '-keyout',str(generation/'ca/ca.key'),'-out',str(generation/'ca/ca.crt'),'-subj','/CN=Fixture CA',
                        '-addext','basicConstraints=critical,CA:TRUE,pathlen:0','-addext','keyUsage=critical,keyCertSign,cRLSign'],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        (generation/'ca/ca.key').chmod(0o600)
        (generation/'ca/ca.crt').chmod(0o644)
        current=root/'current';current.unlink(missing_ok=True);current.symlink_to('generations/'+generation.name)
        return generation

    def request(self,method,**fields): return self.access.request({'method':method,**fields})

    def create(self): return self.request('certificate.create',label='Browser laptop',password='private pass')

    def test_default_status_and_separate_gateway_password_preserves_native(self):
        self.assertEqual(self.request('status')['mode'],'password')
        self.assertFalse(self.access.state.exists())
        self.request('settings',mode='password',password='new secret')
        policy=self.access.load();self.assertNotIn('new secret',self.access.state.read_text())
        self.assertEqual(policy['hash'],password_hash('new secret',policy['hash'].split('$')[2]))
        self.web.prepare();self.api.calls.clear();self.web.authenticate()
        self.assertEqual(self.api.calls,['ready'])
        self.assertEqual(self.native,{p:p.read_bytes() for p in self.native})
        self.assertEqual(self.access.state.stat().st_mode&0o777,0o600)
        self.assertEqual(self.access.root.stat().st_mode&0o777,0o700)
        self.assertEqual(self.calls,['test','reload'])

    def test_no_login_is_explicit_and_preserves_api_proxy_and_all_routes(self):
        self.request('settings',mode='none');policy=self.access.load();raw=render(policy)
        self.assertIn('auth_basic off;',raw)
        self.assertEqual(raw.count('include /data/sv08/mainsail-auth/moonraker-proxy.conf;'),2)
        self.assertEqual(raw.count('proxy_set_header Authorization "";'),2)
        validate_nginx(raw,policy)
        with self.assertRaises(ValueError):validate_nginx(raw)
        with self.assertRaises(ValueError):validate_nginx(raw.replace('proxy_set_header Authorization "";',''),policy)
        self.web.prepare();self.web.authenticate()
        self.request('settings',mode='password');self.assertEqual(self.request('status')['mode'],'password')

    def test_invalid_requests_and_duplicate_fields_fail_without_change(self):
        for request in ({'method':'unknown'},{'method':'settings','mode':'none','extra':1},
                        {'method':'settings','mode':'certificate'}, {'method':'settings','mode':'password','password':'short'},
                        {'method':'settings','mode':'none','password':'a long secret'},[],{'method':[]}):
            with self.assertRaises(ValueError):self.access.request(request)
        with self.assertRaises(ValueError):decode('{"method":"status","method":"settings"}')
        for value in ('short','x\nyyyyyyyyy',None,256*'é'):
            with self.assertRaises(ValueError):secret(value)
        self.assertFalse(self.access.state.exists());self.assertFalse(self.calls)

    def test_validation_failure_rolls_back_initial_bytes_and_permissions(self):
        before={p:(p.read_bytes(),p.stat().st_mode&0o777,p.stat().st_uid,p.stat().st_gid) for p in self.access.files().values() if p.exists()}
        operations=[]
        def controller(operation):
            operations.append(operation)
            if operations == ['test']:raise ValueError('fixture rejected new config')
        self.access.controller=controller
        with self.assertRaises(ValueError):self.request('settings',mode='none')
        self.assertFalse(self.access.state.exists());self.assertFalse(self.access.journal.exists())
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_mode&0o777,p.stat().st_uid,p.stat().st_gid) for p in before})
        self.web.prepare();self.web.authenticate()
        self.assertEqual(operations,['test','test','reload'])

    def test_reload_failure_rolls_back_committed_policy(self):
        self.request('settings',mode='password',password='first secret');before=self.access.state.read_bytes();old=self.access.snapshot()
        calls=[]
        def controller(operation):
            calls.append(operation)
            if calls == ['test','reload']:raise ValueError('fixture reload failed')
        self.access.controller=controller
        with self.assertRaises(ValueError):self.request('settings',mode='none')
        self.assertEqual(self.access.state.read_bytes(),before);self.assertEqual(self.access.snapshot(),old)
        self.assertEqual(calls,['test','reload','test','reload'])
        self.assertFalse(self.access.journal.exists())

    def test_policy_publish_failure_after_replace_restores_previous(self):
        self.request('settings',mode='password',password='first secret')
        previous=self.access.state.read_bytes();old=self.access.snapshot()
        original=self.access.sync;failed=False
        def failure(path):
            nonlocal failed
            if path==self.access.root and self.access.load()['mode']=='none' and not failed:
                failed=True;raise OSError('fixture directory sync failure')
            return original(path)
        with patch.object(self.access,'sync',side_effect=failure):
            with self.assertRaises(OSError):self.request('settings',mode='none')
        self.assertEqual(self.access.state.read_bytes(),previous)
        self.assertEqual(self.access.snapshot(),old);self.assertFalse(self.access.journal.exists())

    def test_crash_before_commit_recovers_previous_and_after_commit_desired(self):
        self.request('settings',mode='password',password='first secret');previous=self.access.load();old=self.access.snapshot()
        original=self.access.write
        def crash(path,*args,**kwargs):
            if path==self.access.state:raise KeyboardInterrupt('fixture process interruption')
            return original(path,*args,**kwargs)
        with patch.object(self.access,'write',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):self.request('settings',mode='none')
        self.assertTrue(self.access.journal.exists());self.assertNotEqual(self.access.snapshot(),old)
        self.web.prepare();self.assertEqual(self.access.load(),previous);self.assertEqual(self.access.snapshot(),old)
        original_sync=self.access.sync
        def crash_after_commit(path):
            if path==self.access.root and self.access.state.exists() and self.access.load()['mode']=='none':raise KeyboardInterrupt()
            return original_sync(path)
        with patch.object(self.access,'sync',side_effect=crash_after_commit):
            with self.assertRaises(KeyboardInterrupt):self.request('settings',mode='none')
        self.assertTrue(self.access.journal.exists());self.web.prepare()
        self.assertEqual(self.access.load()['mode'],'none');self.assertFalse(self.access.journal.exists())

    def test_managed_policy_missing_corrupt_or_gateway_changed_fails_closed(self):
        self.request('settings',mode='none');before=self.access.state.read_bytes()
        self.access.state.write_text('{}')
        with self.assertRaises(ValueError):self.web.prepare()
        self.access.state.write_bytes(before);self.access.state.unlink()
        with self.assertRaises(ValueError):self.request('status')
        with self.assertRaises(ValueError):self.web.prepare()
        self.access.state.write_bytes(before);users=self.access.auth/'users';users.write_text('sv08:invalid\n')
        with self.assertRaises(ValueError):self.request('status')
        self.assertEqual(users.read_text(),'sv08:invalid\n')

    def test_symlink_hardlink_and_private_policy_permissions_rejected(self):
        self.request('settings',mode='password',password='first secret')
        self.access.state.chmod(0o644)
        with self.assertRaises(ValueError):self.request('status')
        self.access.state.chmod(0o600);os.link(self.access.state,self.root/'second')
        with self.assertRaises(ValueError):self.request('status')
        (self.root/'second').unlink();raw=self.access.state.read_bytes();self.access.state.unlink()
        path=self.root/'target';path.write_bytes(raw);path.chmod(0o600);self.access.state.symlink_to(path)
        with self.assertRaises(OSError):self.request('status')

    def test_publisher_template_restored_from_policy_but_unknown_edits_rejected(self):
        self.request('settings',mode='none');config=self.config/'nginx-mainsail.conf'
        config.write_text(NGINX);self.web.prepare();self.assertEqual(config.read_text(),render(self.access.load()))
        config.write_text(NGINX.replace('listen 8443 ssl','listen 9443 ssl'))
        with self.assertRaises(ValueError):self.web.prepare()

    def test_storage_refusal_changes_no_gateway(self):
        old=self.access.snapshot()
        with patch.object(self.budget,'check',side_effect=ValueError('storage full')):
            with self.assertRaises(ValueError):self.request('settings',mode='none')
        self.assertEqual(self.access.snapshot(),old);self.assertFalse(self.access.state.exists())

    def test_client_bundle_real_crypto_allowlist_revocation_and_cleanup(self):
        generation=self.ca();authority_key=(generation/'ca/ca.key').read_bytes();download=self.create()
        policy=self.access.load();self.assertEqual(policy['mode'],'password')
        self.assertEqual(len(policy['certificates']),1);self.assertNotIn('PRIVATE KEY',self.access.state.read_text())
        bundle=self.root/'bundle.p12';bundle.write_bytes(base64.b64decode(download['pkcs12_base64']))
        subprocess.run(['openssl','pkcs12','-in',str(bundle),'-passin','stdin','-noout'],input=b'private pass\n',check=True,capture_output=True)
        wrong=subprocess.run(['openssl','pkcs12','-in',str(bundle),'-passin','stdin','-noout'],input=b'incorrect\n',capture_output=True)
        self.assertNotEqual(wrong.returncode,0)
        client=self.root/'client.crt';result=subprocess.run(['openssl','pkcs12','-in',str(bundle),'-passin','stdin','-clcerts','-nokeys'],input=b'private pass\n',check=True,capture_output=True);client.write_bytes(result.stdout)
        subprocess.run(['openssl','verify','-purpose','sslclient','-CAfile',str(generation/'ca/ca.crt'),str(client)],check=True,capture_output=True)
        result=subprocess.run(['openssl','verify','-purpose','sslserver','-CAfile',str(generation/'ca/ca.crt'),str(client)],capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(list(self.root.glob('sv08-client-*')))
        self.request('settings',mode='certificate');raw=render(self.access.load())
        self.assertIn('ssl_verify_client on;',raw);self.assertIn('if ($sv08_client_allowed = 0) { return 403; }',raw)
        self.assertIn(policy['certificates'][0]['nginx_fingerprint'],raw);self.assertIn('default 0;',raw)
        http_prefix=raw.split('server {',1)[0]
        buckets=re.findall(r'(?m)^map_hash_bucket_size ([0-9]+);$',http_prefix)
        self.assertEqual(len(buckets),1)
        # A 40-byte SHA1 key plus hash-entry length/pointer overhead needs 64.
        self.assertGreaterEqual(int(buckets[0]),len(policy['certificates'][0]['nginx_fingerprint'])+2+8)
        self.request('certificate.revoke',id=download['certificate']['id'])
        self.assertNotIn(policy['certificates'][0]['nginx_fingerprint'],render(self.access.load()))
        self.assertEqual(self.request('status')['mode'],'certificate')
        with self.assertRaises(ValueError):self.request('settings',mode='certificate')
        self.request('settings',mode='password');self.assertEqual((generation/'ca/ca.key').read_bytes(),authority_key)

    def test_ca_restore_status_switch_and_explicit_regeneration(self):
        self.ca();first=self.create();self.request('settings',mode='certificate');self.ca(replace=True)
        status=self.request('status');self.assertFalse(status['authority_valid']);self.assertTrue(status['warning'])
        with self.assertRaises(ValueError):self.web.prepare()
        with self.assertRaises(ValueError):self.request('settings',mode='certificate')
        self.request('settings',mode='password');self.web.prepare()
        second=self.create();policy=self.access.load()
        self.assertTrue(policy['certificates'][0]['revoked']);self.assertFalse(policy['certificates'][1]['revoked'])
        self.assertNotEqual(first['certificate']['id'],second['certificate']['id']);self.request('settings',mode='certificate')
        self.assertTrue(self.request('status')['authority_valid'])

    def test_expired_certificate_cannot_activate_mode_and_policy_parser_strict(self):
        policy=self.access.initial();policy['mode']='certificate'
        policy['ca']='fixture';policy['ca_fingerprint']='a'*64
        policy['certificates']=[dict(id='a'*32,label='Expired',fingerprint='a'*64,nginx_fingerprint='a'*40,created=1,expires=2,revoked=False)]
        validate_policy(policy)
        self.access.roots();self.access.write(self.access.state,json.dumps(policy));self.access.publish(self.access.outputs(policy))
        with patch.object(self.access,'authority'):
            with self.assertRaisesRegex(ValueError,'active'):self.request('settings',mode='certificate')
        for key,value in (('hash','bad'),('mode','unknown'),('version',True),('certificates',[{}])):
            invalid=copy.deepcopy(policy);invalid[key]=value
            with self.assertRaises(ValueError):validate_policy(invalid)

    def test_rpc_boundary_envelope_bounded_input_root_and_no_secret_error(self):
        from io import BytesIO, StringIO
        class Input:
            def __init__(self,raw):self.buffer=BytesIO(raw)
        stdout=StringIO()
        with patch.object(access_module.os,'geteuid',return_value=0),patch.object(access_module.sys,'stdin',Input(b'{"method":"status"}')),patch.object(access_module.sys,'stdout',stdout),patch.object(access_module,'MainsailAccess',return_value=self.access):
            access_module.main()
        self.assertTrue(json.loads(stdout.getvalue())['ok'])
        with patch.object(access_module.os,'geteuid',return_value=1000):
            with self.assertRaisesRegex(ValueError,'root'):access_module.main()
        with patch.object(access_module.os,'geteuid',return_value=0),patch.object(access_module.sys,'stdin',Input(b'x'*(LIMIT+1))):
            with self.assertRaisesRegex(ValueError,'bound'):access_module.main()
        result=subprocess.run([sys.executable,str(Path(access_module.__file__))],input=b'{"method":"settings","password":"secret-material"}',capture_output=True)
        self.assertEqual(result.returncode,1);self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertNotIn(b'secret-material',result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
