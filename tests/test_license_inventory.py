import json
import base64
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import warnings
import tarfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import license_inventory as m


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = dict(identity='fixture', version='1.0', kind='source-archive', sha256='a' * 64)

    def pin(self, name, content):
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return dict(root=str(self.base), path=name, sha256=m.sha(path))

    def provenance(self):
        return dict(name='fixture', version='1.0', source_pin=self.source,
                    classification='upstream-binary', rebuild_evidence=[])

    def wheel(self, notices=True, extra=None):
        path = self.base / 'fixture-1.0-py3-none-any.whl'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('fixture-1.0.dist-info/METADATA', 'Name: fixture\nVersion: 1.0\nLicense: supplier text, not inferred SPDX\n')
            z.writestr('fixture/_vendor/other-9.dist-info/METADATA', 'Name: wrong\nVersion: 9\n')
            if notices:
                z.writestr('fixture-1.0.dist-info/LICENSE.txt', b'license text')
                z.writestr('fixture/_vendor/NOTICE', b'vendor notice')
            if extra:
                z.writestr(*extra)
        return path

    def npm_fixture(self, include_notice=True, declared_license='MIT', prefix='package'):
        content = {prefix + '/package.json': json.dumps({'name': 'fixture', 'version': '1.0', 'license': declared_license}).encode()}
        if include_notice:
            content[prefix + '/LICENSE'] = b'authoritative npm supplier notice'
        archive = self.base / 'npm-fixture.tar'
        with tarfile.open(archive, 'w') as tar:
            for name, data in content.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
        package_json = dict(self.pin('copied/package.json', content[prefix + '/package.json']), archive_member=prefix + '/package.json')
        notices = [dict(self.pin('copied/LICENSE', content[prefix + '/LICENSE']), archive_member=prefix + '/LICENSE')] if include_notice else []
        entry = dict(name='fixture', version='1.0', integrity=integrity,
                     archive=dict(root=str(self.base), path=archive.name, sha256=m.sha(archive)),
                     package_json=package_json, notices=notices)
        lock = {'packages': {'': {}, 'node_modules/fixture': {'version': '1.0', 'integrity': integrity,
                                                           'resolved': 'https://supplier/example.tgz', 'dev': True}}}
        pin = self.pin('package-lock.json', json.dumps(lock).encode())
        pin.update(archive_notice_root=str(self.base), dependency_notices={'node_modules/fixture': entry})
        self.pin('configs/apps/mainsail.json', json.dumps({'patched_package_lock_sha256': pin['sha256']}).encode())
        return pin, lock

    def test_top_level_metadata_and_all_embedded_notices(self):
        result = m.inspect_wheel(self.wheel(), ('fixture', '1.0'), self.provenance())
        self.assertEqual(result['name'], 'fixture')
        self.assertEqual(len(result['embedded_notices']), 2)
        self.assertEqual(result['declared_license_metadata']['License'], ['supplier text, not inferred SPDX'])
        self.assertEqual(result['classification'], 'upstream-binary')
        self.assertEqual(result['rebuild_evidence'], [])

    def test_metadata_and_source_version_mismatch(self):
        with self.assertRaises(ValueError):
            m.inspect_wheel(self.wheel(), ('fixture', '2.0'), self.provenance())
        provenance = self.provenance()
        provenance['version'] = '2.0'
        with self.assertRaises(ValueError):
            m.inspect_wheel(self.wheel(), ('fixture', '1.0'), provenance)

    def test_missing_notice_requires_actual_source_bound_text(self):
        wheel = self.wheel(notices=False)
        with self.assertRaises(ValueError):
            m.inspect_wheel(wheel, ('fixture', '1.0'), self.provenance())
        notice = dict(self.pin('source/LICENSE', b'authoritative source notice'), source_pin=self.source)
        provenance = dict(self.provenance(), supplemental_notices=[notice])
        result = m.inspect_wheel(wheel, ('fixture', '1.0'), provenance)
        self.assertEqual(result['supplemental_notices'][0]['sha256'], notice['sha256'])
        (self.base / notice['path']).write_bytes(b'tamper')
        with self.assertRaises(ValueError):
            m.inspect_wheel(wheel, ('fixture', '1.0'), provenance)

    def test_declared_notice_and_unsafe_members_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            wheel = self.wheel(extra=('fixture-1.0.dist-info/METADATA', 'Name: fixture\nVersion: 1.0\n'))
        with self.assertRaises(ValueError):
            m.inspect_wheel(wheel, ('fixture', '1.0'), self.provenance())
        wheel = self.wheel(extra=('../escape/LICENSE', 'text'))
        with self.assertRaises(ValueError):
            m.inspect_wheel(wheel, ('fixture', '1.0'), self.provenance())
        wheel = self.wheel()
        with zipfile.ZipFile(wheel, 'r') as z:
            contents = {name: z.read(name) for name in z.namelist()}
        contents['fixture-1.0.dist-info/METADATA'] += b'License-File: missing.txt\n'
        with zipfile.ZipFile(wheel, 'w') as z:
            for name, content in contents.items():
                z.writestr(name, content)
        with self.assertRaises(ValueError):
            m.inspect_wheel(wheel, ('fixture', '1.0'), self.provenance())

    def test_file_paths_and_source_file_tamper(self):
        pin = self.pin('source.tar.gz', b'source')
        source = dict(self.source, sha256=pin['sha256'], file=pin)
        self.assertEqual(m.source_pin(source)['file']['sha256'], pin['sha256'])
        (self.base / pin['path']).write_bytes(b'tamper')
        with self.assertRaises(ValueError):
            m.source_pin(source)
        for relative in ('../escape', '/etc/passwd'):
            with self.assertRaises(ValueError):
                m.checked_path(self.base, relative)
        outside = self.base.parent / 'outside'
        (self.base / 'escape').symlink_to(outside)
        with self.assertRaises(ValueError):
            m.checked_path(self.base, 'escape')

    def test_rebuild_proof_not_inferred_from_native_binary(self):
        provenance = dict(self.provenance(), classification='project-source-build')
        with self.assertRaises(ValueError):
            m.evidence(provenance)
        proof = self.pin('proof.json', b'{"two_identical_builds":true}')
        provenance['rebuild_evidence'] = [proof]
        self.assertEqual(len(m.evidence(provenance)['rebuild_evidence']), 1)
        provenance['classification'] = 'upstream-binary'
        with self.assertRaises(ValueError):
            m.evidence(provenance)

    def test_exact_wheel_lock_tamper_and_determinism(self):
        wheel = self.wheel()
        lock = self.pin('runtime.lock', ('fixture==1.0 --hash=sha256:' + m.sha(wheel) + '\n').encode())
        inputs = dict(wheelhouses=[dict(root=str(self.base), lock=lock['path'], lock_sha256=lock['sha256'])],
                      wheel_sources={m.sha(wheel): self.provenance()})
        self.pin('configs/apps/fixture.json', json.dumps({'runtime_lock': lock['path'], 'runtime_lock_sha256': lock['sha256']}).encode())
        with patch.object(m, 'REPO', self.base):
            first = m.serialize(m.wheel_inventory(inputs))
            self.assertEqual(first, m.serialize(m.wheel_inventory(inputs)))
            self.assertNotIn(str(self.base), first)
            (self.base / 'extra.whl').write_bytes(b'extra')
            with self.assertRaises(ValueError):
                m.wheel_inventory(inputs)
            (self.base / 'extra.whl').unlink()
            wheel.write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                m.wheel_inventory(inputs)

    def test_application_selection_version_and_patch_tamper(self):
        config = dict(version='current-2', source_commit='b' * 40,
                      source_patches=[dict(path='patch.diff', sha256=self.pin('patch.diff', b'patch')['sha256'])])
        name = 'configs/apps/fixture.json'
        config_pin = self.pin(name, json.dumps(config).encode())
        rauc = 'configs/host-os/rauc-package.json'
        rauc_pin = self.pin(rauc, json.dumps(dict(version='current-2')).encode())
        artifact = self.pin('artifact.deb', b'package')
        notice = dict(self.pin('LICENSE', b'notice'), source_pin=self.source)
        record = dict(self.provenance(), config_sha256=config_pin['sha256'], version='current-2',
                      source_pin=dict(self.source, commit='b' * 40, kind='git-commit'),
                      artifact=artifact, notices=[notice])
        inputs = {'applications': {name: record, rauc: dict(record, config_sha256=rauc_pin['sha256'])}}
        with patch.object(m, 'REPO', self.base):
            self.assertEqual(len(m.applications(inputs)), 2)
            record['version'] = 'obsolete-1'
            with self.assertRaises(ValueError):
                m.applications(inputs)
            record['version'] = 'current-2'
            (self.base / 'patch.diff').write_bytes(b'tamper')
            with self.assertRaises(ValueError):
                m.applications(inputs)

    def missing_license_fixture(self):
        source_artifact = self.pin('extensions/fixture.py', b'fixture source with no license declaration')
        config = {'version': '1-2', 'source': source_artifact['path'], 'source_sha256': source_artifact['sha256']}
        name = 'configs/apps/fixture.json'
        config_pin = self.pin(name, json.dumps(config).encode())
        artifact = self.pin('fixture.deb', b'package')
        receipt = {'license_status': 'not-declared-in-inspected-source', 'source_sha256': source_artifact['sha256'],
                   'inspected_paths': [source_artifact['path'], 'LICENSE', 'COPYING'], 'notices': []}
        inspection = self.pin('license-inspection.json', json.dumps(receipt).encode())
        record = dict(self.provenance(), config_sha256=config_pin['sha256'], version=config['version'],
                      source_pin=dict(self.source, kind='source-file', sha256=source_artifact['sha256']),
                      artifact=artifact, notices=[], license_status='not-declared-in-inspected-source',
                      source_artifact=source_artifact, license_inspection=inspection)
        rauc = 'configs/host-os/rauc-package.json'
        rauc_config = self.pin(rauc, json.dumps({'version': '1-2'}).encode())
        licensed = dict(self.provenance(), config_sha256=rauc_config['sha256'], version='1-2', artifact=artifact,
                        notices=[dict(self.pin('LICENSE.txt', b'actual notice'), source_pin=self.source)])
        return {'applications': {name: record, rauc: licensed}}, record, receipt

    def test_application_missing_declaration_is_visible_and_source_bound(self):
        inputs, record, receipt = self.missing_license_fixture()
        with patch.object(m, 'REPO', self.base):
            output = m.applications(inputs)[0]
        self.assertTrue(output['unresolved_license_declaration'])
        self.assertEqual(output['license_status'], 'not-declared-in-inspected-source')
        self.assertEqual(output['notices'], [])
        self.assertEqual(output['source']['kind'], 'source-file')
        self.assertEqual(output['source_artifact']['sha256'], record['source_pin']['sha256'])
        self.assertEqual(output['license_inspection']['sha256'], record['license_inspection']['sha256'])
        self.assertEqual(output['license_inspection']['inspected_paths'], receipt['inspected_paths'])

    def test_application_empty_notices_require_actual_matching_inspection(self):
        for missing in ('license_status', 'license_inspection', 'source_artifact'):
            inputs, record, receipt = self.missing_license_fixture()
            record.pop(missing)
            with patch.object(m, 'REPO', self.base), self.assertRaises(ValueError):
                m.applications(inputs)
        for mutation in ({'source_sha256': 'f' * 64}, {'notices': ['LICENSE']}, {'inspected_paths': ['LICENSE']},
                         {'license_status': 'license-declared'}):
            inputs, record, receipt = self.missing_license_fixture()
            receipt.update(mutation)
            record['license_inspection'] = self.pin('license-inspection.json', json.dumps(receipt).encode())
            with patch.object(m, 'REPO', self.base), self.assertRaises(ValueError):
                m.applications(inputs)
        inputs, record, receipt = self.missing_license_fixture()
        (self.base / record['source_artifact']['path']).write_bytes(b'tampered source')
        with patch.object(m, 'REPO', self.base), self.assertRaises(ValueError):
            m.applications(inputs)

    def test_application_undeclared_flag_rejects_contradictory_notice(self):
        inputs, record, receipt = self.missing_license_fixture()
        record['notices'] = [dict(self.pin('notice.txt', b'actual notice'), source_pin=self.source)]
        with patch.object(m, 'REPO', self.base), self.assertRaises(ValueError):
            m.applications(inputs)

    def test_npm_patched_lock_integrity_and_declared_metadata(self):
        pin, lock = self.npm_fixture()
        with patch.object(m, 'REPO', self.base):
            result = m.npm_inventory(pin)
            self.assertIsNone(result['packages'][0]['declared_license'])
            self.assertEqual(result['packages'][0]['dependency_scope'], 'build')
            self.assertEqual(result['packages'][0]['notices'][0]['sha256'], pin['dependency_notices']['node_modules/fixture']['notices'][0]['sha256'])
            lock['packages']['node_modules/fixture'].pop('integrity')
            new_pin = self.pin('package-lock.json', json.dumps(lock).encode())
            pin.update(new_pin)
            self.pin('configs/apps/mainsail.json', json.dumps({'patched_package_lock_sha256': pin['sha256']}).encode())
            with self.assertRaises(ValueError):
                m.npm_inventory(pin)

    def test_npm_archive_integrity_and_copied_text_tamper(self):
        pin, lock = self.npm_fixture()
        entry = pin['dependency_notices']['node_modules/fixture']
        package = lock['packages']['node_modules/fixture']
        notice = entry['notices'][0]
        (self.base / notice['path']).write_bytes(b'tampered')
        # Even a refreshed copied-file pin cannot substitute unrelated text.
        notice['sha256'] = m.sha(self.base / notice['path'])
        with self.assertRaises(ValueError):
            m.npm_archive_notices('node_modules/fixture', package, entry, self.base)
        pin, lock = self.npm_fixture()
        entry = pin['dependency_notices']['node_modules/fixture']
        archive = self.base / entry['archive']['path']
        archive.write_bytes(b'tampered archive')
        entry['archive']['sha256'] = m.sha(archive)
        with self.assertRaises(ValueError):
            m.npm_archive_notices('node_modules/fixture', lock['packages']['node_modules/fixture'], entry, self.base)

    def test_npm_all_optional_platform_notices_required_and_bound_root(self):
        pin, lock = self.npm_fixture()
        entry = pin['dependency_notices']['node_modules/fixture']
        entry['archive']['root'] = str(self.base.parent)
        with self.assertRaises(ValueError):
            m.npm_archive_notices('node_modules/fixture', lock['packages']['node_modules/fixture'], entry, self.base)
        pin, lock = self.npm_fixture()
        lock['packages']['node_modules/fixture']['optional'] = True
        pin.update(self.pin('package-lock.json', json.dumps(lock).encode()))
        self.pin('configs/apps/mainsail.json', json.dumps({'patched_package_lock_sha256': pin['sha256']}).encode())
        with patch.object(m, 'REPO', self.base):
            self.assertTrue(m.npm_inventory(pin)['packages'][0]['optional'])
            pin['dependency_notices'].clear()
            with self.assertRaises(ValueError):
                m.npm_inventory(pin)

    def test_npm_inspected_declaration_only_and_nonstandard_archive_prefix(self):
        pin, lock = self.npm_fixture(include_notice=False, declared_license='MIT', prefix='node')
        with patch.object(m, 'REPO', self.base):
            result = m.npm_inventory(pin)
        package = result['packages'][0]
        self.assertEqual(package['classification'], 'supplier-declaration-only; no embedded notice text')
        self.assertEqual(package['archive_declared_license'], 'MIT')
        self.assertEqual(package['archive_declared_license_sha256'], m.digest(b'MIT'))
        self.assertEqual(package['recognizable_notice_file_count'], 0)
        self.assertEqual(result['notice_coverage']['declaration_only_dependencies'], 1)
        self.assertEqual(result['notice_coverage']['inspected_supplier_archives'], 1)
        self.assertEqual(package['package_json']['archive_member'], 'node/package.json')
        for declared in (None, '', '   ', {}):
            pin, lock = self.npm_fixture(include_notice=False, declared_license=declared)
            with self.assertRaises(ValueError):
                m.npm_archive_notices('node_modules/fixture', lock['packages']['node_modules/fixture'],
                                     pin['dependency_notices']['node_modules/fixture'], self.base)

    def test_npm_declaration_does_not_allow_omitting_present_notice(self):
        pin, lock = self.npm_fixture(declared_license='MIT')
        entry = pin['dependency_notices']['node_modules/fixture']
        entry['notices'].clear()
        with self.assertRaises(ValueError):
            m.npm_archive_notices('node_modules/fixture', lock['packages']['node_modules/fixture'], entry, self.base)
        pin, lock = self.npm_fixture(include_notice=False, declared_license='ISC')
        entry = pin['dependency_notices']['node_modules/fixture']
        entry['declared_license'] = 'MIT'
        with self.assertRaises(ValueError):
            m.npm_archive_notices('node_modules/fixture', lock['packages']['node_modules/fixture'], entry, self.base)

    def test_debian_source_binding_and_literal_supplier_defect(self):
        copyright = self.pin('root/usr/share/doc/fixture/copyright', b'GPL and missing GFDL-3 supplier reference')
        common = self.pin('root/usr/share/common-licenses/GPL-3', b'GPL text')
        package = dict(package='fixture', version='1', architecture='all', sha256='c' * 64,
                       source='fixture-src', source_version='1')
        source = dict(source='fixture-src', source_version='1', binaries=[package],
                      source_archives=[dict(filename='src.tar', sha256='d' * 64, downloaded=False)], source_index='supplier-index')
        records = {'packages': dict(snapshot='fixed', packages=[package]), 'sources': dict(sources=[source]),
                   'copyrights': {'fixture': dict(path='usr/share/doc/fixture/copyright', resolved_path='usr/share/doc/fixture/copyright',
                                                sha256=copyright['sha256'], common_license_references={'GPL-3': common['sha256'], 'GFDL-3': 'missing'})},
                   'license-references': dict(entries=[dict(package='fixture', raw_token='GFDL-3', copyright_sha256=copyright['sha256'],
                                                           candidate_target='usr/share/common-licenses/GFDL-3', target_exists=False,
                                                           target_sha256=None, classification='literal-reference-missing', exact_occurrences=[])])}
        for name, value in records.items():
            self.pin('configs/host-os/recovery-' + name + '.json', json.dumps(value).encode())
        with patch.object(m, 'REPO', self.base):
            result = m.debian_inventory(self.base / 'root')
            self.assertFalse(result['packages'][0]['source_build_proven'])
            refs = result['packages'][0]['common_license_references']
            self.assertEqual(refs[0]['classification'], 'literal-reference-missing')
            self.assertIsNone(refs[0]['sha256'])
            records['sources']['sources'][0]['source_version'] = 'obsolete'
            self.pin('configs/host-os/recovery-sources.json', json.dumps(records['sources']).encode())
            with self.assertRaises(ValueError):
                m.debian_inventory(self.base / 'root')


if __name__ == '__main__':
    unittest.main()
