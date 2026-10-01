import argparse
import importlib.util
import json
import hashlib
import io
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('recovery_image',Path(__file__).resolve().parents[1]/'scripts/recovery_image.py')
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)

class RecoveryImageTests(unittest.TestCase):
    @contextmanager
    def build_fixture(self):
        # Redirect only fixture storage; production path checks remain enabled.
        inputs=m.integration_inputs()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'build').mkdir()
            with patch.object(m,'REPO',root), patch.object(m,'integration_inputs',return_value=inputs):
                with tempfile.TemporaryDirectory(dir=root/'build') as work:
                    yield work

    def test_recovery_stages_post_pid1_private_mount_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);units=root/'etc/systemd/system';units.mkdir(parents=True)
            m.stage_recovery_units(units)
            private=(units/'sv08-recovery-private-mounts.service').read_text()
            prepare=(units/'sv08-recovery-prepare.service').read_text()
            display=(units/'sv08-recovery-display.service.d/independent.conf').read_text()
            target=(units/'sv08-recovery.target').read_text()
            udev=(units/'systemd-udevd.service.d/recovery-namespace.conf').read_text()
            logind=(units/'systemd-logind.service.d/recovery-namespace.conf').read_text()
            runtime=root/'usr/lib/sv08';runtime.mkdir(parents=True)
            for name in ('sv08_recovery_media.py', 'sv08_recovery_prepare.py'):
                (runtime/name).write_text(name)
            bound=m.installed_provider_inputs(root)
            destination_hashes = {
                'configs/host-os/recovery-systemd-udevd.conf':
                    m.sha(units/'systemd-udevd.service.d/recovery-namespace.conf'),
                'configs/host-os/recovery-systemd-logind.conf':
                    m.sha(units/'systemd-logind.service.d/recovery-namespace.conf'),
            }
        self.assertEqual(private.count('ExecStart=/bin/mount --make-rprivate /'),1)
        self.assertIn('After=sysinit.target basic.target',private)
        self.assertIn('Before=sv08-recovery-prepare.service sv08-recovery-display.service',
                      private)
        for sandbox in ('PrivateMounts=', 'MountFlags='):
            self.assertNotIn(sandbox,private)
        self.assertIn('Requires=sv08-recovery-private-mounts.service',prepare)
        self.assertIn('After=systemd-udev-settle.service sv08-recovery-private-mounts.service',
                      prepare)
        self.assertIn('Before=sv08-recovery-display.service',prepare)
        self.assertIn('Wants=systemd-udev-settle.service sv08-recovery-private-mounts.service',
                      display)
        self.assertIn('After=sv08-recovery-private-mounts.service',display)
        self.assertIn('Wants=sv08-recovery-private-mounts.service ',target)
        self.assertIn('After=sysinit.target basic.target sv08-recovery-private-mounts.service ',
                      target)
        self.assertNotIn('Requires=sv08-recovery-private-mounts.service',target)
        self.assertEqual(udev,'[Service]\nPrivateMounts=no\n')
        self.assertEqual(logind,('[Service]\nPrivateMounts=no\nPrivateTmp=no\n'
                                 'ProtectSystem=no\nProtectHome=no\n'
                                 'ProtectKernelModules=no\nProtectKernelLogs=no\n'
                                 'ProtectControlGroups=no\nReadWritePaths=\n'))
        current=m.integration_inputs()
        for source, digest in destination_hashes.items():
            self.assertEqual(current[source],m.sha(m.REPO/source))
            self.assertEqual(current[source],digest)
            self.assertEqual(bound[source],digest)

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
        with self.build_fixture() as directory:
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
        with self.build_fixture() as t:
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
        with self.build_fixture() as t:
            root=Path(t);intake=root/'intake';intake.mkdir();archive=intake/'archive';archive.write_bytes(b'archive')
            digest=m.sha(archive);archive.rename(intake/(digest+'.deb'))
            lock=root/'lock.json';lock.write_text(json.dumps(dict(packages=[dict(package='fixture',version='1',architecture='arm64',sha256=digest,bytes=7)])))
            work=root/'output';a=argparse.Namespace(work=work,intake=intake,lock=lock,execute=False)
            with patch.object(m,'run',return_value=SimpleNamespace(stdout='Package: fixture\nVersion: 1\nArchitecture: arm64\n')), patch.object(m,'private',side_effect=AssertionError('privileged action')):
                self.assertFalse(m.assemble(a)['execute'])
            self.assertFalse(work.exists())
            with patch.object(m,'run',return_value=SimpleNamespace(stdout='Package: wrong\nVersion: 1\nArchitecture: arm64\n')):
                with self.assertRaisesRegex(ValueError,'Archive control differs'):m.assemble(a)
            self.assertFalse(work.exists())
            (intake/(digest+'.deb')).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Missing/changed'):m.assemble(a)
            self.assertFalse(work.exists())

    def test_existing_output_refused_before_work(self):
        with self.build_fixture() as t:
            p=Path(t);source=p/'source';source.mkdir();(source/'rootfs').mkdir();(source/'assembly.json').write_text('{}')
            work=p/'output';work.mkdir()
            with self.assertRaisesRegex(ValueError,'fresh output'):
                m.build(argparse.Namespace(work=work,assembly=source,execute=False))


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        (self.root/'build').mkdir()
        self.lock=self.root/'lock.json'
        self.payload=b'tiny archive'
        self.archive_hash=hashlib.sha256(self.payload).hexdigest()
        # Whitespace is intentionally significant to the receipt's byte identity.
        self.captured=(json.dumps(dict(packages=[dict(bytes=len(self.payload),
            sha256=self.archive_hash,url='https://snapshot.debian.org/archive/fixture')]),
            indent=2)+'\n').encode()
        self.lock.write_bytes(self.captured)
        self.args=SimpleNamespace(work=self.root/'build/intake',lock=self.lock,execute=True)
        for mock in (patch.object(m,'REPO',self.root),
                     patch.object(m.os,'geteuid',return_value=1000),
                     patch.object(m,'private',side_effect=AssertionError('privileged action')),
                     patch.object(m,'run',side_effect=AssertionError('subprocess'))):
            mock.start();self.addCleanup(mock.stop)
        self.network=patch.object(m.urllib.request,'urlopen')
        self.urlopen=self.network.start();self.addCleanup(self.network.stop)
        self.urlopen.side_effect=lambda *a,**k:io.BytesIO(self.payload)

    def replace(self,content):
        replacement=self.root/'replacement.json';replacement.write_bytes(content)
        replacement.replace(self.lock)

    def during_download(self,action):
        payload=self.payload
        class Response(io.BytesIO):
            def read(response,size=-1):
                if response.tell()==0:action()
                return super().read(size)
        self.urlopen.side_effect=lambda *a,**k:Response(payload)

    def assert_receipt(self):
        result=m.intake(self.args)
        self.assertEqual(result,dict(stage='intake',packages=1,
            lock_sha256=hashlib.sha256(self.captured).hexdigest()))
        self.assertEqual((self.args.work/(self.archive_hash+'.deb')).read_bytes(),self.payload)
        return result

    def test_stable_exact_byte_receipt(self):
        self.assert_receipt()
        self.urlopen.assert_called_once_with('https://snapshot.debian.org/archive/fixture',timeout=60)

    def test_replacement_during_download_refuses_completion(self):
        self.during_download(lambda:self.replace(b'{"packages": []}'))
        with self.assertRaisesRegex(ValueError,'Lock content changed'):m.intake(self.args)
        self.assertTrue((self.args.work/(self.archive_hash+'.deb')).exists())
        with self.assertRaisesRegex(ValueError,'fresh output'):m.intake(self.args)
        self.assertEqual(self.urlopen.call_count,1)

    def test_replacement_after_initial_read_refuses(self):
        original=Path.read_bytes
        def capture_then_replace(path):
            data=original(path)
            if path==self.lock:self.replace(b'{"packages": []}')
            return data
        with patch.object(Path,'read_bytes',capture_then_replace):
            with self.assertRaisesRegex(ValueError,'Lock content changed'):m.intake(self.args)
        # A selected the download even though the path already named B at parsing.
        self.urlopen.assert_called_once()
        self.assertEqual((self.args.work/(self.archive_hash+'.deb')).read_bytes(),self.payload)

    def test_intake_path_refusals_precede_network(self):
        cases=[(self.root/'outside',self.lock,'repository build'),
               (self.root/'build/overlap',self.root/'build/overlap/lock','overlap'),
               (self.root/'build/raw',Path('/dev/null'),'raw devices')]
        alias=self.root/'alias';alias.symlink_to(self.root/'build')
        cases.append((alias/'output',self.lock,'Symlink'))
        for work,lock,message in cases:
            with self.subTest(message=message):
                args=SimpleNamespace(work=work,lock=lock,execute=True)
                with self.assertRaisesRegex(ValueError,message):m.intake(args)
                self.assertFalse(work.exists())
        self.urlopen.assert_not_called()

    def test_same_byte_replacement_passes(self):
        self.during_download(lambda:self.replace(self.captured))
        self.assert_receipt()

    def test_deleted_completion_lock_refuses(self):
        self.during_download(self.lock.unlink)
        with self.assertRaisesRegex(ValueError,'Lock unreadable'):m.intake(self.args)

    def test_unreadable_completion_lock_refuses(self):
        original=Path.open
        def open_path(path,*args,**kwargs):
            if path==self.lock and self.args.work.exists():raise PermissionError('fixture denied')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',open_path):
            with self.assertRaisesRegex(ValueError,'Lock unreadable'):m.intake(self.args)

    def test_replacement_after_comparison_reports_captured_digest(self):
        original=m.sha
        def hash_then_replace(path):
            digest=original(path)
            if path==self.lock:self.replace(b'{"packages": []}')
            return digest
        with patch.object(m,'sha',side_effect=hash_then_replace) as hashed:
            self.assert_receipt()
        self.assertEqual(sum(call.args[0]==self.lock for call in hashed.call_args_list),1)
        self.assertNotEqual(hashlib.sha256(self.lock.read_bytes()).hexdigest(),
                            hashlib.sha256(self.captured).hexdigest())

    def test_inspection_has_no_output_or_network(self):
        self.args.execute=False
        self.assertEqual(m.intake(self.args),dict(execute=False,stage='intake',packages=1,bytes=len(self.payload)))
        self.assertFalse(self.args.work.exists());self.urlopen.assert_not_called()

    def test_root_and_existing_output_refused(self):
        with patch.object(m.os,'geteuid',return_value=0):
            with self.assertRaisesRegex(ValueError,'unprivileged'):m.intake(self.args)
        self.assertFalse(self.args.work.exists())
        self.args.work.mkdir()
        with self.assertRaisesRegex(ValueError,'fresh output'):m.intake(self.args)
        self.urlopen.assert_not_called()

    def test_invalid_identity_refused_without_download(self):
        self.lock.write_text(json.dumps(dict(packages=[dict(bytes=1,sha256='invalid',url='http://example.invalid')])) )
        with self.assertRaisesRegex(ValueError,'Invalid locked'):m.intake(self.args)
        self.urlopen.assert_not_called()

    def test_size_hash_and_network_failures_exhaust_retries(self):
        for name,payload,error in [('size',b'x','Archive size/hash'),
                                    ('hash',b'x'*len(self.payload),'Archive size/hash'),
                                    ('network',None,'offline failure')]:
            with self.subTest(name=name):
                self.args.work=self.root/'build'/name
                self.urlopen.reset_mock()
                if payload is None:self.urlopen.side_effect=OSError('offline failure')
                else:self.urlopen.side_effect=lambda *a,**k:io.BytesIO(payload)
                with self.assertRaisesRegex((ValueError,OSError),error):m.intake(self.args)
                self.assertEqual(self.urlopen.call_count,3)
                self.assertEqual(list(self.args.work.iterdir()),[])

if __name__=='__main__':unittest.main()
