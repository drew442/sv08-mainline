import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_admin import Controller
from sv08_state import Store
from sv08_recovery import RecoveryController


class AdministrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.store = Store(Path(temporary.name) / 'state', reserve_bytes=0)
        self.store.initialize()
        self.boot = self.store.prepare_boot('A', 'release-1')
        self.controller = Controller(self.store, self.boot)

    def test_review_does_not_write_and_apply_preserves_generation(self):
        before = self.store.load()
        plan = self.controller.plan('policy.mode', {'mode': 'writable'})
        self.assertEqual(before, self.store.load())
        self.controller.apply(plan)
        after = self.store.load()
        self.assertEqual(after['requested_mode'], 'writable')
        self.assertEqual(after['slots'], before['slots'])
        self.assertEqual(self.boot['mode'], 'immutable')

    def test_hostname_is_saved_without_changing_runtime_or_other_state(self):
        before = self.store.load()
        self.controller.apply(self.controller.plan('config.hostname', {'hostname':'workshop-sv08'}))
        self.assertEqual((self.store.root / 'system/hostname').read_text(), 'workshop-sv08\n')
        self.assertEqual(self.store.load(), before)
        self.assertEqual(self.controller.status()['hostname'], 'workshop-sv08')
        for name in ('-printer', 'printer-', 'UPPERCASE', 'a'*64, 'printer;reboot', 'printer.local'):
            with self.assertRaises(ValueError): self.controller.plan('config.hostname', {'hostname':name})

    def test_interrupted_name_change_keeps_old_and_new_aliases(self):
        from sv08_admin import atomic_text
        parent = self.store.root / 'system'; parent.mkdir(exist_ok=True)
        (parent / 'hostname').write_text('old-printer\n')
        (parent / 'hosts').write_text('127.0.0.1 localhost\n127.0.1.1 old-printer my-alias # keep\n192.0.2.4 lan-node\n')
        plan = self.controller.plan('config.hostname', {'hostname':'new-printer'})
        def fail_hostname(path, text):
            if path.name == 'hostname': raise OSError('interrupted publication')
            atomic_text(path, text)
        with patch('sv08_admin.atomic_text', side_effect=fail_hostname):
            with self.assertRaises(OSError): self.controller.apply(plan)
        self.assertEqual((parent / 'hostname').read_text(), 'old-printer\n')
        self.assertIn('old-printer my-alias new-printer # keep', (parent / 'hosts').read_text())
        self.assertIn('192.0.2.4 lan-node', (parent / 'hosts').read_text())
        self.controller.apply(self.controller.plan('config.hostname', {'hostname':'new-printer'}))
        self.assertEqual((parent / 'hostname').read_text(), 'new-printer\n')

    def test_stale_or_edited_review_is_rejected(self):
        plan = self.controller.plan('policy.auto', {'enabled': False})
        self.store.policy(mode='writable')
        with self.assertRaisesRegex(ValueError, 'changed'): self.controller.apply(plan)
        plan = self.controller.plan('policy.auto', {'enabled': False})
        plan['effect'] = 'Forged review'
        with self.assertRaisesRegex(ValueError, 'changed'): self.controller.apply(plan)
        self.assertTrue(self.store.load()['auto_update'])

    def test_pending_or_staged_update_blocks_mode_change(self):
        journal = dict(phase='staged')
        (self.store.root / 'update.json').write_text(json.dumps(journal))
        with self.assertRaisesRegex(ValueError, 'pending'): self.controller.plan('policy.mode', {'mode': 'writable'})
        self.controller.apply(self.controller.plan('policy.auto', {'enabled': False}))
        self.assertFalse(self.store.load()['auto_update'])

    def test_unknown_fields_and_command_paths_are_rejected(self):
        for request in ({'method':'shell', 'command':'id'}, {'method':'status', 'root':'/'},
                        {'method':'plan', 'action':'policy.auto', 'arguments':{'enabled':'false'}}):
            with self.subTest(request=request), self.assertRaises(ValueError): self.controller.request(request)
        with self.assertRaises(ValueError): self.controller.plan('software.install', {'package':'--allow-unauthenticated'})
        with self.assertRaises(ValueError): self.controller.plan('recovery.restore', {'image':'../../dev/mmcblk0'})

    def test_missing_backend_never_claims_recovery_or_installation(self):
        for context, action, arguments in [('host','image.stage',{'digest':'a'*64}),
                ('host','software.install',{'package':'vim'}), ('recovery','recovery.boot',{'slot':'B'}),
                ('recovery','recovery.restore',{'image':'release-2'})]:
            controller = Controller(self.store, self.boot, context)
            self.assertFalse(controller.status()['capabilities'][action]['available'])
            with self.assertRaises(ValueError): controller.plan(action, arguments)
        self.assertIsNone(self.store.load()['pending'])

    def test_recovery_cannot_change_host_policy(self):
        controller = Controller(self.store, self.boot, 'recovery')
        with self.assertRaises(ValueError): controller.plan('policy.auto', {'enabled':False})

    def test_symlink_journal_refused(self):
        (self.store.root / 'update.json').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'journal'): self.controller.status()


class RecoveryIndependenceTests(unittest.TestCase):
    def test_missing_data_can_be_inspected_without_creating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'missing-data'
            controller = RecoveryController(Store(root))
            status = controller.status()
            self.assertTrue(status['capabilities']['recovery.check']['available'])
            result = controller.apply(controller.plan('recovery.check', {}))
            self.assertIn('unavailable or damaged', result['message'])
            self.assertFalse(root.exists())
            with self.assertRaises(ValueError): controller.plan('recovery.boot', {'slot':'A'})

    def test_corrupt_registry_stays_corrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'state.json').write_text('damaged')
            controller = RecoveryController(Store(root))
            controller.apply(controller.plan('recovery.check', {}))
            self.assertEqual((root / 'state.json').read_text(), 'damaged')
            self.assertFalse((root / '.lock').exists())
