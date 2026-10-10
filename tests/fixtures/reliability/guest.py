"""Installed ARM/systemd/RAUC journey; printer and idle ACK are simulated."""
import hashlib,json,os,select,signal,shutil,socket,sqlite3,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/usr/lib/sv08')
DATA=Path('/data');RUNTIME=Path('/run/sv08')
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(value,message):
    if not value:raise AssertionError(message)
def command(*args):
    result=subprocess.run(args,text=True,capture_output=True,timeout=120)
    if result.returncode:raise subprocess.CalledProcessError(result.returncode,args,result.stdout,result.stderr)
    return result.stdout.strip()
def wait(predicate):
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.25)
    raise AssertionError('Bounded readiness timed out')
def interrupted_copy_child(root):
    import sv08_state
    original=sv08_state.snapshot
    def pause_after_copy(source,target):
        original(source,target)
        print('RELIABILITY_COPY_PAUSED '+json.dumps({'target':str(target),'target_fingerprint':sv08_state.fingerprint(target),'source_fingerprint':sv08_state.fingerprint(source)}),flush=True)
        os.kill(os.getpid(),signal.SIGSTOP)
    sv08_state.snapshot=pause_after_copy
    sv08_state.Store(root).prepare_boot('B','interrupted-target')
def interruption_checks():
    from sv08_state import Store,fingerprint
    root=DATA/'interruption-store';require(not root.exists(),'Interruption fixture already exists')
    store=Store(root);store.initialize();source=store.prepare_boot('A','interrupted-source');source_path=Path(source['generation'])
    (source_path/'config/fixture.cfg').write_text('interruption-source-preserved\n');store.expect_trial('B','interrupted-target','A')
    before=digest(root/'state.json');source_before=fingerprint(source_path);generations=set((root/'generations').iterdir())
    child=subprocess.Popen(['/usr/bin/python3','-u','/input/guest.py','--interrupt-copy',str(root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    output=b'';receipt=None;started=time.monotonic()
    try:
        while time.monotonic()-started<15:
            if select.select([child.stdout],[],[],.25)[0]:
                output+=os.read(child.stdout.fileno(),4096)
                require(len(output)<8192,'Interrupted child output exceeded bound')
                for line in output.decode().splitlines():
                    if line.startswith('RELIABILITY_COPY_PAUSED '):receipt=json.loads(line.split(' ',1)[1])
                if receipt:break
            if child.poll() is not None:break
        require(receipt is not None,'Child did not complete actual snapshot before interruption')
        child.kill();require(child.wait(timeout=5)==-signal.SIGKILL,'Child not actually interrupted')
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=5)
    target=Path(receipt['target']);require(target in set((root/'generations').iterdir())-generations,'Completed orphan target missing')
    require(fingerprint(target)==receipt['target_fingerprint'] and fingerprint(source_path)==source_before==receipt['source_fingerprint'] and digest(root/'state.json')==before,'Interrupted copy modified source or published state')
    retry=store.prepare_boot('B','interrupted-target');require(Path(retry['generation'])!=target and (Path(retry['generation'])/'config/fixture.cfg').read_text()=='interruption-source-preserved\n','Retry reused orphan or lost source')
    before_migration=digest(root/'state.json')
    try:store.prepare_boot('A','interrupted-source',schema=2)
    except ValueError as exc:require('Unsupported' in str(exc),'Wrong migration refusal')
    else:raise AssertionError('Unsupported migration accepted')
    require(digest(root/'state.json')==before_migration,'Migration refusal changed state')
    print('RELIABILITY_INTERRUPTION_RESULT '+json.dumps({'child_pid':child.pid,'child_exit':child.returncode,'completed_copy':receipt,'registry_sha256_before_and_after_interruption':before,'source_fingerprint_preserved':source_before,'retry_generation':retry['generation'],'migration_registry_sha256_preserved':before_migration,'elapsed_seconds':time.monotonic()-started}),flush=True)
    shutil.rmtree(root)
def simulated_printer():
    require(command('systemd-detect-virt','--vm')=='qemu','Not disposable QEMU')
    require('sv08.test=rauc-backend' in Path('/proc/cmdline').read_text().split(),'Missing fixture guard')
    require(not list(Path('/dev').glob('ttyACM*')),'Unexpected MCU')
    view=RUNTIME/'printer_data';(view/'comms').mkdir(exist_ok=True)
    path=view/'comms/update.sock';path.unlink(missing_ok=True)
    server=socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET);server.bind(str(path));server.listen(2)
    db=sqlite3.connect(view/'database/reliability.db');db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA wal_autocheckpoint=0')
    db.execute('CREATE TABLE IF NOT EXISTS values_seen(value TEXT UNIQUE)');db.execute('INSERT OR IGNORE INTO values_seen VALUES("before-stage")');db.commit()
    while True:
        if (DATA/'late-write-request').exists():
            db.execute('INSERT OR IGNORE INTO values_seen VALUES("committed-late-wal")');db.commit();(DATA/'late-write-ready').touch()
        if select.select([server],[],[],.1)[0]:
            connection,_=server.accept()
            with connection:
                require(json.loads(connection.recv(4096))=={'action':'quiesce'},'Unexpected simulated request')
                printing=(DATA/'simulated-printing').exists()
                connection.sendall(json.dumps({'accepted':not printing,'wait_for_service_exit':not printing,'reason':'simulated printing' if printing else 'simulated idle ACK'}).encode())
def main():
    from sv08_state import Store,atomic_json
    from sv08_transaction import Transaction
    from sv08_rauc import Backend
    from sv08_bundle import inspect
    from sv08_admission import Admission
    from sv08_network import Network
    from sv08_restart import clear,intent,require_running
    require(command('systemd-detect-virt','--vm')=='qemu','Not QEMU')
    require(Path('/proc/1/comm').read_text().strip()=='systemd','Not systemd PID1')
    require(Path('/sys/block/vda/serial').read_text().strip()=='SV08-QEMU-DISPOSABLE','Unexpected medium')
    boot=json.loads((RUNTIME/'boot.json').read_text());manifest=json.loads(Path('/usr/lib/sv08/release.json').read_text())
    require(manifest['deployable'] is False,'Deployable image refused')
    phase_path=DATA/'reliability-phase.json';phase=json.loads(phase_path.read_text()) if phase_path.exists() else {'phase':0,'boots':[]}
    number=phase['phase'];require(boot['boot_id'] not in phase['boots'],'Repeated boot identity');phase['boots'].append(boot['boot_id'])
    store=Store('/data/sv08');policy=json.loads(Path('/usr/lib/sv08/update-policy.json').read_text())
    backend=Backend(manifest,policy,json.loads(Path('/usr/lib/sv08/layout.json').read_text()),json.loads(Path('/usr/lib/sv08/environment.json').read_text()),fixture=True)
    tx=Transaction(store,backend,Admission())
    require(command('/usr/bin/rauc','--version')=='rauc 1.15.2','Wrong RAUC version')
    require(digest('/usr/bin/rauc')=='51d7c057c7fb00917287b5324303c747e71c5406f4c1363a678578ac7a3b12e3','RAUC changed')
    package=command('dpkg-query','-W','-f=${Package} ${Version} ${db:Status-Abbrev}\\n','rauc','sv08-klipper')
    require('rauc 1.15.2-0sv08.1 ii' in package and 'sv08-klipper 0.0+gitf0892d82-1 ii' in package,'Packages not configured')
    from sv08_identity import Identity
    authority=Identity()
    if number==0:
        recovery_path=Path('/input/interrupted-install.json')
        if recovery_path.exists():
            expected=json.loads(recovery_path.read_text());recovered=tx.load()
            require(recovered is not None and recovered['id']==expected['transaction']['id'] and recovered['phase']=='cancelled' and recovered['boot_id']!=boot['boot_id'],'Production health failed interrupted-install cancellation')
            require(store.load()==expected['source_state'],'Interrupted install changed source registry')
            backend.validate_context(boot)
            require(backend.primary()=='A' and backend.good('A'),'Production normal health failed source counter recovery')
            print('RELIABILITY_INTERRUPTED_INSTALL_RECOVERY '+json.dumps({'old_transaction_id':recovered['id'],'old_boot_id':recovered['boot_id'],'new_boot_id':boot['boot_id'],'phase':recovered['phase'],'source_registry_preserved':True,'fixture_source_counter_refilled':False}),flush=True)
        authority.ensure(['sv08-disposable.local'])
    current_authority=authority.current();require(current_authority is not None,'Persistent authority absent')
    identity={name:digest(store.root/'system'/name) for name in ('machine-id','hostname','hosts','ssh/ssh_host_ed25519_key','ssh/ssh_host_ed25519_key.pub')}
    for name in ('ca/ca.crt','ca/ca.key','services/server.crt','ssh/ssh_host_ed25519_key'):
        identity['authority/'+name]=digest(current_authority/name)
    require((current_authority/'ca/ca.key').stat().st_mode&0o777==0o600,'CA private key permissions differ')
    if 'identity' in phase:require(identity==phase['identity'],'Persistent identity changed')
    else:phase['identity']=identity
    if (RUNTIME/'qemu-fallback-requested.json').exists():
        require(number==2 and boot['slot']=='A' and boot['trial'],'Unexpected failed target')
        require(not (RUNTIME/'os-health-ready').exists() and (RUNTIME/'trial').exists(),'Failed health released gate')
        require(tx.load()['phase']=='armed','Failed health changed journal')
        require(any(json.loads(p.read_text())['boot_id']==boot['boot_id'] for p in (store.root/'shared/logs/journal/boot-health').glob('*.json')),'Missing failure record')
        failed_generation=Path(boot['generation'])
        (failed_generation/'config/owner.cfg').write_text('bad-target-only\n')
        db=sqlite3.connect(failed_generation/'database/reliability.db');db.execute('INSERT OR IGNORE INTO values_seen VALUES("bad-target-only")');db.commit();db.close()
        phase['failed_target_boots']=phase.get('failed_target_boots',0)+1;atomic_json(phase_path,phase)
        print('RELIABILITY_FAILED_TARGET_RESULT '+json.dumps({'boot_id':boot['boot_id'],'slot':'A','retry':phase['failed_target_boots'],'actual_production_health':True}),flush=True)
        command('systemctl','--no-block','reboot');return
    if number==4:
        require(boot['slot']=='B' and boot['mode']=='writable' and boot['customized'] and not boot['trial'],'Failed normal boot identity differs')
        require(not (RUNTIME/'os-health-ready').exists(),'Failed normal health opened readiness')
        attempts=command('fw_printenv','-c','/etc/fw_env.config','BOOT_B_LEFT')
        require(attempts=='BOOT_B_LEFT=2','Failed normal health replenished attempts')
        require(command('systemctl','show','sv08-boot-health.service','-p','ActiveState','--value')=='failed','Normal health failure not observed')
        require(store.load()==phase['normal_state'],'Failed health changed registry')
        (DATA/'normal-health-failure').unlink()
        command('systemctl','reset-failed','sv08-boot-health.service');command('systemctl','restart','sv08-boot-health.service')
        require((RUNTIME/'os-health-ready').is_file() and command('fw_printenv','-c','/etc/fw_env.config','BOOT_B_LEFT')=='BOOT_B_LEFT=3','Healthy retry did not restore readiness/attempts')
        store.policy(mode='immutable');phase['phase']=5;atomic_json(phase_path,phase)
        print('RELIABILITY_FAILED_NORMAL_HEALTH_RESULT '+json.dumps({'boot_id':boot['boot_id'],'failed_attempts':2,'healthy_retry_attempts':3,'normal_registry_preserved':True}),flush=True)
        print('RELIABILITY_PHASE_RESULT '+json.dumps({'phase':4,'slot':'B','boot_id':boot['boot_id']}),flush=True)
        command('systemctl','--no-block','reboot');return
    require((RUNTIME/'os-health-ready').is_file() and not (RUNTIME/'trial').exists(),'Actual health gate absent')
    generation=Path(boot['generation'])
    def start_printers():
        command('systemctl','start','sv08-klipper.service','sv08-moonraker.service');wait(lambda:(RUNTIME/'printer_data/comms/update.sock').exists())
        require(command('systemctl','is-active','sv08-klipper.service')=='active','Simulated printer inactive')
    def network_with_queue(mode):
        def invoke(*args):
            if args==('systemctl','--no-block','reboot'):
                if mode=='refused':raise FileNotFoundError('injected proven launch refusal')
                if mode=='lost-ack':raise subprocess.TimeoutExpired(args,1)
                if mode=='held':return ''
            return command(*args)
        return Network(command=invoke)
    if number==0:
        require(boot['slot']=='A' and not boot['trial'],'Initial source differs');backend.validate_context(boot)
        (generation/'config/owner.cfg').write_text('original-owner-config\n');(DATA/'user-sentinel').write_text('shared-owner-artifact\n');start_printers()
        (DATA/'simulated-printing').touch()
        try:network_with_queue('held').request({'method':'restart','confirm':True})
        except ValueError as exc:require('Idle admission refused' in str(exc),'Wrong print refusal')
        else:raise AssertionError('Printing restart accepted')
        (DATA/'simulated-printing').unlink()
        try:network_with_queue('refused').request({'method':'restart','confirm':True})
        except FileNotFoundError:pass
        else:raise AssertionError('Injected refusal accepted')
        require(intent() is None and command('systemctl','is-active','sv08-klipper.service')=='active','Known refusal failed restoration')
        network_with_queue('held').request({'method':'restart','confirm':True});require(intent() is not None,'Queue lacks shutdown intent')
        for operation in (lambda:store.policy(mode='writable'),lambda:network_with_queue('held').request({'method':'restart','confirm':True}),lambda:require_running()):
            try:operation()
            except ValueError:pass
            else:raise AssertionError('Queued reboot admitted mutation')
        result=subprocess.run(['systemctl','start','sv08-klipper.service'],text=True,capture_output=True,timeout=15)
        require(result.returncode!=0 and command('systemctl','show','sv08-klipper.service','-p','ActiveState','--value')!='active','ExecStartPre admitted queued start')
        clear(RUNTIME,intent());command('systemctl','reset-failed','sv08-klipper.service');start_printers()
        blocked=store.root/'software/jobs/fixture-pending.json';blocked.parent.mkdir(parents=True,exist_ok=True);atomic_json(blocked,{'status':'queued'})
        try:network_with_queue('held').request({'method':'restart','confirm':True})
        except ValueError as exc:require('software job' in str(exc),'Wrong job refusal')
        else:raise AssertionError('Queued software admitted restart')
        try:store.policy(mode='writable')
        except ValueError:pass
        else:raise AssertionError('Queued software admitted mode switch')
        blocked.unlink()
        print('RELIABILITY_GOOD_STAGE_BEGIN',flush=True)
        bundle=Path('/input/reliability-good.raucb');proof=inspect(bundle,policy,Path('/etc/rauc/release-keyring.pem'));tx.stage(bundle,proof,boot)
        require(store.load()['slots'].keys()=={'A'},'State copied prematurely')
        try:store.policy(mode='writable')
        except ValueError:pass
        else:raise AssertionError('Staged image admitted mode switch')
        (generation/'config/owner.cfg').write_text('committed-after-stage\n');(DATA/'late-write-request').touch();wait(lambda:(DATA/'late-write-ready').exists())
        require((generation/'database/reliability.db-wal').stat().st_size>0,'Committed late WAL absent')
        phase['source_generation']=boot['generation'];tx.arm(boot);phase['phase']=1;atomic_json(phase_path,phase)
        try:network_with_queue('lost-ack').request({'method':'restart','confirm':True})
        except (subprocess.TimeoutExpired,ValueError):pass
        else:raise AssertionError('Lost ACK returned success')
        require(intent() is not None and command('systemctl','show','sv08-klipper.service','-p','ActiveState','--value')=='inactive','Lost ACK reopened admission/restored printer')
        try:store.policy(auto_update=False)
        except ValueError:pass
        else:raise AssertionError('Lost ACK allowed mutation')
        print('RELIABILITY_SOURCE_STAGE_RESTART_EXCLUSION_PASS',flush=True)
    elif number==1:
        require(boot['slot']=='B' and boot['trial'] and tx.load()['phase']=='complete' and store.load()['pending'] is None,'Good B not confirmed')
        require(boot['generation']!=phase['source_generation'] and (generation/'config/owner.cfg').read_text()=='committed-after-stage\n','Late state copy lost')
        db=sqlite3.connect(generation/'database/reliability.db')
        require(db.execute('SELECT value FROM values_seen ORDER BY value').fetchall()==[('before-stage',),('committed-late-wal',)] and db.execute('PRAGMA quick_check').fetchone()==('ok',),'Committed SQLite WAL lost');db.close()
        (generation/'config/owner.cfg').write_text('preserved-good-target\n');phase['good_generation']=boot['generation']
        bundle=Path('/input/reliability-bad.raucb');proof=inspect(bundle,policy,Path('/etc/rauc/release-keyring.pem'));tx.stage(bundle,proof,boot);tx.arm(boot)
        phase['phase']=2;atomic_json(phase_path,phase);print('RELIABILITY_ACTUAL_SIGNED_UPDATE_CONFIRM_LATE_WAL_PASS',flush=True)
    elif number==2:
        require(boot['slot']=='B' and tx.load()['phase']=='failed' and phase.get('failed_target_boots')==3,'Fallback/retries not reconciled')
        require(boot['generation']==phase['good_generation'] and (generation/'config/owner.cfg').read_text()=='preserved-good-target\n' and (DATA/'user-sentinel').read_text()=='shared-owner-artifact\n','Fallback/user data changed')
        db=sqlite3.connect(generation/'database/reliability.db');require(db.execute('SELECT value FROM values_seen WHERE value="bad-target-only"').fetchall()==[],'Failed-target database write leaked into fallback');db.close()
        require(command('fw_printenv','-c','/etc/fw_env.config','BOOT_B_LEFT')=='BOOT_B_LEFT=3','Fallback normal health did not restore attempts');store.policy(mode='writable');phase['phase']=3;atomic_json(phase_path,phase)
        print('RELIABILITY_ACTUAL_FAILED_HEALTH_RETRIES_FALLBACK_PASS',flush=True)
    elif number==3:
        require(boot['slot']=='B' and boot['mode']=='writable' and boot['customized'],'Writable not customized')
        healthy_boots=phase.get('healthy_writable_boots',0)+1
        require(command('fw_printenv','-c','/etc/fw_env.config','BOOT_B_LEFT')=='BOOT_B_LEFT=3','Healthy writable boot did not replenish attempts')
        cmdline=dict(value.split('=',1) for value in Path('/proc/cmdline').read_text().split() if value.startswith('sv08.fixture.') and '=' in value)
        attempts_before=int(cmdline['sv08.fixture.attempts_before'])
        require(attempts_before in (1,3),'Unexpected normal boot attempt input')
        if attempts_before==1:
            require(healthy_boots==4 and command('fw_printenv','-c','/etc/fw_env.config','BOOT_A_LEFT')=='BOOT_A_LEFT=0','All-zero recovery fixture identity differs')
        if healthy_boots>1:
            require(Path('/etc/reliability-owner-custom.conf').read_text()=='owner-root-customization\n' and (generation/'config/custom.cfg').read_text()=='owner-application-customization\n','Repeated writable boot lost customization')
        before_package=digest(store.root/'state.json')
        with Admission()():
            result=subprocess.run(['/usr/bin/python3','/usr/lib/sv08/sv08_package.py','--execute','check'],capture_output=True,text=True,timeout=15)
        require(result.returncode!=0 and 'Resource temporarily unavailable' in result.stderr and not (RUNTIME/'package-lease.json').exists() and digest(store.root/'state.json')==before_package,'Actual package CLI bypassed admission or changed state')
        print('RELIABILITY_ACTUAL_PACKAGE_EXCLUSION_RESULT '+json.dumps({'exit_status':result.returncode,'stderr':result.stderr.strip(),'state_sha256_preserved':before_package,'package_lease':False}),flush=True)
        if healthy_boots==1:interruption_checks()
        Path('/etc/reliability-owner-custom.conf').write_text('owner-root-customization\n');(generation/'config/custom.cfg').write_text('owner-application-customization\n')
        phase['healthy_writable_boots']=healthy_boots
        if healthy_boots==4:
            phase['normal_state']=store.load();(DATA/'normal-health-failure').touch();phase['phase']=4
        atomic_json(phase_path,phase)
        print('RELIABILITY_NORMAL_WRITABLE_BOOT_RESULT '+json.dumps({'boot_id':boot['boot_id'],'normal_boot':healthy_boots,'host_attempts_before_consumption':attempts_before,'attempts_after_consumption_inferred':attempts_before-1,'attempts_restored':3,'customized':True}),flush=True)
    elif number==5:
        require(phase['healthy_writable_boots']==4,'Fewer than four healthy normal writable boots')
        require(boot['mode']=='immutable' and boot['customized'] and Path('/etc/reliability-owner-custom.conf').read_text()=='owner-root-customization\n' and (generation/'config/custom.cfg').read_text()=='owner-application-customization\n','Customization lost')
        before=tx.path.read_bytes()
        try:tx.stage(Path('/input/reliability-good.raucb'),{'release':'forbidden','bundle_sha256':'a'*64},boot)
        except ValueError as exc:require('Customized/writable' in str(exc),'Wrong replacement refusal')
        else:raise AssertionError('Customized replacement accepted')
        require(tx.path.read_bytes()==before,'Refused replacement changed journal')
        small=Path('/run/no-space');small.mkdir();command('mount','-t','tmpfs','-o','size=64m','tmpfs',str(small));limited=Store(small/'sv08');limited.initialize();old=(limited.root/'state.json').read_bytes()
        try:limited.prepare_boot('A','no-space')
        except ValueError as exc:require('Insufficient' in str(exc),'Wrong no-space refusal')
        else:raise AssertionError('Constrained storage admitted generation')
        require((limited.root/'state.json').read_bytes()==old and not list((limited.root/'generations').iterdir()),'No-space changed state')
        command('umount',str(small));phase['phase']=6;atomic_json(phase_path,phase)
        print('RELIABILITY_CUSTOMIZED_DERIVATION_GATE_AND_NO_SPACE_PASS',flush=True);print('RELIABILITY_JOURNEY_PASS',flush=True);command('systemctl','--no-block','poweroff');return
    else:raise AssertionError('Unexpected phase')
    print('RELIABILITY_PHASE_RESULT '+json.dumps({'phase':number,'slot':boot['slot'],'boot_id':boot['boot_id'],'actual_rauc':True,'actual_prepare_health':True,'printer':'simulated'}),flush=True)
    command('systemctl','--no-block','reboot')
if __name__=='__main__':
    if '--interrupt-copy' in sys.argv:interrupted_copy_child(sys.argv[-1])
    elif '--printer' in sys.argv:simulated_printer()
    else:
        try:main()
        except BaseException as exc:
            print('RELIABILITY_FAILURE '+repr(exc),flush=True)
            for unit in ('sv08-prepare.service','sv08-boot-health.service','rauc.service','fixture.service'):
                result=subprocess.run(['journalctl','--no-pager','-u',unit,'-n','30'],capture_output=True,text=True,timeout=15);print('BOUNDED_UNIT_DIAGNOSTIC '+unit+' '+result.stdout[-12000:],flush=True)
            subprocess.run(['systemctl','--no-block','poweroff'],timeout=15);raise
