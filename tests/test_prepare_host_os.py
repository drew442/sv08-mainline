import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_host_os', REPO / 'scripts/prepare_host_os.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HostBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (REPO / "build").mkdir(exist_ok=True)

    def setUp(self):
        self.c = json.loads((REPO / 'configs/images/host-ab.json').read_text())

    def test_factory_capacity_and_boot_gap(self):
        parts = m.layout(self.c)
        self.assertEqual(parts[0]['offset_bytes'], 16 * m.MIB)
        for a, b in zip(parts, parts[1:]):
            self.assertEqual(a['offset_bytes'] + a['size_bytes'], b['offset_bytes'])
        self.assertEqual(parts[-1]['offset_bytes'] + parts[-1]['size_bytes'] + m.MIB,
                         7818182656)

    def test_oversized_and_asymmetric_slots_rejected(self):
        for delta in [1, -1]:
            c = copy.deepcopy(self.c)
            c['partitions'][1]['mib'] += delta
            c['partitions'][-1]['mib'] -= delta
            with self.assertRaises(ValueError):
                m.layout(c)
        self.c['partitions'][-1]['mib'] += 1
        with self.assertRaises(ValueError):
            m.layout(self.c)

    def test_invalid_inputs_rejected(self):
        for key, value in [('snapshot', 'latest'), ('packages', ['--allow-unauthenticated']),
                           ('default_mode', 'writable'), ('root_content_budget_mib', 2048)]:
            c = dict(self.c, **{key: value})
            with self.assertRaises(ValueError):
                m.layout(c)

    def test_work_boundaries_and_symlinks(self):
        with self.assertRaises(ValueError):
            m.work_path('/dev/null')
        with self.assertRaises(ValueError):
            m.work_path(REPO / 'build')
        with tempfile.TemporaryDirectory(dir=REPO / 'build') as d:
            link = Path(d) / 'alias'
            link.symlink_to('/tmp', target_is_directory=True)
            with self.assertRaises(ValueError):
                m.work_path(link / 'new')

    def test_inspection_requires_security_refresh(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'build') as d:
            work = Path(d)
            (work / 'packages-complete').write_text(m.digest(self.c) + '\n')
            with self.assertRaises(FileNotFoundError):
                m.inspect(self.c, work)
            self.assertFalse((work / 'report.json').exists())

    def test_dry_run_does_not_create_work(self):
        with tempfile.TemporaryDirectory(dir=REPO / 'build') as d:
            work = Path(d) / 'untouched'
            for stage in ['bootstrap', 'packages', 'refresh', 'inspect']:
                result = subprocess.run(['python3', str(REPO / 'scripts/prepare_host_os.py'),
                                         '--stage', stage, '--work', str(work)],
                                        check=True, capture_output=True, text=True)
                self.assertFalse(json.loads(result.stdout)['execute'])
                self.assertFalse(work.exists())


if __name__ == '__main__':
    unittest.main()
