"""Pinned factory facts, complete native output and independent component replacement."""
import copy,json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_catalog import Catalog,empty_draft,digest
from sv08_printer_definitions import builtins
from sv08_printer_compose import select_definition,validate_plan
from sv08_printer_generate import generate

def factory_draft():
    c=Catalog(ROOT/'catalog/printer/catalog.json');records=builtins(c)
    factory=next(d for d in records if d['id']=='sv08.factory')
    ref=dict(source='builtin',id=factory['id'],version=factory['version'],sha256=digest(factory),commit=c.revision)
    snapshots={'builtin::'+d['id']+'@'+d['version']:d for d in records}
    return c,select_definition(c,empty_draft(),ref,snapshots),snapshots

def calibrated_fixture():
    c,d,s=factory_draft()
    for role in ('main','tool'):d['boards'][role]['identity']='/dev/serial/by-id/fixture-'+role
    next(x for x in d['devices'] if x['name']=='probe')['settings']['z_offset']=0
    return c,d,s

class Factory(unittest.TestCase):
    def test_complete_factory_has_all_devices_and_only_private_calibration_gaps(self):
        c,d,s=factory_draft();self.assertEqual(len(d['devices']),24)
        self.assertLess(len(json.dumps(d).encode()),128*1024)
        def browser_numbers(value):
            if isinstance(value,dict):return {k:browser_numbers(v) for k,v in value.items()}
            if isinstance(value,list):return [browser_numbers(v) for v in value]
            return int(value) if type(value) is float and value.is_integer() else value
        for definition in s.values():self.assertEqual(digest(definition),digest(browser_numbers(definition)))
        self.assertEqual(set(d['boards']),{'main','tool'})
        self.assertTrue(all('identity' not in b for b in d['boards'].values()))
        self.assertFalse(any('current_rating_rms' in x['settings'] or any(k.startswith('pid_') for k in x['settings']) for x in d['devices']))
        blockers=generate(c,d,'full')['blockers']
        self.assertTrue(blockers);self.assertTrue(all('identity' in b.lower() or 'z_offset' in b for b in blockers),blockers)
    def test_native_output_preserves_factory_wiring_homing_and_protections(self):
        c,d,s=calibrated_fixture();result=generate(c,d,'full');self.assertTrue(result['complete'],result['blockers']);text=result['text']
        for fragment in ('endstop_pin: tmc2209_stepper_x:virtual_endstop','diag_pin: PE15','driver_SGTHRS: 65','gear_ratio: 80:12','sensor_pin: tool:PA5','pullup_resistor: 11500','[heater_fan hotend_fan]','tachometer_pin: tool:PA1','[display]','lcd_type: uc1701','encoder_pins: ^PC6, ^PC7','[adxl345]','spi_software_miso_pin: tool:PB14','[gcode_button pressure_switch]','pin: ^!PE12','[neopixel screen_colour]','[output_pin main_led]','[safe_z_home]','[bed_mesh]','[quad_gantry_level]','[verify_heater heater_bed]','check_gain_time: 40'):
            self.assertIn(fragment,text)
        self.assertNotIn('hold_current:',text);self.assertNotIn('[probe_pressure]',text);self.assertNotIn('[homing_override]',text);self.assertNotIn('G0 ',text)
        self.assertFalse(generate(c,d,'sensors')['complete'])
    def test_replace_bed_inside_factory_preserves_every_other_device_and_clears_probe_calibration(self):
        c,d,s=calibrated_fixture();prior={x['name']:copy.deepcopy(x) for x in d['devices']}
        bed=copy.deepcopy(next(x for x in s.values() if x['id']=='sv08-main.bed_assembly'));bed['id']='fixture-bed';bed['components'][1]['settings']['max_power']=.7
        ref=dict(source='fixture',id=bed['id'],version=bed['version'],sha256=digest(bed),commit='a'*40)
        changed=select_definition(c,d,ref,{'fixture::'+bed['id']+'@'+bed['version']:bed})
        closure,_=validate_plan(changed['definition_plan'],c)
        self.assertIn('builtin::sv08.factory@0.2.0',closure);self.assertNotIn('builtin::sv08-main.bed_assembly@0.2.0',closure)
        self.assertEqual(len(changed['devices']),24)
        for x in changed['devices']:
            if x['name'] not in ('bed_sensor','heater_bed','probe'):self.assertEqual(x,prior[x['name']])
        self.assertNotIn('z_offset',next(x for x in changed['devices'] if x['name']=='probe')['settings'])
    def test_custom_current_requires_real_rating(self):
        c,d,s=calibrated_fixture();motor=next(x for x in d['devices'] if x['name']=='stepper_x');motor['settings']['run_current']=1.6
        self.assertIn('stepper_x.current_rating_rms: required for full',generate(c,d,'full')['blockers'])
        motor['settings']['current_rating_rms']=1.5
        with self.assertRaisesRegex(ValueError,'RMS'):generate(c,d,'full')
    def test_creator_bundle_replaces_a_factory_child(self):
        c,d,s=calibrated_fixture();bed=copy.deepcopy(next(x for x in s.values() if x['id']=='sv08-main.bed_assembly'));bed['id']='bundle-bed'
        bundle=copy.deepcopy(bed);bundle.update(id='bed-kit',components=[],connections=[],dependencies=[dict(id=bed['id'],version=bed['version'],sha256=digest(bed))])
        source='fixture';snap={source+'::'+x['id']+'@'+x['version']:x for x in (bed,bundle)}
        ref=dict(source=source,id=bundle['id'],version=bundle['version'],sha256=digest(bundle),commit='a'*40)
        result=select_definition(c,d,ref,snap);closure,_=validate_plan(result['definition_plan'],c)
        self.assertEqual(len(result['devices']),24);self.assertIn('builtin::sv08.factory@0.2.0',closure);self.assertIn('fixture::bundle-bed@0.2.0',closure)
        self.assertNotIn('builtin::sv08-main.bed_assembly@0.2.0',closure)
        # Whole-kit bed selection invalidates the probe offset too.
        self.assertNotIn('z_offset',next(x for x in result['devices'] if x['name']=='probe')['settings'])
    def test_documented_current_cannot_follow_a_changed_motor_connector(self):
        c,d,s=calibrated_fixture();x=next(x for x in d['devices'] if x['name']=='stepper_x');y=next(x for x in d['devices'] if x['name']=='stepper_y')
        x['settings']['connector'],y['settings']['connector']=y['settings']['connector'],x['settings']['connector']
        self.assertTrue(any('current_rating_rms' in b for b in generate(c,d,'full')['blockers']))
    def test_factory_draft_schema_and_new_fields_fail_closed(self):
        import jsonschema
        c,d,s=factory_draft();jsonschema.validate(d,json.loads((ROOT/'catalog/printer/draft.schema.json').read_text()))
        bad=copy.deepcopy(d);next(x for x in bad['devices'] if x['kind']=='neopixel')['settings']['color_order']='WRONG'
        with self.assertRaises(ValueError):c.validate(bad)
        bad=copy.deepcopy(d);next(x for x in bad['devices'] if x['kind']=='bed')['settings']['verify_max_error']=121
        with self.assertRaisesRegex(ValueError,'protection'):c.validate(bad)
        bad=copy.deepcopy(d);x=next(x for x in bad['devices'] if x['name']=='stepper_x');x['settings'].pop('driver_sgthrs');c.validate(bad)
        self.assertTrue(any('driver_sgthrs' in b for b in generate(c,bad,'full')['blockers']))
    @unittest.skipUnless(os.environ.get('SV08_PRINTER_VALIDATION_PYTHON'),'Explicit existing pinned environment required')
    def test_complete_factory_with_pinned_klipper_no_live_mcu(self):
        from sv08_printer_publish import Publisher,validate_output
        c,d,s=calibrated_fixture();result=generate(c,d,'full');self.assertTrue(result['complete'])
        source=Path(os.environ['SV08_PRINTER_SOURCE_ROOT'])
        with tempfile.TemporaryDirectory() as temporary:
            preview=Publisher(temporary).preview({'hardware.cfg':result['text']},{},'factory-fixture')
            self.assertTrue(validate_output(preview,Path(temporary),os.environ['SV08_PRINTER_VALIDATION_PYTHON'],str(source/'upstream/klipper/klippy/klippy.py'),str(source/'artifacts/test-sv08-01-mcu-usb-v1/klipper.dict'))['validated'])

if __name__=='__main__':unittest.main()
