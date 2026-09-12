import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_admin import Controller
from sv08_admin_images import HostImages
from sv08_admin_jobs import Jobs
from sv08_admin_upload import Uploads, Transport
from sv08_bundle import manifest_output
from sv08_staging import Staging
from sv08_state import Store
from sv08_transaction import Transaction
from test_transaction import Backend, admitted


class UploadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=Path.home(),prefix='.sv08-upload-'); self.addCleanup(temp.cleanup)
        self.root=Path(temp.name); self.store=Store(self.root/'state',reserve_bytes=0); self.store.initialize()
        self.boot=self.store.prepare_boot('A','release-1'); self.boot['boot_id']='boot-1'
        self.stage=self.root/'uploads'; self.stage.mkdir(mode=0o700)
        self.staging=Staging(self.stage,max_bytes=1024*1024,reserve_bytes=0,owner_uid=os.getuid())
        self.jobs=Jobs(self.root/'jobs','boot-1',launcher=lambda identity:None)
        self.backend=Backend(); self.backend.manifest={'deployable':True}
        self.backend.cleanup_observation=lambda boot,lease:dict(primary=self.backend.primary(),good=dict(self.backend.states))
        self.verify=lambda p:dict(bundle_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),release='release-2',full_payload_verified=False)
        self.adapter=HostImages(self.store,self.boot,self.backend,self.staging,admitted,self.verify)
        self.c=Controller(self.store,self.boot,adapter=self.adapter,jobs=self.jobs)
        key=self.root/'key'; key.write_text('transport-only test verifier')
        self.u=Uploads(self.c,self.staging,{},key,self.verify); self.c.uploads=self.u
        self.data=b'fixture'*100; self.digest=hashlib.sha256(self.data).hexdigest()

    def receive(self):
        return self.u.receive(self.u.plan('local display.raucb',len(self.data)),io.BytesIO(self.data))

    def test_receive_lists_truthful_scope_and_exact_cleanup(self):
        before=self.store.load(); result=self.receive()
        self.assertFalse(result['proof']['full_payload_verified']); self.assertEqual(before,self.store.load())
        listed=self.u.listing(); self.assertFalse(listed['busy']); self.assertEqual(len(listed['objects']),1)
        plan=self.u.cleanup_plan(result['name']); self.assertTrue((self.stage/result['name']).exists()) # review/cancel does nothing
        self.u.cleanup(plan); self.receive()

    def test_stale_replaced_symlink_hardlink_and_unmanaged_cleanup(self):
        name=self.receive()['name']; plan=self.u.cleanup_plan(name); path=self.stage/name
        path.chmod(0o600); path.write_bytes(b'replaced'); path.chmod(0o400)
        with self.assertRaisesRegex(ValueError,'changed'):self.u.cleanup(plan)
        plan=self.u.cleanup_plan(name); os.link(path,self.stage/'alias')
        with self.assertRaisesRegex(ValueError,'linked'):self.u.cleanup(plan)
        (self.stage/'alias').unlink(); path.unlink(); path.symlink_to(self.root/'key')
        with self.assertRaisesRegex(ValueError,'linked'):self.u.cleanup(plan)
        for name in ('../key','.lock','no.raucb'):
            with self.assertRaises(ValueError):self.u.cleanup_plan(name)

    def test_existing_partial_preserved_and_explicit_cleanup(self):
        path=self.stage/('.partial-'+'a'*32);path.write_bytes(b'partial');path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'existing'):self.u.plan('x',100)
        self.assertIn('interrupted',self.u.listing()['objects'][0]['state'])
        self.u.cleanup(self.u.cleanup_plan(path.name));self.receive()

    def test_stale_policy_state_and_metadata(self):
        plan=self.u.plan('x',700);self.store.policy(auto_update=False)
        with self.assertRaisesRegex(ValueError,'changed'):self.u.receive(plan,io.BytesIO(self.data))
        for name,size in [('x'*241,1),('x\n',1),('x',True),('x',0),('x',1024*1024+1)]:
            with self.assertRaises(ValueError):self.u.plan(name,size)
        plan=self.u.plan('x',700);plan['policy']='0'*64
        with self.assertRaisesRegex(ValueError,'changed'):self.u.receive(plan,io.BytesIO(self.data))

    def test_missing_damaged_state_never_initializes(self):
        (self.store.root/'state.json').unlink()
        with self.assertRaisesRegex(ValueError,'unavailable'):self.u.plan('x',1)
        self.assertFalse(self.jobs.root.exists())
        (self.store.root/'state.json').write_text('{bad')
        with self.assertRaises(ValueError):self.u.plan('x',1)
        self.assertFalse(self.jobs.root.exists())

    def test_paused_transfer_status_policy_history_and_three_races(self):
        review=self.u.plan('x',len(self.data)); image=self.c.plan('image.stage',{'digest':self.digest})
        entered=threading.Event(); release=threading.Event(); errors=[]
        class Paused(io.BytesIO):
            def read(inner,n):
                entered.set();release.wait(5);return super().read(n)
        def receive():
            try:self.u.receive(review,Paused(self.data))
            except Exception as error:errors.append(error)
        thread=threading.Thread(target=receive);thread.start();self.assertTrue(entered.wait(2))
        try:
            start=time.monotonic();self.assertTrue(self.u.listing()['busy'])
            self.assertFalse(self.c.status()['capabilities']['image.stage']['available'])
            self.assertEqual(self.jobs.history()['jobs'],[])
            self.c.apply(self.c.plan('policy.auto',{'enabled':False}))
            self.assertLess(time.monotonic()-start,1)
            with self.assertRaises(BlockingIOError):self.u.plan('second',1)
            with self.assertRaises(BlockingIOError):self.u.cleanup_plan('.partial-'+'a'*32)
            with self.assertRaisesRegex(ValueError,'lease'):self.jobs.submit('a'*32,image,self.c)
            with self.assertRaisesRegex(ValueError,'lease'):self.c.plan('image.stage',{'digest':self.digest})
            self.assertEqual(self.jobs.history()['jobs'],[])
        finally:release.set();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[]);self.assertEqual(self.backend.calls,[])

    def test_job_admission_first_blocks_upload_queued_running_interrupted(self):
        plan=self.c.plan('image.stage',{'digest':self.digest});self.jobs.submit('a'*32,plan,self.c)
        for phase in ('queued','running','interrupted'):
            with self.jobs.lock('ledger.lock'):
                rows=self.jobs.load();rows[0]['phase']=phase;self.jobs.save(rows)
            with self.assertRaisesRegex(ValueError,'job'):self.u.plan('x',1)
            self.assertEqual(list(self.stage.glob('*.raucb')),[])

    def terminal_cleanup(self, completion):
        result=self.receive();p=self.c.plan('image.stage',{'digest':self.digest})
        identity='a'*32
        self.jobs.submit(identity,p,self.c);self.jobs.work(lambda:self.c,identity)
        self.assertEqual(self.jobs.load()[0]['phase'],'succeeded')
        tx=Transaction(self.store,self.backend,admitted)
        if completion:
            tx.arm(self.boot)
            boot=self.store.prepare_boot('B','release-2');boot['boot_id']='boot-2'
            tx.confirm(boot,lambda boot:True);self.c.boot=boot;self.adapter.boot=boot
        else:tx.cancel(self.boot)
        history=self.jobs.load();journal=tx.path.read_bytes()
        self.u.cleanup(self.u.cleanup_plan(result['name']))
        self.assertEqual(history,self.jobs.load());self.assertEqual(journal,tx.path.read_bytes())
        self.data=b'distinct subsequent release fixture'; self.digest=hashlib.sha256(self.data).hexdigest()
        self.verify=lambda p:dict(bundle_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),release='release-3',full_payload_verified=False)
        self.u.verify=self.verify;self.adapter.verify=self.verify
        again=self.receive();self.assertNotEqual(again['name'],result['name'])
        second=self.c.plan('image.stage',{'digest':self.digest})
        self.jobs.boot_id=self.c.boot['boot_id']
        self.jobs.submit('b'*32,second,self.c);self.jobs.work(lambda:self.c,'b'*32)
        self.assertEqual(self.jobs.load()[-1]['phase'],'succeeded')
        tx.cancel(self.c.boot)
        self.u.cleanup(self.u.cleanup_plan(again['name']))
        self.assertEqual(len(self.jobs.load()),2)

    def test_complete_cleanup_allows_second_upload(self):self.terminal_cleanup(True)
    def test_cancelled_cleanup_allows_second_upload(self):self.terminal_cleanup(False)

    def test_terminal_mismatch_and_failed_journal_preserved(self):
        result=self.receive();self.c.apply(self.c.plan('image.stage',{'digest':self.digest}))
        tx=Transaction(self.store,self.backend,admitted);tx.cancel(self.boot)
        self.backend.states['B']=True
        with self.assertRaisesRegex(ValueError,'disagree'):self.u.cleanup_plan(result['name'])
        self.backend.states['B']=False;tx.save(tx.load(),'failed')
        with self.assertRaisesRegex(ValueError,'unresolved'):self.u.cleanup_plan(result['name'])

    def test_stage_reauthenticates_and_idle_guard_still_applies(self):
        result=self.receive();review=self.c.plan('image.stage',{'digest':self.digest})
        with patch.object(self.adapter,'verify',side_effect=ValueError('signature changed')):
            with self.assertRaisesRegex(ValueError,'signature'):self.adapter.apply(review)
        self.assertEqual(self.backend.calls,[])
        from contextlib import contextmanager
        @contextmanager
        def printing():raise ValueError('printer busy');yield
        self.adapter.admission=printing
        with self.assertRaisesRegex(ValueError,'printer busy'):self.adapter.apply(review)
        self.assertEqual(self.backend.calls,[])


class ProtocolTests(unittest.TestCase):
    def transport(self):
        a,b=socket.socketpair();self.addCleanup(a.close);self.addCleanup(b.close)
        t=Transport(a.fileno(),a.fileno());return t,b

    def test_header_bounds_fragmentation_and_timeout(self):
        t,b=self.transport();b.sendall(b'{"size":3}\n');self.assertEqual(t.header(),{'size':3})
        t,b=self.transport();b.sendall(b'x'*4097)
        with self.assertRaisesRegex(ValueError,'metadata'):t.header()
        t,b=self.transport();t.deadline=time.monotonic()+.05
        with self.assertRaisesRegex(ValueError,'timeout'):t.header()

    def test_chunk_ack_short_extra_and_one_byte_final_chunk(self):
        t,b=self.transport();t.size=3;b.sendall(b'abc');self.assertEqual(t.read(3),b'abc')
        self.assertEqual(json.loads(b.recv(100)),dict(type='ack',received=3))
        b.sendall(b'x');self.assertEqual(t.read(1),b'x')
        t,b=self.transport();t.size=1;b.sendall(b'x');self.assertEqual(t.read(1),b'x')
        self.assertEqual(json.loads(b.recv(100))['received'],1)
        t,b=self.transport();t.size=3;b.sendall(b'x');b.shutdown(socket.SHUT_WR)
        with self.assertRaisesRegex(ValueError,'Truncated'):t.read(3)

    def test_verifier_timeout_and_output_are_bounded(self):
        with patch('sv08_bundle.VERIFY_SECONDS',.1):
            start=time.monotonic()
            with self.assertRaisesRegex(ValueError,'timed out'):manifest_output([sys.executable,'-c','import time;time.sleep(5)'])
            self.assertLess(time.monotonic()-start,1)
        with patch('sv08_bundle.VERIFY_OUTPUT',1024):
            with self.assertRaisesRegex(ValueError,'budget'):manifest_output([sys.executable,'-c','print("x"*2048)'])

    def test_overall_helper_deadline_covers_verification(self):
        code = """import sys,time
sys.path.insert(0, RUNTIME)
import sv08_admin_upload as u, sv08_admin
u.TRANSFER_SECONDS=.1
sv08_admin.installed_controller=lambda:None
class Intake:
    def receive(self, plan, stream):time.sleep(5)
u.installed_uploads=lambda c:Intake()
u.Transport.header=lambda t:{'size':1}
sys.exit(u.main())
""".replace('RUNTIME',repr(str(Path(__file__).resolve().parents[1]/'runtime')))
        start=time.monotonic();result=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=2)
        self.assertEqual(result.returncode,1);self.assertLess(time.monotonic()-start,1)
        self.assertNotIn(b'complete',result.stdout)

    def test_readonly_runner_propagates_through_devices_and_status(self):
        from sv08_boot import verify_devices
        from sv08_rauc import Backend as RealBackend
        calls=[]
        def reader(command,**kwargs):
            calls.append(command)
            if command[0]=='findmnt':return '1:1' if command[-1]=='/' else '1:2'
            return '{"observed":true}'
        with patch('sv08_boot.device_number',side_effect=['1:1','1:2','1:3']):
            verify_devices({'devices':{'root-a':'root','data':'data','boot-a':'boot'}},'A',read_command=reader)
        backend=RealBackend({}, {}, {}, {})
        self.assertEqual(backend.status(reader),{'observed':True})
        self.assertEqual([call[0] for call in calls],['findmnt','findmnt','/usr/bin/rauc'])

    def test_cleanup_backend_probe_is_bounded_without_install_timeout(self):
        from sv08_rauc import Backend as RealBackend
        backend=RealBackend({}, {}, {}, {})
        def context(boot,read_command=None):
            read_command([sys.executable,'-c','import time;time.sleep(5)'])
        backend.validate_context=context
        with patch('sv08_rauc.CLEANUP_SECONDS',.1):
            with self.assertRaisesRegex(ValueError,'timed out'):backend.cleanup_observation({},None)

    def test_parent_sigkill_terminates_verifier_descendants(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); ready=root/'ready'; escaped=root/'escaped'
            descendant = "import pathlib,time;time.sleep(.6);pathlib.Path("+repr(str(escaped))+").write_text('escaped')"
            verifier = "import subprocess,sys,pathlib,time; p=subprocess.Popen([sys.executable,'-c',"+repr(descendant)+"]);pathlib.Path("+repr(str(ready))+").write_text(str(p.pid));time.sleep(10)"
            lock=root/'lease'
            runner = "import sys,os,fcntl;sys.path.insert(0,"+repr(str(Path(__file__).resolve().parents[1]/'runtime'))+");from sv08_bundle import manifest_output;fd=os.open("+repr(str(lock))+",os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX);manifest_output([sys.executable,'-c',"+repr(verifier)+"],lease_fd=fd)"
            parent=subprocess.Popen([sys.executable,'-c',runner],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                end=time.monotonic()+3
                while not ready.exists() and time.monotonic()<end:time.sleep(.01)
                self.assertTrue(ready.exists())
                # Freeze the guardian to make the parent-loss window deterministic.
                children=Path('/proc')/str(parent.pid)/'task'/str(parent.pid)/'children'
                guardian=int(children.read_text().split()[0]);os.kill(guardian,19)
                parent.kill();parent.wait()
                import fcntl
                fd=os.open(lock,os.O_RDWR)
                try:
                    with self.assertRaises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    os.kill(guardian,18);time.sleep(.8)
                    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                finally:os.close(fd)
                self.assertFalse(escaped.exists())
                proc=Path('/proc')/ready.read_text()/'stat'
                if proc.exists():self.assertEqual(proc.read_text().split()[2],'Z')
            finally:
                if parent.poll() is None:parent.kill();parent.wait()
