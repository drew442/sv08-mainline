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

    def test_public_certificate_refuses_private_or_mixed_input(self):
        cert=self.certificate(); self.assertEqual(public_certificate(cert),cert.read_bytes())
        raw=cert.read_bytes(); cert.write_bytes(raw+b'private annotation\n')
        with self.assertRaises(ValueError): public_certificate(cert)
        cert.write_bytes(raw+(self.base/'synthetic.key').read_bytes())
        with self.assertRaises(ValueError): public_certificate(cert)
        with self.assertRaises(ValueError): public_certificate(None)

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
        cert=self.certificate();value=profile();manifest=profile_check(value)
        with patch('integrate_host_os.rebuild_initramfs') as rebuild:
            stage(work,manifest,supported_profile=value,release_certificate=cert)
        rebuild.assert_called_once()
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

    def test_supported_finalization_rejects_drift_and_nonempty_data(self):
        from finalize_supported_host import checks, WIFI_FILES
        work,root,_=integration.IntegrationManifestTests.admission_fixture(self)
        shutil.rmtree(root/'home/sovol')
        (root/'etc/shadow').write_text('root:*:20000:0:99999:7:::\nsv08:!:0:0:99999:7:::\n')
        value=profile();cert=self.certificate()
        with patch('integrate_host_os.rebuild_initramfs'): stage(work,profile_check(value),supported_profile=value,release_certificate=cert)
        data=self.base/'data';data.mkdir()
        for name in WIFI_FILES:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.touch()
        (root/'boot/initrd.img-test').touch()
        with patch('finalize_supported_host.initramfs_entries',return_value={'scripts/local-bottom/sv08-data'}), \
             patch('project_license.validate',return_value=dict(development=False,source_revision='a'*40)):
            result=checks(root,data,value);self.assertFalse(result['release_qualified'])
            (data/'owner-state').touch()
            with self.assertRaisesRegex(ValueError,'empty'): checks(root,data,value)
            (data/'owner-state').unlink()
            path=root/'usr/lib/sv08/environment-device.json';path.write_text('{}')
            with self.assertRaisesRegex(ValueError,'binding'): checks(root,data,value)


if __name__ == '__main__': unittest.main()
