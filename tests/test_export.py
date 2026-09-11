from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_export import Export, ExportAdapter, publish
from sv08_recovery import RecoveryController
from sv08_state import Store


class ExportTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.source=self.root/'source';self.source.mkdir()
        self.target=self.root/'usb';self.target.mkdir()
        (self.source/'state.json').write_text('damaged registry')
        (self.source/'config').mkdir();(self.source/'config/printer.cfg').write_text('private configuration')
        self.depth=0
        @contextmanager
        def admission(target):
            self.assertEqual(target,'usb-1');self.assertEqual(self.depth,0)
            self.depth+=1
            try:yield
            finally:self.depth-=1
        self.export=Export(self.source,{'usb-1':{'path':self.target,'label':'Test USB'}},admission,reserve_bytes=0)

    def test_real_archive_readback_and_corrupt_registry_preserved(self):
        before={str(p.relative_to(self.source)):p.read_bytes() for p in self.source.rglob('*') if p.is_file()}
        plan=self.export.prepare('usb-1');self.assertEqual(list(self.target.iterdir()),[])
        result=self.export.execute(plan)
        path=self.target/result['filename']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),result['sha256'])
        with tarfile.open(path) as archive:
            self.assertEqual(archive.extractfile('data/state.json').read(),b'damaged registry')
            self.assertEqual(archive.extractfile('data/config/printer.cfg').read(),b'private configuration')
            manifest=json.load(archive.extractfile('export-manifest.json'))
            self.assertEqual(len(manifest['files']),2)
        self.assertEqual(before,{str(p.relative_to(self.source)):p.read_bytes() for p in self.source.rglob('*') if p.is_file()})
        self.assertEqual(self.depth,0)

    def test_controller_review_and_apply_creates_a_real_archive(self):
        controller=RecoveryController(Store(self.source),ExportAdapter(self.export))
        self.assertTrue(controller.status()['capabilities']['recovery.export']['available'])
        plan=controller.plan('recovery.export',{'destination':'usb-1'})
        self.assertIn('private configuration',plan['effect'])
        self.assertEqual(plan['export']['label'],'Test USB')
        self.assertEqual(list(self.target.iterdir()),[])
        result=controller.apply(plan)
        self.assertTrue((self.target/result['filename']).is_file())
        with self.assertRaises(ValueError):controller.plan('recovery.boot',{'slot':'A'})

    def test_no_replace_publication_preserves_existing_output(self):
        (self.target/'partial').write_bytes(b'new')
        (self.target/'existing').write_bytes(b'keep')
        fd=os.open(self.target,os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaises(FileExistsError):publish(fd,'partial','existing')
        finally:os.close(fd)
        self.assertEqual((self.target/'existing').read_bytes(),b'keep')

    def test_preexisting_partial_is_not_removed_after_creation_collision(self):
        existing=self.target/'.sv08-user-data-collision.tar.partial'
        existing.write_bytes(b'previous interrupted export')
        plan=self.export.prepare('usb-1')
        with patch('sv08_export.uuid.uuid4',return_value=SimpleNamespace(hex='collision')):
            with self.assertRaises(FileExistsError):self.export.execute(plan)
        self.assertEqual(existing.read_bytes(),b'previous interrupted export')

    def test_source_change_and_destination_replacement_refused(self):
        plan=self.export.prepare('usb-1');(self.source/'state.json').write_text('changed')
        with self.assertRaisesRegex(ValueError,'changed'):self.export.execute(plan)
        plan=self.export.prepare('usb-1');self.target.rename(self.root/'previous-usb');self.target.mkdir()
        with self.assertRaisesRegex(ValueError,'changed'):self.export.execute(plan)
        self.assertEqual(list(self.target.iterdir()),[])

    def test_links_special_files_and_overlapping_destination_refused(self):
        for make in (lambda p:p.symlink_to('/etc/passwd'),lambda p:os.mkfifo(p)):
            path=self.source/'unsupported';make(path)
            with self.assertRaises(ValueError):self.export.prepare('usb-1')
            path.unlink()
        self.export.targets['usb-1']['path']=self.source/'export'
        with self.assertRaisesRegex(ValueError,'overlap'):self.export.prepare('usb-1')

    def test_short_space_and_size_limit_refused_before_writing(self):
        fs=SimpleNamespace(f_bavail=0,f_frsize=4096,f_bsize=4096,f_favail=1000,f_files=1000)
        with patch('sv08_export.os.fstatvfs',return_value=fs):
            with self.assertRaisesRegex(ValueError,'space'):self.export.prepare('usb-1')
        self.export.max_archive_bytes=10240
        with self.assertRaisesRegex(ValueError,'file-size'):self.export.prepare('usb-1')
        self.assertEqual(list(self.target.iterdir()),[])

    def test_readback_failure_never_publishes_complete_archive(self):
        plan=self.export.prepare('usb-1')
        with patch('sv08_export.verify_archive',side_effect=ValueError('readback failed')):
            with self.assertRaisesRegex(ValueError,'readback'):self.export.execute(plan)
        self.assertEqual(list(self.target.iterdir()),[])
        self.assertEqual(self.depth,0)

    def test_source_mutation_during_copy_never_publishes(self):
        from sv08_export import HashReader
        plan=self.export.prepare('usb-1');original=HashReader.read
        def changed(reader,size):
            data=original(reader,size)
            (self.source/'state.json').write_text('changed while copying')
            return data
        with patch.object(HashReader,'read',changed):
            with self.assertRaisesRegex(ValueError,'changed'):self.export.execute(plan)
        self.assertEqual(list(self.target.iterdir()),[])

    def test_fat_without_inode_accounting_and_counted_inode_exhaustion(self):
        available=SimpleNamespace(f_bavail=100000,f_frsize=4096,f_bsize=4096,f_favail=0,f_files=0)
        with patch('sv08_export.os.fstatvfs',return_value=available):self.export.prepare('usb-1')
        available.f_files=100000
        with patch('sv08_export.os.fstatvfs',return_value=available):
            with self.assertRaisesRegex(ValueError,'inodes'):self.export.prepare('usb-1')

    def test_sparse_file_expansion_and_long_unicode_paths_are_budgeted(self):
        path=self.source/('é'*80);path.mkdir()
        with (path/'sparse').open('wb') as stream:stream.truncate(1024*1024)
        plan=self.export.prepare('usb-1');result=self.export.execute(plan)
        self.assertLessEqual((self.target/result['filename']).stat().st_size,plan['required_bytes'])

    def test_snapshot_keeps_sqlite_database_and_committed_wal(self):
        path=self.source/'database.sqlite'
        with sqlite3.connect(path) as connection:
            connection.execute('PRAGMA journal_mode=WAL');connection.execute('create table t(value)')
            connection.execute("insert into t values ('preserved')");connection.commit()
            result=self.export.execute(self.export.prepare('usb-1'))
            # Restore only these fixed names into a disposable test directory.
            restore=self.root/'restored';restore.mkdir()
            with tarfile.open(self.target/result['filename']) as archive:
                for name in ('database.sqlite','database.sqlite-wal'):
                    (restore/name).write_bytes(archive.extractfile('data/'+name).read())
            with sqlite3.connect(restore/'database.sqlite') as recovered:
                self.assertEqual(recovered.execute('select value from t').fetchone(),('preserved',))
