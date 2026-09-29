#!/usr/bin/env python3
"""One recovery return attempt, with live UART admission before fixed KVM HID.

Default inspection is inert. Existing coordinator SSH authentication is reused;
never transfer keys or let Beelink contact KVM. Retire with authenticated recovery
reboot/selection. Operational delivery requires the exact reviewed source gate.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.sd_boot_route import regular_bytes, sha

ATTEMPT = 'sd-recovery-return-20260929-01'
APPROVAL = '93f021c0fb801551d88d3ae04dc9683ee29092fe80d3f8872662d5227cfd10ea'
RISK_APPROVAL = 'd2a5dcd9cc8fc839a2c416305a8428e30bb2b194a8f98a975b982036c8bb613e'
COLLECTOR_SHA = '5c4e6cd4f1e8039949c83654c1265ffad51c269230268ca445e4491d7bf2b0ed'
RECOVERY_SHA = 'c83975508e1cafca51e23c6ad9e19408fa01b5d35be583b39a38c5b13ad2345c'
REPORTS = (bytes((5,0,59,0,0,0,0,0)),bytes(8),
           bytes((5,0,76,0,0,0,0,0)),bytes(8))
SOURCE_MAPPING = {
    'recovery_sha256':RECOVERY_SHA,
    'kernel_sha256':'5bc7c62df2b521610d0dea0a82b38aceb54af7d340a44b02a27428d6ea28dc34',
    'unit_chain_sha256':'c70df852d92d0c3dbdd074cb5524d343e196338d805818e50d90d796a1174dbd',
    'systemd_package_sha256':'dcc3ba37f0488ecd513820035b4efc300e198849f5b6437a9bac9c2f307149ab',
    'review_sha256':'e89460c6052d390bc328208e01db885e32165e5de693843caec3b6f06ab27c0d',
}
MAX_LINE = 16384
TIMEOUT = 20


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def token(value, *, path=False):
    pattern = r'/[A-Za-z0-9_./-]+' if path else r'[A-Za-z0-9][A-Za-z0-9_.:@-]*'
    if not isinstance(value,str) or not re.fullmatch(pattern,value) or '..' in value.split('/'):
        raise ValueError('Unsafe fixed command token')
    return value


def exception_admitted(policy):
    item = policy.get('recovery_return_exception',{})
    return (item.get('format')=='sv08-one-recovery-return-v1' and
            item.get('attempt')==ATTEMPT and item.get('approval_sha256')==APPROVAL and
            item.get('risk_amendment_sha256')==RISK_APPROVAL and
            re.fullmatch(r'[0-9a-f]{64}',item.get('operation_review_sha256','')) is not None and
            all(item.get(key) is True for key in
                ('counters_unknown','rtc_retention_unknown','jobs_disabled','claims_disabled','writer_markers_disabled')))


def process_identity(pid):
    data=Path(f'/proc/{pid}/stat').read_text()
    tail=data[data.rindex(')')+2:].split()
    if tail[0]=='Z':raise ValueError('Controller/parent is dead')
    return {'pid':pid,'starttime':int(tail[19]),
            'exe':os.readlink(f'/proc/{pid}/exe')}


def live_process(expected):
    if process_identity(expected['pid'])!=expected:
        raise ValueError('PID exited/reused or executable changed')


def descriptor(fd):
    info=os.fstat(fd)
    return {'fd':fd,'dev':info.st_dev,'inode':info.st_ino,'mode':info.st_mode,
            'rdev':info.st_rdev,'uid':info.st_uid}


def channel_read(stream,timeout=TIMEOUT):
    # Byte-at-a-time avoids buffered-reader readiness races and bounds protocol.
    fd=stream.fileno();deadline=time.monotonic()+timeout;data=bytearray()
    while time.monotonic()<deadline:
        if not select.select([fd],[],[],max(0,deadline-time.monotonic()))[0]:break
        byte=os.read(fd,1)
        if not byte:raise EOFError('Parent/SSH channel lost')
        data.extend(byte)
        if len(data)>MAX_LINE:raise ValueError('Oversized protocol message')
        if byte==b'\n':return json.loads(data)
    raise TimeoutError('Readiness acknowledgment timed out')


def channel_write(stream,item):
    stream.write(canonical(item)+b'\n');stream.flush()


def parent_live(parent,stream):
    live_process(parent)
    if select.select([stream.fileno()],[],[],0)[0]:
        # After one acknowledgment, any EOF/additional command is a stop.
        raise EOFError('Parent channel closed or unexpected extra acknowledgment')


def readiness(fd,capture,policy,nonce,channel_in,channel_out):
    """Actual child callback: proof after exclusive UART/capture admission."""
    from scripts.sv08_serial_boot_route import serial_identity
    child=process_identity(os.getpid());parent=process_identity(os.getppid())
    uart,raw=descriptor(fd),descriptor(capture)
    sources={'guard_sha256':sha(regular_bytes(__file__)),
             'serial_sha256':sha(regular_bytes(Path(__file__).with_name('sv08_serial_boot_route.py')))}
    def check():
        live_process(child);live_process(parent);serial_identity(fd,policy)
        if descriptor(fd)!=uart or descriptor(capture)!=raw:
            raise ValueError('Readiness descriptor binding changed')
        if sources!={'guard_sha256':sha(regular_bytes(__file__)),
                     'serial_sha256':sha(regular_bytes(Path(__file__).with_name('sv08_serial_boot_route.py')))}:
            raise ValueError('Controller source changed')
        os.fsync(capture)
    check()
    ready={'kind':'ready','attempt':ATTEMPT,'nonce':nonce,'child':child,
           'uart':uart,'capture':raw,'topology':policy['sysfs_path'],'dev_t':policy['dev_t'],**sources}
    channel_write(channel_out,ready)
    ack=channel_read(channel_in)
    if ack!={'kind':'ack','attempt':ATTEMPT,'nonce':nonce,'challenge':ack.get('challenge')} or not re.fullmatch(r'[0-9a-f]{64}',ack.get('challenge','')):
        raise ValueError('Malformed/stale acknowledgment')
    check()
    channel_write(channel_out,{**ready,'kind':'live','challenge':ack['challenge']})
    def still_live():
        check();parent_live(parent,channel_in)
    return still_live


def source_gate(policy):
    evidence=policy['mapping_evidence']
    if (any(evidence.get(key)!=value for key,value in SOURCE_MAPPING.items()) or
            evidence.get('route')!='ordered-ctrl-alt-del-target' or
            evidence.get('normal_final_reboot_force') is not True or
            evidence.get('early_force_risk_accepted') is not True or
            RISK_APPROVAL is None or evidence.get('risk_amendment_sha256')!=RISK_APPROVAL or
            evidence.get('event_or_reboot_count_proven') is not False or
            not all(re.fullmatch(r'[0-9a-f]{64}',evidence.get(key,'')) for key in
                    ('kernel_sha256','systemd_package_sha256','unit_chain_sha256','review_sha256'))):
        raise ValueError('Exact pinned recovery source/approval gate unresolved')


def validate(policy):
    if policy.get('attempt')!=ATTEMPT or not exception_admitted(policy['serial_policy']):
        raise ValueError('Only the explicitly approved unknown-counter attempt is admitted')
    if policy['serial_policy'].get('fresh_environment_reviewed') is not False:
        raise ValueError('Do not manufacture fresh environment evidence')
    for host in ('beelink_host','kvm_host'):token(policy[host])
    for key in ('remote_script','beelink_policy','kvm_policy','attempt_receipt'):
        token(policy[key],path=True)


def ssh(policy,host,mode,nonce):
    # ssh joins remote arguments into a shell string; every token is constrained.
    privilege=['sudo','-n'] if host=='beelink_host' else []
    return ['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
            token(policy[host]),*privilege,'python3',token(policy['remote_script'],path=True),
            mode,'--policy',token(policy['beelink_policy' if host=='beelink_host' else 'kvm_policy'],path=True),
            '--nonce',token(nonce)]


def validate_live(item,ready,nonce,challenge,serial_policy):
    expected={**ready,'kind':'live','challenge':challenge}
    if item!=expected or ready.get('kind')!='ready' or ready.get('attempt')!=ATTEMPT or ready.get('nonce')!=nonce:
        raise ValueError('Stale/malformed live controller proof')
    if ready.get('guard_sha256')!=sha(regular_bytes(__file__)) or ready.get('serial_sha256')!=sha(regular_bytes(Path(__file__).with_name('sv08_serial_boot_route.py'))):
        raise ValueError('Remote controller source differs')
    child=ready.get('child',{})
    if type(child.get('pid')) is not int or child['pid']<=1 or type(child.get('starttime')) is not int or child['starttime']<=0 or not str(child.get('exe','')).startswith('/'):
        raise ValueError('Invalid live PID/start identity')
    uart,raw=ready.get('uart',{}),ready.get('capture',{})
    if not all(type(obj.get(key)) is int for obj in (uart,raw) for key in ('fd','dev','inode','mode','rdev','uid')):
        raise ValueError('Malformed descriptor proof')
    if (any(obj['fd']<0 or obj['inode']<=0 for obj in (uart,raw)) or
            not stat.S_ISCHR(uart['mode']) or
            f"{os.major(uart['rdev'])}:{os.minor(uart['rdev'])}"!=serial_policy['dev_t'] or
            ready.get('topology')!=serial_policy['sysfs_path'] or ready.get('dev_t')!=serial_policy['dev_t'] or
            not stat.S_ISREG(raw['mode']) or raw['uid']!=0 or raw['mode']&0o077 or not raw['mode']&0o200 or raw['inode']<=0 or uart['fd']==raw['fd']):
        raise ValueError('UART/capture proof differs from admitted policy')


def primary(policy, *, apply=False, launch=subprocess.Popen):
    validate(policy)
    if not apply:
        try:source_gate(policy);mapping_ready=True
        except (ValueError,KeyError):mapping_ready=False
        return {'apply':False,'attempt':ATTEMPT,'mapping_ready':mapping_ready,'reports':[x.hex() for x in REPORTS]}
    source_gate(policy)
    # O_EXCL consumes this one controller attempt even if later readiness fails.
    out=os.open(policy['attempt_receipt'],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    children=[];events=[]
    def record(item):
        data=canonical(item)+b'\n'
        if os.write(out,data)!=len(data):raise OSError('Short guard receipt')
        os.fsync(out);events.append(item)
    nonce=os.urandom(32).hex();challenge=os.urandom(32).hex()
    try:
        record({'kind':'attempt','attempt':ATTEMPT,'nonce':nonce,'policy_sha256':sha(canonical(policy))})
        kvm=launch(ssh(policy,'kvm_host','--hid-serve',nonce),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        children.append(kvm)
        kvm_ready=channel_read(kvm.stdout)
        if kvm_ready!={'kind':'hid-ready','attempt':ATTEMPT,'nonce':nonce,'dev_t':'237:0','gadget':'Keyboard hid.usb0','guard_sha256':sha(regular_bytes(__file__))}:
            raise ValueError('KVM Keyboard readiness differs')
        controller=launch(ssh(policy,'beelink_host','--serve',nonce),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        children.append(controller)
        ready=channel_read(controller.stdout)
        # Validate the full static proof before sending the single challenge.
        validate_live({**ready,'kind':'live','challenge':challenge},ready,nonce,challenge,policy['serial_policy'])
        if controller.poll() is not None or kvm.poll() is not None:raise ValueError('Ready child exited')
        channel_write(controller.stdin,{'kind':'ack','attempt':ATTEMPT,'nonce':nonce,'challenge':challenge})
        live=channel_read(controller.stdout)
        validate_live(live,ready,nonce,challenge,policy['serial_policy'])
        # The child just revalidated PID/starttime, descriptors, UART and parent.
        if controller.poll() is not None or kvm.poll() is not None:raise ValueError('Child died at HID boundary')
        record(live)
        channel_write(kvm.stdin,{'kind':'fire','attempt':ATTEMPT,'nonce':nonce,'challenge':challenge})
        result=channel_read(kvm.stdout)
        reports=result.get('report_results',[])
        if (result.get('kind')!='hid-complete' or result.get('attempt')!=ATTEMPT or result.get('nonce')!=nonce or
                result.get('reports')!=4 or len(reports)!=4 or any(item.get('report')!=expected.hex() or item.get('written')!=8 or item.get('elapsed_seconds',-1)<0 or 'error' in item for item,expected in zip(reports,REPORTS))):
            raise ValueError('Uncertain HID result')
        record(result)
        completion=channel_read(controller.stdout,timeout=120)
        record(completion)
        if completion.get('kind')!='controller-complete':raise ValueError('Controller failed; no retry')
        return {'attempt':ATTEMPT,'events':events,'physical_return_verified':False}
    except BaseException as error:
        record({'kind':'stopped','error':type(error).__name__,'message':str(error)[:1000]})
        raise
    finally:
        for child in children:
            try:child.stdin.close()  # EOF releases child; independent supervisor restores collector.
            except OSError:pass  # Still close every other child after a broken pipe.
        os.close(out)


def collector_command(policy,nonce):
    collector=token(policy['collector_script'],path=True)
    if policy['collector_sha256']!=COLLECTOR_SHA or sha(regular_bytes(collector))!=COLLECTOR_SHA:
        raise ValueError('Receive-only collector source changed')
    # The retained receive-only collector has no command-line arguments.
    if policy.get('collector_args',[])!=[]:raise ValueError('Collector arguments are forbidden')
    retained=sum(path.stat().st_size for path in Path(collector).parent.iterdir() if path.name in ('console.raw','events.jsonl'))
    if retained>8*1024*1024:raise ValueError('Retained capture would exceed aggregate64MiB budget')
    return ['systemd-run','--unit=sv08-recovery-capture-'+nonce,'--collect',
            '--property=RuntimeMaxSec=43200','python3',collector]


def supervise(policy,pid,starttime,nonce, *, run=subprocess.run, clock=time.monotonic, pause=time.sleep):
    if type(pid) is not int or pid<=1 or type(starttime) is not int or starttime<=0:
        raise ValueError('Exact controller PID/starttime required for restoration')
    command=collector_command(policy,nonce)
    deadline=clock()+180
    while clock()<deadline:
        try:
            current=process_identity(pid)
            if current['starttime']!=starttime:break
        except (OSError,ValueError):break
        pause(.2)
    else:raise TimeoutError('Controller did not release within supervisor bound')
    # The retained collector does not share this lock. Require actual descriptor
    # release as well as exclusive-UART open, not a cooperating-lock claim.
    lock=os.open(policy['serial_policy']['ownership_lock'],os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fd=os.open(policy['serial_policy']['device'],os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK|os.O_NOFOLLOW)
        try:
            from scripts.sv08_serial_boot_route import serial_identity
            serial_identity(fd,policy['serial_policy'])
            rdev=os.fstat(fd).st_rdev
            for process in Path('/proc').iterdir():
                if not process.name.isdigit():continue
                try:descriptors=list((process/'fd').iterdir())
                except FileNotFoundError:continue
                for item in descriptors:
                    if process.name==str(os.getpid()) and item.name==str(fd):continue
                    try:info=item.stat()
                    except FileNotFoundError:continue
                    if stat.S_ISCHR(info.st_mode) and info.st_rdev==rdev:
                        raise ValueError('UART still owned; collector not recreated')
        finally:os.close(fd)  # No termios/control-line/TX; denial stops recreation.
        run(command,check=True,capture_output=True,timeout=20)
    finally:os.close(lock)


def serve(policy,nonce,policy_path, *, run=subprocess.run):
    source_gate(policy)
    if not exception_admitted(policy['serial_policy']):raise ValueError('Exception not approved')
    me=process_identity(os.getpid())
    collector_command(policy,nonce)  # Validate restoration input before UART open.
    # systemd service survives this SSH child and primary connection loss.
    run(['systemd-run','--unit=sv08-recovery-supervisor-'+nonce,'--collect',
         '--property=RuntimeMaxSec=240','python3',token(str(Path(__file__).resolve()),path=True),
         '--supervise','--policy',token(str(policy_path),path=True),'--nonce',nonce,
         '--pid',str(me['pid']),'--starttime',str(me['starttime'])],
        check=True,capture_output=True,timeout=20)
    from scripts.sv08_serial_boot_route import run as serial_run
    result=serial_run(policy['serial_policy'],'sd',policy['script'],policy['command'],
                      policy['composition'],policy['capture'],apply=True,
                      ready_hook=lambda fd,raw:readiness(fd,raw,policy['serial_policy'],nonce,sys.stdin.buffer,sys.stdout.buffer))
    channel_write(sys.stdout.buffer,{'kind':'controller-complete','result':result})


def hid_binding(fd,policy):
    info=os.fstat(fd)
    if not stat.S_ISCHR(info.st_mode) or (os.major(info.st_rdev),os.minor(info.st_rdev))!=(237,0):
        raise ValueError('Fresh HID character identity differs')
    gadget=Path('/sys/kernel/config/usb_gadget/rockchip/functions/hid.usb0')
    if sorted(x.name for x in gadget.parents[1].parent.iterdir())!=['rockchip']:
        raise ValueError('Unexpected gadget topology')
    metadata={key:(gadget/key).read_text().strip() for key in ('protocol','subclass','report_length','dev')}
    description=json.loads(Path('/run/kvmd/otg/hid.usb0@meta.json').read_text())
    if (metadata!={'protocol':'1','subclass':'1','report_length':'8','dev':'237:0'} or
            description!={'function':'hid.usb0','description':'Keyboard','endpoints':1,'order':0} or
            str(Path('/sys/dev/char/237:0').resolve())!='/sys/devices/virtual/hidg/hidg0'):
        raise ValueError('Fresh Keyboard gadget metadata differs')
    return descriptor(fd)


def hid_serve(policy,nonce):
    source_gate(policy)
    if policy['hid_device']!='/dev/hidg0':raise ValueError('Only fixed keyboard gadget admitted')
    receipt=os.open(token(policy['hid_receipt'],path=True),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    fd=None;results=[]
    def record(item):
        data=canonical(item)+b'\n'
        if os.write(receipt,data)!=len(data):raise OSError('Uncertain HID receipt write; stop')
        os.fsync(receipt)
    try:
        record({'kind':'hid-attempt','attempt':ATTEMPT,'nonce':nonce,'policy_sha256':sha(canonical(policy))})
        fd=os.open('/dev/hidg0',os.O_WRONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        parent=process_identity(os.getppid());bound=hid_binding(fd,policy)
        channel_write(sys.stdout.buffer,{'kind':'hid-ready','attempt':ATTEMPT,'nonce':nonce,'dev_t':'237:0','gadget':'Keyboard hid.usb0','guard_sha256':sha(regular_bytes(__file__))})
        message=channel_read(sys.stdin.buffer)
        if message!={'kind':'fire','attempt':ATTEMPT,'nonce':nonce,'challenge':message.get('challenge')} or not re.fullmatch(r'[0-9a-f]{64}',message.get('challenge','')):
            raise ValueError('Wrong one-attempt HID acknowledgment')
        for index,report in enumerate(REPORTS):
            parent_live(parent,sys.stdin.buffer)
            if hid_binding(fd,policy)!=bound:raise ValueError('HID identity changed')
            started=time.monotonic()
            item={'kind':'hid-report','index':index,'report':report.hex()}
            try:item['written']=os.write(fd,report)
            except OSError as error:
                item['error']=str(error)[:1000]
                item['elapsed_seconds']=time.monotonic()-started;record(item)
                raise
            item['elapsed_seconds']=time.monotonic()-started;record(item);results.append(item)
            if item['written']!=8:raise OSError('Partial HID report; stop without retry')
            if index==1:time.sleep(.2)  # VT settling only after the release; no deliberate key hold.
        channel_write(sys.stdout.buffer,{'kind':'hid-complete','attempt':ATTEMPT,'nonce':nonce,'reports':4,'report_results':results})
    finally:
        if fd is not None:os.close(fd)
        os.close(receipt)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--policy',type=Path,required=True)
    mode=p.add_mutually_exclusive_group()
    for name in ('apply','serve','hid-serve','supervise'):mode.add_argument('--'+name,action='store_true')
    p.add_argument('--nonce');p.add_argument('--pid',type=int);p.add_argument('--starttime',type=int)
    args=p.parse_args();policy=json.loads(regular_bytes(args.policy))
    if args.serve or args.hid_serve or args.supervise:
        if not re.fullmatch(r'[0-9a-f]{64}',args.nonce or ''):raise ValueError('Invalid attempt nonce')
    if args.serve:serve(policy,args.nonce,args.policy)
    elif args.hid_serve:hid_serve(policy,args.nonce)
    elif args.supervise:supervise(policy,args.pid,args.starttime,args.nonce)
    else:print(json.dumps(primary(policy,apply=args.apply),sort_keys=True,indent=2))


if __name__=='__main__':main()
