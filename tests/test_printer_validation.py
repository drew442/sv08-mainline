"""Deterministic deadlines, private telemetry and single-owner cleanup; no Klipper."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contextlib import ExitStack
import sv08_printer_publish as publish


class Clock:
    def __init__(self):self.now=0
    def monotonic(self):return self.now
    def sleep(self,seconds):self.now+=seconds


class Child:
    pid=987654321
    def __init__(self,timeout=False,stopped=None):
        self.returncode=stopped;self.timeout=timeout;self.signals=[]
    def poll(self):return self.returncode
    def terminate(self):self.signals.append('TERM')
    def kill(self):self.signals.append('KILL');self.returncode=-9
    def wait(self,timeout=None):
        if self.timeout and timeout is not None:raise subprocess.TimeoutExpired('fixture',timeout)
        if self.returncode is None:self.returncode=-15
        return self.returncode


class API:
    def __init__(self,clock,chunks,advances,connect_advance=0,send_advance=0):self.clock=clock;self.chunks=iter(chunks);self.advances=iter(advances);self.timeouts=[];self.operations=[];self.connect_advance=connect_advance;self.send_advance=send_advance
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def settimeout(self,value):self.timeouts.append(value)
    def connect(self,path):self.operations.append('connect');self.clock.now+=self.connect_advance
    def sendall(self,data):self.operations.append('send');self.assertion=data.endswith(b'\x03');self.clock.now+=self.send_advance
    def recv(self,size):self.operations.append('recv');self.clock.now+=next(self.advances);return next(self.chunks)


class ValidatorTests(unittest.TestCase):
    def run_validator(self,chunks=(),advances=(),stopped=None,timeout=False,private=False,api=True,connect_advance=0,send_advance=0,broken_sink=False,missing_progress=False):
        with tempfile.TemporaryDirectory() as root,ExitStack() as patches:
            root=Path(root);dictionary=root/'dict';dictionary.write_bytes(b'dictionary');python=root/'python';python.touch();klippy=root/'klippy';klippy.write_bytes(b'entry')
            config=root/'config';config.mkdir();preview=publish.Publisher(config).preview({'hardware.cfg':'[printer]\nkinematics: none\n'}, {},'test')
            clock=Clock();child=Child(timeout,stopped);sock=API(clock,chunks,advances,connect_advance,send_advance);captures=[];scratch=[]
            original_sha=publish.sha
            def sha(raw):
                if raw==b'dictionary':return '86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b'
                if raw==b'entry':return 'aa9eb47fbe3598fc814d40ed8e0b2b814a0af459fca7acab6732c59bf42e4659'
                return original_sha(raw)
            def popen(args,**kwargs):
                self.args=args;work=Path(args[args.index('-a')+1]).parent;scratch.append(work)
                if api:(work/'api').touch()
                (work/'klippy.log').write_text('PRIVATE CONFIG SECRET\n'+'x'*10000)
                (work/'stdout.log').write_text('PRIVATE STDOUT SECRET')
                self.assertTrue(kwargs['start_new_session']);return child
            original_read=Path.read_text;child.progress_reads=[]
            def read(path,*args,**kwargs):
                if path.parent==Path('/proc')/str(child.pid) and path.name in ('stat','wchan','io'):
                    child.progress_reads.append(path.name)
                    if missing_progress:raise FileNotFoundError('fixture /proc unavailable')
                    if path.name=='stat':return str(child.pid)+' (comm with ) spaces) D '+' '.join(['0']*10)+ ' 123 45 0\n'
                    if path.name=='wchan':return 'wait_on_page_bit_common\n'
                    return 'rchar: 900\nsyscr: 20\nread_bytes: 4096\n'
                if path==Path('/proc')/str(child.pid)/'limits':return 'Max cpu time              8                    8                    seconds\nMax address space         268435456            268435456            bytes\nMax file size             4194304              4194304              bytes\n'
                if path==Path('/proc')/str(child.pid)/'status':return 'VmSize:\t12000 kB\nVmPeak:\t14000 kB\nVmRSS:\t3000 kB\n'
                if path==Path('/proc')/str(child.pid)/'cgroup':return '0::/sv08-isolated-fixture\n'
                if str(path).startswith('/sys/fs/cgroup/sv08-isolated-fixture/'):
                    return 'oom 0\noom_kill '+str(int(child.returncode is not None))+'\n'
                return original_read(path,*args,**kwargs)
            for target,value in (('sv08_printer_publish.sha',sha),('subprocess.Popen',popen),('time.monotonic',clock.monotonic),('time.sleep',clock.sleep),('socket.socket',lambda *args:sock),('pathlib.Path.read_text',read)):
                patches.enter_context(patch(target,value))
            def sink(row):
                if broken_sink:raise RuntimeError('private callback failure')
                captures.append(row)
            result=None;error=None
            try:result=publish.validate_output(preview,config,str(python),str(klippy),str(dictionary),private_diagnostics=sink if private else None,isolated_children=private)
            except ValueError as failure:error=str(failure)
            self.assertTrue(scratch and not scratch[0].exists());self.assertIsNotNone(child.returncode)
            self.assertIn('--as=268435456',self.args);self.assertIn('--cpu=8',self.args);self.assertIn('--fsize=4194304',self.args)
            return result,error,child,sock,captures,clock
    def test_fragmented_ready_each_receive_uses_remaining_deadline(self):
        result,error,child,sock,_,clock=self.run_validator([b'{"result":',b'{"state":"ready"}}\x03'],[9.6,.1])
        self.assertTrue(result['validated']);self.assertIsNone(error);self.assertEqual(child.signals,['TERM'])
        self.assertAlmostEqual(sock.timeouts[-1],.4);self.assertEqual(sock.operations,['connect','send','recv','recv'])
    def test_connect_and_send_recheck_budget_before_following_operation(self):
        _,error,child,sock,_,_=self.run_validator(connect_advance=10)
        self.assertIn('within budget',error);self.assertEqual(sock.operations,['connect']);self.assertEqual(child.signals,['TERM'])
        _,error,child,sock,_,_=self.run_validator(connect_advance=9.8,send_advance=.3)
        self.assertIn('within budget',error);self.assertEqual(sock.operations,['connect','send']);self.assertAlmostEqual(sock.timeouts[-1],.2)
    def test_broken_private_sink_preserves_failure_and_cleanup(self):
        _,error,child,_,captures,_=self.run_validator(stopped=-9,private=True,broken_sink=True)
        self.assertIn('stopped before ready (-9)',error);self.assertEqual(child.returncode,-9);self.assertEqual(captures,[])

    def test_late_ready_refused_and_cleanup_kills_if_term_does_not_exit(self):
        result,error,child,sock,captures,_=self.run_validator([b'{"result":{"state":"ready"}}\x03'],[10.01],timeout=True,private=True)
        self.assertIsNone(result);self.assertIn('within budget',error);self.assertEqual(child.signals,['TERM','KILL'])
        row=captures[0];self.assertEqual(row['last_state'],'ready');self.assertIsNone(row['returncode_before_cleanup']);self.assertEqual(row['returncode_after_cleanup'],-9)
        self.assertTrue(row['socket_observed']);self.assertEqual(row['cleanup_signals'],child.signals)
        self.assertEqual(row['pid'],child.pid);self.assertIn('268435456',row['effective_limits']);self.assertEqual(row['vm_kib']['VmPeak'],14000)
        self.assertEqual(row['cgroup']['delta']['memory.events']['oom_kill'],1)
        self.assertIn('isolated_child_cpu_seconds',row);self.assertLessEqual(len(row['private_log_excerpts']['klippy.log']),8192)
    def test_timeout_without_socket_remains_bounded_and_private(self):
        result,error,child,_,captures,clock=self.run_validator(private=True,api=False)
        self.assertIsNone(result);self.assertIn('within budget',error);self.assertLessEqual(clock.now,10)
        self.assertFalse(captures[0]['socket_observed']);self.assertEqual(child.signals,['TERM'])
        self.assertIn('PRIVATE STDOUT SECRET',captures[0]['private_log_excerpts']['stdout.log']);self.assertNotIn('PRIVATE',error)
    def test_progress_samples_are_bounded_private_and_preserve_timeout(self):
        _,error,child,_,captures,clock=self.run_validator(private=True,api=False)
        progress=captures[0]['progress_samples'];self.assertLessEqual(len(progress),32);self.assertGreater(len(progress),20)
        self.assertEqual(progress[0]['guest_elapsed'],0);self.assertEqual(progress[-1]['guest_elapsed'],clock.now)
        self.assertTrue(all(row['child_state']=='D' and row['kernel_accounted_cpu_ticks']=={'user':123,'system':45} for row in progress))
        self.assertEqual(progress[-1]['wchan'],'wait_on_page_bit_common');self.assertEqual(progress[-1]['io']['read_bytes'],4096)
        self.assertEqual(len(child.progress_reads),3*len(progress));self.assertIn('within budget',error);self.assertEqual(child.signals,['TERM'])
        _,default_error,default_child,_,default_captures,default_clock=self.run_validator(api=False)
        self.assertEqual(default_child.progress_reads,[]);self.assertEqual(default_captures,[]);self.assertEqual(default_error,error);self.assertEqual(default_clock.now,clock.now)
    def test_missing_progress_proc_files_remain_unknown(self):
        _,error,child,_,captures,_=self.run_validator(private=True,stopped=-9,missing_progress=True)
        self.assertIn('stopped before ready (-9)',error);self.assertEqual(child.signals,[])
        for row in captures[0]['progress_samples']:
            for field in ('child_state','kernel_accounted_cpu_ticks','wchan','io'):self.assertIsNone(row[field])

    def test_deadline_between_fragments_stops_before_next_receive(self):
        result,error,child,sock,_,_=self.run_validator([b'{"result":'],[10])
        self.assertIsNone(result);self.assertIn('within budget',error);self.assertEqual(sock.operations.count('recv'),1)
    def test_stopped_process_never_discloses_default_logs(self):
        result,error,child,_,captures,_=self.run_validator(stopped=-9,private=True)
        self.assertIsNone(result);self.assertNotIn('PRIVATE',error);self.assertEqual(captures[0]['returncode_before_cleanup'],-9);self.assertEqual(child.signals,[])
        _,default_error,_,_,default_captures,_=self.run_validator(stopped=-9)
        self.assertEqual(default_captures,[]);self.assertEqual(error,default_error)
    def test_error_shutdown_refused_without_state_message_leakage(self):
        for state in ('error','shutdown'):
            with self.subTest(state=state):
                result,error,child,_,captures,_=self.run_validator([json.dumps({'result':{'state':state,'state_message':'PRIVATE CONFIG SECRET'}}).encode()+b'\x03'],[0],private=True)
                self.assertIsNone(result);self.assertNotIn('PRIVATE',error);self.assertEqual(captures[0]['last_state'],state);self.assertEqual(child.signals,['TERM'])

class ProbeTests(unittest.TestCase):
    def test_source_bound_probe_invokes_real_route_once_and_retains_failure(self):
        import printer_validator_probe as probe
        import recovery_restore_stack as guest
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory,ExitStack() as patches:
            parent=Path(directory);parent.chmod(0o700);source=parent/'source';source.mkdir(mode=0o700)
            for name in ('printer_validator_probe.py','sv08_printer_publish.py','recovery_restore_stack.py'):
                (source/name).write_text('# staged current source\n');(source/name).chmod(0o600)
            marker=parent/'marker';marker.write_text(guest.MARKER);marker.chmod(0o600)
            work=parent/'probe';original_stat=Path.stat
            def root_stat(path,*args,**kwargs):
                actual=original_stat(path,*args,**kwargs)
                return SimpleNamespace(st_uid=0,st_mode=actual.st_mode)
            for target,value in (('printer_validator_probe.SOURCE',source),('printer_validator_probe.sha',lambda path:'a'*64),
                                 ('sv08_printer_publish.__file__',str(source/'sv08_printer_publish.py')),
                                 ('os.geteuid',lambda:0),('platform.machine',lambda:'aarch64'),('platform.system',lambda:'Linux')):
                patches.enter_context(patch(target,value))
            # Only stat ownership is synthetic; preview/generation/closure uses
            # real local factory inputs and the production Publisher.
            patches.enter_context(patch('pathlib.Path.stat',root_stat))
            patches.enter_context(patch.object(probe,'factory',side_effect=lambda path,name:guest.factory(Path(__file__).resolve().parents[1]/'catalog/printer/catalog.json',name)))
            def failure(preview,config,**kwargs):
                self.assertEqual(set(preview['files']),{'hardware.cfg'});self.assertIn('sv08-stack-restored-main',preview['files']['hardware.cfg'])
                self.assertTrue(kwargs['isolated_children']);kwargs['private_diagnostics']({'private_log_excerpts':{'klippy.log':'PRIVATE'}})
                raise ValueError('Complete-output validation process stopped before ready (-9)')
            with patch.object(probe,'validate_output',side_effect=failure) as validate:
                self.assertFalse(probe.probe(work,marker));validate.assert_called_once()
            receipt=json.loads((work/'probe-private.json').read_text())
            self.assertEqual(receipt['result'],'FAIL');self.assertIn('(-9)',receipt['failure_private']);self.assertEqual(receipt['diagnostics_private'][0]['private_log_excerpts']['klippy.log'],'PRIVATE')
            self.assertEqual((work/'probe-private.json').stat().st_mode & 0o777,0o600)
            self.assertEqual(len(receipt['validator_input_sha256']),3);self.assertFalse(receipt['physical_hardware'])
            with patch.object(probe,'validate_output') as validate:
                with self.assertRaisesRegex(ValueError,'Fresh work'):probe.probe(work,marker)
                validate.assert_not_called()

if __name__=='__main__':unittest.main()
