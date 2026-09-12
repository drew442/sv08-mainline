import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from cockpit_fixture import boot, prepare


class FixtureTargetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name); self.work.chmod(0o700)
        artifact = self.work / 'kernel'; artifact.write_bytes(b'fixture')
        reference = dict(path=str(artifact), sha256=hashlib.sha256(b'fixture').hexdigest())
        self.report = dict(deployable=False, kernel=reference, initrd=reference, image_sha256='0'*64)
        (self.work / 'prepare.json').write_text(json.dumps(self.report))
        self.args = SimpleNamespace(work=self.work, execute=False)

    def test_symlink_image_is_refused_before_opening_target(self):
        (self.work / 'guest.ext4').symlink_to('/dev/null')
        with self.assertRaisesRegex(ValueError, 'private owned regular'): boot(self.args)

    def test_shared_and_wrong_size_images_are_refused(self):
        image = self.work / 'guest.ext4'; image.write_bytes(b'not an image')
        with self.assertRaisesRegex(ValueError, 'private owned regular'): boot(self.args)
        image.unlink(); image.hardlink_to(self.work / 'kernel')
        with self.assertRaisesRegex(ValueError, 'private owned regular'): boot(self.args)

    def test_shared_output_and_changed_boot_artifact_are_refused(self):
        image = self.work / 'guest.ext4'
        with image.open('wb') as stream: stream.truncate(2 * 1024**3)
        self.work.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private owned regular'): boot(self.args)
        self.work.chmod(0o700); (self.work / 'kernel').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Boot artifact changed'): boot(self.args)


class FixtureSourceTests(unittest.TestCase):
    def test_nested_output_is_refused_before_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary); baseline = parent / 'baseline'; baseline.mkdir()
            intake = parent / 'intake'; intake.mkdir()
            for source in (baseline, intake):
                output = source / 'new-output'
                args = SimpleNamespace(baseline=baseline, intake=intake, work=output, execute=False)
                with self.assertRaisesRegex(ValueError, 'overlap'): prepare(args)
                self.assertFalse(output.exists())
