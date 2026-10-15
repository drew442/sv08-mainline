# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import resolve_npm_notices as m
import license_inventory

class SupplementalTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name);self.revision='a'*40
        self.archive=self.base/'package.tgz'
        with tarfile.open(self.archive,'w:gz') as archive:
            raw=json.dumps({'name':'fixture','version':'1.0','license':'MIT'}).encode()
            entry=tarfile.TarInfo('package/package.json');entry.size=len(raw);archive.addfile(entry,io.BytesIO(raw))
        self.integrity='sha512-'+base64.b64encode(hashlib.sha512(self.archive.read_bytes()).digest()).decode()
        self.registry={'name':'fixture','version':'1.0','dist':{'integrity':self.integrity},'gitHead':self.revision,
                       'repository':{'url':'git+https://github.com/owner/repo.git'}}
        self.prefix='https://raw.githubusercontent.com/owner/repo/'+self.revision+'/'
        self.record=dict(path='node_modules/fixture',name='fixture',version='1.0',integrity=self.integrity,
                         archive_sha256=m.digest(self.archive.read_bytes()),source_revision=self.revision,source_repository='owner/repo',
                         registry_metadata=self.pin('https://registry.npmjs.org/fixture/1.0',json.dumps(self.registry)),
                         source_package_metadata=self.pin(self.prefix+'packages/fixture/package.json',json.dumps({'name':'fixture','version':'1.0'})),
                         notices=[self.pin(self.prefix+'LICENSE','Copyright upstream\nOriginal full grant wording\n')])

    def pin(self,url,text):return dict(url=url,text=text,sha256=m.digest(text.encode()))
    def validate(self,record):return m.validate_record(record,'fixture','1.0',self.integrity,m.digest(self.archive.read_bytes()))

    def test_exact_source_notice_preserved_and_independently_validated_by_inventory(self):
        before=copy.deepcopy(self.record);self.validate(self.record);self.assertEqual(self.record,before)
        text=m.notice_text({'records':[self.record]});self.assertIn(self.record['notices'][0]['text'],text)
        result=license_inventory.npm_supplemental(self.record,{'name':'fixture','archive':{'sha256':self.record['archive_sha256']}},
                                                {'version':'1.0','integrity':self.integrity})
        self.assertEqual(result[0]['sha256'],self.record['notices'][0]['sha256'])

    def test_tampered_license_registry_wrong_archive_and_sibling_notices_rejected(self):
        changes=[lambda r:r['notices'][0].update(text='invented'),
                 lambda r:r.update(version='2.0'),lambda r:r.update(archive_sha256='b'*64),
                 lambda r:r['registry_metadata'].update(url='https://example.com/fixture/1.0'),
                 lambda r:r['notices'][0].update(url=self.prefix+'packages/sibling/LICENSE'),
                 lambda r:r['notices'][0].update(url=self.prefix.replace(self.revision,'b'*40)+'LICENSE'),
                 lambda r:r['source_package_metadata'].update(**self.pin(self.prefix+'packages/fixture/package.json','{"name":"fixture","version":"2.0"}'))]
        for change in changes:
            record=copy.deepcopy(self.record);change(record)
            with self.subTest(record=record),self.assertRaises(ValueError):self.validate(record)

    def test_homepage_repository_prefix_cannot_substitute_for_exact_upstream(self):
        record=copy.deepcopy(self.record);metadata=copy.deepcopy(self.registry)
        metadata.pop('repository');metadata['homepage']='https://github.com/owner/repo-unrelated'
        record['registry_metadata']=self.pin('https://registry.npmjs.org/fixture/1.0',json.dumps(metadata))
        with self.assertRaisesRegex(ValueError,'matching upstream'):self.validate(record)

    def test_generated_package_githead_requires_root_notice_without_package_directory_proof(self):
        record=copy.deepcopy(self.record);record.pop('source_package_metadata');self.validate(record)
        record['notices'][0]['url']=self.prefix+'packages/other/LICENSE'
        with self.assertRaises(ValueError):self.validate(record)

    def test_missing_githead_requires_exact_tag_and_source_identity(self):
        record=copy.deepcopy(self.record);registry=copy.deepcopy(self.registry);registry.pop('gitHead')
        record['registry_metadata']=self.pin('https://registry.npmjs.org/fixture/1.0',json.dumps(registry))
        with self.assertRaises(KeyError):self.validate(record)
        record['version_reference']=self.pin('https://api.github.com/repos/owner/repo/commits/v1.0',json.dumps({'sha':self.revision}))
        self.validate(record)
        record.pop('source_package_metadata')
        with self.assertRaises(ValueError):self.validate(record)

    def test_real_archive_sri_identity_and_bytes_integrity(self):
        self.assertEqual(m.archive_identity(self.archive,self.integrity,'fixture','1.0'),self.record['archive_sha256'])
        with self.assertRaises(ValueError):m.archive_identity(self.archive,self.integrity,'fixture','2.0')
        self.archive.write_bytes(b'tamper')
        with self.assertRaises(ValueError):m.archive_identity(self.archive,self.integrity,'fixture','1.0')

    def test_later_author_notice_requires_complete_authoritative_unchanged_tree(self):
        record=copy.deepcopy(self.record);original='b'*40
        metadata=copy.deepcopy(self.registry);metadata['gitHead']=original
        record['registry_metadata']=self.pin('https://registry.npmjs.org/fixture/1.0',json.dumps(metadata))
        comparison={'base_commit':{'sha':original},'commits':[{'sha':self.revision}],'total_commits':1,
                    'files':[{'filename':'LICENSE','status':'added'}]}
        url='https://api.github.com/repos/owner/repo/compare/'+original+'...'+self.revision
        record['source_tree_comparison']=self.pin(url,json.dumps(comparison))
        result=self.validate(record);self.assertIn('preexisting-source-unchanged',result['source_mapping'])
        for change in (lambda c:c['files'].append({'filename':'index.js','status':'modified'}),
                       lambda c:c.update(total_commits=2),lambda c:c['base_commit'].update(sha='c'*40)):
            modified=copy.deepcopy(comparison);change(modified);record['source_tree_comparison']=self.pin(url,json.dumps(modified))
            with self.assertRaises(ValueError):self.validate(record)

    def test_executable_source_equality_uses_actual_archive_bytes_and_complete_coverage(self):
        # A publish-generated package with no gitHead/tag can still bind exact
        # source code bytes; name/version alone is deliberately insufficient.
        code=b'module.exports = true;\n'
        with tarfile.open(self.archive,'w:gz') as archive:
            for name,raw in [('package/package.json',b'{"name":"fixture","version":"1.0"}'),('package/index.js',code)]:
                entry=tarfile.TarInfo(name);entry.size=len(raw);archive.addfile(entry,io.BytesIO(raw))
        record=copy.deepcopy(self.record);record['archive_sha256']=m.digest(self.archive.read_bytes())
        metadata=copy.deepcopy(self.registry);metadata.pop('gitHead')
        record['registry_metadata']=self.pin('https://registry.npmjs.org/fixture/1.0',json.dumps(metadata))
        record['source_package_comparisons']=[dict(archive_member='package/index.js',source=self.pin(self.prefix+'index.js',code.decode()))]
        result=m.validate_record(record,'fixture','1.0',self.integrity,record['archive_sha256'],self.archive)
        self.assertIn('exact-shipped-executable-source-bytes',result['source_mapping'])
        alias=copy.deepcopy(record);alias_registry=copy.deepcopy(self.registry)
        alias['registry_metadata']=self.pin('https://registry.npmjs.org/fixture/1.0',json.dumps(alias_registry))
        alias['source_package_metadata']=self.pin(self.prefix+'package.json','{"name":"fixture-alias","version":"1.0"}')
        mapped=m.validate_record(alias,'fixture','1.0',self.integrity,alias['archive_sha256'],self.archive)
        self.assertEqual(mapped['source_package_identity_discrepancy']['source_name'],'fixture-alias')
        with self.assertRaisesRegex(ValueError,'Actual archive required'):
            m.validate_record(alias,'fixture','1.0',self.integrity,alias['archive_sha256'])

        record['source_package_comparisons'][0]['source']=self.pin(self.prefix+'index.js','changed')
        with self.assertRaisesRegex(ValueError,'source bytes differ'):
            m.validate_record(record,'fixture','1.0',self.integrity,record['archive_sha256'],self.archive)
        record['source_package_comparisons']=[]
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            m.code_equivalence(record,self.archive,self.prefix)

    def test_pinned_source_explicit_author_document_reference_required(self):
        record=copy.deepcopy(self.record)
        record['notices']=[self.pin('https://author.example/license.txt','Full author grant wording')]
        with self.assertRaisesRegex(ValueError,'commit mismatch'):self.validate(record)
        record['referenced_source_notice']=self.pin(self.prefix+'README.md','License: http://author.example/license.txt')
        result=self.validate(record)
        self.assertIn('pinned-source-references-author-document',result['source_mapping'])
        record['referenced_source_notice']=self.pin(self.prefix+'README.md','Unrelated README')
        with self.assertRaisesRegex(ValueError,'explicitly reference'):self.validate(record)

    def test_archive_build_commit_and_exact_tag_bind_generated_package(self):
        raw=json.dumps({'name':'fixture','version':'1.0','buildInfo':{'commitSha':self.revision}}).encode()
        with tarfile.open(self.archive,'w:gz') as archive:
            entry=tarfile.TarInfo('package/package.json');entry.size=len(raw);archive.addfile(entry,io.BytesIO(raw))
        record=copy.deepcopy(self.record);record.pop('source_package_metadata')
        metadata=copy.deepcopy(self.registry);metadata.pop('gitHead')
        record['registry_metadata']=self.pin('https://registry.npmjs.org/fixture/1.0',json.dumps(metadata))
        record['version_reference']=self.pin('https://api.github.com/repos/owner/repo/commits/v1.0',json.dumps({'sha':self.revision}))
        digest=m.digest(self.archive.read_bytes());record['archive_sha256']=digest
        result=m.validate_record(record,'fixture','1.0',self.integrity,digest,self.archive)
        self.assertEqual(result['source_mapping'],'archive-build-commit-and-version-tag')
        record['version_reference']=self.pin('https://api.github.com/repos/owner/repo/commits/v1.0',json.dumps({'sha':'b'*40}))
        with self.assertRaisesRegex(ValueError,'build commit/tag mismatch'):
            m.validate_record(record,'fixture','1.0',self.integrity,digest,self.archive)

    def test_historical_coverage_cannot_be_omitted_or_replaced(self):
        with self.assertRaisesRegex(ValueError,'exactly cover'):m.resolve([])
        with self.assertRaisesRegex(ValueError,'exactly cover'):m.resolve([self.record])

    def test_resolve_reports_missing_facts_and_deterministic_retained_evidence(self):
        counter=0
        def retained(pin):
            nonlocal counter
            counter+=1;path=self.base/str(counter);path.write_text(pin['text'])
            return {'url':pin['url'],'path':str(path),'sha256':pin['sha256']}
        research={k:self.record[k] for k in ('path','name','version','integrity','source_revision')}
        research.update(local_archive=str(self.archive),source_repository_normalized='owner/repo',
                        registry_metadata=retained(self.record['registry_metadata']),
                        source_package_metadata=retained(self.record['source_package_metadata']),
                        notices=[retained(p) for p in self.record['notices']])
        expected={research['path']:('fixture','1.0',self.integrity,self.record['archive_sha256'])}
        first=m.resolve([research],expected);self.assertEqual(first,m.resolve([research],expected));self.assertEqual(first['coverage']['resolved'],1)
        broken=copy.deepcopy(research);broken['notices']=[]
        result=m.resolve([broken],expected);self.assertEqual(result['coverage']['unresolved'],1)
        self.assertEqual(result['records'],[])
        Path(research['notices'][0]['path']).write_text('tamper')
        self.assertEqual(m.resolve([research],expected)['coverage']['unresolved'],1)

class AuthoredSelectionTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        import package_mainsail as builder
        self.builder=builder
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.repo=Path(__file__).resolve().parents[1]
        for folder in ('configs/apps','configs/host','source/vendor/ospath-compat'):
            (self.base/folder).mkdir(parents=True)
        for name in ('source-license-inventory.json','npm-supplemental-notices.json'):
            (self.base/'configs/host'/name).write_bytes((self.repo/'configs/host'/name).read_bytes())
        self.source=self.base/'source';directory=self.source/'vendor/ospath-compat'
        self.contents={'package.json':json.dumps(dict(name='@sv08-mainline/ospath-compat',version='1.0.0',
                       license='AGPL-3.0-or-later',main='index.js')).encode(),
                       'index.js':b'// Independently authored disposable fixture\nmodule.exports = {}\n',
                       'README.md':b'Independently authored fixture\n','LICENSE':(self.repo/'LICENSE').read_bytes()}
        for name,raw in self.contents.items():(directory/name).write_bytes(raw)
        self.spec=dict(name='@sv08-mainline/ospath-compat',version='1.0.0',source_directory='vendor/ospath-compat',
                       files={name:m.digest(raw) for name,raw in self.contents.items()},
                       archive_path='vendor/compat.tgz')
        (self.source/'package.json').write_text(json.dumps({'devDependencies':{'ospath':'file:vendor/compat.tgz'},'overrides':{'cypress':{'ospath':'$ospath'}}}))
        self.archive=self.source/self.spec['archive_path']
        self.archive.write_bytes(builder.authored_archive_bytes(self.source,self.spec))
        self.spec['archive_sha256']=m.digest(self.archive.read_bytes())
        baseline=json.loads((self.base/'configs/host/source-license-inventory.json').read_text())
        packages={p['path']:dict(version=p['version'],integrity=p['integrity'])
                  for p in baseline['mainsail_dependencies']['packages'] if not p['notices']}
        self.selected=dict(name=self.spec['name'],version='1.0.0',resolved='file:vendor/compat.tgz',
                           integrity='sha512-'+base64.b64encode(hashlib.sha512(self.archive.read_bytes()).digest()).decode())
        packages['node_modules/ospath']=self.selected
        self.lock=self.source/'package-lock.json';self.lock.write_text(json.dumps({'packages':{'':{},**packages}}))
        self.config=dict(patched_package_lock_sha256=m.digest(self.lock.read_bytes()),source_patches=[],
                         authored_npm_replacements={'node_modules/ospath':self.spec})
        self.write_config()
        self.inputs=dict(selected_lock=self.pin(self.lock),
            supplemental_notices=self.pin(self.base/'configs/host/npm-supplemental-notices.json'),
            replacement_archives={'node_modules/ospath':dict(self.pin(self.archive),authored_source=self.pin(self.source/'package.json'))})
        mock=patch.object(m,'REPO',self.base);mock.start();self.addCleanup(mock.stop)

    def pin(self,path):return dict(root=str(path.parent),path=path.name,sha256=m.digest(path.read_bytes()))
    def write_config(self):(self.base/'configs/apps/mainsail.json').write_text(json.dumps(self.config))
    def record(self):return next(p for p in m.selection_resolution(self.inputs)['records'] if p['path']=='node_modules/ospath')
    def repin_archive_and_lock(self):
        self.selected['integrity']='sha512-'+base64.b64encode(hashlib.sha512(self.archive.read_bytes()).digest()).decode()
        lock=json.loads(self.lock.read_text());lock['packages']['node_modules/ospath']=self.selected
        self.lock.write_text(json.dumps(lock));self.config['patched_package_lock_sha256']=m.digest(self.lock.read_bytes())
        self.write_config();self.inputs['selected_lock']=self.pin(self.lock)
        self.inputs['replacement_archives']['node_modules/ospath'].update(self.pin(self.archive))

    def test_explicit_source_bound_identity_preserves_historical_unresolved_fact(self):
        record=self.record()
        self.assertEqual(record['selection_status'],'replaced-by-source-bound-authored-package')
        self.assertEqual(record['historical_notice_status'],'unresolved-author-notice')
        self.assertFalse(record['selected_notice_gap'])
        self.assertEqual(record['authored_replacement']['name'],self.spec['name'])
        self.assertEqual(record['replacement_notices'][0]['text'],(self.repo/'LICENSE').read_text())
        self.assertEqual(m.selection_resolution(self.inputs)['coverage']['historical_notice_resolved'],60)

    def test_archive_tamper_and_wrong_selected_identity_fail_closed(self):
        original=self.archive.read_bytes();self.archive.write_bytes(original+b'tamper')
        self.repin_archive_and_lock()
        with self.assertRaisesRegex(ValueError,'source/archive mismatch'):self.record()
        self.archive.write_bytes(original);self.selected['name']='ospath';self.repin_archive_and_lock()
        with self.assertRaisesRegex(ValueError,'identity mismatch'):self.record()

    def test_source_tamper_missing_notice_and_label_only_evidence_rejected(self):
        index=self.source/self.spec['source_directory']/'index.js';index.write_text('tampered')
        with self.assertRaisesRegex(ValueError,'source hash mismatch'):self.record()
        index.write_bytes(self.contents['index.js'])
        notice=self.source/self.spec['source_directory']/'LICENSE';notice.write_text('AGPL-3.0-or-later')
        self.spec['files']['LICENSE']=m.digest(notice.read_bytes());self.write_config()
        with self.assertRaisesRegex(ValueError,'complete project notice'):self.record()
        notice.unlink()
        with self.assertRaisesRegex(ValueError,'directory contents'):self.record()
        self.inputs['replacement_archives']['node_modules/ospath'].pop('authored_source')
        with self.assertRaisesRegex(ValueError,'source evidence required'):self.record()

    def test_root_local_edge_and_cypress_scoped_reference_are_both_required(self):
        manifest=self.source/'package.json'
        original=json.loads(manifest.read_text())
        for section in ('devDependencies','overrides'):
            with self.subTest(section=section):
                changed=copy.deepcopy(original)
                if section=='devDependencies':changed[section].pop('ospath')
                else:changed[section]['cypress']['ospath']='file:vendor/compat.tgz'
                manifest.write_text(json.dumps(changed))
                self.inputs['replacement_archives']['node_modules/ospath']['authored_source']=self.pin(manifest)
                with self.assertRaisesRegex(ValueError,'manifest override mismatch'):self.record()

    def test_wrong_archive_identity_and_missing_notice_even_with_updated_sri_rejected(self):
        for missing_notice in (False,True):
            with self.subTest(missing_notice=missing_notice):
                with tarfile.open(self.archive,'w:gz') as archive:
                    for name,raw in self.contents.items():
                        if missing_notice and name=='LICENSE':continue
                        if not missing_notice and name=='package.json':
                            metadata=json.loads(raw);metadata['name']='ospath';raw=json.dumps(metadata).encode()
                        member=tarfile.TarInfo('package/'+name);member.size=len(raw);archive.addfile(member,io.BytesIO(raw))
                self.repin_archive_and_lock()
                with self.assertRaisesRegex(ValueError,'identity mismatch|source/archive mismatch'):self.record()


class HumanfsAuthoredSelectionTests(unittest.TestCase):
    pin = AuthoredSelectionTests.pin
    write_config = AuthoredSelectionTests.write_config

    def setUp(self):
        AuthoredSelectionTests.setUp(self)
        self.path='node_modules/@humanfs/types'
        self.directory=self.source/'vendor/humanfs-types-compat';self.directory.mkdir()
        self.contents={'package.json':json.dumps(dict(name='@sv08-mainline/humanfs-types-compat',version='1.0.0',
            license='AGPL-3.0-or-later',type='module',types='index.d.ts',
            exports={'.':{'types':'./index.d.ts'}},files=['index.d.ts','LICENSE','README.md'])).encode(),
            'index.d.ts':b'export interface Fixture { value: string; }\n',
            'README.md':b'Independently authored disposable type-only fixture\n',
            'LICENSE':(self.repo/'LICENSE').read_bytes()}
        for name,raw in self.contents.items():(self.directory/name).write_bytes(raw)
        self.spec=dict(name='@sv08-mainline/humanfs-types-compat',version='1.0.0',format='types-only',
            source_directory='vendor/humanfs-types-compat',files={n:m.digest(r) for n,r in self.contents.items()},
            archive_path='vendor/humanfs.tgz')
        self.archive=self.source/self.spec['archive_path']
        self.archive.write_bytes(self.builder.authored_archive_bytes(self.source,self.spec))
        self.spec['archive_sha256']=m.digest(self.archive.read_bytes())
        self.manifest=self.source/'package.json'
        self.manifest.write_text(json.dumps({'devDependencies':{'@humanfs/types':'file:'+self.spec['archive_path']},
            'overrides':{parent:{'@humanfs/types':'$@humanfs/types'} for parent in ('@humanfs/core','@humanfs/node')}}))
        baseline=json.loads((self.base/'configs/host/source-license-inventory.json').read_text())
        packages={p['path']:dict(version=p['version'],integrity=p['integrity'])
                  for p in baseline['mainsail_dependencies']['packages'] if not p['notices']}
        self.selected=dict(name=self.spec['name'],version='1.0.0',resolved='file:'+self.spec['archive_path'],
            integrity='sha512-'+base64.b64encode(hashlib.sha512(self.archive.read_bytes()).digest()).decode())
        packages[self.path]=self.selected
        self.lock.write_text(json.dumps({'packages':{'':{},**packages}}))
        self.config['authored_npm_replacements']={self.path:self.spec}
        self.inputs['replacement_archives']={self.path:dict(self.pin(self.archive),authored_source=self.pin(self.manifest))}
        self.repin()

    def repin(self):
        lock=json.loads(self.lock.read_text());lock['packages'][self.path]=self.selected
        self.lock.write_text(json.dumps(lock));self.config['patched_package_lock_sha256']=m.digest(self.lock.read_bytes())
        self.write_config();self.inputs['selected_lock']=self.pin(self.lock)
        self.inputs['replacement_archives'][self.path].update(self.pin(self.archive))
        self.inputs['replacement_archives'][self.path]['authored_source']=self.pin(self.manifest)

    def record(self):return next(p for p in m.selection_resolution(self.inputs)['records'] if p['path']==self.path)

    def test_type_only_selection_retains_original_notice_facts(self):
        record=self.record()
        self.assertEqual(record['selection_status'],'replaced-by-source-bound-authored-package')
        self.assertEqual(record['historical_notice_status'],'unresolved-author-notice')
        self.assertFalse(record['selected_notice_gap'])
        result=m.selection_resolution(self.inputs)
        self.assertEqual(len(result['records']),69)
        self.assertEqual(result['coverage']['historical_notice_resolved'],60)

    def test_explicit_root_and_both_named_parent_edges_are_required(self):
        original=json.loads(self.manifest.read_text())
        mutations=[lambda v:v['devDependencies'].pop('@humanfs/types'),
            lambda v:v['overrides'].pop('@humanfs/core'),lambda v:v['overrides'].pop('@humanfs/node'),
            lambda v:v['overrides'].update({'@humanfs/types':'file:'+self.spec['archive_path']}),
            lambda v:v['overrides']['@humanfs/core'].update({'@humanfs/types':'file:'+self.spec['archive_path']})]
        for change in mutations:
            changed=copy.deepcopy(original);change(changed);self.manifest.write_text(json.dumps(changed));self.repin()
            with self.assertRaisesRegex(ValueError,'manifest override mismatch'):self.record()

    def test_wrong_identity_sri_source_and_notice_rejected(self):
        self.selected['name']='@humanfs/types';self.repin()
        with self.assertRaisesRegex(ValueError,'identity mismatch'):self.record()
        self.selected['name']=self.spec['name'];self.selected['integrity']='sha512-'+base64.b64encode(bytes(64)).decode();self.repin()
        with self.assertRaisesRegex(ValueError,'SRI mismatch'):self.record()
        self.selected['integrity']='sha512-'+base64.b64encode(hashlib.sha512(self.archive.read_bytes()).digest()).decode();self.repin()
        source=self.directory/'index.d.ts';source.write_text('tamper')
        with self.assertRaisesRegex(ValueError,'source hash mismatch'):self.record()
        source.write_bytes(self.contents['index.d.ts'])
        notice=self.directory/'LICENSE';notice.unlink()
        with self.assertRaisesRegex(ValueError,'directory contents'):self.record()
        notice.write_bytes(self.contents['LICENSE'])
        self.archive.write_bytes(self.archive.read_bytes()+b'tamper')
        self.selected['integrity']='sha512-'+base64.b64encode(hashlib.sha512(self.archive.read_bytes()).digest()).decode();self.repin()
        with self.assertRaisesRegex(ValueError,'source/archive mismatch'):self.record()


if __name__=='__main__':unittest.main()
