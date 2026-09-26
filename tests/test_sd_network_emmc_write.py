"""Offline admission and failure tests for the disposable QEMU writer."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'tests/fixtures/sd-network-root/emmc_image_writer.c'
SPEC = importlib.util.spec_from_file_location(
    'host_qemu_sd_network_emmc_write', REPO / 'tests/host_qemu_sd_network_emmc_write.py')
writer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(writer)


class WriterAdmissionTests(unittest.TestCase):
    def test_fresh_work_rejects_alias_and_existing_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            existing = base / 'existing'
            existing.mkdir()
            with self.assertRaisesRegex(ValueError, 'Fresh'):
                writer.fresh_work(existing)
            alias = base / 'alias'
            alias.symlink_to(existing)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                writer.fresh_work(alias)

    def test_host_rejects_block_like_paths_and_outside_assignment(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'regular'):
                writer.secure_path('/dev/null')
            outside = base / 'outside.img'
            outside.write_bytes(b'x')
            sub = base / 'assigned'
            sub.mkdir()
            with self.assertRaisesRegex(ValueError, 'outside'):
                writer.secure_path(outside, parent=sub)
            link = sub / 'link.img'
            link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                writer.secure_path(link, parent=sub)

    def test_target_identity_size_overlap_substitution_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            source = work / 'source.img'
            source.write_bytes(b's')
            with mock.patch.object(writer, 'TARGET_BYTES', 1024):
                fd = writer.create_target(work / 'target.img')
                try:
                    self.assertEqual(writer.admit_target(work, fd, source), work / 'target.img')
                    (work / 'target-extra.img').write_bytes(b'x')
                    with self.assertRaisesRegex(ValueError, 'Ambiguous'):
                        writer.admit_target(work, fd, source)
                    (work / 'target-extra.img').unlink()
                    os.ftruncate(fd, 100)
                    with self.assertRaisesRegex(ValueError, 'undersized'):
                        writer.admit_target(work, fd, source)
                    os.ftruncate(fd, 1024)
                    (work / 'target.img').rename(work / 'old-target.img')
                    (work / 'target.img').write_bytes(b'x' * 1024)
                    with self.assertRaisesRegex(ValueError, 'substituted'):
                        writer.admit_target(work, fd, source)
                finally:
                    os.close(fd)
            (work / 'target.img').unlink()
            os.link(source, work / 'target.img')
            fd = os.open(work / 'target.img', os.O_RDWR | os.O_NOFOLLOW)
            try:
                with mock.patch.object(writer, 'TARGET_BYTES', 1):
                    with self.assertRaisesRegex(ValueError, 'overlapping'):
                        writer.admit_target(work, fd, source)
            finally:
                os.close(fd)

    def test_missing_truncated_changed_source_and_both_gpt_copies(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source.img'
            with self.assertRaises(FileNotFoundError):
                writer.validate_source(source)
            source.write_bytes(b'truncated')
            with self.assertRaisesRegex(ValueError, 'truncated'):
                writer.validate_source(source)
            source.unlink()
            self.assertEqual(writer.create_synthetic_source(source), writer.IMAGE_SHA256)
            self.assertEqual(writer.validate_source(source), source)
            fd = os.open(source, os.O_RDWR)
            try:
                for offset in (512, writer.IMAGE_BYTES - 512):
                    original = os.pread(fd, 1, offset)
                    os.pwrite(fd, bytes([original[0] ^ 1]), offset)
                    with self.assertRaisesRegex(ValueError, 'GPT'):
                        writer.inspect_gpt(source)
                    os.pwrite(fd, original, offset)
                os.pwrite(fd, b'X', 8192)
                with self.assertRaisesRegex(ValueError, 'changed'):
                    writer.validate_source(source)
            finally:
                os.close(fd)

    def test_failure_cannot_produce_success_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'fresh'

            def source(path):
                path.write_bytes(b'source')
                return writer.IMAGE_SHA256

            def uncertain(*args):
                os.write(args[3], b'partly written')
                raise OSError('injected first-write failure')

            with (mock.patch.object(writer, 'verify_inputs', return_value='root=/dev/nfs ro'),
                  mock.patch.object(writer, 'create_synthetic_source', side_effect=source),
                  mock.patch.object(writer, 'validate_source'),
                  mock.patch.object(writer, 'TARGET_BYTES', 1024),
                  mock.patch.object(writer, 'execute', side_effect=uncertain),
                  mock.patch('sys.argv', ['writer', '--work', str(work), '--sd-work',
                                          str(Path(temporary) / 'sd'), '--package-root',
                                          str(Path(temporary) / 'packages'), '--execute'])):
                with self.assertRaisesRegex(OSError, 'first-write'):
                    writer.main()
            self.assertTrue((work / 'FAILED').exists())
            self.assertFalse((work / 'result.json').exists())
            self.assertEqual((work / 'target.img').read_bytes()[:14], b'partly written')

    def test_host_readback_failure_has_no_success_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'fresh'

            def source(path):
                path.write_bytes(b'source')
                return writer.IMAGE_SHA256

            with (mock.patch.object(writer, 'verify_inputs', return_value='root=/dev/nfs ro'),
                  mock.patch.object(writer, 'create_synthetic_source', side_effect=source),
                  mock.patch.object(writer, 'validate_source'),
                  mock.patch.object(writer, 'TARGET_BYTES', 1024),
                  mock.patch.object(writer, 'execute'),
                  mock.patch.object(writer, 'digest', side_effect=OSError('readback I/O error')),
                  mock.patch('sys.argv', ['writer', '--work', str(work), '--sd-work',
                                          str(Path(temporary) / 'sd'), '--package-root',
                                          str(Path(temporary) / 'packages'), '--execute'])):
                with self.assertRaisesRegex(OSError, 'readback'):
                    writer.main()
            self.assertTrue((work / 'FAILED').exists())
            self.assertFalse((work / 'result.json').exists())

    def test_guest_identity_and_root_refusals_precede_target_open(self):
        source = SOURCE.read_text()
        gate = source.index('if(!exact_usb_serial()')
        target_open = source.index('out=open(target,O_RDWR')
        self.assertLess(source.index('sv08.qemu_reimage=1'), target_open)
        self.assertLess(source.index('mounted("/","nfs","ro")'), target_open)
        self.assertLess(gate, target_open)
        self.assertIn('access("/sys/block/sdb",F_OK)', source)
        self.assertIn('target="/dev/sda"', source)
        self.assertIn('capacity!=TARGET_BYTES', source)
        self.assertIn('S_ISBLK(ts.st_mode)', source)
        self.assertIn('SV08_QEMU_REIMAGE_TEST_ONLY', source)
        self.assertIn('finish("REFUSED_TARGET_ID")', source)
        self.assertIn('finish("REFUSED_INPUT")', source)

    def test_timeout_and_flush_failure_never_mark_guest_success(self):
        source = SOURCE.read_text()
        self.assertIn('expired(started)||!exact_read(in,n)', source)
        self.assertIn('expired(started)||!exact_read(out,n)', source)
        self.assertIn('if(fsync(out)||ioctl(out,BLKFLSBUF,0)', source)
        self.assertLess(source.index('finish("FAILED_FLUSH")'), source.index('finish("PASS")'))
        self.assertLess(source.index('finish("FAILED_READBACK_HASH")'),
                        source.index('finish("PASS")'))


@unittest.skipUnless(shutil.which('cc'), 'native C compiler unavailable')
class WriterNativeFailureTests(unittest.TestCase):
    def compile_run(self, definition):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / 'writer-test'
            subprocess.run(['cc', '-O2', '-D_FORTIFY_SOURCE=2', '-Wall', '-Wextra',
                            '-Wno-unused-function',
                            f'-D{definition}', str(SOURCE), '-o', str(executable)], check=True)
            return subprocess.check_output([str(executable)], text=True).strip()

    def test_sha256_known_vector(self):
        self.assertEqual(self.compile_run('SV08_SHA_SELFTEST'),
                         'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_short_read_write_and_flush_fail_closed(self):
        self.assertEqual(self.compile_run('SV08_IO_SELFTEST'),
                         'short-read short-write flush-failure timeout rw-proto refused')


if __name__ == '__main__':
    unittest.main()
