import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_recovery_media import PROTOCOL, WRITER_MODEL, durable_identity
from sv08_recovery_prepare import RecoveryPreparer, find_identity, reviewed_inventory

IMAGE_SPEC = importlib.util.spec_from_file_location(
    'recovery_image_for_prepare_test', Path(__file__).resolve().parents[1] / 'scripts/recovery_image.py')
recovery_image = importlib.util.module_from_spec(IMAGE_SPEC); IMAGE_SPEC.loader.exec_module(recovery_image)


class FakeLease:
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def check(self): pass


class FakeKernel:
    def __init__(self, inventory):
        self.value = inventory
        self.events = []

    def inventory(self):
        self.events.append('inventory')
        return copy.deepcopy(self.value)

    def mounts(self):
        root = self.value[0]
        self.events.append('mounts')
        return [dict(path='/', device=root['device'])]

    def set_readonly(self, identity, observer):
        self.events.append(('setro', identity['device']))
        observer('source-whole-ro', device=identity['disk_device'], readonly=True)
        observer('source-partition-ro', device=identity['device'], readonly=True)

    def mount(self, identity, path, options, filesystem):
        self.events.append(('mount', identity['device'], str(path), options, filesystem))

    def unmount(self, path):
        self.events.append(('unmount', str(path)))


def medium(name, stable, device, *, filesystem, uuid, partition=0, removable=False,
           disk_device=None):
    value = dict(node='/dev/'+name, device=device, sysfs='/sys/devices/'+name,
                 sysfs_inode=100+len(name), disk='/sys/devices/'+name.rstrip('1'),
                 disk_device=disk_device or device,
                 diskseq=10+len(name), partition=partition, start=2048 if partition else 0,
                 sectors=131072, readonly=False, disk_readonly=False, removable=removable,
                 filesystem_uuid=uuid, filesystem=filesystem, partuuid='part-'+uuid)
    return value


class RecoveryPrepareTests(unittest.TestCase):
    def setUp(self):
        recovery = medium('vda', {'serial':'recovery'}, '254:0', filesystem='ext4', uuid='root')
        source = medium('sda1', {'device/wwid':'source'}, '8:1', filesystem='ext4', uuid='source',
                        partition=1, disk_device='8:0')
        destination = medium('sdb1', {'device/serial':'usb'}, '8:17', filesystem='vfat', uuid='fat',
                             partition=1, removable=True, disk_device='8:16')
        self.inventory = [
            dict(name='vda', device='254:0', sysfs='/sys/devices/vda', sysfs_inode=1,
                 diskseq=1, disk='/sys/devices/vda', disk_device='254:0',
                 stable={'serial':'recovery'}, sectors=recovery['sectors'], readonly=True,
                 removable=False, transport='virtio', filesystem_uuid='root', filesystem='ext4', partitions=[]),
            dict(name='sda', device='8:0', sysfs='/sys/devices/sda', sysfs_inode=2,
                 diskseq=2, disk='/sys/devices/sda', disk_device='8:0',
                 stable={'device/wwid':'source'}, sectors=262144, readonly=False,
                 removable=False, transport='scsi', filesystem_uuid='', filesystem='', partitions=[source]),
            dict(name='sdb', device='8:16', sysfs='/sys/devices/sdb', sysfs_inode=3,
                 diskseq=3, disk='/sys/devices/sdb', disk_device='8:16',
                 stable={'device/serial':'usb'}, sectors=262144, readonly=False,
                 removable=True, transport='usb-scsi', filesystem_uuid='', filesystem='', partitions=[destination]),
        ]
        self.policy = dict(format_version=2, kind='independent-recovery', protocol=PROTOCOL,
                           writer_model=WRITER_MODEL, envelope_manifest_sha256='2'*64,
                           media=reviewed_inventory(self.inventory),
                           recovery=dict(stable={'serial':'recovery'}, partition=0, start=0,
                                         sectors=131072, filesystem_uuid='root'),
                           source=dict(stable={'device/wwid':'source'}, partition=1, start=2048,
                                       sectors=131072, filesystem_uuid='source'),
                           protected=[],
                           source_path='/run/sv08-recovery/source',
                           destinations={'usb':dict(
                               identity=dict(stable={'device/serial':'usb'}, partition=1, start=2048,
                                             sectors=131072, filesystem_uuid='fat'),
                               path='/run/sv08-recovery/destinations/usb', label='Reviewed USB')})

    def run_preparer(self, policy=None, kernel=None):
        policy = policy or self.policy
        kernel = kernel or FakeKernel(self.inventory)
        with tempfile.TemporaryDirectory() as directory:
            context = Path(directory) / 'run/media-context.json'
            context.parent.mkdir(mode=0o700)
            preparer = RecoveryPreparer(policy, kernel=kernel, context=context)
            expected = {'verified':'snapshot'}
            original_stat = Path.stat
            def trusted_runtime(path, *args, **kwargs):
                value = original_stat(path, *args, **kwargs)
                if path == context.parent:
                    return SimpleNamespace(st_uid=0, st_mode=value.st_mode)
                return value
            with patch('sv08_recovery_prepare.MediaLease', FakeLease), \
                 patch.object(preparer, 'authenticate'), \
                 patch('sv08_recovery_prepare.MediaProvider') as provider, \
                 patch('sv08_recovery_prepare.Path.stat', trusted_runtime):
                provider.return_value.snapshot.return_value = expected
                result = preparer.prepare()
            self.assertEqual(json.loads(context.read_text()), result)
            self.assertEqual(result['expected'], expected)
            return kernel, result

    def test_complete_reviewed_topology_prepares_in_safe_order_then_publishes(self):
        observed_events = []
        with patch('sv08_recovery_prepare.emit',
                   side_effect=lambda event, **fields: observed_events.append((event, fields))):
            kernel, result = self.run_preparer()
        self.assertEqual(kernel.events[0:2], ['inventory', 'mounts'])
        self.assertEqual(kernel.events[2], ('setro', '8:1'))
        self.assertEqual(kernel.events[3][1:], ('8:1', '/run/sv08-recovery/source',
                                               'ro,noload,nosuid,nodev,noexec', 'ext4'))
        self.assertEqual(kernel.events[4][1:], ('8:17', '/run/sv08-recovery/destinations/usb',
                                               'rw,nosuid,nodev,noexec,umask=0077', 'vfat'))
        self.assertEqual([event for event, _ in observed_events],
                         ['source-whole-ro', 'source-partition-ro',
                          'source-mount-begin', 'source-mount-complete'])
        self.assertEqual(observed_events[2][1]['options'], 'ro,noload,nosuid,nodev,noexec')
        self.assertEqual(result['format_version'], 2)

    def test_omission_replacement_and_duplicate_stable_identity_refuse(self):
        for change, phrase in (
                (lambda value: value['media'].pop(), 'topology'),
                (lambda value: value['media'][1]['partitions'][0].update(filesystem_uuid='replacement'), 'topology'),
                (lambda value: value['media'][2].update(stable={'device/wwid':'source'}), 'topology')):
            policy = copy.deepcopy(self.policy); change(policy)
            with self.subTest(policy=policy):
                with self.assertRaisesRegex(ValueError, phrase):
                    self.run_preparer(policy)

    def test_manifest_authentication_precedes_inventory_and_failure_never_publishes(self):
        kernel = FakeKernel(self.inventory)
        with tempfile.TemporaryDirectory() as directory:
            context = Path(directory) / 'run/media-context.json'; context.parent.mkdir(mode=0o700)
            preparer = RecoveryPreparer(self.policy, kernel=kernel, context=context)
            with patch('sv08_recovery_prepare.MediaLease', FakeLease), \
                 patch.object(preparer, 'authenticate', side_effect=ValueError('manifest changed')):
                with self.assertRaisesRegex(ValueError, 'manifest changed'): preparer.prepare()
            self.assertEqual(kernel.events, [])
            self.assertFalse(context.exists())

    def test_authentication_requires_both_manifest_hashes_and_boot_bindings(self):
        envelope = b'envelope\n'
        policy = copy.deepcopy(self.policy)
        policy['envelope_manifest_sha256'] = hashlib.sha256(envelope).hexdigest()
        policy_digest = hashlib.sha256(
            (json.dumps(policy, sort_keys=True, separators=(',', ':'))+'\n').encode()).hexdigest()
        provider_value = recovery_image.compose_provider_manifest(policy_digest, {'runtime':'digest'})
        provider = (json.dumps(provider_value, sort_keys=True, separators=(',', ':'))+'\n').encode()
        preparer = RecoveryPreparer(policy, kernel=FakeKernel(self.inventory))
        provider_digest = hashlib.sha256(provider).hexdigest()
        cmdline = ('sv08.recovery='+provider_digest+' '
                   'sv08.envelope='+policy['envelope_manifest_sha256'])
        with patch('sv08_recovery_prepare.trusted_file', side_effect=[provider, envelope]), \
             patch('sv08_recovery_prepare.os.stat', return_value=SimpleNamespace(st_dev=7)), \
             patch('sv08_recovery_prepare.Path.read_text', return_value=cmdline):
            preparer.authenticate()
        with patch('sv08_recovery_prepare.trusted_file', side_effect=[provider, envelope]), \
             patch('sv08_recovery_prepare.os.stat', return_value=SimpleNamespace(st_dev=7)), \
             patch('sv08_recovery_prepare.Path.read_text', return_value='sv08.envelope='+policy['envelope_manifest_sha256']):
            with self.assertRaisesRegex(ValueError, 'boot selection'): preparer.authenticate()
        changed = copy.deepcopy(policy); changed['source']['filesystem_uuid'] = 'tampered'
        changed_preparer = RecoveryPreparer(changed, kernel=FakeKernel(self.inventory))
        with patch('sv08_recovery_prepare.trusted_file', side_effect=[provider, envelope]), \
             patch('sv08_recovery_prepare.os.stat', return_value=SimpleNamespace(st_dev=7)), \
             patch('sv08_recovery_prepare.Path.read_text', return_value=cmdline):
            with self.assertRaisesRegex(ValueError, 'does not bind'):
                changed_preparer.authenticate()

    def test_partial_mount_failure_is_cleaned_and_context_remains_absent(self):
        kernel = FakeKernel(self.inventory)
        original = kernel.mount
        def fail(identity, path, options, filesystem):
            if filesystem == 'vfat': raise OSError('destination failure')
            original(identity, path, options, filesystem)
        kernel.mount = fail
        with tempfile.TemporaryDirectory() as directory:
            context = Path(directory) / 'run/media-context.json'; context.parent.mkdir(mode=0o700)
            preparer = RecoveryPreparer(self.policy, kernel=kernel, context=context)
            with patch('sv08_recovery_prepare.MediaLease', FakeLease), patch.object(preparer, 'authenticate'):
                with self.assertRaisesRegex(OSError, 'destination failure'): preparer.prepare()
            self.assertIn(('unmount', '/run/sv08-recovery/source'), kernel.events)
            self.assertFalse(context.exists())

    def test_destination_partition_cannot_share_a_protected_whole_disk(self):
        observed = copy.deepcopy(self.inventory)
        protected = medium('sdb2', {'device/serial':'usb'}, '8:18', filesystem='ext4',
                           uuid='protected', partition=2, removable=True, disk_device='8:16')
        protected['start'] = 133120
        observed[2]['partitions'].append(protected)
        policy = copy.deepcopy(self.policy)
        policy['media'] = reviewed_inventory(observed)
        policy['protected'] = [dict(role='additional-protected', identity=dict(
            stable={'device/serial':'usb'}, partition=2, start=133120,
            sectors=131072, filesystem_uuid='protected'))]
        kernel = FakeKernel(observed)
        preparer = RecoveryPreparer(policy, kernel=kernel)
        with patch('sv08_recovery_prepare.MediaLease', FakeLease), patch.object(preparer, 'authenticate'):
            with self.assertRaisesRegex(ValueError, 'whole disk aliases protected'):
                preparer.prepare()
        self.assertEqual(kernel.events, ['inventory'])

    def test_context_observations_do_not_select_or_authorize_media(self):
        observed = copy.deepcopy(self.inventory)
        identity = find_identity(observed, self.policy['source'])
        self.assertEqual(identity['device'], '8:1')
        observed[1]['partitions'][0]['diskseq'] += 1
        self.assertEqual(find_identity(observed, self.policy['source'])['device'], '8:1')
        changed = copy.deepcopy(self.policy['source']); changed['filesystem_uuid'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'): find_identity(observed, changed)

    def test_builder_binds_reviewed_profile_to_final_manifests(self):
        profile = {name:copy.deepcopy(self.policy[name]) for name in
                   ('recovery', 'source', 'source_path', 'media', 'protected', 'destinations')}
        result = recovery_image.compose_media_policy(profile, '2'*64)
        self.assertEqual(result['envelope_manifest_sha256'], '2'*64)
        self.assertNotIn('expected', result)
        policy_digest = hashlib.sha256(
            (json.dumps(result, sort_keys=True, separators=(',', ':'))+'\n').encode()).hexdigest()
        provider = recovery_image.compose_provider_manifest(policy_digest, {'runtime':'hash'})
        self.assertEqual(provider['policy_sha256'], policy_digest)
        with self.assertRaisesRegex(ValueError, 'schema'):
            recovery_image.compose_media_policy({**profile, 'expected':{}}, '2'*64)


if __name__ == '__main__': unittest.main()
