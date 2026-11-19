from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_admin import validate_arguments
from sv08_recovery import RecoveryController
from sv08_recovery_restore_media import RestoreAdapter, Composite
from sv08_restore import Restore
from sv08_state import Store
from sv08_owner import Owner
from test_data_budget import fixture_root, fixture_budget

PASSWORD='private fixture password'


class RecoveryOwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=fixture_root());self.addCleanup(self.temp.cleanup)
        self.parent=Path(self.temp.name); self.media='fixture-media';self.leased=False
        targets={'disk':dict(mount=str(self.parent),root=str(self.parent/'restored'),fresh_root=str(self.parent/'fresh'),label='Fixture storage')}
        @contextmanager
        def admission(target):
            self.assertEqual(target,'disk');self.assertFalse(self.leased);self.leased=True
            parent=self
            class Guard:
                fingerprint=parent.media
                def recheck(guard): parent.assertTrue(parent.leased)
            try: yield Guard()
            finally:self.leased=False
        self.adapter=RestoreAdapter(Restore({},targets,admission,reserve_bytes=0))
        self.adapter.owner.root_uid=os.getuid()
        for root in (self.parent/'sv08',self.parent/'fresh',self.parent/'restored/sv08'):
            Store(root,reserve_bytes=0,budget=fixture_budget()).initialize()
            (root/'system').chmod(0o700)
        self.controller=RecoveryController(Store(self.parent/'sv08'),self.adapter)

    def plan(self,state='current',reset=False):
        return self.controller.plan('recovery.owner',dict(target='disk',state=state,reset=reset))

    def test_enroll_all_finite_states_cancel_and_redaction(self):
        for state,root in [('current',self.parent/'sv08'),('fresh',self.parent/'fresh'),('restored',self.parent/'restored/sv08')]:
            plan=self.plan(state); self.assertFalse((root/'system/owner.json').exists())
            self.assertNotIn('password_hash',json.dumps(plan));self.assertNotIn(PASSWORD,json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'local recovery'):self.controller.apply(plan)
            self.controller.enroll_owner(plan,PASSWORD,PASSWORD)
            self.assertTrue(Owner(root,os.getuid()).status()['enrolled'])
            self.assertFalse(self.leased)
            with self.assertRaisesRegex(ValueError,'explicit'):self.plan(state)

    def test_reset_and_state_media_cas(self):
        plan=self.plan();self.media='different'
        with self.assertRaisesRegex(ValueError,'changed'):self.controller.enroll_owner(plan,PASSWORD,PASSWORD)
        self.assertFalse((self.parent/'sv08/system/owner.json').exists())
        plan=self.plan();self.controller.enroll_owner(plan,PASSWORD,PASSWORD)
        reset=self.plan(reset=True);record=self.parent/'sv08/system/owner.json';before=record.read_bytes()
        with self.assertRaisesRegex(ValueError,'match'):self.controller.enroll_owner(reset,PASSWORD,'mismatch')
        self.assertEqual(record.read_bytes(),before)
        self.controller.enroll_owner(reset,'replacement fixture','replacement fixture')
        self.assertNotEqual(record.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'changed'):self.controller.enroll_owner(reset,PASSWORD,PASSWORD)

    def test_export_restore_and_activation_rollback_preserve_owner(self):
        from sv08_export import Export
        from sv08_recovery_activation import Activation
        from test_recovery_activation import state_fixture, BOOT
        source=self.parent/'export-source';source.mkdir(mode=0o700)
        canonical=source/'sv08';state_fixture(canonical,'original');(canonical/'system').chmod(0o700)
        original=Owner(canonical,os.getuid());original.save(PASSWORD,PASSWORD,original.status())
        usb=self.parent/'usb';usb.mkdir(mode=0o700)
        exporter=Export(source,{'usb':dict(path=usb,label='Fixture USB')},self.adapter.restorer.admission,reserve_bytes=0)
        # The fixture's existing admission accepts one configured media ID.
        @contextmanager
        def admission(target):
            class Guard:
                fingerprint='fixture archive media'
                def recheck(self):pass
            yield Guard()
        exporter.admission=admission
        archive=usb/exporter.execute(exporter.prepare('usb'))['filename']
        destination=self.parent/'destination';destination.mkdir(mode=0o700)
        targets={'disk':dict(mount=str(destination),root=str(destination/'restored'),fresh_root=str(destination/'fresh'),label='Destination')}
        restore=Restore({'archive':dict(path=archive,label='Fixture archive')},targets,admission,reserve_bytes=0)
        restore.execute(restore.prepare('disk','archive'))
        restored=destination/'restored/sv08'
        self.assertEqual((restored/'system/owner.json').read_bytes(),(canonical/'system/owner.json').read_bytes())
        state_fixture(destination/'sv08','previous');(destination/'sv08/system').chmod(0o700)
        previous=Owner(destination/'sv08',os.getuid());previous.save('previous password','previous password',previous.status())
        previous_bytes=(destination/'sv08/system/owner.json').read_bytes()
        activation=Activation(targets,admission,BOOT);activation.execute(activation.prepare('disk'))
        self.assertEqual((destination/'sv08/system/owner.json').read_bytes(),(canonical/'system/owner.json').read_bytes())
        activation.execute(activation.prepare('disk',rollback=True))
        self.assertEqual((destination/'sv08/system/owner.json').read_bytes(),previous_bytes)

    def test_no_unknown_state_initialization_or_arbitrary_paths(self):
        for args in (dict(target='/tmp',state='current',reset=False),dict(target='disk',state='../other',reset=False),dict(target='disk',state='current',reset=1),dict(target='disk',state='current',reset=False,password=PASSWORD)):
            with self.assertRaises(ValueError):validate_arguments('recovery.owner',args)
        state=self.parent/'fresh/state.json';state.write_bytes(b'broken')
        with self.assertRaises(ValueError):self.plan('fresh')
        self.assertEqual(state.read_bytes(),b'broken');self.assertFalse((state.parent/'system/owner.json').exists())
        (self.parent/'.sv08-activation-pending').write_text('interrupted')
        with self.assertRaisesRegex(ValueError,'rollback'):self.plan()

if __name__=='__main__':unittest.main()
