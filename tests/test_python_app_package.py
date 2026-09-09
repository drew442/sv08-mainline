import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import package_python_app as app


class PythonAppInputsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.wheels = self.root / 'wheels'
        self.wheels.mkdir()
        self.wheel = self.wheels / 'test.whl'
        self.wheel.write_bytes(b'locked content')
        lock = self.root / 'runtime.lock'
        lock.write_text('test==1 --hash=sha256:' + app.sha(self.wheel) + '\n')
        self.c = dict(app='moonraker', source_commit='a'*40, runtime_lock='runtime.lock', runtime_lock_sha256=app.sha(lock))
        (self.root / 'upstream-lock.json').write_text(json.dumps({'submodules': [
            {'path': 'upstream/moonraker', 'commit': 'a'*40}]}))

    def verify(self, head='a'*40):
        with patch.object(app, 'REPO', self.root), patch.object(app.subprocess, 'check_output', return_value=head):
            return app.verify(self.c, self.wheels)

    def test_modified_runtime_rejected(self):
        self.verify()
        self.wheel.write_bytes(b'replacement')
        with self.assertRaisesRegex(ValueError, 'Wheelhouse'):
            self.verify()

    def test_source_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Source pin'):
            self.verify('b'*40)

    def test_symlink_input_rejected(self):
        self.wheel.rename(self.root / 'outside')
        self.wheel.symlink_to(self.root / 'outside')
        with self.assertRaisesRegex(ValueError, 'Wheelhouse'):
            self.verify()
