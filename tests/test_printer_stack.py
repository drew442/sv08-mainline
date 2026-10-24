"""Complete software configuration: source resolution, print protections and real parser."""
import base64
import copy
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_catalog import Catalog,empty_draft,digest
from sv08_printer_definitions import builtins
from sv08_printer_compose import select_definition,apply_inputs
from sv08_printer_generate import generate
from sv08_printer_stack import archive,MOONRAKER
from sv08_printer_publish import Publisher,inventory,validate_output


def factory(calibrated=False):
    catalog=Catalog(ROOT/'catalog/printer/catalog.json');records=builtins(catalog)
    record=next(d for d in records if d['id']=='sv08.factory')
    draft=empty_draft();draft['boards']={r:dict(id='sv08-'+r,transport='serial',identity='/dev/null',reference_ack=True) for r in ('main','tool')}
    snapshots={'builtin::'+r['id']+'@'+r['version']:r for r in records}
    draft=select_definition(catalog,draft,dict(source='builtin',id=record['id'],version=record['version'],sha256=digest(record),commit=catalog.revision),snapshots)
    if calibrated:next(d for d in draft['devices'] if d['kind']=='probe')['settings']['z_offset']=.25 # disposable software fixture only
    return catalog,draft


class CalibrationPersistence(unittest.TestCase):
    def setUp(self):
        from test_printer_configuration import PersistenceTests
        PersistenceTests.setUp(self)
    def tearDown(self):self.tmp.cleanup()
    def request(self,**request):
        status=self.service.request({'action':'status'})
        request.setdefault('expected_identity',status['loaded_identity'])
        if request['action'] in ('save','component'):request.setdefault('expected_revision',status['state']['revision'])
        return self.service.request(request)
    def state(self):return self.service.request({'action':'status'})['state']
    def prepare(self):
        review=self.request(action='review',mode='full')
        self.request(action='apply',mode='full',review=review['review'])
        return review
    def test_calibration_edit_clear_reload_regenerate_and_component_preview(self):
        catalog,draft=factory()
        draft['definition_plan'].setdefault('instance_values',{})['probe.z_offset']=.25
        self.request(action='save',draft=draft);self.prepare()
        before=self.state();live=(self.view/'printer.cfg').read_bytes() if (self.view/'printer.cfg').exists() else None
        edited=copy.deepcopy(before['draft'])
        next(d for d in edited['devices'] if d['kind']=='probe')['settings']['z_offset']=.4
        edited['definition_plan']['instance_values']['probe.z_offset']=.4
        self.assertEqual(self.state(),before)
        self.request(action='save',draft=edited)
        self.assertEqual(self.state()['current'],before['current'])
        review=self.prepare();self.assertTrue(review['printing_enabled']);self.assertIn('z_offset: 0.4',review['text'])
        measured=self.state();self.assertEqual(measured['previous'],before['current'])
        cleared=copy.deepcopy(measured['draft']);next(d for d in cleared['devices'] if d['kind']=='probe')['settings'].pop('z_offset')
        cleared['definition_plan']['instance_values']['probe.z_offset']=None
        self.request(action='save',draft=cleared)
        self.assertIsNone(self.state()['draft']['definition_plan']['instance_values']['probe.z_offset'])
        self.assertEqual(self.state()['current'],measured['current'])
        review=self.prepare();self.assertTrue(review['complete']);self.assertFalse(review['printing_enabled']);self.assertIn('z_offset: 0',review['text'])
        self.request(action='save',draft=edited);before=self.state()
        replacement=self.request(action='component',draft=before['draft'],role='main',preset='bed_assembly')['draft']
        self.assertEqual(self.state(),before)
        self.assertIsNone(replacement['definition_plan']['instance_values']['probe.z_offset'])
        self.assertNotIn('z_offset',next(d for d in replacement['devices'] if d['kind']=='probe')['settings'])
        pending=generate(catalog,replacement,'full')
        self.assertTrue(pending['complete'],pending['blockers']);self.assertFalse(pending['printing_enabled'])
        self.assertIn('control: watermark',pending['text']);self.assertNotIn('pid_kp:',pending['text'])
        self.assertEqual(replacement['definition_plan']['snapshots'],before['draft']['definition_plan']['snapshots'])
        self.assertEqual(replacement['definition_plan']['runtime_assets'],before['draft']['definition_plan']['runtime_assets'])
        # Legacy profiles without a native definition pin only the explicitly
        # selected catalogue profile; missing fitted sensor facts stay missing.
        legacy=self.request(action='component',draft=before['draft'],role='main',preset='funssor_cn3d_bed')['draft']
        generated=generate(catalog,legacy,'full');self.assertFalse(generated['complete'])
        self.assertTrue(any('curve' in blocker for blocker in generated['blockers']))
        original_assets=before['draft']['definition_plan']['runtime_assets']
        for board in legacy['definition_plan']['runtime_assets']['boards']:
            prior=next(b for b in original_assets['boards'] if b['id']==board['id'])
            self.assertEqual({k:v for k,v in board.items() if k!='presets'},{k:v for k,v in prior.items() if k!='presets'})
            if board['role']=='main':self.assertEqual(board['presets'],[next(p for p in catalog.boards[board['id']]['presets'] if p['id']=='funssor_cn3d_bed')])
            else:self.assertEqual(board,prior)
        with self.assertRaisesRegex(ValueError,'Unknown component'):self.request(action='component',draft=before['draft'],role='tool',preset='bed_assembly')
        incompatible=copy.deepcopy(before['draft'])
        board=next(b for b in incompatible['definition_plan']['runtime_assets']['boards'] if b['role']=='main')
        board['source']['revision']='0'*40
        with self.assertRaisesRegex(ValueError,'pinned board mapping'):self.request(action='component',draft=incompatible,role='main',preset='bed_assembly')
        self.assertEqual(self.state(),before)
        self.assertEqual((self.view/'printer.cfg').read_bytes() if (self.view/'printer.cfg').exists() else None,live)

    def test_saved_component_choices_remain_available_without_repinning(self):
        catalog,draft=factory()
        self.request(action='save',draft=draft)
        before=copy.deepcopy(self.state()['draft']['definition_plan'])
        loaded=self.service.request({'action':'status'})
        self.assertTrue(all(not b['presets'] for b in loaded['catalog']['boards'] if b['id'] in ('sv08-main','sv08-tool')))
        choices=loaded['available_components']
        for board,preset in [('sv08-main','bed_assembly'),('sv08-tool','hotend_assembly'),('sv08-main','exhaust_fan')]:
            self.assertIn(preset,{p['id'] for p in choices[board]})
        for role,preset in [('main','bed_assembly'),('tool','hotend_assembly'),('main','exhaust_fan')]:
            changed=self.request(action='component',draft=self.state()['draft'],role=role,preset=preset)['draft']
            self.request(action='save',draft=changed)
            reloaded=self.service.request({'action':'status'})
            self.assertIn(preset,{p['id'] for p in reloaded['available_components']['sv08-'+role]})
            plan=reloaded['state']['draft']['definition_plan']
            self.assertEqual(plan['runtime_assets'],before['runtime_assets'])
            self.assertEqual(plan['snapshots'],before['snapshots'])
        # A newer incompatible current source never becomes a pinned board choice.
        self.c.boards['sv08-main']['source']['revision']='0'*40
        loaded=self.service.request({'action':'status'})
        self.assertNotIn('sv08-main',loaded['available_components'])
        with self.assertRaisesRegex(ValueError,'pinned board mapping'):
            self.request(action='component',draft=loaded['state']['draft'],role='main',preset='bed_assembly')
        self.assertEqual(self.state()['draft']['definition_plan']['runtime_assets'],before['runtime_assets'])

    def test_temperature_save_import_and_generate_guardrails(self):
        catalog,draft=factory()
        for expanded in (False,True):
            candidate=apply_inputs(draft,catalog) if expanded else copy.deepcopy(draft)
            bed=next(d for d in candidate['devices'] if d['kind']=='bed')
            sensor=next(d for d in candidate['devices'] if d['name']==bed['settings']['sensor'])
            sensor['settings']['max_temp']=120
            self.request(action='save',draft=candidate)
            saved=self.state();self.assertEqual(next(d for d in saved['draft']['devices'] if d['name']==sensor['name'])['settings']['max_temp'],120)
            self.assertTrue(generate(catalog,saved['draft'],'setup')['complete'])
            sensor['settings']['max_temp']=1200
            for action in ('save','import'):
                with self.assertRaisesRegex(ValueError,'supported-FDM'):
                    self.request(action=action,draft=candidate,expected_revision=saved['revision'])
            with self.assertRaisesRegex(ValueError,'supported-FDM'):generate(catalog,candidate,'full')
            self.assertEqual(self.state(),saved)

    def test_funssor_120_with_factory_curve_remains_a_local_modification(self):
        catalog,draft=factory()
        selected=self.request(action='component',draft=draft,role='main',preset='funssor_cn3d_bed')['draft']
        sensor=next(d for d in selected['devices'] if d['kind']=='sensor' and d['board']=='main')
        sensor['settings'].update(curve='sovol-bed',max_temp=120)
        for candidate in (selected,apply_inputs(selected,catalog)):
            catalog.validate(candidate)
            self.request(action='save',draft=candidate)
            generated=generate(catalog,self.state()['draft'],'setup')
            self.assertTrue(generated['complete'],generated['blockers'])
            self.assertIn('max_temp: 120',generated['text'])
            self.assertEqual(next(c for c in candidate['definition_plan']['runtime_assets']['curves'] if c['id']=='sovol-bed')['reference_bounds'],[5,105])

    def test_legacy_geometry_replacements_invalidate_probe_but_fans_preserve_it(self):
        catalog,draft=factory(True);draft['definition_plan']['instance_values']={'probe.z_offset':.25}
        self.request(action='save',draft=draft);before=self.state()
        for role,preset,sensitive in [('tool','hotend_assembly',True),('main','stepper_x',True),('main','exhaust_fan',False)]:
            with self.subTest(role=role,preset=preset):
                # Exercise compatibility fallback when this profile has no native
                # definition available; catalogue presets themselves stay pinned.
                records=[d for d in builtins(catalog) if d['id']!='sv08-'+role+'.'+preset]
                with patch('sv08_printer_store.builtins',return_value=records):
                    changed=self.request(action='component',draft=draft,role=role,preset=preset)['draft']
                effective=apply_inputs(changed,catalog)
                self.assertEqual(next(d for d in effective['devices'] if d['kind']=='probe')['settings'].get('z_offset'),None if sensitive else .25)
                self.assertEqual(changed['definition_plan']['instance_values']['probe.z_offset'],None if sensitive else .25)
                self.assertEqual(changed['definition_plan']['snapshots'],draft['definition_plan']['snapshots'])
                self.assertEqual(self.state(),before)

    @unittest.skipUnless(os.environ.get('SV08_PRINTER_VALIDATION_PYTHON'),'Pinned parser environment required')
    def test_stock_component_full_without_pid_reaches_real_parser_ready(self):
        catalog,draft=factory(True)
        draft['definition_plan']['instance_values']={'probe.z_offset':.25}
        self.request(action='save',draft=draft)
        source=Path(os.environ['SV08_PRINTER_SOURCE_ROOT'])
        for role,preset in [('main','bed_assembly'),('tool','hotend_assembly'),('main','stepper_x')]:
            with self.subTest(role=role,preset=preset):
                changed=self.request(action='component',draft=draft,role=role,preset=preset)['draft']
                output=generate(catalog,changed,'full')
                self.assertTrue(output['complete']);self.assertFalse(output['printing_enabled'])
                self.assertNotIn('pid_kp:',output['text']);self.assertIn('z_offset: 0',output['text'])
                with tempfile.TemporaryDirectory() as tmp:
                    for name,value in output['files'].items():(Path(tmp)/name).write_text(value)
                    preview=dict(files={},review='export',activation=output['files']['printer.cfg'])
                    result=validate_output(preview,Path(tmp),os.environ['SV08_PRINTER_VALIDATION_PYTHON'],str(source/'upstream/klipper/klippy/klippy.py'),str(source/'artifacts/test-sv08-01-mcu-usb-v1/klipper.dict'))
                    self.assertTrue(result['validated']);self.assertFalse(result['physical_hardware'])


class SelectedComponentContract(unittest.TestCase):
    def test_browser_selection_uses_active_closure_and_replacements(self):
        # Execute the production resolver with genuine factory source records.
        # Historical snapshots and replaced dependency records must not select it.
        catalog,draft=factory()
        source=(ROOT/'ui/printer/app.js').read_text()
        function=source[source.index('    function activeComponentPresets()'):source.index('    function renderComponents()')]
        native=copy.deepcopy(draft)
        replaced=copy.deepcopy(draft)
        plan=replaced['definition_plan'];key=next(k for k,d in plan['snapshots'].items() if d['id']=='sv08-main.bed_assembly')
        original=plan['snapshots'][key];custom=copy.deepcopy(original);custom['id']='custom-bed'
        ref=dict(source='local',id=custom['id'],version=custom['version'],sha256=digest(custom),commit='fixture')
        plan.setdefault('replacements',{})[key]=ref
        plan['snapshots']['local::'+custom['id']+'@'+custom['version']]=custom
        inactive=copy.deepcopy(native);inactive['definition_plan']['selections']=[]
        script='const cases='+json.dumps([native,replaced,inactive])+';let draft;'+function+';process.stdout.write(JSON.stringify(cases.map(value=>{draft=value;return [...activeComponentPresets()]})));'
        result=subprocess.run([os.environ.get('SV08_NODE','node')],input=script,capture_output=True,text=True,check=True)
        selected=json.loads(result.stdout)
        self.assertIn('sv08-main.bed_assembly',selected[0])
        self.assertNotIn('sv08-main.bed_assembly',selected[1])
        self.assertIn('sv08-tool.hotend_assembly',selected[1])
        self.assertEqual(selected[2],[])
    def test_production_calibration_projection_preserves_unrelated_edits_and_explicit_intent(self):
        catalog,draft=factory()
        draft['native_calibration']={'records':{'probe':{'z_offset':'0.000'},'heater_bed':{'control':'pid','pid_kp':'20','pid_ki':'1','pid_kd':'50'}}}
        source=(ROOT/'ui/printer/app.js').read_text()
        functions=source[source.index("    const calibrationFields="):source.index('    function renderCalibration()')]
        functions+=source[source.index('    function inputValue('):source.index('    function componentChanges()')]
        script='const seed='+json.dumps(draft)+";const copy=v=>JSON.parse(JSON.stringify(v));let draft,saved,changed;let nonce=0;const crypto={randomUUID:()=> (++nonce).toString(16).padStart(32,'0')};const document={querySelectorAll:()=>[]};let nativeCalibrationStatus={values:seed.native_calibration.records};"+functions+"""
        function reset(){draft=copy(seed);saved={draft:copy(seed)};changed=false;}
        function check(value,message){if(!value)throw Error(message);}
        reset();let probe=draft.devices.find(d=>d.kind==='probe');
        check(calibrationValue(probe,'z_offset')===0,'persisted native zero');
        check(instanceFieldValue('heater_bed','control')==='pid','native PID control in advanced field');
        draft.devices.find(d=>d.kind==='fan').settings.max_power=.8;changed=true;
        check(calibrationValue(probe,'z_offset')===0,'unrelated dirty fan does not hide zero');
        setInstanceField('heater_bed','pid_kp',30);
        check(instanceFieldValue('heater_bed','control')==='pid','gain edit retains PID control');
        check(instanceFieldValue('heater_bed','pid_kp')===30&&instanceFieldValue('heater_bed','pid_ki')===1&&instanceFieldValue('heater_bed','pid_kd')===50,'coherent PID tuple');
        check(calibrationValue(probe,'z_offset')===0,'PID marker does not invalidate probe');
        setInstanceField('heater_bed','control','watermark');
        check(instanceFieldValue('heater_bed','control')==='watermark','intentional watermark effective');
        reset();probe=draft.devices.find(d=>d.kind==='probe');setInstanceField('probe','z_offset',undefined);
        check(calibrationValue(probe,'z_offset')===undefined&&draft.calibration_edits['probe.z_offset'].value===null,'generic clear of absent base value');
        reset();probe=draft.devices.find(d=>d.kind==='probe');setCalibration(probe,'z_offset',.4);
        check(calibrationValue(probe,'z_offset')===.4,'explicit manual value retained');
        reset();probe=draft.devices.find(d=>d.kind==='probe');setInstanceField('probe','pin',probe.settings.pin+'-different');
        check(calibrationValue(probe,'z_offset')===undefined,'changed hardware does not inherit native zero');
        process.stdout.write('calibration projection cases passed');
        """
        result=subprocess.run([os.environ.get('SV08_NODE','node')],input=script,capture_output=True,text=True,check=True)
        self.assertIn('projection cases passed',result.stdout)

    def test_supported_v2_shareable_export_redacts_mirror_and_never_falls_back_to_history(self):
        catalog,draft=factory();draft['custom_config']='PRIVATE_CUSTOM_TEXT';draft['native_calibration']={'context':{'generation':'PRIVATE_GENERATION'}}
        draft['definition_plan']['instance_values']={'main.identity':'PRIVATE_INPUT_ID','probe.z_offset':0}
        source=(ROOT/'ui/printer/app.js').read_text();start=source.index('    function shareableDraft(state)');end=source.index('\n',source.index("    $('export').onclick=",start))
        functions=source[start:end]
        script='let draft='+json.dumps(draft)+";const saved={private_history:'PRIVATE_HISTORY'},catalog={};let output;const button={};const $=()=>button;const download=(name,data)=>{output={name,data:JSON.parse(data)}};"+functions+"""
        for(const version of [1,2]){
            draft.format_version=version;button.onclick();
            if(output.name!=='printer-hardware-draft.json')throw Error('supported draft fell into diagnostic export');
            const text=JSON.stringify(output.data);
            for(const value of ['PRIVATE_INPUT_ID','PRIVATE_CUSTOM_TEXT','PRIVATE_GENERATION','PRIVATE_HISTORY','/dev/null'])if(text.includes(value))throw Error('private value exported: '+value);
            if('native_calibration' in output.data)throw Error('mirror crossed export boundary');
        }
        draft.format_version=3;button.onclick();
        if(output.name!=='printer-hardware-diagnosis.json'||output.data.state.private_history!=='PRIVATE_HISTORY')throw Error('unsupported diagnostic changed');
        process.stdout.write('v1/v2 redacted; future diagnosis private');
        """
        result=subprocess.run([os.environ.get('SV08_NODE','node')],input=script,capture_output=True,text=True,check=True)
        self.assertIn('v1/v2 redacted',result.stdout)



class StackTests(unittest.TestCase):
    def test_factory_complete_closed_bundle_and_print_integration(self):
        catalog,draft=factory(True);original=copy.deepcopy(draft);output=generate(catalog,draft,'full')
        self.assertTrue(output['complete']);self.assertTrue(output['printing_enabled']);self.assertEqual(draft,original)
        contents=output['files'];self.assertEqual(contents['moonraker.conf'],(Path(os.environ.get('SV08_PRINTER_SOURCE_ROOT', str(ROOT)))/'configs/host-os/moonraker.conf').read_text())
        for required in ('virtual_sdcard','pause_resume','display_status','respond','exclude_object','gcode_macro PAUSE','gcode_macro RESUME','gcode_macro CANCEL_PRINT','gcode_macro PRINT_START','gcode_macro PRINT_END','gcode_macro M106','gcode_macro M107'):
            self.assertIn('['+required+']',output['text'])
        self.assertIn('QUAD_GANTRY_LEVEL\n  G28 Z',output['text']);self.assertIn('BED_MESH_CALIBRATE',output['text'])
        self.assertIn('Requested temperatures exceed selected hardware limits',output['text'])
        self.assertIn('proxy_set_header Host $http_host;',contents['nginx-mainsail.conf'])
        self.assertEqual(json.loads(contents['mainsail.json'])['instancesDB'],'moonraker')
        self.assertIn('FAN=part_cooling_front',output['text']);self.assertIn('FAN=part_cooling_rear',output['text']);self.assertNotIn('FAN=exhaust_fan',output['text'])
        with tempfile.TemporaryDirectory() as tmp:
            for n,v in contents.items():(Path(tmp)/n).write_text(v)
            _,names=inventory(Path(tmp));self.assertIn('extruder',names);self.assertIn('virtual_sdcard',names)
        with ZipFile(BytesIO(archive(contents))) as z:
            self.assertEqual(len(z.namelist()),len(contents));self.assertEqual(archive(contents),archive(contents))
        import hashlib
        for n,h in json.loads(contents['configuration-manifest.json'])['files'].items():self.assertEqual(hashlib.sha256(contents[n].encode()).hexdigest(),h)

    def test_setup_is_complete_without_borrowed_calibration_and_blocks_printing(self):
        catalog,draft=factory();original=copy.deepcopy(draft)
        next(d for d in draft['devices'] if d['kind']=='bed')['settings']['control']='pid'
        changed=copy.deepcopy(draft);full=generate(catalog,draft,'full');self.assertFalse(full['complete'])
        self.assertTrue(any('pid_' in s for s in full['blockers']))
        output=generate(catalog,draft,'setup');self.assertTrue(output['complete']);self.assertFalse(output['printing_enabled']);self.assertEqual(draft,changed)
        self.assertNotIn('pid_kp:',output['text']);self.assertIn('control: watermark',output['text']);self.assertIn('z_offset: 0',output['text'])
        for command in ('PRINT_START','M24','SDCARD_PRINT_FILE','RESUME'):
            section=output['text'].split('[gcode_macro '+command+']',1)[1].split('\n[',1)[0]
            self.assertIn('action_raise_error',section)
        self.assertTrue(output['setup_requirements']);self.assertEqual(original['geometry'],draft['geometry'])

    def test_full_uses_sourced_start_before_local_calibration(self):
        catalog,draft=factory();original=copy.deepcopy(draft)
        output=generate(catalog,draft,'full')
        self.assertTrue(output['complete']);self.assertFalse(output['printing_enabled'])
        self.assertEqual(draft,original);self.assertIn('z_offset: 0',output['text'])
        self.assertNotIn('z_offset: 1.0',output['text'])
        self.assertTrue(json.loads(output['files']['configuration-manifest.json'])['probe_calibration_pending'])
        for command in ('PRINT_START','M24','SDCARD_PRINT_FILE','RESUME'):
            self.assertIn('action_raise_error',output['text'].split('[gcode_macro '+command+']',1)[1].split('\n[',1)[0])

    def test_explicit_fan_roles_override_legacy_semantics(self):
        catalog,draft=factory(True)
        for d in draft['devices']:
            if d['kind']=='fan':d['settings']['print_fan']=d['name']=='exhaust_fan'
        text=generate(catalog,draft,'full')['text'];self.assertIn('FAN=exhaust_fan',text);self.assertNotIn('FAN=part_cooling',text)

    def test_universal_zero_input_default_is_not_reported_manual_calibration(self):
        catalog,draft=factory();plan=draft['definition_plan']
        record=next(d for d in plan['snapshots'].values() if d['id']=='sv08-tool.probe')
        for inp in record['inputs'].values():
            if inp['target']=='probe.z_offset':inp['default']=0
        for definition in plan['snapshots'].values():
            for dep in definition.get('dependencies',[]):
                target=dep.get('source','builtin')+'::'+dep['id']+'@'+dep['version']
                if target in plan['snapshots']:dep['sha256']=digest(plan['snapshots'][target])
        for ref in plan['selections']:ref['sha256']=digest(plan['snapshots'][ref['source']+'::'+ref['id']+'@'+ref['version']])
        # Exercise the actual selection/materialization path, then a retained
        # instance value equal to the publisher default. Neither is local intent.
        from sv08_printer_compose import select_definition
        ref=plan['selections'][0];snapshots=copy.deepcopy(plan['snapshots'])
        initial=empty_draft();initial['boards']=copy.deepcopy(draft['boards'])
        selected=select_definition(catalog,initial,ref,snapshots)
        selected['definition_plan'].setdefault('instance_values',{})['probe.z_offset']=0
        output=generate(catalog,selected,'full')
        self.assertTrue(output['complete'],output['blockers']);self.assertFalse(output['printing_enabled'])
        self.assertEqual(output['manual_calibration'],{});self.assertNotIn('#*# z_offset',output['files']['printer.cfg'])
        selected['format_version']=2;selected['calibration_edits']={'probe.z_offset':{'value':0,'nonce':'a'*32}}
        explicit=generate(catalog,selected,'full');self.assertTrue(explicit['printing_enabled'])
        self.assertEqual(explicit['manual_calibration']['probe']['z_offset'],'0')

    def test_sensors_stay_output_free_and_do_not_gain_print_stack(self):
        from test_printer_configuration import sensor_draft
        result=generate(Catalog(ROOT/'catalog/printer/catalog.json'),sensor_draft(),'sensors')
        self.assertTrue(result['complete']);self.assertNotIn('files',result);self.assertNotIn('[virtual_sdcard]',result['text'])

    @unittest.skipUnless(os.environ.get('SV08_PRINTER_VALIDATION_PYTHON'),'Pinned parser environment required')
    def test_real_factory_setup_and_full_closed_output_reach_ready(self):
        source=Path(os.environ['SV08_PRINTER_SOURCE_ROOT']);python=os.environ['SV08_PRINTER_VALIDATION_PYTHON']
        for mode in ('setup','full'):
            catalog,draft=factory(mode=='full');output=generate(catalog,draft,mode)
            with tempfile.TemporaryDirectory() as tmp:
                for n,v in output['files'].items():(Path(tmp)/n).write_text(v)
                preview=dict(files={},review='export',activation=output['files']['printer.cfg'])
                result=validate_output(preview,Path(tmp),python,str(source/'upstream/klipper/klippy/klippy.py'),str(source/'artifacts/test-sv08-01-mcu-usb-v1/klipper.dict'))
                self.assertTrue(result['validated']);self.assertFalse(result['physical_hardware'])

    @unittest.skipUnless(os.environ.get('SV08_PRINTER_VALIDATION_PYTHON'),'Pinned parser environment required')
    def test_setup_guard_commands_in_real_klipper_do_not_submit_printing(self):
        source=Path(os.environ['SV08_PRINTER_SOURCE_ROOT']);python=os.environ['SV08_PRINTER_VALIDATION_PYTHON'];catalog,draft=factory()
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);output=generate(catalog,draft,'setup')
            for n,v in output['files'].items():(work/n).write_text(v)
            dictionary=str(source/'artifacts/test-sv08-01-mcu-usb-v1/klipper.dict')
            args=[python,str(source/'upstream/klipper/klippy/klippy.py'),str(work/'printer.cfg'),'-I',str(work/'tty'),'-a',str(work/'api'),'-o',str(work/'mcu.out'),'-d',dictionary,'-d','tool='+dictionary,'-l',str(work/'klippy.log')]
            with (work/'process.log').open('w') as log:
                child=subprocess.Popen(args,stdout=log,stderr=log,env={**os.environ,'MALLOC_ARENA_MAX':'1'})
                try:
                    def request(method,params):
                        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as api:
                            api.settimeout(2);api.connect(str(work/'api'));api.sendall(json.dumps(dict(id=1,method=method,params=params)).encode()+b'\x03');reply=b''
                            while b'\x03' not in reply:reply+=api.recv(65536)
                            return json.loads(reply.split(b'\x03')[0])
                    for _ in range(100):
                        if (work/'api').exists() and request('info',{}).get('result',{}).get('state')=='ready':break
                        time.sleep(.05)
                    else:self.fail('Klipper did not reach ready')
                    for command in ('PRINT_START BED_TEMP=60 EXTRUDER_TEMP=200','SDCARD_PRINT_FILE FILENAME=example.gcode','M24','RESUME'):
                        result=request('gcode/script',dict(script=command));self.assertIn('Setup configuration',result['error']['message'])
                    self.assertEqual(request('info',{})['result']['state'],'ready')
                finally:
                    child.terminate()
                    try:child.wait(timeout=2)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
