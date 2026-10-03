"""Offline initial baseline, interruption, exact overlay and selected-tool tests."""
from contextlib import contextmanager, nullcontext
import copy
import base64
import fcntl
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid
import zlib

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'runtime'), str(REPO / 'scripts')]
import sv08_commissioning_health as health
import stage_commissioning_host as staging
from sv08_state import Store

BOOT_ID = '11111111-1111-4111-8111-111111111111'
# Ordinary tests use synthetic package metadata, never captured deployment input.
STOCK_BRANDING = b'/* synthetic stock package branding preimage */\n'
PREIMAGES = {
    '/usr/share/cockpit/branding/debian/branding.css': dict(
        kind='file', mode=0o644, bytes=len(STOCK_BRANDING),
        sha256=hashlib.sha256(STOCK_BRANDING).hexdigest(),
        source_base64=base64.b64encode(STOCK_BRANDING).decode()),
    '/usr/share/cockpit/branding/debian/badge.svg': dict(kind='absent'),
}


def historical_source_fixture(root):
    """Materialize immutable Git BASE independently of staging's closure walk.

    The caller owns/cleans this temporary tree. It is a source fixture, not a
    claim of matching an actual installed target or its deployment preimages.
    """
    paths = subprocess.check_output(
        ['git', '-C', str(REPO), 'ls-tree', '-r', '--name-only', staging.BASE, 'runtime'],
        text=True, timeout=3).splitlines()
    mapping = {path: 'usr/lib/sv08/' + Path(path).name
               for path in paths if path.endswith('.py')}
    mapping.update({'ui/host/' + name: 'usr/share/cockpit/sv08-host/' + name
                    for name in ('index.html', 'style.css', 'app.js', 'manifest.json')})
    for source, relative in mapping.items():
        data = subprocess.check_output(
            ['git', '-C', str(REPO), 'show', staging.BASE + ':' + source], timeout=3)
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if target.name == 'sv08_state.py' else 0o644)
    shell = root / 'etc/cockpit/cockpit.conf'
    shell.parent.mkdir(parents=True, exist_ok=True)
    shell.write_bytes(b'[WebService]\nShell=/sv08-host/index.html\n')
    return root


def image(flag, counter, extra='keep unchanged'):
    data = (f'BOOT_A_LEFT={counter}\0BOOT_B_LEFT=0\0BOOT_ORDER=A\0sv08_env_layout=ab-8gb-v1\0extra={extra}\0\0').encode().ljust(65531, b'\xff')
    return zlib.crc32(data).to_bytes(4, 'little') + bytes([flag]) + data


def config():
    closure = staging.dependency_closure()
    deps = {}
    for name, data in closure.items():
        if name in ('sv08_state', 'sv08_boot'):
            data = staging.source(staging.TLS, 'runtime/' + name + '.py')
        deps['/usr/lib/sv08/'+name+'.py'] = staging.sha(data)
    return dict(format_version=1, release='diagnostic-1', generation='diagnostic-1',
                disk=dict(path='/dev/mmcblk9', major_minor='179:72', sysfs='/sys/devices/synthetic/mmcblk9',
                          physical_bytes=32000000000, image_bytes=8000000000, disk_guid='22222222-2222-4222-8222-222222222222',
                          partition_records=[dict(number=n,name='SYNTHETIC-'+str(n),partuuid=f'00000000-0000-4000-8000-{n:012d}',offset_bytes=16*1024**2+n*1024**3,size_bytes=1024**3) for n in range(1,7)]),
                fw_config_sha256=staging.sha(b'/dev/mmcblk9 0x400000 0x10000\n/dev/mmcblk9 0x800000 0x10000\n'),
                tools=dict(package='libubootenv-tool', version='0.3.5-0.1+b2', files={
                    '/usr/bin/fw_printenv': health.SELECTED_TOOL_SHA256,
                    '/usr/bin/fw_setenv': health.SELECTED_TOOL_SHA256,
                    **{name: '0'*64 for name in ('/usr/lib/aarch64-linux-gnu/libubootenv.so.0.3.5',
                      '/usr/lib/aarch64-linux-gnu/libubootenv.so.0', '/usr/lib/aarch64-linux-gnu/libc.so.6',
                      '/usr/lib/aarch64-linux-gnu/libz.so.1', '/usr/lib/aarch64-linux-gnu/libyaml-0.so.2', '/lib/ld-linux-aarch64.so.1')}}), dependencies=deps)


class FixtureRuntime:
    def __init__(self, root, counter):
        self.store = Store(root)
        self.store.root.mkdir()
        (self.store.root / 'shared/logs/journal').mkdir(parents=True)
        self.clock = 0
        self.now = lambda: self.clock
        self.deadline = 60
        self.writes = 0
        self.calls = 0
        self.images = (image(1, counter), image(2, counter))
        self.values = health.bank(self.images[1])[1]
        self.fail = None
        self.change = None

    def probe(self):
        self.calls += 1
        if self.fail == 'prepare':
            raise ValueError('prepare inactive')
        result = dict(boot={'boot_id': BOOT_ID}, state={'pending': None}, manifest={'deployable': False}, images=self.images, values=self.values)
        if self.change and self.calls > 2:
            result[self.change] = {'changed': True}
        return copy.deepcopy(result)

    def sleep(self, seconds):
        self.clock += seconds

    def write(self):
        self.writes += 1
        if self.fail == 'prewrite':
            raise ValueError('tool refused')
        self.images = (image(3, 3), self.images[1])
        self.values = health.bank(self.images[0])[1]
        if self.fail == 'postwrite':
            raise TimeoutError('readback/flush unknown')


def holder(path, ready, stop):
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    ready.set()
    stop.wait(5)
    os.close(fd)


class CommissioningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix='commissioning-source-')
        cls.addClassCleanup(temporary.cleanup)
        cls.source = historical_source_fixture(Path(temporary.name))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_fixture(self, counter, **options):
        rt = FixtureRuntime(self.root / ('state-'+str(counter)), counter)
        for key, value in options.items():
            setattr(rt, key, value)
        with patch.object(health.Path, 'read_text', return_value=BOOT_ID):
            result = health.run(rt, nullcontext, nullcontext, sleep=rt.sleep)
        return rt, result

    def test_single_write_and_noop(self):
        for counter in (1, 2, 3):
            rt, result = self.run_fixture(counter)
            self.assertEqual(rt.writes, int(counter != 3))
            self.assertEqual(result, 'noop' if counter == 3 else 'confirmed')
            self.assertEqual(rt.clock, 5)
            self.assertEqual(health.without_counter(rt.values)['extra'], 'keep unchanged')
            with patch.object(health.Path, 'read_text', return_value=BOOT_ID):
                with self.assertRaisesRegex(ValueError, 'Same-boot'):
                    health.run(rt, nullcontext, nullcontext, sleep=rt.sleep)

    def test_failure_unknown_retry_and_midwindow(self):
        for number, fault in enumerate(('prepare', 'prewrite', 'postwrite', 'change', 'deadline')):
            rt = FixtureRuntime(self.root / str(number), 2)
            if fault == 'change': rt.change = 'boot'
            elif fault == 'deadline': rt.deadline = 2
            else: rt.fail = fault
            with patch.object(health.Path, 'read_text', return_value=BOOT_ID):
                with self.assertRaises((ValueError, TimeoutError)):
                    health.run(rt, nullcontext, nullcontext, sleep=rt.sleep)
                writes = rt.writes
                with self.assertRaisesRegex(ValueError, 'Same-boot'):
                    health.run(rt, nullcontext, nullcontext, sleep=rt.sleep)
                self.assertEqual(rt.writes, writes)
            record = json.loads(next((rt.store.root / 'shared/logs/journal/commissioning-health').glob('*.json')).read_text())
            self.assertEqual(record['status'], 'failed-or-unknown')

    def test_initial_baseline_refusals(self):
        root = self.root / 'state'; generation = root / 'generations/diagnostic-1'; generation.mkdir(parents=True)
        cfg = config()
        boot = dict(boot_id=BOOT_ID, slot='A', release='diagnostic-1', mode='immutable', generation=str(generation), trial=False, customized=False)
        state = dict(format_version=1, requested_mode='immutable', auto_update=True, pending=None,
                     slots={'A':dict(release='diagnostic-1', schema=1, generation='diagnostic-1', customized=False, parent_generation=None)})
        manifest = dict(release='diagnostic-1', state_schema=1, deployable=False)
        check = lambda b,s,m: health.validate_baseline(b,s,m,cfg,BOOT_ID,'rauc.slot=A',root)
        check(boot,state,manifest)
        cases=[]
        for key,value in [('boot_id',str(uuid.uuid4())),('slot','B'),('mode','writable'),('trial',True),('customized',True),('release','wrong'),('generation','wrong')]:
            b=copy.deepcopy(boot);b[key]=value;cases.append((b,state,manifest))
        for key,value in [('requested_mode','writable'),('pending',{}),('last_failed_trial',None)]:
            s=copy.deepcopy(state);s[key]=value;cases.append((boot,s,manifest))
        for key,value in [('parent_generation','old'),('customized',True),('schema',2),('release','wrong')]:
            s=copy.deepcopy(state);s['slots']['A'][key]=value;cases.append((boot,s,manifest))
        s=copy.deepcopy(state);s['slots']['B']=s['slots']['A'];cases.append((boot,s,manifest))
        for key,value in [('deployable',True),('state_schema',2),('release','wrong')]:
            m=copy.deepcopy(manifest);m[key]=value;cases.append((boot,state,m))
        for b,s,m in cases:
            with self.assertRaises(ValueError):check(b,s,m)

    def test_environment_exhaustion_crc_selection_and_other_variables(self):
        for key,value in [('BOOT_A_LEFT','0'),('BOOT_B_LEFT','1'),('BOOT_ORDER','A B'),('sv08_env_layout','wrong')]:
            values=health.bank(image(1,2))[1];values[key]=value
            with self.assertRaises(ValueError):health.eligible(values)
        with self.assertRaises(ValueError):health.bank(bytes(65536))
        with self.assertRaisesRegex(ValueError,'Ambiguous'):health.selected_bank((image(1,1),image(1,2)))
        for flags,selected in [((255,0),1),((0,255),0),((1,2),1),((254,255),1)]:
            self.assertEqual(health.selected_bank(tuple(image(f,1) for f in flags)),selected)
        before=(image(1,1),image(2,2))
        after=(image(3,3,'changed'),before[1])
        with self.assertRaises(ValueError):health.verify_readback(before,after,health.bank(after[0])[1])

    def test_real_state_boot_and_writer_lock_contention(self):
        from sv08_rauc_service import Service
        for leaf, acquire in [('.lock',lambda rt,path:rt.store.locked(nonblocking=True)),
                              ('boot.lock',lambda rt,path:health.boot_admission(path)),
                              ('writer.lock',lambda rt,path:Service(lock=path).writer())]:
            rt=FixtureRuntime(self.root/leaf.replace('.','-'),2);path=rt.store.root/leaf
            ready,stop=multiprocessing.Event(),multiprocessing.Event()
            child=multiprocessing.Process(target=holder,args=(str(path),ready,stop));child.start()
            self.addCleanup(lambda c=child:c.is_alive() and c.terminate())
            self.assertTrue(ready.wait(2))
            try:
                with self.assertRaises((ValueError,BlockingIOError)):
                    # Real flock contention on worker-owned files. Only root identity
                    # metadata is simulated; this does not test installed ownership.
                    real_fstat = os.fstat
                    def root_stat(fd):
                        info = real_fstat(fd)
                        return type('Info', (), dict(st_mode=info.st_mode, st_uid=0, st_nlink=info.st_nlink))
                    with patch.object(health.os, 'geteuid', return_value=0), patch.object(health.os, 'fstat', side_effect=root_stat):
                        with acquire(rt,path):pass
            finally:stop.set();child.join(2)

    def test_retention_full_storage_and_interrupted_record(self):
        rt=FixtureRuntime(self.root/'state',2)
        directory=rt.store.root/'shared/logs/journal/commissioning-health';directory.mkdir()
        for number in range(16):
            (directory/(str(number)+'.json')).write_bytes(b'x'*health.RECORD_LIMIT)
        with self.assertRaisesRegex(ValueError,'Cannot retain'):health.Diagnostics(rt.store,BOOT_ID)
        self.assertEqual(sum(p.stat().st_size for p in directory.iterdir()),health.RETAINED_LIMIT)
        rt2=FixtureRuntime(self.root/'state2',2)
        with patch.object(health.os,'statvfs',return_value=type('FS',(),dict(f_bavail=0,f_frsize=4096,f_favail=0))):
            with self.assertRaises(ValueError):health.Diagnostics(rt2.store,BOOT_ID)
        record=health.Diagnostics(rt2.store,BOOT_ID);record.save('unknown-outcome')
        with self.assertRaisesRegex(ValueError,'Same-boot'):health.Diagnostics(rt2.store,BOOT_ID)
        self.assertEqual(json.loads(record.path.read_text())['status'],'unknown-outcome')

    def test_bounded_process_timeout_and_overflow(self):
        runtime=health.Runtime(config())
        for code in ["import time;time.sleep(4)", "print('x'*40000)"]:
            with self.assertRaisesRegex(ValueError,'timed out|overflow'):
                runtime.command([sys.executable,'-c',code])
        runtime.deadline=runtime.now()-1
        with self.assertRaisesRegex(ValueError,'deadline'):runtime.command([sys.executable,'-c','pass'])

    def test_overlay_exact_historical_tls_deterministic_and_conflicts(self):
        cfg=config()
        one=staging.stage(self.source,cfg,deployment_preimages=PREIMAGES)
        two=staging.stage(self.source,cfg,deployment_preimages=PREIMAGES)
        self.assertEqual(one,two)
        result=staging.stage(self.source,cfg,self.root/'overlay',True,deployment_preimages=PREIMAGES)
        output=self.root/'overlay/rootfs'
        self.assertEqual((output/'usr/lib/sv08/sv08_state.py').read_bytes(),staging.source(staging.TLS,'runtime/sv08_state.py'))
        self.assertNotIn(b'sv08_data_budget',(output/'usr/lib/sv08/sv08_state.py').read_bytes())
        # Existing sv08-state symlink executes this file directly. TLS overlay
        # must preserve its installed executable mode, while boot stays 0644.
        for name,mode in [('sv08_state.py',0o755),('sv08_boot.py',0o644)]:
            relative='usr/lib/sv08/'+name
            self.assertEqual(result['preimages'][relative]['mode'],mode)
            self.assertEqual(result['files'][relative]['mode'],mode)
            self.assertEqual((output/relative).stat().st_mode&0o777,mode)
        commands=output/'usr/bin';commands.mkdir()
        command=commands/'sv08-state';command.symlink_to('../lib/sv08/sv08_state.py')
        self.assertEqual(os.readlink(command),'../lib/sv08/sv08_state.py')
        help_result=subprocess.run([str(command),'--help'],capture_output=True,text=True,timeout=3)
        self.assertEqual(help_result.returncode,0,help_result.stderr)
        self.assertIn('usage:',help_result.stdout)
        self.assertEqual(os.readlink(command),'../lib/sv08/sv08_state.py')

        self.assertFalse((output/'usr/share/cockpit/sv08-host/app.js').exists())
        self.assertFalse((output/'etc/systemd/system').exists())
        self.assertEqual(json.loads((output/'usr/lib/sv08/admin-context.json').read_text()),dict(format_version=1,context='host'))
        for rel,entry in result['files'].items():
            self.assertEqual(staging.sha((output/rel).read_bytes()),entry['sha256'])
            self.assertEqual((output/rel).stat().st_mode&0o777,entry['mode'])
        with self.assertRaises(ValueError):staging.stage(self.source,cfg,self.root/'overlay',True,deployment_preimages=PREIMAGES)
        bad=copy.deepcopy(cfg);bad['dependencies']['/usr/lib/sv08/sv08_state.py']='0'*64
        with self.assertRaisesRegex(ValueError,'closure'):staging.stage(self.source,bad,deployment_preimages=PREIMAGES)
        with self.assertRaises(ValueError):staging.check_target(output,result)

    def test_copied_target_preflight_dependency_and_preimage_conflicts(self):
        manifest = staging.stage(self.source,config(),deployment_preimages=PREIMAGES)
        copied = self.root/'copied-target';copied.mkdir()
        for rel,entry in manifest['preimages'].items():
            path=copied/rel
            if entry['kind']=='file':
                if rel.startswith('usr/share/cockpit/branding/'):
                    import base64
                    path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(base64.b64decode(PREIMAGES['/'+rel]['source_base64']));path.chmod(entry['mode']);continue
                repo_path=('runtime/'+Path(rel).name if rel.startswith('usr/lib/sv08/') else 'ui/host/'+Path(rel).name)
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(staging.source(staging.BASE,repo_path));path.chmod(entry['mode'])
            elif entry['kind']=='empty-directory':
                path.mkdir(parents=True);path.chmod(entry['mode'])
            elif entry['kind']=='requires-coordinator-capture':
                # Synthetic absence is allowed only in this copied fixture;
                # coordinator must capture real stock branding independently.
                entry['kind']='absent'
        for rel,entry in manifest['unchanged'].items():
            path=copied/rel;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((self.source/rel).read_bytes());path.chmod(entry['mode'])
        for rel in manifest['dependency_closure']:
            if rel.lstrip('/') in manifest['files']:continue
            path=copied/rel.lstrip('/');path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(staging.source(staging.BASE,'runtime/'+path.name))
        self.assertTrue(staging.check_target(copied,manifest))
        path=copied/'usr/lib/sv08/sv08_transaction.py';original=path.read_bytes();path.unlink()
        with self.assertRaisesRegex(ValueError,'dependency'):staging.check_target(copied,manifest)
        path.write_bytes(original)
        config_path=copied/'usr/lib/sv08/admin-context.json';config_path.write_text('owner conflict')
        with self.assertRaisesRegex(ValueError,'conflict'):staging.check_target(copied,manifest)
        self.assertEqual(config_path.read_text(),'owner conflict')

    def test_staging_uses_immutable_css_base_and_default_hook_is_inert(self):
        with patch.object(staging,'source',wraps=staging.source) as read:
            staging.stage(self.source,config(),deployment_preimages=PREIMAGES)
        css_reads=[call.args[0] for call in read.call_args_list if call.args[1]=='ui/host/style.css']
        self.assertTrue(css_reads)
        self.assertEqual(set(css_reads),{staging.BASE})
        from test_host_integration import IntegrationManifestTests
        fixture=IntegrationManifestTests('test_refresh_replaces_only_a_reviewed_existing_runtime')
        captured=[]
        import integrate_host_os
        actual=integrate_host_os.stage
        def stage(*args,**kwargs):
            result=actual(*args,**kwargs);captured.append(args[0]/'rootfs');return result
        try:
            with patch('test_host_integration.stage',side_effect=stage):fixture.test_refresh_replaces_only_a_reviewed_existing_runtime()
            root=captured[0]
            self.assertTrue((root/'usr/lib/sv08/sv08_commissioning_health.py').is_file())
            for rel in ('usr/lib/systemd/system/sv08-commissioning-health.service',
                        'etc/sv08/commissioning-target.json','etc/sv08/commissioning-fw_env.config',
                        'etc/systemd/system/multi-user.target.wants/sv08-commissioning-health.service'):
                self.assertFalse(health.present(root/rel))
        finally:fixture.doCleanups()

    def test_real_sigkill_before_and_after_write_prevents_retry(self):
        for phase in ('health', 'after-write'):
            rt = FixtureRuntime(self.root/phase, 2)
            ready = multiprocessing.Event()
            def child_run():
                if phase == 'health':
                    def probe():
                        ready.set()
                        time.sleep(10)
                    rt.probe = probe
                else:
                    original = rt.write
                    def write():
                        original()
                        (rt.store.root/'mutation').write_text('one selected write fixture')
                        ready.set()
                        time.sleep(10)
                    rt.write = write
                with patch.object(health.Path, 'read_text', return_value=BOOT_ID):
                    health.run(rt, nullcontext, nullcontext, sleep=rt.sleep)
            child = multiprocessing.Process(target=child_run)
            child.start()
            self.assertTrue(ready.wait(3))
            child.kill()
            child.join(2)
            self.assertEqual(child.exitcode, -9)
            with self.assertRaisesRegex(ValueError,'Same-boot'):
                health.Diagnostics(rt.store,BOOT_ID)
            record = json.loads((rt.store.root/'shared/logs/journal/commissioning-health'/ (BOOT_ID+'.json')).read_text())
            self.assertEqual(record['status'],'checking' if phase=='health' else 'unknown-outcome')
            self.assertEqual((rt.store.root/'mutation').exists(),phase=='after-write')

    def test_probe_every_journal_phase_masks_and_rauc_composition(self):
        rt = health.Runtime(config())
        rt.store = Store(self.root/'state')
        generation = rt.store.root/'generations/diagnostic-1'
        generation.mkdir(parents=True)
        state = dict(format_version=1,requested_mode='immutable',auto_update=True,pending=None,
            slots={'A':dict(release='diagnostic-1',schema=1,generation='diagnostic-1',customized=False,parent_generation=None)})
        (rt.store.root/'state.json').write_text(json.dumps(state))
        boot = dict(slot='A',release='diagnostic-1',mode='immutable',generation=str(generation),
                    trial=False,customized=False,boot_id=BOOT_ID)
        manifest = dict(release='diagnostic-1',state_schema=1,deployable=False)
        images = (image(1,2),image(2,2))
        cmdline = 'rauc.slot=A '+ ' '.join('systemd.mask='+name+'.service' for name in health.MASKS)
        original_read = Path.read_text
        def read_text(path,*args,**kwargs):
            if str(path)=='/proc/cmdline':return cmdline
            if str(path)=='/proc/sys/kernel/random/boot_id':return BOOT_ID
            return original_read(path,*args,**kwargs)
        original_json = health.read_json
        def read_json(path):
            if str(path)=='/run/sv08/boot.json':return boot
            if str(path)=='/usr/lib/sv08/release.json':return manifest
            return original_json(path)
        extra_present = set()
        original_present = health.present
        def present(path):
            if str(path).startswith('/run/sv08') or str(path).startswith('/usr/lib/sv08') or str(path)=='/etc/rauc/system.conf':
                return str(path) in extra_present
            return original_present(path)
        active = 'inactive'
        def command(args):
            return 'active' if args[1]=='is-active' else active
        original_link = Path.is_symlink
        def is_symlink(path):
            return True if str(path).startswith('/etc/systemd/system/') else original_link(path)
        with patch.object(health.Path,'read_text',read_text), patch.object(health,'read_json',read_json), \
             patch.object(health,'present',present), patch.object(health.Path,'is_symlink',is_symlink), \
             patch.object(health.os,'readlink',return_value='/dev/null'), \
             patch.object(rt,'tool_identity'),patch.object(rt,'devices'),patch.object(rt,'command',side_effect=command), \
             patch.object(rt,'environment',return_value=(images,health.bank(images[1])[1])):
            # generation link test is real outside this system-mask shim.
            with patch.object(health,'validate_baseline'):
                rt.probe()
                for phase in ('staging','staged','arming','armed','confirming','complete','cancelled','failed','unknown'):
                    (rt.store.root/'update.json').write_text(json.dumps({'phase':phase}))
                    with self.assertRaisesRegex(ValueError,'composition'):rt.probe()
                    (rt.store.root/'update.json').unlink()
                for unit in health.MASKS:
                    original = cmdline
                    cmdline = cmdline.replace('systemd.mask='+unit+'.service','')
                    with self.assertRaisesRegex(ValueError,'mask'):rt.probe()
                    cmdline = original
                for path in ('/run/sv08/trial','/run/sv08/rauc-operation.json','/etc/rauc/system.conf',
                             '/usr/lib/sv08/layout.json','/usr/lib/sv08/environment.json','/usr/lib/sv08/update-policy.json'):
                    extra_present.add(path)
                    with self.assertRaisesRegex(ValueError,'composition'):rt.probe()
                    extra_present.clear()
                for active in ('active','activating','deactivating','unknown'):
                    with self.assertRaisesRegex(ValueError,'RAUC'):rt.probe()

    def test_installed_old_store_api_with_tls_delta(self):
        closure=staging.dependency_closure()
        modules=self.root/'historical';modules.mkdir()
        for name,data in closure.items():
            if name in ('sv08_state','sv08_boot'):
                data=staging.source(staging.TLS,'runtime/'+name+'.py')
            (modules/(name+'.py')).write_bytes(data)
        code = "import sys; from pathlib import Path; from sv08_state import Store; import sv08_commissioning_health as h; s=Store(sys.argv[1],reserve_bytes=0); s.initialize(); assert not hasattr(s,'budget'); s.prepare_boot('A','diagnostic-1',1); print('old Store and full import closure OK')"
        result=subprocess.run([sys.executable,'-c',code,str(self.root/'historical-state')],
            env={**os.environ,'PYTHONPATH':str(modules),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_device_gpt_and_mount_identity_refusals(self):
        cfg = config()
        disk = self.root/'disk';disk.write_bytes(b'fixture')
        sysfs = self.root/'sysfs/disk';sysfs.mkdir(parents=True)
        (sysfs/'size').write_text('32768')
        cfg['disk'].update(path=str(disk),sysfs=str(sysfs),major_minor='179:0',physical_bytes=32768*512,image_bytes=16384*512)
        partitions=[]
        mappings={}
        manifest={'devices':{}}
        for number,key in enumerate(('root-a','boot-a','data'),1):
            part=sysfs/('p'+str(number));part.mkdir()
            (part/'partition').write_text(str(number));(part/'start').write_text(str(20000+number*10));(part/'size').write_text('10')
            uid=f'00000000-0000-4000-8000-{number:012d}'
            path='/dev/disk/by-partuuid/'+uid
            manifest['devices'][key]=path;mappings[path]='179:'+str(number)
            partitions.append(dict(number=number,name=key,partuuid=uid,offset_bytes=(20000+number*10)*512,size_bytes=5120))
        partitions += [dict(number=n,name='other',partuuid=f'00000000-0000-4000-8000-{n:012d}',offset_bytes=1,size_bytes=1) for n in range(4,7)]
        cfg['disk']['partition_records']=partitions
        runtime=health.Runtime(cfg)
        observed=dict(disk_guid=cfg['disk']['disk_guid'],partition_records=copy.deepcopy(partitions),partitions=6)
        original_stat=Path.lstat;original_resolve=Path.resolve
        def lstat(path,*args,**kwargs):
            if path==disk:return type('Disk',(),dict(st_mode=0o060600,st_rdev=os.makedev(179,0)))
            return original_stat(path,*args,**kwargs)
        def resolve(path,*args,**kwargs):
            if str(path)=='/sys/dev/block/179:0':return sysfs
            if str(path).startswith('/sys/dev/block/179:'):
                return sysfs/('p'+str(path).split(':')[-1])
            return original_resolve(path,*args,**kwargs)
        output={'/':'179:1 ro,relatime','/boot':'179:2 ro,relatime','/data':'179:3 rw,relatime'}
        with patch.object(health.Path,'lstat',lstat),patch.object(health.Path,'resolve',resolve), \
             patch.object(health,'device_number',side_effect=lambda path:mappings[path]), \
             patch.object(health,'inspect',side_effect=lambda *a,**k:observed) as inspector, \
             patch.object(runtime,'command',side_effect=lambda argv:output[argv[-1]]):
            runtime.devices(manifest)
            self.assertEqual(inspector.call_args.kwargs['image_bytes'],16384*512)
            self.assertNotEqual(inspector.call_args.kwargs['image_bytes'],cfg['disk']['physical_bytes'])
            for mount in output:
                previous=output[mount];output[mount]='179:99 rw'
                with self.assertRaisesRegex(ValueError,'Mount'):runtime.devices(manifest)
                output[mount]=previous
            for key,value in [('disk_guid','wrong'),('partitions',5),('partition_records',[])]:
                previous=observed[key];observed[key]=value
                with self.assertRaisesRegex(ValueError,'GPT'):runtime.devices(manifest)
                observed[key]=previous
            (sysfs/'p2/start').write_text('1')
            with self.assertRaisesRegex(ValueError,'GPT/disk'):runtime.devices(manifest)
            (sysfs/'p2/start').write_text('20020')
            cfg['disk']['major_minor']='179:99'
            with self.assertRaisesRegex(ValueError,'disk identity'):runtime.devices(manifest)

    def test_config_selection_and_input_overflow(self):
        cfg=config();health.validate_config(cfg)
        for change in ('package','version','binary','missing-loader'):
            bad=copy.deepcopy(cfg)
            if change in ('package','version'):bad['tools'][change]='wrong'
            elif change=='binary':bad['tools']['files']['/usr/bin/fw_printenv']='0'*64
            else:del bad['tools']['files']['/lib/ld-linux-aarch64.so.1']
            with self.assertRaises(ValueError):health.validate_config(bad)
        path=self.root/'oversized.json';path.write_bytes(b'x'*65537)
        with self.assertRaisesRegex(ValueError,'oversized'):health.read_json(path)


class SelectedToolTests(unittest.TestCase):
    def test_real_selected_libubootenv_regular_file(self):
        if not os.environ.get('SV08_SELECTED_TOOL_TEST'):
            self.skipTest('enable explicit assigned selected-tool regular-file fixture')
        selected_path = os.environ.get('SV08_SELECTED_TOOL_ROOT')
        self.assertTrue(selected_path, 'Opt-in selected-tool test requires SV08_SELECTED_TOOL_ROOT')
        selected_root = Path(selected_path)
        self.assertTrue(selected_root.is_absolute() and selected_root.is_dir(),
                        'Selected ARM64 root must be an explicit existing absolute directory')
        tool=selected_root/'usr/bin/fw_printenv'
        self.assertEqual(health.digest(tool),health.SELECTED_TOOL_SHA256)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);disk=root/'disk';config_path=root/'fw.config'
            with disk.open('wb') as stream:stream.truncate(0x820000)
            config_path.write_text(f'{disk} 0x400000 0x10000\n{disk} 0x800000 0x10000\n')
            def call(name,*arguments):
                argv=['sudo','-n','/usr/bin/qemu-aarch64-static','-L',str(selected_root),str(selected_root/'usr/bin'/name),'-c',str(config_path),*arguments]
                result=subprocess.run(argv,capture_output=True,text=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr)
                return result.stdout
            cases=[]
            for flags in [(1,2),(254,255),(255,0),(0,255),(0,1),(1,0)]:
                for counter in (1,2,3):
                    with disk.open('r+b') as stream:
                        for offset,flag in zip((0x400000,0x800000),flags):stream.seek(offset);stream.write(image(flag,counter))
                    before=disk.read_bytes();images=tuple(before[o:o+65536] for o in (0x400000,0x800000))
                    health.verify_environment_copies(config_path)
                    values=health.parse_environment(call('fw_printenv'))
                    self.assertEqual(values,health.bank(images[health.selected_bank(images)])[1])
                    if counter != 3:call('fw_setenv','BOOT_A_LEFT','3')
                    after=disk.read_bytes();after_images=tuple(after[o:o+65536] for o in (0x400000,0x800000))
                    health.verify_environment_copies(config_path)
                    post=health.parse_environment(call('fw_printenv'))
                    if counter==3:self.assertEqual(before,after)
                    else:health.verify_readback(images,after_images,post)
                    for start,end in [(0,0x400000),(0x410000,0x800000),(0x810000,len(before))]:self.assertEqual(before[start:end],after[start:end])
                    cases.append(dict(flags=flags,counter=counter,selected_before=health.selected_bank(images),selected_after=health.selected_bank(after_images)))
            destination=os.environ.get('SV08_TOOL_EVIDENCE')
            if destination:Path(destination).write_text(json.dumps(dict(binary_sha256=health.digest(tool),package='0.3.5-0.1+b2',regular_file_only=True,cases=cases),indent=2)+'\n')
