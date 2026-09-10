import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
import stat
from types import SimpleNamespace
from unittest.mock import patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_gpt_layout import inspect


@unittest.skipUnless(shutil.which('sgdisk'), 'requires GPT fdisk')
class GPTTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.image = Path(t.name) / 'test.img'
        with self.image.open('wb') as f:
            f.truncate(16 * 1024 * 1024)

    def table(self, relocated=False, start=8192):
        args = ['sgdisk', '--clear']
        if relocated:
            args.append('--move-main-table=4096')
        args += [f'--new=1:{start}:{start+8191}', str(self.image)]
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def test_standard_gpt_conflicts_with_spl(self):
        self.table()
        with self.assertRaisesRegex(ValueError, 'SPL reservation overlaps'):
            inspect(self.image)

    def test_relocated_arrays_preserve_spl_space(self):
        self.table(True)
        self.assertTrue(inspect(self.image)['collision_free'])

    def test_corruption_rejected(self):
        self.table(True)
        with self.image.open('r+b') as f:
            f.seek(4096 * 512 + 80)
            f.write(b'corruption')
        with self.assertRaisesRegex(ValueError, 'CRC mismatch'):
            inspect(self.image)

    def test_redundant_environment_cannot_overlap_reserved_storage(self):
        with self.image.open('r+b') as stream:
            stream.truncate(32 * 1024 * 1024)
        self.table(True, start=32768)
        valid = [(4*1024*1024, 65536), (8*1024*1024, 65536)]
        self.assertTrue(inspect(self.image, environment_regions=valid)['collision_free'])
        for invalid in ([(0,512)], [(8192,65536)], [(2*1024*1024,65536)],
                        [valid[0], (valid[0][0]+512,65536)],
                        [(16*1024*1024,65536)], [(4194305,65536)]):
            with self.subTest(regions=invalid), self.assertRaises(ValueError):
                inspect(self.image, environment_regions=invalid)

    def test_block_audit_requires_explicit_footprint_and_is_read_only(self):
        self.table(True)
        before = self.image.read_bytes()
        with patch.object(Path, 'stat', return_value=SimpleNamespace(st_mode=stat.S_IFBLK)):
            with self.assertRaises(ValueError): inspect(self.image)
            with self.assertRaises(ValueError): inspect(self.image, allow_block=True)
            self.assertTrue(inspect(self.image, allow_block=True, image_bytes=len(before))['collision_free'])
        self.assertEqual(self.image.read_bytes(), before)
