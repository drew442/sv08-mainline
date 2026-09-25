"""Execute the generated selector with command fixtures; no block-device I/O.

The real shell parser/control flow and -b tests run. Commands that could access
media are functions, and the absolute busybox invocation is redirected to one.
This does not substitute for partitioned VM or physical boot evidence.
"""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recovery_image',REPO/'scripts/recovery_image.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class BoardRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.profile=m.board_profile(REPO/'configs/host-os/recovery-test-sv08-01.json')
        self.root='root=PARTUUID='+self.profile['recovery']['partuuid']
        self.binding='sv08.envelope='+'a'*64

    def test_profile_refuses_ambiguous_layout_and_missing_artifacts(self):
        cases=[]
        for key,value in [('bytes',1),('index',4),('partuuid','bad'),('filesystem_uuid','bad')]:
            p=copy.deepcopy(self.profile);p['recovery'][key]=value;cases.append(p)
        p=copy.deepcopy(self.profile);p['partitions'][0]['partuuid']=p['partitions'][1]['partuuid'];cases.append(p)
        p=copy.deepcopy(self.profile);del p['artifacts']['modules'];cases.append(p)
        p=copy.deepcopy(self.profile);p['packages'][0]['sha256']='bad';cases.append(p)
        for value in cases:
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'profile.json';path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):m.board_profile(path)

    def test_derived_runtime_targets_exist_before_package_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);m.prepare_derived_runtime(root)
            for relative in ('log','tmp','cache','lib/systemd','lib/dbus'):
                self.assertTrue((root/'run/recovery-var'/relative).is_dir())
            self.assertEqual((root/'run/recovery-var/tmp').stat().st_mode & 0o7777,0o1777)
            # Ordinary writes used by dpkg/mkinitramfs now have existing targets.
            (root/'run/recovery-var/log/dpkg.log').write_text('fixture')
            with tempfile.TemporaryDirectory(dir=root/'run/recovery-var/tmp',prefix='mkinitramfs_'):pass

    def test_regdb_selection_requires_registered_existing_alternative(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(m,'run',side_effect=AssertionError('absent package must not invoke alternatives')):
                self.assertEqual(m.select_upstream_regdb(root),dict(status='not-installed',selected=False))
            target=root/'usr/lib/firmware/regulatory.db-upstream';target.parent.mkdir(parents=True);target.write_text('signed fixture')
            with patch.object(m,'run',return_value=SimpleNamespace(stdout='')):
                with self.assertRaisesRegex(ValueError,'not registered'):m.select_upstream_regdb(root)
            registered='Alternative: /lib/firmware/regulatory.db-upstream\n'
            selected='Value: /lib/firmware/regulatory.db-upstream\n'
            with patch.object(m,'run',side_effect=[SimpleNamespace(stdout=registered),SimpleNamespace(),SimpleNamespace(stdout=selected)]) as calls:
                self.assertTrue(m.select_upstream_regdb(root)['selected'])
                self.assertEqual(calls.call_args_list[1].args[0][-3:],['--set','regulatory.db','/lib/firmware/regulatory.db-upstream'])

    def test_shared_module_directory_mode_normalization_keeps_exact_byte_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);profile=copy.deepcopy(self.profile)
            modules=root/profile['artifacts']['modules']['path'];modules.mkdir(parents=True,mode=0o755)
            payload=modules/'driver.ko';payload.write_bytes(b'reviewed module')
            (modules/'modules.dep').write_text('driver.ko:\n')
            profile['artifacts']['modules']['inventory_sha256']=m.inventory(modules)['sha256']
            modules.chmod(0o775)
            receipt=m.normalize_board_module_directory(root,profile)
            self.assertEqual(receipt['before_mode'],'0o775')
            self.assertEqual(modules.stat().st_mode & 0o7777,0o755)
            self.assertTrue(receipt['exact_reviewed_inventory'])
            for changed in (payload,modules/'modules.dep'):
                original=changed.read_bytes();changed.write_bytes(b'changed')
                modules.chmod(0o775)
                with self.assertRaisesRegex(ValueError,'beyond reviewed directory mode'):m.normalize_board_module_directory(root,profile)
                self.assertEqual(modules.stat().st_mode & 0o7777,0o775)
                changed.write_bytes(original)

    def selector(self,cmdline,scenario='ok'):
        # Use existing nodes for shell -b only. No command reads/writes a device.
        if not Path('/dev/loop0').is_block_device() or not Path('/dev/loop1').is_block_device():self.skipTest('block-node type fixtures unavailable')
        gate=m.boot_gate(self.profile)
        selector=gate[gate.index('# Generated board selector'):gate.index('manifest=/newroot/')]
        selector=selector.replace('/bin/busybox blockdev','fixture_blockdev')
        harness=r'''
fail() { echo "REFUSED:$*"; exit 91; }
modprobe() { return 0; }
sleep() { :; }
cat() {
 case "$1" in
 /proc/cmdline) echo "$cmdline";;
 */partition) [ "$scenario" != whole ] && echo 5;;
 */size) if [ "$scenario" = capacity ]; then echo 1; else echo 1048576; fi;;
 */ro) if [ "$scenario" = sysrw ]; then echo 0; else echo 1; fi;;
 *) exit 92;; esac
}
readlink() {
 case "$2" in
 /sys/dev/block/7:0) echo /sys/devices/virtual/block/loop0;;
 /sys/dev/block/7:1) echo /sys/devices/virtual/block/loop1;;
 *) echo "$2";; esac
}
stat() { case "$3" in /dev/loop1) echo 7:1;; *) echo 7:0;; esac; }
blkid() {
 case "$*" in
 *'-o device') case "$scenario" in
   none) :;; ambiguous) echo '/dev/loop0 /dev/loop1';;
   aliases) echo '/dev/loop0 /dev/loop0';; nonblock) echo /dev/null;;
   *) echo /dev/loop0;; esac;;
 *'-s PARTUUID'*) echo 'b28438ed-f895-4b93-9bad-d27d3890ccd3';;
 *'-s UUID'*) if [ "$scenario" = uuid ]; then echo wrong; else echo '964ed891-6ec4-4a95-8762-e32c91260394'; fi;;
 *) exit 93;; esac
}
fixture_blockdev() {
 [ "$2" = /dev/loop0 ] || exit 94
 case "$1" in
 --setro) echo SETRO; [ "$scenario" != setfail ];;
 --getro) if [ "$scenario" = stillrw ]; then echo 0; else echo 1; fi;;
 *) exit 95;; esac
}
mount() { echo "MOUNT:$*"; }
'''
        script='cmdline='+__import__('shlex').quote(cmdline)+'\nscenario='+scenario+'\n'+harness+selector
        return subprocess.run(['/bin/sh'],input=script,text=True,capture_output=True,timeout=5)

    def test_actual_parser_rejects_missing_duplicate_and_conflicting_inputs(self):
        cases=[self.binding,self.root,self.root+' '+self.root+' '+self.binding,
               self.root+' root=/dev/vda '+self.binding,'root=/dev/vda '+self.binding,
               self.root+' '+self.binding+' '+self.binding,self.root+' sv08.envelope=',
               self.root+' sv08.envelope='+'G'*64,self.root+' sv08.envelope= sv08.envelope='+'a'*64]
        for command in cases:
            with self.subTest(command=command):
                result=self.selector(command)
                self.assertEqual(result.returncode,91,result.stdout+result.stderr)
                self.assertNotIn('SETRO',result.stdout);self.assertNotIn('MOUNT:',result.stdout)

    def test_actual_discovery_and_readonly_refusals(self):
        for scenario in ['none','ambiguous','nonblock','whole','capacity','uuid','setfail','stillrw','sysrw']:
            with self.subTest(scenario=scenario):
                result=self.selector(self.root+' '+self.binding,scenario)
                self.assertEqual(result.returncode,91,result.stdout+result.stderr)
                self.assertNotIn('MOUNT:',result.stdout)

    def test_partition_protection_precedes_mount_and_aliases_collapse(self):
        for scenario in ['ok','aliases']:
            result=self.selector(self.root+' '+self.binding,scenario)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('SETRO\nMOUNT:-t ext4 -o ro,noload /dev/loop0 /newroot',result.stdout)

    def test_common_gates_retained_and_default_byte_identical(self):
        original=(REPO/'configs/host-os/recovery-init').read_text()
        self.assertEqual(m.boot_gate(),original)
        common=original[original.index('manifest=/newroot/'):]
        common=common.replace("= '/dev/vda:ext4:ro,relatime,norecovery'",'= "${recovery_device}:ext4:ro,relatime,norecovery"')
        self.assertTrue(m.boot_gate(self.profile).endswith(common))

    def test_derivation_refuses_changed_parent_and_package_without_mutation(self):
        with tempfile.TemporaryDirectory(dir=REPO/'build') as directory:
            base=Path(directory);source=base/'parent';root=source/'rootfs';root.mkdir(parents=True)
            (root/'identity').write_text('original')
            receipt=source/'assembly.json';receipt.write_text(json.dumps(dict(root=m.inventory(root),integration_inputs=m.integration_inputs())))
            packages=base/'packages';packages.mkdir()
            profile=copy.deepcopy(self.profile)
            for package in profile['packages']:
                archive=packages/package['filename'];archive.write_bytes(b'fixture')
                package.update(bytes=7,sha256=m.sha(archive))
            path=base/'profile.json';path.write_text(json.dumps(profile))
            args=SimpleNamespace(assembly=source,work=base/'derived',packages=packages,board_profile=path,execute=False)
            def control(command,**kwargs):
                return SimpleNamespace(stdout='Package: '+Path(command[2]).name.split('_')[0]+'\nArchitecture: arm64\n')
            with patch.object(m,'run',side_effect=control),patch.object(m,'private',side_effect=AssertionError('unexpected privileged work')):
                self.assertFalse(m.derive(args)['execute'])
                (packages/profile['packages'][0]['filename']).write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'board package'):m.derive(args)
                (root/'identity').write_text('changed')
                with self.assertRaisesRegex(ValueError,'source changed'):m.derive(args)
            self.assertFalse(args.work.exists())

    def test_board_artifact_hashes_bind_kernel_config_dtb_and_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);profile=copy.deepcopy(self.profile)
            for name,item in profile['artifacts'].items():
                path=root/item['path'];path.parent.mkdir(parents=True,exist_ok=True)
                if name=='modules':
                    path.mkdir();(path/'modules.dep').write_text('fixture')
                    item['inventory_sha256']=m.inventory(path)['sha256']
                else:
                    path.write_text('fixture');item['sha256']=m.sha(path)
            for name in ['image','config','dtb','modules']:
                with self.subTest(artifact=name):
                    changed=copy.deepcopy(profile)
                    key='inventory_sha256' if name=='modules' else 'sha256'
                    changed['artifacts'][name][key]='0'*64
                    with self.assertRaisesRegex(ValueError,'Changed board artifact: '+name):m.check_board_artifacts(root,changed)

    def test_old_assembly_usr_cache_refused(self):
        with tempfile.TemporaryDirectory(dir=REPO/'build') as directory:
            base=Path(directory);source=base/'derived';root=source/'rootfs';root.mkdir(parents=True)
            recorded=m.inventory(root)
            (source/'assembly.json').write_text(json.dumps(dict(root=recorded,board_profile=self.profile,integration_inputs=m.integration_inputs())))
            cache=base/'old-cache';cache.mkdir()
            (cache/'build.json').write_text(json.dumps(dict(source={'sha256':'old-parent'},usr_sha256='0'*64)))
            args=SimpleNamespace(work=base/'output',assembly=source,board_profile=REPO/'configs/host-os/recovery-test-sv08-01.json',reuse_usr=cache,execute=True)
            with patch.object(m,'private'),patch.object(m,'check_board_artifacts'):
                with self.assertRaisesRegex(ValueError,'Compressed cache differs'):m.build(args)


if __name__=='__main__':unittest.main()
