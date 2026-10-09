from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_software import Apt, Software, CATALOG, ROOT_RESERVE, digest
from sv08_state import Store


class FakeBudget:
    floor = 768*1024*1024
    @contextmanager
    def locked(self): yield self
    def check(self,*args,**kwargs): pass


class FakeApt:
    def __init__(self, root):
        self.root = root; self.runtime = root/'run'; self.runtime.mkdir()
        self.packages = []; self.changed = False; self.calls = []; self.fail = False
    def evidence(self): return dict(inventory=self.packages.copy(), manual=[], held=[], configuration={'apt':str(self.changed)},service=self.service())
    def audit(self): return ''
    def worker_state(self,ident): return 'active'
    def service(self): return dict(ActiveState='inactive',UnitFileState='disabled')
    def stopped(self): return {'sv08-klipper.service':'inactive','sv08-moonraker.service':'inactive'}
    def simulate(self,action,package,inventory):
        return dict(install=[dict(package=package,version='1')] if action=='install' else [], remove=[package] if action=='remove' else [],download_bytes=100,installed_delta_bytes=200,simulation_digest=digest([action,package]))
    def root_capacity(self,needed,writable=True): return dict(root_free_bytes=10**10,required_bytes=ROOT_RESERVE+needed)
    def locks(self): self.calls.append('locks')
    def execute(self,action,arguments,token):
        self.calls.append(action)
        if self.fail: raise ValueError('APT interrupted')
        if action=='install': self.packages.append([arguments['package'],'1','arm64','ii '])


class SoftwareTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name); data=root/'data'; data.mkdir(mode=0o700)
        self.store=Store(data,budget=FakeBudget()); self.boot=dict(mode='writable',slot='A',release='base',boot_id='one')
        self.state=dict(format_version=1,requested_mode='writable',auto_update=True,pending=None,slots={'A':dict(release='base',generation='a',schema=1,customized=True)})
        self.store.save(self.state); self.apt=FakeApt(root); self.launched=[]
        @contextmanager
        def admission(): yield
        self.api=Software(self.store,self.boot,self.apt,admission,self.launched.append)
        (root/'usr/sbin').mkdir(parents=True)
        self.policy=root/'usr/sbin/policy-rc.d'; self.policy.write_text('#!/bin/sh\nexit 0\n'); self.policy.chmod(0o755)
    def test_timeout_descendants_exit_before_admission_restoration(self):
        marker=Path(self.temp.name)/'late-write'; ready=marker.with_name('child-pid')
        child="import os,signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path(%r).write_text(str(os.getpid()));time.sleep(5);Path(%r).write_text('late')" % (str(ready),str(marker))
        parent="import subprocess,time;subprocess.Popen(%r);time.sleep(10)" % [sys.executable,'-c',child]
        real=Apt()
        self.apt.execute=lambda action,arguments,token: real.run([sys.executable,'-c',parent],timeout=.2,token=token)
        restored=[]
        @contextmanager
        def admission():
            try: yield
            finally:
                self.assertTrue(ready.exists(),'Child actually started before timeout')
                fields=Path('/proc/'+ready.read_text()+'/stat')
                self.assertTrue(not fields.exists() or fields.read_text().rsplit(') ',1)[1].split()[0] in ('Z','X'))
                restored.append(True)
        self.api.admission=admission
        plan=self.reviewed();job=self.submit(plan);result=self.api.worker(job['id'])
        self.assertEqual(result['status'],'unknown');self.assertEqual(restored,[True])
        time.sleep(.55);self.assertFalse(marker.exists())

    def reviewed(self,action='install',arguments=None): return self.api.plan(action,arguments or {'package':'nano'})
    def test_partial_fresh_service_install_is_disabled_before_admission_exits(self):
        real=Apt(root=self.apt.root)
        real.inventory=lambda: []
        calls=[]
        def run(command, **kwargs):
            calls.append(command)
            self.assertTrue((self.apt.runtime/'package-lease.json').exists())
            if command[0]=='apt-get':
                unit=real.root/'usr/lib/systemd/system/vnstat.service'
                unit.parent.mkdir(parents=True);unit.write_text('[Service]\nExecStart=/bin/true\n')
                raise ValueError('Later APT trigger failed')
            self.assertEqual(command,['systemctl','disable','--now','vnstat.service'])
            return ''
        real.run=run
        self.apt.execute=real.execute
        @contextmanager
        def admission():
            try: yield
            finally: self.assertEqual(calls[-1],['systemctl','disable','--now','vnstat.service'])
        self.api.admission=admission
        plan=self.reviewed(arguments={'package':'vnstat'});job=self.submit(plan)
        result=self.api.worker(job['id'])
        self.assertEqual(result['status'],'unknown')
        self.assertTrue(self.store.load()['slots']['A']['customized'])
        self.assertFalse((self.apt.runtime/'package-lease.json').exists())

    def submit(self,plan): return self.api.apply(plan['token'],plan['digest'])
    def test_real_command_is_finite_and_never_purges_or_autoremoves(self):
        apt=Apt()
        command=apt.command('remove','nano')
        self.assertIn('remove',command); self.assertNotIn('purge',command)
        self.assertIn('APT::Get::AutomaticRemove=false',command)
        self.assertNotIn('--allow-change-held-packages',command)
        self.assertIn('APT::Get::AllowUnauthenticated=false',command)
    def test_plan_job_executes_and_preserves_policy_and_customization(self):
        before=self.policy.read_bytes(); plan=self.reviewed(); receipt=self.submit(plan)
        self.assertEqual(self.launched,[receipt['id']]); self.assertEqual(self.submit(plan),receipt)
        job=self.api.worker(receipt['id'])
        self.assertEqual(job['status'],'completed'); self.assertEqual(self.apt.calls,['locks','install'])
        self.assertEqual(self.policy.read_bytes(),before); self.assertTrue(self.store.load()['slots']['A']['customized'])
        report=self.api.request({'method':'reconciliation-export','id':receipt['id']})
        self.assertTrue(report['activation_blocked']); self.assertEqual(report['requested_catalog'],['nano'])
        self.assertEqual(os.stat(self.api.root/'exports'/(receipt['id']+'.json')).st_mode & 0o777,0o600)
    def test_immutable_preview_available_but_apply_refused(self):
        self.boot['mode']='immutable'; plan=self.reviewed()
        self.assertFalse(plan['available']); self.assertTrue(plan['preview']['install'])
        with self.assertRaisesRegex(ValueError,'writable'): self.submit(plan)
        self.assertFalse(self.apt.calls)
    def test_state_repository_and_digest_changes_refused(self):
        plan=self.reviewed(); self.apt.changed=True
        with self.assertRaisesRegex(ValueError,'changed'): self.submit(plan)
        self.apt.changed=False
        with self.assertRaisesRegex(ValueError,'digest'): self.api.apply(plan['token'],'0'*64)
        self.state['pending']=dict(slot='B',release='next',previous_slot='A',phase='armed',id='trial'); self.store.save(self.state)
        with self.assertRaisesRegex(ValueError,'changed'): self.submit(plan)
    def test_worker_revalidates_after_queue(self):
        plan=self.reviewed(); receipt=self.submit(plan); self.apt.changed=True
        self.assertEqual(self.api.worker(receipt['id'])['status'],'failed'); self.assertFalse(self.apt.calls)
    def test_failed_apt_unknown_and_blocks_further_operations(self):
        plan=self.reviewed(); receipt=self.submit(plan); self.apt.fail=True
        self.assertEqual(self.api.worker(receipt['id'])['status'],'unknown')
        with self.assertRaisesRegex(ValueError,'unknown'): self.reviewed()
        self.assertFalse((self.apt.runtime/'package-lease.json').exists())
        self.assertEqual(self.policy.read_text(),'#!/bin/sh\nexit 0\n')
    def test_restart_unknown_no_replay(self):
        plan=self.reviewed(); receipt=self.submit(plan); self.boot['boot_id']='two'
        self.assertEqual(self.api.request({'method':'job','id':receipt['id']})['status'],'unknown')
        with self.assertRaisesRegex(ValueError,'earlier boot'): self.api.worker(receipt['id'])
        self.assertFalse(self.apt.calls)
    def test_reconciliation_is_report_not_reset(self):
        self.boot['mode']='immutable'; plan=self.api.plan('reconcile',{}); receipt=self.submit(plan)
        self.assertEqual(self.api.worker(receipt['id'])['status'],'completed')
        self.assertTrue(self.store.load()['slots']['A']['customized']); self.assertFalse(self.apt.calls)
    def test_review_explains_fresh_service_and_removal_effects(self):
        fresh=self.api.plan('install',dict(package='vnstat'))
        self.assertIn('stopped and disabled',fresh['preview']['service_effect'])
        self.apt.packages=[['vnstat','1','arm64','ii ']]
        existing=self.api.plan('install',dict(package='vnstat'))
        self.assertIn('Preserve the existing',existing['preview']['service_effect'])
        removed=self.api.plan('remove',dict(package='vnstat'))
        self.assertIn('before removing',removed['preview']['service_effect'])

    def test_service_only_known_unit_installed(self):
        with self.assertRaises(ValueError): self.api.plan('service',dict(package='nano',enabled=True))
        with self.assertRaisesRegex(ValueError,'Install'): self.api.plan('service',dict(package='vnstat',enabled=True))
        self.apt.packages=[['vnstat','1','arm64','ii ']]
        receipt=self.submit(self.api.plan('service',dict(package='vnstat',enabled=False)))
        self.assertEqual(self.api.worker(receipt['id'])['status'],'completed'); self.assertIn('service',self.apt.calls)
    def test_policy_mutation_retains_recovery_preimage(self):
        self.api.setup()
        with self.assertRaisesRegex(ValueError,'policy changed'):
            with self.api.activation_guard('1'*32): self.policy.write_text('changed')
        with self.assertRaisesRegex(ValueError,'policy requires'): self.api.busy()
    def test_status_progress_while_write_lock_held(self):
        plan=self.reviewed(); receipt=self.submit(plan)
        with self.store.locked():
            status=self.api.status()
            self.assertEqual(status['jobs'][0]['id'],receipt['id'])
            self.assertFalse(status['capabilities']['install']['available'])
    def test_inactive_worker_unknown_and_reviewed_acknowledgment(self):
        plan=self.reviewed(); receipt=self.submit(plan)
        path=self.api.root/'jobs'/(receipt['id']+'.json')
        job=json.loads(path.read_text()); job['created_at']=0; path.write_text(json.dumps(job))
        self.apt.worker_state=lambda ident:'inactive'
        report=self.api.request(dict(method='inspect',id=receipt['id']))
        self.assertEqual(report['job']['status'],'unknown')
        acknowledged=self.submit(self.api.plan('acknowledge',dict(id=receipt['id'])))
        self.assertEqual(self.api.worker(acknowledged['id'])['status'],'completed')
        original=self.api.request(dict(method='job',id=receipt['id']))
        self.assertEqual(original['status'],'acknowledged'); self.assertEqual(original['prior_outcome'],'unknown')
        self.assertNotIn('install',self.apt.calls)
        self.assertTrue(self.store.load()['slots']['A']['customized'])
    def test_exact_policy_recovery_without_package_replay(self):
        plan=self.reviewed(); receipt=self.submit(plan)
        try:
            with self.api.activation_guard(receipt['id']):
                # emulate a crash by retaining the private journal and guard
                record=(self.api.root/'jobs'/(receipt['id']+'.policy.json')).read_bytes()
        finally: pass
        (self.api.root/'jobs'/(receipt['id']+'.policy.json')).write_bytes(record)
        from sv08_software import GUARD
        self.policy.write_bytes(GUARD)
        path=self.api.root/'jobs'/(receipt['id']+'.json'); job=json.loads(path.read_text()); job['status']='unknown'; path.write_text(json.dumps(job))
        acknowledgment=self.submit(self.api.plan('acknowledge',dict(id=receipt['id'])))
        self.assertEqual(self.api.worker(acknowledgment['id'])['status'],'completed')
        self.assertEqual(self.policy.read_text(),'#!/bin/sh\nexit 0\n'); self.assertNotIn('install',self.apt.calls)
    def test_expired_unused_plans_are_reclaimed(self):
        plan=self.reviewed(); path=self.api.root/'plans'/(plan['token']+'.json')
        expired=json.loads(path.read_text()); expired['created_at']=0; path.write_text(json.dumps(expired))
        self.reviewed(); self.assertFalse(path.exists())
    def test_storage_hard_limit_and_catalog_match(self):
        self.api.setup()
        for i in range(64): (self.api.root/'plans'/f'{i}.json').write_text(json.dumps({'created_at':__import__('time').time()}))
        with self.assertRaisesRegex(ValueError,'history is full'): self.reviewed()
        config=json.loads((Path(__file__).resolve().parents[1]/'configs/host-os/software-catalog.json').read_text())
        self.assertEqual(config['packages'],CATALOG)
    def test_root_capacity_and_read_only_report(self):
        fs=type('FS',(),dict(f_flag=os.ST_RDONLY,f_bavail=1000000,f_frsize=4096,f_favail=2000))()
        with patch('sv08_software.os.statvfs',return_value=fs):
            with self.assertRaisesRegex(ValueError,'read-only'): Apt().root_capacity(0)
            self.assertGreater(Apt().root_capacity(0,writable=False)['root_free_bytes'],0)
            fs.f_bavail=1
            with self.assertRaisesRegex(ValueError,'space'): Apt().root_capacity(0,writable=False)


class AptServiceLifecycleTests(unittest.TestCase):
    def execution(self, action, installed=False, before=None, after=None):
        apt = Apt()
        calls = []
        apt.inventory = lambda: [['vnstat','2','arm64','ii ']] if installed else []
        states = iter([before,after]) if before else iter([])
        apt.service = lambda: next(states)
        apt.run = lambda command, **kwargs: calls.append((command,kwargs)) or ''
        apt.execute(action, {'package':'vnstat'}, 'lease')
        return calls

    def test_fresh_install_disables_postinst_enablement_after_apt(self):
        calls = self.execution('install')
        self.assertEqual([command[0] for command,kwargs in calls], ['apt-get','systemctl'])
        self.assertEqual(calls[1][0], ['systemctl','disable','--now','vnstat.service'])
        self.assertTrue(all(kwargs['token']=='lease' for command,kwargs in calls))

    def test_remove_stops_before_apt_while_policy_blocks_maintainer_stops(self):
        calls = self.execution('remove',installed=True)
        self.assertEqual(calls[0][0], ['systemctl','disable','--now','vnstat.service'])
        self.assertEqual(calls[1][0][0], 'apt-get')
        self.assertIn('remove',calls[1][0]); self.assertNotIn('purge',calls[1][0])

    def test_reinstall_preserves_existing_enabled_active_service(self):
        state = dict(UnitFileState='enabled',ActiveState='active')
        calls = self.execution('install',installed=True,before=state,after=state)
        self.assertEqual(len(calls),1); self.assertEqual(calls[0][0][0],'apt-get')

    def test_reinstall_restores_disabled_and_inactive_user_state(self):
        calls = self.execution('install',installed=True,
            before=dict(UnitFileState='disabled',ActiveState='inactive'),
            after=dict(UnitFileState='enabled',ActiveState='active'))
        self.assertEqual([command for command,kwargs in calls[1:]],
            [['systemctl','disable','vnstat.service'],['systemctl','stop','vnstat.service']])

    def test_reinstall_restores_enabled_active_user_state_if_changed(self):
        calls = self.execution('install',installed=True,
            before=dict(UnitFileState='enabled',ActiveState='active'),
            after=dict(UnitFileState='disabled',ActiveState='inactive'))
        self.assertEqual([command for command,kwargs in calls[1:]],
            [['systemctl','enable','vnstat.service'],['systemctl','start','vnstat.service']])


class AptSimulationTests(unittest.TestCase):
    def simulate(self,text,metadata='Size: 10\nInstalled-Size: 20\n',inventory=(),audit=''):
        apt=Apt()
        def run(command,*args,**kwargs):
            if command[:2]==['dpkg','--audit']: return audit
            if command[0]=='apt-get': return text
            if command[0]=='apt-mark': return ''
            return metadata
        apt.run=run
        return apt.simulate('install','nano',inventory)
    def test_dependency_versions_sizes_and_removal_protections(self):
        result=self.simulate('Inst nano (8.4 Debian:stable [arm64])\nInst libmagic1 (1 Debian:stable [arm64])\n')
        self.assertEqual(result['download_bytes'],20); self.assertEqual(result['installed_delta_bytes'],40*1024)
        for text in ('Remv openssh-server [1]\n','Inst linux-image-arm64 (1 Debian [arm64])\n'):
            with self.assertRaises(ValueError): self.simulate(text)
        with self.assertRaises(ValueError): self.simulate('Inst libmagic1 [1] (2 Debian [arm64])\n',inventory=[['libmagic1','1']])
        with self.assertRaises(ValueError): self.simulate('Inst libmagic1:arm64 [1] (2 Debian [arm64])\n',inventory=[['libmagic1','1']])
        with self.assertRaisesRegex(ValueError,'unfinished'): self.simulate('',audit='pending config')
        with self.assertRaisesRegex(ValueError,'metadata'): self.simulate('Inst nano (1 Debian [arm64])\n',metadata='')


if __name__=='__main__': unittest.main()
