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


class RaucPackagePatches(unittest.TestCase):
    def config(self):
        return json.loads((REPO / 'configs/host-os/rauc-package.json').read_text())

    def test_pinned_patch_is_verified(self):
        from package_rauc import verify_patches
        config = self.config()
        self.assertEqual(verify_patches(config), config['patches'])
        self.assertEqual(config['version'], '1.15.2-0sv08.2')

    def test_missing_unknown_duplicate_and_changed_patch_are_rejected(self):
        from copy import deepcopy
        from package_rauc import verify_patches
        config = self.config()
        for patches in ([], [{'path': '../outside', 'sha256': '0'*64}], config['patches']*2):
            candidate = deepcopy(config)
            candidate['patches'] = patches
            with self.assertRaisesRegex(ValueError, 'identity'):
                verify_patches(candidate)
        config['patches'][0]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'hash'):
            verify_patches(config)

    def test_bad_patch_hash_stops_before_application(self):
        from unittest.mock import patch
        from package_rauc import apply_patches
        config = self.config()
        config['patches'][0]['sha256'] = '0'*64
        with patch('package_rauc.subprocess.run') as run:
            with self.assertRaisesRegex(ValueError, 'hash'):
                apply_patches(config, Path('/disposable/source'), None)
            run.assert_not_called()

    def test_symlink_patch_is_rejected(self):
        from unittest.mock import patch
        from package_rauc import verify_patches
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / self.config()['patches'][0]['path']
            target.parent.mkdir(parents=True)
            target.symlink_to(REPO / self.config()['patches'][0]['path'])
            with patch('package_rauc.REPO', root):
                with self.assertRaisesRegex(ValueError, 'hash'):
                    verify_patches(self.config())
