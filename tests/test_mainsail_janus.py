# SPDX-License-Identifier: AGPL-3.0-or-later
"""Exact SDK extraction, notice and dependency/consumer regression evidence."""
import base64
import os
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


class MainsailJanus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='mainsail-janus-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.source = Path(cls.temporary.name)
        cls.config = json.loads((REPO/'configs/apps/mainsail.json').read_text())
        cls.provenance = json.loads((REPO/'configs/host/mainsail-janus-sdk.json').read_text())
        archive = subprocess.check_output(['git','-C',str(REPO/cls.config['source_path']),'archive',cls.config['source_commit']])
        import io
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(cls.source,filter='data')
        for index, patch in enumerate(cls.config['source_patches']):
            raw = (REPO/patch['path']).read_bytes()
            if sha(raw) != patch['sha256']: raise AssertionError('patch pin mismatch')
            if index == 4:
                cls.before_manifest = json.loads((cls.source/'package.json').read_text())
                cls.before_lock = json.loads((cls.source/'package-lock.json').read_text())
            subprocess.run(['patch','--batch','--fuzz=0','-p1','-d',str(cls.source),'-i',str(REPO/patch['path'])],
                           check=True,stdout=subprocess.DEVNULL)

    def test_entire_sdk_and_exact_public_notice(self):
        p = self.provenance
        raw = (self.source/p['vendored_path']).read_bytes()
        self.assertEqual(sha(raw),p['vendored_sha256'])
        tail = p['export_tail'].encode()
        self.assertTrue(raw.endswith(tail))
        original = raw[:-len(tail)]
        self.assertEqual(len(original),117451)
        self.assertEqual(sha(original),p['sdk_sha256'])
        notice = (self.source/p['notice_path']).read_bytes()
        self.assertEqual(sha(notice),p['notice_sha256'])
        self.assertEqual(notice,p['sdk_header'].encode())
        self.assertEqual(sha(notice),p['sdk_header_sha256'])
        self.assertIn(notice,original)
        self.assertEqual((self.source/'public/licenses/sv08-janus-adapter-AGPL-3.0.txt').read_bytes(),
                         (REPO/'LICENSE').read_bytes())
        self.assertEqual(subprocess.check_output(['git','-C',str(REPO/self.config['source_path']),'show',
                         self.config['source_commit']+':LICENSE']), (self.source/'LICENSE').read_bytes())

    def test_supplied_supplier_archive_extraction(self):
        archive = os.environ.get('MAINSAIL_JANUS_ARCHIVE')
        if not archive: self.skipTest('Set MAINSAIL_JANUS_ARCHIVE to the retained verified supplier archive')
        p = self.provenance
        raw = Path(archive).read_bytes()
        self.assertEqual(sha(raw),p['archive_sha256'])
        self.assertEqual('sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode(),p['archive_sri'])
        with tarfile.open(archive) as tar: member = tar.extractfile(p['member']).read()
        self.assertEqual(sha(member),p['member_sha256'])
        mapping = json.loads(member)
        self.assertEqual(mapping['sources'][p['source_index']],p['source_name'])
        extracted = mapping['sourcesContent'][p['source_index']].encode()
        self.assertEqual(sha(extracted),p['sdk_sha256'])
        self.assertEqual((self.source/p['vendored_path']).read_bytes(),extracted+p['export_tail'].encode())

    def test_exact_manifest_and_complete_lock_delta(self):
        expected = self.before_manifest
        expected['dependencies'].pop('typed_janus_js')
        expected['dependencies']['webrtc-adapter'] = '9.0.3'
        expected['overrides'].pop('typed_janus_js')
        self.assertEqual(json.loads((self.source/'package.json').read_text()),expected)
        before = self.before_lock['packages']
        after = json.loads((self.source/'package-lock.json').read_text())['packages']
        removed = {'lunr','@gerrit0/mini-shiki','typed_janus_js','typed_janus_js/node_modules/balanced-match',
                   'entities','aigle','@types/unist','@types/hast','aigle-core','@shikijs/themes','linkify-it',
                   'typed_janus_js/node_modules/minimatch','markdown-it','mdurl','typed_janus_js/node_modules/typedoc',
                   '@shikijs/engine-oniguruma','typed_janus_js/node_modules/brace-expansion','@shikijs/langs',
                   '@shikijs/types','@shikijs/vscode-textmate','punycode.js','typed_janus_js/node_modules/typescript','uc.micro'}
        self.assertEqual(before.keys()-after.keys(),{'node_modules/'+name for name in removed})
        self.assertEqual(after.keys()-before.keys(),set())
        self.assertEqual({name for name in before.keys() & after.keys() if before[name]!=after[name]},{''})
        root = json.loads(json.dumps(before['']))
        root['dependencies'].pop('typed_janus_js'); root['dependencies']['webrtc-adapter']='9.0.3'
        self.assertEqual(after[''],root)
        for record in after.values():
            self.assertFalse({'typed_janus_js','aigle','aigle-core'} & record.get('dependencies',{}).keys())

    def test_sole_consumer_preserves_presentation_and_addressing(self):
        name = 'src/components/webcams/streamers/JanusStreamer.vue'
        original = subprocess.check_output(['git','-C',str(REPO/self.config['source_path']),'show',
                                            self.config['source_commit']+':'+name],text=True)
        changed = (self.source/name).read_text()
        self.assertEqual(original.split('<script')[0],changed.split('<script')[0])
        self.assertEqual(original.split('<style')[1],changed.split('<style')[1])
        for start,end in [('    get url()', '    get wrapperStyle()'),
                          ('    get wrapperStyle()', '    startStream()'),
                          ('    onLoadedMetadata()', '    beforeDestroy()')]:
            # The only config annotation change is our independently authored narrow type.
            a=original[original.index(start):original.index(end if end!='    startStream()' else '    async startStream()')]
            b=changed[changed.index(start):changed.index(end)]
            self.assertEqual(a.replace('ConstructorOptions','StreamConfig'),b)
        self.assertIn("@Watch('streamId')",changed)
        self.assertNotIn('typed_janus_js',changed)


if __name__ == '__main__': unittest.main()
