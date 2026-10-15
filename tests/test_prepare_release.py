# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import copy
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_release as m

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name);self.image=self.base/'image';self.image.write_bytes(b'image')
        self.public=self.base/'public.json';self.public.write_text(json.dumps({'source_revision':'a'*40}))
        self.record=dict(image={'sha256':m.file_hash(self.image),'bytes':5},roots=[{'source_qualification':{'qualified':True,'source_revision':'a'*40}}])

    def prepare(self):return m.prepare(self.image,self.public,profile='project-source')

    def test_fixed_checks_deterministic_package_no_input_mutations_or_overall_claim(self):
        before=self.image.read_bytes()
        with patch.object(m,'inspect_artifact',return_value=self.record) as inspect:
            first=self.prepare();self.assertEqual(first,self.prepare())
            self.assertEqual(inspect.call_args.args,(self.image,None,{'source_revision':'a'*40}))
        report=json.loads(first['report.json']);self.assertFalse(report['overall_release_qualified'])
        self.assertFalse(report['hardware_qualified']);self.assertFalse(report['software_notice_inventory_checked'])
        self.assertEqual([c['id'] for c in report['checks']],list(m.PROFILES['project-source']))
        manifest=json.loads(first['release-manifest.json'])
        for name,digest in manifest['files'].items():self.assertEqual(m.hashlib.sha256(first[name]).hexdigest(),digest)
        output=self.base/'package';m.write_package(output,first)
        with self.assertRaises(ValueError):m.write_package(output,first)
        self.assertEqual(before,self.image.read_bytes())

    def test_missing_stale_failed_source_cannot_be_replaced_by_receipt(self):
        for record in ({'image':self.record['image'],'roots':[]},
                       {'image':self.record['image'],'roots':[{'passed':True}]},
                       {'image':self.record['image'],'roots':[{'source_qualification':{'qualified':True,'source_revision':'b'*40}}]}):
            with patch.object(m,'inspect_artifact',return_value=record),self.assertRaises(ValueError):self.prepare()
        with patch.object(m,'inspect_artifact',side_effect=ValueError('stale installed bytes')),self.assertRaises(ValueError):self.prepare()

    def test_artifact_and_input_drift_refused(self):
        def drift(*args):self.image.write_bytes(b'tampered');return self.record
        with patch.object(m,'inspect_artifact',side_effect=drift),self.assertRaisesRegex(ValueError,'Artifact changed'):self.prepare()
        def input_drift(*args):self.public.write_text('{}');return self.record
        with patch.object(m,'inspect_artifact',side_effect=input_drift),self.assertRaisesRegex(ValueError,'inputs changed'):self.prepare()

    def deb_fixture(self):
        root=self.base/'deb-root';(root/'DEBIAN').mkdir(parents=True)
        (root/'DEBIAN/control').write_text('Package: example\nVersion: 1.0\nArchitecture: all\nMaintainer: Test <test@example.invalid>\nDescription: disposable test package\n')
        payload=root/'usr/bin/example';payload.parent.mkdir(parents=True);payload.write_bytes(b'exact application bytes')
        artifact=self.base/'example.deb'
        subprocess.run(['dpkg-deb','--build','--root-owner-group',str(root),str(artifact)],check=True,stdout=subprocess.DEVNULL)
        pin={'root':str(self.base),'path':artifact.name,'sha256':m.file_hash(artifact)}
        inputs={'applications':{'configs/apps/mainsail.json':{'artifact':pin}},'mainsail':{}}
        source_path=m.license_inventory.REPO/'configs/apps/mainsail.json'
        root_record=dict(self.record['roots'][0],selected_partition=2,
            project={'source_files':{'configs/apps/mainsail.json':m.file_hash(source_path)}},
            packages=[{'name':'example','version':'1.0','architecture':'all'}],
            files=[{'path':'usr/bin/example','kind':'file','sha256':m.file_hash(payload)}])
        return inputs,root_record

    def test_real_debian_installed_identity_payload_and_tamper_bindings(self):
        inputs,root=self.deb_fixture()
        binding=m.installed_application_bindings(inputs,[root])[0]
        self.assertEqual(binding['usr_payload_files'],1);self.assertEqual(binding['matching_partitions'],[2])
        for mutate in (lambda r:r['packages'][0].update(version='2.0'),
                       lambda r:r['files'][0].update(sha256='b'*64),lambda r:r.update(files=[])):
            changed=copy.deepcopy(root);mutate(changed)
            with self.assertRaisesRegex(ValueError,'not found'):m.installed_application_bindings(inputs,[changed])
        (self.base/'example.deb').write_bytes(b'tampered archive')
        with self.assertRaises(ValueError):m.installed_application_bindings(inputs,[root])

    def test_selected_software_fixed_checks_and_missing_failed_prerequisites(self):
        inputs,root=self.deb_fixture();record=dict(self.record,roots=[root])
        path=self.base/'inventory.json';path.write_text(json.dumps(inputs))
        inventory={'applications':[],'mainsail_dependencies':{'notice_coverage':{'declaration_only_dependencies':0}}}
        with patch.object(m,'inspect_artifact',return_value=record),patch.object(m.license_inventory,'generate',return_value=inventory):
            result=m.prepare(self.image,self.public,inventory_inputs=path)
            report=json.loads(result['report.json'])
            self.assertEqual([c['id'] for c in report['checks']],list(m.PROFILES['selected-software']))
            self.assertTrue(report['software_notice_inventory_checked']);self.assertFalse(report['overall_release_qualified'])
            inventory['mainsail_dependencies']['notice_coverage']['declaration_only_dependencies']=1
            with self.assertRaisesRegex(ValueError,'Unresolved NPM'):m.prepare(self.image,self.public,inventory_inputs=path)
            inventory['mainsail_dependencies']['notice_coverage']['declaration_only_dependencies']=0
            inventory['applications']=[{'unresolved_license_declaration':True}]
            with self.assertRaisesRegex(ValueError,'Unresolved application'):m.prepare(self.image,self.public,inventory_inputs=path)
            inventory['applications']=[]
            root['project']['source_files']={}
            with self.assertRaisesRegex(ValueError,'configuration differs'):m.prepare(self.image,self.public,inventory_inputs=path)
            root['packages']=[]
            with self.assertRaisesRegex(ValueError,'package databases'):m.prepare(self.image,self.public,inventory_inputs=path)

    def test_profiles_require_all_applicable_inputs(self):
        with self.assertRaisesRegex(ValueError,'requires inventory'):m.prepare(self.image,self.public)
        with self.assertRaises(ValueError):m.prepare(self.image,self.public,profile='unknown')
        with self.assertRaises(ValueError):m.prepare(self.image,self.public,profile='project-source',inventory_inputs='unused')
        with self.assertRaises(OSError):m.prepare(self.base/'absent',self.base/'absent',profile='project-source')

if __name__=='__main__':unittest.main()
