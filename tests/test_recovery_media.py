import copy
import json
import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_recovery_media import (Kernel, MediaProvider, PROTOCOL, WRITER_MODEL,
                                 POLICY, Unavailable, durable_identity, fingerprint, mount_table,
                                 opened, production_adapter, trusted_file)
from sv08_recovery import installed_controller
from sv08_state import Store


class RecoveryMediaTests(unittest.TestCase):
    def setUp(self):
        self.policy = dict(format_version=1, kind='independent-recovery', protocol=PROTOCOL,
                           writer_model=WRITER_MODEL, image_manifest_sha256='1'*64,
                           recovery={}, source={}, system_media=[{'wwid':'reviewed-root'}])
        self.context = dict(format_version=1, protocol=PROTOCOL, policy_sha256=fingerprint(self.policy),
                            source='/data', destinations={'usb': dict(path='/media/usb', label='Reviewed USB')},
                            expected={})

    def adapter(self, policy, context):
        with patch('sv08_recovery_media.trusted_file', side_effect=[json.dumps(policy).encode(), json.dumps(context).encode()]):
            return production_adapter()

    def test_mount_parser_distinguishes_vfs_from_superblock_and_decodes_paths(self):
        mounts = mount_table('41 30 8:1 / /source\\040data ro,noatime - ext4 /dev/sda1 rw,norecovery\n')
        self.assertEqual(mounts[0]['path'], '/source data')
        self.assertIn('ro', mounts[0]['options'])
        self.assertIn('rw', mounts[0]['super_options'])
        self.assertNotIn('ro', mounts[0]['super_options'])

    def test_ambiguous_mounts_and_nonblock_topology_refused(self):
        line = '41 30 8:1 / /data ro - ext4 /dev/sda1 ro\n'
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            mount_table(line+line.replace('41 ', '42 ', 1))
        with self.assertRaisesRegex(ValueError, 'non-block'):
            Kernel().block({'device':'0:35'})

    def test_absent_and_malformed_production_contexts_are_diagnostic_only(self):
        with patch('sv08_recovery_media.trusted_file', side_effect=FileNotFoundError('Recovery context is absent')):
            adapter = production_adapter()
            self.assertIsInstance(adapter, Unavailable)
            self.assertIn('absent', adapter.reason)
        with patch('sv08_recovery_media.trusted_file', return_value=b'{broken'):
            self.assertIsInstance(production_adapter(), Unavailable)
        cases = [(None, self.context), ([], self.context), (self.policy, None), (self.policy, [])]
        for field, values in {'format_version':[True, '1'], 'destinations':[[], 'usb', None, {'usb':None}, {'usb':dict(path=None,label='USB')}],
                              'source':[None, '/data/../data', 'data']}.items():
            for value in values:
                context = copy.deepcopy(self.context);context[field] = value
                cases.append((self.policy, context))
        for policy, context in cases:
            with self.subTest(policy=policy, context=context):
                with patch('sv08_recovery_media.MediaLease', side_effect=AssertionError('Malformed configuration reached admission')):
                    adapter = self.adapter(policy, context)
                self.assertIsInstance(adapter, Unavailable)
                self.assertFalse(adapter.capability('recovery.export', {})[0])
                self.assertEqual(adapter.destinations(), [])

    def test_fixture_policy_cannot_enable_production(self):
        policy = {**self.policy, 'kind':'disposable-recovery-fixture'}
        context = {**self.context, 'policy_sha256':fingerprint(policy)}
        adapter = self.adapter(policy, context)
        self.assertIsInstance(adapter, Unavailable)
        self.assertIn('independent recovery', adapter.reason)

    def test_ordinary_ab_or_workstation_root_with_marker_cannot_enable_export(self):
        # The old display-service marker says nothing about the actual root.
        # No host block node is opened by these ordinary-root negative tests.
        for filesystem in ('ext4', 'overlay'):
            text = ('1 1 8:1 / / rw - '+filesystem+' /dev/root rw\n'
                    '2 1 0:2 / /proc rw - proc proc rw\n'
                    '3 1 0:3 / /sys ro - sysfs sysfs ro\n')
            provider = MediaProvider(self.policy, self.context)
            with patch.object(provider.kernel, 'mounts', return_value=mount_table(text)), \
                 patch.object(provider.kernel, 'session', return_value={}), \
                 patch.object(provider.kernel, 'block', side_effect=AssertionError('Must not probe host media')):
                with self.assertRaisesRegex(ValueError, 'Recovery root requires consistent ro'):
                    provider.snapshot()

    def test_untrusted_or_symlinked_context_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'context.json';path.write_text('{}');path.chmod(0o644)
            original = os.fstat
            def root_owned(fd):
                # Isolate file validation from the workstation user and /tmp
                # ancestors; actual file modes and no-follow opens remain real.
                info = list(original(fd));info[4] = 0
                if stat.S_ISDIR(info[0]):info[0] = stat.S_IFDIR | 0o755
                return os.stat_result(info)
            with patch('sv08_recovery_media.os.geteuid', return_value=0), patch('sv08_recovery_media.os.fstat', root_owned):
                self.assertEqual(trusted_file(path), b'{}')
                path.chmod(0o666)
                with self.assertRaisesRegex(ValueError, 'Untrusted recovery configuration file'):
                    trusted_file(path)
                path.chmod(0o644)
                link = root / 'linked.json';link.symlink_to(path)
                with self.assertRaises(OSError):trusted_file(link)

    def test_readonly_ordinary_root_marker_cannot_replace_reviewed_image_or_boot_identity(self):
        from contextlib import contextmanager
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name in ('recovery', 'source', 'fat'):(base / name).mkdir()
            (base / 'recovery/etc/sv08').mkdir(parents=True)
            manifest = base / 'recovery/etc/sv08/recovery-image.json'
            manifest.write_text('{"reviewed_fixture_manifest":true}')
            # An apparent legacy marker is present even for the refused A/B root.
            (base / 'recovery/etc/sv08-recovery-image').write_text('present')
            policy_file = base / 'recovery/etc/sv08/recovery-media-policy.json'
            policy_file.write_text('{}')
            paths = {'/':base / 'recovery', '/data':base / 'source', '/media/usb':base / 'fat',
                     '/etc/sv08/recovery-image.json':manifest, str(POLICY):policy_file}
            devices = {'/':os.makedev(8, 1), '/data':os.makedev(8, 2), '/media/usb':os.makedev(8, 3),
                       '/etc/sv08/recovery-image.json':os.makedev(8, 1), str(POLICY):os.makedev(8, 1)}
            held = {}
            @contextmanager
            def fake_open(path, **kwargs):
                key = str(path)
                with opened(paths[key], **kwargs) as fd:
                    held[fd] = key
                    try:yield fd
                    finally:held.pop(fd)
            original = os.fstat
            def information(fd):
                info = original(fd)
                return SimpleNamespace(st_dev=devices[held[fd]], st_ino=info.st_ino,
                                       st_mode=info.st_mode, st_size=info.st_size)
            blocks = {}
            for index, path in enumerate(('/', '/data', '/media/usb'), start=1):
                blocks[path] = dict(stable={'wwid':'reviewed-'+str(index)}, partition=1, start=2048, sectors=131072,
                                    filesystem_uuid='fs-'+str(index), disk='/sys/devices/disk'+str(index),
                                    readonly=index != 3, disk_readonly=index != 3, removable=index == 3)
            policy = {**self.policy, 'image_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                      'recovery':durable_identity(blocks['/']), 'source':durable_identity(blocks['/data']),
                      'system_media':[blocks['/']['stable'], blocks['/data']['stable'], {'wwid':'unmounted-slot-medium'}]}
            context = {**self.context, 'policy_sha256':fingerprint(policy)}
            provider = MediaProvider(policy, context)
            mounts = mount_table('1 1 8:1 / / ro - ext4 /dev/recovery ro,norecovery\n'
                                 '2 1 0:2 / /proc rw - proc proc rw\n'
                                 '3 1 0:3 / /sys ro - sysfs sysfs ro\n'
                                 '4 1 8:2 / /data ro - ext4 /dev/data ro,norecovery\n'
                                 '5 1 8:3 / /media/usb rw - vfat /dev/usb rw\n')
            with patch.object(provider.kernel, 'mounts', return_value=mounts), \
                 patch.object(provider.kernel, 'session', return_value={'test':'measured-session-double'}), \
                 patch.object(provider.kernel, 'block', side_effect=lambda mount, fixture:copy.deepcopy(blocks[mount['path']])), \
                 patch('sv08_recovery_media.opened', fake_open), patch('sv08_recovery_media.os.fstat', information), \
                 patch('sv08_recovery_media.os.fstatvfs', side_effect=lambda fd:SimpleNamespace(f_flag=0 if held[fd] == '/media/usb' else os.ST_RDONLY)), \
                 patch('sv08_recovery_media.Path.read_text', return_value='sv08.recovery='+policy['image_manifest_sha256']) as cmdline:
                self.assertIn('recovery', provider.snapshot())  # Positive control.
                blocks['/media/usb']['stable'] = {'device/wwid':'unmounted-slot-medium', 'device/serial':'extra-attribute'}
                with self.assertRaisesRegex(ValueError, 'shares a system/source medium'):provider.snapshot()
                blocks['/media/usb']['stable'] = {'wwid':'reviewed-3'}
                blocks['/']['filesystem_uuid'] = 'ordinary-readonly-slot-A'
                with self.assertRaisesRegex(ValueError, 'independently reviewed identities'):provider.snapshot()
                blocks['/']['filesystem_uuid'] = 'fs-1'
                blocks['/']['stable'] = {'wwid':'ordinary-workstation-medium'}
                with self.assertRaisesRegex(ValueError, 'independently reviewed identities'):provider.snapshot()
                blocks['/']['stable'] = {'wwid':'reviewed-1'}
                cmdline.return_value = 'root=ordinary-slot-A'
                with self.assertRaisesRegex(ValueError, 'Kernel boot selection'):provider.snapshot()
                cmdline.return_value = 'sv08.recovery='+policy['image_manifest_sha256']+' sv08.recovery=other'
                with self.assertRaisesRegex(ValueError, 'Kernel boot selection'):provider.snapshot()

    def test_installed_controller_keeps_invalid_context_diagnostic_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'missing-registry'
            with patch('sv08_recovery_media.production_adapter', return_value=Unavailable('Untrusted recovery media context')), \
                 patch('sv08_state.Store', return_value=Store(root)):
                status = installed_controller().status()
            self.assertIn('damaged', status['diagnostic'])
            self.assertFalse(status['capabilities']['recovery.export']['available'])
            self.assertIn('Untrusted', status['capabilities']['recovery.export']['reason'])
            self.assertTrue(status['capabilities']['recovery.check']['available'])
            self.assertFalse(root.exists())
