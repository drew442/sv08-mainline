"""Durable automatic restart fixtures; real transaction, no system service calls."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_data_budget import fixture_budget, fixture_root
from test_transaction import Backend, admitted
from test_network_admin import Commands, Budget
from test_service_admission import Services
from sv08_state import Store, atomic_json
from sv08_transaction import Transaction
from sv08_network import Network
from sv08_admission import Admission, KLIPPER, MOONRAKER
from sv08_auto_reboot import AutoReboot
from sv08_restart import intent


class AutoRebootTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=fixture_root()); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name); self.runtime = root/'run'; self.runtime.mkdir()
        self.boot_id = root/'boot-id'; self.boot_id.write_text('boot-1')
        self.store = Store(root/'data', reserve_bytes=0, budget=fixture_budget(), runtime=self.runtime, boot_id=self.boot_id)
        self.store.initialize()
        self.boot = self.store.prepare_boot('A', 'release-1', release_revision=1); self.boot['boot_id'] = 'boot-1'
        atomic_json(self.runtime/'boot.json', self.boot)
        self.backend = Backend(); self.tx = Transaction(self.store, self.backend, admitted)
        proof = dict(release='release-2',release_revision=2,signer_trusted=True,bundle_sha256='a'*64)
        self.tx.stage('bundle',proof,self.boot,automatic=True); self.tx.arm(self.boot,automatic=True)
        self.command = Commands()
        self.network = Network(self.store.root, command=self.command, budget=Budget(), runtime=self.runtime, boot_id=self.boot_id)
        self.restart = AutoReboot(self.store,self.tx,self.boot,network=self.network)
        uid = patch('sv08_admission.os.geteuid',return_value=0); uid.start(); self.addCleanup(uid.stop)

    def dispatches(self): return sum('reboot' in row for row in self.command.calls)

    def test_one_dispatch_retains_gate_and_does_not_claim_health(self):
        self.assertEqual(self.restart.run(),'reboot-queued')
        self.assertEqual(self.restart.load()['state'],'queued')
        self.assertEqual(self.tx.load()['phase'],'armed')
        self.assertIsNotNone(intent(self.runtime,self.boot_id))
        self.assertEqual(self.restart.run(),'reboot-queued')
        self.assertEqual(self.dispatches(),1)

    def test_opt_out_suppresses_before_dispatch_and_can_resume(self):
        self.store.policy(auto_update=False)
        self.assertEqual(self.restart.run(),'reboot-suppressed')
        self.assertEqual(self.dispatches(),0)
        self.assertEqual(self.tx.load()['phase'],'armed')
        self.store.policy(auto_update=True)
        self.assertEqual(self.restart.run(),'reboot-queued')

    def test_policy_jobs_network_and_wrong_origin_do_not_dispatch(self):
        state=self.store.load();state['update_policy']={'check_version':False};self.store.save(state)
        with self.assertRaisesRegex(ValueError,'policy changed'):self.restart.run()
        state.pop('update_policy');self.store.save(state)
        root=self.store.root/'software/jobs';root.mkdir(parents=True)
        atomic_json(root/'job.json',dict(status='running'))
        with self.assertRaisesRegex(ValueError,'software job'):self.restart.run()
        (root/'job.json').unlink()
        with patch.object(self.network,'pending',return_value={'token':'pending'}):
            with self.assertRaisesRegex(ValueError,'network changes'):self.restart.run()
        tx=self.tx.load();tx['automatic']=False;self.tx.save(tx,'armed')
        with self.assertRaisesRegex(ValueError,'automatic transaction'):self.restart.run()
        self.assertEqual(self.dispatches(),0)

    def test_printing_refuses_without_dispatch(self):
        services=Services()
        def refuse(path):raise ValueError('printing')
        self.restart.admission=Admission(self.runtime,services,refuse,boot_id=self.boot_id)
        with self.assertRaisesRegex(ValueError,'printing'):self.restart.run()
        self.assertEqual(self.dispatches(),0);self.assertEqual(services.calls,[])
        self.assertEqual(self.restart.load()['state'],'ready')

    def test_launch_failure_restores_services_and_can_retry(self):
        services=Services();self.restart.admission=Admission(self.runtime,services,lambda p:None,boot_id=self.boot_id)
        def failed(*args):
            if 'reboot' in args:raise FileNotFoundError('not launched')
            return self.command(*args)
        self.restart.command=failed
        with self.assertRaises(FileNotFoundError):self.restart.run()
        self.assertEqual(self.restart.load()['state'],'ready')
        self.assertIsNone(intent(self.runtime,self.boot_id))
        self.assertEqual(set(services.states.values()),{'active'})
        self.restart.command=self.command
        self.assertEqual(self.restart.run(),'reboot-queued')

    def test_timeout_nonzero_or_killed_caller_is_never_replayed(self):
        for error in (TimeoutError('lost'),ValueError('failed acknowledgment'),KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                for path in (self.restart.path,self.runtime/'shutdown.json'):path.unlink(missing_ok=True)
                services=Services();self.restart.admission=Admission(self.runtime,services,lambda p:None,boot_id=self.boot_id)
                def failed(*args):
                    if 'reboot' in args:raise error
                    return self.command(*args)
                self.restart.command=failed
                with self.assertRaises((ValueError,KeyboardInterrupt)):self.restart.run()
                self.assertIn(self.restart.load()['state'],('uncertain','dispatching'))
                self.assertEqual(self.restart.run(),'reboot-uncertain')
                self.assertEqual(set(services.states.values()),{'inactive'})
                self.assertIsNotNone(intent(self.runtime,self.boot_id))

    def test_lost_receipt_after_accepted_command_keeps_dispatching(self):
        original=self.restart.save
        def save(record,state,value=None):
            if state=='queued':raise FileNotFoundError('receipt filesystem unavailable')
            return original(record,state,value)
        with patch.object(self.restart,'save',side_effect=save):
            with self.assertRaises(FileNotFoundError):self.restart.run()
        self.assertEqual(self.restart.load()['state'],'dispatching')
        self.assertIsNotNone(intent(self.runtime,self.boot_id))
        self.assertEqual(self.restart.run(),'reboot-uncertain');self.assertEqual(self.dispatches(),1)

    def test_new_boot_waits_for_health_then_records_observed(self):
        self.restart.run();self.boot_id.write_text('boot-2')
        self.assertEqual(self.restart.run(),'awaiting-health-reconciliation')
        tx=self.tx.load();self.tx.save(tx,'complete')
        self.assertEqual(self.restart.run(),'reboot-observed')
        self.assertEqual(self.restart.load()['state'],'observed');self.assertEqual(self.dispatches(),1)

    def test_cancelled_undispatched_receipt_does_not_block_next_release(self):
        for state in ('suppressed','ready'):
            with self.subTest(state=state):
                if state=='suppressed':
                    self.store.policy(auto_update=False)
                    self.assertEqual(self.restart.run(),'reboot-suppressed')
                    self.store.policy(auto_update=True)
                else:
                    record=self.restart.load();record['state']='ready';atomic_json(self.restart.path,record)
                self.tx.cancel(self.boot)
                proof=dict(release='release-'+state,release_revision=3,signer_trusted=True,bundle_sha256='b'*64)
                self.tx.stage('bundle',proof,self.boot,automatic=True);self.tx.arm(self.boot,automatic=True)
                if state=='suppressed':
                    services=Services()
                    def refuse(path):raise ValueError('printing')
                    self.restart.admission=Admission(self.runtime,services,refuse,boot_id=self.boot_id)
                    with self.assertRaisesRegex(ValueError,'printing'):self.restart.run()
                else:
                    self.restart.admission=None
                    self.assertEqual(self.restart.run(),'reboot-queued')
        self.assertEqual(self.dispatches(),1)

    def test_malformed_receipt_and_identity_mismatch_fail_closed(self):
        self.restart.path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'receipt'):self.restart.run()
        self.restart.path.unlink();self.restart.run()
        record=self.restart.load();record['state']='ready';record['release']='wrong';atomic_json(self.restart.path,record)
        with self.assertRaisesRegex(ValueError,'differs'):self.restart.run()
