import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
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

    def table(self, relocated=False):
        args = ['sgdisk', '--clear']
        if relocated:
            args.append('--move-main-table=4096')
        args += ['--new=1:8192:16383', str(self.image)]
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
