import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from sv08_export import Export
from sv08_restore import Restore
from sv08_recovery_restore_media import RestoreAdapter
from sv08_recovery import RecoveryController
from sv08_state import Store
from test_data_budget import fixture_root


class Guard:
    fingerprint = 'fixture-identities'
    def recheck(self): pass


@contextmanager
def admission(target):
    yield Guard()


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('SV08_RESTORE_SCRATCH') or fixture_root()); self.root = Path(self.tmp.name)
        self.source = self.root/'source'; self.source.mkdir(mode=0o700)
        self.usb = self.root/'usb'; self.usb.mkdir(mode=0o700)
        self.target = self.root/'target'; self.target.mkdir(mode=0o700)
        (self.target/'keep').write_bytes(b'keep')
        (self.source/'sv08').mkdir(mode=0o700)
        (self.source/'sv08/state.json').write_bytes(b'damaged registry bytes')
        (self.source/'gcodes').mkdir(mode=0o750)
        (self.source/'gcodes/example.gcode').write_bytes(b'G28\n')
        (self.source/'database.sqlite-wal').write_bytes(b'opaque database bytes')
        (self.source/'credentials').write_bytes(b'fixture secret'); os.chmod(self.source/'credentials',0o600)
        self.archive = self.export()
        self.restore = Restore({'backup': dict(path=self.archive,label='Fixture archive')},
            {'target':dict(root=self.target/'data',fresh_root=self.target/'sv08',label='Fixture target')},admission,reserve_bytes=0)
        self.controller = RecoveryController(Store(self.source/'sv08'),RestoreAdapter(self.restore))
    def tearDown(self): self.tmp.cleanup()
    def export(self):
        exporter = Export(self.source,{'usb':dict(path=self.usb,label='Fixture USB')},admission,reserve_bytes=0)
        result = exporter.execute(exporter.prepare('usb'))
        return self.usb/result['filename']
    def plan(self): return self.restore.prepare('target','backup')
    def rewrite(self, change):
        with tarfile.open(self.archive) as archive:
            entries = [(item,archive.extractfile(item).read() if item.isfile() else None) for item in archive]
        change(entries)
        with tarfile.open(self.archive,'w',format=tarfile.PAX_FORMAT) as archive:
            for item,data in entries: archive.addfile(item,io.BytesIO(data) if data is not None else None)
    def test_complete_roundtrip_preserves_modes_private_bytes_damaged_registry_and_siblings(self):
        before = self.archive.read_bytes()
        plan = self.controller.plan('recovery.data-restore',dict(archive='backup',target='target'))
        self.assertIn(str(self.target/'data'),plan['effect'])
        result = self.controller.apply(plan)
        self.assertIn('without repair',result['registry'])
        self.assertIn('No automatic',result['message'])
        for path in self.source.rglob('*'):
            restored = self.target/'data'/path.relative_to(self.source)
            self.assertEqual(path.stat().st_mode & 0o777,restored.stat().st_mode & 0o777)
            if path.is_file(): self.assertEqual(path.read_bytes(),restored.read_bytes())
        self.assertEqual(self.archive.read_bytes(),before); self.assertEqual((self.target/'keep').read_bytes(),b'keep')
    def test_inspect_review_cancel_fresh_do_not_write_apply_creates_immutable_defaults(self):
        self.controller.status()
        plan = self.controller.plan('recovery.initialize',dict(target='target'))
        self.assertFalse((self.target/'sv08').exists())
        result = self.controller.apply(plan)
        state = Store(self.target/'sv08').load()
        self.assertEqual(state['requested_mode'],'immutable'); self.assertEqual(state['slots'],{})
        self.assertEqual(result['registry'],'readable')
        for damage in (False,True):
            if damage: (self.target/'sv08/state.json').write_bytes(b'broken')
            before = (self.target/'sv08/state.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'already exists'): self.controller.plan('recovery.initialize',dict(target='target'))
            self.assertEqual((self.target/'sv08/state.json').read_bytes(),before)
    def test_fresh_layout_matches_existing_store_initialize(self):
        upstream = self.root/'upstream'; Store(upstream).initialize()
        self.restore.execute(self.restore.prepare('target',fresh=True))
        restored=self.target/'sv08'
        self.assertEqual({str(p.relative_to(upstream)) for p in upstream.rglob('*')},
                         {str(p.relative_to(restored)) for p in restored.rglob('*')})
        for path in upstream.rglob('*'):
            other=restored/path.relative_to(upstream)
            self.assertEqual(path.stat().st_mode & 0o777,other.stat().st_mode & 0o777)
            self.assertEqual((path.stat().st_uid,path.stat().st_gid),(other.stat().st_uid,other.stat().st_gid))
            if path.is_file():self.assertEqual(path.read_bytes(),other.read_bytes())
    def test_fresh_silent_write_corruption_and_metadata_failure_refuse_publication(self):
        plan=self.restore.prepare('target',fresh=True)
        original=os.fdopen
        for defect in ('bytes', 'defaults', 'mode', 'lock', 'extra', 'missing', 'directory-mode'):
            class Writer:
                def __init__(self,output):self.output=output
                def __enter__(self):return self
                def __exit__(self,*args):return self.output.__exit__(*args)
                def __getattr__(self,name):return getattr(self.output,name)
                def write(self,block):
                    if block and defect == 'bytes':self.output.write(b'X'*len(block))
                    elif block and defect == 'defaults':self.output.write(block.replace(b'immutable',b'writable '))
                    elif not block and defect == 'lock':self.output.write(b'X')
                    else:self.output.write(block)
                    if block and defect == 'mode':os.fchmod(self.output.fileno(),0o644)
                    if block and defect in ('extra', 'missing', 'directory-mode'):
                        stage=Path(os.readlink('/proc/self/fd/'+str(self.output.fileno()))).parent
                        if defect == 'extra':(stage/'unexpected').touch()
                        elif defect == 'missing':(stage/'uploads').rmdir()
                        else:os.chmod(stage/'generations',0o755)
                    return len(block)
            def open_file(fd,*args,**kwargs):
                output=original(fd,*args,**kwargs)
                return Writer(output) if args and args[0]=='wb' else output
            with self.subTest(defect=defect),patch('sv08_restore.os.fdopen',side_effect=open_file),\
                 self.assertRaisesRegex(ValueError,'Fresh state (readback|file metadata|directory metadata) mismatch|Unexpected fresh state entry|Incomplete fresh state layout'):
                self.restore.execute(plan)
            self.assertFalse((self.target/'sv08').exists())
            self.assertEqual((self.target/'keep').read_bytes(),b'keep')
        self.assertEqual(len(list(self.target.glob('.sv08-restore-*.partial'))),7)
        self.restore.execute(plan)
        self.assertEqual(Store(self.target/'sv08').load()['requested_mode'],'immutable')
    def test_exact_committed_history_fence_roundtrip_and_wrong_binding_refused(self):
        from sv08_admin_history import encode, digest
        from sv08_admin_jobs import Jobs
        history=self.source/'sv08/admin-image-jobs'; history.mkdir(mode=0o700)
        payload=encode([]); checksum=hashlib.sha256(payload).hexdigest()
        name='snapshot-'+checksum+'.json'
        (history/name).write_bytes(payload);os.chmod(history/name,0o600)
        manifest=dict(format_version=2,generation=1,parent_revision=None,active=dict(name=name,sha256=checksum,bytes=len(payload),count=0),archives=[],maintenance=None)
        (history/'jobs.json').write_bytes(encode(manifest));os.chmod(history/'jobs.json',0o600)
        (history/'ledger.lock').touch(mode=0o600);os.link(history/'ledger.lock',history/'history-format-v2.lock')
        expected=Jobs(history,'').view()['revision']
        self.archive=self.export();self.restore.archives['backup']['path']=self.archive
        result=self.restore.execute(self.plan()); restored=self.target/'data/sv08/admin-image-jobs'
        self.assertEqual((restored/'ledger.lock').stat().st_ino,(restored/'history-format-v2.lock').stat().st_ino)
        self.assertEqual(Jobs(restored,'').view()['revision'],expected)
        self.restore.targets['target']['root']=self.target/'bad-data'
        def change(entries):
            item,raw=entries[-1];value=json.loads(raw);value['history'][0]['revision']='f'*64
            raw=json.dumps(value).encode();item.size=len(raw);entries[-1]=(item,raw)
        self.rewrite(change)
        with self.assertRaisesRegex(ValueError,'committed binding'):self.restore.execute(self.plan())
        self.assertFalse((self.target/'bad-data').exists())
    def test_manifest_corruption_and_missing_duplicate_extra_members(self):
        mutations = [lambda es: es.pop(), lambda es: es.append(es[0]),
                     lambda es: es.__setitem__(-1,(es[-1][0],b'x'*len(es[-1][1]))),
                     lambda es: es.__setitem__(1,(es[1][0],b'X'*len(es[1][1])))]
        original = self.archive.read_bytes()
        for mutate in mutations:
            self.archive.write_bytes(original); self.rewrite(mutate)
            with self.assertRaises((ValueError,tarfile.TarError)): self.plan()
            self.assertFalse((self.target/'data').exists())
    def test_traversal_symlink_special_and_illegal_hardlink_or_mode_refused(self):
        original = self.archive.read_bytes()
        for kind in ('traversal','symlink','fifo','hardlink','mode'):
            self.archive.write_bytes(original)
            def change(es):
                item = es[0][0]
                if kind == 'traversal': item.name='data/../escape'
                elif kind == 'symlink': item.type=tarfile.SYMTYPE; item.linkname='/etc'
                elif kind == 'fifo': item.type=tarfile.FIFOTYPE
                elif kind == 'hardlink': item.type=tarfile.LNKTYPE; item.linkname='data/credentials'
                else: item.mode=0o4755
            self.rewrite(change)
            with self.assertRaises(ValueError): self.plan()
        self.assertFalse((self.root/'escape').exists())
    def test_truncated_missing_terminators_trailing_garbage(self):
        original = self.archive.read_bytes()
        for data in (original[:512], original[:len(original)-1024]+b'X'*1024):
            self.archive.write_bytes(data)
            with self.assertRaises((ValueError,tarfile.TarError)): self.plan()
    def test_payload_entry_space_and_inode_limits(self):
        self.restore.max_bytes = 1
        with self.assertRaisesRegex(ValueError,'bounds|bound'): self.plan()
        self.restore.max_bytes = 2**32-1; self.restore.max_entries=1
        with self.assertRaisesRegex(ValueError,'too many'): self.plan()
        self.restore.max_entries=100000
        for field,value in (('f_bavail',0),('f_favail',1)):
            real=os.statvfs(self.target)
            class FS: pass
            fs=FS()
            for name in ('f_flag','f_bavail','f_frsize','f_bsize','f_files','f_favail'):setattr(fs,name,getattr(real,name))
            setattr(fs,field,value)
            with patch('sv08_restore.os.fstatvfs',return_value=fs), self.assertRaisesRegex(ValueError,'space or inodes'): self.plan()
    def test_stale_archive_parent_identity_and_existing_no_replace(self):
        plan = self.plan(); self.archive.write_bytes(self.archive.read_bytes())
        with self.assertRaisesRegex(ValueError,'identity changed'): self.restore.execute(plan)
        self.assertFalse((self.target/'data').exists())
        plan = self.plan(); (self.target/'data').mkdir(); (self.target/'data/keep').write_bytes(b'old')
        with self.assertRaisesRegex(ValueError,'already exists'): self.restore.execute(plan)
        self.assertEqual((self.target/'data/keep').read_bytes(),b'old')
        (self.target/'data/keep').unlink(); (self.target/'data').rmdir()
        plan=self.plan(); self.target.rename(self.root/'old-target'); self.target.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError,'parent changed'): self.restore.execute(plan)
    def test_interruption_write_failure_and_publication_failure_leave_private_residue_only(self):
        plan=self.plan()
        for error in (OSError('storage write failure'),KeyboardInterrupt()):
            with patch('sv08_restore.scan',side_effect=error),self.assertRaises(type(error)): self.restore.execute(plan)
            self.assertFalse((self.target/'data').exists())
        self.assertEqual(len(list(self.target.glob('.sv08-restore-*.partial'))),2)
        with patch('sv08_restore.publish',side_effect=FileExistsError()),self.assertRaises(FileExistsError): self.restore.execute(plan)
        self.assertFalse((self.target/'data').exists()); self.assertEqual((self.target/'keep').read_bytes(),b'keep')
        self.restore.execute(plan)
        self.assertTrue((self.target/'data').is_dir())
    def test_silent_storage_corruption_is_detected_from_destination_readback(self):
        plan=self.plan();original=Path.open
        class CorruptWriter:
            def __init__(self,output):self.output=output
            def write(self,block):
                self.output.write(b'X'*len(block));return len(block)
            def __getattr__(self,name):return getattr(self.output,name)
        def open_file(path,*args,**kwargs):
            result=original(path,*args,**kwargs)
            return CorruptWriter(result) if args and args[0]=='xb' else result
        with patch.object(Path,'open',open_file),self.assertRaisesRegex(ValueError,'Staged restore checksum'):
            self.restore.execute(plan)
        self.assertFalse((self.target/'data').exists());self.assertEqual((self.target/'keep').read_bytes(),b'keep')
        self.assertEqual((self.source/'credentials').read_bytes(),b'fixture secret')
    def test_postpublication_guard_failure_withdraws_only_own_root(self):
        plan=self.plan()
        class FailGuard(Guard):
            count=0
            def recheck(self):
                self.count+=1
                if self.count == 3: raise ValueError('medium changed after publication')
        @contextmanager
        def fail(target): yield FailGuard()
        self.restore.admission=fail
        with self.assertRaisesRegex(ValueError,'after publication'):self.restore.execute(plan)
        self.assertFalse((self.target/'data').exists()); self.assertTrue(list(self.target.glob('.sv08-restore-*.partial')))
    def test_parent_substitution_at_publication_never_reports_replacement_root_or_touches_it(self):
        from sv08_export import publish
        plan=self.plan();old=self.root/'old-target';calls=[]
        def replace_parent(fd,partial,name):
            publish(fd,partial,name)
            if not calls:
                calls.append(True);self.target.rename(old);self.target.mkdir(mode=0o700)
                (self.target/'keep-new').write_bytes(b'new sibling')
        with patch('sv08_restore.publish',side_effect=replace_parent),self.assertRaises(OSError):self.restore.execute(plan)
        self.assertFalse((self.target/'data').exists());self.assertEqual((self.target/'keep-new').read_bytes(),b'new sibling')
        self.assertFalse((old/'data').exists());self.assertEqual((old/'keep').read_bytes(),b'keep')
        self.assertTrue(list(old.glob('.sv08-restore-*.partial')))
    def test_archive_and_target_links_refused_and_raw_paths_rejected(self):
        plan=self.plan(); linked=self.usb/'linked.tar'; linked.symlink_to(self.archive)
        self.restore.archives['backup']['path']=linked
        with self.assertRaises(OSError):self.plan()
        with self.assertRaises(ValueError):self.controller.plan('recovery.data-restore',dict(archive=str(self.archive),target='target'))
        self.restore.archives['backup']['path']=self.archive
        (self.target/'data').symlink_to(self.source)
        with self.assertRaisesRegex(ValueError,'already exists'):self.plan()


if __name__ == '__main__': unittest.main()
