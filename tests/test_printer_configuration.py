"""Focused offline catalog, generation, Store and durable fault tests."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_catalog import Catalog, empty_draft, strict_json
from sv08_printer_generate import generate
from sv08_printer_store import PrinterStore
from sv08_state import Store, snapshot

CATALOG=ROOT/'catalog/printer/catalog.json'


def primary_source(path):
    local=ROOT/path
    if local.is_file():return local
    return Path(os.environ.get('SV08_PRINTER_SOURCE_ROOT','/home/drew/sv08-mainline'))/path


def sensor_draft():
    return dict(format_version=1,boards={r:dict(id='sv08-'+('main' if r=='main' else 'tool'),transport='serial',identity='/dev/null',reference_ack=True) for r in ('main','tool')},geometry={},devices=[dict(name=n,kind='sensor',board=r,settings=dict(pin=p,curve=c,pullup_resistor=u,min_temp=5,max_temp=m)) for n,r,p,c,u,m in [('bed_check','main','PC5','sovol-bed',4700,105),('hotend_check','tool','PA5','sovol-hotend',11500,305)]])


def full_draft():
    d=sensor_draft();d['geometry']=dict(max_velocity=100,max_accel=1000,max_z_velocity=5,max_z_accel=50)
    c=Catalog(CATALOG)
    for name,conn in [('stepper_x','stepper_x'),('stepper_y','stepper_y'),('stepper_z','stepper_z'),('stepper_z1','stepper_z1'),('stepper_z2','stepper_z2'),('stepper_z3','stepper_z3'),('extruder','extruder')]:
        s=dict(connector=conn,invert_dir=False,invert_enable=True,microsteps=16,rotation_distance=40,run_current=.5,current_rating_rms=1.0,sense_resistor=.15,uart_address=3)
        if name in ('stepper_x','stepper_y','stepper_z'):s.update(position_min=0,position_max=350,homing_speed=10)
        if name in ('stepper_x','stepper_y'):s.update(position_endstop=0,endstop_pin='PE15' if name=='stepper_x' else 'PE13',endstop_invert=False,endstop_pullup=False)
        if name=='extruder':s.update(rotation_distance=6.5,pin='PB9',invert=False,sensor='hotend_check',max_power=.5,control='pid',pid_kp=33.838,pid_ki=5.223,pid_kd=47.752,nozzle_diameter=.4,filament_diameter=1.75,min_extrude_temp=150)
        d['devices'].append(dict(name=name,board='tool' if name=='extruder' else 'main',kind='extruder' if name=='extruder' else 'motor',settings=s))
    d['devices'].append(dict(name='heater_bed',board='main',kind='bed',settings=dict(pin='PA0',invert=False,sensor='bed_check',max_power=.5,control='pid',pid_kp=73.571,pid_ki=1.820,pid_kd=783.849)))
    d['devices'].append(dict(name='probe',board='tool',kind='probe',settings=dict(pin='PB6',invert=False,digital_pullup=False,x_offset=0,y_offset=0,z_offset=0)))
    return d


class CatalogTests(unittest.TestCase):
    def setUp(self):self.c=Catalog(CATALOG)
    def test_catalog_sources(self):
        source=Path(os.environ.get('SV08_PRINTER_SOURCE_ROOT','/home/drew/sv08-mainline'))
        import hashlib
        for board in self.c.boards.values():
            self.assertEqual(hashlib.sha256(primary_source(board['source']['path']).read_bytes()).hexdigest(),board['source']['sha256'])
        self.assertIn('heater',self.c.boards['octopus-v1.1-non-pro']['warning'])
        self.assertEqual(self.c.curves['sovol-bed']['points'],[[25,100000],[50,18085.4],[100,5362.6]])
        self.assertEqual(self.c.curves['sovol-hotend']['points'],[[25,110000],[100,7008],[220,435]])
    def test_all_selectable_capabilities_primary_line_audit(self):
        root=Path(os.environ.get('SV08_PRINTER_SOURCE_ROOT','/home/drew/sv08-mainline'))
        for board in self.c.boards.values():
            lines=primary_source(board['source']['path']).read_text().splitlines()
            for pin,signal in board['signals'].items():
                source=signal['source'];line=lines[source['line']-1]
                self.assertIn(source['option']+':',line.replace(' ',''),(board['id'],pin))
                normalized=line.split(':',1)[1].split('#')[0].strip().replace(' ','').lstrip('^!~').split(':')[-1]
                self.assertEqual(normalized,pin,(board['id'],pin))
                option=source['option'];kind=source['section'].split()[0]
                expected={'step_pin':'step','dir_pin':'dir','enable_pin':'enable','uart_pin':'uart','sensor_pin':'adc','heater_pin':'heater','switch_pin':'input','endstop_pin':'input','diag_pin':'input'}.get(option)
                if option=='pin':expected='fan' if 'fan' in kind else 'probe' if kind=='probe' else None
                if kind=='bltouch' and option=='sensor_pin':expected='probe'
                self.assertEqual(signal['capabilities'],[expected],(board['id'],pin))
            for cap,count in board['channel_counts'].items():self.assertEqual(count,sum(cap in sig['capabilities'] for sig in board['signals'].values()))
            for pin in board['reserved_pins']:
                with self.assertRaises(ValueError):self.c.pin(board,pin,'heater')
    def test_fixed_factory_schema_and_catalog_corruption(self):
        for mutate in [lambda c:c['curves'][0]['points'][0].__setitem__(1,109999),lambda c:c['curves'][0].__setitem__('sensor_type','injected\n[heater_bed]'),lambda c:c['boards'][0]['channel_counts'].__setitem__('adc',99),lambda c:c['boards'][0]['signals']['PC5']['capabilities'].append('output_pin')]:
            data=copy.deepcopy(self.c.data);mutate(data)
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'catalog.json';path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):Catalog(path)

    def test_sensor_positive_allowlist_and_determinism(self):
        d=sensor_draft();a=generate(self.c,d,'sensors');self.assertTrue(a['complete']);self.assertEqual(a,generate(self.c,d,'sensors'))
        allowed=('mcu','printer','thermistor ','temperature_sensor ')
        for line in a['text'].splitlines():
            if line.startswith('['):self.assertTrue(line[1:].startswith(allowed),line)
        self.assertIn('pullup_resistor: 11500',a['text'])
        self.assertFalse(generate(self.c,full_draft(),'sensors')['complete'])
        onlytool=sensor_draft();del onlytool['boards']['main'];onlytool['devices']=onlytool['devices'][1:]
        self.assertFalse(generate(self.c,onlytool,'sensors')['complete'])
        d['devices'].append(dict(name='filament_check',board='main',kind='input',settings=dict(pin='PE9',invert=False,digital_pullup=True)))
        text=generate(self.c,d,'sensors')['text'];self.assertIn('pause_on_runout: false',text);self.assertNotIn('runout_gcode',text)
    def test_full_protected_and_incomplete(self):
        a=generate(self.c,full_draft(),'full');self.assertTrue(a['complete'],a['blockers'])
        for name in ['stepper_z','stepper_z1','stepper_z2','stepper_z3','extruder','heater_bed']:self.assertIn('['+name+']',a['text'])
        self.assertIn('min_extrude_temp: 150',a['text']);self.assertNotIn('verify_heater',a['text']) # upstream defaults retained
        self.assertFalse(generate(self.c,sensor_draft(),'full')['complete'])
    def test_tmc2209_software_current_boundary(self):
        for current in (3,4):
            d=full_draft();d['devices'][2]['settings'].update(run_current=current,current_rating_rms=4)
            with self.subTest(current=current),self.assertRaisesRegex(ValueError,'2.000 A'):
                generate(self.c,d,'full')
        d=full_draft();d['devices'][2]['settings'].update(run_current=2,current_rating_rms=4)
        self.assertTrue(generate(self.c,d,'full')['complete'])
        del d['devices'][2]['settings']['current_rating_rms']
        self.assertIn('stepper_x.current_rating_rms', '\n'.join(generate(self.c,d,'full')['blockers']))

    def test_component_replacement_is_atomic_and_keeps_unrelated_devices(self):
        d=empty_draft();d['boards']={'main':{'id':'sv08-main'}}
        d=self.c.apply_preset(d,'main','bed_sensor')
        d=self.c.apply_preset(d,'main','exhaust_fan')
        before=copy.deepcopy(d)
        selected=self.c.select_component(d,'main','bed_assembly')
        self.assertEqual(d,before)
        self.assertEqual({x['name'] for x in selected['devices']},{'bed_sensor','heater_bed','exhaust_fan'})
        selected['devices'][-1]['settings']['pid_kp']=99
        replacement=self.c.select_component(selected,'main','bed_assembly')
        self.assertNotEqual(replacement['devices'][-1]['settings'].get('pid_kp'),99)
        bad=copy.deepcopy(d);bad['devices'].append(dict(name='other_heater',kind='bed',board='main',settings={'pin':'PA0'}))
        with self.assertRaisesRegex(ValueError,'collision'):
            self.c.select_component(bad,'main','bed_assembly')
        self.assertEqual(d,before)

    def test_pt1000_and_advanced_custom_ntc_curve(self):
        d=sensor_draft();s=d['devices'][0]['settings'];s['curve']='pt1000'
        self.assertIn('sensor_type: PT1000',generate(self.c,d,'sensors')['text'])
        s['custom_curve']=[[25,100000],[100,7008],[220,435]]
        with self.assertRaisesRegex(ValueError,'PT1000'):self.c.validate(d)
        s['curve']='generic3950'
        text=generate(self.c,d,'sensors')['text']
        self.assertIn('[thermistor sv08_custom_bed_check]',text)
        self.assertIn('sensor_type: sv08_custom_bed_check',text)
        self.assertIn('pullup_resistor: 4700',text)
        for points in ([[25,100000],[25,7008],[220,435]],[[25,-1],[100,7008],[220,435]],[[25,100000],[100,7008]],[[25,435],[100,7008],[220,100000]]):
            s['custom_curve']=points
            with self.assertRaises(ValueError):self.c.validate(d)

    def test_catalog_transport_metadata_is_bounded(self):
        for value in ([], ['usb'], ['can','can'], 'can'):
            data=copy.deepcopy(self.c.data);data['boards'][-1]['supported_transports']=value
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'catalog.json';p.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError,'transports'):Catalog(p)

    def test_named_bed_preserves_unknown_sensor_and_defers_pid(self):
        d=empty_draft();d['boards']['main']={'id':'sv08-main'}
        d=self.c.select_component(d,'main','bed_assembly')
        d['devices'][0]['settings']['curve']='sovol-bed'
        selected=self.c.select_component(d,'main','funssor_cn3d_bed')
        sensor=next(x for x in selected['devices'] if x['kind']=='sensor')
        heater=next(x for x in selected['devices'] if x['kind']=='bed')
        self.assertNotIn('curve',sensor['settings']);self.assertEqual(sensor['settings']['max_temp'],105)
        self.assertEqual(heater['profile'],'funssor_cn3d_bed');self.assertNotIn('pid_kp',heater['settings'])
        self.c.validate(selected)
        self.assertFalse(generate(self.c,selected,'full')['complete'])

    def test_chamber_module_uses_separate_can_identity_and_internal_pins(self):
        d=full_draft();d['boards']['chamber']={'id':'sovol-sv08-max-chamber','transport':'can'}
        d=self.c.select_component(d,'chamber','chamber_module')
        review=generate(self.c,d,'full')
        self.assertFalse(review['complete']);self.assertIn('chamber.identity','\n'.join(review['blockers']))
        d['boards']['chamber'].update(identity='0123456789ab',reference_ack=True)
        review=generate(self.c,d,'full');self.assertTrue(review['complete'],review['blockers'])
        self.assertIn('[mcu chamber]',review['text']);self.assertIn('heater_pin: chamber:PA0',review['text'])
        self.assertIn('sensor_pin: chamber:PA5',review['text']);self.assertIn('pullup_resistor: 20000.0',review['text'])
        self.assertIn('[heater_generic chamber_temp]',review['text']);self.assertIn('control: watermark',review['text'])
        self.assertNotIn('[verify_heater chamber_temp]',review['text']);self.assertNotIn('[gcode_macro',review['text'])
        self.assertNotIn('58a72bb93aa4',review['text'])
        self.assertFalse(generate(self.c,d,'sensors')['complete'])
        serial=copy.deepcopy(d);serial['boards']['chamber'].update(transport='serial',identity='/dev/null')
        with self.assertRaisesRegex(ValueError,'transport'):self.c.validate(serial)
        collision=copy.deepcopy(d);collision['devices'].append(dict(name='extra_chamber_sensor',kind='sensor',board='chamber',settings={'pin':'PA5'}))
        with self.assertRaisesRegex(ValueError,'collision'):self.c.validate(collision)
        rewire=copy.deepcopy(d);heater=next(x for x in rewire['devices'] if x['kind']=='chamber');heater['board']='main'
        with self.assertRaisesRegex(ValueError,'own board'):self.c.validate(rewire)

    def test_reference_presets_and_dependencies(self):
        d=empty_draft();d['boards']['main']={'id':'sv08-main'}
        original=copy.deepcopy(d);d=self.c.apply_preset(d,'main','bed_sensor')
        self.assertEqual(original['devices'],[])
        self.assertEqual(d['devices'][0]['settings'],dict(pin='PC5',curve='sovol-bed',min_temp=5,max_temp=105,pullup_resistor=4700))
        d=self.c.apply_preset(d,'main','stepper_x');motor=d['devices'][1]
        self.assertEqual(motor['name'],'stepper_x');self.assertEqual(motor['settings']['uart_address'],3)
        self.assertEqual(motor['settings']['rotation_distance'],40);self.assertEqual(motor['settings']['run_current'],1.5)
        self.assertNotIn('current_rating_rms',motor['settings']);self.assertNotIn('endstop_pin',motor['settings'])
        before=copy.deepcopy(d)
        with self.assertRaisesRegex(ValueError,'unique'):self.c.apply_preset(d,'main','stepper_x')
        with self.assertRaises(ValueError):self.c.apply_preset(d,'main','bed_assembly')
        self.assertEqual(d,before)
        d['devices'][0]['name']='custom_sensor'
        with self.assertRaisesRegex(ValueError,'collision'):self.c.apply_preset(d,'main','bed_sensor')
        tool=empty_draft();tool['boards']['tool']={'id':'sv08-tool'}
        tool=self.c.apply_preset(tool,'tool','hotend_assembly');self.assertEqual(tool['devices'][1]['settings']['sensor'],'hotend_sensor')
        z=self.c.apply_preset(original,'main','stepper_z')['devices'][0]['settings']
        self.assertEqual((z['rotation_distance'],z['gear_ratio']),(40,'80:12'))
        full=full_draft();full['devices'][4]['settings']['gear_ratio']='80:12'
        self.assertIn('gear_ratio: 80:12',generate(self.c,full,'full')['text'])
        full['devices'][4]['settings']['gear_ratio']='80:0\n[heater_bed]'
        with self.assertRaisesRegex(ValueError,'ratio'):self.c.validate(full)

    def test_reference_field_primary_sources(self):
        import ast
        root=Path(os.environ.get('SV08_PRINTER_SOURCE_ROOT','/home/drew/sv08-mainline'))
        for board in self.c.boards.values():
            for preset in board['presets']:
                for device in preset['devices']:
                    self.assertNotIn('current_rating_rms',device['settings'])
                    for key,field_source in device['sources'].items():
                        s={**board['source'],**field_source}
                        with self.subTest(board=board['id'],preset=preset['id'],field=key):
                            lines=primary_source(s['path']).read_text().splitlines();line=lines[s['line']-1]
                            actual=device['settings'][key];transform=s['transform']
                            if transform=='software-default':
                                tree=ast.parse(primary_source(s['path']).read_text())
                                calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and n.lineno<=s['line']<=getattr(n,'end_lineno',n.lineno) and len(n.args)>=2 and isinstance(n.args[0],ast.Constant) and n.args[0].value==key]
                                self.assertTrue(any(isinstance(n.args[1],ast.Constant) and n.args[1].value==actual for n in calls));continue
                            raw=line.strip().lstrip('#').strip().split(':',1)[1].split('#')[0].strip()
                            self.assertEqual(raw,s['value']);self.assertIn(s['option'].lower(),line.lower())
                            if transform=='number':self.assertEqual(actual,float(raw))
                            elif transform=='pin':self.assertEqual(actual,raw.replace(' ','').lstrip('^!~').split(':')[-1])
                            elif transform=='invert':self.assertEqual(actual,'!' in raw)
                            elif transform=='pullup':self.assertEqual(actual,'^' in raw)
                            elif transform=='text':self.assertEqual(actual,raw)
                            elif transform=='connector':self.assertEqual(actual,s['section']);self.assertIn(actual,board['motors'])
                            elif transform=='association':self.assertTrue(any(d['name']==actual and d['kind']=='sensor' for d in preset['devices']))
                            elif transform=='curve':self.assertEqual(self.c.curves[actual]['sensor_type'],{'my_thermistor':'sv08_factory_bed','my_thermistor_e':'sv08_factory_hotend'}.get(raw,raw))
                            else:self.fail('Unexpected transformation')

    def test_data_only_preset_extension_and_negatives(self):
        data=copy.deepcopy(self.c.data);board=data['boards'][0]
        extra=copy.deepcopy(board['presets'][0]);extra['id']='contributor_sensor';extra['label']='Contributor EPCOS reference option';extra['devices'][0]['name']='contributor_sensor'
        # An existing supported curve option and its exact primary origin are data.
        octopus=next(b for b in data['boards'] if b['id']=='octopus-v1.1-non-pro')
        sample=next(p for p in octopus['presets'] if p['id']=='hotend_sensor')['devices'][0]
        extra['devices'][0]['settings']['curve']=sample['settings']['curve']
        extra['devices'][0]['sources']['curve']={**octopus['source'],**copy.deepcopy(sample['sources']['curve'])}
        board['presets'].append(extra)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'catalog.json';p.write_text(json.dumps(data));ext=Catalog(p)
            d=empty_draft();d['boards']['main']={'id':board['id']}
            selected=ext.apply_preset(d,'main','contributor_sensor')['devices'][0]
            self.assertEqual((selected['name'],selected['settings']['curve']),('contributor_sensor','epcos100k'))
            for mutate in (lambda d:d['sources'].pop('pin'),lambda d:d['settings'].__setitem__('pin','PA0'),lambda d:d['settings'].__setitem__('current_rating_rms',4),lambda d:d['settings'].__setitem__('raw','[include x]')):
                bad=copy.deepcopy(data);mutate(bad['boards'][0]['presets'][0]['devices'][0]);p.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):Catalog(p)
    def test_rejections(self):
        for key,value in [('pin','!PC5'),('pin','PA0'),('pullup_resistor',True),('max_temp',float('nan')),('digital_pullup',True),('min_temp',110),('curve','x\n[heater_bed]')]:
            d=sensor_draft();d['devices'][0]['settings'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.c.validate(d)
        d=sensor_draft();d['devices'].append(copy.deepcopy(d['devices'][0]));d['devices'][-1]['name']='collision'
        with self.assertRaisesRegex(ValueError,'collision'):self.c.validate(d)
        d=full_draft();d['devices'][2]['settings']['run_current']=2
        with self.assertRaisesRegex(ValueError,'RMS'):self.c.validate(d)
        with self.assertRaises(ValueError):strict_json(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):strict_json(b' '*131073)
        d=sensor_draft();d['devices']*=33
        with self.assertRaises(ValueError):self.c.validate(d)
    def test_board_change_and_data_extension(self):
        d=self.c.change_board(sensor_draft(),'main','octopus-v1.1-non-pro');self.assertEqual(len(d['devices']),1);self.assertEqual(d['boards']['main'],{'id':'octopus-v1.1-non-pro'})
        c=copy.deepcopy(self.c.data);extra=copy.deepcopy(c['boards'][0]);extra['id']='contributor-fixture';c['boards'].append(extra)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'catalog.json';p.write_text(json.dumps(c));ext=Catalog(p);d=sensor_draft();d['boards']['main']['id']='contributor-fixture';self.assertTrue(generate(ext,d,'sensors')['complete'])


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='printer-',dir=os.environ.get('SV08_PRINTER_SCRATCH','/home/drew/.cache/sv08-printer-fixtures-20261004')); self.root=Path(self.tmp.name);self.root.chmod(0o700)
        from sv08_data_budget import Budget
        budget=Budget(self.root/'data',state_reserve=0,copy_limit=8*1024*1024,staging_reserve=0)
        self.store=Store(self.root/'data',reserve_bytes=0,copy_limit_bytes=8*1024*1024,budget=budget)
        self.store.initialize();self.boot=self.store.prepare_boot('A','r1');self.boot['boot_id']='fixture'
        self.boot_path=self.root/'boot.json';self.boot_path.write_text(json.dumps(self.boot))
        self.view=self.root/'config';self.view.symlink_to(Path(self.boot['generation'])/'config')
        self.c=Catalog(CATALOG);self.service=PrinterStore(self.store,self.boot_path,self.view,self.c,privileged=lambda:True)
    @staticmethod
    def filesystem(path):
        from types import SimpleNamespace
        return SimpleNamespace(f_frsize=4096,f_bsize=4096,f_bavail=1024*1024,f_favail=1000000)
    def tearDown(self):self.tmp.cleanup()
    def status(self):return self.service.request({'action':'status'})['state']
    def request(self, request):
        # Existing same-generation fixtures load current context explicitly;
        # stale-context regressions below submit their captured status directly.
        request.setdefault('expected_identity',self.service.request({'action':'status'})['loaded_identity'])
        return self.service.request(request)
    def save(self,d,revision=None):return self.request(dict(action='save',draft=d,expected_revision=self.status()['revision'] if revision is None else revision))
    def activate(self, boot):
        self.boot_path.write_text(json.dumps(boot))
        self.view.unlink();self.view.symlink_to(Path(boot['generation'])/'config')

    def assert_stale_operations(self, loaded):
        path=self.service.directory/'state.json';before=path.read_bytes()
        requests=[dict(action='save',draft=loaded['state']['draft'],expected_revision=loaded['state']['revision']),
                  dict(action='restore',expected_revision=loaded['state']['revision']),
                  dict(action='import',draft=loaded['state']['draft'],expected_revision=loaded['state']['revision']),
                  dict(action='preset',draft=loaded['state']['draft'],role='main',preset='stepper_x',expected_revision=loaded['state']['revision']),
                  dict(action='review',mode='sensors'),
                  dict(action='apply',mode='sensors',review='old-review')]
        for request in requests:
            with self.subTest(action=request['action']):
                request['expected_identity']=loaded['loaded_identity']
                with patch('sv08_printer_store.generate',side_effect=AssertionError('must refuse before generation')), patch.object(self.c,'apply_preset',side_effect=AssertionError('must refuse before preview')):
                    with self.assertRaisesRegex(ValueError,'stale'):
                        self.service.request(request)
                self.assertEqual(path.read_bytes(),before)

    def test_loaded_context_actual_copy_equal_revision_and_divergence(self):
        # Exact original reproduction: A revision1 copied by actual Store into B.
        self.save(sensor_draft());a=copy.deepcopy(self.boot)
        loaded=self.service.request({'action':'status'})
        b=self.store.prepare_boot('B','r1');self.activate(b)
        current=self.service.request({'action':'status'})
        self.assertEqual(current['state']['revision'],1)
        self.assertEqual(current['state'],loaded['state'])
        self.assertNotEqual(current['loaded_identity'],loaded['loaded_identity'])
        self.assert_stale_operations(loaded)
        # Explicit refresh permits edits in B, while A remains unchanged.
        d=sensor_draft();d['devices'][0]['settings']['max_temp']=100
        self.service.request(dict(action='save',draft=d,expected_revision=1,expected_identity=current['loaded_identity']))
        self.activate(a);self.assertEqual(self.status(),loaded['state'])

    def test_loaded_context_actual_copy_equal_revision_overwrite(self):
        # Exact reviewer follow-up: apply in A, copy revision2, diverge to3.
        self.save(sensor_draft());self.apply();a=copy.deepcopy(self.boot)
        b=self.store.prepare_boot('B','r1');self.activate(b)
        d=sensor_draft();d['devices'][0]['settings']['max_temp']=100;self.save(d)
        self.activate(a);d['devices'][0]['settings']['max_temp']=90;self.save(d)
        loaded=self.service.request({'action':'status'})
        self.activate(b);current=self.service.request({'action':'status'})
        self.assertEqual(loaded['state']['revision'],current['state']['revision'])
        self.assertEqual(loaded['state']['revision'],3)
        self.assertEqual(current['state']['draft']['devices'][0]['settings']['max_temp'],100)
        self.assert_stale_operations(loaded)
        imported=self.service.request(dict(action='import',draft=loaded['state']['draft'],expected_revision=3,expected_identity=current['loaded_identity']))
        self.assertTrue(imported['changed'])
        self.service.request(dict(action='save',draft=imported['draft'],expected_revision=3,expected_identity=current['loaded_identity']))
        self.assertEqual(self.status()['draft']['devices'][0]['settings']['max_temp'],90)
        self.activate(a);self.assertEqual(self.status(),loaded['state'])

    def test_loaded_binding_boot_mode_catalog_generator_and_content(self):
        self.save(sensor_draft());self.apply()
        for field,value in [('boot_id','next-boot'),('mode','writable')]:
            loaded=self.service.request({'action':'status'})
            boot=copy.deepcopy(self.boot);boot[field]=value;self.activate(boot)
            self.service.request({'action':'status'});self.assert_stale_operations(loaded)
            self.activate(self.boot)
        loaded=self.service.request({'action':'status'})
        with patch.object(self.c,'revision','changed-catalog'):
            self.assert_stale_operations(loaded)
        with patch('sv08_printer_store.GENERATOR_VERSION',999):
            self.assert_stale_operations(loaded)
        # Content identity also protects equal revision envelope replacements.
        path=self.service.directory/'state.json';before=path.read_bytes()
        for mutate in [lambda s:s['draft']['devices'][0]['settings'].__setitem__('max_temp',100),lambda s:s.__setitem__('current',None)]:
            state=copy.deepcopy(loaded['state']);mutate(state);path.write_text(json.dumps(state))
            self.assert_stale_operations(loaded);path.write_bytes(before)
        # Identity never replaces mandatory integer revision CAS or strict schema.
        for expected in [True,0]:
            with self.assertRaises(ValueError):self.service.request(dict(action='save',draft=sensor_draft(),expected_revision=expected,expected_identity=loaded['loaded_identity']))
        with self.assertRaises(ValueError):self.service.request(dict(action='save',draft=sensor_draft(),expected_revision=loaded['state']['revision']))
        self.assertEqual(path.read_bytes(),before)

    def test_two_sessions_stale_import_and_reviewed_replacement(self):
        self.save(sensor_draft());tab_a=copy.deepcopy(self.status())
        # Independent logical session over the actual same generation/locks.
        tab_b=PrinterStore(self.service.store,self.service.boot_path,self.service.config_view,self.c,privileged=lambda:True)
        changed=copy.deepcopy(tab_a['draft']);changed['devices'][0]['settings']['max_temp']=100
        tab_b.request(dict(action='save',draft=changed,expected_revision=tab_a['revision'],expected_identity=tab_b.request({'action':'status'})['loaded_identity']))
        before=self.status()
        with self.assertRaisesRegex(ValueError,'refresh before importing'):
            self.request(dict(action='import',draft=tab_a['draft'],expected_revision=tab_a['revision']))
        self.assertEqual(self.status(),before)
        with self.assertRaisesRegex(ValueError,'refresh before saving'):self.save(tab_a['draft'],tab_a['revision'])
        refreshed=self.status()
        imported=self.request(dict(action='import',draft=tab_a['draft'],expected_revision=refreshed['revision']))
        self.assertTrue(imported['changed']);self.assertEqual(imported['expected_revision'],refreshed['revision'])
        self.assertEqual(refreshed['draft']['devices'][0]['settings']['max_temp'],100)
        self.save(imported['draft'],refreshed['revision']);self.assertEqual(self.status()['draft']['devices'][0]['settings']['max_temp'],105)
        # Another write after a successful import still cannot bypass Save CAS.
        with self.assertRaises(ValueError):self.save(imported['draft'],imported['expected_revision'])

    def test_preset_request_is_preview_only(self):
        d=empty_draft();d['boards']['main']={'id':'sv08-main'};self.save(d);before=self.status()
        result=self.request(dict(action='preset',draft=d,role='main',preset='stepper_x',expected_revision=before['revision']))
        self.assertEqual(self.status(),before);self.assertEqual(result['draft']['devices'][0]['name'],'stepper_x')
        self.save(result['draft'],before['revision']);self.assertNotIn('current_rating_rms',self.status()['draft']['devices'][0]['settings'])
    def apply(self,mode='sensors'):
        r=self.request(dict(action='review',mode=mode));return self.request(dict(action='apply',mode=mode,review=r['review']))
    def test_cas_review_previous_restore_ack(self):
        self.save(sensor_draft(),0);self.apply();first=self.status()['current']
        with self.assertRaises(ValueError):self.save(sensor_draft(),0)
        r=self.request(dict(action='review',mode='sensors'));d=sensor_draft();d['devices'][0]['settings']['max_temp']=100;self.save(d)
        with self.assertRaises(ValueError):self.request(dict(action='apply',mode='sensors',review=r['review']))
        self.apply();state=self.status();self.assertEqual(state['previous'],first)
        # Lost response: actual status reconciles applied identity; old review cannot reapply.
        with self.assertRaises(ValueError):self.request(dict(action='apply',mode='sensors',review=r['review']))
        self.request(dict(action='restore',expected_revision=state['revision']));self.assertEqual(self.status()['draft'],first['draft'])
    def test_no_space_killed_publication_and_corruption(self):
        self.save(sensor_draft());self.apply();path=self.service.directory/'state.json';before=path.read_bytes()
        with patch('sv08_printer_store.atomic_json',side_effect=OSError('ENOSPC')):
            with self.assertRaises(OSError):self.save(sensor_draft())
        self.assertEqual(path.read_bytes(),before)
        # Kill actual writer after private temp fsync, immediately before replace.
        pid=os.fork()
        if pid==0:
            import sv08_state
            def kill(*args):os.kill(os.getpid(),signal.SIGKILL)
            sv08_state.os.replace=kill
            self.save(sensor_draft());os._exit(99)
        _,status=os.waitpid(pid,0);self.assertTrue(os.WIFSIGNALED(status));self.assertEqual(path.read_bytes(),before)
        self.assertTrue(list(self.service.directory.glob('.state.json.*')))
        self.save(sensor_draft());self.assertFalse(list(self.service.directory.glob('.state.json.*')))
        state=self.status();state['format_version']=2;path.write_text(json.dumps(state));path.chmod(0o600)
        self.assertEqual(self.status()['format_version'],2)
        with self.assertRaises(ValueError):self.save(sensor_draft(),state['revision'])
        self.assertEqual(json.loads(path.read_text())['format_version'],2)
    def test_real_generation_copy_rollback_current_and_historical(self):
        self.save(sensor_draft());self.apply();original=self.status()
        for label,cls in [('current',Store),('historical',self.historical_store())]:
            with self.subTest(api=label):
                data=self.root/label;kwargs={}
                if cls is Store:
                    from sv08_data_budget import Budget
                    kwargs['budget']=Budget(data,state_reserve=0,copy_limit=8*1024*1024,staging_reserve=0)
                st=cls(data,reserve_bytes=0,copy_limit_bytes=8*1024*1024,**kwargs);st.initialize();a=st.prepare_boot('A','a')
                source=Path(self.boot['generation'])/'config'/'printer-hardware';target=Path(a['generation'])/'config'/'printer-hardware'
                import shutil
                shutil.copytree(source,target)
                bootfile=self.root/(label+'.json');bootfile.write_text(json.dumps(a));view=self.root/(label+'view');view.symlink_to(Path(a['generation'])/'config')
                svc=PrinterStore(st,bootfile,view,self.c,privileged=lambda:True)
                self.assertEqual(svc.request({'action':'status'})['state'],original)
                svc.request(dict(action='save',draft=sensor_draft(),expected_revision=original['revision'],expected_identity=svc.request({'action':'status'})['loaded_identity']))
                b=st.prepare_boot('B','a');self.assertEqual((Path(a['generation'])/'config/printer-hardware/state.json').read_bytes(),(Path(b['generation'])/'config/printer-hardware/state.json').read_bytes())
                # A rollback is its preserved generation; no shared/global feature state.
                self.assertEqual(st.prepare_boot('A','a')['generation'],a['generation'])
    def test_low_blocks_inodes_feature_footprint_and_default_reserve(self):
        self.save(sensor_draft());self.apply();path=self.service.directory/'state.json';before=path.read_bytes()
        from types import SimpleNamespace
        for blocks,inodes in [(1,100000),(1000000,1)]:
            fs=SimpleNamespace(f_frsize=4096,f_bsize=4096,f_bavail=blocks,f_favail=inodes)
            with self.subTest(blocks=blocks,inodes=inodes),patch('os.statvfs',return_value=fs),patch('os.fstatvfs',return_value=fs):
                with self.assertRaises(ValueError):self.save(sensor_draft())
            self.assertEqual(path.read_bytes(),before)
        # Production Budget floor is unchanged, and rejects only165MiB capacity.
        from sv08_data_budget import Budget
        fs=SimpleNamespace(f_frsize=4096,f_bsize=4096,f_bavail=165*256,f_favail=100000)
        with self.assertRaises(ValueError):Budget(self.store.root).check(4096,2,fs=fs)
        abandoned=self.service.directory/'.state.json.abandoned'
        with abandoned.open('wb') as f:f.truncate(4*1024*1024)
        abandoned.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'storage limit'):self.save(sensor_draft())
        self.assertEqual(path.read_bytes(),before);abandoned.unlink()
        for n in range(31):
            p=self.service.directory/('.state.json.'+str(n));p.write_bytes(b'');p.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'storage limit'):self.save(sensor_draft())
        self.assertEqual(path.read_bytes(),before)

    def test_independent_process_cas_and_context_change(self):
        self.save(sensor_draft());self.apply();before=self.status();expected=before['revision']
        children=[];readers=[]
        for n in range(2):
            read,write=os.pipe();pid=os.fork()
            if pid==0:
                os.close(read)
                try:
                    d=sensor_draft();d['devices'][0]['settings']['max_temp']=100+n
                    self.save(d,expected);result=b'saved'
                except ValueError:result=b'refused'
                os.write(write,result);os.close(write);os._exit(0)
            os.close(write);children.append(pid);readers.append(read)
        outcomes=[os.read(fd,32) for fd in readers]
        for fd in readers:os.close(fd)
        for pid in children:self.assertEqual(os.waitpid(pid,0)[1],0)
        self.assertEqual(outcomes.count(b'saved'),1,outcomes)
        self.assertEqual(self.status()['current'],before['current'])
        review=self.request(dict(action='review',mode='sensors'))
        # Boot identity changes between review and apply: ordinary hash is stale.
        boot=copy.deepcopy(self.boot);boot['boot_id']='next-boot';self.boot_path.write_text(json.dumps(boot))
        with self.assertRaisesRegex(ValueError,'stale'):self.request(dict(action='apply',mode='sensors',review=review['review']))
        self.assertEqual(self.status()['current'],before['current'])
        boot['generation']='/invalid-generation';self.boot_path.write_text(json.dumps(boot))
        with self.assertRaisesRegex(ValueError,'generation'):self.status()
        self.boot_path.write_text(json.dumps(self.boot))

    def historical_store(self):
        raw=subprocess.check_output(['git','show','8c6f24f^:runtime/sv08_state.py'],cwd=ROOT)
        path=self.root/'historical.py';path.write_bytes(raw);spec=importlib.util.spec_from_file_location('historical',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.Store
    def test_unknown_catalog_diagnosis_corrupt_state_and_mutation_preservation(self):
        self.save(sensor_draft());self.apply();before=self.status();path=self.service.directory/'state.json';raw=path.read_bytes()
        catalog=copy.deepcopy(self.c.data);catalog['format_version']=2;p=self.root/'unsupported-catalog.json';p.write_text(json.dumps(catalog))
        diagnostic=Catalog(p,diagnostic=True);self.service.catalog=diagnostic
        status=self.service.request({'action':'status'});self.assertFalse(status['catalog_supported']);self.assertEqual(status['state'],before)
        with self.assertRaises(ValueError):self.save(sensor_draft(),before['revision'])
        self.assertEqual(path.read_bytes(),raw);self.service.catalog=self.c
        path.write_bytes(b'{broken');path.chmod(0o600)
        with self.assertRaises(ValueError):self.status()
        self.assertEqual(path.read_bytes(),b'{broken')

    def test_context_privilege_links_import_and_locks(self):
        self.save(sensor_draft());before=self.status()
        self.service.privileged=lambda:False
        with self.assertRaises(ValueError):self.status()
        self.service.privileged=lambda:True
        result=self.request(dict(action='import',draft=sensor_draft(),expected_revision=before['revision']));self.assertIn('expected_revision',result);self.assertEqual(self.status(),before)
        bad=sensor_draft();bad['devices'][0]['name']='inject\n'
        with self.assertRaises(ValueError):self.request(dict(action='import',draft=bad,expected_revision=before['revision']))
        with self.store.locked(nonblocking=True):
            with self.assertRaises(ValueError):self.status()
        boot=copy.deepcopy(self.boot);boot['trial']=True;self.boot_path.write_text(json.dumps(boot))
        with self.assertRaises(ValueError):self.status()
        self.boot_path.write_text(json.dumps(self.boot));p=self.service.directory/'evil';p.symlink_to(self.boot_path)
        with self.assertRaises(ValueError):self.status()

class HistoricalPersistenceTests(PersistenceTests):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='printer-historical-',dir=os.environ.get('SV08_PRINTER_SCRATCH','/home/drew/.cache/sv08-printer-fixtures-20261004'))
        self.root=Path(self.tmp.name);self.root.chmod(0o700)
        self.store=self.historical_store()(self.root/'data',reserve_bytes=0,copy_limit_bytes=8*1024*1024)
        self.store.initialize();self.boot=self.store.prepare_boot('A','r1');self.boot['boot_id']='fixture'
        self.boot_path=self.root/'boot.json';self.boot_path.write_text(json.dumps(self.boot))
        self.view=self.root/'config';self.view.symlink_to(Path(self.boot['generation'])/'config')
        self.c=Catalog(CATALOG);self.service=PrinterStore(self.store,self.boot_path,self.view,self.c,privileged=lambda:True)
    def test_historical_generation_copy_rollback(self):
        self.save(sensor_draft());self.apply();before=self.status();b=self.store.prepare_boot('B','r1')
        self.assertEqual((Path(self.boot['generation'])/'config/printer-hardware/state.json').read_bytes(),(Path(b['generation'])/'config/printer-hardware/state.json').read_bytes())
        self.assertEqual(self.store.prepare_boot('A','r1')['generation'],self.boot['generation'])
        self.assertEqual(self.status(),before)


if __name__=='__main__':unittest.main()
