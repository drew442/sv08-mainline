# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
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

    def deb_fixture(self, opt=False):
        root=self.base/'deb-root';(root/'DEBIAN').mkdir(parents=True)
        (root/'DEBIAN/control').write_text('Package: example\nVersion: 1.0\nArchitecture: all\nMaintainer: Test <test@example.invalid>\nDescription: disposable test package\n')
        payload=root/'usr/bin/example';payload.parent.mkdir(parents=True);payload.write_bytes(b'exact application bytes')
        if opt:
            executable=root/'opt/sv08-mainline/klipper/klippy.py'
            executable.parent.mkdir(parents=True);executable.write_bytes(b'exact main executable')
            interpreter=root/'opt/sv08-mainline/venvs/klipper/bin/python'
            interpreter.parent.mkdir(parents=True);interpreter.symlink_to('/usr/bin/python3')
            for name in ('etc/example.conf','opt/private/secret','opt/sv08-mainline-other/token'):
                excluded=root/name;excluded.parent.mkdir(parents=True,exist_ok=True);excluded.write_bytes(b'excluded')
        artifact=self.base/'example.deb'
        subprocess.run(['dpkg-deb','--build','--root-owner-group',str(root),str(artifact)],check=True,stdout=subprocess.DEVNULL)
        pin={'root':str(self.base),'path':artifact.name,'sha256':m.file_hash(artifact)}
        inputs={'applications':{'configs/apps/mainsail.json':{'artifact':pin}},'mainsail':{}}
        source_path=m.license_inventory.REPO/'configs/apps/mainsail.json'
        root_record=dict(self.record['roots'][0],selected_partition=2,
            project={'source_files':{'configs/apps/mainsail.json':m.file_hash(source_path)}},
            packages=[{'name':'example','version':'1.0','architecture':'all'}],
            files=[{'path':'usr/bin/example','kind':'file','sha256':m.file_hash(payload)}])
        if opt:
            from image_license_inventory import tree_inventory
            root_record['files']=tree_inventory(root)
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

    def test_opt_executable_and_venv_symlink_are_bound_and_exclusions_counted(self):
        inputs,root=self.deb_fixture(opt=True)
        binding=m.installed_application_bindings(inputs,[root])[0]
        self.assertEqual(binding['software_payload_files'],3)
        self.assertEqual(binding['usr_payload_files'],1)
        self.assertEqual(binding['opt_payload_files'],2)
        self.assertEqual(binding['excluded_non_software_members'],3)
        self.assertEqual(binding['excluded_non_usr_members'],5)
        self.assertEqual(binding['matching_partitions'],[2])
        for path,key,value in (('opt/sv08-mainline/klipper/klippy.py','sha256','b'*64),
                               ('opt/sv08-mainline/venvs/klipper/bin/python','target','/another/python')):
            for missing in (False,True):
                with self.subTest(path=path,missing=missing):
                    changed=copy.deepcopy(root)
                    if missing:changed['files']=[f for f in changed['files'] if f['path']!=path]
                    else:next(f for f in changed['files'] if f['path']==path)[key]=value
                    with self.assertRaisesRegex(ValueError,'not found'):
                        m.installed_application_bindings(inputs,[changed])

    def ab_fixture(self):
        inputs,root=self.deb_fixture(opt=True)
        partitions=[dict(number=i+1,name=name) for i,name in enumerate(
            ('boot-a','root-a','boot-b','root-b','recovery','data'))]
        roots=[]
        for number in (2,4,5):
            record=copy.deepcopy(root);record.update(selected_partition=number,partitions=copy.deepcopy(partitions))
            roots.append(record)
        # Recovery has its own package DB and project source, without selected apps.
        roots[2].update(packages=[dict(name='recovery-tools',version='1',architecture='all')],files=[])
        return inputs,roots

    def test_all_normal_slots_bound_and_recovery_exempt(self):
        inputs,roots=self.ab_fixture()
        binding=m.installed_application_bindings(inputs,roots)[0]
        self.assertEqual(binding['matching_partitions'],[2,4])
        self.assertEqual(binding['required_normal_partitions'],[2,4])
        for slot in (0,1):
            for defect in ('changed-payload','missing-payload','changed-package','missing-package'):
                with self.subTest(slot=slot,defect=defect):
                    changed=copy.deepcopy(roots)
                    executable=next(f for f in changed[slot]['files'] if f['path'].endswith('klippy.py'))
                    if defect=='changed-payload':executable['sha256']='b'*64
                    elif defect=='missing-payload':changed[slot]['files'].remove(executable)
                    elif defect=='changed-package':changed[slot]['packages'][0]['version']='2'
                    else:changed[slot]['packages']=[]
                    # Even a matching recovery root must not substitute for A or B.
                    changed[2]['files']=copy.deepcopy(roots[0]['files'])
                    changed[2]['packages']=copy.deepcopy(roots[0]['packages'])
                    with self.assertRaisesRegex(ValueError,'not found in every required normal slot'):
                        m.installed_application_bindings(inputs,changed)
        for slot in (0,1):
            with self.subTest(missing_slot=slot),self.assertRaisesRegex(ValueError,'Missing normal-root inventory'):
                m.installed_application_bindings(inputs,[r for i,r in enumerate(roots) if i!=slot])

    def test_complete_disk_prepare_requires_apps_in_normal_slots_and_recovery_source_metadata(self):
        inputs,roots=self.ab_fixture()
        path=self.base/'inventory.json';path.write_text(json.dumps(inputs))
        record=dict(self.record,roots=roots)
        inventory={'applications':[],'mainsail_dependencies':{'notice_coverage':{'declaration_only_dependencies':0}}}
        with patch.object(m,'inspect_artifact',return_value=record),patch.object(m.license_inventory,'generate',return_value=inventory):
            result=m.prepare(self.image,self.public,inventory_inputs=path)
            self.assertEqual(json.loads(result['installed-application-bindings.json'])[0]['required_normal_partitions'],[2,4])
            roots[2]['source_qualification']['qualified']=False
            with self.assertRaisesRegex(ValueError,'Every software root'):m.prepare(self.image,self.public,inventory_inputs=path)
            roots[2]['source_qualification']['qualified']=True
            roots[2]['packages']=[]
            with self.assertRaisesRegex(ValueError,'package databases'):m.prepare(self.image,self.public,inventory_inputs=path)

    def test_partition_identities_cannot_hide_required_normal_slot(self):
        inputs,roots=self.ab_fixture()
        for defect in ('duplicate-number','duplicate-role','contradictory-table','missing-table',
                       'missing-role','duplicate-root','unknown-root'):
            with self.subTest(defect=defect):
                changed=copy.deepcopy(roots)
                if defect=='duplicate-number':
                    for root in changed:root['partitions'][3]['number']=2
                elif defect=='duplicate-role':
                    for root in changed:root['partitions'][3]['name']='root-a'
                elif defect=='contradictory-table':changed[0]['partitions'][3]['name']='other'
                elif defect=='missing-table':del changed[0]['partitions']
                elif defect=='missing-role':
                    for root in changed:root['partitions'][3]['name']='other'
                elif defect=='duplicate-root':changed[1]['selected_partition']=2
                else:changed[1]['selected_partition']=99
                with self.assertRaises(ValueError):m.installed_application_bindings(inputs,changed)

    def test_raw_single_root_partition_metadata_keeps_existing_binding(self):
        inputs,root=self.deb_fixture()
        root.update(selected_partition=0,partitions=[dict(number=0,format='ext4')])
        binding=m.installed_application_bindings(inputs,[root])[0]
        self.assertEqual(binding['matching_partitions'],[0]);self.assertEqual(binding['required_normal_partitions'],[])

    def test_standalone_gpt_root_a_supported_but_incomplete_ab_refused(self):
        inputs,root=self.deb_fixture()
        root['partitions']=[dict(number=1,name='boot-a'),dict(number=2,name='root-a')]
        binding=m.installed_application_bindings(inputs,[root])[0]
        self.assertEqual(binding['matching_partitions'],[2]);self.assertEqual(binding['required_normal_partitions'],[])
        for evidence in ('boot-b','recovery'):
            with self.subTest(evidence=evidence):
                changed=copy.deepcopy(root);changed['partitions'].append(dict(number=3,name=evidence))
                with self.assertRaisesRegex(ValueError,'Incomplete normal A/B'):
                    m.installed_application_bindings(inputs,[changed])
        root['partitions']=[dict(number=2,name='recovery')]
        with self.assertRaisesRegex(ValueError,'Incomplete normal A/B'):m.installed_application_bindings(inputs,[root])

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


    @unittest.skipUnless(os.environ.get('SV08_GCODEVIEWER_ARCHIVE'),'requires retained exact supplier archive')
    def test_standard_terms_export_exact_bytes_manifest_and_reject_stale_missing_corrupt(self):
        inv=m.license_inventory;approved=inv.APPROVED_STANDARD_LICENSE;dependency=approved['path']
        archive=Path(os.environ['SV08_GCODEVIEWER_ARCHIVE'])
        package={k:approved[k] for k in ('name','version','integrity','license')}
        verified=inv.verify_npm_standard_license(approved,package,archive)
        inputs,root=self.deb_fixture();record=dict(self.record,roots=[root])
        config=inv.REPO/'configs/host/npm-standard-license-texts.json'
        pin=dict(root=str(config.parent),path=config.name,sha256=inv.sha(config))
        lock=self.base/'lock.json';lock.write_text(json.dumps({'packages':{dependency:package}}))
        inputs['mainsail']=dict(root=str(self.base),path=lock.name,sha256=inv.sha(lock),standard_license_texts=pin)
        path=self.base/'inventory.json'
        inventory={'applications':[],'mainsail_dependencies':{'packages':[{'path':dependency,'standard_license_texts':[verified]}],
            'notice_coverage':{'declaration_only_dependencies':0}}}
        def run():
            path.write_text(json.dumps(inputs))
            return m.prepare(self.image,self.public,inventory_inputs=path)
        with patch.object(m,'inspect_artifact',return_value=record),patch.object(inv,'generate',return_value=inventory):
            result=run();text=inv.REPO/approved['license_text']['path']
            self.assertEqual(result[text.name],text.read_bytes())
            self.assertEqual(result['npm-standard-license-texts.json'],config.read_bytes())
            output=self.base/'standard-package';m.write_package(output,result)
            manifest=json.loads((output/'release-manifest.json').read_bytes())
            for name in (text.name,'npm-standard-license-texts.json'):
                self.assertEqual(inv.sha(output/name),manifest['files'][name])
                self.assertEqual((output/name).read_bytes(),result[name])
            inventory['mainsail_dependencies']['packages'][0]['standard_license_texts']=[]
            with self.assertRaisesRegex(ValueError,'qualified inventory'):run()
            inventory['mainsail_dependencies']['packages'][0]['standard_license_texts']=[verified]
            pin['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'hash mismatch'):run()
            pin['sha256']=inv.sha(config);pin['path']='missing.json'
            with self.assertRaises(ValueError):run()
            pin.update(root=str(config.parent),path=config.name,sha256=inv.sha(config))
            # Exercise the actual repository text reads and exporter, including a
            # valid copy, altered full text and a missing standard document.
            repository=self.base/'repository'
            relative='configs/apps/mainsail.json'
            copied_config=repository/relative;copied_config.parent.mkdir(parents=True)
            copied_config.write_bytes((inv.REPO/relative).read_bytes())
            copied_text=repository/approved['license_text']['path'];copied_text.parent.mkdir(parents=True)
            copied_text.write_bytes(text.read_bytes())
            with patch.object(inv,'REPO',repository):
                self.assertEqual(run()[text.name],text.read_bytes())
                copied_text.write_bytes(text.read_bytes()+b'altered')
                with self.assertRaisesRegex(ValueError,'text bytes'):run()
                copied_text.unlink()
                with self.assertRaises(ValueError):run()
            fake=self.base/'fake.json';value=json.loads(config.read_bytes());value['records'][0]['source']['source_revision']='a'*40
            fake.write_text(json.dumps(value));pin.update(root=str(self.base),path=fake.name,sha256=inv.sha(fake))
            with self.assertRaisesRegex(ValueError,'Unapproved'):run()

    def test_profiles_require_all_applicable_inputs(self):
        with self.assertRaisesRegex(ValueError,'requires inventory'):m.prepare(self.image,self.public)
        with self.assertRaises(ValueError):m.prepare(self.image,self.public,profile='unknown')
        with self.assertRaises(ValueError):m.prepare(self.image,self.public,profile='project-source',inventory_inputs='unused')
        with self.assertRaises(OSError):m.prepare(self.base/'absent',self.base/'absent',profile='project-source')

if __name__=='__main__':unittest.main()
