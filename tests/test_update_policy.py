import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_update_policy import DEFAULTS, admit, check_source, effective
from sv08_bundle import validate
import test_bundle_policy


class UpdatePolicyTests(unittest.TestCase):
    def setUp(self):
        self.state = dict(requested_mode='immutable', slots={'A': dict(release='z-last', release_revision=10, customized=False)})
        self.boot = dict(slot='A', release='z-last', mode='immutable')
        self.proof = dict(release='a-new', release_revision=11, signer_trusted=True)

    def test_strict_named_booleans(self):
        self.assertEqual(effective(), DEFAULTS)
        for key in DEFAULTS:
            for value in (1, 0, 'false', None, [], {}):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError): effective({key: value})
        with self.assertRaises(ValueError): effective({'bypass': True})
        with self.assertRaises(ValueError): effective({'allow_untrusted_provenance': True}, automatic=True)

    def test_signed_numeric_order_only_and_individual_downgrade(self):
        self.assertEqual(admit(self.proof, self.state, self.boot), DEFAULTS)
        for revision in (9, 10, None, True, '11', 0):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                admit(dict(self.proof, release_revision=revision), self.state, self.boot)
        admit(dict(self.proof, release_revision=9), self.state, self.boot, {'allow_downgrade': True})
        del self.state['slots']['A']['release_revision']
        with self.assertRaisesRegex(ValueError, 'unknown'): admit(self.proof, self.state, self.boot)
        admit(dict(self.proof, release_revision=None), self.state, self.boot, {'check_version': False})

    def test_customization_exception_keeps_mode_and_source_checks(self):
        self.state['slots']['A']['customized'] = True
        with self.assertRaisesRegex(ValueError, 'Customized'): check_source(self.state, self.boot)
        check_source(self.state, self.boot, {'check_customization': False})
        self.assertTrue(self.state['slots']['A']['customized'])
        with self.assertRaises(ValueError): check_source(self.state, dict(self.boot, mode='writable'), {'check_customization': False})
        with self.assertRaises(ValueError): check_source(self.state, dict(self.boot, release='other'), {'check_customization': False})

    def test_automatic_never_accepts_manual_provenance(self):
        unknown = dict(self.proof, signer_trusted=False)
        with self.assertRaises(ValueError): admit(unknown, self.state, self.boot)
        admit(unknown, self.state, self.boot, {'allow_untrusted_provenance': True})
        for options in ({}, {'check_version': False}, {'allow_untrusted_provenance': True}):
            with self.subTest(options=options), self.assertRaises(ValueError): admit(unknown, self.state, self.boot, options, automatic=True)

    def test_compatibility_only_exception_and_immutable_manifest_fields(self):
        fixture = test_bundle_policy.BundlePolicyTests(); fixture.setUp()
        fixture.info['update']['compatible'] = 'other'
        options = {'check_compatibility': False}
        self.assertEqual(validate(fixture.info, fixture.policy, 500, options)['compatible'], 'other')
        fixture.info['meta']['sv08']['release-revision'] = '11'
        self.assertEqual(validate(fixture.info, fixture.policy, 500, options)['release_revision'], 11)
        for field, value in [('layout', 'other'), ('state-schema', '2'), ('klipper-commit', 'b'*40), ('release-revision', '0'), ('extra', 'x')]:
            info = copy.deepcopy(fixture.info); info['meta']['sv08'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): validate(info, fixture.policy, 500, options)

    def test_installed_revision_is_explicit_and_exact_image_only(self):
        import json
        import tempfile
        from sv08_state import installed_release_revision
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'release.json'
            self.assertIsNone(installed_release_revision('r', 1, path))
            path.write_text(json.dumps(dict(release='r', state_schema=1, release_revision=8)))
            self.assertEqual(installed_release_revision('r', 1, path), 8)
            self.assertIsNone(installed_release_revision('other', 1, path))
            self.assertIsNone(installed_release_revision('r', 2, path))
            path.write_text(json.dumps(dict(release='r', state_schema=1, release_revision=True)))
            with self.assertRaises(ValueError): installed_release_revision('r', 1, path)
            link = path.with_name('link'); link.symlink_to(path)
            with self.assertRaises(ValueError): installed_release_revision('r', 1, link)
