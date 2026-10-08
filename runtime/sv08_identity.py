#!/usr/bin/env python3
"""Printer authority and service certificates. No hardware or arbitrary commands."""
import base64
from contextlib import contextmanager
import fcntl
import hashlib
from io import BytesIO
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import uuid
from zipfile import ZipFile, ZIP_STORED, BadZipFile
from sv08_data_budget import Budget

LIMIT = 1024 * 1024
AUTHORITY = ('ca/ca.crt', 'ca/ca.key', 'ssh/ssh_host_ed25519_key',
             'ssh/ssh_host_ed25519_key.pub', 'users/sv08/authorized_keys')


def run(*args, input=None):
    result = subprocess.run(list(args), input=input, capture_output=True, timeout=20)
    if result.returncode:
        # Tool stderr can contain input paths/key data; never expose it via RPC.
        raise ValueError('Identity cryptographic validation failed')
    return result.stdout


def fsync(path):
    fd = os.open(path, os.O_RDONLY | (os.O_DIRECTORY if path.is_dir() else 0))
    try: os.fsync(fd)
    finally: os.close(fd)


def normal_names(names):
    result = {'DNS:localhost', 'IP:127.0.0.1', 'IP:::1'}
    if not isinstance(names, list) or len(names) > 64:
        raise ValueError('Invalid certificate names')
    for value in names:
        if not isinstance(value, str): raise ValueError('Invalid certificate name')
        try: result.add('IP:' + str(ipaddress.ip_address(value)))
        except ValueError:
            if not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,251}[a-zA-Z0-9])?', value):
                raise ValueError('Invalid certificate name')
            result.add('DNS:' + value.lower())
    return sorted(result)


def public_keys(raw):
    if not isinstance(raw, str) or len(raw.encode()) > 65536:
        raise ValueError('SSH public keys must be at most 64 KiB')
    result, fingerprints = [], set()
    for line in raw.splitlines():
        if not line.strip(): continue
        fields = line.split(None, 2)
        if len(fields) < 2 or fields[0] not in ('ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521', 'sk-ssh-ed25519@openssh.com', 'sk-ecdsa-sha2-nistp256@openssh.com'):
            raise ValueError('Upload SSH public keys, one per line; private keys and key options are not accepted')
        with tempfile.TemporaryDirectory(prefix='sv08-public-key-') as work:
            path = Path(work) / 'key.pub'; path.write_text(line + '\n')
            fingerprint = run('ssh-keygen', '-l', '-E', 'sha256', '-f', str(path)).decode().split()[1]
        if fingerprint not in fingerprints:
            result.append(line.strip()); fingerprints.add(fingerprint)
    if not result or len(result) > 64: raise ValueError('Keep between one and 64 authorized public keys')
    return ('\n'.join(result) + '\n').encode()


class Identity:
    def __init__(self, data='/data/sv08', owner_uid=1000, owner_gid=1000, root_uid=0, budget=None):
        self.data = Path(data); self.root = self.data / 'system/identity'
        self.owner_uid, self.owner_gid, self.root_uid = owner_uid, owner_gid, root_uid
        self.budget = budget if budget is not None else Budget(self.data)

    def safe(self, path):
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Identity storage must not contain unexpected symlinks')
        if path.exists() and not (path.is_file() or path.is_dir()):
            raise ValueError('Invalid identity file type')
        if path.is_file() and path.stat().st_nlink != 1:
            raise ValueError('Identity files must not have hard links')
        return path

    @contextmanager
    def locked(self):
        self.safe(self.root); self.root.mkdir(mode=0o711, parents=True, exist_ok=True)
        self.root.chmod(0o711)
        lock = self.safe(self.root / '.lock')
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.budget.locked(): yield
        except BlockingIOError: raise ValueError('Printer identity is busy; reload before retrying')
        finally: os.close(fd)

    def current(self):
        pointer = self.root / 'current'
        if not pointer.is_symlink():
            if pointer.exists(): raise ValueError('Invalid identity selector')
            return None
        target = os.readlink(pointer)
        if not re.fullmatch(r'generations/[0-9a-f]{32}', target):
            raise ValueError('Invalid identity generation')
        path = self.safe(self.root / target)
        if not path.is_dir(): raise ValueError('Selected printer identity is missing; restore it explicitly')
        return path

    def put(self, path, raw, mode=0o600, owner=False, service=False):
        path.parent.mkdir(mode=0o711, parents=True, exist_ok=True)
        with path.open('xb') as stream:
            os.fchmod(stream.fileno(), mode)
            os.fchown(stream.fileno(), self.owner_uid if owner else self.root_uid,
                      self.owner_gid if owner or service else self.root_uid)
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())

    def validate(self, path):
        for name in AUTHORITY:
            p = self.safe(path / name)
            if not p.is_file() or p.stat().st_size > 65536: raise ValueError('Incomplete identity bundle')
            st = p.stat()
            if st.st_mode & 0o022: raise ValueError('Identity files must not be writable by other users')
            if name in ('ca/ca.key','ssh/ssh_host_ed25519_key') and (st.st_uid != self.root_uid or st.st_mode & 0o077):
                raise ValueError('Identity authority keys must remain private to root')
        ca = path / 'ca/ca.crt'; key = path / 'ca/ca.key'
        cert_pub = run('openssl', 'x509', '-in', str(ca), '-pubkey', '-noout')
        key_pub = run('openssl', 'pkey', '-in', str(key), '-pubout')
        if cert_pub != key_pub: raise ValueError('CA certificate and private key do not match')
        text = run('openssl', 'x509', '-in', str(ca), '-text', '-noout').decode()
        if 'CA:TRUE' not in text or 'Certificate Sign' not in text:
            raise ValueError('Certificate is not a signing CA')
        run('openssl', 'verify', '-CAfile', str(ca), str(ca))
        run('openssl', 'pkey', '-in', str(key), '-check', '-noout')
        actual = run('ssh-keygen', '-y', '-P', '', '-f', str(path / 'ssh/ssh_host_ed25519_key')).decode().split()
        supplied = (path / 'ssh/ssh_host_ed25519_key.pub').read_text().split()
        if actual[:2] != supplied[:2] or not actual or actual[0] != 'ssh-ed25519':
            raise ValueError('SSH host private/public keys do not match')
        public_keys((path / 'users/sv08/authorized_keys').read_text())

    def new_generation(self, assets=None):
        self.budget.check(2*LIMIT, inodes=64)
        generations = self.safe(self.root / 'generations'); generations.mkdir(mode=0o711, exist_ok=True)
        if len(list(generations.iterdir())) >= 8:
            raise ValueError('Identity generation storage needs inspection before more changes')
        path = generations / uuid.uuid4().hex; path.mkdir(mode=0o711)
        if assets:
            for name in AUTHORITY:
                self.put(path / name, assets[name], owner=name.startswith('users/'),
                         mode=0o644 if name.endswith('.pub') or name.endswith('.crt') else 0o600)
        (path / 'ca').mkdir(mode=0o700, exist_ok=True); (path / 'ca').chmod(0o700)
        return path

    def sign(self, path, names):
        services = path / 'services'; services.mkdir(mode=0o711)
        with tempfile.TemporaryDirectory(prefix='.sign-', dir=self.root) as work:
            work = Path(work); csr = work / 'server.csr'; key = services / 'server.key'
            run('openssl', 'req', '-new', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key),
                '-out', str(csr), '-subj', '/CN=SV08 Mainline printer')
            ext = work / 'extensions'; ext.write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=' + ','.join(names) + '\n')
            cert = services / 'server.crt'
            run('openssl', 'x509', '-req', '-in', str(csr), '-CA', str(path / 'ca/ca.crt'),
                '-CAkey', str(path / 'ca/ca.key'), '-set_serial', '0x' + uuid.uuid4().hex,
                '-days', '365', '-sha256', '-extfile', str(ext), '-out', str(cert))
            run('openssl', 'verify', '-purpose', 'sslserver', '-CAfile', str(path / 'ca/ca.crt'), str(cert))
            os.chown(key, self.root_uid, self.owner_gid); key.chmod(0o640)
            os.chown(cert, self.root_uid, self.root_uid); cert.chmod(0o644)
            fsync(key); fsync(cert)
            cockpit = path / 'cockpit'; cockpit.mkdir(mode=0o700)
            self.put(cockpit / '50-printer.cert', cert.read_bytes() + (path / 'ca/ca.crt').read_bytes() + key.read_bytes())
            self.put(path / 'names.json', (json.dumps(names) + '\n').encode(), 0o644)

    def select(self, path):
        for file in (p for p in path.rglob('*') if p.is_file()): fsync(file)
        for directory in sorted((p for p in path.rglob('*') if p.is_dir()), key=lambda p:len(p.parts), reverse=True): fsync(directory)
        fsync(path); fsync(path.parent)
        old = self.current()
        previous = self.root / 'previous'
        if previous.exists() and not previous.is_symlink(): raise ValueError('Invalid previous identity selector')
        if previous.is_symlink() and not re.fullmatch(r'generations/[0-9a-f]{32}', os.readlink(previous)):
            raise ValueError('Invalid previous identity selector')
        if old:
            temporary_previous = self.root / ('.previous-' + uuid.uuid4().hex)
            temporary_previous.symlink_to('generations/' + old.name)
            os.replace(temporary_previous, previous); fsync(self.root)
        temporary = self.root / ('.current-' + uuid.uuid4().hex)
        temporary.symlink_to('generations/' + path.name)
        try: os.replace(temporary, self.root / 'current'); fsync(self.root)
        finally: temporary.unlink(missing_ok=True)
        # Keep the active and immediately previous complete identity. Unknown or
        # interrupted generations are retained for inspection and count toward cap.
        for candidate in path.parent.iterdir():
            if candidate in (path, old) or not re.fullmatch('[0-9a-f]{32}', candidate.name): continue
            if not candidate.is_symlink() and (candidate / 'names.json').is_file():
                try: self.validate(candidate)
                except (ValueError, OSError): continue
                shutil.rmtree(candidate)
        fsync(path.parent)

    def ensure(self, names, renew=False):
        names = normal_names(names)
        with self.locked():
            current = self.current()
            if current:
                self.validate(current)
                if not renew and json.loads((current / 'names.json').read_text()) == names:
                    result = subprocess.run(['openssl', 'x509', '-in', str(current / 'services/server.crt'), '-checkend', str(30*86400), '-noout'], capture_output=True, timeout=20)
                    if result.returncode == 0: return self.status_unlocked(current)
                path = self.new_generation({n:(current / n).read_bytes() for n in AUTHORITY})
            else:
                path = self.new_generation()
                legacy = self.safe(self.data / 'system/ssh/ssh_host_ed25519_key')
                if legacy.is_file():
                    self.put(path / 'ssh/ssh_host_ed25519_key', legacy.read_bytes())
                    pub = run('ssh-keygen', '-y', '-P', '', '-f', str(legacy))
                    self.put(path / 'ssh/ssh_host_ed25519_key.pub', pub, 0o644)
                else:
                    ssh = path / 'ssh'; ssh.mkdir(mode=0o711)
                    run('ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(ssh / 'ssh_host_ed25519_key'))
                legacy_keys = self.safe(self.data / 'users/sv08/.ssh/authorized_keys')
                self.put(path / 'users/sv08/authorized_keys', public_keys(legacy_keys.read_text()), owner=True)
                run('openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-sha256', '-days', '7300',
                    '-keyout', str(path / 'ca/ca.key'), '-out', str(path / 'ca/ca.crt'), '-subj', '/CN=SV08 Mainline printer CA',
                    '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0',
                    '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
                (path / 'ca/ca.key').chmod(0o600)
                (path / 'ca/ca.crt').chmod(0o644)
            try:
                self.validate(path); self.sign(path, names); self.select(path)
            except BaseException:
                shutil.rmtree(path); raise
            return self.status_unlocked(path)

    def status_unlocked(self, path):
        der = run('openssl', 'x509', '-in', str(path / 'ca/ca.crt'), '-outform', 'DER')
        ssh = run('ssh-keygen', '-l', '-E', 'sha256', '-f', str(path / 'ssh/ssh_host_ed25519_key.pub')).decode().split()[1]
        return dict(revision=path.name, ca_fingerprint=hashlib.sha256(der).hexdigest(),
                    ssh_fingerprint=ssh, authorized_keys=(path / 'users/sv08/authorized_keys').read_text(),
                    service_names=json.loads((path / 'names.json').read_text()))

    def decode_bundle(self, encoded):
        if not isinstance(encoded, str) or len(encoded) > (LIMIT*4//3+4): raise ValueError('Identity bundle is too large')
        try: raw = base64.b64decode(encoded, validate=True)
        except ValueError: raise ValueError('Invalid identity bundle')
        if len(raw) > LIMIT: raise ValueError('Identity bundle is too large')
        try:
            with ZipFile(BytesIO(raw)) as archive:
                entries = archive.infolist()
                if len(entries) != len(AUTHORITY)+1 or set(i.filename for i in entries) != set(AUTHORITY)|{'manifest.json'}:
                    raise ValueError('Unexpected identity bundle entries')
                if sum(i.file_size for i in entries) > LIMIT or any(i.file_size > 65536 or i.flag_bits & 1 for i in entries):
                    raise ValueError('Invalid identity bundle size')
                assets = {n:archive.read(n) for n in AUTHORITY}
                manifest = json.loads(archive.read('manifest.json'))
        except (OSError, RuntimeError, KeyError, BadZipFile, json.JSONDecodeError) as error:
            raise ValueError('Invalid identity bundle') from error
        if manifest != dict(format_version=1, kind='sv08-printer-identity', sha256={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()}):
            raise ValueError('Identity bundle manifest does not match its contents')
        self.budget.check(2*LIMIT, inodes=64)
        with tempfile.TemporaryDirectory(prefix='.validate-', dir=self.root) as work:
            work = Path(work)
            for n,raw in assets.items(): self.put(work / n, raw)
            self.validate(work)
        return assets

    def request(self, request):
        methods = {'status','ca.download','bundle.export','bundle.preview','bundle.restore','keys.replace'}
        method = request.get('method')
        if method not in methods: raise ValueError('Unknown identity operation')
        expected_fields = {'method'} | ({'bundle'} if method == 'bundle.preview' else {'bundle','revision'} if method == 'bundle.restore' else {'keys','revision'} if method == 'keys.replace' else set())
        if set(request) != expected_fields: raise ValueError('Unexpected identity request fields')
        with self.locked():
            current = self.current()
            if current is None: raise ValueError('Printer identity has not been provisioned')
            try: self.validate(current); healthy = True
            except (ValueError,OSError): healthy = False
            if method == 'status':
                if healthy: return dict(self.status_unlocked(current),healthy=True)
                return dict(revision=current.name,healthy=False,ca_fingerprint='Unavailable — restore identity',ssh_fingerprint='Unavailable — restore identity',authorized_keys='')
            if not healthy and method not in ('bundle.preview','bundle.restore'):
                raise ValueError('Printer authority is damaged; restore a verified identity backup')
            if method == 'ca.download': return dict(filename='sv08-printer-ca.crt', content=(current / 'ca/ca.crt').read_text())
            if method == 'bundle.export':
                assets = {n:(current / n).read_bytes() for n in AUTHORITY}
                manifest = dict(format_version=1, kind='sv08-printer-identity', sha256={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()})
                buffer = BytesIO()
                with ZipFile(buffer, 'w', compression=ZIP_STORED) as archive:
                    for n,raw in assets.items(): archive.writestr(n,raw)
                    archive.writestr('manifest.json',json.dumps(manifest,sort_keys=True))
                return dict(filename='sv08-printer-identity.zip', content=base64.b64encode(buffer.getvalue()).decode())
            assets = self.decode_bundle(request['bundle']) if method.startswith('bundle.') else {n:(current / n).read_bytes() for n in AUTHORITY}
            if method == 'keys.replace': assets['users/sv08/authorized_keys'] = public_keys(request['keys'])
            if method != 'bundle.preview' and request['revision'] != current.name: raise ValueError('Printer identity changed; reload before retrying')
            path = self.new_generation(assets)
            try:
                self.validate(path)
                names_path = self.safe(current / 'names.json')
                names = json.loads(names_path.read_text()) if names_path.is_file() else normal_names(installed_names(self.data))
                self.sign(path, names)
                status = self.status_unlocked(path)
                if method == 'bundle.preview':
                    return dict(ca_fingerprint=status['ca_fingerprint'],ssh_fingerprint=status['ssh_fingerprint'],authorized_keys=status['authorized_keys'])
                self.select(path)
                return dict(status, services_restart_required=method=='bundle.restore')
            finally:
                if self.current() != path: shutil.rmtree(path)


def publish_cockpit(identity):
    directory = identity.safe(identity.data / 'system/cockpit/ws-certs.d')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True); directory.chmod(0o700)
    target = identity.safe(directory / 'zz-printer.cert')
    raw = (identity.current() / 'cockpit/50-printer.cert').read_bytes()
    if target.is_file() and target.read_bytes() == raw: return False
    temporary = directory / ('.printer-' + uuid.uuid4().hex)
    identity.put(temporary, raw)
    os.replace(temporary, target); fsync(directory); return True


def installed_names(data):
    hostname = (Path(data) / 'system/hostname').read_text().strip()
    running_name = socket.gethostname()
    names = [hostname,hostname+'.local',running_name,running_name+'.local']
    for interface in json.loads(run('ip','-j','address','show')):
        for address in interface.get('addr_info',[]):
            if address.get('scope') == 'global': names.append(address['local'])
    return names


def main():
    if os.geteuid() != 0: raise ValueError('Administrator access is required for printer identity')
    identity = Identity()
    if sys.argv[1:] == ['--ensure']:
        before = identity.current()
        result = identity.ensure(installed_names(identity.data))
        published = publish_cockpit(identity)
        if before != identity.current() or published: Path('/run/sv08/identity-reload').touch()
        print(json.dumps({k:result[k] for k in ('revision','ca_fingerprint','ssh_fingerprint')})); return
    if sys.argv[1:] == ['--reload-services']:
        marker = Path('/run/sv08/identity-reload')
        if marker.exists():
            for unit in ('ssh.service','nginx.service','sv08-mainsail.service','cockpit.service'):
                state = run('systemctl','show',unit,'-p','ActiveState','--value').decode().strip()
                if state == 'active':
                    if unit == 'sv08-mainsail.service': run('systemctl','kill','--kill-whom=main','--signal=HUP',unit)
                    else: run('systemctl','--no-block','try-reload-or-restart',unit)
            marker.unlink()
        return
    if sys.argv[1:]: raise ValueError('Unknown identity command')
    raw = sys.stdin.buffer.read(2*LIMIT+1)
    if len(raw) > 2*LIMIT: raise ValueError('Identity request is too large')
    result = identity.request(json.loads(raw))
    print(json.dumps(dict(ok=True,result=result)), flush=True)
    if result.get('services_restart_required'):
        Path('/run/sv08/identity-reload').touch()
        subprocess.Popen(['systemctl','--no-block','start','sv08-identity.service'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    try: main()
    except Exception as error:
        # Only our finite validation messages are public; tool/OS errors may
        # contain paths or private input, and are deliberately kept generic.
        message = str(error) if isinstance(error,ValueError) else 'Identity operation failed. Reload and check the identity; no automatic retry was attempted.'
        print(json.dumps(dict(ok=False,error=message)))
        if sys.argv[1:]: sys.exit(1)
