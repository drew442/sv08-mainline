import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_rauc import REPO, verify


class RaucPackageInputs(unittest.TestCase):
    def test_unreviewed_source_and_wrong_hash_are_rejected(self):
        config = json.loads((REPO / 'configs/host-os/rauc-package.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'source.tar.gz'
            archive.write_bytes(b'not the pinned source archive')
            with self.assertRaisesRegex(ValueError, 'hash'):
                verify(config, archive)
            config['source']['commit'] = '0' * 40
            with self.assertRaisesRegex(ValueError, 'identity'):
                verify(config, archive)
