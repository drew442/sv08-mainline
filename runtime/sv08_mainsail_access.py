#!/usr/bin/env python3
"""Root-only browser access policy; native Moonraker and admin identity stay separate.

A durable transaction retains old gateway bytes until validation and reload finish.
Boot recovery rolls incomplete changes back; no client private key is persisted.
"""
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import time

from sv08_data_budget import Budget
from sv08_printer_stack import NGINX
from sv08_web import directory, read, password_hash, validate_nginx

LIMIT = 64 * 1024
MARKER = '# SV08 managed browser access v1\n'
HASH = r'\$6\$[A-Za-z0-9./]{1,16}\$[A-Za-z0-9./]{86}'


def run(*args, input=None):
    result = subprocess.run(list(args), input=input, capture_output=True, timeout=20)
    if result.returncode: raise ValueError('Browser access operation failed; prior access retained')
    return result.stdout


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('Duplicate request or policy field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def secret(value):
    if (not isinstance(value, str) or not 8 <= len(value.encode()) <= 256
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('Password must be 8 to 256 UTF-8 bytes without control characters')
    return value


def validate_policy(policy):
    if (not isinstance(policy, dict) or set(policy) != {'version', 'mode', 'username', 'hash', 'ca', 'ca_fingerprint', 'certificates'}
            or type(policy['version']) is not int or policy['version'] != 1
            or policy['mode'] not in ('password', 'none', 'certificate')
            or not isinstance(policy['username'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', policy['username'])
            or not isinstance(policy['hash'], str) or not re.fullmatch(HASH, policy['hash'])
            or not isinstance(policy['certificates'], list) or len(policy['certificates']) > 32):
        raise ValueError('Invalid browser access policy')
    if not isinstance(policy['ca'], str) or len(policy['ca']) > 8192:
        raise ValueError('Invalid browser certificate authority')
    if policy['ca']:
        if not isinstance(policy['ca_fingerprint'],str) or not re.fullmatch(r'[a-f0-9]{64}', policy['ca_fingerprint']): raise ValueError('Invalid browser certificate authority')
    elif policy['ca_fingerprint'] != '' or policy['certificates']:
        raise ValueError('Missing browser certificate authority')
    ids = set(); fingerprints = set()
    for cert in policy['certificates']:
        if (not isinstance(cert, dict) or set(cert) != {'id','label','fingerprint','nginx_fingerprint','created','expires','revoked'}
                or not isinstance(cert['id'], str) or not re.fullmatch(r'[a-f0-9]{32}', cert['id'])
                or not isinstance(cert['label'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}', cert['label'])
                or not isinstance(cert['fingerprint'], str) or not re.fullmatch(r'[a-f0-9]{64}', cert['fingerprint'])
                or not isinstance(cert['nginx_fingerprint'], str) or not re.fullmatch(r'[a-f0-9]{40}', cert['nginx_fingerprint'])
                or type(cert['created']) is not int or type(cert['expires']) is not int
                or cert['created'] < 0 or cert['expires'] <= cert['created']
                or type(cert['revoked']) is not bool
                or cert['id'] in ids or cert['nginx_fingerprint'] in fingerprints):
            raise ValueError('Invalid browser client certificate policy')
        ids.add(cert['id']); fingerprints.add(cert['nginx_fingerprint'])
    return policy


def active(policy):
    return [c for c in policy['certificates'] if not c['revoked'] and c['expires'] > time.time()]


def render(policy):
    validate_policy(policy)
    auth = '    auth_basic "SV08 printer";\n    auth_basic_user_file /data/sv08/mainsail-auth/users;\n'
    prefix = MARKER
    if policy['mode'] == 'none': replacement = '    auth_basic off;\n'
    elif policy['mode'] == 'certificate':
        # ARM nginx defaults to 32-byte buckets, smaller than a SHA1 key.
        prefix += 'map_hash_bucket_size 64;\nmap $ssl_client_fingerprint $sv08_client_allowed {\n    default 0;\n'
        # Expiry is checked by TLS, so rendered bytes do not change with wall time.
        for cert in policy['certificates']:
            if not cert['revoked']: prefix += '    "'+cert['nginx_fingerprint']+'" 1;\n'
        prefix += '}\n'
        replacement = ('    auth_basic off;\n    ssl_client_certificate /data/sv08/mainsail-auth/client-ca.crt;\n'
                       '    ssl_verify_client on;\n    ssl_verify_depth 1;\n'
                       '    if ($sv08_client_allowed = 0) { return 403; }\n')
    else: replacement = auth
    return prefix + NGINX.replace(auth, replacement)


class MainsailAccess:
    def __init__(self, data='/data/sv08', config='/run/sv08/printer_data/config', uid=1000, gid=1000,
                 root_uid=0, budget=None, controller=None, temporary=None):
        self.data = Path(data); self.config = Path(config).resolve(strict=True)
        self.uid, self.gid, self.root_uid = uid, gid, root_uid
        self.root = self.data/'system/mainsail-access'; self.state = self.root/'policy.json'
        self.journal = self.root/'transaction.json'; self.auth = self.data/'mainsail-auth'
        self.budget = budget or Budget(self.data)
        self.controller = controller or self.service
        self.temporary = temporary

    def service(self, operation):
        if operation == 'test': run('/usr/sbin/nginx', '-t', '-c', '/etc/sv08/nginx-mainsail-service.conf')
        else:
            # An inactive gateway has no workers to reload; boot will validate it.
            result = subprocess.run(['systemctl','is-active','--quiet','sv08-mainsail.service'], capture_output=True, timeout=10)
            if result.returncode == 0: run('systemctl','reload','sv08-mainsail.service')
            elif result.returncode not in (3,): raise ValueError('Cannot determine gateway service state')

    def roots(self):
        for path in (self.data, *self.data.parents):
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, self.root_uid, os.geteuid()) or info.st_mode & 0o022:
                raise ValueError('Invalid browser access ancestry')
        directory(self.config, self.uid)
        for path in self.config.parents:
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022: raise ValueError('Invalid gateway ancestry')
        directory(self.auth, self.uid, 0o700)
        system = self.data/'system'
        if not system.exists(): system.mkdir(mode=0o711); os.chown(system, self.root_uid, self.root_uid)
        directory(system, self.root_uid)
        if not self.root.exists(): self.root.mkdir(mode=0o700); os.chown(self.root, self.root_uid, self.root_uid)
        directory(self.root, self.root_uid, 0o700)

    def write(self, path, raw, mode=0o600, uid=None, gid=None):
        if len(raw.encode()) > LIMIT: raise ValueError('Browser access file exceeds bound')
        if path.exists() or path.is_symlink():
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1: raise ValueError('Invalid browser access file')
        temporary = path.with_name('.access-'+secrets.token_hex(12))
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        try:
            os.fchown(fd, self.root_uid if uid is None else uid, self.root_uid if gid is None else gid)
            os.fchmod(fd, mode)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw.encode()); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path); self.sync(path.parent)
        finally: temporary.unlink(missing_ok=True)

    def sync(self, path):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try: os.fsync(fd)
        finally: os.close(fd)

    def load(self):
        if not self.state.exists() and not self.state.is_symlink(): return None
        return validate_policy(decode(read(self.state, self.root_uid, True)))

    def gateway_read(self, path):
        # Managed rendered files are root owned and readable by the nginx group.
        return read(path, self.uid, root_gid=self.gid)

    def initial(self):
        raw = read(self.auth/'users', self.uid, True)
        match = re.fullmatch(r'([A-Za-z0-9_-]{1,64}):('+HASH+r')\n?', raw)
        if not match: raise ValueError('Existing browser credentials are not valid')
        config = self.gateway_read(self.config/'nginx-mainsail.conf')
        if config.startswith(MARKER): raise ValueError('Managed browser policy is missing; restore explicitly')
        validate_nginx(config)
        if (self.auth/'client-ca.crt').exists() or (self.auth/'client-ca.crt').is_symlink():
            raise ValueError('Unknown browser client authority retained; inspect before migration')
        return dict(version=1, mode='password', username=match[1], hash=match[2], ca='', ca_fingerprint='', certificates=[])

    def ca(self):
        # Only the documented identity selector is followed, never arbitrary links.
        root = self.data/'system/identity'; directory(root, self.root_uid)
        selector = root/'current'
        if not selector.is_symlink(): raise ValueError('Printer certificate authority unavailable')
        target = os.readlink(selector)
        if not re.fullmatch(r'generations/[a-f0-9]{32}', target): raise ValueError('Invalid identity selector')
        generation = root/target
        for path in (root/'generations', generation, generation/'ca'): directory(path, self.root_uid)
        cert, key = generation/'ca/ca.crt', generation/'ca/ca.key'
        raw = read(cert, self.root_uid); read(key, self.root_uid, True)
        der = run('openssl','x509','-in',str(cert),'-outform','DER')
        return raw, hashlib.sha256(der).hexdigest(), cert, key

    def authority(self, policy):
        if policy['ca']:
            raw, fingerprint, _, _ = self.ca()
            if fingerprint != policy['ca_fingerprint'] or raw != policy['ca']:
                raise ValueError('Browser certificates belong to another printer authority; regenerate explicitly')

    def snapshot(self):
        result = {}
        for name, path in self.files().items():
            result[name] = self.gateway_read(path) if path.exists() or path.is_symlink() else None
        return result

    def files(self):
        return {'nginx':self.config/'nginx-mainsail.conf', 'users':self.auth/'users', 'ca':self.auth/'client-ca.crt'}

    def outputs(self, policy):
        return {'nginx':render(policy),'users':policy['username']+':'+policy['hash']+'\n','ca':policy['ca'] or None}

    def publish(self, outputs, metadata=None):
        for name, path in self.files().items():
            if outputs[name] is not None:
                mode, uid, gid = metadata[name] if metadata else (0o640, self.root_uid, self.gid)
                self.write(path, outputs[name], mode, uid, gid)
            elif path.exists() or path.is_symlink():
                self.gateway_read(path); path.unlink(); self.sync(path.parent)

    def verify(self, policy, prepare=False, check_authority=True):
        if check_authority and policy['mode'] == 'certificate': self.authority(policy)
        expected = self.outputs(policy); current = self.snapshot()
        if prepare and current['nginx'] != expected['nginx']:
            # The configuration publisher emits the legacy template on hardware apply.
            # Admit that known template only, then reconstruct the managed gateway.
            if current['nginx'] != NGINX: raise ValueError('Managed gateway configuration disagrees with policy')
            self.write(self.files()['nginx'], expected['nginx'], 0o640, self.root_uid, self.gid)
            current['nginx'] = expected['nginx']
        if current != expected: raise ValueError('Managed browser gateway disagrees with policy')

    def recover_unlocked(self, reload=True):
        self.roots()
        if not self.journal.exists() and not self.journal.is_symlink(): return
        journal = decode(read(self.journal, self.root_uid, True))
        if (not isinstance(journal, dict) or set(journal) != {'old','desired','previous','metadata','rollback'}
                or type(journal['rollback']) is not bool
                or not isinstance(journal['old'], dict) or set(journal['old']) != {'nginx','users','ca'}
                or any(v is not None and (not isinstance(v,str) or len(v.encode()) > LIMIT) for v in journal['old'].values())):
            raise ValueError('Invalid browser recovery transaction')
        metadata = journal['metadata']
        if not isinstance(metadata, dict) or set(metadata) != {'nginx','users','ca'}:
            raise ValueError('Invalid browser recovery metadata')
        for values in metadata.values():
            if (not isinstance(values,list) or len(values) != 3 or any(type(v) is not int for v in values)
                    or values[0] not in (0o600,0o640,0o644)
                    or values[1] not in (self.root_uid,self.uid) or values[2] not in (self.root_uid,self.gid)):
                raise ValueError('Invalid browser recovery permissions')
        desired = validate_policy(journal['desired']); previous = journal['previous']
        if previous is not None:
            validate_policy(previous)
            if journal['old'] != self.outputs(previous): raise ValueError('Browser recovery gateway conflict')
        else:
            if journal['old']['nginx'] is None or journal['old']['users'] is None or journal['old']['ca'] is not None:
                raise ValueError('Invalid legacy browser recovery state')
            validate_nginx(journal['old']['nginx'])
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}:'+HASH+r'\n?', journal['old']['users']):
                raise ValueError('Invalid legacy browser recovery credentials')
        policy = self.load()
        committed = policy == desired and not journal['rollback']
        outputs = self.outputs(desired) if committed else journal['old']
        # A changed root policy is not an interrupted transaction we can repair.
        if policy not in (previous, desired): raise ValueError('Browser recovery policy conflict')
        self.publish(outputs, None if committed else metadata)
        if reload: self.controller('test'); self.controller('reload')
        if journal['rollback']:
            if previous is None:
                self.state.unlink(missing_ok=True); self.sync(self.root)
            else: self.write(self.state,json.dumps(previous)+'\n')
        self.journal.unlink(); self.sync(self.root)

    def change(self, previous, desired):
        validate_policy(desired)
        self.budget.check(8*LIMIT, inodes=16)
        metadata = {}
        for name, path in self.files().items():
            info = path.lstat() if path.exists() or path.is_symlink() else None
            metadata[name] = [stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid] if info else [0o640,self.root_uid,self.gid]
        journal = {'old':self.snapshot(),'desired':desired,'previous':previous,'metadata':metadata,'rollback':False}
        self.write(self.journal, json.dumps(journal)+'\n')
        try:
            self.publish(self.outputs(desired)); self.controller('test'); self.controller('reload')
            self.write(self.state, json.dumps(desired)+'\n')
        except Exception:
            # Mark caught failures for rollback even if policy replace succeeded.
            # Process interruptions instead use the durable policy commit boundary.
            journal['rollback'] = True
            self.write(self.journal,json.dumps(journal)+'\n')
            self.recover_unlocked(); raise
        self.journal.unlink(); self.sync(self.root)

    def status(self, policy, managed):
        authority_valid = True
        try: self.authority(policy)
        except (OSError, ValueError): authority_valid = False
        return {'authority_valid':authority_valid,
                'warning':'' if authority_valid else 'Printer authority changed; generate a new client certificate or choose password/no login mode',
                'mode':policy['mode'],'username':policy['username'],'managed':managed,
                'ca_fingerprint':policy['ca_fingerprint'],
                'certificates':[{k:v for k,v in c.items() if k != 'nginx_fingerprint'} for c in policy['certificates']]}

    def issue(self, policy, label, password):
        if not isinstance(label,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}',label):
            raise ValueError('Certificate label must be 1 to 64 simple characters')
        secret(password)
        if len(policy['certificates']) >= 32: raise ValueError('Browser certificate storage is full')
        raw, fingerprint, ca, ca_key = self.ca()
        if policy['ca_fingerprint'] and fingerprint != policy['ca_fingerprint']:
            # A deliberately restored CA cannot authorize the old client certificates.
            for cert in policy['certificates']: cert['revoked'] = True
        policy['ca'], policy['ca_fingerprint'] = raw, fingerprint
        with tempfile.TemporaryDirectory(prefix='sv08-client-', dir=self.temporary) as temporary:
            work = Path(temporary); work.chmod(0o700)
            key, csr, cert, ext = [work/n for n in ('client.key','client.csr','client.crt','extensions')]
            run('openssl','req','-new','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(csr),'-subj','/CN='+label)
            key.chmod(0o600)
            ext.write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=clientAuth\n')
            identifier = secrets.token_hex(16)
            run('openssl','x509','-req','-in',str(csr),'-CA',str(ca),'-CAkey',str(ca_key),'-set_serial','0x'+identifier,
                '-days','365','-sha256','-extfile',str(ext),'-out',str(cert))
            run('openssl','verify','-purpose','sslclient','-CAfile',str(ca),str(cert))
            der = run('openssl','x509','-in',str(cert),'-outform','DER')
            expires = run('openssl','x509','-in',str(cert),'-enddate','-noout').decode().strip().split('=',1)[1]
            metadata = dict(id=identifier,label=label,fingerprint=hashlib.sha256(der).hexdigest(),
                            nginx_fingerprint=hashlib.sha1(der).hexdigest(),created=int(time.time()),
                            expires=int(datetime.strptime(expires,'%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc).timestamp()),revoked=False)
            bundle = run('openssl','pkcs12','-export','-inkey',str(key),'-in',str(cert),'-certfile',str(ca),
                         '-name',label,'-passout','stdin',input=(password+'\n').encode())
            if len(bundle) > LIMIT: raise ValueError('Client certificate download exceeds bound')
        policy['certificates'].append(metadata)
        return {'certificate':{k:v for k,v in metadata.items() if k != 'nginx_fingerprint'},
                'filename':'sv08-'+identifier+'.p12','pkcs12_base64':base64.b64encode(bundle).decode()}

    def request(self, request):
        if not isinstance(request,dict): raise ValueError('Invalid browser access request')
        method = request.get('method')
        allowed = {'status':{'method'},'settings':{'method','mode','password'},
                   'certificate.create':{'method','label','password'},'certificate.revoke':{'method','id'}}
        if not isinstance(method,str) or method not in allowed or set(request)-allowed[method]: raise ValueError('Invalid browser access request')
        with self.budget.locked():
            self.budget.check(8*LIMIT,inodes=16); self.recover_unlocked()
            previous = self.load(); policy = copy.deepcopy(previous) if previous else self.initial()
            if previous:
                # Creating certificates is the explicit recovery for a restored CA.
                if method != 'certificate.create': self.verify(previous, check_authority=method not in ('status','settings'))
                elif self.snapshot() != self.outputs(previous): raise ValueError('Managed browser gateway disagrees with policy')
            if method == 'status': return self.status(policy, previous is not None)
            result = None
            if method == 'settings':
                mode = request.get('mode')
                if mode not in ('password','none','certificate'): raise ValueError('Invalid browser access mode')
                if 'password' in request:
                    if mode != 'password': raise ValueError('Password applies only to password mode')
                    policy['hash'] = password_hash(secret(request['password']))
                if mode == 'certificate':
                    self.authority(policy)
                    if not active(policy): raise ValueError('Create an active client certificate before enabling certificate mode')
                policy['mode'] = mode
            elif method == 'certificate.create': result = self.issue(policy, request.get('label'), request.get('password'))
            else:
                identifier = request.get('id')
                matches = [c for c in policy['certificates'] if c['id'] == identifier]
                if not matches: raise ValueError('Unknown browser certificate')
                matches[0]['revoked'] = True
            self.change(previous, policy)
            return result if result is not None else self.status(policy, True)


def main():
    if os.geteuid() != 0: raise ValueError('Browser access management requires root')
    raw = sys.stdin.buffer.read(LIMIT+1)
    if len(raw) > LIMIT: raise ValueError('Browser access request exceeds bound')
    result = MainsailAccess().request(decode(raw))
    print(json.dumps({'ok':True,'result':result}))


if __name__ == '__main__':
    try: main()
    except Exception:
        # Never expose subprocess output, password, native key, or private key.
        print(json.dumps({'ok':False,'error':'Browser access operation failed; reload and review the access state'}))
        raise SystemExit(1) from None
