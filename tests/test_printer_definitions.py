import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_catalog import Catalog,empty_draft,digest
from sv08_printer_definitions import builtins,validate_definition,public_json,resolve
from sv08_printer_compose import select_definition,validate_plan,migration_preview,remap_board,remove_definition
from sv08_printer_sources import GitHub,accept_source,bundle_preview,repository

class Definitions(unittest.TestCase):
    def setUp(self):
        self.c=Catalog(ROOT/'catalog/printer/catalog.json');self.records=builtins(self.c)
        self.bed=copy.deepcopy(next(d for d in self.records if d['id']=='sv08-main.bed_assembly'))
        self.ref=dict(source='builtin',id=self.bed['id'],version=self.bed['version'],sha256=digest(self.bed),commit=self.c.revision)
        self.snapshots={'builtin::'+self.bed['id']+'@'+self.bed['version']:self.bed}
        self.d=empty_draft();self.d['boards']['main']={'id':'sv08-main'}
    def test_factory_only_builtin_choices(self):
        self.assertTrue(self.records)
        self.assertTrue(all(d['id'].startswith(('sv08-main.','sv08-tool.','sv08.factory')) for d in self.records))
        self.assertFalse(any('funssor' in d['id'] for d in self.records))
    def test_all_builtins_public_schema_and_semantics(self):
        import jsonschema
        schema=json.loads((ROOT/'schemas/printer-definitions/v1/definition.schema.json').read_text())
        for d in self.records:validate_definition(d,self.c);jsonschema.validate(d,schema)
    def test_same_public_data_generates_same_bindings_across_origins(self):
        a=select_definition(self.c,self.d,self.ref,self.snapshots)
        ref={**self.ref,'source':'github:17:.'};snap={'github:17:.::'+self.bed['id']+'@'+self.bed['version']:self.bed}
        b=select_definition(self.c,self.d,ref,snap)
        self.assertEqual(a['devices'],b['devices']);self.assertEqual(self.d['devices'],[])
        self.assertEqual(a['devices'][0]['settings']['pin'],'PC5');self.assertEqual(a['devices'][0]['settings']['curve'],'sovol-bed')
    def test_legacy_alias_migration_preserves_identity_and_unknown_origin(self):
        self.d['devices']=[dict(name='bed_temperature',kind='sensor',board='main',settings={'pin':'PC5','curve':'sovol-bed'})]
        self.d['boards']['main'].update(transport='serial',identity='/dev/null')
        preview=migration_preview(self.d,self.c,self.records)
        self.assertEqual(preview['backup'],self.d);self.assertEqual(preview['draft']['boards'],self.d['boards'])
        self.assertEqual(preview['draft']['definition_plan']['selections'],[])
        selected=select_definition(self.c,self.d,self.ref,self.snapshots)
        self.assertNotIn('bed_temperature',[d['name'] for d in selected['devices']])
    def test_explicit_update_preserves_local_override_and_old_snapshot(self):
        selected=select_definition(self.c,self.d,self.ref,self.snapshots)
        selected['devices'][0]['settings']['max_temp']=90
        new=copy.deepcopy(self.bed);new['version']='0.3.0';new['components'][0]['settings']['max_temp']=100
        ref={**self.ref,'version':new['version'],'sha256':digest(new)}
        updated=select_definition(self.c,selected,ref,{'builtin::'+new['id']+'@'+new['version']:new})
        self.assertEqual(updated['devices'][0]['settings']['max_temp'],90)
        self.assertIn('builtin::'+self.bed['id']+'@'+self.bed['version'],updated['definition_plan']['snapshots'])
    def test_source_qualified_dependencies_and_digest_fail_closed(self):
        d=copy.deepcopy(self.bed);d['dependencies']=[dict(source='other',id=self.bed['id'],version=self.bed['version'],sha256=digest(self.bed))]
        r={**self.ref,'sha256':digest(d)}
        with self.assertRaisesRegex(ValueError,'unavailable'):resolve(r,{next(iter(self.snapshots)):d},self.c)
        with self.assertRaisesRegex(ValueError,'changed'):resolve({**self.ref,'sha256':'0'*64},self.snapshots,self.c)
    def test_conflicting_dependency_versions(self):
        v2=copy.deepcopy(self.bed);v2['version']='0.3.0'
        plan=dict(format_version=1,selections=[self.ref,{**self.ref,'version':'0.3.0','sha256':digest(v2)}],snapshots={**self.snapshots,'builtin::'+v2['id']+'@0.3.0':v2})
        with self.assertRaisesRegex(ValueError,'versions'):validate_plan(plan,self.c)
    def test_unknown_operational_fields_and_raw_code_are_rejected(self):
        for field in ('setup_script','raw_macros','python'):
            d=copy.deepcopy(self.bed);d[field]='danger'
            with self.assertRaises(ValueError):validate_definition(d,self.c)
        d=copy.deepcopy(self.bed);d['compatibility']['requires_capabilities']=['unknown.v1']
        with self.assertRaisesRegex(ValueError,'capability'):validate_definition(d,self.c)
        with self.assertRaisesRegex(ValueError,'Duplicate'):public_json(b'{"id":1,"id":2}')
        with self.assertRaisesRegex(ValueError,'nesting'):public_json(('['*30+'0'+']'*30).encode())
    def test_malformed_display_metadata_and_connections_are_unavailable(self):
        mutations=[lambda d:d.update(aliases={'bad':'shape'}),lambda d:d.update(inputs=[]),lambda d:d['compatibility'].update(boards='sv08-main'),lambda d:d['sources'][0].update(url=123),lambda d:d['connections'][0].update(capability='executable')]
        for mutate in mutations:
            bad=copy.deepcopy(self.bed);mutate(bad)
            with self.assertRaises(ValueError):validate_definition(bad,self.c)
    def test_board_remap_retains_semantic_devices_and_clears_identity(self):
        self.d['devices']=[dict(name='bed_temperature',kind='sensor',board='main',settings={'pin':'PC5','curve':'sovol-bed','pullup_resistor':4700})]
        self.d['boards']['main']['identity']='/dev/null'
        p=remap_board(self.d,'main','octopus-v1.1-non-pro',self.c)
        self.assertEqual(p['draft']['devices'][0]['name'],'bed_temperature');self.assertNotIn('identity',p['draft']['boards']['main']);self.assertNotIn('pin',p['draft']['devices'][0]['settings']);self.assertEqual(self.d['devices'][0]['settings']['pin'],'PC5')
    def test_local_bundle_and_immutable_version_check(self):
        root=ROOT/'examples/printer-definitions';m=json.loads((root/'catalog.json').read_text());bundle=dict(manifest=m,files={r['path']:base64.b64encode((root/r['path']).read_bytes()).decode() for r in m['definitions']})
        candidate=bundle_preview(bundle,self.c);accepted=accept_source({},candidate,self.c)
        changed=copy.deepcopy(candidate);key=next(iter(changed['file_hashes']));changed['file_hashes'][key]='0'*64
        with self.assertRaisesRegex(ValueError,'index/digest'):accept_source(accepted,changed,self.c)
        github={k:v for k,v in candidate.items() if k!='raw_files'};github.update(id='github:17:.',origin='github',repository_id=17,repository='test/kits',url='https://github.com/test/kits',path='catalog.json',ref='main',commit='a'*40)
        accepted=accept_source({},github,self.c);changed=copy.deepcopy(github)
        changed['file_hashes'][key]='0'*64
        for row in changed['manifest']['definitions']:
            if row['id']+'@'+row['version']==key:row['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'bump version'):accept_source(accepted,changed,self.c)
        impostor={**candidate,'id':'builtin'}
        with self.assertRaisesRegex(ValueError,'built-in'):accept_source({},impostor,self.c)
    def test_github_pins_single_commit_checks_modes_and_hashes(self):
        d=self.bed;raw=json.dumps(d).encode();h=hashlib.sha256(raw).hexdigest();manifest=dict(format_version='0.1',catalog_id='test',name='Creator',publisher={'name':'Creator'},license='GPL-3.0',definitions=[dict(id=d['id'],version=d['version'],path='bed.json',sha256=h)])
        mraw=json.dumps(manifest).encode();commit='a'*40;calls=[]
        replies={'/repos/test/kits':dict(id=17,default_branch='main',full_name='test/kits',private=False),'/repos/test/kits/commits/main':dict(sha=commit),'/repos/test/kits/git/commits/'+commit:dict(tree={'sha':'tree'}),'/repos/test/kits/git/trees/tree':dict(tree=[dict(path='catalog.json',mode='100644',type='blob',sha='manifest',size=len(mraw)),dict(path='bed.json',mode='100644',type='blob',sha='bed',size=len(raw))]),'/repos/test/kits/git/blobs/manifest':dict(encoding='base64',size=len(mraw),content=base64.b64encode(mraw).decode()),'/repos/test/kits/git/blobs/bed':dict(encoding='base64',size=len(raw),content=base64.b64encode(raw).decode())}
        def fetch(path):calls.append(path);return copy.deepcopy(replies[path])
        source=GitHub(fetch).preview('https://github.com/test/kits',self.c)
        self.assertEqual(source['commit'],commit);self.assertEqual(source['id'],'github:17:.');self.assertEqual(len(source['records']),1)
        self.assertFalse(any('/contents/' in path for path in calls))
        replies['/repos/test/kits/git/trees/tree']['tree'][1]['mode']='120000'
        with self.assertRaisesRegex(ValueError,'links'):GitHub(fetch).preview('https://github.com/test/kits',self.c)
    def test_check_only_policies_compose_independent_of_order_and_reject_contradiction(self):
        from test_printer_configuration import full_draft
        from sv08_printer_generate import generate
        draft=full_draft();records={};refs=[]
        for ident,comparison,threshold in [('fixture-lower','at_least',25),('fixture-upper','at_most',50)]:
            d=copy.deepcopy(self.bed);d.update(id=ident,kind='behaviour',category='probe',behaviours=[dict(hook='levelling.preconditions',operation='check',sensor='bed_check',comparison=comparison,threshold=threshold,abort='error',sources=['software-fixture'])]);d.pop('components');d.pop('connections')
            records['fixture::'+ident+'@0.2.0']=d;refs.append(dict(source='fixture',id=ident,version='0.2.0',sha256=digest(d),commit='a'*40))
        outputs=[]
        for order in [refs,list(reversed(refs))]:
            candidate=copy.deepcopy(draft);candidate['definition_plan']=dict(format_version=1,selections=order,snapshots=records)
            output=generate(self.c,candidate,'full');self.assertTrue(output['complete']);outputs.append(output['text'])
        self.assertEqual(*outputs);self.assertEqual(outputs[0].count('[gcode_macro SV08_LEVELLING_PRECONDITIONS]'),1)
        self.assertNotIn('M140',outputs[0]);self.assertNotIn('TEMPERATURE_WAIT',outputs[0])
        records['fixture::fixture-upper@0.2.0']['behaviours'][0]['threshold']=20
        refs[1]['sha256']=digest(records['fixture::fixture-upper@0.2.0'])
        with self.assertRaisesRegex(ValueError,'Conflicting levelling'):validate_plan(dict(format_version=1,selections=refs,snapshots=records),self.c)
    def test_multiple_factory_motors_fans_and_boards_coexist(self):
        draft=copy.deepcopy(self.d);draft['boards']['tool']={'id':'sv08-tool'}
        snapshots={'builtin::'+d['id']+'@'+d['version']:d for d in self.records}
        for d in self.records:
            if d['id']=='sv08.factory':continue
            if d['category'] not in ('motion','cooling','boards') or d['kind']!='board' and any(c['kind']=='sensor' for c in d.get('components',[])):continue
            draft=select_definition(self.c,draft,dict(source='builtin',id=d['id'],version=d['version'],sha256=digest(d),commit=self.c.revision),snapshots)
        self.assertEqual(len([d for d in draft['devices'] if d['kind']=='motor']),6)
        self.assertEqual(len([d for d in draft['devices'] if d['kind']=='fan']),3)
        self.assertEqual(len([r for r in draft['definition_plan']['selections'] if r['id'].endswith('.board')]),2)
    def test_source_board_definition_pins_mapping_offline(self):
        board=copy.deepcopy(next(d for d in self.records if d['kind']=='board' and d['mapping']['role']=='main'))
        board['id']='fixture-mainboard';board['mapping']['id']='fixture-main'
        ref=dict(source='fixture',id=board['id'],version=board['version'],sha256=digest(board),commit='a'*40)
        selected=select_definition(self.c,self.d,ref,{'fixture::'+board['id']+'@'+board['version']:board})
        self.assertEqual(selected['boards']['main']['id'],'fixture-main')
        from sv08_printer_compose import locked_catalog
        self.assertEqual(locked_catalog(selected,self.c).boards['fixture-main']['connectors'],board['mapping']['connectors'])
    def test_shared_dependency_removal_and_addition_preserve_override_and_calibration(self):
        bed=copy.deepcopy(self.bed);bed['id']='shared-bed'
        snap={'fixture::shared-bed@0.2.0':bed}
        selections=[]
        for ident,category in [('bundle-bed','bed'),('bundle-probe','probe')]:
            bundle=copy.deepcopy(bed);bundle.update(id=ident,category=category,components=[],connections=[],dependencies=[dict(id='shared-bed',version='0.2.0',sha256=digest(bed))])
            snap['fixture::'+ident+'@0.2.0']=bundle
            selections.append(dict(source='fixture',id=ident,version='0.2.0',sha256=digest(bundle),commit='a'*40))
        selected=select_definition(self.c,self.d,selections[0],snap)
        heater=next(d for d in selected['devices'] if d['kind']=='bed');heater['settings']['max_power']=.6;heater['settings'].update(pid_kp=1,pid_ki=2,pid_kd=3)
        shared=select_definition(self.c,selected,selections[1],snap)
        self.assertEqual(next(d for d in shared['devices'] if d['kind']=='bed')['settings'],heater['settings'])
        removed=remove_definition(self.c,shared,selections[0]);self.assertEqual(removed['devices'],shared['devices'])
        removed=remove_definition(self.c,removed,selections[1]);self.assertEqual(removed['devices'],[])
    def test_inputs_contribute_and_incomplete_definitions_fail_generation(self):
        from sv08_printer_generate import generate
        self.d['boards']['main'].update(transport='serial',identity='/dev/null',reference_ack=True)
        self.bed['components']=[c for c in self.bed['components'] if c['kind']=='sensor']
        self.bed['connections']=[c for c in self.bed['connections'] if c['capability']=='adc']
        self.bed['inputs']={'limit':dict(type='number',label='Fixture limit',target='bed_sensor.max_temp',default=95,required=True)}
        ref={**self.ref,'sha256':digest(self.bed)};snapshot={'builtin::'+self.bed['id']+'@0.2.0':self.bed}
        selected=select_definition(self.c,self.d,ref,snapshot)
        output=generate(self.c,selected,'sensors');self.assertTrue(output['complete']);self.assertIn('max_temp: 95',output['text'])
        selected['definition_plan']['instance_values']={'bed_sensor.max_temp':90}
        self.assertIn('max_temp: 90',generate(self.c,selected,'sensors')['text'])
        selected['devices']=[];output=generate(self.c,selected,'sensors');self.assertFalse(output['complete']);self.assertTrue(any('contribution removed' in x for x in output['blockers']))
    def test_repository_path_injection(self):
        for url in ['http://github.com/a/b','https://user@github.com/a/b','https://github.com/a/b?token=secret','https://evil.test/a/b','https://github.com/a/b/blob/main/catalog.json']:
            with self.assertRaises(ValueError):repository(url)

if __name__=='__main__':unittest.main()
