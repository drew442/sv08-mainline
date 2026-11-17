"""Permission outcomes using real publication and pinned native SAVE_CONFIG."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'))
from sv08_commissioning import Commissioning
from sv08_printer_publish import Publisher
from sv08_state import Store, atomic_json
from sv08_restart import publish, start_admitted
from test_data_budget import fixture_root, fixture_budget
from test_printer_configuration import primary_source
import test_printer_calibration as calibration
sys.path.insert(0,str(ROOT/'scripts'))
from integrate_host_os import firmware_manifest
from test_supported_candidate import profile, profile_check


class CommissioningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=fixture_root());self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.runtime=self.base/'run';self.runtime.mkdir()
        self.store=Store(self.base/'data',reserve_bytes=0,budget=fixture_budget());self.store.initialize()
        (self.store.root/'system').chmod(0o700)
        self.boot=self.store.prepare_boot('A','fixture-rc1');self.boot['boot_id']='synthetic-boot'
        atomic_json(self.runtime/'boot.json',self.boot);(self.runtime/'os-health-ready').touch()
        self.release=self.base/'release.json';atomic_json(self.release,firmware_manifest(profile_check(profile())))
        self.source=primary_source('upstream/klipper/klippy/configfile.py').parents[1]
        if not (self.source/'klippy/configfile.py').is_file(): self.fail('Existing pinned source required for native calibration contract')
        self.config=Path(self.boot['generation'])/'config'
        publisher=Publisher(self.config,admit=lambda:True,source=self.source,
                            binding=dict(hardware='a'*64,firmware_boards={'main':dict(id='fixture-board')}),
                            validate=lambda *a:dict(validated=True))
        files={'hardware.cfg':calibration.HARDWARE}
        review=publisher.preview(files,{},'fixture');publisher.apply(review['review'],files,{},'fixture')
        self.service=Commissioning(self.store,self.release,self.runtime,uid=os.getuid(),source=self.source)

    def test_explicit_authorization_cancel_stale_and_no_service_operation(self):
        review=self.service.snapshot();self.assertFalse(self.service.permission.exists())
        with self.assertRaisesRegex(ValueError,'reviewed'): self.service.check()
        with self.assertRaisesRegex(ValueError,'changed'): self.service.authorize('stale','H05 synthetic review')
        self.assertFalse(self.service.permission.exists())
        with patch('subprocess.run') as command:
            result=self.service.authorize(review['review_sha256'],'H05 synthetic review')
        command.assert_not_called();self.assertEqual(result['service_action'],'none')
        self.assertFalse(result['printing_qualified']);self.assertTrue(self.service.check()['permitted'])
        self.service.permission.chmod(0o644)
        with self.assertRaisesRegex(ValueError,'permission'): self.service.check()

    def test_save_config_survives_both_slots_and_modes_without_granting_new_hardware(self):
        self.service.authorize(self.service.snapshot()['review_sha256'],'H05 synthetic review')
        before=self.service.permission.read_bytes()
        with patch.object(calibration,'SOURCE',self.source):
            writer=calibration.NativeWriter(self.config/'printer.cfg')
            writer.native.set('probe','z_offset','0.125');writer.save()
        self.assertTrue(self.service.check()['permitted'])
        self.assertEqual(self.service.permission.read_bytes(),before)
        self.store.policy(mode='writable')
        boot=self.store.prepare_boot('B','fixture-rc1');boot['boot_id']='another-synthetic-boot'
        atomic_json(self.runtime/'boot.json',boot)
        self.assertTrue(self.service.check()['permitted'])
        receipt=json.loads((Path(boot['generation'])/'config/printer-managed/receipt.json').read_text())
        relative=next(name for name in receipt['after'] if name.endswith('hardware.cfg'))
        path=Path(boot['generation'])/'config'/relative;path.write_text(path.read_text().replace('PA2','PA9'))
        with self.assertRaisesRegex(ValueError,'drift'): self.service.check()
        with patch('sv08_commissioning.subprocess.run') as command:
            self.assertIn('drift',self.service.boot_activate()['reason'])
        command.assert_not_called()
        self.assertEqual(self.service.permission.read_bytes(),before)

    def test_health_trial_and_firmware_change_refuse(self):
        self.service.authorize(self.service.snapshot()['review_sha256'],'H05 synthetic review')
        before=self.service.permission.read_bytes()
        (self.runtime/'os-health-ready').unlink()
        with self.assertRaisesRegex(ValueError,'healthy'): self.service.check()
        (self.runtime/'os-health-ready').touch();(self.runtime/'trial').touch()
        with self.assertRaisesRegex(ValueError,'healthy'): self.service.check()
        (self.runtime/'trial').unlink()
        manifest=json.loads(self.release.read_text())
        manifest['mcu_firmware']['host_klipper_commit']='b'*40;manifest['mcu_firmware']['definitions']=[]
        atomic_json(self.release,manifest)
        with self.assertRaisesRegex(ValueError,'MCU firmware was not flashed'): self.service.check()
        with patch('sv08_commissioning.subprocess.run') as command:
            self.assertIn('MCU firmware was not flashed',self.service.boot_activate()['reason'])
        command.assert_not_called()
        self.assertEqual(self.service.permission.read_bytes(),before)

    def test_boot_activation_absent_revoked_and_stale_permission_never_dispatch(self):
        with patch('sv08_commissioning.subprocess.run') as command:
            result=self.service.boot_activate()
            self.assertEqual(result['service_action'],'none');self.assertIn('reviewed',result['reason'])
            self.service.authorize(self.service.snapshot()['review_sha256'],'H05 synthetic review')
            self.service.permission.unlink()  # Same persisted outcome as explicit revoke.
            self.assertEqual(self.service.boot_activate()['service_action'],'none')
            self.service.authorize(self.service.snapshot()['review_sha256'],'H05 synthetic review')
            permission=json.loads(self.service.permission.read_text());permission['binding']['hardware']='b'*64
            atomic_json(self.service.permission,permission)
            result=self.service.boot_activate()
            self.assertEqual(result['service_action'],'none');self.assertIn('changed',result['reason'])
        command.assert_not_called()

    def test_boot_activation_health_trial_pending_shutdown_and_busy_never_dispatch(self):
        self.service.authorize(self.service.snapshot()['review_sha256'],'H05 synthetic review')
        with patch('sv08_commissioning.subprocess.run') as command:
            (self.runtime/'os-health-ready').unlink()
            self.assertIn('healthy',self.service.boot_activate()['reason'])
            (self.runtime/'os-health-ready').touch();(self.runtime/'trial').touch()
            self.assertIn('healthy',self.service.boot_activate()['reason'])
            (self.runtime/'trial').unlink()
            boot=dict(self.boot,trial=True);atomic_json(self.runtime/'boot.json',boot)
            self.assertIn('healthy',self.service.boot_activate()['reason'])
            atomic_json(self.runtime/'boot.json',self.boot)
            self.store.expect_trial('B','fixture-rc2','A')
            self.assertIn('healthy',self.service.boot_activate()['reason'])
            state=self.store.load();state['pending']=None;self.store.save(state)
            publish(self.runtime)
            self.assertIn('shutdown',self.service.boot_activate()['reason'])
            (self.runtime/'shutdown.json').unlink()
            with start_admitted(self.runtime):
                self.assertEqual(self.service.boot_activate()['service_action'],'none')
        command.assert_not_called()

    def test_boot_activation_repeats_across_modes_slots_and_compatible_host_update(self):
        self.service.authorize(self.service.snapshot()['review_sha256'],'H05 synthetic review')
        permission=self.service.permission.read_bytes();calls=[]
        def queue(args,**kwargs):
            # Dispatch must not race execution-time guards for their locks.
            with self.store.locked(nonblocking=True), start_admitted(self.runtime):
                self.assertTrue(self.service.check()['permitted'])
            calls.append((args,kwargs))
        for mode,slot,release in [('immutable','A','fixture-rc1'),('immutable','B','fixture-rc2'),
                                  ('immutable','A','fixture-rc1'),('writable','B','fixture-rc2')]:
            with self.subTest(mode=mode,slot=slot,release=release):
                self.store.policy(mode=mode)
                manifest=json.loads(self.release.read_text());manifest['release']=release
                manifest.pop('mcu_firmware');atomic_json(self.release,firmware_manifest(manifest))
                if not any(record['release']==release for record in self.store.load()['slots'].values()):
                    self.store.expect_trial(slot,release,'B' if slot=='A' else 'A')
                    self.store.prepare_boot(slot,release)
                    self.store.confirm(slot,release)
                boot=self.store.prepare_boot(slot,release);boot['boot_id']='synthetic-new-boot'
                atomic_json(self.runtime/'boot.json',boot)
                self.assertEqual(self.service.boot_activate(queue)['service_action'],'start-queued')
                self.assertEqual(self.service.permission.read_bytes(),permission)
        self.assertEqual(len(calls),4)
        for args,kwargs in calls:
            self.assertEqual(args,['/usr/bin/systemctl','--no-block','start','sv08-klipper.service'])
            self.assertEqual(kwargs,dict(check=True,timeout=15))

    def test_boot_activation_dispatch_failure_is_not_reported_as_queued(self):
        import subprocess
        self.service.authorize(self.service.snapshot()['review_sha256'],'H05 synthetic review')
        with patch('sv08_commissioning.subprocess.run',side_effect=subprocess.CalledProcessError(1,'stub')):
            with self.assertRaises(subprocess.CalledProcessError):self.service.boot_activate()

    def test_actual_trial_confirmation_allows_activation_in_same_original_boot(self):
        from sv08_boot_health import HealthFailure, run, validate_boot
        from sv08_transaction import Transaction
        from test_host_boot_health import Backend, admitted
        self.service.authorize(self.service.snapshot()['review_sha256'],'H05 synthetic review')
        permission=self.service.permission.read_bytes()
        # Real state/transaction transition, with explicitly synthetic backend
        # and health callbacks. No production OS-health acceptance is asserted.
        self.store.prepare_boot('A','fixture-rc1',release_revision=1)
        tx=Transaction(self.store,Backend(),admitted)
        tx.stage('fixture-bundle',dict(release='fixture-rc2',release_revision=2,
                 bundle_sha256='a'*64,signer_trusted=True),self.boot)
        tx.arm(self.boot)
        target=self.store.prepare_boot('B','fixture-rc2',release_revision=2)
        target['boot_id']=str(uuid.uuid4());original=dict(target)
        boot_path=self.runtime/'boot.json';atomic_json(boot_path,target)
        manifest=json.loads(self.release.read_text());manifest['release']='fixture-rc2'
        manifest['release_revision']=2;manifest.pop('mcu_firmware')
        manifest=firmware_manifest(manifest);atomic_json(self.release,manifest)
        gate=self.runtime/'trial';gate.touch();ready=self.runtime/'os-health-ready';ready.unlink()
        def validate():
            return validate_boot(target,self.store,manifest,boot_id=original['boot_id'],
                                 cmdline='rauc.slot=B',observed_slot='B',verify=lambda *_:None)
        with patch('sv08_commissioning.subprocess.run') as command:
            self.assertEqual(self.service.boot_activate()['service_action'],'none')
            self.assertEqual(run(target,tx,Mock(side_effect=HealthFailure('synthetic unstable')),
                                 admitted,Mock(),ready=ready,trial_marker=gate,validate=validate,
                                 boot_path=boot_path),'needs-health')
            self.assertEqual(self.service.boot_activate()['service_action'],'none')
            command.assert_not_called()
            self.assertEqual(json.loads(boot_path.read_text()),original)
            self.assertEqual(run(target,tx,Mock(return_value=True),admitted,Mock(),ready=ready,
                                 trial_marker=gate,validate=validate,boot_path=boot_path),'idle')
            self.assertEqual(target,dict(original,trial=False))
            self.assertEqual(json.loads(boot_path.read_text()),target)
            self.assertTrue(self.service.check()['permitted'])
            self.assertEqual(self.service.boot_activate()['service_action'],'start-queued')
            command.assert_called_once_with(['/usr/bin/systemctl','--no-block','start','sv08-klipper.service'],
                                            check=True,timeout=15)
        self.assertEqual(self.service.permission.read_bytes(),permission)


if __name__=='__main__': unittest.main()
