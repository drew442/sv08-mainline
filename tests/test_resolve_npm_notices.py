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

if __name__=='__main__':unittest.main()
