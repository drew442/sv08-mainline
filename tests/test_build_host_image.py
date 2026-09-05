"""Offline safety and layout tests; full-image checks are integration evidence."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('image_builder', REPO / 'scripts/build_host_image.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ImageBuilderTests(unittest.TestCase):
    def test_layout_rejects_overlap_and_misalignment(self):
        c = json.loads((REPO / 'configs/images/test-sv08-01-host.json').read_text())
        boot, root, size = builder.layout(c)
        self.assertEqual(root + size, 8 * 1024**3)
        self.assertEqual(root - boot, 256 * 1024**2)
        for changes in ({'root_start_sector': 8192}, {'image_bytes': 8589934593},
                        {'boot_start_sector': 0}, {'image_bytes': 1024}):
            with self.assertRaises(ValueError):
                builder.layout(dict(c, **changes))

    def test_regular_rejects_device_and_link(self):
        with self.assertRaises(ValueError):
            builder.regular('/dev/null')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'link'
            p.symlink_to('/etc/hosts')
            with self.assertRaises(ValueError):
                builder.regular(p)

    def test_support_unpack_rejects_traversal_and_ignores_links(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            archive = base / 'input.tar'
            with tarfile.open(archive, 'w') as t:
                link = tarfile.TarInfo('lib/modules/link')
                link.type = tarfile.SYMTYPE
                link.linkname = '/etc/passwd'
                t.addfile(link)
                bad = tarfile.TarInfo('boot/../../escape')
                bad.size = 1
                t.addfile(bad, io.BytesIO(b'x'))
            with self.assertRaises(ValueError):
                builder.unpack_support(archive, base / 'out')
            self.assertFalse((base / 'out/lib/modules/link').exists())
            self.assertFalse((base / 'escape').exists())

    def test_plan_does_not_create_work_or_image(self):
        work = REPO / 'build/test-plan-must-not-exist'
        output = REPO / 'artifacts/test-plan-must-not-exist.img'
        self.assertFalse(work.exists())
        self.assertFalse(output.exists())
        proc = subprocess.run([sys.executable, str(REPO / 'scripts/build_host_image.py'),
                               '--stage', 'assemble', '--work', str(work),
                               '--output', str(output)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(work.exists())
        self.assertFalse(output.exists())

    def test_rejects_output_device_before_execution(self):
        proc = subprocess.run([sys.executable, str(REPO / 'scripts/build_host_image.py'),
                               '--stage', 'assemble', '--work', str(REPO / 'build/test-plan'),
                               '--output', '/dev/null'], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)


if __name__ == '__main__':
    unittest.main()
