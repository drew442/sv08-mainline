import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import unittest
from cockpit_fixture import boot, prepare, writable_fixture_paths, DATA_IMAGE_BYTES, fixture_read_access


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


class FixtureWritableTests(unittest.TestCase):
    def test_capacity_covers_boot_and_full_save_admission(self):
        from sv08_data_budget import Budget
        # Saving reserves a full256MiB copy above the768MiB floor, plus journal
        # headroom; boot alone does not exercise this stronger requirement.
        budget=Budget('/unused')
        def filesystem(size):
            return SimpleNamespace(f_frsize=4096,f_bsize=4096,
                f_bavail=int(size*.90)//4096,f_favail=100000)
        with self.assertRaisesRegex(ValueError,'Insufficient shared data'):
            budget.check(256*1024**2,128,fs=filesystem(1024**3))
        admitted=budget.check(256*1024**2,128,fs=filesystem(DATA_IMAGE_BYTES))
        self.assertLess(admitted['required_bytes'],DATA_IMAGE_BYTES*.90)
        self.assertLessEqual(DATA_IMAGE_BYTES,2*1024**3)

    def test_packaged_service_paths_are_guest_only_writable_mounts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'etc').mkdir()
            fstab=root/'etc/fstab';fstab.write_text('tmpfs /tmp tmpfs mode=1777 0 0\n')
            writable_fixture_paths(root)
            self.assertTrue(fstab.read_text().startswith('tmpfs /tmp tmpfs mode=1777 0 0\n'))
            rows=[line.split() for line in fstab.read_text().splitlines() if line.startswith('tmpfs ')]
            for target,size,mode in [('/var/lib/systemd','16M',0o755),('/var/tmp','32M',0o1777)]:
                row=next(r for r in rows if r[1]==target)
                self.assertEqual(row[2],'tmpfs')
                self.assertIn('size='+size,row[3]);self.assertIn('mode='+format(mode,'04o'),row[3])
                self.assertEqual((root/target.lstrip('/')).stat().st_mode & 0o7777,mode)


class FixtureReadAccessTests(unittest.TestCase):
    def test_synthetic_accounts_get_only_finite_helper_without_changing_production_rule(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);directory=root/'etc/sudoers.d';directory.mkdir(parents=True)
            from cockpit_fixture import REPO
            production=(REPO/'configs/host-os/sv08-view-sudoers').read_bytes()
            (directory/'sv08-view').write_bytes(production)
            (root/'etc/hosts').write_text('127.0.0.1 localhost\n')
            fixture_read_access(root)
            self.assertEqual((directory/'sv08-view').read_bytes(),production)
            fixture=directory/'cockpit-fixture-view'
            grants=[line for line in fixture.read_text().splitlines() if not line.startswith('#')]
            self.assertEqual(grants,[name+' ALL=(root) NOPASSWD: /usr/bin/python3 -I /usr/lib/sv08/sv08_view.py' for name in ('fixtureadmin','fixtureordinary')])
            self.assertEqual(fixture.stat().st_mode & 0o7777,0o440)
            self.assertEqual((root/'etc/hosts').read_text(),'127.0.0.1 localhost\n\n127.0.1.1 sv08-cockpit-fixture\n')
