"""Public-path regressions for independent review F1-F4; offline only."""
from contextlib import nullcontext
from io import BytesIO
import copy
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from test_data_budget import fixture_root, fixture_budget
from test_admin_history import receipt, disposed
from sv08_admin import revision
from sv08_admin_jobs import Jobs
from sv08_admin_history import History
from sv08_admin_resolution import KIND
from sv08_boot import prepare_permissions
from sv08_data_budget import Budget
from sv08_export import Export, restore_history, TAR_BUFFER, ReadbackReader
from sv08_staging import Staging
from sv08_state import Store, atomic_json
import sv08_admin_resolution as resolution


class Repairs(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=fixture_root());self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)

    def test_post_boot_history_upload_and_new_generation_use_shared_private_lock(self):
        root=self.base/'sv08';budget=Budget(root);store=Store(root,budget=budget)
        store.initialize();boot=store.prepare_boot('A','release-1')
        with patch('sv08_boot.os.chown'):prepare_permissions(root,boot['generation'])
        self.assertEqual(stat.S_IMODE(root.stat().st_mode),0o711)
        jobs=Jobs(root/'admin-image-jobs','fixture',lambda i:None,budget=budget)
        jobs.root.mkdir(mode=0o700);rows=[receipt(i) for i in range(128)];rows[0]=disposed(0)
        atomic_json(jobs.root/'jobs.json',rows)
        self.assertTrue(jobs.history()['maintenance_available'])
        History(jobs).apply(History(jobs).review());History(jobs).apply(History(jobs).review())
        self.assertEqual(jobs.load(),rows)
        payload=b'bounded post-boot upload';sha=hashlib.sha256(payload).hexdigest()
        (root/'uploads').mkdir(mode=0o700)
        staging=Staging(root/'uploads',owner_uid=os.geteuid(),budget=budget)
        staging.receive(BytesIO(payload),len(payload),sha,lambda p:dict(bundle_sha256=sha))
        store.expect_trial('B','release-2','A');trial=store.prepare_boot('B','release-2')
        self.assertNotEqual(boot['generation'],trial['generation']);self.assertEqual(jobs.load(),rows)
        lock=root/'allocation.lock';info=lock.stat()
        self.assertEqual((stat.S_IMODE(info.st_mode),info.st_uid,info.st_nlink),(0o600,os.geteuid(),1))
        self.assertEqual(stat.S_IMODE(root.stat().st_mode),0o711)
        for mode in (0o755,0o710,0o777):
            root.chmod(mode)
            with self.assertRaises(ValueError):budget.check(1)
            with self.assertRaises(ValueError):
                with budget.locked():pass
        root.chmod(0o711)
        lock.chmod(0o644)
        with self.assertRaises(ValueError):
            with budget.locked():pass
        lock.chmod(0o600);os.link(lock,root/'extra-lock-link')
        with self.assertRaises(ValueError):
            with budget.locked():pass
        (root/'extra-lock-link').unlink()

    def jobs(self,root,rows=(),v2=False):
        root.mkdir(mode=0o700)
        jobs=Jobs(root,'fixture',lambda i:self.fail('Unexpected worker launch'),budget=fixture_budget(self.base))
        atomic_json(root/'jobs.json',list(rows))
        if v2:History(jobs).apply(History(jobs).review())
        return jobs

    def test_public_submit_retry_and_jobs_observation_settle_or_refuse(self):
        for v2 in (False,True):
            for point in ('manifest-directory-fsync','manifest-parent-fsync'):
                with self.subTest(v2=v2,point=point):
                    root=self.base/('submit-'+str(v2)+point);jobs=self.jobs(root,v2=v2)
                    plan=receipt(1)['plan'];hit=[];failed=[False]
                    def fault(boundary):
                        if boundary==point:failed[0]=True;hit.append(boundary);raise OSError(errno.EIO,'post-replace durability')
                        if failed[0] and boundary in ('recovery-directory-fsync','recovery-parent-fsync'):
                            hit.append(boundary);raise OSError(errno.EIO,'persistent recovery failure')
                    jobs.history_fault=fault
                    class Current:
                        context='host'
                        def plan(self,*args):return plan
                    with self.assertRaises(OSError):jobs.submit('1'*32,plan,Current())
                    self.assertIn(point,hit);raw=(root/'jobs.json').read_bytes();names=set(os.listdir(root))
                    class NoCurrent:
                        @property
                        def context(self):raise AssertionError('Retry reached current controller')
                    with patch('sv08_admin_history.os.fsync',wraps=os.fsync) as sync:
                        for route in (lambda:jobs.submit('1'*32,plan,NoCurrent()),jobs.history):
                            with self.assertRaises(OSError):route()
                        self.assertGreater(sync.call_count,0)
                    self.assertEqual((root/'jobs.json').read_bytes(),raw);self.assertEqual(set(os.listdir(root)),names)
                    changed=copy.deepcopy(plan);changed['revision']='f'*64
                    with self.assertRaisesRegex(ValueError,'different review'):jobs.submit('1'*32,changed,NoCurrent())
                    settled=[];jobs.history_fault=settled.append
                    self.assertEqual(jobs.submit('1'*32,plan,NoCurrent())['phase'],'queued')
                    self.assertTrue({'recovery-directory-fsync','recovery-parent-fsync'}.issubset(settled))
                    self.assertEqual(len(jobs.history()['jobs']),1)
                    self.assertEqual((root/'jobs.json').read_bytes(),raw);self.assertEqual(set(os.listdir(root)),names)

    def test_submit_second_acquisition_refuses_concurrent_uncertain_receipt(self):
        jobs=self.jobs(self.base/'second-submit',v2=True);plan=receipt(1)['plan'];failed=[False]
        def fault(point):
            if point=='manifest-directory-fsync':failed[0]=True;raise OSError(errno.EIO,'post-replace durability')
            if failed[0] and point=='recovery-directory-fsync':raise OSError(errno.EIO,'persistent recovery failure')
        jobs.history_fault=fault
        class Inner:
            context='host'
            def plan(self,*args):return plan
        class Outer:
            context='host'
            def plan(inner,*args):
                # Another supported writer commits between the two ledger locks.
                with self.assertRaises(OSError):jobs.submit('1'*32,plan,Inner())
                return plan
        with self.assertRaises(OSError):jobs.submit('1'*32,plan,Outer())
        self.assertTrue(failed[0]);raw=(jobs.root/'jobs.json').read_bytes()
        jobs.history_fault=lambda point:None
        self.assertEqual(jobs.submit('1'*32,plan,object())['phase'],'queued')
        self.assertEqual((jobs.root/'jobs.json').read_bytes(),raw)

    def test_public_disposition_ack_and_inspect_settle_before_current_gates(self):
        for v2 in (False,True):
            for point in ('manifest-directory-fsync','manifest-parent-fsync'):
                with self.subTest(v2=v2,point=point):
                    jobs=self.jobs(self.base/('dispose-'+str(v2)+point),v2=v2)
                    row=receipt(7,'interrupted')
                    with jobs.lock('ledger.lock'):jobs.save([row],jobs.view()['revision'])
                    evidence=dict(original_sha256=revision(row),bounded_evidence='preserved')
                    plan=dict(kind=KIND,id=row['id'],evidence_sha256=revision(evidence));failed=[False];hit=[]
                    def fault(boundary):
                        if boundary==point:failed[0]=True;hit.append(boundary);raise OSError(errno.EIO,'post-replace durability')
                        if failed[0] and boundary in ('recovery-directory-fsync','recovery-parent-fsync'):
                            hit.append(boundary);raise OSError(errno.EIO,'persistent recovery failure')
                    jobs.history_fault=fault
                    with patch.object(resolution,'admitted',return_value=nullcontext((None,None))),patch.object(resolution,'evidence',return_value=evidence):
                        with self.assertRaises(OSError):resolution.apply(jobs,plan,object())
                    self.assertIn(point,hit);raw=(jobs.root/'jobs.json').read_bytes();names=set(os.listdir(jobs.root))
                    with patch.object(resolution,'admitted',side_effect=AssertionError('Acknowledgement reached current gates')):
                        for route in (lambda:resolution.apply(jobs,plan,object()),lambda:resolution.inspect(jobs,row['id'],object()),jobs.history):
                            with self.assertRaises(OSError):route()
                        jobs.history_fault=lambda point:None
                        self.assertEqual(resolution.apply(jobs,plan,object())['phase'],'interrupted')
                        self.assertEqual(jobs.load()[0]['disposition']['outcome'],'unknown')
                        self.assertIsNone(resolution.inspect(jobs,row['id'],object())['plan'])
                    self.assertEqual((jobs.root/'jobs.json').read_bytes(),raw);self.assertEqual(set(os.listdir(jobs.root)),names)
                    changed=dict(plan,evidence_sha256='f'*64)
                    with self.assertRaisesRegex(ValueError,'different review'):resolution.apply(jobs,changed,object())

    def test_restore_requires_exact_legacy_and_fenced_inventory(self):
        for v2 in (False,True):
            with self.subTest(v2=v2):
                source=self.base/('source-'+str(v2));source.mkdir(mode=0o700)
                jobs=self.jobs(source/'admin-image-jobs',[disposed(0)],v2=v2)
                with jobs.lock('ledger.lock'):pass
                media=self.base/('media-'+str(v2));media.mkdir(mode=0o700)
                exporter=Export(source,{'fixture':{'path':media}},lambda target:nullcontext(),reserve_bytes=0)
                result=exporter.execute(exporter.prepare('fixture'));archive=media/result['filename']
                destination=self.base/('complete-'+str(v2));restored=restore_history(archive,destination,nullcontext)
                self.assertEqual(restored['count'],1);self.assertEqual(Jobs(destination,'').load(),jobs.load())
                from test_admin_history_compatibility import frozen
                old=frozen('sv08_admin_jobs',self.base).Jobs(destination,'old',lambda identity:self.fail('Old restore writer launched'))
                restored_raw=(destination/'jobs.json').read_bytes()
                if v2:
                    with self.assertRaisesRegex(ValueError,'lock'):old.history()
                    with self.assertRaisesRegex(ValueError,'lock'):old.submit(jobs.load()[0]['id'],jobs.load()[0]['plan'],object())
                else:
                    old.submit(jobs.load()[0]['id'],jobs.load()[0]['plan'],object())
                self.assertEqual((destination/'jobs.json').read_bytes(),restored_raw)
                with tarfile.open(archive,'r:') as original:
                    members=[(item,original.extractfile(item).read() if item.isfile() else None) for item in original]
                selected=[item.name for item,_ in members if item.name.endswith('/jobs.json') or item.name.endswith('/ledger.lock') or item.name.endswith('/history-format-v2.lock') or '/snapshot-' in item.name]
                for omitted in selected:
                    for remove_record in (False,True):
                        damaged=media/'missing.tar'
                        with tarfile.open(damaged,'w') as out:
                            for item,payload in members:
                                if item.name==omitted:continue
                                if item.name=='export-manifest.json' and remove_record:
                                    inventory=json.loads(payload);inventory['files']=[r for r in inventory['files'] if r['path']!=omitted]
                                    payload=json.dumps(inventory).encode();item=copy.copy(item);item.size=len(payload)
                                out.addfile(item,BytesIO(payload) if payload is not None else None)
                        dest=self.base/'refused'
                        # A legacy inventory may legitimately omit an unreferenced lock,
                        # but it must never omit jobs.json. Fenced refs/pair are mandatory.
                        if remove_record and omitted.endswith('/ledger.lock') and not v2:continue
                        with self.subTest(omitted=omitted,remove_record=remove_record),patch('sv08_export.publish') as publish:
                            with self.assertRaises((ValueError,OSError,tarfile.TarError)):restore_history(damaged,dest,nullcontext)
                            publish.assert_not_called();self.assertFalse(dest.exists())
                            self.assertFalse(list(self.base.glob('.history-restore-*')))

    def test_export_missing_legacy_manifest_refuses_without_source_repair(self):
        source=self.base/'export-source';source.mkdir(mode=0o700)
        jobs=self.jobs(source/'admin-image-jobs',[disposed(0)])
        with jobs.lock('ledger.lock'):pass
        (jobs.root/'jobs.json').unlink();before={p.name:p.read_bytes() for p in jobs.root.iterdir()}
        media=self.base/'export-media';media.mkdir(mode=0o700)
        exporter=Export(source,{'fixture':{'path':media}},lambda target:nullcontext(),reserve_bytes=0)
        with self.assertRaisesRegex(ValueError,'Missing committed history'):exporter.prepare('fixture')
        self.assertEqual({p.name:p.read_bytes() for p in jobs.root.iterdir()},before)
        self.assertEqual(list(media.iterdir()),[])

    def test_restore_predecode_pax_global_nested_gnu_and_sparse_are_bounded(self):
        variants={}
        for name,kind in [('pax',tarfile.XHDTYPE),('global',tarfile.XGLTYPE),('gnu-name',tarfile.GNUTYPE_LONGNAME),('gnu-link',tarfile.GNUTYPE_LONGLINK)]:
            info=tarfile.TarInfo(name);info.type=kind;info.size=1024*1024
            variants[name]=info.tobuf(format=tarfile.USTAR_FORMAT)+b'X'*info.size+bytes(TAR_BUFFER)
        pax=tarfile.TarInfo('nested');pax.type=tarfile.XHDTYPE;pax.size=0
        variants['nested']=pax.tobuf(format=tarfile.USTAR_FORMAT)*160+bytes(TAR_BUFFER)
        sparse=tarfile.TarInfo('data/sparse');fields=b'1000000\n'+b'0\n0\n'*20000;sparse.size=len(fields)
        sparse.pax_headers={'GNU.sparse.major':'1','GNU.sparse.minor':'0','GNU.sparse.realsize':'0','GNU.sparse.name':sparse.name}
        variants['sparse-map']=sparse.tobuf(format=tarfile.PAX_FORMAT)+fields+bytes(TAR_BUFFER)
        for name,raw in variants.items():
            archive=self.base/'metadata.tar';archive.write_bytes(raw);requests=[];read_counts=[];original=ReadbackReader.read
            def counted(reader,size):
                requests.append(size)
                try:return original(reader,size)
                finally:read_counts.append(reader.count)
            with self.subTest(kind=name),patch.object(ReadbackReader,'read',counted),patch('sv08_export.publish') as publish:
                with self.assertRaisesRegex(ValueError,'metadata.*budget'):restore_history(archive,self.base/'refused',nullcontext)
                self.assertLessEqual(max(read_counts),65536+TAR_BUFFER)
                self.assertLessEqual(max(requests),TAR_BUFFER)
                publish.assert_not_called();self.assertFalse((self.base/'refused').exists())
