import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_catalog import Catalog, empty_draft, digest
from sv08_printer_definitions import builtins,validate_definition
from sv08_printer_compact import compile_records
from sv08_printer_sources import bundle_preview, accept_source, GitHub
from sv08_printer_compose import select_definition,locked_catalog
from sv08_printer_generate import generate

class CompactTests(unittest.TestCase):
    def setUp(self):
        self.c=Catalog(ROOT/'catalog/printer/catalog.json');self.factory=builtins(self.c)
        self.bed=dict(id='funssor-cn3d-hotbed',name='Funssor CN3D heated bed',version='1.0.0',extends='sv08.factory.hotbed',heater_bed=dict(max_temp=120))
    def compile(self,*records):
        compiled,errors=compile_records(list(records),self.c);self.assertEqual(errors,{});return compiled
    def select(self,record,draft=None):
        snap={'builtin::'+d['id']+'@'+d['version']:d for d in self.factory};snap['test::'+record['id']+'@'+record['version']]=record
        draft=copy.deepcopy(draft) if draft else empty_draft()
        for role in ('main','tool'):draft['boards'][role]=dict(id='sv08-'+role,transport='serial',identity='/dev/null',reference_ack=True)
        if not draft['devices']:
            factory=next(d for d in self.factory if d['id']=='sv08.factory')
            draft=select_definition(self.c,draft,dict(source='builtin',id=factory['id'],version=factory['version'],sha256=digest(factory),commit=self.c.revision),snap)
        selected=select_definition(self.c,draft,dict(source='test',id=record['id'],version=record['version'],sha256=digest(record),commit='a'*40),snap)
        next(d for d in selected['devices'] if d['kind']=='probe')['settings']['z_offset']=0
        return selected
    def test_exact_owner_example_changes_only_factory_temperature(self):
        d=self.compile(self.bed)[0];base=copy.deepcopy(next(d for d in self.factory if d['id']=='sv08-main.bed_assembly'))
        expected=copy.deepcopy(base['components']);expected[0]['settings']['max_temp']=120
        self.assertEqual(d['components'],expected);self.assertEqual(d['connections'],base['connections'])
        before=self.select(base);after=self.select(d,before)
        text=generate(self.c,after,'full')['text'];self.assertIn('max_temp: 120',text);self.assertEqual(text,generate(self.c,before,'full')['text'].replace('max_temp: 105','max_temp: 120').replace('bed >= 105','bed >= 120'))
        self.assertNotIn('pid_kp',text);self.assertEqual(len(after['devices']),len(before['devices']))
    def test_every_factory_definition_has_compact_inheritance(self):
        for base in self.factory:
            with self.subTest(base=base['id']):
                d=self.compile(dict(id='compact-'+base['id'],name=base['name'],version='1.0.0',extends=base['id']))[0]
                validate_definition(d,self.c)
                selected=self.select(d)
                output=generate(locked_catalog(selected,self.c),selected,'full')
                self.assertIsInstance(output['text'],str)
                if base['id']=='sv08.factory':self.assertEqual(len(selected['devices']),len(self.select(next(d for d in self.factory if d['id']=='sv08.factory'))['devices']))
    def test_section_vocabulary_for_every_device_kind(self):
        sections={'sensor':'temperature_sensor ','bed':'heater_bed','extruder':'extruder','motor':None,'input':'filament_switch_sensor ','fan':'fan_generic ','probe':'probe','pressure_switch':'gcode_button ','output':'output_pin ','display':'display','neopixel':'neopixel ','mcu_temperature':'temperature_sensor ','heater_fan':'heater_fan ','accelerometer':'adxl345 '}
        covered=set()
        for base in self.factory:
            for component in base.get('components',[]):
                kind=component['kind'];prefix=sections[kind];section=component['name'] if prefix is None else prefix+component['name'] if prefix.endswith(' ') else prefix
                settings={k:v for k,v in component['settings'].items() if k not in ('sensor','verify_max_error','verify_check_gain_time','verify_hysteresis','verify_heating_gain')}
                if kind=='mcu_temperature':settings['sensor_type']='temperature_mcu'
                if kind=='sensor':section='temperature_sensor '+component['name'];settings['sensor_type']=settings.pop('curve')
                record=dict(id='compact-'+base['id'],name='Compact',version='1.0.0',extends=base['id'],configuration={section:settings})
                self.compile(record);covered.add(kind)
        self.assertEqual(covered,set(self.c.kinds)-{'chamber'})
    def test_local_inheritance_bundle_and_offline_snapshot_retention(self):
        child={**self.bed,'id':'child','extends':'funssor-cn3d-hotbed','heater_bed':dict(max_temp=115)}
        records=self.compile(child,self.bed);self.assertEqual(records[0]['components'][0]['settings']['max_temp'],115)
        manifest=dict(format_version='0.1',catalog_id='mods',name='Mods',publisher={'name':'Modder'},license='GPL-3.0-or-later',definitions=[]);files={}
        for raw in (child,self.bed):
            path='definitions/'+raw['id']+'.json';data=json.dumps(raw).encode();files[path]=base64.b64encode(data).decode();manifest['definitions'].append(dict(id=raw['id'],version=raw['version'],path=path,sha256=hashlib.sha256(data).hexdigest()))
        source=bundle_preview(dict(manifest=manifest,files=files),self.c);self.assertFalse(source['unavailable']);accept_source({},source,self.c)
        selected=self.select(source['records'][0]);self.bed['heater_bed']['max_temp']=90
        self.assertIn('max_temp: 115',generate(self.c,selected,'full')['text'])
    def test_unknown_cycle_and_calibration_defaults_are_rejected(self):
        mutations=[{'extends':'unknown'},{'extends':'funssor-cn3d-hotbed'},{'heater_bed':{'pid_Kp':10}},{'heater_bed':{'max_tempp':120}},{'heater_bed':{'heater_pin':'tool:PA5'}},{'setup_script':'evil'},{'guide':'http://example.com'}]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                records,errors=compile_records([{**self.bed,**mutation}],self.c);self.assertFalse(records);self.assertIn(self.bed['id'],errors)
        cycle=[{**self.bed,'id':'a','extends':'b'},{**self.bed,'id':'b','extends':'a'}]
        self.assertEqual(set(compile_records(cycle,self.c)[1]),{'a','b'})
    def test_new_components_require_explicit_board_and_documented_connections(self):
        record=dict(id='my-fan',name='My fan',version='1.0.0',category='cooling',configuration={'fan_generic enclosure_fan':dict(board='sv08-main',pin='fan_generic fan3 / pin',invert=False,max_power=1)})
        fan=self.compile(record)[0];draft=empty_draft();draft['boards']['main']={'id':'sv08-main'};selected=select_definition(self.c,draft,dict(source='test',id=fan['id'],version=fan['version'],sha256=digest(fan),commit='a'*40),{'test::'+fan['id']+'@'+fan['version']:fan});self.assertEqual(next(d for d in selected['devices'] if d['name']=='enclosure_fan')['settings']['pin'],self.c.boards['sv08-main']['connectors']['fan_generic fan3 / pin']['pin'])
        record['configuration']['fan_generic enclosure_fan']['pin']='PA99';self.assertTrue(compile_records([record],self.c)[1])
    def test_new_chamber_supported_with_exact_board_and_control(self):
        board=next(b for b in self.c.boards.values() if b['role']=='chamber')
        # Build from documented module reference, without borrowing main/tool identities.
        preset=board['presets'][0]
        heater=next(d for d in preset['devices'] if d['kind']=='chamber');sensor=next(d for d in preset['devices'] if d['kind']=='sensor')
        connector=lambda pin,cap:next(n for n,c in board['connectors'].items() if c['pin']==pin and c['capability']==cap)
        settings={**heater['settings'],'heater_pin':connector(heater['settings']['pin'],'heater'),'sensor_pin':connector(sensor['settings']['pin'],'adc'),'sensor_type':sensor['settings']['curve'],'pullup_resistor':sensor['settings']['pullup_resistor'],'min_temp':sensor['settings']['min_temp'],'max_temp':sensor['settings']['max_temp'],'board':board['id']};settings.pop('pin');settings.pop('sensor')
        self.compile(dict(id='my-chamber',name='Chamber',version='1.0.0',category='cooling',configuration={'heater_generic chamber_temp':settings}))
    def test_klipper_wiring_names_match_documented_motor_display_and_sensor(self):
        board=self.c.boards['sv08-main'];motor=next(d for d in self.factory if d['id']=='sv08-main.stepper_x')
        connector=next(c for c in motor['connections'] if c['capability']=='motor')['connector'];pins=board['motors'][connector]
        values={k+'_pin':('!' if k=='dir' else '')+v for k,v in pins.items()}
        d=self.compile(dict(id='motor-mod',name='Motor',version='1.0.0',extends=motor['id'],configuration={'stepper_x':{k:v for k,v in values.items() if k!='uart_pin'},'tmc2209 stepper_x':{'uart_pin':values['uart_pin'],'run_current':.7}}))[0]
        self.assertTrue(d['components'][0]['settings']['invert_dir']);self.assertEqual(d['components'][0]['settings']['run_current'],.7)
        display=next(d for d in self.factory if d['id']=='sv08-main.display');connections={x['endpoint']:x for x in display['connections']}
        c=display['components'][0];pin=lambda field:board['connectors'][connections[c['endpoints'][field]]['connector']]['pin']
        d=self.compile(dict(id='display-mod',name='Display',version='1.0.0',extends=display['id'],display={'lcd_type':'uc1701','encoder_pins':'^'+pin('encoder_a')+', ^'+pin('encoder_b'),'click_pin':'^!'+pin('click_pin')}))[0]
        self.assertTrue(d['components'][0]['settings']['click_invert']);self.assertTrue(d['components'][0]['settings']['encoder_pullup'])
        for mutation in ({'heater_bed':{'min_temp':130,'max_temp':120}},{'heater_bed':{'sensor_type':'Not a sensor'}}):self.assertTrue(compile_records([{**self.bed,**mutation}],self.c)[1])
    def test_declared_sensor_swap_and_printer_settings(self):
        d=self.compile({**self.bed,'heater_bed':{'sensor_type':'PT1000','max_temp':120}})[0]
        self.assertEqual(self.c.curves[d['components'][0]['settings']['curve']]['sensor_type'],'PT1000')
        d=self.compile(dict(id='geometry-mod',name='Geometry',version='1.0.0',extends='sv08.factory.printer',configuration={'printer':{'max_velocity':300},'bed_mesh':{'speed':90}}))[0]
        self.assertEqual(d['printer_settings']['geometry']['max_velocity'],300);self.assertEqual(d['printer_settings']['bed_mesh']['speed'],90)
    def test_compact_schema_and_bounded_inheritance(self):
        import jsonschema
        schema=json.loads((ROOT/'schemas/printer-definitions/v1/compact.schema.json').read_text());jsonschema.validate(self.bed,schema)
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate({**self.bed,'setup_script':'evil'},schema)
        records=[{**self.bed,'id':'chain-'+str(i),'extends':'chain-'+str(i+1)} for i in range(14)];records.append({**self.bed,'id':'chain-14'})
        result,errors=compile_records(records,self.c);self.assertIn('chain-0',errors);self.assertIn('depth',errors['chain-0'])
    def test_advanced_supported_behaviour_and_board_mapping(self):
        b=dict(id='my-check',name='Check',version='1.0.0',category='bed',advanced={'behaviours':[dict(hook='levelling.preconditions',operation='none',sources=['author'])]})
        self.assertEqual(self.compile(b)[0]['kind'],'behaviour')
        base=next(d for d in self.factory if d['id']=='sv08-main.board');mapping=copy.deepcopy(base['mapping']);mapping['id']='my-main'
        board=self.compile(dict(id='my-board',name='Board',version='1.0.0',extends='sv08.factory.mainboard',advanced=dict(mapping=mapping)))[0]
        self.assertEqual(board['mapping']['id'],'my-main')
