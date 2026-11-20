"""Supported candidate contracts; synthetic inputs are not artifact qualification."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from supported_candidate import profile_check, backend_documents, public_account_checks, public_certificate
from integrate_host_os import stage, validate
from assemble_board_diagnostic import seed_environment, MASKS
from test_data_budget import fixture_root
import test_host_integration as integration


def profile():
    from sv08_printer_calibration import KLIPPER_REVISION
    return dict(format_version=1, purpose='supported-configured-printer-candidate',
                hardware_profile='test-sv08-01', release='fixture-rc1', release_revision=1,
                project_source_revision='a'*40, compatible='sv08-test-sv08-01-ab8g-v1',
                expected_cid_sha256='b'*64, board_mmc_device_index=1,
                klipper_commit=KLIPPER_REVISION)


class SupportedCandidate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=fixture_root()); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def certificate(self):
        key, cert = self.base/'synthetic.key', self.base/'authority.pem'
        subprocess.run(['openssl','req','-new','-x509','-newkey','ed25519','-nodes',
                        '-keyout',str(key),'-out',str(cert),'-subj','/CN=Disposable candidate test/', '-days','1'],
                       check=True, capture_output=True, timeout=10)
        return cert

    def test_explicit_profile_and_diagnostic_entry_contract(self):
        value=profile(); manifest=profile_check(value)
        with self.assertRaises(ValueError): validate(manifest)
        validate(manifest,supported=True)
        for field, wrong in [('purpose','physical-update-qualification'),('hardware_profile','other'),
                              ('board_mmc_device_index',True),('expected_cid_sha256','unknown'),
                              ('expected_cid_sha256',None),('release',1),
                              ('klipper_commit','0'*40),('release_revision',True)]:
            changed={**value,field:wrong}
            with self.subTest(field=field), self.assertRaises(ValueError): profile_check(changed)
        with self.assertRaises(ValueError): profile_check({**value,'test_only':True})
        legacy=seed_environment(); supported=seed_environment(supported=True)
        for name in MASKS:
            self.assertIn('systemd.mask='+name+'.service', legacy)
            self.assertNotIn('systemd.mask='+name+'.service', supported)
        self.assertIn('BOOT_A_LEFT=3\n',supported)
        self.assertNotIn('saveenv',supported.split('sv08_consoleargs=')[0])

    def test_supported_finalizer_requires_matching_clean_source(self):
        from finalize_supported_host import source_check
        with patch('project_license.source_state',return_value=('a'*40,False)):
            source_check(profile())
        for state in [('b'*40,False),('a'*40,True),(None,False)]:
            with self.subTest(state=state),patch('project_license.source_state',return_value=state),self.assertRaisesRegex(ValueError,'Freeze clean'):
                source_check(profile())

    def test_recovery_component_identity_preserves_normal_release_without_host_authority(self):
        import recovery_image
        from integrate_host_os import firmware_manifest
        normal=firmware_manifest(profile_check(profile()))
        recovery={**normal,'deployable':False,'component':'independent-recovery'}
        path=self.base/'recovery-release.json';path.write_text(json.dumps(recovery))
        with patch('project_license.source_state',return_value=('a'*40,False)):
            bound=recovery_image.release_manifest(path)
        self.assertEqual(json.loads(bound['raw']),recovery)
        self.assertEqual(recovery['mcu_firmware'],normal['mcu_firmware'])
        self.assertEqual(recovery['devices'],normal['devices'])
        self.assertTrue(normal['deployable']);self.assertFalse(recovery['deployable'])

    def test_public_certificate_refuses_private_or_mixed_input(self):
        cert=self.certificate(); self.assertEqual(public_certificate(cert),cert.read_bytes())
        raw=cert.read_bytes(); cert.write_bytes(raw+b'private annotation\n')
        with self.assertRaises(ValueError): public_certificate(cert)
        cert.write_bytes(raw+(self.base/'synthetic.key').read_bytes())
        with self.assertRaises(ValueError): public_certificate(cert)
        with self.assertRaises(ValueError): public_certificate(None)

    def test_optional_lan_feed_retains_https_and_fixed_public_trust(self):
        value={**profile(),'feed':dict(url='https://192.0.2.10:8443/releases/',channel='stable')}
        documents=backend_documents(value)
        self.assertEqual(documents['feed.json']['ca_file'],'/etc/rauc/release-keyring.pem')
        self.assertEqual(documents['feed.json']['signer_ca_file'],documents['feed.json']['ca_file'])
        self.assertNotIn('feed.json',backend_documents(profile()))
        for url in ('http://192.0.2.10/releases/','https://user:password@example.test/releases/',
                    'https://example.test/releases/?q=1','https://example.test/releases',
                    'https://example.test/\nreleases/'):
            with self.subTest(url=url),self.assertRaises(ValueError):
                profile_check({**value,'feed':dict(url=url,channel='stable')})

    def test_independent_sd_profile_keeps_distinct_root_and_common_board_pins(self):
        from recovery_image import board_profile, boot_gate
        from build_sd_recovery_host import PARTUUID, ROOT_UUID
        normal=board_profile(ROOT/'configs/host-os/recovery-test-sv08-01.json')
        sd=board_profile(ROOT/'configs/host-os/supported/recovery-sd.json')
        self.assertEqual(sd['artifacts'],normal['artifacts']);self.assertEqual(sd['packages'],normal['packages'])
        self.assertEqual(sd['recovery']['partuuid'],PARTUUID);self.assertEqual(sd['recovery']['filesystem_uuid'],ROOT_UUID)
        self.assertTrue(set(p['partuuid'] for p in normal['partitions']).isdisjoint(p['partuuid'] for p in sd['partitions']))
        gate=boot_gate(sd)
        self.assertIn('root=PARTUUID='+PARTUUID,gate);self.assertIn("= '2'",gate)
        self.assertNotIn(normal['recovery']['filesystem_uuid'],gate)
        self.assertIn('ro,noload',gate);self.assertNotIn('fw_setenv',gate)
        subprocess.run(['/bin/sh','-n'],input=gate,text=True,check=True,timeout=10)
        wrong=copy.deepcopy(sd);wrong['recovery']['index']=5
        path=self.base/'bad-sd.json';path.write_text(json.dumps(wrong))
        with self.assertRaises(ValueError): board_profile(path)

    def test_supported_stage_uses_no_owner_seed_and_preserves_production_health(self):
        work,root,_=integration.IntegrationManifestTests.admission_fixture(self)
        shutil.rmtree(root/'home/sovol')
        (root/'etc/shadow').write_text('root:*:20000:0:99999:7:::\nsv08:!:0:0:99999:7:::\n')
        password_stack=root/'etc/pam.d/common-password';password_stack.parent.mkdir(parents=True,exist_ok=True)
        vendor=b'# vendor header\n# here are the per-package modules (the Primary block)\npassword [success=1 default=ignore] pam_unix.so obscure yescrypt\npassword requisite pam_deny.so\n'
        password_stack.write_bytes(vendor)
        cert=self.certificate();value=profile();manifest=profile_check(value)
        with patch('integrate_host_os.rebuild_initramfs') as rebuild:
            stage(work,manifest,supported_profile=value,release_certificate=cert)
        rebuild.assert_called_once()
        policy=(ROOT/'configs/host-os/supported/owner-password-policy.conf').read_bytes()
        self.assertEqual(password_stack.read_bytes(),policy+vendor)
        self.assertEqual(password_stack.read_bytes().count(b'password requisite pam_succeed_if.so quiet user != sv08'),1)
        self.assertEqual((root/'usr/lib/sv08/seed/authorized_keys').read_bytes(),b'')
        self.assertIn('sv08:*::0:99999:7:::',(root/'etc/shadow').read_text())
        public_account_checks(root)
        self.assertFalse((root/'etc/systemd/system/sv08-boot-health.service').is_symlink())
        self.assertTrue((root/'etc/systemd/system/multi-user.target.wants/sv08-boot-health.service').is_symlink())
        self.assertFalse((root/'etc/systemd/system/multi-user.target.wants/sv08-klipper.service').exists())
        self.assertIn('sv08_commissioning.py check',(root/'etc/systemd/system/sv08-klipper.service.d/supported-commissioning.conf').read_text())
        units=root/'etc/systemd/system'
        self.assertEqual((units/'multi-user.target.wants/sv08-commissioned-start.service').readlink(),
                         Path('../sv08-commissioned-start.service'))
        activation=(units/'sv08-commissioned-start.service').read_text()
        self.assertIn('Requires=sv08-prepare.service sv08-boot-health.service',activation)
        self.assertIn('After=sv08-prepare.service sv08-boot-health.service',activation)
        self.assertIn('sv08_commissioning.py boot-activate',activation)
        self.assertNotIn('Wants=sv08-klipper',activation)
        self.assertNotIn('Before=sv08-klipper',activation)
        self.assertFalse((units/'multi-user.target.wants/sv08-moonraker.service').exists())
        for name,document in backend_documents(value).items():
            if name!='release.json': self.assertEqual(json.loads((root/'usr/lib/sv08'/name).read_text()),document)
        original=(root/'etc/shadow').read_bytes()
        with self.assertRaises(ValueError):
            stage(work,manifest,owner_key=cert,supported_profile=value,release_certificate=cert)
        self.assertEqual((root/'etc/shadow').read_bytes(),original)
        # No inherited credential or first-login expiry can pass public finalization.
        for replacement in ('sv08:$6$inherited::0:99999:7:::\n','sv08:*:0:0:99999:7:::\n','sv08::20000:0:99999:7:::\n'):
            (root/'etc/shadow').write_text('root:*:20000:0:99999:7:::\n'+replacement)
            with self.assertRaises(ValueError): public_account_checks(root)

    def test_diagnostic_stage_preserves_vendor_password_stack(self):
        work,root,_=integration.IntegrationManifestTests.admission_fixture(self)
        password_stack=root/'etc/pam.d/common-password';password_stack.parent.mkdir(parents=True,exist_ok=True)
        vendor=b'# vendor header\npassword required pam_unix.so\n';password_stack.write_bytes(vendor)
        manifest=integration.IntegrationManifestTests.manifest(self)
        with patch('integrate_host_os.rebuild_initramfs'):stage(work,manifest)
        self.assertEqual(password_stack.read_bytes(),vendor)

    def test_supported_finalization_rejects_drift_and_nonempty_data(self):
        from finalize_supported_host import checks, WIFI_FILES
        work,root,_=integration.IntegrationManifestTests.admission_fixture(self)
        shutil.rmtree(root/'home/sovol')
        (root/'etc/shadow').write_text('root:*:20000:0:99999:7:::\nsv08:!:0:0:99999:7:::\n')
        password_stack=root/'etc/pam.d/common-password';password_stack.parent.mkdir(parents=True,exist_ok=True)
        password_stack.write_bytes(b'# vendor stack\npassword required pam_unix.so\n')
        value=profile();cert=self.certificate()
        with patch('integrate_host_os.rebuild_initramfs'): stage(work,profile_check(value),supported_profile=value,release_certificate=cert)
        # Exercise the real composition boundary: admin staging creates the
        # persistent certificate binding consumed by supported finalization.
        from stage_admin_ui import stage as stage_admin
        with patch('project_license.source_state',return_value=('a'*40,False)):
            staged=stage_admin(work,'host',execute=True,refresh=True)
        certs=root/'etc/cockpit/ws-certs.d'
        canonical=certs.readlink()
        self.assertEqual(canonical,Path('/data/sv08/system/cockpit/ws-certs.d'))
        self.assertIn('etc/cockpit/ws-certs.d',staged['hashes'])
        # Never follow the absolute certificate link into the build host.
        exists,iterdir=Path.exists,Path.iterdir
        def no_cert_exists(path):
            self.assertNotEqual(path,certs,'Certificate link was followed')
            return exists(path)
        def no_cert_iterdir(path):
            self.assertNotEqual(path,certs,'Certificate link was followed')
            return iterdir(path)
        with patch.object(Path,'exists',no_cert_exists),patch.object(Path,'iterdir',no_cert_iterdir):
            public=public_account_checks(root)
        self.assertTrue(public['inherited_identity_absent'])
        data=self.base/'data';data.mkdir()
        for name in WIFI_FILES:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.touch()
        (root/'boot/initrd.img-test').touch()
        with patch('finalize_supported_host.initramfs_entries',return_value={'scripts/local-bottom/sv08-data'}), \
             patch('project_license.validate',return_value=dict(development=False,source_revision='a'*40)):
            result=checks(root,data,value);self.assertFalse(result['release_qualified'])
            activation=root/'etc/systemd/system/sv08-commissioned-start.service'
            original_activation=activation.read_bytes()
            activation.write_bytes(original_activation.replace(b'After=',b'#After='))
            with self.assertRaisesRegex(ValueError,'service differs'):checks(root,data,value)
            activation.write_bytes(original_activation)
            activation_link=root/'etc/systemd/system/multi-user.target.wants/sv08-commissioned-start.service'
            activation_link.unlink()
            with self.assertRaisesRegex(ValueError,'boot activation'):checks(root,data,value)
            activation_link.symlink_to('../sv08-boot-health.service')
            with self.assertRaisesRegex(ValueError,'boot activation'):checks(root,data,value)
            activation_link.unlink();activation_link.symlink_to('../sv08-commissioned-start.service')
            physical=root/'etc/systemd/system/multi-user.target.wants/sv08-klipper.service'
            physical.symlink_to('../sv08-klipper.service')
            with self.assertRaisesRegex(ValueError,'must not autostart'):checks(root,data,value)
            physical.unlink()
            # Wrong/relative links and private certificate directories remain
            # forbidden, and diagnostics never copy credential bytes.
            secret='synthetic-private-credential-do-not-publish'
            private=self.base/'private-certs';private.mkdir()
            (private/'host.key').write_text(secret)
            for target in (private,Path('../../data/sv08/system/cockpit/ws-certs.d'),
                           Path('/data/sv08/system/cockpit/other'),
                           '/data//sv08/system/cockpit/ws-certs.d'):
                with self.subTest(target=target):
                    certs.unlink();certs.symlink_to(target)
                    with self.assertRaisesRegex(ValueError,'private state') as raised:
                        checks(root,data,value)
                    self.assertNotIn(secret,str(raised.exception))
            certs.unlink();certs.mkdir();(certs/'host.key').write_text(secret)
            with self.assertRaisesRegex(ValueError,'private state') as raised:
                checks(root,data,value)
            self.assertNotIn(secret,str(raised.exception))
            (certs/'host.key').unlink();certs.rmdir();certs.symlink_to(canonical)
            embedded=root/'data';embedded.mkdir(exist_ok=True)
            checks(root,data,value)
            (embedded/'host.key').write_text(secret)
            with self.assertRaisesRegex(ValueError,'embedded data') as raised:
                checks(root,data,value)
            self.assertNotIn(secret,str(raised.exception))
            (embedded/'host.key').unlink();embedded.rmdir();embedded.symlink_to(private)
            with self.assertRaisesRegex(ValueError,'embedded data'):checks(root,data,value)
            embedded.unlink()
            correct=password_stack.read_bytes()
            password_stack.write_bytes(b'# reordered policy\n'+correct)
            with self.assertRaisesRegex(ValueError,'password policy'):checks(root,data,value)
            password_stack.write_bytes(b'password required pam_unix.so\n')
            with self.assertRaisesRegex(ValueError,'password policy'):checks(root,data,value)
            password_stack.write_bytes(correct)
            (data/'owner-state').touch()
            with self.assertRaisesRegex(ValueError,'empty'): checks(root,data,value)
            (data/'owner-state').unlink()
            path=root/'usr/lib/sv08/environment-device.json';path.write_text('{}')
            with self.assertRaisesRegex(ValueError,'binding'): checks(root,data,value)




class IndependentSDPayloadTests(unittest.TestCase):
    def test_explicit_source_pin(self):
        import hashlib
        from assemble_supported_candidate import recovery_source_check
        producer='a'*40;current='b'*40
        record={'release_manifest':{'project_source_revision':producer}}
        sources={'runtime/protected.py':b'protected',
                 'scripts/assemble_supported_candidate.py':b'old wrapper',
                 'tests/test_supported_candidate.py':b'old test'}
        tree=b''.join(b'100644 blob '+b'c'*40+b'\t'+name.encode()+b'\0' for name in sources)
        blobs=b''.join(b'c'*40+b' blob '+str(len(raw)).encode()+b'\n'+raw+b'\n' for raw in sources.values())
        hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}
        hashes['scripts/assemble_supported_candidate.py']='d'*64
        hashes['tests/test_supported_candidate.py']='e'*64
        def git(args,**kwargs):
            self.assertEqual(kwargs['timeout'],30)
            command=args[3]
            if command=='merge-base':return b''
            if command=='diff':
                self.assertEqual(args[4:],['--quiet',producer,current,'--','upstream/'])
                return b''
            if command=='ls-tree':return tree
            if command=='cat-file':return blobs
            self.fail(str(args))
        with patch('subprocess.check_output',side_effect=git), patch('project_license.source_files',return_value=hashes):
            self.assertEqual(recovery_source_check(ROOT,record,current,False,producer),producer)
            for pin in ('',True,42,'A'*40,'a'*39,'a'*41):
                with self.subTest(pin=pin), self.assertRaisesRegex(ValueError,'SHA40'):
                    recovery_source_check(ROOT,record,current,False,pin)
            with self.assertRaisesRegex(ValueError,'current project source revision'):
                recovery_source_check(ROOT,record,current,False,None)
            with self.assertRaisesRegex(ValueError,'differs from pin'):
                recovery_source_check(ROOT,record,current,False,'c'*40)
            with self.assertRaisesRegex(ValueError,'clean current'):
                recovery_source_check(ROOT,record,current,True,producer)
            for mutation in ({**hashes,'runtime/protected.py':'0'*64},
                             {**hashes,'runtime/added.py':'0'*64},
                             {name:value for name,value in hashes.items() if name!='runtime/protected.py'}):
                with patch('project_license.source_files',return_value=mutation):
                    with self.assertRaisesRegex(ValueError,'protected project source'):
                        recovery_source_check(ROOT,record,current,False,producer)
            def changed_gitlink(args,**kwargs):
                if args[3]=='diff':raise subprocess.CalledProcessError(1,args)
                return git(args,**kwargs)
            with patch('subprocess.check_output',side_effect=changed_gitlink):
                with self.assertRaisesRegex(ValueError,'upstream gitlinks'):
                    recovery_source_check(ROOT,record,current,False,producer)
            with patch('subprocess.check_output',side_effect=subprocess.CalledProcessError(1,['git'])):
                with self.assertRaisesRegex(ValueError,'available ancestor'):
                    recovery_source_check(ROOT,record,current,False,producer)

    def test_export_restore_admission_and_integrity(self):
        import gzip
        import hashlib
        from contextlib import ExitStack
        import recovery_image as recovery
        from assemble_supported_candidate import sd_payloads
        with tempfile.TemporaryDirectory(dir=fixture_root()) as directory:
            base=Path(directory);(base/'build').mkdir();source=base/'build/recovery';source.mkdir()
            board=copy.deepcopy(recovery.board_profile(ROOT/'configs/host-os/supported/recovery-sd.json'))
            envelope=source/'envelope';envelope.mkdir()
            dtb=b'fixture dtb';board['artifacts']['dtb']['sha256']=hashlib.sha256(dtb).hexdigest()
            usr=envelope/'usr.squashfs';usr.write_bytes(b'fixture compressed usr')
            manifests=envelope/'etc/sv08';manifests.mkdir(parents=True,exist_ok=True)
            (manifests/'recovery-image.json').write_text('{"fixture":"provider"}\n')
            (manifests/'recovery-envelope.manifest').write_text('usr_sha256='+recovery.sha(usr)+'\n')
            raw=b'fixture kernel';(source/'vmlinuz').write_bytes(gzip.compress(raw))
            (source/'initrd.img').write_bytes(b'fixture initrd')
            (source/'recovery.ext4').write_bytes(b'fixture root')
            record=dict(board_profile=board,usr_sha256=recovery.sha(usr),integration_inputs=recovery.integration_inputs(),
                        release_manifest=dict(project_source_revision='a'*40),
                        image_sha256=recovery.sha(source/'recovery.ext4'),envelope=recovery.inventory(envelope),
                        kernel_sha256=recovery.sha(source/'vmlinuz'),initrd_sha256=recovery.sha(source/'initrd.img'),
                        manifest_sha256=recovery.sha(manifests/'recovery-envelope.manifest'),
                        provider_manifest_sha256=recovery.sha(manifests/'recovery-image.json'))
            # Use file digests as emitted by the builder, not truthy mode markers.
            profile=base/'profile.json';profile.write_text('{"fixture":"reviewed"}\n');digest=recovery.sha(profile)
            def run(*args):
                if args[0]=='unsquashfs':
                    self.assertEqual(args,('unsquashfs','-cat',usr,board['artifacts']['dtb']['path'][4:]))
                    self.assertFalse((envelope/board['artifacts']['dtb']['path']).exists())
                    return dtb
                self.assertEqual(args[0],'mkimage');Path(args[-1]).write_bytes(b'compiled fixture script')
            from prepare_host_os import work_path
            def fixture_work_path(path):
                with patch('prepare_host_os.REPO',base):return work_path(path)
            with ExitStack() as stack:
                stack.enter_context(patch('assemble_supported_candidate.work_path',side_effect=fixture_work_path))
                stack.enter_context(patch('project_license.source_state',return_value=('a'*40,False)))
                stack.enter_context(patch('assemble_board_diagnostic.RAW_IMAGE',hashlib.sha256(raw).hexdigest()))
                stack.enter_context(patch('assemble_board_diagnostic.run',side_effect=run))
                stack.enter_context(patch('recovery_image.board_profile',return_value=board))
                for key in ('media_profile_sha256','restore_profile_sha256'):
                    (source/'build.json').write_text(json.dumps({**record,key:digest}))
                    before=recovery.inventory(source);output=base/'build'/key
                    result=sd_payloads(source,output)
                    self.assertFalse(result['deployable']);self.assertFalse(result['physical_boot'])
                    args=(output/'boot.cmd').read_text().splitlines()[0].split()
                    for arg,field in (('sv08.envelope=', 'manifest_sha256'),
                                      ('sv08.recovery=', 'provider_manifest_sha256')):
                        self.assertEqual([token.rstrip('"') for token in args if token.startswith(arg)],
                                         [arg+record[field]])
                    self.assertNotEqual(record['manifest_sha256'],record['provider_manifest_sha256'])
                    self.assertEqual((output/'boot/sv08.dtb').read_bytes(),dtb)
                    self.assertEqual(result['producer_source_revision'],'a'*40)
                    self.assertEqual(result['builder_source_revision'],'a'*40)
                    self.assertEqual((output/'boot/Image').read_bytes(),raw)
                    self.assertEqual(recovery.sha(output/'recovery.ext4'),record['image_sha256'])
                    self.assertEqual(recovery.inventory(source),before)
                (source/'build.json').write_text(json.dumps({**record,'media_profile_sha256':digest}))
                with patch('project_license.source_state',return_value=('b'*40,False)), \
                     patch('assemble_supported_candidate.recovery_source_check',return_value='a'*40) as admission:
                    result=sd_payloads(source,base/'build/pinned','a'*40)
                    admission.assert_called_once_with(ROOT,{**record,'media_profile_sha256':digest},'b'*40,False,'a'*40)
                    self.assertEqual(result['producer_source_revision'],'a'*40)
                    self.assertEqual(result['builder_source_revision'],'b'*40)
                before=recovery.inventory(source)
                for label,effect in (('extraction',subprocess.CalledProcessError(1,['unsquashfs'])),
                                     ('dtb-hash',lambda *args:b'changed dtb')):
                    output=base/'build'/label
                    with patch('assemble_board_diagnostic.run',side_effect=effect):
                        with self.assertRaises((ValueError,subprocess.CalledProcessError)):
                            sd_payloads(source,output)
                    self.assertFalse(output.exists());self.assertEqual(recovery.inventory(source),before)
                for label,changed in (('usr-record',{**record,'usr_sha256':'0'*64}),
                                      ('usr-file',{**record,'usr_sha256':'1'*64})):
                    (source/'build.json').write_text(json.dumps({**changed,'media_profile_sha256':digest}))
                    output=base/'build'/label
                    with self.assertRaisesRegex(ValueError,'compressed userspace'):sd_payloads(source,output)
                    self.assertFalse(output.exists())
                original_usr=usr.read_bytes();usr.write_bytes(b'changed compressed usr')
                changed={**record,'media_profile_sha256':digest,'envelope':recovery.inventory(envelope)}
                (source/'build.json').write_text(json.dumps(changed));output=base/'build/usr-content'
                with self.assertRaisesRegex(ValueError,'compressed userspace'):sd_payloads(source,output)
                self.assertFalse(output.exists());usr.write_bytes(original_usr)
                manifest=manifests/'recovery-envelope.manifest';original_manifest=manifest.read_bytes()
                for number,text in enumerate(('usr_sha256='+'0'*64+'\n',original_manifest.decode()*2)):
                    manifest.write_text(text)
                    changed={**record,'media_profile_sha256':digest,'envelope':recovery.inventory(envelope),
                             'manifest_sha256':recovery.sha(manifest)}
                    (source/'build.json').write_text(json.dumps(changed));output=base/'build'/f'usr-manifest-{number}'
                    with self.assertRaisesRegex(ValueError,'compressed userspace'):sd_payloads(source,output)
                    self.assertFalse(output.exists())
                manifest.write_bytes(original_manifest)
                invalid=[{},dict(media_profile_sha256=digest,restore_profile_sha256=digest)]
                for key in ('media_profile_sha256','restore_profile_sha256'):
                    invalid.extend({key:value} for value in (None,'',True,42,'reviewed','A'*64,'g'*64))
                    invalid.append({key:digest,('restore_profile_sha256' if key=='media_profile_sha256' else 'media_profile_sha256'):None})
                for number,binding in enumerate(invalid):
                    with self.subTest(binding=binding):
                        (source/'build.json').write_text(json.dumps({**record,**binding}))
                        output=base/'build'/('invalid-'+str(number));before=recovery.inventory(source)
                        with self.assertRaisesRegex(ValueError,'exactly one reviewed'):sd_payloads(source,output)
                        self.assertFalse(output.exists());self.assertEqual(recovery.inventory(source),before)
                for field in ('manifest_sha256','provider_manifest_sha256'):
                    for number,value in enumerate((None,'',True,42,'reviewed','A'*64,'g'*64,'0'*64,'missing')):
                        with self.subTest(manifest=field,value=value):
                            changed={**record,'media_profile_sha256':digest,field:value}
                            if value == 'missing':del changed[field]
                            (source/'build.json').write_text(json.dumps(changed))
                            output=base/'build'/f'{field}-{number}'
                            with self.assertRaisesRegex(ValueError,field):sd_payloads(source,output)
                            self.assertFalse(output.exists())
                    manifest=manifests/('recovery-envelope.manifest' if field=='manifest_sha256' else 'recovery-image.json')
                    contents=manifest.read_bytes();manifest.unlink()
                    changed={**record,'media_profile_sha256':digest,'envelope':recovery.inventory(envelope)}
                    (source/'build.json').write_text(json.dumps(changed))
                    output=base/'build'/f'{field}-absent-file'
                    with self.assertRaisesRegex(ValueError,field):sd_payloads(source,output)
                    self.assertFalse(output.exists());manifest.write_bytes(contents)
                for field,value in [('integration_inputs',{}),('image_sha256','0'*64),('envelope',{}),
                                    ('kernel_sha256','0'*64),('initrd_sha256','0'*64),
                                    ('release_manifest',dict(project_source_revision='b'*40))]:
                    with self.subTest(drift=field):
                        (source/'build.json').write_text(json.dumps({**record,'media_profile_sha256':digest,field:value}))
                        output=base/'build'/('drift-'+field)
                        with self.assertRaises(ValueError):sd_payloads(source,output)
                        self.assertFalse(output.exists())


class RecoveryOwnerDependencyTests(unittest.TestCase):
    def test_default_supplement_adds_openssl_without_replacing_base(self):
        import recovery_image as recovery
        from types import SimpleNamespace
        lock=ROOT/'configs/host-os/recovery-packages.json'
        supplement=ROOT/'configs/host-os/supported/recovery-owner-packages.json'
        before=(lock.read_bytes(),supplement.read_bytes())
        _,_,packages,_,binding=recovery.package_inputs(SimpleNamespace(
            lock=lock,package_supplement=supplement),ROOT/'build/supplement-inspection-unused')
        base=json.loads(before[0])['packages']
        self.assertEqual(packages[:len(base)],base)
        self.assertEqual([p['package'] for p in packages[len(base):]],['openssl'])
        self.assertEqual(binding['package_supplement_sha256'],recovery.sha(supplement))
        self.assertEqual((lock.read_bytes(),supplement.read_bytes()),before)
        self.assertEqual(recovery.integration_inputs()[str(supplement.relative_to(ROOT))],recovery.sha(supplement))

if __name__ == '__main__': unittest.main()
