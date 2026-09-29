"""Offline guard entrypoints with fake SSH/HID and real private receipts/captures."""
import copy
from contextlib import ExitStack
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import threading
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

from scripts import sv08_recovery_boot_guard as guard

def setUpModule():
    global synthetic_amendment
    synthetic_amendment=mock.patch.object(guard,'RISK_APPROVAL','3'*64)
    synthetic_amendment.start()

def tearDownModule():
    synthetic_amendment.stop()


def exception():
    return {'format':'sv08-one-recovery-return-v1','attempt':guard.ATTEMPT,
            'approval_sha256':guard.APPROVAL,'risk_amendment_sha256':guard.RISK_APPROVAL,'operation_review_sha256':'1'*64,
            **{key:True for key in ('counters_unknown','rtc_retention_unknown',
                                   'jobs_disabled','claims_disabled','writer_markers_disabled')}}


def policy(work):
    return {'attempt':guard.ATTEMPT,'beelink_host':'root@beelink','kvm_host':'root@kvm',
            'remote_script':'/public/sv08_recovery_boot_guard.py',
            'beelink_policy':'/private/beelink.json','kvm_policy':'/private/kvm.json',
            'attempt_receipt':str(work/'attempt.jsonl'),
            'serial_policy':{'fresh_environment_reviewed':False,'dev_t':'188:0',
                'sysfs_path':'/sys/test/ch340','recovery_return_exception':exception()},
            'mapping_evidence':{**guard.SOURCE_MAPPING,
                'route':'ordered-ctrl-alt-del-target','normal_final_reboot_force':True,
                'early_force_risk_accepted':True,'risk_amendment_sha256':'3'*64,
                'event_or_reboot_count_proven':False}}


def ready(policy,nonce):
    return {'kind':'ready','attempt':guard.ATTEMPT,'nonce':nonce,
            'child':{'pid':200,'starttime':1234,'exe':'/usr/bin/python3'},
            'uart':{'fd':4,'dev':6,'inode':20,'mode':stat.S_IFCHR|0o660,'rdev':os.makedev(188,0),'uid':0},
            'capture':{'fd':5,'dev':6,'inode':21,'mode':stat.S_IFREG|0o600,'rdev':0,'uid':0},
            'topology':policy['serial_policy']['sysfs_path'],'dev_t':'188:0',
            'guard_sha256':guard.sha(guard.regular_bytes(guard.__file__)),
            'serial_sha256':guard.sha(guard.regular_bytes(Path(guard.__file__).with_name('sv08_serial_boot_route.py')))}


class Child:
    def __init__(self):self.stdin=io.BytesIO();self.stdout=io.BytesIO();self.dead=False
    def poll(self):return 1 if self.dead else None


class PrimaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name);self.policy=policy(self.work)
        self.kvm=Child();self.serial=Child();self.fault=None;self.sends=[]
        self.nonce=None;self.identity=None

    def execute(self,apply=True):
        def launch(argv,**kwargs):
            self.nonce=argv[-1]
            self.identity=ready(self.policy,self.nonce)
            return self.kvm if '--hid-serve' in argv else self.serial
        def receive(stream,**kwargs):
            if stream is self.kvm.stdout:
                if self.sends and self.sends[-1][1]['kind']=='fire':
                    if self.fault=='partial-hid':raise EOFError('Partial HID child exit')
                    return {'kind':'hid-complete','attempt':guard.ATTEMPT,'nonce':self.nonce,'reports':4,'report_results':[{'report':r.hex(),'written':8,'elapsed_seconds':.001} for r in guard.REPORTS]}
                return {'kind':'hid-ready','attempt':guard.ATTEMPT,'nonce':self.nonce,'dev_t':'237:0',
                        'gadget':'Keyboard hid.usb0','guard_sha256':self.identity['guard_sha256']}
            if not any(x[1]['kind']=='ack' for x in self.sends):
                if self.fault=='failed-ready':raise EOFError('Admission failed')
                if self.fault=='dead':self.serial.dead=True
                if self.fault=='malformed':self.identity['capture']['uid']=1000
                return self.identity
            if any(x[1]['kind']=='fire' for x in self.sends):
                if self.fault=='abnormal':raise EOFError('Controller abnormal exit')
                return {'kind':'controller-complete'}
            ack=next(x[1] for x in self.sends if x[1]['kind']=='ack')
            if self.fault=='ack-timeout':raise TimeoutError('Ack timeout')
            live={**self.identity,'kind':'live','challenge':ack['challenge']}
            if self.fault=='stale':live['nonce']='f'*64
            if self.fault=='pid-reused':live['child']={**live['child'],'starttime':999}
            if self.fault=='parent-loss':raise EOFError('SSH lost')
            if self.fault=='hid-boundary-dead':self.serial.dead=True
            return live
        def send(stream,item):self.sends.append((stream,item))
        with mock.patch.object(guard,'channel_read',side_effect=receive),mock.patch.object(guard,'channel_write',side_effect=send):
            return guard.primary(self.policy,apply=apply,launch=launch)

    def test_default_is_inert_even_with_unresolved_mapping(self):
        self.policy['mapping_evidence']['early_force_risk_accepted']=False
        result=self.execute(False)
        self.assertFalse(result['mapping_ready']);self.assertFalse(self.policy['serial_policy']['fresh_environment_reviewed'])
        self.assertEqual(self.sends,[]);self.assertFalse((self.work/'attempt.jsonl').exists())

    def test_ordered_live_ack_then_one_fire_and_receipt(self):
        result=self.execute()
        self.assertEqual([x[1]['kind'] for x in self.sends],['ack','fire'])
        self.assertEqual(self.sends[0][1]['challenge'],self.sends[1][1]['challenge'])
        self.assertFalse(result['physical_return_verified'])
        self.assertIn(b'"kind":"live"',(self.work/'attempt.jsonl').read_bytes())
        self.assertTrue(self.serial.stdin.closed);self.assertTrue(self.kvm.stdin.closed)
        with self.assertRaises(FileExistsError):self.execute()

    def test_failed_dead_stale_malformed_reused_ack_timeout_and_ssh_loss_never_fire(self):
        for fault in ('failed-ready','dead','malformed','stale','pid-reused','ack-timeout','parent-loss','hid-boundary-dead'):
            with self.subTest(fault=fault):
                self.setUp();self.fault=fault
                with self.assertRaises((ValueError,EOFError,TimeoutError)):self.execute()
                self.assertNotIn('fire',[x[1]['kind'] for x in self.sends])
                self.assertTrue(self.kvm.stdin.closed)
                self.assertIn(b'"kind":"stopped"',(self.work/'attempt.jsonl').read_bytes())

    def test_partial_hid_or_abnormal_exit_has_no_retry(self):
        for fault in ('partial-hid','abnormal'):
            self.setUp();self.fault=fault
            with self.assertRaises(EOFError):self.execute()
            self.assertEqual([x[1]['kind'] for x in self.sends].count('fire'),1)
            self.assertTrue(self.serial.stdin.closed)

    def test_no_shell_interpolation_or_fake_freshness(self):
        for field,value in (('beelink_host','root@host;reboot'),('remote_script','/tmp/$(reboot)')):
            bad=copy.deepcopy(self.policy);bad[field]=value
            with self.assertRaises(ValueError):guard.primary(bad)
        self.policy['serial_policy']['fresh_environment_reviewed']=True
        with self.assertRaises(ValueError):guard.primary(self.policy)

    def test_existing_beelink_ssh_uses_only_fixed_noninteractive_sudo(self):
        self.policy['beelink_host']='drew@beelink.drewnet.online'
        beelink=guard.ssh(self.policy,'beelink_host','--serve','a'*64)
        kvm=guard.ssh(self.policy,'kvm_host','--hid-serve','a'*64)
        self.assertEqual(beelink[6:10],['drew@beelink.drewnet.online','sudo','-n','python3'])
        self.assertEqual(kvm[6:8],['root@kvm','python3'])
        self.assertNotIn('sudo',kvm)
        self.assertIn('BatchMode=yes',beelink);self.assertIn('StrictHostKeyChecking=yes',beelink)

    def test_source_gate_blocks_apply_before_any_child(self):
        self.policy['mapping_evidence']['early_force_risk_accepted']=False
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(self.sends,[]);self.assertFalse((self.work/'attempt.jsonl').exists())


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.capture=Path(self.temp.name)/'capture';self.capture_fd=os.open(self.capture,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        self.addCleanup(os.close,self.capture_fd)
        self.device=Path(self.temp.name)/'uart-fixture';self.device.touch();self.fd=os.open(self.device,os.O_RDWR)
        self.addCleanup(os.close,self.fd)
        self.nonce='a'*64;self.policy={'sysfs_path':'fixture','dev_t':'188:0'}
        self.ack={'kind':'ack','attempt':guard.ATTEMPT,'nonce':self.nonce,'challenge':'b'*64}

    def execute(self):
        with mock.patch('scripts.sv08_serial_boot_route.serial_identity'),mock.patch.object(guard,'channel_read',return_value=self.ack),mock.patch.object(guard,'channel_write') as send:
            check=guard.readiness(self.fd,self.capture_fd,self.policy,self.nonce,io.BytesIO(),io.BytesIO())
            return check,[x.args[1] for x in send.call_args_list]

    def test_actual_pid_start_descriptor_binding_and_exact_ack(self):
        check,messages=self.execute()
        self.assertEqual(messages[0]['child'],guard.process_identity(os.getpid()))
        self.assertEqual(messages[0]['capture']['inode'],self.capture.stat().st_ino)
        self.assertEqual(messages[1]['challenge'],'b'*64)
        self.assertTrue(callable(check))

    def test_stale_or_extra_ack_refused(self):
        for ack in ({**self.ack,'nonce':'c'*64},{**self.ack,'extra':'bad'},{**self.ack,'challenge':'bad'}):
            self.ack=ack
            with self.assertRaises(ValueError):self.execute()

    def test_pid_reuse_detection(self):
        actual=guard.process_identity(os.getpid())
        with self.assertRaises(ValueError):guard.live_process({**actual,'starttime':actual['starttime']+1})

    def test_channel_eof_and_timeout_stop(self):
        read,write=os.pipe()
        with os.fdopen(read,'rb',buffering=0) as stream:
            with self.assertRaises(TimeoutError):guard.channel_read(stream,timeout=.01)
            os.close(write)
            with self.assertRaises(EOFError):guard.channel_read(stream,timeout=.01)


class SupervisorTests(unittest.TestCase):
    def test_actual_supervisor_recreates_after_exit_and_exclusive_release(self):
        with tempfile.TemporaryDirectory() as work:
            work=Path(work);uart=work/'uart';uart.touch()
            p={'serial_policy':{'ownership_lock':str(work/'lock'),'device':str(uart)}}
            command=['systemd-run','--unit=fixed','--collect','--property=RuntimeMaxSec=43200','python3','/pinned/capture.py']
            with mock.patch.object(guard,'collector_command',return_value=command),mock.patch.object(guard,'process_identity',side_effect=FileNotFoundError),mock.patch('scripts.sv08_serial_boot_route.serial_identity'),mock.patch.object(guard,'Path',side_effect=lambda x:work if str(x)=='/proc' else Path(x)):
                runner=mock.Mock();guard.supervise(p,123,456,'a'*64,run=runner)
                self.assertEqual(runner.call_args.args[0],command)

    def test_uart_exclusion_failure_never_recreates(self):
        with tempfile.TemporaryDirectory() as work:
            p={'serial_policy':{'ownership_lock':work+'/lock','device':work+'/absent'}}
            runner=mock.Mock()
            with mock.patch.object(guard,'collector_command',return_value=['systemd-run']),mock.patch.object(guard,'process_identity',side_effect=FileNotFoundError):
                with self.assertRaises(FileNotFoundError):guard.supervise(p,123,456,'a'*64,run=runner)
            runner.assert_not_called()

    def test_serve_starts_independent_supervisor_before_serial_callback(self):
        with tempfile.TemporaryDirectory() as work:
            p=policy(Path(work));p.update(script='s',command='c',composition='j',capture='raw')
            events=[]
            def run(argv,**kwargs):events.append(('supervisor',argv))
            def serial(*args,**kwargs):
                events.append(('serial',kwargs));raise ValueError('Fixture readiness refusal')
            with mock.patch.object(guard,'collector_command',return_value=['fixed']),mock.patch('scripts.sv08_serial_boot_route.run',side_effect=serial):
                with self.assertRaises(ValueError):guard.serve(p,'a'*64,'/private/policy.json',run=run)
            self.assertEqual([x[0] for x in events],['supervisor','serial'])
            self.assertIn('--supervise',events[0][1]);self.assertIn('ready_hook',events[1][1])


    def test_supervisor_observes_real_controller_exit_after_channel_loss(self):
        with tempfile.TemporaryDirectory() as work:
            work=Path(work);uart=work/'uart';uart.touch()
            p={'serial_policy':{'ownership_lock':str(work/'lock'),'device':str(uart)}}
            child=subprocess.Popen([sys.executable,'-c','import sys; sys.stdin.buffer.read()'],stdin=subprocess.PIPE)
            try:
                identity=guard.process_identity(child.pid)
                closer=threading.Timer(.1,child.stdin.close);closer.start()
                def restore(command,**kwargs):
                    child.wait(timeout=2)
                    self.assertIsNotNone(child.poll())
                with mock.patch.object(guard,'collector_command',return_value=['systemd-run','--collect']),mock.patch('scripts.sv08_serial_boot_route.serial_identity'),mock.patch.object(guard,'Path',side_effect=lambda x:work if str(x)=='/proc' else Path(x)):
                    guard.supervise(p,child.pid,identity['starttime'],'a'*64,run=restore)
                closer.join()
            finally:
                if child.poll() is None:child.terminate()
                child.wait(timeout=2)

    def test_pinned_collector_recreation_has_no_args_and_respects_budget(self):
        with tempfile.TemporaryDirectory() as work:
            work=Path(work);source=work/'capture.py';source.write_text('# public readonly fixture\n')
            expected=guard.sha(source.read_bytes())
            p={'collector_script':str(source),'collector_sha256':expected,'collector_args':[]}
            with mock.patch.object(guard,'COLLECTOR_SHA',expected):
                command=guard.collector_command(p,'a'*64)
                self.assertEqual(command[-2:],['python3',str(source)])
                self.assertIn('--collect',command)
                self.assertIn('--property=LimitFSIZE=4194304',command)
                self.assertIn('--property=Restart=no',command)
                p['collector_args']=['/arbitrary']
                with self.assertRaises(ValueError):guard.collector_command(p,'a'*64)
                p['collector_args']=[]
                with (work/'console.raw').open('wb') as raw:raw.truncate(9*1024*1024)
                with self.assertRaises(ValueError):guard.collector_command(p,'a'*64)
            with self.assertRaises(ValueError):guard.collector_command(p,'a'*64)


    def test_each_retained_collector_file_must_be_strictly_below_absolute_limit(self):
        with tempfile.TemporaryDirectory() as work:
            work=Path(work);source=work/'capture.py';source.write_text('# readonly fixture\n')
            expected=guard.sha(source.read_bytes())
            p={'collector_script':str(source),'collector_sha256':expected}
            with mock.patch.object(guard,'COLLECTOR_SHA',expected):
                for name in ('console.raw','events.jsonl'):
                    with self.subTest(name=name):
                        retained=work/name
                        with retained.open('wb') as stream:stream.truncate(4194303)
                        guard.collector_command(p,'a'*64)
                        with retained.open('r+b') as stream:stream.truncate(4194304)
                        with self.assertRaises(ValueError):guard.collector_command(p,'a'*64)
                        self.assertEqual(retained.stat().st_size,4194304)
                        retained.unlink()


class HIDTests(unittest.TestCase):
    def test_actual_emitter_four_fixed_reports_or_partial_stop(self):
        for fail_at in (None,0,2):
            with tempfile.TemporaryDirectory() as work:
                work=Path(work);p=policy(work);p['hid_device']='/dev/hidg0';p['hid_receipt']=str(work/'hid-receipt.jsonl')
                hid=work/'hid';hid.touch();real_open=os.open;real_write=os.write
                writes=[];hid_fd=[None]
                def open_fd(path,*args):
                    fd=real_open(hid if path=='/dev/hidg0' else path,*args)
                    if path=='/dev/hidg0':hid_fd[0]=fd
                    return fd
                def write(fd,data):
                    if fd!=hid_fd[0]:return real_write(fd,data)
                    writes.append(data);return 3 if len(writes)-1==fail_at else len(data)
                with ExitStack() as stack:
                    for patcher in (mock.patch.object(guard.os,'open',side_effect=open_fd),mock.patch.object(guard.os,'write',side_effect=write),
                        mock.patch.object(guard,'hid_binding',return_value={'identity':'fixture'}),mock.patch.object(guard,'parent_live'),
                        mock.patch.object(guard,'channel_write'),mock.patch.object(guard,'channel_read',return_value={'kind':'fire','attempt':guard.ATTEMPT,'nonce':'a'*64,'challenge':'b'*64}),mock.patch.object(guard.time,'sleep')):
                        stack.enter_context(patcher)
                    if fail_at is None:guard.hid_serve(p,'a'*64)
                    else:
                        with self.assertRaises(OSError):guard.hid_serve(p,'a'*64)
                self.assertEqual(writes,list(guard.REPORTS[:4 if fail_at is None else fail_at+1]))
                entries=[json.loads(line) for line in Path(p['hid_receipt']).read_text().splitlines()]
                reports=[item for item in entries if item['kind']=='hid-report']
                self.assertEqual(len(reports),len(writes))
                self.assertTrue(all(item['elapsed_seconds']>=0 for item in reports))
                if fail_at is not None:self.assertEqual(reports[-1]['written'],3)

    def test_parent_loss_before_report_sends_nothing(self):
        with tempfile.TemporaryDirectory() as work:
            p=policy(Path(work));p['hid_device']='/dev/hidg0';p['hid_receipt']=str(Path(work)/'hid-receipt.jsonl');hid=Path(work)/'hid';hid.touch();real_open=os.open
            with mock.patch.object(guard.os,'open',side_effect=lambda path,*args:real_open(hid if path=='/dev/hidg0' else path,*args)),mock.patch.object(guard,'hid_binding',return_value={}),mock.patch.object(guard,'parent_live',side_effect=EOFError),mock.patch.object(guard,'channel_write'),mock.patch.object(guard,'channel_read',return_value={'kind':'fire','attempt':guard.ATTEMPT,'nonce':'a'*64,'challenge':'b'*64}),mock.patch.object(guard.os,'write',wraps=os.write) as write:
                with self.assertRaises(EOFError):guard.hid_serve(p,'a'*64)
                self.assertTrue(all(len(call.args[1])!=8 for call in write.call_args_list))


class HIDBindingTests(unittest.TestCase):
    def test_actual_fresh_metadata_checks_reject_device_and_metadata_drift(self):
        with tempfile.TemporaryDirectory() as work:
            work=Path(work);gadget=work/'usb_gadget/rockchip/functions/hid.usb0';gadget.mkdir(parents=True)
            for key,value in {'protocol':'1','subclass':'1','report_length':'8','dev':'237:0'}.items():(gadget/key).write_text(value)
            metadata=work/'meta.json';metadata.write_text(json.dumps({'function':'hid.usb0','description':'Keyboard','endpoints':1,'order':0}))
            sysdev=work/'sysdev';target=work/'hidg0';target.touch();sysdev.symlink_to(target)
            actual_path=Path
            def paths(value):
                return {'/sys/kernel/config/usb_gadget/rockchip/functions/hid.usb0':gadget,
                        '/run/kvmd/otg/hid.usb0@meta.json':metadata,
                        '/sys/dev/char/237:0':sysdev}.get(str(value),actual_path(value))
            info=SimpleNamespace(st_mode=stat.S_IFCHR|0o600,st_rdev=os.makedev(237,0))
            with mock.patch.object(guard,'Path',side_effect=paths),mock.patch.object(guard.os,'fstat',return_value=info):
                # The exact resolved topology is part of the production gate.
                with self.assertRaises(ValueError):guard.hid_binding(10,{})
                with mock.patch.object(Path,'resolve',return_value=Path('/sys/devices/virtual/hidg/hidg0')),mock.patch.object(guard,'descriptor',return_value={'fixture':True}):
                    self.assertEqual(guard.hid_binding(10,{}),{'fixture':True})
                    (gadget/'protocol').write_text('0')
                    with self.assertRaises(ValueError):guard.hid_binding(10,{})
                    (gadget/'protocol').write_text('1');metadata.write_text('{}')
                    with self.assertRaises(ValueError):guard.hid_binding(10,{})
                info.st_rdev=os.makedev(237,1)
                with self.assertRaises(ValueError):guard.hid_binding(10,{})




class ActualCollectorLimitTests(unittest.TestCase):
    def test_unchanged_collector_tiny_reads_exhaust_events_limit_and_release_uart(self):
        source=Path('/home/drew/sv08-mainline/local/sd-recovery-host/collector-source.py')
        if not source.exists():self.skipTest('Explicitly supplied public collector source absent')
        data=source.read_bytes()
        self.assertEqual(guard.sha(data),guard.COLLECTOR_SHA)
        with tempfile.TemporaryDirectory() as work:
            work=Path(work);collector=work/'capture.py';collector.write_bytes(data)
            uart=work/'uart';uart.write_bytes(b'fixture')
            device=work/'device';device.mkdir()
            (device/'idVendor').write_text('1a86');(device/'idProduct').write_text('7523')
            (work/'events.jsonl').write_bytes(b'retained-prefix\n')
            wrapper=work/'fixture.py'
            wrapper.write_text(r"""
import errno, fcntl, json, os, pathlib, resource, runpy, select, sys, termios, types
base=pathlib.Path(sys.argv[1]);real_path=pathlib.Path
real_open,real_close,real_read,real_write=os.open,os.close,os.read,os.write
uart_fd=None;opened_flags=[];reads=0;transmits=0
# Only hardware interfaces are fixtures. Collector filesystem I/O, event logging,
# control flow, exceptions and Linux's regular-file resource limit are real.
def hardware_path(value):
    if str(value)=='/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0':return base/'uart'
    if str(value)=='/sys/class/tty':return base/'sys-class'
    return real_path(value)
(base/'sys-class'/'uart').mkdir(parents=True)
(base/'sys-class'/'uart'/'device').symlink_to(base/'device')
fake_pathlib=types.ModuleType('pathlib');fake_pathlib.Path=hardware_path
sys.modules['pathlib']=fake_pathlib
def opens(path,flags,*args):
    global uart_fd
    fd=real_open(path,flags,*args)
    if real_path(path)==base/'uart':
        if flags & os.O_ACCMODE!=os.O_RDONLY:raise AssertionError('Non-readonly UART open')
        uart_fd=fd;opened_flags.append(flags)
    return fd
def reads_from_uart(fd,count):
    global reads
    if fd==uart_fd:reads+=1;return b'x'
    return real_read(fd,count)
def writes(fd,data):
    global transmits
    if fd==uart_fd:transmits+=1;raise AssertionError('UART TX forbidden')
    return real_write(fd,data)
os.open=opens;os.read=reads_from_uart;os.write=writes
fcntl.ioctl=lambda *args:0
select.select=lambda readers,*args:(readers,[],[])
termios.tcgetattr=lambda fd:[0,0,0,0,0,0,[0]*32]
termios.tcsetattr=lambda *args:None
resource.setrlimit(resource.RLIMIT_FSIZE,(4096,4096))
try:runpy.run_path(str(base/'capture.py'),run_name='__main__')
finally:
    try:os.fstat(uart_fd);released=False
    except OSError as error:released=error.errno==errno.EBADF
    print(json.dumps(dict(reads=reads,transmits=transmits,released=released,opens=len(opened_flags))),flush=True)
""")
            result=subprocess.run([sys.executable,str(wrapper),str(work)],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0)
            proof=json.loads(result.stdout.strip())
            self.assertTrue(proof['released']);self.assertEqual(proof['transmits'],0);self.assertEqual(proof['opens'],1)
            self.assertGreater(proof['reads'],0)
            self.assertLess((work/'console.raw').stat().st_size,4096)
            self.assertEqual((work/'events.jsonl').stat().st_size,4096)
            self.assertTrue((work/'events.jsonl').read_bytes().startswith(b'retained-prefix\n'))
            self.assertIn('File too large',result.stderr)
            self.assertEqual(collector.read_bytes(),data)



if __name__=='__main__':unittest.main()
