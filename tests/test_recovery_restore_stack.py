"""Offline harness guards and deterministic factory/media/role contracts.

These checks never stage a host root, create OS images, start services or boot
QEMU. Actual installed assertions are distinct coordinator-run evidence.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import recovery_restore_stack as guest
import recovery_restore_stack_vm as vm
from sv08_printer_generate import generate
from test_data_budget import fixture_root


class StackHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=fixture_root());self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.fixture=self.root/'fixture';self.fixture.mkdir(mode=0o700)
        (self.fixture/'disposable-marker').write_text(guest.MARKER)
        (self.fixture/'stack-expectations.json').write_text(json.dumps(dict(boot=dict(slot='A',release='synthetic-stack',state_schema=1,release_revision=7))))
    def test_factory_saved_values_and_complete_bundle_keep_uncalibrated_guards(self):
        catalog,draft=guest.factory(vm.REPO/'catalog/printer/catalog.json','restored')
        before=json.dumps(draft,sort_keys=True); output=generate(catalog,draft,'full')
        self.assertEqual(before,json.dumps(draft,sort_keys=True));self.assertTrue(output['complete']);self.assertFalse(output['printing_enabled'])
        self.assertTrue(json.loads(output['files']['configuration-manifest.json'])['probe_calibration_pending'])
        self.assertEqual(output,generate(catalog,draft,'full'))
        persisted=json.loads(json.dumps(draft,sort_keys=True))
        self.assertEqual(output['files'],generate(catalog,persisted,'full')['files'])
        self.assertEqual(output['text'],generate(catalog,persisted,'full')['text'])
        self.assertIn('z_offset: 0',output['text']);self.assertIn('control: watermark',output['text'])
        for command in ('PRINT_START','SDCARD_PRINT_FILE','RESUME','M24'):
            section=output['text'].split('[gcode_macro '+command+']',1)[1].split('[',1)[0]
            self.assertIn('action_raise_error',section)
        self.assertIn('verify_heater',output['text']);self.assertIn('/dev/serial/by-id/sv08-stack-restored-main',output['text'])
    def test_profile_exact_bounded_gpt_identity_and_no_capacity_override(self):
        profile=vm.profile(self.fixture)
        self.assertEqual(profile['boot']['release'],'synthetic-stack')
        sizes={disk['stable'].get('device/wwid'):disk for disk in profile['media'] if 'device/wwid' in disk['stable']}
        self.assertEqual(sizes['naa.5000000000000003']['sectors'],vm.DATA_BYTES//512)
        self.assertEqual(vm.DATA_BYTES,1536*1024**2)
        self.assertGreater(vm.DATA_BYTES,1024*1024**2)
        self.assertEqual(profile['targets']['target']['root'],'/run/sv08-recovery/targets/target/restored')
        self.assertEqual(profile['archives']['backup']['path'],'/run/sv08-recovery/archives/backup/backup.tar')
    def test_identity_oneshot_requires_actual_successful_run(self):
        facts=dict(ActiveState='inactive',Result='success',ExecMainStatus='0',ExecMainStartTimestampMonotonic='123456')
        self.assertTrue(guest.completed_identity(facts))
        self.assertTrue(guest.completed_identity({**facts,'ActiveState':'active'}))
        for change in ({'ExecMainStartTimestampMonotonic':'0'},{'ExecMainStartTimestampMonotonic':''},
                       {'ExecMainStartTimestampMonotonic':'unknown'},{'Result':'exit-code'},
                       {'ExecMainStatus':'1'},{'ActiveState':'failed'},{'ActiveState':'activating'}):
            with self.subTest(change=change):self.assertFalse(guest.completed_identity({**facts,**change}))
        self.assertFalse(guest.completed_identity({}))
        self.assertNotIn('sv08-identity.service',guest.REQUIRED_UNITS)
        self.assertEqual(len(guest.REQUIRED_UNITS),8)
    def test_bootstrap_role_cannot_be_a_qualification_role(self):
        self.assertTrue(guest.bootstrap_role('console=ttyAMA0 sv08.stack.bootstrap=1'))
        for cmdline in ('', 'sv08.stack.bootstrap=0', 'sv08.stack.bootstrap=1 sv08.stack.bootstrap=1',
                        'sv08.stack.bootstrap=1 sv08.stack.expect=restored'):
            self.assertFalse(guest.bootstrap_role(cmdline))
        with patch.object(guest.Path,'read_text',return_value='sv08.stack.bootstrap=1'):
            with self.assertRaisesRegex(ValueError,'not a qualification'):
                guest.normal_assert('restored',self.fixture/'not-used',self.fixture/'not-used')
    def test_bootstrap_seed_contains_only_owned_private_empty_state_directory(self):
        import stat
        tree=vm.bootstrap_tree(self.fixture)
        self.assertEqual([path.name for path in tree.iterdir()],['sv08'])
        self.assertEqual(list((tree/'sv08').iterdir()),[])
        for path in (tree,tree/'sv08'):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o700)
            self.assertEqual(path.stat().st_uid,os.geteuid())
        self.assertEqual(vm.bootstrap_tree(self.fixture),tree)
        (tree/'sv08/state.json').write_text('preserved partial fixture')
        with self.assertRaisesRegex(ValueError,'must be empty'):vm.bootstrap_tree(self.fixture)
        self.assertEqual((tree/'sv08/state.json').read_text(),'preserved partial fixture')
    def test_network_profile_distinct_uuid_same_explicit_virtual_mac(self):
        import configparser
        for name in ('previous','restored'):
            profile=configparser.ConfigParser();profile.read_string(guest.network_profile(name).decode())
            self.assertEqual(profile['connection']['uuid'],guest.PROFILE_UUIDS[name]);self.assertEqual(profile['ethernet']['mac-address'],guest.MAC)
            self.assertEqual(profile['ipv4']['method'],'auto');self.assertNotIn('interface-name',profile['connection'])
        self.assertNotEqual(guest.network_profile('previous'),guest.network_profile('restored'))
    def test_private_marker_links_permissions_and_unassigned_root_refuse(self):
        self.assertEqual(guest.private_fixture(self.fixture),self.fixture)
        self.fixture.chmod(0o755)
        with self.assertRaises(ValueError):guest.private_fixture(self.fixture)
        self.fixture.chmod(0o700);alias=self.root/'alias';alias.symlink_to(self.fixture)
        with self.assertRaises(ValueError):guest.private_fixture(alias)
        (self.fixture/'disposable-marker').write_text('wrong')
        with self.assertRaises(ValueError):guest.private_fixture(self.fixture)
        for root in (Path('/'),Path('/tmp/rootfs'),vm.REPO/'build/unassigned/rootfs'):
            with self.assertRaises(ValueError):vm.installed_root(root)
    def candidate(self):
        candidate=self.root/'candidate';candidate.mkdir();
        for name in ('vmlinuz','initrd.img','recovery.ext4'):(candidate/name).write_bytes(name.encode())
        (candidate/'build.json').write_text(json.dumps(dict(manifest_sha256='a'*64,provider_manifest_sha256='b'*64)))
        for name in ('archive','target','boot'):(self.fixture/(name+'.raw')).write_bytes(name.encode())
        return candidate
    def test_recovery_command_contains_no_network_or_host_share_and_only_one_writable_disk(self):
        candidate=self.candidate();command=vm.command(candidate,self.fixture,self.fixture/'recovery.qmp')
        self.assertEqual(command[command.index('-nic')+1],'none');self.assertNotIn('-netdev',command);self.assertNotIn('-icount',command)
        self.assertEqual(command[command.index('-accel')+1],'tcg,thread=multi')
        with self.assertRaisesRegex(ValueError,'Functional clock requires'):
            vm.command(candidate,self.fixture,self.fixture/'recovery.qmp',functional_clock=True)
        drives=[command[n+1] for n,value in enumerate(command) if value=='-drive']
        self.assertEqual(len(drives),4);self.assertEqual(sum('readonly=on' not in drive for drive in drives),1)
        self.assertFalse(any('file=/dev/' in drive for drive in drives));self.assertNotIn('-virtfs',command)
        with self.assertRaises(ValueError):vm.command(candidate,self.fixture,self.root/'unassigned.qmp')
    def test_normal_command_strict_hash_bindings_restricted_ports_and_fixture_mac(self):
        candidate=self.candidate();normal=self.fixture/'normal';normal.mkdir()
        (normal/'normal-root.raw').write_bytes(b'normal root');(normal/'normal-initrd.img').write_bytes(b'normal initrd')
        receipt=dict(normal_root_sha256=guest.sha(normal/'normal-root.raw'),initrd_sha256=guest.sha(normal/'normal-initrd.img'),kernel_sha256=guest.sha(candidate/'vmlinuz'),manifest_sha256='c'*64)
        (normal/'normal-fixture.json').write_text(json.dumps(receipt))
        command=vm.command(candidate,self.fixture,self.fixture/'normal.qmp',normal,'previous')
        self.assertIn('sv08.stack.expect=previous',command[command.index('-append')+1]);self.assertIn('rauc.slot=A',command[command.index('-append')+1])
        network=command[command.index('-netdev')+1]
        self.assertIn('restrict=on',network);self.assertIn('127.0.0.1:19090',network);self.assertIn('127.0.0.1:18443',network)
        self.assertIn('virtio-net-pci,netdev=net0,mac='+guest.MAC,command)
        self.assertIn('127.0.0.1:12222-:22',network)
        self.assertNotIn('-icount',command)
        functional=vm.command(candidate,self.fixture,self.fixture/'functional.qmp',normal,functional_clock=True)
        self.assertEqual(functional[functional.index('-accel')+1],'tcg,thread=single')
        self.assertEqual(functional[functional.index('-icount')+1],'shift=0,align=off,sleep=off')
        bootstrap=vm.command(candidate,self.fixture,self.fixture/'bootstrap.qmp',normal,bootstrap=True)
        args=bootstrap[bootstrap.index('-append')+1]
        self.assertTrue(guest.bootstrap_role(args));self.assertNotIn('sv08.stack.expect=',args)
        functional_bootstrap=vm.command(candidate,self.fixture,self.fixture/'functional-bootstrap.qmp',normal,bootstrap=True,functional_clock=True)
        self.assertTrue(guest.bootstrap_role(functional_bootstrap[functional_bootstrap.index('-append')+1]))
        self.assertEqual(functional_bootstrap[functional_bootstrap.index('-icount')+1],'shift=0,align=off,sleep=off')
        with self.assertRaisesRegex(ValueError,'complete installed normal'):
            vm.command(candidate,self.fixture,self.fixture/'bootstrap.qmp',bootstrap=True)
        (normal/'normal-initrd.img').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hashes changed'):vm.command(candidate,self.fixture,self.fixture/'normal.qmp',normal)
    def test_image_replacement_and_block_input_refused_before_mutation(self):
        (self.fixture/'target.raw').write_bytes(b'preserved evidence')
        with patch.object(vm,'partition_image') as make:
            with self.assertRaisesRegex(ValueError,'explicit recorded'):vm.image(self.fixture,'target',None,vm.DATA_BYTES,vm.TARGET_UUID,vm.TARGET_PARTUUID)
            with self.assertRaisesRegex(ValueError,'Preserve the actual booted source'):
                vm.image(self.fixture,'target',None,vm.DATA_BYTES,vm.TARGET_UUID,vm.TARGET_PARTUUID,replace=True)
            make.assert_not_called()
        self.assertEqual((self.fixture/'target.raw').read_bytes(),b'preserved evidence')
        with self.assertRaises(ValueError):vm.regular('/dev/null')
    def test_distinct_reboot_and_rollback_receipts_required(self):
        directory=self.fixture/'receipts';directory.mkdir()
        values=[dict(result='PASS',expected=expected,boot_id=boot_id,physical_hardware=False,printing_ready=False)
                for expected,boot_id in (('restored','one'),('restored','two'),('previous','three'))]
        for n,row in enumerate(values):(directory/(str(n)+'.json')).write_text(json.dumps(row))
        self.assertEqual(guest.audit_boots(directory)['restored_boots'],2)
        values[1]['boot_id']='one';(directory/'1.json').write_text(json.dumps(values[1]))
        with self.assertRaisesRegex(ValueError,'distinct'):guest.audit_boots(directory)
        (directory/'1.json').unlink()
        with self.assertRaisesRegex(ValueError,'Two restored'):guest.audit_boots(directory)
    def test_export_requires_actual_readonly_mount_and_boot_receipt(self):
        source=self.fixture/'mounted-source';source.mkdir();(self.fixture/'archive-tree').mkdir()
        with patch.object(vm.subprocess,'check_output',return_value=vm.TARGET_UUID+' ext4 rw,nodev\n'):
            with self.assertRaisesRegex(ValueError,'read-only'):vm.export_source(self.fixture,source)
        with patch.object(vm.subprocess,'check_output',return_value=vm.TARGET_UUID+' ext4 ro,nodev\n'):
            with self.assertRaisesRegex(ValueError,'boot receipt'):vm.export_source(self.fixture,source)
        self.assertEqual(list((self.fixture/'archive-tree').iterdir()),[])

if __name__=='__main__':unittest.main()
