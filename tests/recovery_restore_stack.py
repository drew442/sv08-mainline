#!/usr/bin/env python3
"""Disposable installed-stack recovery qualification; no physical output authority.

The coordinator stages this driver and executes it in its private ARM64 chroot
or guest. Provision uses actual pinned Moonraker/Identity/PrinterStore and the
Klipper debug validator. Normal assertions observe PID 1 production units;
recovery operations use the installed reviewed-media controller.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import stat
import subprocess
import time

MARKER = 'sv08-disposable-recovery-stack-v1\n'
MAC = '52:54:00:08:10:13'
PROFILE_UUIDS = {'previous':'daa90916-6d0d-493e-84bc-968c502f7351',
                 'restored':'daa90916-6d0d-493e-84bc-968c502f7352'}
REQUIRED_UNITS = ('sv08-prepare.service','sv08-web-prepare.service',
                  'sv08-printer-api.service','sv08-web-auth.service','sv08-mainsail.service',
                  'NetworkManager.service','cockpit.socket','ssh.service')


def require(condition, message):
    if not condition: raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    with Path(path).open('x') as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(value, stream, sort_keys=True, indent=2); stream.write('\n')


def private_fixture(path):
    path = Path(path).absolute()
    require(all(not p.is_symlink() for p in (path, *path.parents)), 'Fixture path cannot contain links')
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and
            not info.st_mode & 0o077, 'Private owned fixture required')
    require((path/'disposable-marker').read_text() == MARKER, 'Disposable fixture marker required')
    return path


def network_profile(name):
    require(name in PROFILE_UUIDS, 'Unknown fixture state')
    return ('[connection]\nid=sv08-stack-'+name+'\nuuid='+PROFILE_UUIDS[name]+
            '\ntype=ethernet\nautoconnect=true\n\n[ethernet]\nmac-address='+MAC+
            '\n\n[ipv4]\nmethod=auto\n\n[ipv6]\nmethod=disabled\n').encode()


def factory(catalog_path, name):
    from sv08_printer_catalog import Catalog, empty_draft, digest
    from sv08_printer_definitions import builtins
    from sv08_printer_compose import select_definition
    catalog = Catalog(catalog_path); records = builtins(catalog)
    selected = next(d for d in records if d['id'] == 'sv08.factory')
    draft = empty_draft()
    # Explicit absent serial endpoints, synthetic instance identity only.
    draft['boards'] = {role:dict(id='sv08-'+role, transport='serial',
        identity='/dev/serial/by-id/sv08-stack-'+name+'-'+role, reference_ack=True)
        for role in ('main','tool')}
    snapshots = {'builtin::'+r['id']+'@'+r['version']:r for r in records}
    draft=select_definition(catalog, draft, dict(source='builtin',id=selected['id'],
        version=selected['version'],sha256=digest(selected),commit=catalog.revision), snapshots)
    # PrinterStore and the expectations file persist sorted JSON. Use that
    # exact input ordering before generation, never refresh failed-byte hashes.
    return catalog, json.loads(json.dumps(draft,sort_keys=True))


def active_generation(root):
    from sv08_state import Store
    store = Store(root); return store.generation_path(store.load()['slots']['A'])


def native_auth(work, root, config, name):
    """Start the installed pinned upstream API only for synthetic DB provisioning."""
    from sv08_web import Web, API, credentials
    view = work/('native-'+name); view.mkdir(mode=0o755)
    for leaf, target in (('config',config),('database',config.parent/'database'),
                         ('gcodes',root/'shared/gcodes'),('logs',root/'shared/logs/printer')):
        (view/leaf).symlink_to(target)
    (view/'comms').mkdir(); os.chown(view,1000,1000); os.chown(view/'comms',1000,1000)
    log = work/('native-'+name+'.log')
    def owner(): os.setgid(1000); os.setuid(1000)
    command = ['/opt/sv08-mainline/venvs/moonraker-985c1d0/bin/python',
               '/opt/sv08-mainline/moonraker/moonraker/moonraker.py', '-d',str(view),'-l',str(log)]
    # Logs live in the generated owner-readable fixture, never inherited state.
    log.touch(mode=0o600); os.chown(log,1000,1000)
    with log.open('ab') as output:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
            preexec_fn=owner, start_new_session=True, env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        try:
            deadline = time.monotonic()+180; api = API()
            while True:
                require(process.poll() is None, 'Installed Moonraker stopped during synthetic provisioning')
                try: api.ready(); break
                except ValueError:
                    require(time.monotonic() < deadline, 'Installed Moonraker provisioning deadline'); time.sleep(.5)
            web = Web(root, config); web.prepare(); web.authenticate()
            result = credentials((root/'moonraker-login.txt').read_text())
            require(api.request('/access/login', result).get('token'), 'Native generated owner login failed')
            return result
        finally:
            if process.poll() is None: os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); process.wait(timeout=5)


def provision(work, release, owner_public_key):
    from sv08_state import Store
    from sv08_boot import initialize_identity, initialize_owner_authorized_keys, prepare_permissions
    from sv08_identity import Identity
    from sv08_printer_generate import generate
    from sv08_printer_store import PrinterStore
    from sv08_printer_publish import validate_output
    work = private_fixture(work)
    require(os.geteuid() == 0, 'Root fixture provisioning required')
    boot = {k:release[k] for k in ('release','state_schema','release_revision')}; boot['slot']='A'
    require(release.get('deployable') is False, 'Fixture release must be nondeployable')
    expectations = {}; credentials = json.loads((work/'credentials.json').read_text())
    # Application UID traverses only this generated work directory; credentials
    # and all authority assets remain private with their native ownership.
    work.chmod(0o711)
    for name, container_name, token in (('previous','target-tree','a'*32),('restored','export-tree','b'*32)):
        container = work/container_name; container.mkdir(mode=0o711)
        root = container/'sv08'; store = Store(root); store.initialize()
        prepared = store.prepare_boot('A',boot['release'],boot['state_schema'],boot['release_revision'])
        prepared['boot_id'] = 'synthetic-provision-'+name
        initialize_identity(root); (root/'system/machine-id').write_text(token+'\n')
        initialize_owner_authorized_keys(root, owner_public_key)
        hostname = 'sv08-stack-'+name
        (root/'system/hostname').write_text(hostname+'\n')
        (root/'system/hosts').write_text('127.0.0.1 localhost\n127.0.1.1 '+hostname+'\n::1 localhost\n')
        profile = root/'system/network-connections/stack.nmconnection'
        profile.write_bytes(network_profile(name)); profile.chmod(0o600)
        config = Path(prepared['generation'])/'config'
        prepare_permissions(root, prepared['generation'])
        identity = Identity(root); identity.ensure([hostname,'10.0.2.15'])
        identity.ensure([hostname,'10.0.2.15'],renew=True)  # real current and previous selectors
        boot_path = work/('boot-'+name+'.json'); write_json(boot_path,prepared)
        view = work/('config-'+name); view.symlink_to(config)
        catalog, draft = factory('/usr/share/sv08/printer/catalog.json',name)
        service = PrinterStore(store,boot_path,view,catalog,publication_admit=lambda:True,
                               publication_validate=validate_output)
        loaded = service.request({'action':'status'})
        service.request(dict(action='save',draft=draft,expected_revision=loaded['state']['revision'],expected_identity=loaded['loaded_identity']))
        loaded = service.request({'action':'status'})
        review = service.request(dict(action='review',mode='full',expected_identity=loaded['loaded_identity']))
        require(review['complete'] and not review['printing_enabled'], 'Uncalibrated factory configuration must block printing')
        service.request(dict(action='apply',mode='full',review=review['review'],expected_identity=loaded['loaded_identity']))
        generated = generate(catalog,draft,'full')
        # Publish through the same validator/Publisher used by the real helper.
        loaded = service.request({'action':'status'})
        pub = service.request(dict(action='publication_review',expected_revision=loaded['state']['revision'],expected_identity=loaded['loaded_identity']))
        service.request(dict(action='publication_apply',review=pub['review'],expected_revision=loaded['state']['revision'],expected_identity=loaded['loaded_identity']))
        for filename in ('moonraker.conf','nginx-mainsail.conf','mainsail.json','configuration-manifest.json'):
            path=config/filename; path.write_text(generated['files'][filename]); path.chmod(0o640); os.chown(path,1000,1000)
        login = native_auth(work,root,config,name); credentials[name] = login
        current = identity.current()
        public_ca = work/(name+'-ca.crt'); public_ca.write_bytes((current/'ca/ca.crt').read_bytes()); public_ca.chmod(0o644)
        public_ssh=work/(name+'-ssh-host.pub'); public_ssh.write_bytes((current/'ssh/ssh_host_ed25519_key.pub').read_bytes()); public_ssh.chmod(0o644)
        # Normal systemd's exact opaque log object is present before export.
        (root/'shared/logs/README').symlink_to('../../usr/share/doc/systemd/README.logs')
        expected_config = {str(p.relative_to(config)):sha(p) for p in config.rglob('*') if p.is_file()}
        expectations[name] = dict(machine_id=token,hostname=hostname,profile_uuid=PROFILE_UUIDS[name],
            profile_sha256=sha(profile),config=expected_config,draft=draft,
            bundle_sha256={n:hashlib.sha256(v.encode()).hexdigest() for n,v in generated['files'].items()},
            ca_sha256=sha(current/'ca/ca.crt'),ssh_public_sha256=sha(current/'ssh/ssh_host_ed25519_key.pub'),
            authorized_keys_sha256=sha(current/'users/sv08/authorized_keys'),
            gateway_sha256=sha(root/'mainsail-auth/users'),native_login_sha256=sha(root/'moonraker-login.txt'))
        (container/'preserved-sibling').write_text('synthetic '+name+' sibling\n')
    (work/'credentials.json').write_text(json.dumps(credentials)); (work/'credentials.json').chmod(0o600)
    write_json(work/'stack-expectations.json',dict(format_version=1,deployable=False,boot=boot,states=expectations))
    work.chmod(0o700)
    return dict(provisioned=list(expectations),physical_hardware=False,printing_ready=False)


BOOTSTRAP_FILES = ('disposable-marker','credentials.json','release.json','owner-key.pub')
BOOTSTRAP_UNITS = ('sv08-mainsail.service','sv08-web-auth.service','sv08-printer-api.service',
    'sv08-moonraker.service','sv08-klipper.service','cockpit.socket','cockpit.service','ssh.service',
    'sv08-identity.timer','sv08-identity.service','sv08-network-rollback.timer',
    'sv08-network-rollback.service','NetworkManager.service')


def bootstrap_role(cmdline):
    values=[part for part in cmdline.split() if part.startswith('sv08.stack.bootstrap=')]
    return values == ['sv08.stack.bootstrap=1'] and not any(part.startswith('sv08.stack.expect=') for part in cmdline.split())


def bootstrap(source=Path('/usr/lib/sv08/stack-bootstrap'), work=Path('/data/stack-bootstrap')):
    """Preparation in real ARM64 PID 1, without a stack qualification claim."""
    require(os.geteuid()==0 and Path('/proc/1/comm').read_text().strip()=='systemd' and
            bootstrap_role(Path('/proc/cmdline').read_text()), 'Explicit full-system bootstrap role required')
    source=private_fixture(source)
    require(set(path.name for path in source.iterdir())==set(BOOTSTRAP_FILES), 'Only known generated bootstrap assets admitted')
    for name in BOOTSTRAP_FILES:
        info=(source/name).lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==0 and
                not info.st_mode & 0o077, 'Root-private regular bootstrap assets required')
    require(not work.exists() and not work.is_symlink(),'Existing bootstrap preparation preserved; use a fresh data fixture')
    work.mkdir(mode=0o700)
    for name in BOOTSTRAP_FILES: shutil.copy2(source/name,work/name)
    # PID 1 completes the actual service stops before the native fixture API
    # binds loopback7125. No output gate/health/commissioning marker is forged.
    for unit in BOOTSTRAP_UNITS:
        result=subprocess.run(['systemctl','stop',unit],capture_output=True,text=True,timeout=60)
        state=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True,timeout=5).strip()
        require(state in ('inactive','failed'), 'Bootstrap writer did not stop: '+unit)
    result=provision(work,json.loads((work/'release.json').read_text()),work/'owner-key.pub')
    write_json(work/'bootstrap-result.json',dict(result,role='preparation-only-full-system',qualified=False,
        source_runtime_sha256=sha(Path(__file__)),stopped_units=list(BOOTSTRAP_UNITS)))
    return dict(result,role='preparation-only-full-system',qualified=False,output=str(work))


def recover(phase):
    from sv08_recovery import installed_controller
    from sv08_recovery_restore_media import POLICY
    from sv08_recovery_activation import boot_guard
    from sv08_export import inventory
    policy = json.loads(POLICY.read_text()); spec=policy['targets']['target']
    target=Path(spec['mount']); archive=Path(policy['archives']['backup']['path'])
    before=sha(archive); sibling=sha(target/'preserved-sibling')
    controller=installed_controller()
    if phase=='restore':
        old=inventory(target/'sv08')
        plan=controller.plan('recovery.data-restore',dict(archive='backup',target='target'))
        require(not (target/'restored').exists(), 'Restore review wrote state')
        controller.apply(plan)
        require(inventory(target/'sv08') == old, 'Restore altered canonical state before activation')
        require((target/'restored/preserved-sibling').read_text()=='synthetic restored sibling\n', 'Archive sibling lost')
    elif phase=='activate':
        require((target/'restored/sv08/system/machine-id').read_text().strip()=='b'*32,'Unexpected restored identity')
        plan=controller.plan('recovery.activate',dict(target='target'))
        require((target/'sv08/system/machine-id').read_text().strip()=='a'*32,'Activation review wrote state')
        controller.apply(plan); boot_guard(target)
    elif phase=='rollback':
        controller.apply(controller.plan('recovery.rollback',dict(target='target'))); boot_guard(target)
        require((target/'sv08/system/machine-id').read_text().strip()=='a'*32,'Rollback did not restore identity')
    else: raise ValueError('Unknown recovery phase')
    require(sha(archive)==before and sha(target/'preserved-sibling')==sibling,'Archive or target sibling changed')
    return dict(phase=phase,result='PASS',archive_sha256=before,sibling_sha256=sibling)


def completed_identity(facts):
    """A successful oneshot may be inactive; an unstarted default is insufficient."""
    started=facts.get('ExecMainStartTimestampMonotonic','')
    return (facts.get('ActiveState') in ('active','inactive') and facts.get('Result')=='success' and
            facts.get('ExecMainStatus')=='0' and isinstance(started,str) and started.isdecimal() and int(started)>0)


def normal_assert(expected, expectations, receipt_dir, deadline=600):
    from sv08_identity import Identity
    from sv08_printer_generate import generate
    from sv08_printer_catalog import Catalog
    from sv08_printer_publish import validate_output
    if expected is None:
        values=[part.split('=',1)[1] for part in Path('/proc/cmdline').read_text().split() if part.startswith('sv08.stack.expect=')]
        require(len(values)==1,'Explicit normal fixture role required'); expected=values[0]
    require(expected in ('previous','restored') and 1 <= deadline <= 600, 'Invalid bounded normal assertion')
    require(not any(part.startswith('sv08.stack.bootstrap=') for part in Path('/proc/cmdline').read_text().split()),
            'Bootstrap preparation is not a qualification boot')
    require(Path('/proc/1/comm').read_text().strip()=='systemd','Real systemd boot required')
    exp=json.loads(Path(expectations).read_text())['states'][expected]
    started=time.monotonic()
    while True:
        states={unit:subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True,timeout=5).strip() for unit in REQUIRED_UNITS}
        identity_output=subprocess.check_output(['systemctl','show','sv08-identity.service','-p','ActiveState','-p','Result','-p','ExecMainStatus','-p','ExecMainStartTimestampMonotonic'],text=True,timeout=5)
        identity_facts=dict(line.split('=',1) for line in identity_output.splitlines() if '=' in line)
        if all(value=='active' for value in states.values()) and completed_identity(identity_facts): break
        require(time.monotonic()-started < deadline, 'Production units not ready: '+json.dumps(dict(units=states,identity=identity_facts))); time.sleep(1)
    boot=json.loads(Path('/run/sv08/boot.json').read_text()); root=Path('/data/sv08')
    require(boot['mode']=='immutable' and boot['slot']=='A' and not boot['trial'],'Unexpected operating mode')
    require(boot['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'Boot ID differs')
    require(Path('/etc/machine-id').read_text().strip()==exp['machine_id'],'Restored machine identity differs')
    mounts={}
    for path,fs,mode in (('/','ext4','ro'),('/usr','squashfs','ro'),('/data','ext4','rw'),('/boot','vfat','ro')):
        row=subprocess.check_output(['findmnt','-n','-o','FSTYPE,OPTIONS','--mountpoint',path],text=True,timeout=5).split()
        require(row[0]==fs and mode in row[1].split(','),'Incorrect normal mount '+path); mounts[path]=row
    config=active_generation(root)/'config'
    for relative, digest in exp['config'].items(): require(sha(config/relative)==digest,'Persistent configuration differs: '+relative)
    generated=generate(Catalog('/usr/share/sv08/printer/catalog.json'),exp['draft'],'full')
    require(generated['complete'] and not generated['printing_enabled'],'Factory commissioning protections changed')
    require({n:hashlib.sha256(v.encode()).hexdigest() for n,v in generated['files'].items()}==exp['bundle_sha256'],'Regenerated software bundle differs')
    parser=validate_output(dict(files={},review='recovery-stack',activation=(config/'printer.cfg').read_text()),config)
    require(parser['validated'] and parser['physical_hardware'] is False,'Pinned offline Klipper validation failed')
    current=Identity(root).current()
    for leaf,key in (('ca/ca.crt','ca_sha256'),('ssh/ssh_host_ed25519_key.pub','ssh_public_sha256'),('users/sv08/authorized_keys','authorized_keys_sha256')):
        require(sha(current/leaf)==exp[key],'Restored persistent identity differs: '+leaf)
    for leaf,key in (('mainsail-auth/users','gateway_sha256'),('moonraker-login.txt','native_login_sha256')):
        require(sha(root/leaf)==exp[key],'Restored persistent authentication differs')
    profile=Path('/etc/NetworkManager/system-connections/stack.nmconnection'); info=profile.stat()
    require(sha(profile)==exp['profile_sha256'] and (info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode))==(0,0,0o600),'Network profile bytes/ownership differ')
    active=subprocess.check_output(['nmcli','-t','-f','UUID','connection','show','--active'],text=True,timeout=30).splitlines()
    require(exp['profile_uuid'] in active,'Actual NetworkManager profile was not activated')
    klipper=subprocess.check_output(['systemctl','show','sv08-klipper.service','-p','ActiveState','-p','SubState','-p','ConditionResult','-p','ExecMainStatus'],text=True,timeout=5)
    health=subprocess.check_output(['systemctl','show','sv08-boot-health.service','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus'],text=True,timeout=5)
    health_marker=Path('/run/sv08/os-health-ready')
    # OS health may legitimately admit the real Klipper host process. Missing
    # synthetic serial MCUs remain an observed software boundary, not a reason
    # to fabricate an inactive unit or suppress the production health service.
    from sv08_web import API, credentials
    api=API(); native=credentials((root/'moonraker-login.txt').read_text())
    token=api.request('/access/login',native)['token']
    info=api.request('/server/info',token=token)
    require(info.get('klippy_state') in ('disconnected','startup','error','shutdown'),
            'Absent-MCU qualification cannot assert a ready physical printer')
    output=Path(receipt_dir); output.mkdir(mode=0o700,exist_ok=True)
    receipt=output/(expected+'-'+boot['boot_id']+'.json')
    write_json(receipt,dict(result='PASS',expected=expected,boot_id=boot['boot_id'],units=states,identity_unit=identity_facts,mounts=mounts,
        profile_uuid=exp['profile_uuid'],identity={k:exp[k] for k in ('ca_sha256','ssh_public_sha256','authorized_keys_sha256')},
        klipper_service=klipper,boot_health_service=health,os_health_marker_present=health_marker.exists(),
        os_health_marker_sha256=sha(health_marker) if health_marker.is_file() else None,
        actual_klippy_state=info['klippy_state'],parser=parser,physical_hardware=False,printing_ready=False))
    return json.loads(receipt.read_text())


def audit_boots(receipt_dir):
    """Canonical data-parent receipts exclude the archived source's siblings."""
    receipts=[json.loads(path.read_text()) for path in Path(receipt_dir).glob('*.json')]
    passed=[row for row in receipts if row.get('result')=='PASS']
    restored=[row for row in passed if row.get('expected')=='restored']
    previous=[row for row in passed if row.get('expected')=='previous']
    require(len(restored)>=2 and len(previous)>=1,'Two restored boots and rollback previous boot required')
    ids=[row['boot_id'] for row in passed]
    require(len(ids)==len(set(ids)),'A reboot must have a distinct real kernel boot ID')
    require(all(row.get('physical_hardware') is False and row.get('printing_ready') is False for row in passed),
            'Software qualification cannot assert physical readiness')
    return dict(result='PASS',restored_boots=len(restored),previous_boots=len(previous),boot_ids=ids,
                physical_hardware=False,printing_ready=False)


def host_assert(fixture, expected, output):
    """Strict CA/hostname verification and real installed gateway/PAM/API requests."""
    import base64
    import http.client
    import ssl
    fixture=private_fixture(fixture); require(expected in ('previous','restored'),'Known paired state required')
    credentials=json.loads((fixture/'credentials.json').read_text()); login=credentials[expected]
    ca=fixture/(expected+'-ca.crt'); context=ssl.create_default_context(cafile=str(ca))
    auth='Basic '+base64.b64encode((login['username']+':'+login['password']).encode()).decode()
    def request(port,path,authorization=None,fields=None):
        connection=http.client.HTTPSConnection('127.0.0.1',port,context=context,timeout=15)
        headers={}
        if authorization: headers['Authorization']=authorization
        data=None
        if fields is not None: headers['Content-Type']='application/json';data=json.dumps(fields)
        try:
            connection.connect(); certificate=connection.sock.getpeercert(binary_form=True)
            connection.request('POST' if fields is not None else 'GET',path,body=data,headers=headers)
            response=connection.getresponse(); body=response.read(1024*1024+1)
            require(len(body)<=1024*1024,'Bounded service response required')
            return response.status,body,certificate
        finally: connection.close()
    anonymous,_,_=request(18443,'/'); require(anonymous==401,'Anonymous gateway access accepted')
    wrong='Basic '+base64.b64encode((login['username']+':deliberately-wrong').encode()).decode()
    require(request(18443,'/',wrong)[0]==401,'Wrong gateway password accepted')
    for route in ('/server/info','/websocket'):
        require(request(18443,route)[0]==401 and request(18443,route,wrong)[0]==401,
                'Unauthenticated API/WebSocket gateway request accepted')
    other='previous' if expected=='restored' else 'restored'
    other_login=credentials[other]
    other_auth='Basic '+base64.b64encode((other_login['username']+':'+other_login['password']).encode()).decode()
    require(request(18443,'/',other_auth)[0]==401,'Other generation gateway password accepted')
    status,body,cert=request(18443,'/',auth); require(status==200 and b'<html' in body.lower(),'Actual Mainsail assets unavailable')
    status,body,_=request(18443,'/server/info',auth); require(status==200,'Authenticated actual Moonraker API unavailable')
    info=json.loads(body)['result']; require(info.get('moonraker_version') and info.get('klippy_state') in ('disconnected','startup','error','shutdown'),'Actual API observation missing')
    status,body,_=request(18443,'/access/login',auth,login)
    require(status==200 and json.loads(body).get('result',{}).get('token'),'Actual restored native Moonraker owner login failed')
    require(request(18443,'/access/login',auth,other_login)[0] in (400,401),'Other generation native password accepted')
    owner=credentials['owner']; owner_auth='Basic '+base64.b64encode((owner['username']+':'+owner['password']).encode()).decode()
    require(request(19090,'/cockpit/login')[0]==401,'Anonymous Cockpit login accepted')
    require(request(19090,'/cockpit/login',wrong)[0]==401,'Wrong Cockpit login accepted')
    require(request(19090,'/cockpit/login',owner_auth)[0]==200,'Real paired OS PAM owner login failed')
    # The other generated state's authority must fail strict verification.
    rejected=False
    connection=http.client.HTTPSConnection('127.0.0.1',18443,context=ssl.create_default_context(cafile=str(fixture/(other+'-ca.crt'))),timeout=15)
    try:
        connection.request('GET','/'); connection.getresponse()
    except ssl.SSLCertVerificationError: rejected=True
    finally: connection.close()
    require(rejected,'Other generated authority accepted the active service certificate')
    output=Path(output); output.mkdir(mode=0o700)
    certificate=output/'service-public.crt';certificate.write_text(ssl.DER_cert_to_PEM_cert(cert));certificate.chmod(0o644)
    # Pin the daemon's actual host key, and authenticate using only this
    # generated owner's key. No host SSH configuration, agents or global
    # known-host records are consulted and private key bytes are never read.
    public_host=fixture/(expected+'-ssh-host.pub')
    expectations=json.loads((fixture/'stack-expectations.json').read_text())['states'][expected]
    require(sha(public_host)==expectations['ssh_public_sha256'],'Generated SSH host public key differs')
    fields=public_host.read_text().split(); require(len(fields)>=2 and fields[0]=='ssh-ed25519','Expected generated Ed25519 host key')
    known_hosts=output/'known_hosts'
    with known_hosts.open('x') as stream:
        os.fchmod(stream.fileno(),0o600); stream.write('[127.0.0.1]:12222 '+fields[0]+' '+fields[1]+'\n')
    identity=fixture/'owner-key'; info=identity.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.geteuid() and
            not info.st_mode & 0o077,'Private generated owner key required')
    command=['ssh','-F','/dev/null','-p','12222','-i',str(identity),'-o','IdentityAgent=none',
        '-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known_hosts),
        '-o','GlobalKnownHostsFile=/dev/null','-o','BatchMode=yes','-o','PasswordAuthentication=no',
        '-o','KbdInteractiveAuthentication=no','-o','PreferredAuthentications=publickey',
        '-o','ConnectTimeout=10','-o','ConnectionAttempts=1','sv08@127.0.0.1','id','-u']
    ssh=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=20)
    require(ssh.returncode==0 and ssh.stdout.strip()=='1000','Actual pinned SSH host identity/owner-key authentication failed')
    # Never retain tokens, response bodies or credentials in evidence.
    result=dict(result='PASS',expected=expected,strict_ca_and_hostname=True,wrong_ca_rejected=True,
        anonymous_rejected=True,wrong_password_rejected=True,other_state_password_rejected=True,
        native_owner_login=True,ssh_host_key_verified=True,ssh_owner_authenticated=True,ssh_owner_uid=1000,paired_os_pam_login=True,pam_password_portable=False,
        actual_moonraker_version=info['moonraker_version'],klippy_state=info['klippy_state'],physical_hardware=False,printing_ready=False)
    write_json(output/'host-assert.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=('provision','bootstrap','restore','activate','rollback','normal-assert','host-assert','audit-boots'),required=True)
    p.add_argument('--disposable-marker',type=Path,required=True); p.add_argument('--work',type=Path)
    p.add_argument('--output',type=Path);p.add_argument('--release',type=Path);p.add_argument('--owner-public-key',type=Path)
    p.add_argument('--expected',choices=('restored','previous'));p.add_argument('--expectations',type=Path,default=Path('/usr/lib/sv08/stack-expectations.json'))
    p.add_argument('--receipt-dir',type=Path,default=Path('/data/stack-receipts'));p.add_argument('--deadline',type=int,default=600)
    a=p.parse_args(); require(a.disposable_marker.read_text()==MARKER,'Disposable guest marker required')
    if a.phase=='provision':
        try: result=provision(a.work,json.loads(a.release.read_text()),a.owner_public_key)
        finally:
            if a.work and a.work.is_dir(): a.work.chmod(0o700)
    elif a.phase=='bootstrap':result=bootstrap()
    elif a.phase=='audit-boots':result=audit_boots(a.receipt_dir)
    elif a.phase=='host-assert':result=host_assert(a.work,a.expected,a.output)
    elif a.phase=='normal-assert': result=normal_assert(a.expected,a.expectations,a.receipt_dir,a.deadline)
    else: result=recover(a.phase)
    print('SV08_RECOVERY_STACK '+json.dumps(result,sort_keys=True),flush=True)

if __name__=='__main__': main()
