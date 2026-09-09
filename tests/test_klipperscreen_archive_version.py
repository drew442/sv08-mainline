import ast
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest.mock import Mock

REPO = Path(__file__).resolve().parents[1]


class ArchiveVersionTests(unittest.TestCase):
    def test_archive_version_and_git_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'ks_includes').mkdir()
            source = root / 'ks_includes/functions.py'
            shutil.copyfile(REPO / 'upstream/klipperscreen/ks_includes/functions.py', source)
            subprocess.run(['patch', '--batch', '-d', str(root), '-p1', '-i', str(REPO / 'patches/klipperscreen/0001-archive-version.patch')], check=True, stdout=subprocess.DEVNULL)
            tree = ast.parse(source.read_text())
            function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'get_software_version')
            fake_subprocess = Mock()
            scope = {'os': os, '__file__': str(source), 'subprocess': fake_subprocess, 'logging': Mock()}
            exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), scope)
            (root / '.version').write_text('3791fdf\n')
            self.assertEqual(scope['get_software_version'](), '3791fdf')
            fake_subprocess.Popen.assert_not_called()
            (root / '.version').write_text('')
            fake_subprocess.Popen.return_value = types.SimpleNamespace(communicate=lambda: (b'upstream-version', b''), wait=lambda: 0)
            self.assertEqual(scope['get_software_version'](), 'upstream-version')
