#!/usr/bin/env python3
"""Finite root network RPC. New profiles preserve existing credentials/profiles.

NM checkpoints protect live connectivity; a durable journal and boot preflight
remove unconfirmed candidates after restart. Tool errors never cross the RPC.
"""
from contextlib import contextmanager
import configparser
import io
import fcntl
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import uuid
from sv08_identity import Identity, installed_names, publish_cockpit
from sv08_admission import Admission, KLIPPER, MOONRAKER
from sv08_restart import require_running, publish, clear, require_restart
from sv08_state import Store
from sv08_data_budget import Budget
from sv08_state import fsync_dir

def unique_fields(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate network request field')
        result[key]=value
    return result


TIMEOUT = 180
NM = 'org.freedesktop.NetworkManager'
NM_PATH = '/org/freedesktop/NetworkManager'


class HeldBudget:
    """Identity joins the allocation lock already held by the network transaction."""
    def __init__(self, budget): self.budget = budget
    @contextmanager
    def locked(self): yield self
    def check(self, *args, **kwargs): return self.budget.check(*args, **kwargs)


class NetworkCertificates:
    def __init__(self, network, identity=None, discover=installed_names, publish=publish_cockpit):
        self.network = network
        self.identity = identity or Identity(network.data, budget=HeldBudget(network.budget))
        self.discover, self.publish = discover, publish
        self.changed = False

    def ensure(self, extra):
        current = self.identity.current()
        if current is None: raise ValueError('Prepare the printer identity before changing network settings')
        previous = [value.split(':', 1)[1] for value in json.loads((current/'names.json').read_text())]
        self.identity.ensure(sorted(set(previous + extra)))
        self.changed |= current != self.identity.current()

    def prepare(self, pending, request):
        extra = [request['hostname'], request['hostname']+'.local']
        if request['fqdn']: extra.append(request['fqdn'])
        extra += [str(ipaddress.IPv4Interface(value).ip) for value in request.get('ipv4', {}).get('addresses', [])]
        self.ensure(extra)

    def activate(self, pending, request):
        # Include the newly leased DHCP addresses; old names remain valid during
        # the confirmation/rollback window. Periodic reconciliation is unchanged.
        self.ensure(self.discover(self.network.data))
        published = self.publish(self.identity)
        if not (self.changed or published): return
        for unit in ('sv08-mainsail.service', 'cockpit.service'):
            state = self.network.command('systemctl', 'show', unit, '-p', 'ActiveState', '--value')
            if state == 'active':
                if unit == 'sv08-mainsail.service':
                    self.network.command('systemctl', 'kill', '--kill-whom=main', '--signal=HUP', unit)
                else:
                    # Last operation: disconnecting the browser can terminate its
                    # helper, but the durable journal and NM checkpoint survive.
                    self.network.command('systemctl', '--no-block', 'try-reload-or-restart', unit)
        self.changed = False


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=40,
                            env=dict(os.environ, LC_ALL='C'))
    if result.returncode: raise ValueError('Network service operation failed; inspect status before retrying')
    return result.stdout.strip()


def rows(text):
    """nmcli terse output escapes colons and backslashes, including SSIDs."""
    result = []
    for line in text.splitlines():
        fields, value, escaped = [], '', False
        for char in line:
            if escaped: value += char; escaped = False
            elif char == '\\': escaped = True
            elif char == ':': fields.append(value); value = ''
            else: value += char
        if escaped: value += '\\'
        result.append(fields + [value])
    return result


def key_string(value):
    return value.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t').replace(' ', '\\s')


def names(hostname, fqdn):
    label = r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
    if not isinstance(hostname, str) or not re.fullmatch(label, hostname):
        raise ValueError('Use a lower-case hostname of at most 63 characters')
    if not isinstance(fqdn, str) or len(fqdn) > 253 or (fqdn and ('.' not in fqdn or any(not re.fullmatch(label, x) for x in fqdn.split('.')) or fqdn.split('.')[0] != hostname)):
        raise ValueError('Use a qualified name beginning with the hostname, or leave it empty')
    return hostname, fqdn


def hosts_named(text, hostname, fqdn):
    aliases, remaining, comments = [], [], []
    for line in text.splitlines():
        fields = line.split('#', 1)[0].split()
        if fields and fields[0] == '127.0.1.1':
            aliases += fields[1:]
            if '#' in line: comments.append(line.split('#', 1)[1])
        else:
            if fields and any(n in fields[1:] for n in (hostname, fqdn) if n):
                raise ValueError('Name has a custom hosts mapping; choose another name')
            remaining.append(line)
    ordered = list(dict.fromkeys([*([fqdn] if fqdn else []), hostname, *aliases]))
    remaining.append('127.0.1.1\t' + ' '.join(ordered) + (' #' + ' '.join(comments) if comments else ''))
    return '\n'.join(remaining) + '\n'


def profile(request, identifier):
    required = {'method','device','kind','ssid','password','ipv4','hostname','fqdn','connection_uuid','security'}
    if set(request) != required: raise ValueError('Unexpected network request fields')
    device = request['device']
    if not isinstance(device,str) or not re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,14}',device): raise ValueError('Invalid network device')
    if request['kind'] not in ('wifi','ethernet'): raise ValueError('Choose Wi-Fi or Ethernet')
    names(request['hostname'], request['fqdn'])
    if not isinstance(request['connection_uuid'],str): raise ValueError('Invalid selected connection UUID')
    ip = request['ipv4']
    if not isinstance(ip,dict) or set(ip) != {'method','addresses','gateway','dns'} or ip['method'] not in ('auto','manual'):
        raise ValueError('Invalid IPv4 configuration')
    if not isinstance(ip['addresses'],list) or not isinstance(ip['dns'],list) or len(ip['addresses'])>8 or len(ip['dns'])>8:
        raise ValueError('At most eight addresses and DNS servers are supported')
    try:
        addresses = [str(ipaddress.IPv4Interface(x)) for x in ip['addresses']]
        dns = [str(ipaddress.IPv4Address(x)) for x in ip['dns']]
        gateway = str(ipaddress.IPv4Address(ip['gateway'])) if ip['gateway'] else ''
    except (ValueError,TypeError): raise ValueError('Use valid IPv4 addresses, prefixes, gateway and DNS servers') from None
    if ip['method']=='manual' and not addresses: raise ValueError('Static configuration needs an address and prefix')
    if ip['method']=='auto' and (addresses or gateway): raise ValueError('DHCP must not include static addresses or a gateway')
    lines = ['[connection]', 'id=SV08 '+identifier, 'uuid='+identifier,
             'type='+('wifi' if request['kind']=='wifi' else 'ethernet'),
             'interface-name='+device, 'autoconnect=true', 'autoconnect-priority=100', '', '[ipv4]', 'method='+ip['method']]
    for index,address in enumerate(addresses,1): lines.append('address'+str(index)+'='+address)
    if gateway: lines.append('gateway='+gateway)
    if dns: lines += ['dns='+';'.join(dns)+';', 'ignore-auto-dns=true']
    lines += ['', '[ipv6]', 'method=auto']
    ssid, password = request['ssid'], request['password']
    if not isinstance(ssid,str) or not isinstance(password,str): raise ValueError('Invalid Wi-Fi credentials')
    if request['security'] not in ('open','wpa-psk','sae'): raise ValueError('Choose open, WPA personal or WPA3 personal security')
    if request['kind']=='wifi':
        if not 1<=len(ssid.encode())<=32 or '\x00' in ssid: raise ValueError('SSID must contain between one and 32 UTF-8 bytes')
        if request['security']!='open' and not (request['connection_uuid'] and not password) and not (8<=len(password)<=63 or (request['security']=='wpa-psk' and re.fullmatch(r'[0-9a-fA-F]{64}',password))) or any(ord(x)<32 or ord(x)>126 for x in password):
            raise ValueError('WPA personal password must be 8–63 printable ASCII characters or 64 hexadecimal digits')
        lines += ['', '[wifi]', 'mode=infrastructure', 'ssid='+key_string(ssid)]
        if request['security']!='open': lines += ['', '[wifi-security]', 'key-mgmt='+request['security'], 'psk='+key_string(password), 'psk-flags=0']
        elif password: raise ValueError('Open Wi-Fi does not accept a password')
    elif ssid or password or request['security']!='open': raise ValueError('Ethernet does not accept Wi-Fi credentials')
    return '\n'.join(lines)+'\n'


class Network:
    def __init__(self, data='/data/sv08', command=run, budget=None, admission=None,
                 runtime='/run/sv08', etc='/etc', boot_id='/proc/sys/kernel/random/boot_id', now=time.time, monotonic=time.monotonic, pre_apply=None, post_apply=None, set_hostname=socket.sethostname):
        self.data=Path(data); self.system=self.data/'system'; self.root=self.system/'network-admin'
        self.command=command; self.budget=budget or Budget(self.data)
        self.runtime=Path(runtime); self.etc=Path(etc); self.boot_id=Path(boot_id)
        self.admission=admission; self.now=now; self.monotonic=monotonic
        self.pre_apply=pre_apply; self.post_apply=post_apply; self.set_hostname=set_hostname

    def safe(self,path, live_bind=False):
        for p in (path,*path.parents):
            if p.is_symlink(): raise ValueError('Invalid network storage path')
        allowed_links = (0, 1) if live_bind and path in (self.etc/'hostname', self.etc/'hosts') else (1,)
        if path.exists() and (not (path.is_file() or path.is_dir()) or (path.is_file() and path.stat().st_nlink not in allowed_links)):
            raise ValueError('Invalid network storage file')
        return path

    @contextmanager
    def locked(self):
        self.safe(self.root); self.root.mkdir(parents=True,mode=0o700,exist_ok=True); self.root.chmod(0o700)
        fd=os.open(self.safe(self.root/'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise ValueError('Network administration is busy') from None
            with self.budget.locked(): yield
        finally: os.close(fd)

    def write(self,path,raw,mode=0o600):
        self.safe(path); temporary=path.with_name('.'+path.name+'-'+uuid.uuid4().hex)
        try:
            with temporary.open('xb') as stream:
                os.fchmod(stream.fileno(),mode); stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary,path); fsync_dir(path.parent)
        finally: temporary.unlink(missing_ok=True)

    def pending(self):
        path=self.safe(self.root/'pending.json')
        if not path.exists(): return None
        if path.stat().st_size>65536: raise ValueError('Invalid network rollback journal')
        p=json.loads(path.read_text(),object_pairs_hook=unique_fields)
        fields={'token','uuid','device','checkpoint','boot_id','expires','deadline','old_uuid','old_hostname','old_hosts'}
        if not isinstance(p,dict) or set(p)!=fields: raise ValueError('Invalid network rollback journal')
        if (not isinstance(p['token'],str) or not re.fullmatch(r'[a-f0-9]{32}',p['token'])
                or not isinstance(p['checkpoint'],str) or not re.fullmatch(NM_PATH+r'/Checkpoint/[0-9]+',p['checkpoint'])
                or not isinstance(p['boot_id'],str) or not 1<=len(p['boot_id'])<=64
                or not isinstance(p['device'],str) or (p['device'] and not re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,14}',p['device']))
                or not isinstance(p['old_hosts'],str) or len(p['old_hosts'].encode())>32768):
            raise ValueError('Invalid network rollback journal')
        for key in ('uuid','old_uuid'):
            if not isinstance(p[key],str): raise ValueError('Invalid network rollback journal')
            if p[key]:
                try: valid=str(uuid.UUID(p[key]))==p[key]
                except ValueError: valid=False
                if not valid: raise ValueError('Invalid network rollback journal')
        if bool(p['uuid']) != bool(p['device']): raise ValueError('Invalid network rollback journal')
        names(p['old_hostname'],'')
        for key in ('expires','deadline'):
            if type(p[key]) not in (int,float) or not math.isfinite(p[key]): raise ValueError('Invalid network rollback journal')
        return p

    def journal(self,p): self.write(self.root/'pending.json',(json.dumps(p)+'\n').encode())
    def clear(self): (self.root/'pending.json').unlink(); fsync_dir(self.root)
    def nm(self,*args): return self.command('nmcli','--wait','30','--terse','--escape','yes',*args)
    def call(self,method,signature,*args): return self.command('busctl','call',NM,NM_PATH,NM,method,signature,*args)

    def status(self):
        devices=[]
        for device,kind,state,connection in rows(self.nm('-f','DEVICE,TYPE,STATE,CONNECTION','device','status')):
            details=rows(self.nm('-f','GENERAL.CON-UUID,IP4.ADDRESS,IP4.GATEWAY,IP4.DNS','device','show',device))
            values={}
            for key,value in details: values.setdefault(key.split('[')[0],[]).append(value)
            devices.append(dict(device=device,type=kind,state=state,connection=connection,
                                uuid=values.get('GENERAL.CON-UUID',[''])[0],addresses=values.get('IP4.ADDRESS',[]),gateway=values.get('IP4.GATEWAY',[''])[0],dns=values.get('IP4.DNS',[])))
        connections=[dict(zip(('uuid','name','type','device'),row)) for row in rows(self.nm('-f','UUID,NAME,TYPE,DEVICE','connection','show'))]
        for c in connections:
            c['type'] = {'802-3-ethernet':'ethernet', '802-11-wireless':'wifi'}.get(c['type'], c['type'])
            if c['device'] == '--': c['device'] = ''
            if c['type'] not in ('802-3-ethernet','802-11-wireless','ethernet','wifi'): continue
            fields=rows(self.nm('-f','ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.dns','connection','show','uuid',c['uuid']))
            c['ipv4']={k.split('.')[-1]:v for k,v in fields}
            for key in ('addresses','dns'):
                c['ipv4'][key] = [value.strip() for value in c['ipv4'].get(key, '').split(',') if value.strip() and value.strip() != '--']
            if c['ipv4'].get('gateway') == '--': c['ipv4']['gateway'] = ''
            if c['type'] in ('802-11-wireless','wifi'):
                public=rows(self.nm('-f','802-11-wireless.ssid,802-11-wireless-security.key-mgmt','connection','show','uuid',c['uuid']))
                values=dict(public)
                c['ssid']=values.get('802-11-wireless.ssid','')
                key_mgmt=values.get('802-11-wireless-security.key-mgmt','')
                c['security']=key_mgmt if key_mgmt in ('wpa-psk','sae') else 'open' if key_mgmt in ('','--') else 'unsupported'
        hostname=self.safe(self.system/'hostname').read_text().strip()
        hosts=self.safe(self.system/'hosts').read_text(); fqdn=''
        for line in hosts.splitlines():
            fields=line.split('#',1)[0].split()
            if fields and fields[0]=='127.0.1.1' and len(fields)>1 and fields[1].startswith(hostname+'.'): fqdn=fields[1]
        p=self.pending()
        return dict(devices=devices,connections=connections,hostname=hostname,fqdn=fqdn,
                    pending=dict(token=p['token'],expires=p['expires']) if p else None)

    def expired(self,p):
        return p['boot_id']!=self.boot_id.read_text().strip() or self.now()>=p['expires'] or self.monotonic()>=p['deadline']

    def hostname(self,hostname,hosts,runtime=True):
        self.write(self.system/'hosts',hosts.encode(),0o644)
        self.write(self.system/'hostname',(hostname+'\n').encode(),0o644)
        # /etc files are bind mounts of the prior inodes: update those too. The
        # journal precedes writes, so interruption is recoverable by preflight.
        for name,raw in [('hosts',hosts),('hostname',hostname+'\n')]:
            # Replacing the persistent backing file leaves its old inode alive
            # solely through this bind mount (link count zero).
            path=self.safe(self.etc/name,live_bind=True)
            if path.exists() and path.stat().st_ino != (self.system/name).stat().st_ino:
                with path.open('w') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        if runtime: self.set_hostname(hostname.encode())

    def rollback(self,p,offline=False):
        candidate=self.safe(self.system/'network-connections'/('sv08-'+p['uuid']+'.nmconnection')) if p['uuid'] else None
        if candidate:
            candidate.unlink(missing_ok=True); fsync_dir(candidate.parent)
        # PID 1 may already have adopted the unconfirmed name from the early
        # hostname bind. Reset the kernel name even before NetworkManager starts.
        self.hostname(p['old_hostname'],p['old_hosts'])
        if not offline:
            if p['device']:
                existing=self.nm('-g','UUID','connection','show').splitlines()
                if p['uuid'] in existing: self.nm('connection','delete','uuid',p['uuid'])
                self.nm('connection','reload')
            # Reload removes the candidate even when NM already auto-rolled back.
            # Explicit reactivation also handles a restarted NM with no checkpoint.
            if p['device']:
                if p['old_uuid']: self.nm('connection','up','uuid',p['old_uuid'],'ifname',p['device'])
                else: self.nm('device','disconnect',p['device'])
        if not offline:
            try: self.call('CheckpointDestroy','o',p['checkpoint'])
            except ValueError: pass  # NM may already have timed out or restarted.
        self.clear()
        return dict(rolled_back=True)

    def recover(self,boot=False):
        with self.locked():
            p=self.pending()
            if p and (p['boot_id']!=self.boot_id.read_text().strip() if boot else self.expired(p)):
                return self.rollback(p,offline=boot)
            return dict(rolled_back=False)

    def copy_profile(self,r,identifier,raw):
        selected=r['connection_uuid']
        if not re.fullmatch(r'[0-9a-fA-F-]{36}',selected): raise ValueError('Invalid selected connection UUID')
        candidates = [filename for identifier, filename in rows(self.nm('-f','UUID,FILENAME','connection','show')) if identifier == selected]
        if len(candidates) != 1: raise ValueError('Selected connection is not a persistent NetworkManager profile')
        filename = candidates[0]
        # The bound /etc directory maps to persistent storage; only NM-managed
        # root-private regular files there are eligible for credential reuse.
        source=Path(filename)
        if source.parent != Path('/etc/NetworkManager/system-connections'):
            raise ValueError('Selected connection is not a persistent NetworkManager profile')
        source=self.safe(self.system/'network-connections'/source.name)
        st=source.stat()
        if st.st_uid!=os.geteuid() or st.st_mode & 0o077 or st.st_size>65536:
            raise ValueError('Selected network profile must be private and bounded')
        config=configparser.ConfigParser(interpolation=None,strict=True); config.optionxform=str
        try: config.read_string(source.read_text())
        except (configparser.Error,UnicodeError): raise ValueError('Selected network profile cannot be safely copied') from None
        expected='wifi' if r['kind']=='wifi' else 'ethernet'
        if config.get('connection','uuid',fallback='') != selected or config.get('connection','type',fallback='') not in (expected,'802-11-wireless' if expected=='wifi' else '802-3-ethernet'):
            raise ValueError('Selected profile does not match requested connection type')
        interface=config.get('connection','interface-name',fallback='')
        if interface and interface!=r['device']: raise ValueError('Selected profile belongs to another device')
        update=configparser.ConfigParser(interpolation=None); update.optionxform=str; update.read_string(raw)
        for section in ('connection','ipv4'):
            if section=='ipv4' and config.has_section(section): config.remove_section(section)
            if not config.has_section(section): config.add_section(section)
            for key,value in update[section].items(): config[section][key]=value
        if expected=='wifi':
            # NM decodes GLib escapes and byte-array SSIDs. Compare its public
            # metadata rather than requiring this writer's keyfile spelling.
            public_ssid = rows(self.nm('-f','802-11-wireless.ssid','connection','show','uuid',selected))
            if len(public_ssid) != 1 or public_ssid[0] != ['802-11-wireless.ssid', r['ssid']]:
                raise ValueError('Choose the existing SSID when reusing a connection')
            if r['security']=='open':
                config.remove_section('wifi-security')
            elif not r['password']:
                if config.get('wifi-security','key-mgmt',fallback='') not in ('wpa-psk','sae') or not config.get('wifi-security','psk',fallback=''):
                    raise ValueError('Selected Wi-Fi profile has no reusable WPA personal password')
                retained = config.get('wifi-security','psk')
                if r['security'] == 'sae' and re.fullmatch(r'[0-9a-fA-F]{64}', retained):
                    raise ValueError('Enter a WPA3 personal password for this security change')
                config['wifi-security']['key-mgmt'] = r['security']
            else:
                if not config.has_section('wifi-security'): config.add_section('wifi-security')
                for key,value in update['wifi-security'].items(): config['wifi-security'][key]=value
        output=io.StringIO(); config.write(output,space_around_delimiters=False)
        return output.getvalue()

    def apply(self,r):
        if self.pending(): raise ValueError('Confirm or roll back the pending network change first')
        name_only=r.get('kind')=='name'
        identifier='' if name_only else str(uuid.uuid4())
        if name_only:
            if set(r)!={'method','kind','hostname','fqdn'}: raise ValueError('Unexpected naming request fields')
            names(r['hostname'],r['fqdn']); raw=None
        else:
            raw=profile(r,identifier)
        status=self.status()
        device=None if name_only else next((d for d in status['devices'] if d['device']==r['device']),None)
        if not name_only and (not device or device['type']!=r['kind']): raise ValueError('Device does not match the requested network type')
        directory=self.safe(self.system/'network-connections')
        if not directory.is_dir(): raise ValueError('Persistent network directory is missing')
        if not name_only and len(list(directory.iterdir()))>=64: raise ValueError('Network profile storage is full; inspect existing profiles')
        if not name_only and r['connection_uuid']: raw=self.copy_profile(r,identifier,raw)
        hosts_path=self.safe(self.system/'hosts')
        if hosts_path.stat().st_size>32768: raise ValueError('Hosts configuration is too large for bounded rollback')
        old_hosts=hosts_path.read_text()
        names(status['hostname'],'')
        hosts=hosts_named(old_hosts,r['hostname'],r['fqdn'])
        self.budget.check(131072,inodes=8)
        checkpoint_args=['0',str(TIMEOUT),'0'] if name_only else ['1',self.call('GetDeviceByIpIface','s',r['device']).split('"')[1],str(TIMEOUT),'0']
        checkpoint=self.call('CheckpointCreate','aouu',*checkpoint_args).split('"')[1]
        p=dict(token=uuid.uuid4().hex,uuid=identifier,device='' if name_only else r['device'],checkpoint=checkpoint,
               boot_id=self.boot_id.read_text().strip(),expires=self.now()+TIMEOUT,deadline=self.monotonic()+TIMEOUT,
               old_uuid=device['uuid'] if device and re.fullmatch(r'[0-9a-fA-F-]{36}',device['uuid']) else '',
               old_hostname=status['hostname'],old_hosts=old_hosts)
        self.journal(p)
        try:
            if self.pre_apply: self.pre_apply(p,r)
            if not name_only:
                self.write(directory/('sv08-'+identifier+'.nmconnection'),raw.encode())
                self.nm('connection','reload')
            self.hostname(r['hostname'],hosts)
            if not name_only: self.nm('connection','up','uuid',identifier,'ifname',r['device'])
            if self.post_apply: self.post_apply(p,r)
        except Exception:
            self.rollback(p)
            raise
        return dict(token=p['token'],expires=p['expires'],confirm_required=True)

    def restart(self):
        if self.pending(): raise ValueError('Confirm or roll back network changes before restarting')
        network=self
        class RestartSystemd:
            rebooting=False
            def state(self,name):
                state=network.command('systemctl','show',name,'-p','ActiveState','--value')
                if name==KLIPPER:
                    legacy=network.command('systemctl','show','klipper.service','-p','ActiveState','--value')
                    if legacy not in ('inactive','failed'): raise ValueError('Legacy Klipper prevents controlled restart')
                    if state!='active':
                        modes=[network.command('systemctl','show',unit,'-p','UnitFileState','--value') for unit in (KLIPPER,'klipper.service')]
                        if state!='inactive' or legacy!='inactive' or modes!=['masked','masked']:
                            raise ValueError('Printer idle cannot be proven; restart refused')
                return state
            def stop(self,name):
                network.command('systemctl','stop',name)
                if network.command('systemctl','show',name,'-p','ActiveState','--value') not in ('inactive','failed'):
                    raise ValueError('Printer service did not stop')
            def start(self,name):
                if not self.rebooting: network.command('systemctl','start',name)
        systemd=RestartSystemd()
        admission=self.admission or Admission(self.runtime,systemd=systemd,boot_id=self.boot_id)
        with admission() as lease:
            if network.command('systemctl','show','klipper.service','-p','ActiveState','--value') not in ('inactive','failed'):
                raise ValueError('Legacy Klipper prevents controlled restart')
            expected=publish(self.runtime,self.boot_id)
            # Once the request can reach systemd, a lost acknowledgement cannot
            # prove that shutdown was refused. Keep the barrier through that
            # uncertainty, including interrupted callers.
            systemd.rebooting=True
            if lease is not None: lease.keep_stopped=True
            try:
                network.command('systemctl','--no-block','reboot')
            except (FileNotFoundError, PermissionError):
                # The subprocess could not launch. Clear only our exact intent
                # before allowing the admitted services to be restored.
                clear(self.runtime,expected,self.boot_id)
                systemd.rebooting=False
                if lease is not None: lease.keep_stopped=False
                raise
            except Exception:
                raise ValueError('Restart acknowledgment is uncertain; admission remains closed until the next boot') from None
        return dict(restarting=True)

    def request(self,r):
        if not isinstance(r,dict): raise ValueError('Invalid network request')
        method=r.get('method')
        if method=='restart':
            # State precedes network/budget, matching image and software writers.
            store=Store(self.data,budget=self.budget,runtime=self.runtime,boot_id=self.boot_id)
            with store.locked(nonblocking=True), self.locked():
                require_running(self.runtime,self.boot_id)
                require_restart(store)
                if r!=dict(method='restart',confirm=True): raise ValueError('Confirm controlled restart explicitly')
                return self.restart()
        with self.locked():
            p=self.pending()
            if method!='status': require_running(self.runtime,self.boot_id)
            if method=='status' and set(r)=={'method'}: return self.status()
            if p and self.expired(p): self.rollback(p); p=None
            if method=='wifi.scan' and set(r)=={'method','device'}:
                if not isinstance(r['device'],str) or not re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,14}',r['device']): raise ValueError('Invalid network device')
                return dict(networks=[dict(zip(('ssid','signal','security','in_use'),row)) for row in rows(self.nm('-f','SSID,SIGNAL,SECURITY,IN-USE','device','wifi','list','ifname',r['device'],'--rescan','yes'))])
            if method=='apply': return self.apply(r)
            if method in ('confirm','rollback') and set(r)=={'method','token'}:
                if not p or r['token']!=p['token']: raise ValueError('Network change expired or changed; reload status')
                if method=='rollback': return self.rollback(p)
                # Destroy succeeds only while the live checkpoint still exists.
                # If NM auto-rolled back or restarted, never claim confirmation.
                self.call('CheckpointDestroy','o',p['checkpoint']); self.clear()
                return dict(confirmed=True)
            if method=='restart' and r==dict(method='restart',confirm=True): return self.restart()
            raise ValueError('Unknown network operation or unexpected request fields')


def main():
    if os.geteuid()!=0: raise ValueError('Administrator access is required for network administration')
    network=Network()
    if sys.argv[1:]==['--recover-boot']: network.recover(boot=True); return
    if sys.argv[1:]==['--recover']: network.recover(); return
    if sys.argv[1:]: raise ValueError('Unknown network command')
    certificates=NetworkCertificates(network)
    network.pre_apply, network.post_apply = certificates.prepare, certificates.activate
    raw=sys.stdin.buffer.read(16385)
    if len(raw)>16384: raise ValueError('Network request is too large')
    print(json.dumps(dict(ok=True,result=network.request(json.loads(raw,object_pairs_hook=unique_fields)))),flush=True)


if __name__=='__main__':
    try: main()
    except Exception as error:
        message=str(error) if isinstance(error,ValueError) else 'Network operation failed; reload status and inspect pending rollback'
        print(json.dumps(dict(ok=False,error=message)),flush=True)
        if sys.argv[1:]: sys.exit(1)
