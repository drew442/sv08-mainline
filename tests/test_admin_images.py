import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_admin import Controller
from sv08_admin_images import HostImages
from sv08_state import Store
from sv08_staging import Staging
from test_transaction import Backend, admitted


class ImageAdministrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='.sv08-admin-images-', dir=Path.home())
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.store = Store(root / 'state', reserve_bytes=0); self.store.initialize()
        self.boot = self.store.prepare_boot('A', 'release-1'); self.boot['boot_id'] = 'boot-1'
        upload = root / 'uploads'; upload.mkdir(mode=0o700)
        self.staging = Staging(upload, reserve_bytes=0, owner_uid=os.getuid())
        payload = b'test fixture only'; self.digest = hashlib.sha256(payload).hexdigest()
        verify = lambda path: dict(release='release-2', bundle_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        with self.store.locked(): self.staging.receive(io.BytesIO(payload), len(payload), self.digest, verify)
        # A bootloader double only. No physical target is declared deployable.
        self.backend = Backend(); self.backend.manifest = {'deployable': True}
        self.adapter = HostImages(self.store, self.boot, self.backend, self.staging, admitted, verify)
        self.controller = Controller(self.store, self.boot, adapter=self.adapter)

    def apply(self, action, **arguments):
        return self.controller.apply(self.controller.plan(action, arguments))

    def test_reviewed_stage_arm_cancel_uses_existing_transaction(self):
        self.apply('image.stage', digest=self.digest)
        self.assertEqual(self.backend.primary(), 'A')
        self.assertEqual(self.controller.status()['transaction']['phase'], 'staged')
        self.apply('image.arm')
        self.assertEqual(self.backend.primary(), 'B')
        self.apply('image.cancel')
        self.assertEqual(self.backend.primary(), 'A')
        self.assertIsNone(self.store.load()['pending'])
        self.assertTrue(self.staging.path(self.digest).exists())

    def test_non_deployable_board_and_customization_disable_controls(self):
        self.backend.manifest['deployable'] = False
        with self.assertRaisesRegex(ValueError, 'approved'): self.apply('image.stage', digest=self.digest)
        self.backend.manifest['deployable'] = True
        state = self.store.load(); state['slots']['A']['customized'] = True; self.store.save(state)
        with self.assertRaisesRegex(ValueError, 'customizations'): self.apply('image.stage', digest=self.digest)
        self.assertEqual(self.backend.calls, [])

    def test_race_after_review_is_rechecked_inside_transaction_lock(self):
        plan = self.controller.plan('image.stage', {'digest':self.digest})
        self.store.policy(auto_update=False)
        with self.assertRaisesRegex(ValueError, 'changed'): self.adapter.apply(plan)
        self.assertEqual(self.backend.calls, [])
