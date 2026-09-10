import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_bundle import validate


class BundlePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = dict(compatible='test-only', layout='ab-8gb-v1', state_schema=1,
                           klipper_commit='a'*40, max_bundle_bytes=1024,
                           image_bytes={'boot': 192, 'rootfs': 2048})
        self.info = dict(update={'compatible': 'test-only', 'version': 'release-2'},
            bundle={'format': 'verity'}, meta={'sv08': {'layout': 'ab-8gb-v1',
            'state-schema': '1', 'klipper-commit': 'a'*40}},
            images=[{'slot-class': kind, 'size': size, 'checksum': 'b'*64}
                    for kind, size in self.policy['image_bytes'].items()])

    def test_exact_paired_release(self):
        self.assertEqual(validate(self.info, self.policy, 500)['release'], 'release-2')

    def test_missing_or_incompatible_signed_metadata(self):
        for key in ('layout', 'state-schema', 'klipper-commit'):
            for replacement in (None, 'different'):
                info = copy.deepcopy(self.info)
                if replacement is None:
                    del info['meta']['sv08'][key]
                else:
                    info['meta']['sv08'][key] = replacement
                with self.subTest(key=key, value=replacement), self.assertRaises(ValueError):
                    validate(info, self.policy, 500)

    def test_rejects_layout_shape_hook_variant_and_budget(self):
        cases = []
        for key, value in [('size', 191), ('checksum', 'bad'), ('variant', 'other'),
                           ('hooks', ['install']), ('adaptive', ['block-hash-index']),
                           ('artifact', 'unexpected'), ('type', 'tar')]:
            info = copy.deepcopy(self.info); info['images'][0][key] = value; cases.append(info)
        info = copy.deepcopy(self.info); info['images'].append(info['images'][0]); cases.append(info)
        info = copy.deepcopy(self.info); info['hooks'] = ['install-check']; cases.append(info)
        info = copy.deepcopy(self.info); info['handler'] = {'filename': 'custom'}; cases.append(info)
        info = copy.deepcopy(self.info); info['bundle']['format'] = 'plain'; cases.append(info)
        info = copy.deepcopy(self.info); info['update']['compatible'] = 'other'; cases.append(info)
        for info in cases:
            with self.subTest(info=info), self.assertRaises(ValueError):
                validate(info, self.policy, 500)
        for size in (0, 1025, True):
            with self.subTest(size=size), self.assertRaises(ValueError):
                validate(self.info, self.policy, size)
