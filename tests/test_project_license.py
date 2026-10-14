# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline exact-byte provenance and deterministic anonymous-transport gate tests."""
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import project_license as license
import qualify_project_source as gate

REVISION = 'a'*40


class ProjectLicenseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name); self.repo = self.base/'source'; self.repo.mkdir()
        inputs = {'LICENSE':b'Exact license\n','LICENSING.md':b'Exact project grant\n',
                  'upstream-lock.json':b'{}','.gitmodules':b'',
                  'runtime/controller.py':b'# covered runtime\n','ui/host/index.html':b'<h1>Host</h1>',
                  'scripts/stage_admin_ui.py':b'# build install recipe\n',
                  'scripts/stage_printer_ui.py':b'# overlay recipe\n',
                  'configs/build.json':b'{}','patches/project.patch':b'exact patch',
                  'docs/development/install.md':b'Build and install instructions'}
        for name, raw in inputs.items():
            path = self.repo/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
        self.root = self.base/'root'; (self.root/'usr/lib/sv08').mkdir(parents=True)
        (self.root/'usr/lib/sv08/release.json').write_text(json.dumps({'release':'fixture','project_source_revision':REVISION}))
        self.overrides = {'usr/lib/sv08/controller.py':inputs['runtime/controller.py'],
                          'usr/share/cockpit/sv08-host/index.html':inputs['ui/host/index.html']}

    def prepare(self, dirty=False, public_source=None):
        with patch.object(license,'source_state',return_value=(REVISION,dirty)):
            return license.prepare(self.root,self.overrides,public_source=public_source,repo=self.repo)

    def stage(self, dirty=False):
        payload, record = self.prepare(dirty)
        license.publish(self.root,self.overrides); license.publish(self.root,payload)
        return record

    def public(self, record):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w:gz') as archive:
            for name in record['source_files']:
                raw = (self.repo/name).read_bytes(); entry = tarfile.TarInfo('source/'+name); entry.size=len(raw)
                archive.addfile(entry,io.BytesIO(raw))
        raw=stream.getvalue()
        manifest=dict(format_version=1,source_revision=REVISION,archive_prefix='source/',
                      archive={'url':'https://public.example/source/'+REVISION+'.tar.gz','sha256':license.digest(raw)})
        for group, paths in gate.required_inputs(record['source_files']).items():
            manifest[group]=[dict(path=n,sha256=record['source_files'][n],archive_member=True) for n in sorted(paths)]
        return manifest,raw

    def snapshot(self):
        return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_exact_notices_mapping_and_nonmutating_plan(self):
        before=self.snapshot(); payload,record=self.prepare()
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(payload[license.DOC+'project-LICENSE.txt'],(self.repo/'LICENSE').read_bytes())
        self.assertEqual(payload['usr/share/cockpit/sv08-host/project-NOTICE.txt'],(self.repo/'LICENSING.md').read_bytes())
        self.assertEqual(record['staged_files']['usr/lib/sv08/controller.py']['sources'],['runtime/controller.py'])
        self.assertFalse(record['public_source']['qualified']); self.assertFalse(record['overall_release_qualified'])
        self.stage(); self.assertEqual(license.validate(self.root)['build_id'],record['build_id'])

    def test_file_notice_missing_extra_and_stale_release_refuse(self):
        self.stage(); before=self.snapshot()
        for name in ('usr/lib/sv08/controller.py',license.DOC+'project-NOTICE.txt','usr/lib/sv08/release.json'):
            path=self.root/name; raw=path.read_bytes(); path.write_bytes(b'changed')
            with self.assertRaises(ValueError):license.validate(self.root)
            path.write_bytes(raw); path.unlink()
            with self.assertRaises((ValueError,FileNotFoundError)):license.validate(self.root)
            path.write_bytes(raw)
        extra=self.root/'usr/lib/sv08/extra.py';extra.write_bytes(b'not recorded')
        with self.assertRaisesRegex(ValueError,'inventory'):license.validate(self.root)
        extra.unlink(); self.assertEqual(self.snapshot(),before)

    def test_symlink_source_and_output_refuse_without_mutation(self):
        before=self.snapshot(); link=self.repo/'runtime/link.py';link.symlink_to('/dev/null')
        with self.assertRaisesRegex(ValueError,'Symlink'):self.prepare()
        link.unlink(); target=self.root/'usr/share';target.mkdir();(target/'doc').symlink_to(self.base)
        with self.assertRaisesRegex(ValueError,'Symlink'):self.prepare()
        self.assertEqual(self.snapshot(),before)

    def test_anonymous_exact_archive_and_coverage_pass_source_only(self):
        record=self.stage(); manifest,raw=self.public(record);before=self.snapshot()
        result=gate.verify_public(record,manifest,transport=lambda url:raw)
        self.assertTrue(result['qualified']);self.assertFalse(result['overall_release_qualified'])
        self.assertEqual(result['scope'],'project-source-only');self.assertEqual(result['build_id'],record['build_id'])
        with patch.object(gate,'download',return_value=raw):self.assertEqual(gate.qualify(self.root,manifest),result)
        self.assertEqual(self.snapshot(),before)

    def test_unknown_installed_original_bytes_cannot_qualify(self):
        for filename in ('unknown','unknown.bin','unknown.html','unknown.pyc','project-source.json'):
            path=self.root/'usr/lib/sv08'/filename;path.write_bytes(b'arbitrary unmatched original bytes')
            _,record=self.prepare()
            self.assertTrue(record['development'])
            self.assertIn('usr/lib/sv08/'+filename,record['unmatched_original_files'])
            self.assertEqual(record['staged_files']['usr/lib/sv08/'+filename]['origin'],'unmatched')
            manifest,raw=self.public(record)
            with self.assertRaisesRegex(ValueError,'development'):gate.verify_public(record,manifest,lambda url:raw)
            path.unlink()

    def test_existing_release_producer_needs_no_new_runtime_field(self):
        (self.root/'usr/lib/sv08/release.json').write_text('{"release":"normal-producer"}')
        record=self.stage();manifest,raw=self.public(record)
        self.assertTrue(gate.verify_public(record,manifest,lambda url:raw)['qualified'])
        # Exact release bytes still bind the build, independent of display version.
        (self.root/'usr/lib/sv08/release.json').write_text('{"release":"changed"}')
        with self.assertRaisesRegex(ValueError,'Stale'):license.validate(self.root)

    def test_dirty_missing_identity_and_declared_mismatch_refuse(self):
        record=self.stage(True);manifest,raw=self.public(record)
        with self.assertRaisesRegex(ValueError,'development'):gate.verify_public(record,manifest,lambda url:raw)
        record['development']=False;record['source_revision']=None
        with self.assertRaises(ValueError):gate.verify_public(record,manifest,lambda url:raw)
        record['source_revision']=REVISION;record['release']=None
        with self.assertRaisesRegex(ValueError,'Missing installed'):gate.verify_public(record,manifest,lambda url:raw)
        record['release']={'identity':{'project_source_revision':'b'*40}}
        with self.assertRaisesRegex(ValueError,'mismatch'):gate.verify_public(record,manifest,lambda url:raw)

    def test_moving_wrong_missing_public_inputs_and_unavailable_refuse(self):
        record=self.stage();manifest,raw=self.public(record);before=self.snapshot()
        wrong=json.loads(json.dumps(manifest));wrong['archive']['url']='https://public.example/source/main.tar.gz'
        with self.assertRaisesRegex(ValueError,'Moving'):gate.verify_public(record,wrong,lambda url:raw)
        with self.assertRaisesRegex(ValueError,'hash'):gate.verify_public(record,manifest,lambda url:b'wrong')
        wrong=json.loads(json.dumps(manifest));wrong['patches']=[]
        with self.assertRaisesRegex(ValueError,'coverage'):gate.verify_public(record,wrong,lambda url:raw)
        for group in ('patches','build_inputs','install_inputs'):
            wrong=json.loads(json.dumps(manifest));wrong[group][0]['sha256']='b'*64
            with self.assertRaisesRegex(ValueError,'pin mismatch'):gate.verify_public(record,wrong,lambda url:raw)
        with self.assertRaises(URLError):gate.verify_public(record,manifest,lambda url:(_ for _ in ()).throw(URLError('unavailable')))
        self.assertEqual(self.snapshot(),before)

    def test_wrong_archive_member_and_downloaded_input_refuse(self):
        record=self.stage();manifest,raw=self.public(record)
        (self.repo/'runtime/controller.py').write_bytes(b'different source')
        wrong,new_raw=self.public(record)
        with self.assertRaisesRegex(ValueError,'corresponding source'):gate.verify_public(record,wrong,lambda url:new_raw)
        item=manifest['patches'][0];item.pop('archive_member');item['url']='https://public.example/'+REVISION+'/patch'
        with self.assertRaisesRegex(ValueError,'input hash'):gate.verify_public(record,manifest,lambda url:raw if url.endswith('.tar.gz') else b'wrong')

    def test_public_staging_refusal_and_late_drift_are_nonmutating(self):
        _,record=self.prepare();manifest,raw=self.public(record);before=self.snapshot()
        with patch.object(gate,'download',return_value=b'wrong'):
            with self.assertRaises(ValueError):self.prepare(public_source=manifest)
        self.assertEqual(self.snapshot(),before)
        record=self.stage();manifest,raw=self.public(record)
        def drift(url):
            (self.root/'usr/lib/sv08/release.json').write_text('{}');return raw
        with patch.object(gate,'download',side_effect=drift):
            with self.assertRaisesRegex(ValueError,'Stale'):gate.qualify(self.root,manifest)

    def test_private_or_authenticated_urls_and_unsafe_archives_refuse(self):
        for url in ('https://127.0.0.1/'+REVISION,'https://localhost/'+REVISION,
                    'https://user:secret@public.example/'+REVISION,'https://public.example/'+REVISION+'?token=x'):
            with self.assertRaises(ValueError):gate.immutable_url(url,REVISION,'b'*64)
        for name,kind in (('../escape',tarfile.REGTYPE),('source/link',tarfile.SYMTYPE)):
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w') as archive:
                member=tarfile.TarInfo(name);member.type=kind;archive.addfile(member)
            with self.assertRaises(ValueError):gate.archive_files(stream.getvalue())


if __name__=='__main__':unittest.main()
