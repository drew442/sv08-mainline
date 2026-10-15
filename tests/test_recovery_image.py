import argparse
import importlib.util
import json
import hashlib
import io
from contextlib import contextmanager
from pathlib import Path
import tempfile
import shutil
import sys
import tarfile
from contextlib import ExitStack
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

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

    def test_builder_restore_binding_roundtrips_through_runtime_authentication(self):
        from test_recovery_restore_media import policy as restore_policy
        from sv08_recovery_media import canonical_json, PROVIDER_MANIFEST, ENVELOPE_MANIFEST
        from sv08_recovery_restore_prepare import RestorePreparer, policy_binding
        policy=restore_policy()
        policy['boot']=dict(slot='A',release='fixture-release',state_schema=1,release_revision=7)
        envelope=b'fixture immutable envelope\n'
        policy['envelope_manifest_sha256']=hashlib.sha256(envelope).hexdigest()
        policy['image_manifest_sha256']=''
        original_inputs={'runtime/example.py':'c'*64}
        provider=m.compose_restore_provider_manifest(policy,original_inputs)
        self.assertNotIn('restore_policy',original_inputs)
        self.assertEqual(provider['inputs']['restore_policy'],policy_binding(policy))
        # The on-disk serialization includes a newline; that is not the normalized protocol hash.
        self.assertNotEqual(provider['inputs']['restore_policy'],hashlib.sha256(canonical_json(policy)).hexdigest())
        provider_data=canonical_json(provider)
        policy['image_manifest_sha256']=hashlib.sha256(provider_data).hexdigest()
        # Deserialize both real serialized artifacts, including the final image digest.
        preparer=RestorePreparer(json.loads(canonical_json(policy)))
        files={PROVIDER_MANIFEST:provider_data,ENVELOPE_MANIFEST:envelope}
        cmdline='sv08.recovery='+policy['image_manifest_sha256']+' sv08.envelope='+policy['envelope_manifest_sha256']
        with patch('sv08_recovery_restore_prepare.trusted_file',side_effect=files.__getitem__), \
             patch('sv08_recovery_restore_prepare.os.stat',return_value=SimpleNamespace(st_dev=1)), \
             patch('sv08_recovery_restore_prepare.Path.read_text',return_value=cmdline):
            preparer.authenticate()
            preparer.policy['boot']['release_revision']=8
            with self.assertRaisesRegex(ValueError,'Unreviewed restore policy'):preparer.authenticate()

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
            for name in ('sv08_recovery_activation.py','sv08_recovery_restore_prepare.py','sv08_restore.py', 'sv08_recovery_restore_media.py', 'sv08_recovery_media.py', 'sv08_recovery_prepare.py',
                         'sv08_recovery.py','sv08_recovery_ui.py','sv08_admin.py','sv08_export.py','sv08_state.py',
                         'sv08_admin_history.py','sv08_admin_jobs.py','sv08_data_budget.py','sv08_update_policy.py'):
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


class RecoveryReleaseSourceTests(unittest.TestCase):
    revision='a'*40

    def setUp(self):
        import project_license as license
        self.license=license
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.repo=Path(temporary.name);(self.repo/'build').mkdir()
        sources={'LICENSE':b'project license', 'LICENSING.md':b'project notice',
                 '.gitmodules':b'', 'upstream-lock.json':b'{}',
                 'runtime/controller.py':b'# runtime',
                 'configs/display.service':b'[Service]\nExecStart=/bin/true\n',
                 'configs/late.py':b'# final staged project file',
                 'configs/host-os/recovery-init':b'# boot gate'}
        for name,raw in sources.items():
            path=self.repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        self.manifest=self.repo/'release.json'
        self.value=dict(release='diagnostic-fixture',state_schema=1,release_revision=1,deployable=False,
            project_source_revision=self.revision,
            devices={name:'/dev/disk/by-partuuid/'+str(m.uuid.UUID(int=i+1))
                     for i,name in enumerate(('boot-a','root-a','boot-b','root-b','data','recovery'))})
        self.raw=(json.dumps(self.value,indent=3)+'\n').encode();self.manifest.write_bytes(self.raw)
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(m,'REPO',self.repo))
        self.stack.enter_context(patch.object(m,'integration_inputs',return_value={'fixture':'bound'}))
        self.stack.enter_context(patch.object(license,'source_state',return_value=(self.revision,False)))

    def root(self,work):
        root=work/'rootfs'
        for name in ('usr/lib/sv08','usr/bin','usr/sbin','boot','run','tmp','dev','proc','etc'):
            (root/name).mkdir(parents=True,exist_ok=True)
        (root/'usr/lib/sv08/controller.py').write_bytes((self.repo/'runtime/controller.py').read_bytes())
        (root/'usr/bin/busybox').write_bytes(b'fixture busybox')
        (root/'boot'/('vmlinuz-'+m.KERNEL)).write_bytes(b'fixture kernel')
        return root

    def public(self,root):
        import qualify_project_source as gate
        record=self.license.validate(root);stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w:gz') as archive:
            for name in record['source_files']:
                raw=(self.repo/name).read_bytes();entry=tarfile.TarInfo('source/'+name);entry.size=len(raw)
                archive.addfile(entry,io.BytesIO(raw))
        raw=stream.getvalue()
        manifest=dict(format_version=1,source_revision=self.revision,archive_prefix='source/',
            archive=dict(url='https://public.example/source/'+self.revision+'.tar.gz',sha256=self.license.digest(raw)))
        for group,names in gate.required_inputs(record['source_files']).items():
            manifest[group]=[dict(path=n,sha256=record['source_files'][n],archive_member=True) for n in sorted(names)]
        with patch.object(gate,'download',return_value=raw):result=gate.qualify(root,manifest)
        self.assertTrue(result['qualified']);self.assertFalse(result['overall_release_qualified'])
        return record

    def test_manifest_validation_exact_bytes_and_default_development_behavior(self):
        root=self.root(self.repo/'build/source')
        before=m.inventory(root)
        self.assertIsNone(m.finalize_project_source(root,None));self.assertEqual(before,m.inventory(root))
        release=m.release_manifest(self.manifest)
        self.assertEqual(release['raw'],self.raw)
        binding=m.finalize_project_source(root,release)
        self.assertEqual(binding['sha256'],self.license.digest(self.raw))
        self.assertEqual((root/'usr/lib/sv08/release.json').read_bytes(),self.raw)
        self.public(root);m.checked_project_source(root,binding)
        for update in ({'deployable':True},{'project_source_revision':'b'*40},{'state_schema':2},{'devices':{}}, {'release':None}):
            with self.subTest(update=update):
                self.manifest.write_text(json.dumps(dict(self.value,**update)))
                with self.assertRaises(ValueError):m.release_manifest(self.manifest)
        self.manifest.write_bytes(self.raw[:-2]+b',"release":"duplicate"}')
        with self.assertRaisesRegex(ValueError,'Duplicate'):m.release_manifest(self.manifest)
        self.manifest.write_bytes(self.raw)
        with patch.object(self.license,'source_state',return_value=(self.revision,True)):
            with self.assertRaisesRegex(ValueError,'clean'):m.release_manifest(self.manifest)
        release=m.release_manifest(self.manifest);self.manifest.write_bytes(self.raw+b' ')
        with self.assertRaisesRegex(ValueError,'changed during'):m.finalize_project_source(root,release)
        self.manifest.write_bytes(self.raw)
        for name in ('usr/lib/sv08/release.json','usr/lib/sv08/controller.py'):
            path=root/name;original=path.read_bytes();path.write_bytes(b'tampered')
            with self.assertRaises(ValueError):m.checked_project_source(root,binding)
            path.write_bytes(original)
        with self.assertRaisesRegex(ValueError,'differs'):
            m.checked_project_source(root,dict(binding,sha256='0'*64))

    def test_assemble_final_provenance_includes_late_files_and_bound_release(self):
        import stage_admin_ui
        intake=self.repo/'intake';intake.mkdir();archive=b'disposable package'
        digest=self.license.digest(archive);(intake/(digest+'.deb')).write_bytes(archive)
        lock=self.repo/'lock.json';lock.write_text(json.dumps(dict(packages=[dict(
            package='fixture',version='1',architecture='arm64',sha256=digest,bytes=len(archive))])))
        work=self.repo/'build/assembled'
        def run(args,**kw):
            if args[:2]==['dpkg-deb','-f']:
                return SimpleNamespace(stdout='Package: fixture\nVersion: 1\nArchitecture: arm64\n')
            if args[:2]==['dpkg-deb','--extract']:
                root=Path(args[-1]);doc=root/'usr/share/doc/fixture/copyright'
                doc.parent.mkdir(parents=True);doc.write_bytes(b'fixture notice')
                (root/'boot').mkdir()
            if 'dpkg-query' in args:return SimpleNamespace(stdout='fixture\t1\tinstalled\n',stderr='')
            return SimpleNamespace(stdout='',stderr='')
        def late_units(units):
            root=units.parents[2]
            target=root/'usr/lib/systemd/system/sv08-recovery-display.service'
            target.parent.mkdir(parents=True);target.write_bytes((self.repo/'configs/display.service').read_bytes())
        with patch.object(m,'run',side_effect=run),patch.object(m,'private'), \
             patch.object(m,'configure_recovery_password'),patch.object(m,'installed_provider_inputs',return_value={}), \
             patch.object(m,'stage_recovery_units',side_effect=late_units),patch.object(stage_admin_ui,'stage'):
            m.assemble(SimpleNamespace(work=work,intake=intake,lock=lock,execute=True,release_manifest=self.manifest))
        record=self.public(work/'rootfs')
        self.assertIn('usr/lib/systemd/system/sv08-recovery-display.service',record['staged_files'])
        receipt=json.loads((work/'assembly.json').read_text())
        self.assertEqual(receipt['root'],m.inventory(work/'rootfs'))
        self.assertEqual(receipt['release_manifest']['sha256'],self.license.digest(self.raw))

    def test_build_preserves_bound_source_and_emits_release_binding(self):
        source=self.repo/'build/source';root=self.root(source)
        binding=m.finalize_project_source(root,m.release_manifest(self.manifest))
        (source/'assembly.json').write_text(json.dumps(dict(root=m.inventory(root),
            integration_inputs=m.integration_inputs(),release_manifest=binding)))
        before=m.inventory(source);work=self.repo/'build/image'
        def run(args,**kw):
            if args[:2]==['cp','-a']:
                if Path(args[2]).is_dir():shutil.copytree(args[2],args[3],symlinks=True)
                else:shutil.copy2(args[2],args[3])
            elif args[0]=='mksquashfs':
                self.public(Path(args[1]).parent)
                Path(args[2]).write_bytes(b'compressed fixture')
            return SimpleNamespace(stdout='',stderr='')
        def initramfs(root,output,profile):output.write_bytes(b'fixture initramfs')
        with patch.object(m,'run',side_effect=run),patch.object(m,'private'), \
             patch.object(m,'initramfs',side_effect=initramfs),patch.object(m,'SIZE',4096):
            result=m.build(SimpleNamespace(assembly=source,work=work,execute=True))
        self.assertEqual(before,m.inventory(source));self.assertTrue(result['source_preserved'])
        self.assertEqual(result['release_manifest'],binding)
        self.assertEqual(json.loads((work/'build.json').read_bytes())['release_manifest'],binding)
        self.public(root)

    def test_derive_explicit_and_inherited_release_preserves_parent_and_final_source(self):
        source=self.repo/'build/parent';root=self.root(source)
        # Simulate early staging, then derive adds a final project file.
        notices,_=self.license.prepare(root,repo=self.repo);self.license.publish(root,notices)
        packages=self.repo/'packages';packages.mkdir()
        profile={'packages':[],'kernel_release':m.KERNEL}
        def run(args,**kw):
            if args[:2]==['cp','-a']:shutil.copytree(args[2],args[3],symlinks=True)
            return SimpleNamespace(stdout='',stderr='')
        for inherited in (False,True):
            with self.subTest(inherited=inherited):
                binding=m.finalize_project_source(root,m.release_manifest(self.manifest)) if inherited else None
                receipt=dict(root=m.inventory(root),integration_inputs=m.integration_inputs())
                if binding:receipt['release_manifest']=binding
                (source/'assembly.json').write_text(json.dumps(receipt))
                before=m.inventory(source);work=self.repo/('build/derived-'+str(inherited))
                def final_board(derived,profile):
                    (derived/'usr/lib/sv08/late.py').write_bytes((self.repo/'configs/late.py').read_bytes())
                with patch.object(m,'run',side_effect=run),patch.object(m,'private'), \
                     patch.object(m,'board_profile',return_value=profile), \
                     patch.object(m,'normalize_board_module_directory',side_effect=final_board),patch.object(m,'check_board_artifacts'):
                    m.derive(SimpleNamespace(assembly=source,work=work,packages=packages,board_profile='fixture',
                        execute=True,release_manifest=None if inherited else self.manifest))
                self.assertEqual(before,m.inventory(source))
                final=self.public(work/'rootfs');self.assertIn('usr/lib/sv08/late.py',final['staged_files'])
                record=json.loads((work/'assembly.json').read_text())
                self.assertEqual(record['root'],m.inventory(work/'rootfs'))
                self.assertTrue(record['parent_preserved'])
                snapshot=m.inventory(work)
                args=SimpleNamespace(assembly=work,work=self.repo/('build/image-'+str(inherited)),execute=False)
                m.build(args);self.assertEqual(snapshot,m.inventory(work))
                release=work/'rootfs/usr/lib/sv08/release.json';release.write_bytes(self.raw+b' ')
                with self.assertRaisesRegex(ValueError,'Stale installed release'):m.build(args)


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
