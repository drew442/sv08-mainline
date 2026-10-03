"""Offline storage, identity, publication and compatibility evidence."""
from contextlib import nullcontext
import copy
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_admin import ACTIONS
from sv08_admin_jobs import Jobs
from sv08_admin_history import History, encode, digest, directory, pair, ALLOCATED, METADATA_BYTES
from sv08_export import Export, restore_history
from sv08_state import atomic_json
from test_data_budget import fixture_budget, fixture_root

BASE = 'f2d6a49ffa61b17279be2c59a32b31d4e8273f3f'


def receipt(number, phase='succeeded'):
    title, effect = ACTIONS['image.cancel']
    return dict(id=f'{number:032x}', plan=dict(action='image.cancel', arguments={}, revision='a'*64,
                title=title, effect=effect, preserves_user_data=True), boot_id='original-boot',
                phase=phase, message='Original outcome', queued_at=1)


def disposed(number):
    row = receipt(number, 'interrupted')
    from sv08_admin import revision
    from sv08_admin_resolution import KIND
    evidence = dict(original_sha256=revision(row), bounded_evidence='e'*15000)
    plan = dict(kind=KIND, id=row['id'], evidence_sha256=revision(evidence))
    row['disposition'] = dict(outcome='unknown', plan=plan, evidence=evidence)
    return row


def maximal_disposed(number):
    from sv08_admin import revision
    from sv08_admin_resolution import KIND
    row=receipt(number,'interrupted');row['message']='m'*3200;row['boot_id']='original-'+('b'*100)
    evidence=dict(original_sha256=revision(row),bounded_evidence='e'*16100)
    row['disposition']=dict(outcome='unknown',evidence=evidence,
        plan=dict(kind=KIND,id=row['id'],evidence_sha256=revision(evidence)))
    return row


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=fixture_root())
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'admin-image-jobs'; self.root.mkdir(mode=0o700)
        self.jobs = Jobs(self.root, 'new-boot', lambda identity: None, budget=fixture_budget())
        self.rows = [receipt(i) for i in range(128)]; self.rows[0] = disposed(0)
        atomic_json(self.root / 'jobs.json', self.rows)

    def migrate(self):
        history = History(self.jobs); history.apply(history.review())

    def rollover(self):
        self.migrate(); history = History(self.jobs); history.apply(history.review())

    def test_full_baseline_migration_rollover_retry_and_late_worker(self):
        class Controller:
            context = 'host'
            def plan(inner, *args): raise AssertionError('Historical retry reached state')
        self.assertEqual(self.jobs.submit(self.rows[1]['id'], self.rows[1]['plan'], Controller())['phase'], 'succeeded')
        with self.assertRaisesRegex(ValueError, 'full'): self.jobs.submit('f'*32, self.rows[1]['plan'], Controller())
        self.rollover()
        self.assertEqual(self.jobs.load(), self.rows)
        from sv08_admin_resolution import apply
        self.assertEqual(apply(self.jobs, self.rows[0]['disposition']['plan'], Controller())['phase'], 'interrupted')
        view = self.jobs.view(); queued = receipt(200, 'queued'); queued.update(boot_id='new-boot', queued_at=int(time.monotonic()))
        with self.jobs.lock('ledger.lock'): self.jobs.save([queued], view['revision'])
        self.jobs.work(lambda: (_ for _ in ()).throw(AssertionError('Archived worker constructed controller')), self.rows[0]['id'])
        self.assertEqual(self.jobs.view()['active'], [queued])
        from unittest.mock import patch
        from sv08_admin_jobs import main
        with patch('sv08_admin.installed_job_context', return_value=({}, self.jobs)), patch('sv08_admin.installed_controller', side_effect=AssertionError('Named installed worker constructed backend')), patch('sys.argv', ['worker', self.rows[0]['id']]):
            self.assertEqual(main(), 0)
        changed = copy.deepcopy(self.rows[1]['plan']); changed['revision'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'different'): self.jobs.submit(self.rows[1]['id'], changed, Controller())
        self.assertEqual(self.jobs.load()[:128], self.rows)

    def test_missing_corrupt_references_and_damaged_fence_refuse(self):
        self.migrate(); view = self.jobs.view(); manifest = (self.root / 'jobs.json').read_bytes()
        object = self.root / view['manifest']['active']['name']; raw = object.read_bytes()
        object.unlink()
        with self.assertRaises((ValueError, OSError)): self.jobs.history()
        object.write_bytes(raw); object.chmod(0o600)
        object.write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError, 'Corrupt'): self.jobs.history()
        object.write_bytes(raw)
        (self.root / 'jobs.json').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing'): self.jobs.history()
        (self.root / 'jobs.json').write_bytes(manifest); (self.root / 'jobs.json').chmod(0o600)
        (self.root / 'history-format-v2.lock').unlink()
        with self.assertRaisesRegex(ValueError, 'fence'): self.jobs.history()

    def test_eligibility_no_inference_from_boot_or_time(self):
        for phase in ('queued', 'running', 'interrupted'):
            rows = [receipt(i) for i in range(128)]; rows[0] = receipt(0, phase)
            atomic_json(self.root / 'jobs.json', rows)
            with self.assertRaisesRegex(ValueError, 'Unresolved'): History(self.jobs).review()
        atomic_json(self.root / 'jobs.json', self.rows)
        plan = History(self.jobs).review(); before = (self.root / 'jobs.json').read_bytes()
        self.assertEqual((self.root / 'jobs.json').read_bytes(), before)
        self.assertFalse((self.root / 'history-format-v2.lock').exists())
        self.migrate()
        with self.assertRaisesRegex(ValueError, 'changed'): History(self.jobs).apply(plan | {'revision':'f'*64})

    def test_export_relationship_and_isolated_restore(self):
        self.rollover(); target = self.base / 'destination'; target.mkdir(mode=0o700)
        exporter = Export(self.base, {'usb':dict(path=str(target), label='fixture')}, lambda target:nullcontext(), reserve_bytes=0)
        # Destination must not be within the source; use a sibling fixture.
        other = tempfile.TemporaryDirectory(dir=fixture_root()); self.addCleanup(other.cleanup)
        exporter = Export(self.base, {'usb':dict(path=other.name, label='fixture')}, lambda target:nullcontext(), reserve_bytes=0)
        result = exporter.execute(exporter.prepare('usb'))
        archive = Path(other.name) / result['filename']
        destination = Path(other.name) / 'restored'
        restored = restore_history(archive, destination, nullcontext)
        jobs = Jobs(destination, '', budget=fixture_budget())
        self.assertEqual(jobs.load(), self.rows); self.assertEqual(restored['count'], 128)
        a=(destination/'ledger.lock').stat(); b=(destination/'history-format-v2.lock').stat()
        self.assertEqual((a.st_ino, a.st_nlink), (b.st_ino, 2))
        self.assertEqual(a.st_mode & 0o777, 0o600); self.assertEqual(destination.stat().st_mode & 0o777, 0o700)

    def test_final_finite_capacity_and_measurement(self):
        self.rows=[maximal_disposed(i) for i in range(128)];atomic_json(self.root/'jobs.json',self.rows)
        peaks=[]
        def measure(point):
            peaks.append(dict(point=point,allocated=sum(p.stat().st_blocks*512 for p in self.root.iterdir())+self.root.stat().st_blocks*512,entries=len(list(self.root.iterdir()))+2,objects=sum(p.name.startswith('snapshot-') or p.name.startswith('.history-object-') for p in self.root.iterdir())))
        self.jobs.history_fault=measure
        self.rollover()
        for batch in range(1, 8):
            view = self.jobs.view(); rows = [maximal_disposed(batch*128+i) for i in range(128)]
            with self.jobs.lock('ledger.lock'): self.jobs.save(rows, view['revision'])
            History(self.jobs).apply(History(self.jobs).review())
        view = self.jobs.view(); rows = [maximal_disposed(1024+i) for i in range(128)]
        with self.jobs.lock('ledger.lock'): self.jobs.save(rows, view['revision'])
        start=time.monotonic(); import tracemalloc; tracemalloc.start()
        view=self.jobs.view(); _, peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
        self.assertEqual(len(view['rows']), 1152); self.assertLessEqual(view['stats']['allocated'], ALLOCATED)
        self.assertLessEqual(view['stats']['metadata'], METADATA_BYTES); self.assertLessEqual(view['stats']['entries'], 64)
        class Controller:
            def plan(inner,*args): raise AssertionError('Capacity reached backend')
        with self.assertRaisesRegex(ValueError, 'full'): self.jobs.submit('f'*32, rows[0]['plan'], Controller())
        self.jobs.submit(rows[0]['id'], rows[0]['plan'], Controller())
        with self.assertRaises(ValueError): History(self.jobs).review()
        report=dict(encoded=sum(p.stat().st_size for p in self.root.iterdir()), **view['stats'], read_peak_bytes=peak, read_seconds=time.monotonic()-start, publication_peak_allocated=max(p['allocated'] for p in peaks),publication_peak_entries=max(p['entries'] for p in peaks),publication_peak_objects=max(p['objects'] for p in peaks),block_bytes=os.statvfs(self.root).f_frsize,actual_free_bytes=os.statvfs(self.root).f_bavail*os.statvfs(self.root).f_frsize,fixture_floor=self.jobs.budget.floor)
        Path(fixture_root()).joinpath('history-bounds-'+os.environ.get('SV08_HISTORY_MEASUREMENT_TAG','tmpfs')+'.json').write_text(json.dumps(report,indent=2))

    def test_real_process_contention_persistent_inode(self):
        with self.jobs.lock('worker.lock'):
            child=multiprocessing.Process(target=_maintenance_busy,args=(str(self.root),))
            child.start(); child.join(5); self.assertEqual(child.exitcode,0)
        inode=(self.root/'ledger.lock').stat().st_ino if (self.root/'ledger.lock').exists() else None
        self.migrate()
        if inode is not None: self.assertEqual(inode,(self.root/'ledger.lock').stat().st_ino)

    def test_public_old_gate_and_truthful_bare_missing_counterexample(self):
        source=subprocess.check_output(['git','show',BASE+':runtime/sv08_admin_jobs.py'],text=True)
        oldfile=self.base/'old_jobs.py'; oldfile.write_text(source)
        spec=importlib.util.spec_from_file_location('old_jobs',oldfile); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        old=module.Jobs(self.root,'old',lambda identity: (_ for _ in ()).throw(AssertionError('launch')))
        self.migrate(); manifest=(self.root/'jobs.json').read_bytes()
        for raw in (manifest, None, b'{malformed', b'[]'):
            path=self.root/'jobs.json'
            if raw is None:path.unlink(missing_ok=True)
            else:path.write_bytes(raw);path.chmod(0o600)
            for invoke in (old.history,lambda:old.submit('f'*32,self.rows[1]['plan'],None),lambda:old.work(lambda:None,'f'*32)):
                with self.assertRaisesRegex(ValueError,'lock'):invoke()
        (self.root/'jobs.json').unlink()
        self.assertEqual(old.load(),[])  # A bypass, not a passing refusal.

    def test_publication_fault_matrix_and_bounded_restart(self):
        points=['fence-link','fence-link-created','fence-validate','fence-validated','fence-file-fsync','fence-directory-fsync','fence-parent-fsync',
                'object-create','object-write','object-flush','object-file-fsync','object-publish','object-directory-fsync',
                'manifest-create','manifest-write','manifest-flush','manifest-file-fsync','manifest-replace',
                'manifest-directory-fsync','manifest-parent-fsync','cleanup','lost-ack']
        # Each independent case starts from the same valid legacy source; no failed evidence is overwritten.
        for point in points:
            with self.subTest(point=point):
                temp=tempfile.TemporaryDirectory(dir=fixture_root())
                try:
                    root=Path(temp.name)/'admin-image-jobs';root.mkdir(mode=0o700);atomic_json(root/'jobs.json',self.rows)
                    jobs=Jobs(root,'new',lambda identity:None,budget=fixture_budget()); history=History(jobs);plan=history.review()
                    hit=[]
                    if point == 'cleanup':
                        orphan=root/('snapshot-'+'f'*64+'.json');orphan.write_bytes(b'[]');orphan.chmod(0o600)
                    def fail(boundary):
                        if boundary==point and not hit:hit.append(boundary);raise OSError(28,'Injected ENOSPC at '+point)
                    jobs.history_fault=fail
                    try:History(jobs).apply(plan)
                    except OSError:pass
                    self.assertEqual(hit,[point])
                    jobs.history_fault=lambda boundary:None
                    self.assertEqual(jobs.load(),self.rows)
                    if jobs.view()['format']==1:History(jobs).apply(History(jobs).review())
                    else:History(jobs).apply(plan)
                    self.assertEqual(jobs.load(),self.rows)
                    self.assertLessEqual(jobs.view()['stats']['entries'],64)
                finally:temp.cleanup()


def _maintenance_busy(root):
    try: History(Jobs(root,'',budget=fixture_budget())).apply(History(Jobs(root,'',budget=fixture_budget())).review())
    except BlockingIOError:return
    raise AssertionError('Maintenance entered a held worker lock')


def _old_waiter(root, source, ready, finish, modify):
    spec=importlib.util.spec_from_file_location('waiter_old_jobs', source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=module.fcntl.flock
    def flock(fd, flags):
        ready.set(); return original(fd, flags)
    module.fcntl.flock=flock
    jobs=module.Jobs(root,'old',lambda identity:None)
    try:
        with jobs.lock('ledger.lock'):
            if modify:
                rows=jobs.load();rows[-1]['message']='Durable old waiter update';jobs.save(rows)
            else:
                try:jobs.load()
                except ValueError:finish.set();return
                raise AssertionError('Old waiter accepted version 2')
        finish.set()
    finally:module.fcntl.flock=original


class OldWaiterTests(unittest.TestCase):
    setUp = HistoryTests.setUp
    def test_old_admitted_waiter_same_inode_and_resume_revision(self):
        source=subprocess.check_output(['git','show',BASE+':runtime/sv08_admin_jobs.py'],text=True)
        old=self.base/'old_waiter.py';old.write_text(source)
        history=History(self.jobs);plan=history.review()
        context=multiprocessing.get_context('spawn');ready=context.Event();finish=context.Event()
        with self.jobs.lock('worker.lock'), self.jobs.lock('ledger.lock'):
            child=context.Process(target=_old_waiter,args=(str(self.root),str(old),ready,finish,False));child.start()
            self.assertTrue(ready.wait(5))
            history.publish(self.jobs.view(), self.rows, plan)
        child.join(5)
        if child.is_alive(): child.kill(); child.join(5)
        self.assertEqual(child.exitcode,0);self.assertTrue(finish.is_set())


class ExportStabilityTests(unittest.TestCase):
    setUp=HistoryTests.setUp
    rollover=HistoryTests.rollover
    migrate=HistoryTests.migrate

    def test_read_only_source_alias_change_and_restore_destination_bound(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        self.rollover()
        other=tempfile.TemporaryDirectory(dir=fixture_root());self.addCleanup(other.cleanup)
        exporter=Export(self.base,{'usb':dict(path=other.name,label='fixture')},lambda target:nullcontext(),reserve_bytes=0)
        original_open=os.open
        def read_only(path,flags,*args,**kwargs):
            candidate=Path(path)
            if not candidate.is_absolute() and kwargs.get('dir_fd') is not None:
                candidate=Path(os.readlink('/proc/self/fd/'+str(kwargs['dir_fd'])))/candidate
            if candidate.is_relative_to(self.base) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT):
                raise AssertionError('Exporter wrote read-only source')
            return original_open(path,flags,*args,**kwargs)
        before=set(self.root.iterdir())
        with patch('os.open',side_effect=read_only):plan=exporter.prepare('usb');result=exporter.execute(plan)
        self.assertEqual(set(self.root.iterdir()),before)
        archive=Path(other.name)/result['filename'];destination=Path(other.name)/'too-small'
        fs=SimpleNamespace(f_frsize=4096,f_bsize=4096,f_bavail=0,f_favail=0)
        with patch('sv08_export.os.fstatvfs',return_value=fs):
            with self.assertRaisesRegex(ValueError,'destination space'):restore_history(archive,destination,nullcontext)
        self.assertFalse(destination.exists())
        plan=exporter.prepare('usb');alias=self.root/'history-format-v2.lock';alias.unlink();os.link(self.root/'ledger.lock',alias)
        with self.assertRaisesRegex(ValueError,'changed'):exporter.execute(plan)
        self.assertEqual(len(list(Path(other.name).glob('*.tar'))),1)
