import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import test_recovery_prepare as helpers
FakeKernel, FakeLease = helpers.FakeKernel, helpers.FakeLease
from sv08_recovery_prepare import reviewed_inventory
from sv08_recovery_restore_media import RestoreMediaProvider, PROTOCOL
from sv08_recovery_restore_prepare import RestorePreparer


class RestorePrepareTests(unittest.TestCase):
    def setUp(self):
        fixture=helpers.RecoveryPrepareTests();fixture.setUp();self.inventory=fixture.inventory
        self.inventory[2]['partitions'][0]['filesystem']='ext4'
        self.policy=dict(format_version=1,protocol=PROTOCOL,writer_model=fixture.policy['writer_model'],recovery=fixture.policy['recovery'],recovery_path='/',
            boot=dict(slot='A',release='fixture-release',state_schema=1,release_revision=7),media=reviewed_inventory(self.inventory),image_manifest_sha256='a'*64,envelope_manifest_sha256='b'*64,
            archives=dict(backup=dict(label='Reviewed archive',mount='/run/sv08-recovery/archives/backup',path='/run/sv08-recovery/archives/backup/backup.tar',identity=fixture.policy['source'])),
            targets=dict(target=dict(label='Reviewed target',mount='/run/sv08-recovery/targets/target',root='/run/sv08-recovery/targets/target/restored',fresh_root='/run/sv08-recovery/targets/target/fresh',identity=fixture.policy['destinations']['usb']['identity'])))
    def execute(self, kernel=None, failure=None):
        kernel=kernel or FakeKernel(copy.deepcopy(self.inventory))
        with tempfile.TemporaryDirectory() as directory:
            context=Path(directory)/'context.json';context.write_text('stale')
            preparer=RestorePreparer(self.policy,kernel=kernel,context=context)
            published=[]
            def snapshot(provider,preparation=False):
                kernel.events.append('preflight' if preparation else 'snapshot')
                if failure and preparation: raise ValueError(failure)
                return {'observed':'exact'}
            with patch.object(preparer,'authenticate'),patch.object(preparer,'_publish',side_effect=published.append),patch.object(RestoreMediaProvider,'snapshot',snapshot):
                try: result=preparer.prepare(FakeLease())
                except BaseException:
                    self.assertFalse(context.exists());self.assertFalse(published);raise
            self.assertEqual(result['expected'],{'observed':'exact'});self.assertEqual(published,[result]);return kernel
    def test_exact_preparation_preflight_ro_archive_rw_target_then_context(self):
        kernel=self.execute()
        events=kernel.events;preflight=events.index('preflight')
        mounts=[event for event in events if isinstance(event,tuple) and event[0]=='mount']
        self.assertEqual(len(mounts),2);self.assertEqual(mounts[0][3],'ro,noload,nosuid,nodev,noexec')
        self.assertEqual(mounts[1][3],'rw,nosuid,nodev,noexec');self.assertEqual(mounts[1][4],'ext4')
        self.assertLess(preflight,events.index(mounts[0]));self.assertLess(events.index(mounts[1]),events.index('snapshot'))
    def test_existing_export_fat_archive_is_readonly_without_ext4_options(self):
        self.inventory[1]['partitions'][0]['filesystem']='vfat'
        self.policy['media']=reviewed_inventory(self.inventory)
        kernel=self.execute()
        mounts=[event for event in kernel.events if isinstance(event,tuple) and event[0]=='mount']
        self.assertEqual(mounts[0][3:5],('ro,nosuid,nodev,noexec','vfat'))
        self.assertEqual(mounts[1][4],'ext4')
    def test_changed_runtime_preflight_refuses_before_block_or_mount_mutation(self):
        kernel=FakeKernel(copy.deepcopy(self.inventory))
        with self.assertRaisesRegex(ValueError,'changed runtime'):self.execute(kernel,'changed runtime')
        self.assertFalse([e for e in kernel.events if isinstance(e,tuple)])
    def test_stale_identity_alias_and_existing_mount_refuse(self):
        kernel=FakeKernel(copy.deepcopy(self.inventory));kernel.value[1]['stable']={'serial':'changed'}
        with self.assertRaisesRegex(ValueError,'inventory'):self.execute(kernel)
        kernel=FakeKernel(copy.deepcopy(self.inventory));kernel.value[2]['partitions'][0]['disk_device']='8:0'
        with self.assertRaisesRegex(ValueError,'alias'):self.execute(kernel)
        kernel=FakeKernel(copy.deepcopy(self.inventory))
        kernel.mounts=lambda:[dict(path='/',device='254:0'),dict(path='/unexpected',device='8:1')]
        with self.assertRaisesRegex(ValueError,'mounted'):self.execute(kernel)
    def test_partial_mount_failure_unmounts_archive_and_withholds_context(self):
        kernel=FakeKernel(copy.deepcopy(self.inventory));mount=kernel.mount
        def failing(identity,path,options,filesystem):
            if options.startswith('rw'):raise ValueError('target mount failed')
            mount(identity,path,options,filesystem)
        kernel.mount=failing
        with self.assertRaisesRegex(ValueError,'target mount failed'):self.execute(kernel)
        self.assertEqual(kernel.events[-1],('unmount','/run/sv08-recovery/archives/backup'))

if __name__=='__main__': unittest.main()
