import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from finalize_diagnostic_host import MASKS, WIFI_FILES, finalize


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

    def test_writes_a_receipt_for_matching_non_deployable_inputs(self):
        with patch('finalize_diagnostic_host.initramfs_entries', return_value={
                'scripts/local-bottom/sv08-data'}):
            result = finalize(self.work, self.data, self.source, execute=True)
        self.assertEqual(result['schema'], 3)
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
