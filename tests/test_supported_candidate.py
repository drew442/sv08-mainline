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
