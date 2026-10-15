# SPDX-License-Identifier: AGPL-3.0-or-later
"""Independent path API, deterministic local npm package and selected-source pins."""
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


class MainsailOspath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='mainsail-ospath-')
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
            if index==6:
                cls.before_manifest=json.loads((cls.source/'package.json').read_text())
                cls.before_lock=json.loads((cls.source/'package-lock.json').read_text())
            subprocess.run(['patch','--batch','--fuzz=0','-p1','-d',str(cls.source),'-i',str(REPO/patch['path'])],
                           check=True,stdout=subprocess.DEVNULL)
        cls.spec=cls.config['authored_npm_replacements']['node_modules/ospath']

    def test_complete_measured_api_contract(self):
        result=subprocess.run(['node',str(REPO/'tests/mainsail_ospath_compat.cjs'),
                               str(self.source/self.spec['source_directory']/'index.js')],
                              check=True,capture_output=True,text=True,timeout=10)
        self.assertEqual(json.loads(result.stdout),dict(baselineScenarios=32,mutationStages=32,status='passed'))

    def test_manifest_preserves_test_runner_and_scopes_only_one_edge(self):
        expected=copy.deepcopy(self.before_manifest)
        expected['devDependencies']['ospath']='file:'+self.spec['archive_path']
        expected['overrides']['cypress']={'ospath':'$ospath'}
        actual=json.loads((self.source/'package.json').read_text())
        self.assertEqual(actual,expected)
        self.assertEqual(actual['scripts']['test'],self.before_manifest['scripts']['test'])
        self.assertEqual(actual['scripts']['test:ui'],'cypress open')
        self.assertEqual((self.source/'LICENSE').read_bytes(),self.original_license)

    def test_deterministic_archive_exact_sources_full_grant_and_metadata(self):
        raw=builder.authored_archive_bytes(self.source,self.spec)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),self.spec['archive_sha256'])
        self.assertEqual(builder.authored_archive_bytes(self.source,self.spec),raw)
        self.assertEqual(raw[4:8],bytes(4))  # gzip timestamp
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            self.assertEqual(archive.getnames(),['package/'+n for n in sorted(self.spec['files'])])
            for member in archive:
                self.assertTrue(member.isfile())
                self.assertEqual((member.uid,member.gid,member.mtime,member.mode),(0,0,0,0o644))
                self.assertEqual((member.uname,member.gname),('',''))
                self.assertEqual(hashlib.sha256(archive.extractfile(member).read()).hexdigest(),
                                 self.spec['files'][Path(member.name).name])
        self.assertEqual((self.source/self.spec['source_directory']/'LICENSE').read_bytes(),(REPO/'LICENSE').read_bytes())

    def test_generated_archive_before_install_and_reject_existing_target(self):
        target=self.source/self.spec['archive_path']
        self.addCleanup(lambda:target.unlink(missing_ok=True))
        builder.prepare_authored_archives(self.source,self.config)
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),self.spec['archive_sha256'])
        with self.assertRaisesRegex(ValueError,'already exists'):builder.prepare_authored_archives(self.source,self.config)
        code=(REPO/'scripts/package_mainsail.py').read_text()
        self.assertLess(code.index('    prepare_authored_archives(src, c)'),code.index("    run('npm', 'ci'"))

    def test_reject_tampered_sources_unsafe_members_and_missing_project_notice(self):
        bad=copy.deepcopy(self.spec);bad['files']['index.js']='0'*64
        with self.assertRaisesRegex(ValueError,'source hash'):builder.authored_archive_bytes(self.source,bad)
        bad=copy.deepcopy(self.spec);bad['files'].pop('LICENSE')
        with self.assertRaisesRegex(ValueError,'source members'):builder.authored_archive_bytes(self.source,bad)
        for relative in ('../outside','/outside','vendor/../outside','vendor\\outside'):
            with self.subTest(path=relative),self.assertRaisesRegex(ValueError,'Unsafe'):builder.source_member(self.source,relative)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'link').symlink_to(self.source,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Symlink'):builder.source_member(root,'link/package.json')

    def test_genuine_selected_lock_identity_and_complete_delta(self):
        after=json.loads((self.source/'package-lock.json').read_text())
        self.assertEqual(hashlib.sha256((self.source/'package-lock.json').read_bytes()).hexdigest(),
                         self.config['patched_package_lock_sha256'])
        old,new=self.before_lock['packages'],after['packages']
        self.assertEqual(old.keys(),new.keys())
        self.assertEqual({k for k in old if old[k]!=new[k]},{'','node_modules/ospath'})
        root=copy.deepcopy(old[''])
        root['devDependencies']['ospath']='file:'+self.spec['archive_path']
        self.assertEqual(new[''],root)
        selected=new['node_modules/ospath']
        self.assertEqual((selected['name'],selected['version'],selected['resolved']),
                         (self.spec['name'],self.spec['version'],'file:'+self.spec['archive_path']))
        import base64
        raw=builder.authored_archive_bytes(self.source,self.spec)
        self.assertEqual(selected['integrity'],'sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode())
        self.assertFalse(any(p.get('name',k.rsplit('node_modules/',1)[-1])=='ospath' for k,p in new.items() if k))


if __name__=='__main__':unittest.main()
