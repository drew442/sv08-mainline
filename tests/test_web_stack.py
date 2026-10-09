"""Disposable offline web bootstrap and persistent-state preservation checks."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_web import Web, credentials, validate_nginx, validate_moonraker, API
from sv08_printer_stack import MOONRAKER, NGINX
from test_data_budget import fixture_root


class Budget:
    @contextmanager
    def locked(self): yield
    def check(self, *args, **kwargs): pass


class NativeAPI:
    def __init__(self):
        self.owner = None; self.calls = []; self.key = 'a'*32
    def ready(self): self.calls.append('ready')
    def request(self, path, fields=None, token=None):
        self.calls.append(path)
        if path == '/access/users/list': return {'users': [] if self.owner is None else [{'username': self.owner['username']}]}
        if path == '/access/login':
            if fields != self.owner: raise ValueError('Rejected')
            return {'token': 'fixture-token'}
        if path == '/access/user':
            if self.owner is not None: raise AssertionError('Account overwritten')
            self.owner = dict(fields); return {'token': 'fixture-token'}
        if path == '/access/api_key':
            assert token == 'fixture-token'
            return self.key
        raise AssertionError(path)


class WebTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=fixture_root()); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.data = self.root/'data'; self.data.mkdir(mode=0o711)
        self.config = self.data/'config'; self.config.mkdir(mode=0o750)
        self.api = NativeAPI()
        self.web = Web(self.data, self.config, os.getuid(), os.getgid(), Budget(), self.api)

    def provision(self): self.web.prepare(); self.web.authenticate()

    def test_fresh_native_account_and_gateway_and_reboot_preservation(self):
        hardware = self.config/'printer.cfg'; hardware.write_bytes(b'fixture hardware retained\n')
        database = self.data/'database'; database.mkdir(); state = database/'state'; state.write_bytes(b'fixture native data')
        self.provision()
        paths = [*self.config.iterdir(), self.web.login, *self.web.auth.iterdir(), state]
        before = {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mode) for p in paths}
        self.assertEqual(self.web.auth.stat().st_mode & 0o777, 0o700)
        for p in (self.web.login, *self.web.auth.iterdir()):
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            self.assertEqual(p.stat().st_uid, os.getuid())
        self.assertEqual(self.api.calls.count('/access/user'), 1)
        self.api.calls.clear(); self.provision()
        self.assertEqual(self.api.calls, ['ready'])
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mode) for p in paths})

    def test_existing_accepted_308_config_and_retrieval_format_preserved(self):
        self.provision()
        nginx = self.config/'nginx-mainsail.conf'
        nginx.write_text(nginx.read_text().replace('return 301', 'return 308').replace('SV08 printer', 'SV08 Mainsail'))
        self.web.login.write_text(self.web.login.read_text()+'Mainsail: https://fixture:8443\n')
        old = nginx.read_bytes(), self.web.login.read_bytes()
        self.provision()
        self.assertEqual(old, (nginx.read_bytes(), self.web.login.read_bytes()))

    def test_admits_root_owned_group_readable_config_without_replacing_it(self):
        from sv08_web import read
        self.web.prepare()
        path = self.config/'nginx-mainsail.conf'; raw = path.read_bytes()
        original = os.fstat
        def root_owned(fd):
            values = list(original(fd)); values[0] = (values[0] & ~0o777) | 0o640
            values[4] = 0; values[5] = os.getgid()
            return os.stat_result(values)
        with patch('sv08_web.os.fstat', side_effect=root_owned):
            self.assertEqual(read(path, os.getuid(), root_gid=os.getgid()), raw.decode())
            with self.assertRaisesRegex(ValueError, 'permissions'):
                read(path, os.getuid(), private=True)
        self.assertEqual(path.read_bytes(), raw)

    def test_preserves_accepted_quoted_backend_key(self):
        self.provision()
        proxy = self.web.auth/'moonraker-proxy.conf'
        proxy.write_text('proxy_set_header X-Api-Key "'+self.api.key+'";\n')
        before = {p: p.read_bytes() for p in [self.web.login, *self.web.auth.iterdir()]}
        self.web.authenticate()
        self.assertEqual(self.web.proxy_key(), self.api.key)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        proxy.write_text('proxy_set_header X-Api-Key "'+self.api.key+';\n')
        with self.assertRaisesRegex(ValueError, 'Invalid private'): self.web.authenticate()

    def test_unknown_native_account_refused_without_new_credentials(self):
        self.api.owner = {'username': 'unknown', 'password': 'unknown'}
        self.web.prepare()
        with self.assertRaisesRegex(ValueError, 'Unknown native'): self.web.authenticate()
        self.assertFalse(self.web.login.exists())
        self.assertNotIn('/access/user', self.api.calls)

    def test_partial_gateway_and_password_mismatch_fail_closed_preserve_bytes(self):
        self.provision()
        proxy = self.web.auth/'moonraker-proxy.conf'; before = proxy.read_bytes(); proxy.unlink()
        users = (self.web.auth/'users').read_bytes()
        self.web.authenticate()
        self.assertEqual(users, (self.web.auth/'users').read_bytes())
        self.assertEqual(before, proxy.read_bytes())
        self.web.login.write_text('Moonraker username: sv08\nMoonraker password: '+'x'*32+'\n')
        with self.assertRaisesRegex(ValueError, 'disagree'): self.web.authenticate()
        self.assertEqual(users, (self.web.auth/'users').read_bytes())

    def test_interrupted_gateway_publish_recovers_both_halves_and_rejects_mismatch(self):
        from sv08_web import create
        self.web.prepare()
        def interrupted(path, *args):
            if path.name == 'moonraker-proxy.conf': raise OSError('fixture interruption')
            return create(path, *args)
        with patch('sv08_web.create', side_effect=interrupted):
            with self.assertRaises(OSError): self.web.authenticate()
        users = self.web.auth/'users'; before = users.read_bytes()
        self.web.authenticate()
        self.assertEqual(users.read_bytes(), before)
        self.assertEqual(self.api.calls.count('/access/user'), 1)
        proxy = self.web.auth/'moonraker-proxy.conf'; before_proxy = proxy.read_bytes()
        users.unlink(); self.api.key = 'b'*32
        with self.assertRaisesRegex(ValueError, 'key mismatch'): self.web.authenticate()
        self.assertFalse(users.exists()); self.assertEqual(proxy.read_bytes(), before_proxy)
        self.api.key = 'a'*32; self.web.authenticate()
        self.assertEqual(proxy.read_bytes(), before_proxy)
        self.assertEqual(self.api.calls.count('/access/user'), 1)

    def test_failed_account_creation_retains_retrieval_then_resumes(self):
        self.web.prepare(); original = self.api.request
        def failed(path, *args, **kwargs):
            if path == '/access/user': raise ValueError('fixture unavailable')
            return original(path, *args, **kwargs)
        with patch.object(self.api, 'request', side_effect=failed):
            with self.assertRaises(ValueError): self.web.authenticate()
        raw = self.web.login.read_bytes()
        self.web.authenticate()
        self.assertEqual(self.web.login.read_bytes(), raw)

    def test_symlinks_permissions_and_hardlinks_refused(self):
        self.web.prepare()
        path = self.config/'moonraker.conf'; path.unlink(); path.symlink_to(self.root/'missing')
        with self.assertRaises(OSError): self.web.prepare()
        path.unlink(); self.web.prepare(); self.web.authenticate()
        self.web.login.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'permissions'): self.web.authenticate()
        self.web.login.chmod(0o600); os.link(self.web.login, self.root/'second-link')
        with self.assertRaisesRegex(ValueError, 'permissions'): self.web.authenticate()

    def test_unsafe_config_does_not_get_replaced(self):
        self.web.prepare(); path = self.config/'moonraker.conf'
        unsafe = MOONRAKER.replace('127.0.0.1', '0.0.0.0'); path.write_text(unsafe)
        with self.assertRaisesRegex(ValueError, 'loopback'): self.web.prepare()
        self.assertEqual(path.read_text(), unsafe)
        for unsafe in (NGINX.replace('auth_basic "SV08 printer"', 'auth_basic off'),
                       NGINX.replace('proxy_set_header Authorization "";', ''),
                       NGINX.replace('X-Forwarded-For $remote_addr', 'X-Forwarded-For $http_x_forwarded_for')):
            with self.assertRaises(ValueError): validate_nginx(unsafe)
        with self.assertRaises(ValueError): validate_moonraker(MOONRAKER.replace('force_logins: True', 'force_logins: False'))

    def test_shared_storage_refusal_creates_no_seed_or_credentials(self):
        with patch.object(self.web.budget, 'check', side_effect=ValueError('no space')):
            with self.assertRaisesRegex(ValueError, 'no space'): self.web.prepare()
        self.assertEqual(list(self.config.iterdir()), [])

    def test_api_bypasses_environment_proxy(self):
        with patch.dict(os.environ, {'http_proxy': 'http://invalid:9'}):
            api = API()
        self.assertFalse(any(getattr(handler, 'proxies', {}) for handler in api.opener.handlers))

    def test_api_public_readiness_and_bounded_response(self):
        from io import BytesIO
        from sv08_web import LIMIT
        api = API(); requests = []
        class Response(BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        def response(request, **kwargs):
            requests.append((request.full_url, kwargs['timeout']))
            return Response(b'{"result":{"login_required":true}}')
        with patch.object(api.opener, 'open', side_effect=response): api.ready()
        self.assertEqual(requests, [('http://127.0.0.1:7125/access/info', 2)])
        with patch.object(api.opener, 'open', side_effect=response):
            api.request('/access/user', {'username': 'fixture', 'password': 'fixture'})
        self.assertEqual(requests[-1], ('http://127.0.0.1:7125/access/user', 15))
        with patch.object(api.opener, 'open', return_value=Response(b'x'*(LIMIT+1))):
            with self.assertRaisesRegex(ValueError, 'exceeds'): api.request('/access/info')

    def test_real_shared_storage_admission(self):
        from sv08_data_budget import Budget as RealBudget
        self.web.budget = RealBudget(self.data, state_reserve=0, copy_limit=0, staging_reserve=0)
        self.provision()
        self.assertEqual((self.data/'allocation.lock').stat().st_mode & 0o777, 0o600)

    def test_hashing_does_not_put_password_in_arguments(self):
        from sv08_web import password_hash
        import subprocess
        original = subprocess.run; calls = []
        def run(args, **kwargs): calls.append(args); return original(args, **kwargs)
        with patch('sv08_web.subprocess.run', side_effect=run): password_hash('fixture-secret-password')
        self.assertNotIn('fixture-secret-password', str(calls))

    def test_units_keep_hardware_disconnected_and_gate_gateway(self):
        root = Path(__file__).resolve().parents[1]/'configs/host-os/systemd'
        api = (root/'sv08-printer-api.service').read_text(); nginx = (root/'sv08-mainsail.service').read_text()
        self.assertNotIn('klipper', api); self.assertNotIn('dialout', api)
        for raw in (api, nginx):
            self.assertIn('PrivateDevices=yes', raw); self.assertIn('User=sv08', raw)
            self.assertIn('/usr/lib/sv08/sv08_restart.py check-start', raw)
        prepare = (root/'sv08-web-prepare.service').read_text()
        # Both preparation helpers use the shared nonblocking data budget lock.
        self.assertIn('Requires=sv08-prepare.service sv08-identity.service', prepare)
        self.assertIn('After=sv08-prepare.service sv08-identity.service', prepare)
        self.assertIn('Requires=sv08-web-auth.service sv08-identity.service', nginx)
        self.assertIn('RuntimeDirectoryMode=0700', nginx)
        self.assertIn('nginx -t', nginx)


if __name__ == '__main__': unittest.main()
