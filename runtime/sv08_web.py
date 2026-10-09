"""Bounded, fail-closed web provisioning; no printer configuration/device access.

Existing files are validated, never replaced. A failed partial bootstrap retains
its acknowledged native account and retrieval credentials for the next attempt.
"""
import argparse
import configparser
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import time
import urllib.error
import urllib.request

from sv08_data_budget import Budget
from sv08_printer_stack import MOONRAKER, NGINX, MAINSail

LIMIT = 64 * 1024


def directory(path, uid, mode=None):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_mode & 0o022:
        raise ValueError('Invalid web directory')
    if mode is not None and stat.S_IMODE(info.st_mode) != mode:
        raise ValueError('Invalid private directory permissions')


def read(path, uid, private=False, root_gid=None):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        owner_ok = info.st_uid == uid or (not private and root_gid is not None
                                        and info.st_uid == 0 and info.st_gid == root_gid
                                        and info.st_mode & 0o040)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not owner_ok
                or info.st_size > LIMIT or info.st_mode & 0o022
                or private and stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError('Invalid web file or permissions')
        raw = os.read(fd, LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('Web file exceeds bound')
        return raw.decode()
    finally:
        os.close(fd)


def create(path, raw, uid, gid):
    """Publish only a missing file, with durable private bytes before visibility."""
    payload = raw.encode()
    if len(payload) > LIMIT:
        raise ValueError('Web file exceeds bound')
    temporary = path.with_name('.web-' + secrets.token_hex(12))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchown(fd, uid, gid)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
    finally:
        temporary.unlink(missing_ok=True)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def validate_moonraker(raw):
    config = configparser.ConfigParser(interpolation=None, strict=True)
    config.read_string(raw)
    if (config.get('server', 'host') != '127.0.0.1'
            or config.getint('server', 'port') != 7125
            or config.get('machine', 'provider') != 'none'
            or config.getboolean('machine', 'validate_service', fallback=True)
            or config.getboolean('machine', 'validate_config', fallback=True)
            or not config.getboolean('authorization', 'force_logins')
            or not config.getboolean('authorization', 'enable_api_key', fallback=True)
            or config.has_section('include')):
        raise ValueError('Moonraker must require login on loopback')
    if any(section.startswith('include ') for section in config.sections()):
        raise ValueError('External Moonraker configuration is not admitted')
    trusted = config.get('authorization', 'trusted_clients', fallback='').split()
    if any(client not in ('127.0.0.1', '::1') for client in trusted):
        raise ValueError('Moonraker trust must remain loopback only')


def validate_nginx(raw, policy=None):
    if policy is not None:
        from sv08_mainsail_access import render
        if raw != render(policy): raise ValueError('Managed gateway disagrees with browser policy')
        return
    if raw.startswith('# SV08 managed browser access v1'):
        raise ValueError('Managed browser policy is required')
    # Inspect each lexical block, allowing existing accepted formatting/308 redirects.
    text = re.sub(r'#.*', '', raw)
    tokens = re.findall(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|[{};]|[^\s{};]+', text)
    stack = [[]]; blocks = []; directive = []
    for token in tokens:
        if token == '{':
            stack.append([]); directive = []
        elif token == ';':
            stack[-1].append(' '.join(directive)); directive = []
        elif token == '}':
            if len(stack) == 1 or directive: raise ValueError('Invalid gateway syntax')
            blocks.append(stack.pop()); directive = []
        else: directive.append(token)
    if len(stack) != 1 or directive: raise ValueError('Invalid gateway syntax')
    listens = [d for block in blocks for d in block if d.startswith('listen ')]
    if sorted(listens) != ['listen 8080', 'listen 8443 ssl']:
        raise ValueError('Unexpected web listener')
    if any(d in ('auth_basic off', 'satisfy any') for block in blocks for d in block):
        raise ValueError('Gateway authentication bypass')
    https = next(block for block in blocks if 'listen 8443 ssl' in block)
    if (not any(d.startswith('auth_basic ') for d in https)
            or 'auth_basic_user_file /data/sv08/mainsail-auth/users' not in https
            or 'ssl_certificate /data/sv08/system/identity/current/services/server.crt' not in https
            or 'ssl_certificate_key /data/sv08/system/identity/current/services/server.key' not in https):
        raise ValueError('HTTPS must use persistent identity and gateway authentication')
    proxies = [block for block in blocks if any(d.startswith('proxy_pass ') for d in block)]
    if len(proxies) != 2:
        raise ValueError('API and websocket proxy configuration required')
    for block in proxies:
        required = ['proxy_pass http://127.0.0.1:7125', 'proxy_set_header Authorization ""',
                    'include /data/sv08/mainsail-auth/moonraker-proxy.conf',
                    'proxy_set_header X-Real-IP $remote_addr',
                    'proxy_set_header X-Forwarded-For $remote_addr']
        if any(d not in block for d in required):
            raise ValueError('Proxy must authenticate and preserve browser address')


def credentials(raw):
    fields = {}
    for line in raw.splitlines():
        match = re.fullmatch(r'(?:Moonraker\s+)?(username|password)\s*[:=]\s*(\S+)', line, re.I)
        if match:
            name = match[1].lower()
            if name in fields: raise ValueError('Duplicate retrieval credential')
            fields[name] = match[2]
    if (set(fields) != {'username', 'password'} or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', fields['username'])
            or not 16 <= len(fields['password']) <= 256):
        raise ValueError('Invalid private retrieval credentials')
    return fields


def password_hash(password, salt=None):
    args = ['openssl', 'passwd', '-6', '-stdin']
    if salt is not None: args.extend(['-salt', salt])
    result = subprocess.run(args, input=password+'\n', text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=10, check=False)
    if result.returncode: raise ValueError('Password hashing failed')
    hashed = result.stdout.strip()
    if not re.fullmatch(r'\$6\$[A-Za-z0-9./]{1,16}\$[A-Za-z0-9./]{86}', hashed):
        raise ValueError('Invalid password hash')
    return hashed


class API:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, path, fields=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token: headers['Authorization'] = 'Bearer '+token
        request = urllib.request.Request('http://127.0.0.1:7125'+path,
                                         data=json.dumps(fields).encode() if fields is not None else None,
                                         headers=headers)
        try:
            # Native password/JWT creation can exceed readiness latency on slow hosts.
            timeout = 15 if path in ('/access/user', '/access/login') else 2
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read(LIMIT + 1)
            if len(raw) > LIMIT: raise ValueError('API response exceeds bound')
            return json.loads(raw)['result']
        except urllib.error.HTTPError as error:
            # Do not expose response bodies, request credentials, or tokens.
            raise ValueError('Loopback API rejected authentication operation') from None

    def ready(self):
        deadline = time.monotonic() + 45
        while True:
            try: self.request('/access/info'); return
            except (OSError, ValueError):
                if time.monotonic() >= deadline: raise ValueError('Loopback API readiness timeout') from None
                time.sleep(1)


class Web:
    def __init__(self, data='/data/sv08', config='/run/sv08/printer_data/config',
                 uid=1000, gid=1000, budget=None, api=None, root_uid=0):
        self.data = Path(data); self.config = Path(config).resolve(strict=True)
        self.uid = uid; self.gid = gid; self.root_uid = root_uid
        self.budget = budget or Budget(self.data)
        self.api = api or API()
        self.auth = self.data / 'mainsail-auth'
        self.login = self.data / 'moonraker-login.txt'

    def roots(self):
        for path in (self.data, *self.data.parents):
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022:
                raise ValueError('Invalid persistent web ancestry')
        directory(self.config, self.uid)
        for path in self.config.parents:
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022:
                raise ValueError('Invalid configuration ancestry')

    def prepare(self):
        self.roots()
        seeds = {'moonraker.conf': MOONRAKER, 'nginx-mainsail.conf': NGINX,
                 'mainsail.json': json.dumps(MAINSail, indent=2)+'\n'}
        with self.budget.locked():
            self.budget.check(6*LIMIT, inodes=12)
            managed = self.managed(prepare=True)
            for name, seed in seeds.items():
                path = self.config / name
                if not path.exists() and not path.is_symlink(): create(path, seed, self.uid, self.gid)
                raw = read(path, self.uid, root_gid=self.gid)
                if name == 'moonraker.conf': validate_moonraker(raw)
                elif name == 'nginx-mainsail.conf': validate_nginx(raw, managed)
                else: json.loads(raw)

    def managed(self, prepare=False):
        from sv08_mainsail_access import MainsailAccess
        access = MainsailAccess(self.data, self.config, self.uid, self.gid, root_uid=self.root_uid, budget=self.budget)
        if not access.root.exists() and not access.root.is_symlink(): return None
        access.recover_unlocked(reload=False)
        policy = access.load()
        if policy is not None: access.verify(policy, prepare=prepare)
        return policy

    def existing_gateway(self, fields):
        users = self.auth / 'users'; proxy = self.auth / 'moonraker-proxy.conf'
        exists = [p.exists() or p.is_symlink() for p in (users, proxy)]
        if exists[0]:
            raw = read(users, self.uid, True)
            match = re.fullmatch(r'([A-Za-z0-9_-]+):(\$6\$([A-Za-z0-9./]{1,16})\$[A-Za-z0-9./]{86})\n?', raw)
            if (not match or match[1] != fields['username']
                    or not hmac.compare_digest(match[2], password_hash(fields['password'], match[3]))):
                raise ValueError('Gateway and retrieval credentials disagree')
        if exists[1]: self.proxy_key()
        return all(exists)

    def proxy_key(self):
        match = re.fullmatch(r'\s*proxy_set_header\s+X-Api-Key\s+(?:"([a-fA-F0-9]{32})"|([a-fA-F0-9]{32}));\s*',
                             read(self.auth / 'moonraker-proxy.conf', self.uid, True))
        if not match: raise ValueError('Invalid private API key include')
        return match[1] or match[2]

    def authenticate(self):
        self.roots()
        self.api.ready()
        with self.budget.locked():
            self.budget.check(6*LIMIT, inodes=12)
            if self.managed() is not None:
                # Browser password changes never reset or compare native credentials.
                self.proxy_key()
                return
            if not self.auth.exists() and not self.auth.is_symlink():
                self.auth.mkdir(mode=0o700); os.chown(self.auth, self.uid, self.gid)
            directory(self.auth, self.uid, 0o700)
            if self.login.exists() or self.login.is_symlink():
                fields = credentials(read(self.login, self.uid, True))
            else:
                if any(self.auth.iterdir()): raise ValueError('Missing retrieval credentials; existing gateway retained')
                # Only create credentials when native account enumeration proves fresh state.
                if self.api.request('/access/users/list')['users']:
                    raise ValueError('Unknown native account; refusing reset')
                fields = {'username': 'sv08', 'password': secrets.token_urlsafe(32)}
                create(self.login, 'Moonraker username: '+fields['username']+'\nMoonraker password: '+fields['password']+'\n', self.uid, self.gid)
            if self.existing_gateway(fields): return
            try:
                login = self.api.request('/access/login', fields)
            except ValueError:
                if self.api.request('/access/users/list')['users']:
                    raise ValueError('Native account mismatch; refusing reset') from None
                login = self.api.request('/access/user', fields)
            key = self.api.request('/access/api_key', token=login['token'])
            if not isinstance(key, str) or not re.fullmatch(r'[a-fA-F0-9]{32}', key):
                raise ValueError('Invalid native API key')
            proxy = self.auth / 'moonraker-proxy.conf'
            users = self.auth / 'users'
            if proxy.exists() and not hmac.compare_digest(self.proxy_key(), key):
                raise ValueError('Partial gateway native API key mismatch; retained')
            if not users.exists():
                hashed = password_hash(fields['password'])
                create(users, fields['username']+':'+hashed+'\n', self.uid, self.gid)
            if not proxy.exists():
                create(proxy, 'proxy_set_header X-Api-Key '+key+';\n', self.uid, self.gid)
            self.existing_gateway(fields)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['prepare', 'auth'])
    args = parser.parse_args()
    if os.geteuid() != 0: raise ValueError('Web preparation requires root')
    web = Web()
    if args.operation == 'prepare': web.prepare()
    else: web.authenticate()


if __name__ == '__main__':
    try: main()
    except Exception:
        # Never let API exception text or private material enter the service journal.
        raise SystemExit('SV08 web provisioning failed closed; private state retained') from None
