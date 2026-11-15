import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from finalize_diagnostic_host import MASKS, WIFI_FILES, finalize, main
from prepare_host_os import REPO, digest
from recovery_image import inventory, sha


class FinalizeDiagnosticHostTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name); self.work = self.base / 'work'; self.root = self.work / 'rootfs'
        self.data = self.base / 'data'; (self.work / 'refresh-complete').parent.mkdir()
        (self.work / 'refresh-complete').touch()
        devices = {name: '/dev/disk/by-partuuid/' + str(uuid.uuid4()) for name in
                   ('boot-a', 'root-a', 'boot-b', 'root-b', 'data', 'recovery')}
        release = dict(release='fixture-1', state_schema=1, deployable=False, devices=devices)
        (self.root / 'usr/lib/sv08/seed').mkdir(parents=True)
        (self.root / 'usr/lib/sv08/release.json').write_text(json.dumps(release))
        key = b'ssh-ed25519 fixture owner\n'
        (self.root / 'usr/lib/sv08/seed/authorized_keys').write_bytes(key)
        data_key = self.data / 'sv08/users/sv08/.ssh/authorized_keys'; data_key.parent.mkdir(parents=True)
        data_key.write_bytes(key)
        unit_dir = self.root / 'etc/systemd/system'; unit_dir.mkdir(parents=True)
        for name in MASKS:
            (unit_dir / (name + '.service')).symlink_to('/dev/null')
        for name in WIFI_FILES:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture\n')
        hook = self.root / 'etc/initramfs-tools/scripts/local-bottom/sv08-data'
        hook.parent.mkdir(parents=True)
        hook.write_text("DATA_DEVICE='" + devices['data'] + "'\n")
        initrd = self.root / 'boot/initrd.img-fixture'
        initrd.parent.mkdir(parents=True)
        initrd.write_bytes(b'fixture initramfs')
        self.source = self.base / 'source-finalized.json'
        self.source.write_text(json.dumps(dict(root=dict(schema=2, sha256='0' * 64, files=0, bytes=0))))

    def fresh_inputs(self):
        self.profile = self.base / 'reviewed.json'
        self.profile.write_bytes((REPO / 'configs/images/host-ab.json').read_bytes())
        (self.work / 'profile.json').write_bytes(self.profile.read_bytes())
        value = digest(json.loads(self.profile.read_text()))
        for stage in ('bootstrap-complete', 'packages-complete', 'refresh-complete'):
            (self.work / stage).write_text(value + '\n')

    def test_fresh_inspection_and_execution_bind_actual_inputs(self):
        self.fresh_inputs()
        with patch('finalize_diagnostic_host.initramfs_entries', return_value={
                'scripts/local-bottom/sv08-data'}), patch(
                'finalize_diagnostic_host.subprocess.run', return_value=
                subprocess.CompletedProcess([], 0, '', '')) as run:
            inspected = finalize(self.work, self.data, fresh=True, profile=self.profile)
            self.assertFalse((self.work / 'finalized.json').exists())
            result = finalize(self.work, self.data, fresh=True, profile=self.profile, execute=True)
        self.assertEqual(inspected, result)
        self.assertEqual(result['root'], inventory(self.root))
        self.assertNotIn('source_finalization_sha256', result)
        provenance = result['provenance']
        self.assertEqual(provenance['mode'], 'fresh')
        self.assertEqual(provenance['reviewed_profile_sha256'], sha(self.profile))
        self.assertEqual(provenance['staged_profile_sha256'], sha(self.work / 'profile.json'))
        for stage, value in provenance['stage_marker_sha256'].items():
            self.assertEqual(value, sha(self.work / stage))
        self.assertEqual(json.loads((self.work / 'finalized.json').read_text()), result)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[:2], [['chroot', str(self.root), 'dpkg', '--audit'],
                                       ['chroot', str(self.root), 'apt-get', 'check']])
        self.assertTrue(all(call.kwargs['timeout'] == 120 for call in run.call_args_list))

    def test_fresh_missing_stale_and_symlinked_inputs_refuse_before_chroot(self):
        for name in ('profile.json', 'bootstrap-complete', 'packages-complete', 'refresh-complete'):
            for fault in ('missing', 'stale', 'symlink'):
                with self.subTest(name=name, fault=fault):
                    self.fresh_inputs()
                    path = self.work / name
                    if fault == 'stale':
                        if name == 'profile.json':
                            value = json.loads(path.read_text()); value['snapshot'] = '20260902T000000Z'
                            path.write_text(json.dumps(value))
                        else:
                            path.write_text('stale\n')
                    else:
                        path.unlink()
                        if fault == 'symlink':
                            path.symlink_to(self.profile)
                    with patch('finalize_diagnostic_host.subprocess.run') as run:
                        with self.assertRaises(ValueError):
                            finalize(self.work, self.data, fresh=True, profile=self.profile, execute=True)
                        run.assert_not_called()
                    self.assertFalse((self.work / 'finalized.json').exists())
                    if path.is_symlink():
                        path.unlink()

    def test_fresh_package_audit_and_dependency_failures_refuse(self):
        self.fresh_inputs()
        for outputs in ([subprocess.CompletedProcess([], 0, 'unfinished package', '')],
                        [subprocess.CompletedProcess([], 0, '', 'audit warning')],
                        [subprocess.CalledProcessError(1, ['dpkg'])],
                        [subprocess.CompletedProcess([], 0, '', ''),
                         subprocess.CalledProcessError(100, ['apt-get'])]):
            with self.subTest(outputs=outputs), patch(
                    'finalize_diagnostic_host.subprocess.run', side_effect=outputs):
                with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                    finalize(self.work, self.data, fresh=True, profile=self.profile, execute=True)
                self.assertFalse((self.work / 'finalized.json').exists())

    def test_exactly_one_mode_required_for_api_and_cli(self):
        for kwargs in ({}, dict(fresh=True, source_receipt=self.source)):
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                finalize(self.work, self.data, **kwargs)
        for options in ([], ['--fresh', '--source-receipt', str(self.source)]):
            with patch.object(sys, 'argv', ['finalize', '--work', str(self.work),
                                           '--data', str(self.data), *options]):
                with self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code, 2)

    def test_writes_a_receipt_for_matching_non_deployable_inputs(self):
        with patch('finalize_diagnostic_host.initramfs_entries', return_value={
                'scripts/local-bottom/sv08-data'}):
            result = finalize(self.work, self.data, self.source, execute=True)
        self.assertEqual(result['schema'], 3)
        self.assertEqual(result['source_finalization_sha256'], sha(self.source))
        self.assertNotIn('provenance', result)
        self.assertTrue(result['checks']['owner_key_seeded'])
        self.assertTrue(result['checks']['boot_health_masked'])
        self.assertTrue(result['checks']['wifi_userspace_present'])
        self.assertTrue((self.work / 'finalized.json').is_file())

    def test_mismatched_owner_key_refuses_without_receipt(self):
        (self.data / 'sv08/users/sv08/.ssh/authorized_keys').write_text('other\n')
        with self.assertRaisesRegex(ValueError, 'seeds differ'):
            finalize(self.work, self.data, self.source, execute=True)
        self.assertFalse((self.work / 'finalized.json').exists())

    def test_missing_wifi_userspace_refuses_without_receipt(self):
        (self.root / WIFI_FILES[0]).unlink()
        with self.assertRaisesRegex(ValueError, 'missing Wi-Fi userspace'):
            finalize(self.work, self.data, self.source, execute=True)
        self.assertFalse((self.work / 'finalized.json').exists())

    def test_unmasked_boot_health_refuses_without_receipt(self):
        (self.root / 'etc/systemd/system/sv08-boot-health.service').unlink()
        with self.assertRaisesRegex(ValueError, 'sv08-boot-health'):
            finalize(self.work, self.data, self.source, execute=True)
        self.assertFalse((self.work / 'finalized.json').exists())

    def test_rejects_initramfs_without_persistent_identity_hook(self):
        with patch('finalize_diagnostic_host.initramfs_entries', return_value=set()):
            with self.assertRaisesRegex(ValueError, 'omits the persistent identity hook'):
                finalize(self.work, self.data, self.source, execute=True)
        self.assertFalse((self.work / 'finalized.json').exists())


if __name__ == '__main__':
    unittest.main()
