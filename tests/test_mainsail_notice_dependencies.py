# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline application of every pinned patch and exact dependency delta checks."""
import base64
import io
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import tarfile
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import resolve_npm_notices as notices

REPO = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MainsailNoticeDependencies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='mainsail-notice-patches-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.source = Path(cls.temporary.name)
        cls.config = json.loads((REPO/'configs/apps/mainsail.json').read_text())
        upstream = REPO/cls.config['source_path']
        actual = subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()
        if actual != cls.config['source_commit']:
            raise AssertionError('Prepared upstream source must match the pinned revision')
        for name in ('package.json','package-lock.json','vite.config.ts','src/main.ts','src/components/webcams/streamers/JanusStreamer.vue'):
            (cls.source/name).parent.mkdir(parents=True,exist_ok=True)
            (cls.source/name).write_bytes(subprocess.check_output(['git','-C',str(upstream),'show',actual+':'+name]))
        if sha(cls.source/'package-lock.json') != cls.config['package_lock_sha256']:
            raise AssertionError('Original source lock differs from its pin')
        for index, patch in enumerate(cls.config['source_patches']):
            candidate = REPO/patch['path']
            if sha(candidate) != patch['sha256']:
                raise AssertionError('Source patch pin mismatch')
            if index == 4:
                cls.janus_before_manifest = json.loads((cls.source/'package.json').read_text())
                cls.janus_before_lock = json.loads((cls.source/'package-lock.json').read_text())
            if index == 3:
                cls.vitest_before_manifest = json.loads((cls.source/'package.json').read_text())
                cls.vitest_before_lock = json.loads((cls.source/'package-lock.json').read_text())
            if index == 2:
                cls.before_manifest = json.loads((cls.source/'package.json').read_text())
                cls.before_lock = json.loads((cls.source/'package-lock.json').read_text())
            for mode in (['--dry-run'], []):
                subprocess.run(['patch','--batch','--forward','--fuzz=0',*mode,'-d',str(cls.source),'-p1','-i',str(candidate)],
                               check=True,stdout=subprocess.DEVNULL)
        cls.manifest = json.loads((cls.source/'package.json').read_text())
        cls.lock = json.loads((cls.source/'package-lock.json').read_text())

    def test_exact_patches_and_final_lock_pin(self):
        self.assertEqual(sha(self.source/'package-lock.json'),self.config['patched_package_lock_sha256'])
        self.assertEqual(self.config['package_version'],'2.19.0+git32f99e1c-8')
        self.assertEqual(len(self.config['source_patches']),6)
        self.assertEqual(self.lock['packages']['node_modules/js-yaml']['version'],'4.3.2')
        self.assertEqual(self.lock['packages']['node_modules/nanoid']['version'],'3.3.18')
        self.assertIn('manifestTransforms',(self.source/'vite.config.ts').read_text())

    def test_only_settled_manifest_edges_change(self):
        before = json.loads(json.dumps(self.before_manifest))
        before['devDependencies'].pop('vue-template-compiler')
        before['overrides']['request-progress'] = {'throttleit':'2.1.0'}
        self.assertEqual(self.vitest_before_manifest,before)
        before['devDependencies']['vitest'] = '5.0.4'
        before['devDependencies']['@types/node'] = '^22.0.0'
        self.assertEqual(self.janus_before_manifest,before)
        self.assertNotIn('vue-template-compiler',self.lock['packages']['']['devDependencies'])

    def test_only_expected_supplier_lock_records_change(self):
        before = self.before_lock['packages']; after = self.vitest_before_lock['packages']
        self.assertEqual(set(before)-set(after),{'node_modules/vue-template-compiler','node_modules/de-indent','node_modules/he'})
        self.assertEqual(set(after)-set(before),set())
        self.assertEqual({p for p in set(before)&set(after) if before[p]!=after[p]}, {'','node_modules/throttleit'})
        # Preserve actual supplier metadata, including the parent's original range;
        # npm's scoped override is the documented mechanism selecting 2.1.0.
        self.assertEqual(after['node_modules/request-progress'],before['node_modules/request-progress'])
        self.assertEqual(after['node_modules/request-progress']['dependencies']['throttleit'],'^1.0.0')
        self.assertEqual(after['node_modules/throttleit']['version'],'2.1.0')
        self.assertEqual(after['node_modules/throttleit']['integrity'],
            'sha512-nt6AMGKW1p/70DF/hGBdJB57B8Tspmbp5gfJ8ilhLnt7kkr2ye7hzD6NVG8GGErk2HWF34igrL2CXmNIkzKqKw==')
        self.assertEqual(after['node_modules/throttleit']['engines'],{'node':'>=18'})
        for package in after.values():
            self.assertNotIn('vue-template-compiler',package.get('dependencies',{}))
            self.assertNotIn('de-indent',package.get('dependencies',{}))

    def test_exact_upstream_vitest_family_delta(self):
        before = self.vitest_before_lock['packages']; after = self.janus_before_lock['packages']
        removed = {'@vitest/expect', '@vitest/pretty-format', '@vitest/runner',
                   '@vitest/snapshot', '@vitest/snapshot/node_modules/magic-string',
                   '@vitest/utils', 'pathe', 'siginfo', 'stackback', 'tinyrainbow'}
        # Vitest 5 bundles several former family packages into its distribution.
        self.assertEqual(set(before)-set(after), {'node_modules/'+p for p in removed})
        self.assertEqual(set(after)-set(before), set())
        versions = {
            '@jridgewell/sourcemap-codec':'1.6.0', '@types/node':'22.20.5',
            '@vitest/mocker':'5.0.4', '@vitest/spy':'5.0.4',
            '@vitest/mocker/node_modules/magic-string':'1.4.3',
            'chai':'6.3.0', 'es-module-lexer':'2.3.2', 'obug':'3.0.0',
            'std-env':'4.3.0', 'tinybench':'6.2.2', 'tinyexec':'1.3.1',
            'vitest':'5.0.4', 'vitest/node_modules/magic-string':'1.4.3',
            'vitest/node_modules/picomatch':'4.0.7', 'why-is-node-running':'3.2.1',
        }
        self.assertEqual({p for p in before.keys() & after.keys() if before[p] != after[p]},
                         {''} | {'node_modules/'+p for p in versions})
        for name, version in versions.items():
            record = after['node_modules/'+name]
            self.assertEqual(record['version'],version)
            self.assertEqual(record['resolved'],f'https://registry.npmjs.org/{name.split("node_modules/")[-1]}/-/{name.split("/")[-1]}-{version}.tgz')
            self.assertTrue(record['integrity'].startswith('sha512-'))
        vitest = after['node_modules/vitest']
        self.assertEqual(vitest['integrity'], 'sha512-z0WxZRV2Sg48wF0FSgMq3TFG8JS38/Qr96vZVZdX6+Em9raQTvnXQvdTFJe2m3rfyJnEHeHQ/snceIdi8D1pVg==')
        self.assertEqual(vitest['dependencies']['why-is-node-running'],'3.2.1')
        self.assertEqual(vitest['peerDependencies']['vite'],'^6.4.0 || ^7.0.0 || ^8.0.0')
        why = after['node_modules/why-is-node-running']
        self.assertEqual(why['integrity'], 'sha512-Tb2FUhB4vUsGQlfSquQLYkApkuPAFQXGFzxWKHHumVz2dK+X1RUm/HnID4+TfIGYJ1kTcwOaCk/buYCEJr6YjQ==')
        self.assertEqual(why.get('dependencies',{}),{})
        for record in after.values():
            self.assertNotIn('stackback',record.get('dependencies',{}))
        root = json.loads(json.dumps(before['']))
        root['devDependencies'].update({'vitest':'5.0.4','@types/node':'^22.0.0'})
        self.assertEqual(after[''],root)

    def test_historical_accounting_keeps_removed_and_replaced_license_facts(self):
        with tempfile.TemporaryDirectory(prefix='notice-accounting-') as temporary:
            fixture=Path(temporary);(fixture/'configs/apps').mkdir(parents=True)
            (fixture/'configs/host').mkdir(parents=True)
            archive=fixture/'replacement.tgz'
            with tarfile.open(archive,'w:gz') as tar:
                for name,raw in [('package/package.json',b'{"name":"throttleit","version":"2.1.0"}'),
                                 ('package/license',b'Author notice text retained exactly in disposable fixture')]:
                    member=tarfile.TarInfo(name);member.size=len(raw);tar.addfile(member,io.BytesIO(raw))
            selected=json.loads(json.dumps(self.vitest_before_lock))
            selected['packages']['node_modules/throttleit']['integrity']='sha512-'+base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
            lock=fixture/'package-lock.json';lock.write_text(json.dumps(selected))
            config=json.loads(json.dumps(self.config));config['patched_package_lock_sha256']=sha(lock)
            (fixture/'configs/apps/mainsail.json').write_text(json.dumps(config))
            for name in ('source-license-inventory.json','npm-supplemental-notices.json'):
                (fixture/'configs/host'/name).write_bytes((REPO/'configs/host'/name).read_bytes())
            def pin(path):return dict(root=str(path.parent),path=path.name,sha256=sha(path))
            inputs=dict(selected_lock=pin(lock),supplemental_notices=pin(fixture/'configs/host/npm-supplemental-notices.json'),
                        replacement_archives={'node_modules/throttleit':pin(archive)})
            with patch.object(notices,'REPO',fixture):
                report=notices.selection_resolution(inputs)
                self.assertEqual(report['coverage'],dict(historical_records=69,historical_notice_resolved=60,
                    historical_notice_unresolved=9,selected_dependencies=931,measured_selection_remediations=2,
                    remaining_selected_notice_gaps=7))
                records={r['path']:r for r in report['records']}
                for name in ('throttleit','de-indent'):
                    self.assertEqual(records['node_modules/'+name]['historical_notice_status'],'unresolved-author-notice')
                replacement=records['node_modules/throttleit']
                self.assertEqual(replacement['selection_status'],'replaced-by-notice-bearing-supplier-release')
                self.assertIn('Author notice text retained exactly',replacement['replacement_notices'][0]['text'])
                self.assertEqual(records['node_modules/de-indent']['selection_status'],'removed-from-selected-lock')
                self.assertFalse(report['overall_release_qualified'])
                inputs['replacement_archives']={}
                incomplete=notices.selection_resolution(inputs)
                self.assertEqual(incomplete['coverage']['remaining_selected_notice_gaps'],8)
                lock.write_text('{}')
                with self.assertRaisesRegex(ValueError,'hash mismatch'):notices.selection_resolution(inputs)

    def test_root_compiler_declaration_has_no_source_callsite(self):
        source = REPO/self.config['source_path']
        result = subprocess.run(['git','-C',str(source),'grep','-n','vue-template-compiler','--',
                                 '*.ts','*.js','*.vue','*.cjs','*.mjs'],capture_output=True,text=True)
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        self.assertIn('@pedrolamas/plugin-vue2',(source/'vite.config.ts').read_text())


if __name__ == '__main__':
    unittest.main()
