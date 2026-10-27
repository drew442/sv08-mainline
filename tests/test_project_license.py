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

    def seed_fixture(self):
        sys.path.insert(0,str(license.REPO/'runtime'))
        from sv08_printer_stack import MAINSail, NGINX, MOONRAKER
        for name in ('scripts/project_license.py','scripts/integrate_host_os.py','runtime/sv08_printer_stack.py'):
            target=self.repo/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((license.REPO/name).read_bytes())
        values={'mainsail.json':(json.dumps(MAINSail,indent=2)+'\n').encode(),
                'nginx-mainsail.conf':NGINX.encode(),'moonraker.conf':MOONRAKER.encode()}
        # Moonraker is already recognized as an exact source file in real staging.
        (self.repo/'configs/moonraker.conf').write_bytes(values['moonraker.conf'])
        for filename,raw in values.items():
            path=self.root/'usr/lib/sv08/seed/config'/filename
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        key=self.root/'usr/lib/sv08/seed/authorized_keys'
        key.write_bytes(b'disposable synthetic public-key fixture only\n')
        return key,values

    def test_canonical_seed_recipes_and_hashed_owner_input_qualify_unit_archive(self):
        key,values=self.seed_fixture();before=self.snapshot()
        payload,record=self.prepare();self.assertEqual(self.snapshot(),before)
        self.assertFalse(record['development']);self.assertEqual(record['unmatched_original_files'],[])
        name='usr/lib/sv08/seed/authorized_keys'
        self.assertEqual(record['non_code_build_inputs'],{
            name:dict(type='owner-public-key',sha256=license.digest(key.read_bytes()))})
        self.assertNotIn(name,record['staged_files']);self.assertNotIn(name,record['source_files'])
        self.assertNotIn(key.read_bytes().strip(),license.encoded(record))
        for raw in payload.values():self.assertNotIn(key.read_bytes().strip(),raw)
        for filename in ('mainsail.json','nginx-mainsail.conf'):
            entry=record['staged_files']['usr/lib/sv08/seed/config/'+filename]
            self.assertEqual(entry['origin'],'generated')
            self.assertEqual(entry['sources'],['scripts/project_license.py','scripts/integrate_host_os.py',
                                               'runtime/sv08_printer_stack.py'])
        original_id=record['build_id'];key.write_bytes(b'another synthetic public key\n')
        _,changed=self.prepare();self.assertNotEqual(changed['build_id'],original_id)
        self.stage();record=license.validate(self.root);manifest,raw=self.public(record)
        # Unit transport supplies exact synthetic corresponding-source archive bytes.
        with patch.object(gate,'download',return_value=raw):
            self.assertTrue(gate.qualify(self.root,manifest)['qualified'])
        self.assertFalse(record['overall_release_qualified'])

    def test_seed_recipes_use_supplied_checkout_literals_without_import_or_cache(self):
        _,old=self.seed_fixture()
        source=self.repo/'runtime/sv08_printer_stack.py'
        declared={'defaultMode':'declared-checkout','instances':[]}
        nginx='# nginx from declared checkout\n'
        # This source must never be executed, even though it declares supported literals.
        source.write_text("raise RuntimeError('must not execute source')\nNGINX = "+repr(nginx)+
                          "\nMAINSail = dict(defaultMode='declared-checkout', instances=[])\n")
        import sv08_printer_stack
        with patch.object(sv08_printer_stack,'NGINX','cached unrelated nginx'), \
             patch.object(sv08_printer_stack,'MAINSail',{'defaultMode':'cached-unrelated'}):
            _,record=self.prepare()
            self.assertTrue(record['development'])
            for filename in ('mainsail.json','nginx-mainsail.conf'):
                self.assertIn('usr/lib/sv08/seed/config/'+filename,record['unmatched_original_files'])
            expected={'mainsail.json':(json.dumps(declared,indent=2)+'\n').encode(),
                      'nginx-mainsail.conf':nginx.encode()}
            for filename,raw in expected.items():
                (self.root/'usr/lib/sv08/seed/config'/filename).write_bytes(raw)
            _,record=self.prepare();self.assertFalse(record['development'])
            # A second declaration in the same process also bypasses module caches.
            source.write_text("NGINX = 'new literal nginx\\n'\nMAINSail = "+repr(declared)+"\n")
            _,record=self.prepare();self.assertTrue(record['development'])
            (self.root/'usr/lib/sv08/seed/config/nginx-mainsail.conf').write_bytes(b'new literal nginx\n')
            self.assertFalse(self.prepare()[1]['development'])

    def test_unsupported_or_ambiguous_seed_constant_forms_are_unmatched(self):
        self.seed_fixture();source=self.repo/'runtime/sv08_printer_stack.py'
        cases=("NGINX = 'literal' + ' computed'\nMAINSail = dict(instances=[])\n",
               "NGINX = 'literal'\nNGINX = 'reassigned'\nMAINSail = dict(instances=[])\n",
               "NGINX: str = 'literal'\nMAINSail = dict(instances=[])\n",
               "NGINX = 'literal'\nMAINSail = dict(**{'instances': []})\n",
               "NGINX = 'literal'\nMAINSail = factory()\n",
               "NGINX = 'literal'\nMAINSail = dict(instances=[], instances=[])\n")
        for raw in cases:
            with self.subTest(source=raw):
                source.write_text(raw);self.assertIsNone(license.seed_recipe_bytes(self.repo))
                self.assertTrue(self.prepare()[1]['development'])

    def test_altered_seed_outputs_and_unknown_seed_code_stay_unmatched(self):
        _,values=self.seed_fixture()
        for filename in ('mainsail.json','nginx-mainsail.conf','unknown.conf','controller.py','authorized_keys'):
            path=self.root/'usr/lib/sv08/seed/config'/filename
            original=values.get(filename)
            # Even JSON whitespace differing from the producer is not its recipe.
            path.write_bytes(original+b' ' if original else b'unmapped seed/code bytes')
            _,record=self.prepare();name=path.relative_to(self.root).as_posix()
            self.assertTrue(record['development']);self.assertIn(name,record['unmatched_original_files'])
            manifest,raw=self.public(record)
            with self.assertRaisesRegex(ValueError,'development'):gate.verify_public(record,manifest,lambda url:raw)
            if original is None:path.unlink()
            else:path.write_bytes(original)
        path=self.root/'usr/lib/sv08/seed/config/mainsail.json'
        altered=json.loads(values['mainsail.json']);altered['defaultMode']='altered'
        path.write_text(json.dumps(altered,indent=2)+'\n')
        self.assertTrue(self.prepare()[1]['development'])

    def test_owner_input_drift_presence_bound_and_symlinks_refuse(self):
        key,_=self.seed_fixture();record=self.stage();original=key.read_bytes()
        for raw in (b'changed synthetic input',b'x'*(license.NON_CODE_INPUT_LIMIT+1)):
            key.write_bytes(raw)
            with self.assertRaises(ValueError):license.validate(self.root)
        key.unlink()
        with self.assertRaisesRegex(ValueError,'Non-code build input'):license.validate(self.root)
        external=self.base/'synthetic-key';external.write_bytes(original)
        key.symlink_to(external)
        with self.assertRaisesRegex(ValueError,'Symlink'):license.validate(self.root)
        with self.assertRaisesRegex(ValueError,'Symlink'):self.prepare()
        key.unlink();key.write_bytes(b'x'*(license.NON_CODE_INPUT_LIMIT+1))
        with self.assertRaisesRegex(ValueError,'bound'):self.prepare()
        key.write_bytes(original)
        self.assertEqual(license.validate(self.root),record)
        with self.assertRaisesRegex(ValueError,'Stage the owner public-key'):
            license.prepare(self.root,{key.relative_to(self.root).as_posix():b'override'},repo=self.repo)

    def test_legacy_without_key_validates_and_key_addition_refuses(self):
        self.stage()
        # A pre-field record retains its original build identity and remains valid.
        for base in (license.DOC,*license.PACKAGES):
            path=self.root/(base+'project-source.json')
            if not path.exists():continue
            record=json.loads(path.read_bytes());record.pop('non_code_build_inputs')
            record['build_id']=license.build_id(record);path.write_bytes(license.encoded(record))
        license.validate(self.root)
        key=self.root/'usr/lib/sv08/seed/authorized_keys';key.parent.mkdir(parents=True)
        key.write_bytes(b'synthetic added key')
        with self.assertRaisesRegex(ValueError,'Non-code build input'):license.validate(self.root)

    def test_owner_input_public_failures_do_not_publish_and_late_drift_refuses(self):
        key,_=self.seed_fixture();_,record=self.prepare();manifest,raw=self.public(record)
        before=self.snapshot()
        with patch.object(gate,'download',return_value=b'wrong archive'):
            with self.assertRaisesRegex(ValueError,'hash mismatch'):self.prepare(public_source=manifest)
        self.assertEqual(self.snapshot(),before)
        record=self.stage();manifest,raw=self.public(record)
        def drift(url):key.write_bytes(b'late synthetic key change');return raw
        with patch.object(gate,'download',side_effect=drift):
            with self.assertRaisesRegex(ValueError,'Non-code build input'):gate.qualify(self.root,manifest)

    def test_private_or_authenticated_urls_and_unsafe_archives_refuse(self):
        for url in ('https://127.0.0.1/'+REVISION,'https://localhost/'+REVISION,
                    'https://user:secret@public.example/'+REVISION,'https://public.example/'+REVISION+'?token=x'):
            with self.assertRaises(ValueError):gate.immutable_url(url,REVISION,'b'*64)
        for name,kind in (('../escape',tarfile.REGTYPE),('source/link',tarfile.SYMTYPE)):
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w') as archive:
                member=tarfile.TarInfo(name);member.type=kind;archive.addfile(member)
            with self.assertRaises(ValueError):gate.archive_files(stream.getvalue())


# Keep runtime integrity acceptance in the existing package/release CI suite.
import sv08_provenance as provenance


class ProvenanceTests(unittest.TestCase):
    setUp = ProjectLicenseTests.setUp
    prepare = ProjectLicenseTests.prepare
    stage = ProjectLicenseTests.stage
    snapshot = ProjectLicenseTests.snapshot

    def test_project_branding_allowlist_matches_staged_assets(self):
        assets = license.REPO/'configs/host-os/cockpit-branding'
        self.assertEqual(set(provenance.BRANDING_FILES), {p.name for p in assets.iterdir() if p.is_file()})

    def test_stock_vendor_branding_links_are_outside_project_scope(self):
        branding = self.root/'usr/share/cockpit/branding/debian'
        branding.mkdir(parents=True)
        vendor = self.root/'usr/share/pixmaps/debian-logo.png'
        vendor.parent.mkdir(parents=True); vendor.write_bytes(b'vendor image')
        for name in ('favicon.ico', 'logo.png'):
            (branding/name).symlink_to('../../../pixmaps/debian-logo.png')
        for name in provenance.BRANDING_FILES:
            (branding/name).write_bytes(('project '+name).encode())
        record = self.stage()
        self.assertEqual(provenance.status(self.root)['state'], 'intact')
        for name in ('favicon.ico', 'logo.png'):
            self.assertNotIn(str((branding/name).relative_to(self.root)), record['staged_files'])
        vendor.write_bytes(b'vendor package changed')
        self.assertEqual(provenance.status(self.root)['state'], 'intact')
        asset = branding/'branding.css'; original = asset.read_bytes()
        asset.write_bytes(b'changed project branding')
        self.assertEqual(provenance.status(self.root)['state'], 'tainted')
        asset.write_bytes(original)
        self.assertEqual(provenance.status(self.root)['state'], 'intact')
        asset.unlink(); asset.symlink_to('../../../pixmaps/debian-logo.png')
        self.assertEqual(provenance.status(self.root)['state'], 'tainted')

    def test_shared_validator_and_clean_configuration_exclusion(self):
        self.assertIs(license.validate, provenance.validate)
        record = self.stage()
        config = self.root/'data/config/printer.cfg'
        config.parent.mkdir(parents=True); config.write_text('mutable user configuration')
        before = self.snapshot()
        self.assertEqual(provenance.status(self.root), dict(state='intact',
            build_id=record['build_id'], scope='local-project-record', reason='record-matches'))
        self.assertEqual(self.snapshot(), before)

    def test_covered_changes_additions_deletions_notices_and_records(self):
        self.stage(); before = self.snapshot()
        cases = [('usr/lib/sv08/controller.py', b'changed'),
                 ('usr/lib/sv08/added.py', b'addition'),
                 ('usr/lib/sv08/controller.py', None),
                 (provenance.DOC+'project-NOTICE.txt', b'changed notice'),
                 ('usr/lib/sv08/release.json', b'{}'),
                 (provenance.DOC+'project-source.json', b'[]'),
                 (provenance.DOC+'project-source.json', b'{invalid'),
                 ('usr/share/cockpit/sv08-host/project-source.json', b'{}'),
                 ('usr/share/cockpit/sv08-host/project-source.json', None)]
        for name, raw in cases:
            with self.subTest(name=name, raw=raw):
                path = self.root/name
                if raw is None: path.unlink()
                else: path.write_bytes(raw)
                self.assertEqual(provenance.status(self.root)['state'], 'tainted')
                if name in before: path.write_bytes(before[name])
                else: path.unlink()
        self.assertEqual(provenance.status(self.root)['state'], 'intact')

    def test_missing_read_failed_and_walk_failure_never_green(self):
        self.assertEqual(provenance.status(self.root)['reason'], 'baseline-missing')
        self.stage()
        with patch.object(Path, 'read_bytes', side_effect=PermissionError('private details')):
            self.assertEqual(provenance.status(self.root)['state'], 'unavailable')
        def failed(*args, **kwargs):
            kwargs['onerror'](PermissionError('private directory'))
            return iter(())
        with patch.object(provenance.os, 'walk', side_effect=failed):
            result = provenance.status(self.root)
            self.assertEqual(result['state'], 'unavailable')
            self.assertNotIn('private', json.dumps(result))
        # Non-code public-key hash mismatches remain covered but are never returned.
        key = self.root/'usr/lib/sv08/seed/authorized_keys'
        key.parent.mkdir(); key.write_text('public build input')
        result = provenance.status(self.root)
        self.assertEqual(result['state'], 'tainted')
        self.assertEqual(set(result), {'state','scope','reason','build_id'})



if __name__=='__main__':unittest.main()
