from contextlib import contextmanager
import copy
import hashlib
from types import SimpleNamespace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sv08_recovery_media import WRITER_MODEL, MediaLease, fingerprint
from sv08_recovery_restore_media import RestoreMediaProvider, RestoreAdapter, PROTOCOL, production_adapter


def policy():
    identity=lambda serial:dict(stable={'serial':serial},partition=1,start=1,sectors=2,filesystem_uuid=serial)
    return dict(format_version=1,protocol=PROTOCOL,writer_model=WRITER_MODEL,recovery=identity('recovery'),recovery_path='/',
        image_manifest_sha256='a'*64,envelope_manifest_sha256='b'*64,media=[{'fixture':'reviewed'}],
        archives={'backup':dict(label='Archive USB',mount='/run/restore-archive',identity=identity('archive'),path='/run/restore-archive/backup.tar')},
        targets={'target':dict(label='Prepared data target',mount='/run/restore-target',identity=identity('target'),
                              root='/run/restore-target/data',fresh_root='/run/restore-target/sv08')})


class ProviderTests(unittest.TestCase):
    def provider(self,p=None):
        p=p or policy()
        return RestoreMediaProvider(p,dict(format_version=1,protocol=PROTOCOL,policy_sha256=fingerprint(p),expected={'fixture':'expected'}))
    def test_fixed_production_inputs_fail_closed(self):
        with patch('sv08_recovery_restore_media.trusted_file',side_effect=FileNotFoundError('not provisioned')):
            adapter=production_adapter()
        self.assertFalse(adapter.capability('recovery.data-restore',{})[0])
        self.assertIn('not provisioned',adapter.capability('recovery.initialize',{})[1])
    def test_policy_refuses_ids_paths_overlap_aliases_and_unbound_context(self):
        mutations=[lambda p:p['targets']['target'].__setitem__('root','/etc/other'),
                   lambda p:p['archives']['backup'].__setitem__('path','/run/restore-archive/../escape'),
                   lambda p:p['targets']['target'].__setitem__('identity',p['archives']['backup']['identity']),
                   lambda p:p.__setitem__('writer_model','arbitrary writers'),
                   lambda p:p['targets'].__setitem__('/dev/sda',p['targets'].pop('target'))]
        for mutate in mutations:
            p=policy();mutate(p)
            with self.assertRaises(ValueError):self.provider(p)
        with self.assertRaisesRegex(ValueError,'context'):
            RestoreMediaProvider(policy(),dict(format_version=1,protocol=PROTOCOL,policy_sha256='x',expected={}))
    def test_expected_snapshot_stale_and_recheck_changes_refuse_under_shared_lease(self):
        provider=self.provider()
        events=[]
        @contextmanager
        def lease(path):
            class Held:
                def check(self): events.append('check')
            events.append('enter');yield Held();events.append('exit')
        with patch('sv08_recovery_restore_media.MediaLease',lease),patch.object(provider,'snapshot',return_value={'changed':True}):
            with self.assertRaisesRegex(ValueError,'context changed'):
                with provider.admission('target'): pass
        with patch('sv08_recovery_restore_media.MediaLease',lease),patch.object(provider,'snapshot',side_effect=[{'fixture':'expected'},{'changed':True}]):
            with self.assertRaisesRegex(ValueError,'media changed'):
                with provider.admission('target') as guard: guard.recheck()
        self.assertIn('check',events)
        with self.assertRaises(ValueError):
            with provider.admission('/dev/sda'):pass
    def test_one_controller_status_verifies_two_snapshots_without_mutation_or_nested_lease(self):
        from sv08_recovery import RecoveryController
        from sv08_recovery_restore_media import Composite
        from sv08_recovery_media import Unavailable
        from sv08_state import Store
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=policy();p['boot']=dict(slot='A',release='fixture-release',state_schema=1,release_revision=7)
            p['targets']['target'].update(mount=str(root),root=str(root/'restored'),fresh_root=str(root/'fresh'))
            provider=self.provider(p);events=[];held=[]
            @contextmanager
            def lease(path):
                self.assertFalse(held,'Status attempted a nested media lease')
                held.append(True);events.append('enter')
                class Guard:
                    def check(self):events.append('check')
                try:yield Guard()
                finally:held.pop();events.append('exit')
            controller=RecoveryController(Store(root/'missing-registry'),Composite(Unavailable('No export policy'),provider))
            before=list(root.iterdir())
            with patch('sv08_recovery_restore_media.MediaLease',lease),patch.object(provider,'snapshot',return_value={'fixture':'expected'}) as snapshots:
                status=controller.status()
                self.assertEqual(snapshots.call_count,2)
                self.assertEqual(events.count('enter'),1)
                self.assertEqual(events.count('exit'),1)
                self.assertTrue(status['capabilities']['recovery.initialize']['available'])
                self.assertFalse(status['capabilities']['recovery.activate']['available'])
                self.assertEqual(list(root.iterdir()),before)
                # A second refresh verifies again; there is no persistent trusted result.
                controller.status();self.assertEqual(snapshots.call_count,4)
                snapshots.reset_mock()
                plan=provider.review_restore('recovery.initialize',dict(target='target'))
                self.assertEqual(snapshots.call_count,2,'Review must retain full admission/recheck')
                self.assertEqual(list(root.iterdir()),before)
            with patch('sv08_recovery_restore_media.MediaLease',lease),patch.object(provider,'snapshot',return_value={'changed':True}):
                with self.assertRaisesRegex(ValueError,'context changed'):
                    provider.review_restore('recovery.initialize',dict(target='target'))
                with self.assertRaisesRegex(ValueError,'context changed'):
                    provider.apply(dict(action='recovery.initialize',arguments=dict(target='target'),restore=plan))
            self.assertEqual(list(root.iterdir()),before)

    def test_status_changed_media_at_exit_withholds_all_available_actions(self):
        provider=self.provider()
        @contextmanager
        def lease(path):
            class Guard:
                def check(self):pass
            yield Guard()
        with patch('sv08_recovery_restore_media.MediaLease',lease),patch.object(provider,'snapshot',side_effect=[{'fixture':'expected'},{'changed':True}]) as snapshots:
            result=provider.status_capabilities({})
        self.assertEqual(snapshots.call_count,2)
        self.assertTrue(all(not available and 'changed during status' in reason for available,reason in result.values()))

    def test_installed_status_defers_eager_validation_only_to_its_batched_refresh(self):
        from sv08_recovery import installed_controller
        from sv08_recovery_media import canonical_json, Unavailable
        p=policy();context=dict(format_version=1,protocol=PROTOCOL,policy_sha256=fingerprint(p),expected={'fixture':'expected'})
        @contextmanager
        def lease(path):
            class Guard:
                def check(self):pass
            yield Guard()
        def trusted(path):return canonical_json(p if str(path).endswith('policy.json') else context)
        with patch('sv08_recovery_restore_media.trusted_file',side_effect=trusted), \
             patch('sv08_recovery_media.production_adapter',return_value=Unavailable('No export policy')), \
             patch('sv08_recovery_restore_media.MediaLease',lease), \
             patch.object(RestoreMediaProvider,'snapshot',return_value={'fixture':'expected'}) as snapshots:
            controller=installed_controller();self.assertEqual(snapshots.call_count,0)
            controller.status();self.assertEqual(snapshots.call_count,2)
            production_adapter();self.assertEqual(snapshots.call_count,4,'Standalone production adapter keeps eager validation')

    def test_shared_media_lock_contention_blocks_restore(self):
        provider=self.provider()
        with tempfile.TemporaryDirectory() as d:
            os.chmod(d,0o700);provider.lock=Path(d)/'media.lock'
            real_stat=os.fstat
            def fixture_stat(fd):
                value=real_stat(fd)
                return SimpleNamespace(st_uid=0,st_dev=value.st_dev,st_ino=value.st_ino,st_mode=value.st_mode,st_nlink=value.st_nlink)
            with patch('sv08_recovery_media.os.fstat',side_effect=fixture_stat),MediaLease(provider.lock),patch.object(provider,'snapshot',return_value={'fixture':'expected'}):
                self.assertFalse(provider.capability('recovery.data-restore',{})[0])
                with self.assertRaisesRegex(ValueError,'owns admission'):
                    with provider.admission('target'):pass
    def test_complete_snapshot_recovery_archive_target_and_runtime_binding(self):
        from sv08_recovery_media import canonical_json
        provider=self.provider()
        def mount(path, device, fs, mode):
            return dict(path=path,device=device,root='/',options=[mode],super_options=[mode,'norecovery'],optional=[],filesystem=fs)
        mounts=[mount('/','8:1','ext4','ro'),mount('/proc','0:1','proc','rw'),mount('/sys','0:2','sysfs','rw'),
                mount('/usr','7:0','squashfs','ro'),mount('/run/restore-archive','9:1','ext4','ro'),mount('/run/restore-target','10:1','ext4','rw')]
        blocks={}
        roles=[('/',provider.policy['recovery'],False),('/run/restore-archive',provider.policy['archives']['backup']['identity'],False),
               ('/run/restore-target',provider.policy['targets']['target']['identity'],True)]
        for index,(path,ident,writable) in enumerate(roles):
            m=next(m for m in mounts if m['path']==path)
            blocks[path]=dict(ident,device=m['device'],sysfs='sysfs-'+path,sysfs_inode=index+1,disk='disk-'+path,
                disk_device=m['device'],diskseq=1,readonly=not writable,disk_readonly=not writable,
                filesystem='ext4',partuuid='part-'+path,partitions=[],removable=False)
        inventory=list(blocks.values())
        source=b'fixture runtime bytes'
        names=('sv08_recovery_prepare.py','sv08_recovery_activation.py','sv08_recovery_restore_prepare.py','sv08_restore.py','sv08_recovery_restore_media.py','sv08_recovery.py','sv08_recovery_ui.py','sv08_admin.py',
               'sv08_export.py','sv08_recovery_media.py','sv08_state.py','sv08_admin_history.py','sv08_admin_jobs.py','sv08_data_budget.py','sv08_update_policy.py')
        manifest=dict(format_version=2,kind='sv08-independent-recovery-provider',protocol='sv08-recovery-media-v1',policy_sha256='c'*64,
                      inputs={'runtime/'+name:hashlib.sha256(source).hexdigest() for name in names})
        for name in ('sv08-recovery-prepare.service','sv08-recovery-restore-prepare.service','sv08-recovery-private-mounts.service','recovery-systemd-udevd.conf','recovery-systemd-logind.conf'):
            manifest['inputs']['configs/host-os/'+name]=hashlib.sha256(source).hexdigest()
        from sv08_recovery_restore_prepare import policy_binding
        provider.policy['envelope_manifest_sha256']=hashlib.sha256(b'fixture envelope bytes').hexdigest()
        manifest['inputs']['restore_policy']=policy_binding(provider.policy)
        manifest_data=canonical_json(manifest)
        provider.policy['image_manifest_sha256']=hashlib.sha256(manifest_data).hexdigest()
        envelope=b'fixture envelope bytes'; provider.policy['envelope_manifest_sha256']=hashlib.sha256(envelope).hexdigest()
        files={}; path_to_fd={}; fd_to_path={}
        @contextmanager
        def opened(path,**kwargs):
            path=str(path)
            if path not in path_to_fd:path_to_fd[path]=len(path_to_fd)+100;fd_to_path[path_to_fd[path]]=path
            yield path_to_fd[path]
        def info(fd):
            path=fd_to_path[fd]; b=blocks.get(path,blocks['/']);major,minor=map(int,b['device'].split(':'))
            return SimpleNamespace(st_dev=os.makedev(major,minor),st_ino=123)
        def fs(fd):return SimpleNamespace(f_flag=0 if fd_to_path[fd]=='/run/restore-target' else os.ST_RDONLY)
        def trusted(path):
            path=str(path)
            if path.endswith('recovery-image.json'):return manifest_data
            if path.endswith('recovery-envelope.manifest'):return envelope
            return source
        command='sv08.recovery='+provider.policy['image_manifest_sha256']+' sv08.envelope='+provider.policy['envelope_manifest_sha256']
        compressed=dict(loop_device='7:0',backing=[1,2,3])
        with patch.object(provider.kernel,'mounts',return_value=mounts),patch.object(provider.kernel,'session',return_value={'boot':'fixture'}),\
             patch.object(provider.kernel,'inventory',return_value=inventory),patch.object(provider.kernel,'block',side_effect=lambda m:blocks[m['path']]),\
             patch.object(provider.kernel,'active_loops',return_value=[]),patch('sv08_recovery_restore_media.reviewed_inventory',return_value=provider.policy['media']),\
             patch('sv08_recovery_restore_media.opened',opened),patch('sv08_recovery_restore_media.os.fstat',side_effect=info),\
             patch('sv08_recovery_restore_media.os.fstatvfs',side_effect=fs),patch('sv08_recovery_restore_media.trusted_file',side_effect=trusted),\
             patch('sv08_recovery_restore_media.Path.read_text',return_value=command),\
             patch('sv08_recovery_restore_media.strict_envelope_manifest',return_value=dict(root_uuid='recovery',root_bytes=1024)),\
             patch('sv08_recovery_restore_media.MediaProvider.compressed_userspace',return_value=compressed),\
             patch('sv08_recovery_restore_media.validate_usr_loop_inventory',return_value=dict(device='7:0',backing_identity=[1,2,3])):
            result=provider.snapshot();self.assertEqual(result['targets']['target']['block']['readonly'],False)
            blocks['/run/restore-archive']['readonly']=False
            with self.assertRaisesRegex(ValueError,'write protection'):provider.snapshot()
            blocks['/run/restore-archive']['readonly']=True
            mounts[-1]['options']=['ro']
            with self.assertRaisesRegex(ValueError,'mount mode'):provider.snapshot()
            mounts[-1]['options']=['rw']
            mounts.append(dict(mounts[-1],path='/run/alias'))
            with self.assertRaisesRegex(ValueError,'alias'):provider.snapshot()
            mounts.pop()
            source=b'changed installed runtime'
            with self.assertRaisesRegex(ValueError,'runtime differs'):provider.snapshot()

    def test_kernel_wrong_identity_or_rw_archive_refused_before_any_write(self):
        provider=self.provider()
        mount=lambda path,dev,mode:dict(path=path,device=dev,root='/',options=[mode],super_options=[mode,'norecovery'],optional=[],filesystem='ext4')
        mounts=[mount('/','8:1','ro'),dict(path='/proc',device='0:1',filesystem='proc',root='/',super_options=[],optional=[]),
                dict(path='/sys',device='0:2',filesystem='sysfs',root='/',optional=[])]
        block=dict(provider.policy['recovery'],readonly=True,disk_readonly=True)
        with patch.object(provider.kernel,'mounts',return_value=mounts),patch.object(provider.kernel,'session',return_value={}),\
             patch.object(provider.kernel,'inventory',return_value=[]),patch('sv08_recovery_restore_media.reviewed_inventory',return_value=provider.policy['media']),\
             patch.object(provider.kernel,'block',return_value=dict(block,filesystem_uuid='wrong')):
            with self.assertRaisesRegex(ValueError,'reviewed identity'):provider.snapshot()
            mounts[0]['options']=['rw'];mounts[0]['super_options']=['rw']
            with self.assertRaisesRegex(ValueError,'mount mode'):provider.snapshot()


if __name__=='__main__':unittest.main()
