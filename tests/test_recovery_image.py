import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('recovery_image',Path(__file__).resolve().parents[1]/'scripts/recovery_image.py')
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)

class RecoveryImageTests(unittest.TestCase):
    def test_recovery_masks_unused_binfmt_service_and_automount(self):
        with tempfile.TemporaryDirectory() as directory:
            units=Path(directory)
            for name in ('systemd-binfmt.service','proc-sys-fs-binfmt_misc.automount'):
                (units/name).write_text('unmasked fixture')
            m.mask_recovery_units(units)
            self.assertIn('systemd-binfmt.service',m.RECOVERY_MASKED_UNITS)
            self.assertIn('proc-sys-fs-binfmt_misc.automount',m.RECOVERY_MASKED_UNITS)
            for name in m.RECOVERY_MASKED_UNITS:
                self.assertTrue((units/name).is_symlink(),name)
                self.assertEqual((units/name).readlink(),Path('/dev/null'))

    def test_builder_rejects_stale_assembly_integration_inputs(self):
        with tempfile.TemporaryDirectory(dir=m.REPO/'build') as directory:
            source=Path(directory)/'assembly';root=source/'rootfs'
            (root/'usr/bin').mkdir(parents=True);(root/'boot').mkdir()
            (root/'usr/bin/busybox').write_bytes(b'busybox')
            (root/'boot'/('vmlinuz-'+m.KERNEL)).write_bytes(b'kernel')
            (source/'assembly.json').write_text(json.dumps(dict(integration_inputs={'stale':'digest'})))
            args=SimpleNamespace(work=Path(directory)/'output',assembly=source,execute=False,
                                 board_profile=None,media_profile=None)
            with self.assertRaisesRegex(ValueError,'Stale build assembly'):
                m.build(args)

    def test_vm_adds_provider_binding_only_for_complete_composition_receipt(self):
        spec=importlib.util.spec_from_file_location('recovery_vm',m.REPO/'tests/recovery_vm.py')
        vm=importlib.util.module_from_spec(spec);spec.loader.exec_module(vm)
        legacy={'manifest_sha256':'1'*64}
        self.assertEqual(vm.boot_bindings(legacy),'sv08.envelope='+'1'*64)
        composed={**legacy,'media_profile_sha256':'2'*64,'policy_sha256':'3'*64,
                  'provider_manifest_sha256':'4'*64}
        self.assertEqual(vm.boot_bindings(composed),
                         'sv08.envelope='+'1'*64+' sv08.recovery='+'4'*64)
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            vm.boot_bindings({**legacy,'provider_manifest_sha256':'4'*64})

    def test_inventory_binds_root_xattrs_and_hardlinks(self):
        import os
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);a=root/'a';b=root/'b';a.write_text('same');b.write_text('same')
            initial=m.inventory(root);root.chmod(0o755)
            self.assertNotEqual(initial,m.inventory(root));root.chmod(0o700)
            self.assertEqual(initial,m.inventory(root))
            os.setxattr(a,'user.identity',b'changed')
            self.assertNotEqual(initial,m.inventory(root));os.removexattr(a,'user.identity')
            self.assertEqual(initial,m.inventory(root));b.unlink();os.link(a,b)
            self.assertNotEqual(initial,m.inventory(root))

    def test_vm_refuses_writable_candidate_aliases_and_invalid_duration(self):
        import os,subprocess
        runner=m.REPO/'tests/recovery_vm.py'
        with tempfile.TemporaryDirectory(dir=m.REPO/'build') as t:
            root=Path(t);source=root/'source';source.mkdir();image=source/'recovery.ext4'
            with image.open('wb') as f:f.truncate(m.SIZE)
            for n in ('vmlinuz','initrd.img'):(source/n).write_bytes(b'fixture')
            (source/'build.json').write_text(json.dumps(dict(image_sha256=m.sha(image),kernel_sha256=m.sha(source/'vmlinuz'),initrd_sha256=m.sha(source/'initrd.img'))))
            base=['python3',str(runner),'--build',str(source),'--work',str(root/'output')]
            cases=[['--writable'],['--seconds','0'],['--seconds','601']]
            alias=root/'alias.ext4';os.link(image,alias);cases.append(['--writable','--image',str(alias)])
            for args in cases:
                result=subprocess.run(base+args,capture_output=True,text=True,timeout=10)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse((root/'output').exists())

    def test_rejects_symlink_and_raw_target(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'alias').symlink_to('/tmp')
            with self.assertRaisesRegex(ValueError,'Symlink'):m.clean_path(p/'alias'/'output')
        with self.assertRaisesRegex(ValueError,'raw devices'):m.clean_path('/dev/null')

    def test_rejects_overlap(self):
        for a,b in [('/tmp/x','/tmp/x'),('/tmp/x','/tmp/x/y'),('/tmp/x/y','/tmp/x')]:
            with self.assertRaisesRegex(ValueError,'overlap'):m.separate(Path(a),Path(b))

    def test_rejects_nonbuild_output(self):
        with self.assertRaisesRegex(ValueError,'repository build'):m.clean_path('/tmp/recovery-output',output=True)

    def test_inspection_never_creates_output(self):
        with tempfile.TemporaryDirectory(dir=m.REPO/'build') as t:
            root=Path(t);intake=root/'intake';intake.mkdir();archive=intake/'archive';archive.write_bytes(b'archive')
            digest=m.sha(archive);archive.rename(intake/(digest+'.deb'))
            lock=root/'lock.json';lock.write_text(json.dumps(dict(packages=[dict(package='fixture',version='1',architecture='arm64',sha256=digest,bytes=7)])))
            work=root/'output';a=argparse.Namespace(work=work,intake=intake,lock=lock,execute=False)
            with patch.object(m,'run',return_value=SimpleNamespace(stdout='Package: fixture\nVersion: 1\nArchitecture: arm64\n')), patch.object(m,'private',side_effect=AssertionError('privileged action')):
                self.assertFalse(m.assemble(a)['execute'])
            self.assertFalse(work.exists())
            (intake/(digest+'.deb')).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Missing/changed'):m.assemble(a)
            self.assertFalse(work.exists())

    def test_existing_output_refused_before_work(self):
        with tempfile.TemporaryDirectory(dir=m.REPO/'build') as t:
            p=Path(t);source=p/'source';source.mkdir();(source/'rootfs').mkdir();(source/'assembly.json').write_text('{}')
            work=p/'output';work.mkdir()
            with self.assertRaisesRegex(ValueError,'fresh output'):
                m.build(argparse.Namespace(work=work,assembly=source,execute=False))

if __name__=='__main__':unittest.main()
