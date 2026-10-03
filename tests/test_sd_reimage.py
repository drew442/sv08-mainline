"""Small disposable descriptor/I/O tests; never access production devices."""
import hashlib
import os
import stat
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime'))
import sv08_sd_reimage as M


class Reimage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.target = self.root/'image', self.root/'target'
        self.data = b'new image data'*1000
        self.source.write_bytes(self.data)
        self.old = b'x'*(len(self.data)+1024)
        self.target.write_bytes(self.old)
        self.cfg = dict(source=str(self.source), target=str(self.target), size=len(self.data),
                        sha256=hashlib.sha256(self.data).hexdigest())

    def session(self, admission=None):
        session = M.Session(self.cfg, admission or M.FileFixtureAdmission())
        self.addCleanup(session.close)
        return session

    def test_no_absent_and_relaunch(self):
        for answer in (False, None, 'yes'):
            self.session().apply(answer)
            self.assertEqual(self.target.read_bytes(), self.old)
        self.session().close()  # closed review without any answer
        self.assertEqual(self.target.read_bytes(), self.old)

    def test_yes_short_write_readback_and_duplicate(self):
        session = self.session()
        write = os.pwrite
        with patch.object(M, 'BUFFER', 4096), patch.object(M.os, 'pwrite', side_effect=lambda fd, data, offset: write(fd, data[:31], offset)):
            self.assertIn('readback matched', session.apply(True))
        self.assertEqual(self.target.read_bytes(), self.data+self.old[len(self.data):])
        with self.assertRaisesRegex(ValueError, 'already answered'): session.apply(True)
        self.session().apply(False)
        self.assertEqual(self.target.read_bytes(), self.data+self.old[len(self.data):])

    def test_production_rejects_regular_target(self):
        with self.assertRaisesRegex(ValueError, 'block target'): M.Session(self.cfg)
        self.assertEqual(self.target.read_bytes(), self.old)

    def test_invalid_source_capacity_and_hash(self):
        for change, reason in (({'size':0}, 'positive'), ({'size':len(self.data)+1}, 'wrong size'),
                               ({'sha256':'0'*64}, 'checksum'), ({'target':str(self.source)}, 'Source on target')):
            with self.assertRaisesRegex(ValueError, reason):
                M.Session(dict(self.cfg, **change), M.FileFixtureAdmission())
        self.target.write_bytes(b'x')
        with self.assertRaisesRegex(ValueError, 'capacity'): self.session()

    def test_stale_target_and_source(self):
        session = self.session()
        self.target.rename(self.root/'old'); self.target.write_bytes(self.old)
        with self.assertRaisesRegex(ValueError, 'Stale fixture'): session.apply(True)
        self.assertEqual((self.root/'old').read_bytes(), self.old)
        self.assertEqual(self.target.read_bytes(), self.old)
        session = self.session()
        self.source.unlink(); self.source.write_bytes(self.data)
        with self.assertRaisesRegex(ValueError, 'stale'): session.apply(True)
        self.assertEqual(self.target.read_bytes(), self.old)

    def test_changed_in_use_and_source_independence(self):
        class Admission(M.FileFixtureAdmission):
            refusal = None
            def check(inner, *args):
                super().check(*args)
                if inner.refusal: raise ValueError(inner.refusal)
        for reason in ('Target mounted/in use', 'Source on target'):
            admission = Admission(); session = self.session(admission)
            admission.refusal = reason
            with self.assertRaisesRegex(ValueError, reason): session.apply(True)
            self.assertEqual(self.target.read_bytes(), self.old)

    def test_changed_source_during_transfer_never_success(self):
        for truncate in (True, False):
            self.source.write_bytes(self.data)
            session = self.session()
            read = os.pread
            def changed(fd, size, offset):
                if fd == session.source:
                    if truncate: self.source.write_bytes(b'')
                    else: self.source.write_bytes(b'z'*len(self.data))
                return read(fd, size, offset)
            with patch.object(M.os, 'pread', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'unusable'): session.apply(True)

    def test_io_flush_cache_readback_failures(self):
        for function in ('pwrite', 'fsync', 'posix_fadvise'):
            session = self.session()
            with patch.object(M.os, function, side_effect=OSError(function+' failure')):
                with self.assertRaisesRegex(ValueError, 'unusable'): session.apply(True)
        session = self.session()
        with patch.object(M, 'digest', return_value='0'*64):
            with self.assertRaisesRegex(ValueError, 'readback'): session.apply(True)

    def test_serialized(self):
        self.session()
        with self.assertRaises(BlockingIOError): self.session()

    def test_linux_storage_ancestry(self):
        sysroot = self.root/'sys'; proc = self.root/'proc'
        (sysroot/'dev/block').mkdir(parents=True); proc.mkdir()
        disk = sysroot/'devices/mmcblk0'; disk.mkdir(parents=True)
        part = disk/'mmcblk0p1'; part.mkdir(); (part/'partition').write_text('1')
        (sysroot/'dev/block/179:0').symlink_to(disk)
        (sysroot/'dev/block/179:1').symlink_to(part)
        dm = sysroot/'devices/dm-0'; (dm/'slaves').mkdir(parents=True)
        (part/'dev').write_text('179:1'); (dm/'slaves/mmcblk0p1').symlink_to(part)
        (sysroot/'dev/block/253:0').symlink_to(dm)
        admission = M.LinuxAdmission(sysroot, proc)
        self.assertTrue(admission.depends('179:1', disk))
        self.assertTrue(admission.depends('253:0', disk))
        self.assertFalse(admission.depends('0:44', disk))
        with self.assertRaisesRegex(ValueError, 'Unknown'): admission.depends('8:99', disk)

    def test_linux_identity_unused_readonly_recheck(self):
        # Synthetic sysfs/proc only: no physical identities or device opens.
        sysroot, proc = self.root/'sys', self.root/'proc'
        (sysroot/'dev/block').mkdir(parents=True)
        (sysroot/'class/block').mkdir(parents=True)
        (proc/'self').mkdir(parents=True)
        node = sysroot/'devices/mmcblk0'; node.mkdir(parents=True)
        card = sysroot/'devices/controller/card'; card.mkdir(parents=True)
        (card/'type').write_text('MMC'); (card/'cid').write_text('synthetic-cid')
        (node/'device').symlink_to(card)
        (sysroot/'dev/block/179:0').symlink_to(node)
        (sysroot/'class/block/mmcblk0').symlink_to(node)
        marker = self.root/'gate'; marker.write_text('fixture')
        admission = M.LinuxAdmission(sysroot, proc, marker)
        cfg = dict(self.cfg, dev_t='179:0', controller=str(card.parent), cid='synthetic-cid')
        source_stat = type('S', (), dict(st_dev=os.makedev(0,42)))()
        target_stat = type('T', (), dict(st_mode=stat.S_IFBLK, st_rdev=os.makedev(179,0)))()
        (proc/'self/mountinfo').write_text(f'1 0 0:42 / {self.root} ro - nfs source ro\n')
        (proc/'swaps').write_text('Filename Type Size Used Priority\n')
        real_stat = os.stat
        with patch.object(M.os, 'fstat', side_effect=lambda fd: source_stat if fd == 10 else target_stat), \
             patch.object(M.os, 'stat', side_effect=lambda path, *args, **kwargs: target_stat if str(path) == cfg['target'] else real_stat(path, *args, **kwargs)), \
             patch.object(M.fcntl, 'ioctl', return_value=(len(self.data)+1024).to_bytes(8,'little')):
            admission.check(cfg,10,11)
            with self.assertRaisesRegex(ValueError,'CID'): admission.check(dict(cfg,cid='other'),10,11)
            with self.assertRaisesRegex(ValueError,'dev_t'): admission.check(dict(cfg,dev_t='179:1'),10,11)
            (proc/'self/mountinfo').write_text(f'1 0 0:42 / {self.root} rw - nfs source rw\n')
            with self.assertRaisesRegex(ValueError,'read-only'): admission.check(cfg,10,11)
            (proc/'self/mountinfo').write_text(f'1 0 0:42 / {self.root} ro - nfs source ro\n2 0 179:0 / /target ro - ext4 target ro\n')
            with self.assertRaisesRegex(ValueError,'mounted'): admission.check(cfg,10,11)
            (proc/'self/mountinfo').write_text(f'1 0 0:42 / {self.root} ro - nfs source ro\n')
            (node/'holders').mkdir(); (node/'holders/held').write_text('fixture')
            with self.assertRaisesRegex(ValueError,'held'): admission.check(cfg,10,11)
            (node/'holders/held').unlink()
            with patch.object(M.fcntl,'ioctl',return_value=(1).to_bytes(8,'little')):
                with self.assertRaisesRegex(ValueError,'capacity'): admission.check(cfg,10,11)
            (node/'partition').write_text('1')
            with self.assertRaisesRegex(ValueError,'Whole'): admission.check(cfg,10,11)


if __name__ == '__main__': unittest.main()
