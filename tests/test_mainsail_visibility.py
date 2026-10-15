# SPDX-License-Identifier: AGPL-3.0-or-later
"""Independent directive provenance, exact selection delta and consumer preservation."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class MainsailVisibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='mainsail-visibility-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.source = Path(cls.temporary.name)
        cls.config = json.loads((REPO/'configs/apps/mainsail.json').read_text())
        archive = subprocess.check_output(['git','-C',str(REPO/cls.config['source_path']),
                                           'archive',cls.config['source_commit']])
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(cls.source,filter='data')
        cls.consumers = {str(p.relative_to(cls.source)):p.read_bytes()
                         for p in (cls.source/'src').rglob('*.vue') if b'v-observe-visibility' in p.read_bytes()}
        cls.original_license = (cls.source/'LICENSE').read_bytes()
        for index, patch in enumerate(cls.config['source_patches']):
            raw = (REPO/patch['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != patch['sha256']:
                raise AssertionError('patch pin mismatch')
            if index == 6:
                cls.after_visibility_manifest = json.loads((cls.source/'package.json').read_text())
                cls.after_visibility_lock = json.loads((cls.source/'package-lock.json').read_text())
            if index == 5:
                cls.before_manifest = json.loads((cls.source/'package.json').read_text())
                cls.before_lock = json.loads((cls.source/'package-lock.json').read_text())
            subprocess.run(['patch','--batch','--fuzz=0','-p1','-d',str(cls.source),'-i',str(REPO/patch['path'])],
                           check=True,stdout=subprocess.DEVNULL)

    def test_exact_dependency_removal_and_all_surviving_supplier_records(self):
        expected = json.loads(json.dumps(self.before_manifest))
        expected['dependencies'].pop('vue-observe-visibility')
        self.assertEqual(self.after_visibility_manifest,expected)
        after = self.after_visibility_lock
        before = self.before_lock
        self.assertEqual({k:v for k,v in before.items() if k!='packages'},
                         {k:v for k,v in after.items() if k!='packages'})
        old, new = before['packages'], after['packages']
        self.assertEqual(old.keys()-new.keys(),{'node_modules/vue-observe-visibility'})
        self.assertEqual(new.keys()-old.keys(),set())
        self.assertEqual({key for key in old.keys() & new.keys() if old[key]!=new[key]},{''})
        root = json.loads(json.dumps(old['']))
        root['dependencies'].pop('vue-observe-visibility')
        self.assertEqual(new[''],root)
        for record in new.values():
            self.assertNotIn('vue-observe-visibility',record.get('dependencies',{}))

    def test_every_actual_consumer_is_unchanged(self):
        self.assertEqual(len(self.consumers),9)
        for name, raw in self.consumers.items():
            with self.subTest(consumer=name):
                self.assertEqual((self.source/name).read_bytes(),raw)
        registrations=(self.source/'src/main.ts').read_text()
        self.assertIn("import { ObserveVisibility } from '@/plugins/observeVisibility'",registrations)
        self.assertIn("Vue.directive('observe-visibility', ObserveVisibility)",registrations)
        self.assertNotIn("from 'vue-observe-visibility'",registrations)

    def test_license_and_pinned_build_inputs(self):
        self.assertEqual((self.source/'LICENSE').read_bytes(),self.original_license)
        self.assertEqual((self.source/'public/licenses/sv08-janus-adapter-AGPL-3.0.txt').read_bytes(),
                         (REPO/'LICENSE').read_bytes())
        for name in ('src/plugins/observeVisibility.ts','tests/observeVisibility.spec.ts'):
            self.assertTrue((self.source/name).read_text().startswith('// SPDX-License-Identifier: AGPL-3.0-or-later'))
        self.assertEqual(self.config['source_commit'],'32f99e1cf97640b23a52829dfa3a0aceee11d382')
        self.assertEqual(self.config['node_version'],'22.23.2')
        self.assertEqual(self.config['package_version'],'2.19.0+git32f99e1c-9')
        self.assertEqual(len(self.config['source_patches']),7)
        self.assertEqual(hashlib.sha256((self.source/'package-lock.json').read_bytes()).hexdigest(),
                         self.config['patched_package_lock_sha256'])


if __name__ == '__main__': unittest.main()
