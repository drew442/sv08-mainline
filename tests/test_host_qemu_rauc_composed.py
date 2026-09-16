import json
from pathlib import Path
import tempfile
import unittest

from host_qemu_rauc_composed import LAYOUT, ROLES, fixture_manifest, partition_layout, sgdisk_arguments


class ComposedRaucFixtureLayoutTests(unittest.TestCase):
    def setUp(self):
        self.parts = partition_layout()
        self.uuids = {name: f'00000000-0000-4000-8000-{index:012d}'
                      for index, name in enumerate(ROLES, 1)}

    def test_extents_are_complete_and_reservations_remain_outside_partitions(self):
        self.assertEqual(self.parts[0]['offset_bytes'], 16 * 1024 * 1024)
        self.assertEqual(self.parts[-1]['end_bytes'] + 1024 * 1024, LAYOUT['image_bytes'])
        self.assertEqual([part['name'] for part in self.parts], list(ROLES))
        self.assertTrue(all(left['end_bytes'] == right['offset_bytes']
                            for left, right in zip(self.parts, self.parts[1:])))

    def test_manifest_has_exact_nondeployable_partuuid_devices(self):
        manifest = fixture_manifest(self.uuids)
        self.assertFalse(manifest['deployable'])
        self.assertEqual(set(manifest['devices']), set(ROLES))
        self.assertEqual(len(set(manifest['devices'].values())), 6)
        self.assertEqual(json.loads(json.dumps(manifest)), manifest)

    def test_sgdisk_requires_a_new_non_device_target(self):
        with tempfile.TemporaryDirectory() as directory:
            command = sgdisk_arguments(Path(directory) / 'guest.img', self.parts, self.uuids)
        self.assertEqual(command[0:2], ['sgdisk', '--clear'])
        self.assertIn('--partition-guid=6:00000000-0000-4000-8000-000000000006', command)
        with self.assertRaisesRegex(ValueError, 'new regular'):
            sgdisk_arguments('/dev/vda', self.parts, self.uuids)
