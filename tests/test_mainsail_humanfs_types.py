# SPDX-License-Identifier: AGPL-3.0-or-later
"""Type-only source, deterministic archive and genuine selected lock contracts.

Strict compiler integration uses the shared mainsail_humanfs_types_contract.ts
fixture, copied as .mts, with public core/node entrypoints and no skipLibCheck.
"""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'scripts'))
import package_mainsail as builder


class MainsailHumanfsTypes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='mainsail-humanfs-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.source = Path(cls.temporary.name)
        cls.config = json.loads((REPO/'configs/apps/mainsail.json').read_text())
        upstream = REPO/cls.config['source_path']
        for name in ('package.json','package-lock.json','vite.config.ts','src/main.ts',
                     'src/components/webcams/streamers/JanusStreamer.vue','LICENSE'):
            target=cls.source/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(subprocess.check_output(['git','-C',str(upstream),'show',cls.config['source_commit']+':'+name]))
        cls.original_license=(cls.source/'LICENSE').read_bytes()
        for index, patch in enumerate(cls.config['source_patches']):
            raw=(REPO/patch['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=patch['sha256']:raise AssertionError('patch pin mismatch')
            if index==7:
                cls.before_manifest=json.loads((cls.source/'package.json').read_text())
                cls.before_lock=json.loads((cls.source/'package-lock.json').read_text())
            subprocess.run(['patch','--batch','--fuzz=0','-p1','-d',str(cls.source),'-i',str(REPO/patch['path'])],
                           check=True,stdout=subprocess.DEVNULL)
        cls.spec=cls.config['authored_npm_replacements']['node_modules/@humanfs/types']

    def test_only_manifest_edges_and_type_sources_change(self):
        self.assertEqual(self.config['package_version'],'2.19.0+git32f99e1c-10')
        expected=copy.deepcopy(self.before_manifest)
        expected['devDependencies']['@humanfs/types']='file:'+self.spec['archive_path']
        for parent in ('@humanfs/core','@humanfs/node'):
            expected['overrides'][parent]={'@humanfs/types':'$@humanfs/types'}
        self.assertEqual(json.loads((self.source/'package.json').read_text()),expected)
        self.assertEqual((self.source/'LICENSE').read_bytes(),self.original_license)
        self.assertEqual((self.source/self.spec['source_directory']/'LICENSE').read_bytes(),(REPO/'LICENSE').read_bytes())
        self.assertEqual((self.source/'tests/humanfs-types-contract.mts').read_bytes(),
                         (REPO/'tests/mainsail_humanfs_types_contract.ts').read_bytes())
        patch=(REPO/'patches/mainsail/0008-humanfs-types-compat.patch').read_text()
        touched={line[6:] for line in patch.splitlines() if line.startswith('+++ b/')}
        self.assertEqual(touched,{'package.json','package-lock.json','tests/humanfs-types-contract.mts',
                         *('vendor/humanfs-types-compat/'+n for n in self.spec['files'])})

    def test_type_only_metadata_and_deterministic_complete_archive(self):
        raw=builder.authored_archive_bytes(self.source,self.spec)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),self.spec['archive_sha256'])
        self.assertEqual(raw,builder.authored_archive_bytes(self.source,self.spec))
        self.assertEqual(raw[4:8],bytes(4))
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            self.assertEqual(archive.getnames(),['package/'+n for n in sorted(self.spec['files'])])
            for member in archive:
                self.assertTrue(member.isfile())
                self.assertEqual((member.mode,member.uid,member.gid,member.mtime),(0o644,0,0,0))
                self.assertEqual(hashlib.sha256(archive.extractfile(member).read()).hexdigest(),
                                 self.spec['files'][Path(member.name).name])
        self.assertEqual(self.config['authored_npm_replacements']['node_modules/ospath']['archive_sha256'],
                         'fd33af5945ab0419963815569c5811521eb724ab6b69e06b1749097a407d42b2')

    def test_reject_unknown_format_tamper_symlinks_notice_and_executable_metadata(self):
        directory=self.source/self.spec['source_directory']
        for field,value in (('format','unknown'),('name','@humanfs/types')):
            bad=copy.deepcopy(self.spec);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):builder.authored_archive_bytes(self.source,bad)
        original={name:(directory/name).read_bytes() for name in self.spec['files']}
        try:
            for name in self.spec['files']:
                (directory/name).write_bytes(b'tamper')
                with self.subTest(tamper=name),self.assertRaisesRegex(ValueError,'source hash'):
                    builder.authored_archive_bytes(self.source,self.spec)
                (directory/name).write_bytes(original[name])
            for key,value in (('main','index.js'),('exports',{'.':{'types':'./index.d.ts','default':'./index.js'}}),
                              ('types','missing.d.ts'),('scripts',{'install':'false'})):
                metadata=json.loads(original['package.json']);metadata[key]=value
                (directory/'package.json').write_text(json.dumps(metadata))
                bad=copy.deepcopy(self.spec);bad['files']['package.json']=builder.digest(directory/'package.json')
                with self.subTest(metadata=key),self.assertRaisesRegex(ValueError,'type-only package metadata'):
                    builder.authored_archive_bytes(self.source,bad)
            (directory/'package.json').write_bytes(original['package.json'])
            (directory/'LICENSE').write_text('AGPL-3.0-or-later')
            bad=copy.deepcopy(self.spec);bad['files']['LICENSE']=builder.digest(directory/'LICENSE')
            with self.assertRaisesRegex(ValueError,'complete project notice'):builder.authored_archive_bytes(self.source,bad)
            (directory/'LICENSE').write_bytes(original['LICENSE'])
            (directory/'index.d.ts').unlink();(directory/'index.d.ts').symlink_to(directory/'README.md')
            with self.assertRaisesRegex(ValueError,'Symlink'):builder.authored_archive_bytes(self.source,self.spec)
            (directory/'index.d.ts').unlink()
        finally:
            for name,raw in original.items():(directory/name).write_bytes(raw)

    def test_genuine_lock_only_changes_root_and_selected_types_record(self):
        after=json.loads((self.source/'package-lock.json').read_text())
        self.assertEqual(builder.digest(self.source/'package-lock.json'),self.config['patched_package_lock_sha256'])
        old,new=self.before_lock['packages'],after['packages']
        self.assertEqual(old.keys(),new.keys())
        self.assertEqual({key for key in old if old[key]!=new[key]},{'','node_modules/@humanfs/types'})
        expected=copy.deepcopy(old['']);expected['devDependencies']['@humanfs/types']='file:'+self.spec['archive_path']
        self.assertEqual(new[''],expected)
        selected=new['node_modules/@humanfs/types']
        self.assertEqual((selected['name'],selected['version'],selected['resolved']),
                         (self.spec['name'],self.spec['version'],'file:'+self.spec['archive_path']))
        raw=builder.authored_archive_bytes(self.source,self.spec)
        self.assertEqual(selected['integrity'],'sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode())
        self.assertEqual(new['node_modules/@humanfs/core'],old['node_modules/@humanfs/core'])
        self.assertEqual(new['node_modules/@humanfs/node'],old['node_modules/@humanfs/node'])
        self.assertFalse(any(p.get('name',key.rsplit('node_modules/',1)[-1])=='@humanfs/types'
                             for key,p in new.items() if key))


if __name__=='__main__':unittest.main()
