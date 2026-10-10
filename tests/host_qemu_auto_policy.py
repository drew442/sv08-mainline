#!/usr/bin/env python3
"""Automatic policy ARM guest journey and signed local feed publication.

Used by the bounded reliability runner with automatic_policy_fixture=true,
release_revisions explicit, max_boots=6 and the patched ARM RAUC hash. Transport
and printer services are simulated; signatures, slot writes, controlled restart,
production preparation/health and environment attempt consumption are real.
"""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

NOW = 1791597600
RELEASES = ('automatic-good', 'automatic-bad')


def publish(manifest_path):
    config=json.loads(Path(manifest_path).read_text());scratch=Path(config['scratch'])
    if not config.get('automatic_policy_fixture'):raise ValueError('Explicit automatic fixture required')
    for sequence,release in enumerate(RELEASES,2):
        bundle=scratch/'input'/f'{release}.raucb'
        with bundle.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        index=dict(format_version=1,channel='fixture',sequence=sequence,issued=NOW-60,expires=NOW+3600,
                   compatible='sv08-offline-test-only',release=release,
                   release_revision=config['release_revisions'][release],bundle=bundle.name,
                   bytes=bundle.stat().st_size,sha256=digest)
        path=scratch/'input'/f'{release}-index.json'
        path.write_text(json.dumps(index,sort_keys=True,separators=(',',':')))
        subprocess.run(['openssl','cms','-sign','-binary','-in',str(path),'-signer',str(scratch/'fixture-cert.pem'),
                        '-inkey',str(scratch/'fixture-key.pem'),'-outform','DER','-out',str(path)+'.p7s'],check=True,timeout=15)
    (scratch/'input/fixture-signers.pem').write_bytes((scratch/'fixture-cert.pem').read_bytes())


def guest():
    sys.path.insert(0,'/usr/lib/sv08');sys.path.insert(0,'/input')
    import reliability_helpers as g
    from sv08_state import Store,atomic_json
    from sv08_transaction import Transaction
    from sv08_rauc import Backend
    from sv08_bundle import inspect
    from sv08_admission import Admission
    from sv08_feed import Feed
    from sv08_auto_reboot import AutoReboot
    from sv08_staging import Staging
    from sv08_update_policy import effective
    from sv08_identity import Identity
    g.require(g.command('systemd-detect-virt','--vm')=='qemu','Not QEMU')
    g.require(Path('/proc/1/comm').read_text().strip()=='systemd','Not systemd PID1')
    g.require(Path('/sys/block/vda/serial').read_text().strip()=='SV08-QEMU-DISPOSABLE','Unexpected target')
    boot=json.loads((g.RUNTIME/'boot.json').read_text());manifest=json.loads(Path('/usr/lib/sv08/release.json').read_text())
    g.require(manifest['deployable'] is False,'Physical image refused')
    store=Store('/data/sv08');policy=json.loads(Path('/usr/lib/sv08/update-policy.json').read_text())
    backend=Backend(manifest,policy,json.loads(Path('/usr/lib/sv08/layout.json').read_text()),json.loads(Path('/usr/lib/sv08/environment.json').read_text()),fixture=True)
    tx=Transaction(store,backend,Admission());restart=AutoReboot(store,tx,boot)
    phase_path=g.DATA/'automatic-phase.json'
    phase=json.loads(phase_path.read_text()) if phase_path.exists() else dict(phase=0,boots=[])
    g.require(boot['boot_id'] not in phase['boots'],'Repeated boot identity');phase['boots'].append(boot['boot_id'])
    number=phase['phase']
    package=g.command('dpkg-query','-W','-f=${Version}','rauc')
    g.require(package=='1.15.2-0sv08.2','Wrong patched package')
    service_policy=json.loads(Path('/usr/lib/sv08/rauc-service-policy.json').read_text())
    g.require(g.digest('/usr/bin/rauc')==service_policy['executable_sha256'],'RAUC identity differs')
    if number==0:
        authority=Identity();authority.ensure(['sv08-disposable.local'])
        phase['identity']={name:g.digest(store.root/'system'/name) for name in ('machine-id','hostname','hosts','ssh/ssh_host_ed25519_key.pub')}
        current=authority.current();phase['identity']['CA']=g.digest(current/'ca/ca.crt')
        g.require(boot['slot']=='A' and store.load()['slots']['A']['release_revision']==1,'Initial revision absent')
        generation=Path(boot['generation']);(generation/'config/owner.cfg').write_text('preserved owner settings\n')
        (g.DATA/'owner-sentinel').write_text('shared user artifact\n')
        # Recorded customization of the source is preserved when the owner has
        # individually configured its admission exception; no flags are cleared.
        with store.locked():
            state=store.load();state['slots']['A']['customized']=True;state['update_policy']=effective({'check_customization':False},automatic=True);store.save(state)
    else:
        current=Identity().current()
        observed={name:g.digest(store.root/'system'/name) for name in ('machine-id','hostname','hosts','ssh/ssh_host_ed25519_key.pub')};observed['CA']=g.digest(current/'ca/ca.crt')
        g.require(observed==phase['identity'],'Persistent identity changed')
    if (g.RUNTIME/'qemu-fallback-requested.json').exists():
        g.require(number==2 and boot['slot']=='A' and boot['trial'],'Unexpected failed trial')
        g.require(not (g.RUNTIME/'os-health-ready').exists(),'Failed trial opened printer gate')
        g.require(tx.load()['phase']=='armed','Failure incorrectly confirmed')
        (Path(boot['generation'])/'config/owner.cfg').write_text('failed target only\n')
        phase['failed_boots']=phase.get('failed_boots',0)+1;atomic_json(phase_path,phase)
        print('RELIABILITY_FAILED_TARGET_RESULT '+json.dumps(dict(slot='A',boot_id=boot['boot_id'],failed_boots=phase['failed_boots'],actual_health=True)),flush=True)
        g.command('systemctl','--no-block','reboot');return
    g.require((g.RUNTIME/'os-health-ready').exists(),'Health readiness missing')
    if number==1:
        g.require(boot['slot']=='B' and tx.load()['phase']=='complete' and store.load()['pending'] is None,'Automatic target not confirmed')
        g.require(store.load()['slots']['A']['customized'] is True,'Source customization record was cleared')
        g.require((Path(boot['generation'])/'config/owner.cfg').read_text()=='preserved owner settings\n','Settings copy lost')
        phase['good_generation']=boot['generation']
        print('AUTOMATIC_HEALTHY_CONFIRMATION '+json.dumps(dict(transaction=tx.load()['id'],slot='B',source_customization_preserved=True)),flush=True)
    if number==2:
        g.require(boot['slot']=='B' and tx.load()['phase']=='failed' and phase.get('failed_boots')==3,'Failed health fallback not reconciled')
        g.require(boot['generation']==phase['good_generation'],'Fallback generation changed')
        g.require((Path(boot['generation'])/'config/owner.cfg').read_text()=='preserved owner settings\n','Failed target settings leaked')
        g.require((g.DATA/'owner-sentinel').read_text()=='shared user artifact\n','User data changed')
        g.require(restart.run()=='reboot-observed','Restart did not reconcile')
        atomic_json(phase_path,phase)
        print('AUTOMATIC_FAILED_HEALTH_FALLBACK '+json.dumps(dict(transaction=tx.load()['id'],slot='B',failed_boots=3,identity_preserved=True)),flush=True)
        print('RELIABILITY_JOURNEY_PASS',flush=True);g.command('systemctl','--no-block','poweroff');return
    release=RELEASES[number]
    def fetch(url,limit,deadline):
        filename=url.rsplit('/',1)[1]
        name=f'{release}-index.json'+('.p7s' if filename.endswith('.p7s') else '') if filename.startswith('index.') else filename
        path=Path('/input')/name
        g.require(path.stat().st_size<=limit,'Fixture transport exceeded declared bound')
        return path.open('rb')
    def verify(path):
        options=effective(store.load().get('update_policy'),automatic=True)
        return inspect(path,policy,Path('/etc/rauc/release-keyring.pem'),lease_fd=staging.lease_fd,options=options,automatic=True)
    def activate():
        journal=tx.load()
        if journal['phase'] in ('complete','failed','cancelled'):return restart.run()
        g.require(journal['phase']=='armed' and journal['automatic'],'Not automatically armed')
        phase['phase']=number+1;atomic_json(phase_path,phase)
        print('RELIABILITY_PHASE_RESULT '+json.dumps(dict(phase=number,slot=boot['slot'],transaction=journal['id'],actual_signed_feed=True,automatic=True,release_revision=journal['release_revision'])),flush=True)
        return restart.run()
    g.command('systemctl','start','sv08-klipper.service','sv08-moonraker.service')
    g.wait(lambda:(g.RUNTIME/'printer_data/comms/update.sock').exists())
    staging=Staging('/data/sv08/feed-bundles',max_bytes=policy['max_bundle_bytes'])
    config=dict(format_version=1,url='https://updates.invalid/',channel='fixture',ca_file='/input/fixture-signers.pem',signer_ca_file='/input/fixture-signers.pem')
    feed=Feed(store,staging,tx,boot,verify,config,now=lambda:NOW,fetch=fetch,restart=activate)
    g.require(feed.run()=='reboot-queued','Automatic restart not queued')
    print('AUTOMATIC_REBOOT_QUEUED '+json.dumps(restart.load()),flush=True)


if __name__=='__main__':
    if '--publish' in sys.argv:publish(sys.argv[-1])
    elif '--printer' in sys.argv:
        sys.path.insert(0,'/input');from reliability_helpers import simulated_printer;simulated_printer()
    else:
        try:guest()
        except BaseException as exc:
            print('RELIABILITY_FAILURE '+repr(exc),flush=True)
            for unit in ('sv08-prepare.service','sv08-boot-health.service','rauc.service','fixture.service'):
                result=subprocess.run(['journalctl','--no-pager','-u',unit,'-n','25'],capture_output=True,text=True,timeout=15)
                print('BOUNDED_UNIT_DIAGNOSTIC '+unit+' '+result.stdout[-10000:],flush=True)
            subprocess.run(['systemctl','--no-block','poweroff'],timeout=15);raise
