import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from export_moonraker_lock import select


def wheel(name, tag):
    return {'url': f'https://example.invalid/{name}-1-{tag}.whl', 'hash': 'sha256:' + 'a' * 64}


class TargetLockTests(unittest.TestCase):
    def test_target_markers_and_architecture(self):
        lock = {'package': [
            {'name': 'moonraker', 'dependencies': [{'name': 'runtime'},
                {'name': 'windows-only', 'marker': "sys_platform == 'win32'"}]},
            {'name': 'runtime', 'version': '1', 'wheels': [
                wheel('runtime', 'cp313-cp313-manylinux_2_17_x86_64'),
                wheel('runtime', 'cp313-cp313-manylinux_2_17_aarch64')]}]}
        result = select(lock)
        self.assertEqual(len(result), 1)
        self.assertIn('aarch64', result[0]['filename'])
        self.assertFalse(result[0]['requires_build'])

    def test_missing_binary_is_explicit_source_build(self):
        lock = {'package': [
            {'name': 'moonraker', 'dependencies': [{'name': 'runtime'}]},
            {'name': 'runtime', 'version': '1', 'wheels': [],
             'sdist': {'url': 'https://example.invalid/runtime-1.tar.gz',
                       'hash': 'sha256:' + 'b' * 64}}]}
        self.assertTrue(select(lock)[0]['requires_build'])

    def test_ambiguous_resolution_rejected(self):
        lock = {'package': [
            {'name': 'moonraker', 'dependencies': [{'name': 'runtime'}]},
            {'name': 'runtime', 'version': '1'}, {'name': 'runtime', 'version': '2'}]}
        with self.assertRaises(ValueError):
            select(lock)

    def test_python_resolution_branch(self):
        lock = {'package': [
            {'name': 'moonraker', 'dependencies': [{'name': 'runtime'}]},
            {'name': 'runtime', 'version': '1', 'resolution-markers': ["python_full_version < '3.15'"],
             'wheels': [wheel('runtime', 'py3-none-any')]},
            {'name': 'runtime', 'version': '2', 'resolution-markers': ["python_full_version >= '3.15'"]}]}
        self.assertEqual(select(lock)[0]['version'], '1')
