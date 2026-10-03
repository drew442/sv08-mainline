"""Frozen old supported paths and pre-admitted old waiters, not bare bypasses."""
import importlib.util
import multiprocessing
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from sv08_admin_history import History
from sv08_state import atomic_json
from test_admin_history import HistoryTests, BASE, _old_waiter


def frozen(name, destination):
    source=subprocess.check_output(['git','show',BASE+':runtime/'+name+'.py'],text=True)
    path=destination/(name+'_old.py');path.write_text(source)
    spec=importlib.util.spec_from_file_location(name+'_old',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class CompatibilityTests(unittest.TestCase):
    setUp = HistoryTests.setUp
    migrate = HistoryTests.migrate

    def test_each_old_public_disposition_upload_gate_with_every_manifest_shape(self):
        oldjobs=frozen('sv08_admin_jobs',self.base).Jobs(self.root,'old',lambda i:None)
        oldresolution=frozen('sv08_admin_resolution',self.base)
        oldupload=frozen('sv08_admin_upload',self.base)
        self.migrate();manifest=(self.root/'jobs.json').read_bytes()
        class Store:
            root=None
            def load(inner):return {}
            def locked(inner,**kwargs):raise AssertionError('Old upload reached state')
        class Controller:pass
        controller=Controller();controller.jobs=oldjobs;controller.store=Store();controller.store.root=self.base
        (self.base/'state.json').write_text('{}')
        upload=object.__new__(oldupload.Uploads);upload.controller=controller
        for raw in (manifest,None,b'{malformed',b'[]'):
            path=self.root/'jobs.json'
            if raw is None:path.unlink(missing_ok=True)
            else:path.write_bytes(raw);path.chmod(0o600)
            for action in (lambda:oldresolution.apply(oldjobs,self.rows[0]['disposition']['plan'],controller),
                           lambda:upload.admitted().__enter__()):
                with self.assertRaisesRegex(ValueError,'lock'):action()
            self.assertEqual(path.read_bytes() if path.exists() else None,raw)

    def test_old_waiter_legacy_write_invalidates_prepared_migration(self):
        old=frozen('sv08_admin_jobs',self.base);source=self.base/'sv08_admin_jobs_old.py'
        history=History(self.jobs);plan=history.review();context=multiprocessing.get_context('spawn')
        ready=context.Event();finish=context.Event()
        with self.jobs.lock('worker.lock'),self.jobs.lock('ledger.lock'):
            child=context.Process(target=_old_waiter,args=(str(self.root),str(source),ready,finish,True));child.start()
            self.assertTrue(ready.wait(5))
            def stop(point):
                if point=='fence-file-fsync':raise OSError('Interrupted after durable alias creation boundary')
            self.jobs.history_fault=stop
            with self.assertRaises(OSError):History(self.jobs).publish(self.jobs.view(),self.rows,plan)
        child.join(5)
        if child.is_alive():child.kill();child.join(5)
        self.assertEqual(child.exitcode,0);self.assertTrue(finish.is_set())
        self.jobs.history_fault=lambda point:None
        self.assertEqual(self.jobs.load()[-1]['message'],'Durable old waiter update')
        with self.assertRaisesRegex(ValueError,'changed'):History(self.jobs).apply(plan)
        History(self.jobs).apply(History(self.jobs).review())
        self.assertEqual(self.jobs.load()[-1]['message'],'Durable old waiter update')


    def test_old_writer_precedes_migration_and_prepared_revision_refuses(self):
        frozen('sv08_admin_jobs',self.base)
        plan=History(self.jobs).review();context=multiprocessing.get_context('spawn')
        ready=context.Event();finish=context.Event()
        with self.jobs.lock('ledger.lock'):
            child=context.Process(target=_old_waiter,args=(str(self.root),str(self.base/'sv08_admin_jobs_old.py'),ready,finish,True));child.start()
            self.assertTrue(ready.wait(5))
        try:
            child.join(5);self.assertEqual(child.exitcode,0);self.assertTrue(finish.is_set())
            with self.assertRaisesRegex(ValueError,'changed'):History(self.jobs).apply(plan)
            self.assertFalse((self.root/'history-format-v2.lock').exists())
            History(self.jobs).apply(History(self.jobs).review())
            self.assertEqual(self.jobs.load()[-1]['message'],'Durable old waiter update')
        finally:
            if child.is_alive():child.kill();child.join(5)


def _old_submit_second_lock(root, source, ready, resume, result):
    spec=importlib.util.spec_from_file_location('old_second_submit',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    jobs=module.Jobs(root,'old',lambda identity:os._exit(99))
    rows=jobs.load();plan=rows[0]['plan']
    class Controller:
        context='host'
        def plan(inner,*args):ready.set();resume.wait(5);return plan
    try:jobs.submit('f'*32,plan,Controller())
    except ValueError as error:
        if 'lock' not in str(error):raise
        result.set();return
    raise AssertionError('Old second ledger acquisition admitted mutation')


class SecondAcquisitionTests(unittest.TestCase):
    setUp=HistoryTests.setUp
    def test_old_submit_rechecks_fence_after_releasing_first_ledger(self):
        source=frozen('sv08_admin_jobs',self.base);path=self.base/'sv08_admin_jobs_old.py'
        atomic_json(self.root/'jobs.json',self.rows[:1])
        context=multiprocessing.get_context('spawn');ready=context.Event();resume=context.Event();result=context.Event()
        child=context.Process(target=_old_submit_second_lock,args=(str(self.root),str(path),ready,resume,result));child.start()
        try:
            self.assertTrue(ready.wait(5));History(self.jobs).apply(History(self.jobs).review());resume.set()
            child.join(5);self.assertEqual(child.exitcode,0);self.assertTrue(result.is_set());self.assertEqual(self.jobs.load(),self.rows[:1])
        finally:
            if child.is_alive():child.kill();child.join(5)


def _old_disposition_second_lock(root, jobs_source, resolution_source, ready, resume, result):
    from contextlib import contextmanager, nullcontext
    def load(name, source):
        spec=importlib.util.spec_from_file_location(name,source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    oldjobs=load('old_disposition_jobs',jobs_source)
    oldresolution=load('old_disposition_resolution',resolution_source)
    jobs=oldjobs.Jobs(root,'old',lambda identity:os._exit(99))
    original=oldresolution.admitted
    @contextmanager
    def paused(*args):
        ready.set();assert resume.wait(5)
        with original(*args) as value:yield value
    oldresolution.admitted=paused
    class Store:
        def locked(self,**kwargs):return nullcontext()
    class Backend:
        def resolution_evidence(self,*args):raise AssertionError('Reached old evidence')
    class Adapter:backend=Backend()
    class Controller:context='host';store=Store();adapter=Adapter()
    plan=dict(kind=oldresolution.KIND,id='00000000000000000000000000000001',evidence_sha256='a'*64)
    try:oldresolution.apply(jobs,plan,Controller())
    except ValueError as error:
        if 'lock' not in str(error):raise
        result.set();return
    raise AssertionError('Old disposition second ledger acquisition admitted')


class DispositionAcquisitionTests(unittest.TestCase):
    setUp=HistoryTests.setUp
    def test_old_disposition_rechecks_fence_after_initial_ack_lookup(self):
        frozen('sv08_admin_jobs',self.base);frozen('sv08_admin_resolution',self.base)
        context=multiprocessing.get_context('spawn');ready=context.Event();resume=context.Event();result=context.Event()
        child=context.Process(target=_old_disposition_second_lock,args=(str(self.root),str(self.base/'sv08_admin_jobs_old.py'),str(self.base/'sv08_admin_resolution_old.py'),ready,resume,result));child.start()
        try:
            self.assertTrue(ready.wait(5));History(self.jobs).apply(History(self.jobs).review());resume.set()
            child.join(5);self.assertEqual(child.exitcode,0);self.assertTrue(result.is_set())
            self.assertEqual(self.jobs.load(),self.rows)
        finally:
            if child.is_alive():child.kill();child.join(5)
