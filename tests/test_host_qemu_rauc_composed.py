import json
from pathlib import Path
import tempfile
import unittest

from host_qemu_rauc_composed import LAYOUT, ROLES, create_media, filesystem_types, fixture_manifest, format_media, partition_layout, sgdisk_arguments


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

    def test_sparse_disposable_gpt_readback_matches_every_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'guest.img'
            result = create_media(image, self.uuids)
            self.assertEqual(result['image_bytes'], LAYOUT['image_bytes'])
            self.assertEqual([row[1] for row in result['partitions']], list(ROLES))
            self.assertEqual([row[4] for row in result['partitions']],
                             [self.uuids[name] for name in ROLES])

    def test_formatting_is_bounded_to_the_reviewed_partitions(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'guest.img'
            create_media(image, self.uuids)
            formatted = format_media(image)
            self.assertEqual(set(formatted), set(ROLES))
            self.assertEqual(formatted['root-a']['size_bytes'], 2048 * 1024 * 1024)
            self.assertEqual(filesystem_types(image), dict(zip(ROLES, ('vfat', 'ext4', 'vfat', 'ext4', 'ext4', 'ext4'))))
