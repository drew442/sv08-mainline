"""Pure ownership contract exercised with unmodified pinned SAVE_CONFIG writer."""
import copy
import os
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_calibration import (upstream,parse,split_lane,render,native_parts,
    recognized_root,validate_records,hardware_binding,inspect_envelope,migrate_envelope)

SOURCE=Path(os.environ.get('SV08_PRINTER_SOURCE_ROOT',ROOT))/'upstream/klipper'
HARDWARE='''[probe]
pin: PA1
z_offset: 0
[heater_bed]
heater_pin: PA2
sensor_type: Generic 3950
sensor_pin: PA3
min_temp: 5
max_temp: 120
control: watermark
[bed_mesh]
mesh_min: 10,10
mesh_max: 100,100
probe_count: 3,3
'''


class NativeWriter:
    def __init__(self,path):
        self.restarts=[];self.path=path
        self.gcode=SimpleNamespace(register_command=lambda *a,**kw:None,request_restart=self.restarts.append)
        self.printer=SimpleNamespace(lookup_object=lambda name:self.gcode,get_start_args=lambda:{'config_file':str(path)},command_error=ValueError)
        self.native=upstream(SOURCE).ConfigAutoSave(self.printer)
        self.native.load_main_config()
    def save(self):self.native.cmd_SAVE_CONFIG(SimpleNamespace(error=ValueError))


class NativeCalibration(unittest.TestCase):
    def test_mutable_lane_leaves_wiring_limits_and_structure_immutable(self):
        immutable,lane=split_lane(HARDWARE)
        self.assertIn('max_temp: 120',immutable);self.assertIn('pin: PA1',immutable)
        self.assertNotIn('z_offset:',immutable);self.assertNotIn('control:',immutable)
        self.assertEqual(parse(lane),{'probe':{'z_offset':'0'},'heater_bed':{'control':'watermark'}})
        self.assertEqual(set(parse(immutable)),set(parse(HARDWARE)))

    @unittest.skipUnless((SOURCE/'klippy/configfile.py').is_file(),'Unchanged pinned upstream configfile.py source required; no venv or MCU')
    def test_real_native_writer_root_zero_repeated_save_and_profile_delete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'printer.cfg'
            immutable,lane=split_lane(HARDWARE)
            (root/'hardware.cfg').write_text(immutable)
            baseline='[include hardware.cfg]\n'+lane
            path.write_text(baseline)
            writer=NativeWriter(path)
            writer.native.set('probe','z_offset','0.000')
            writer.native.set('heater_bed','control','pid')
            for field,value in [('pid_kp','20.000'),('pid_ki','1.000'),('pid_kd','50.000')]:writer.native.set('heater_bed',field,value)
            mesh=dict(version='1',points='\n  0, 0, 0\n  0, 0, 0\n  0, 0, 0',min_x='10',max_x='100',min_y='10',max_y='100',x_count='3',y_count='3',mesh_x_pps='2',mesh_y_pps='2',algo='lagrange',tension='.2')
            for field,value in mesh.items():writer.native.set('bed_mesh measured',field,value)
            writer.save();saved=path.read_text()
            records=recognized_root(baseline,saved,parse(HARDWARE),SOURCE)
            self.assertEqual(float(records['probe']['z_offset']),0)
            self.assertIn('bed_mesh measured',records)
            self.assertEqual(writer.restarts,['restart'])
            self.assertIn('#z_offset:',saved);self.assertTrue(saved.rstrip().splitlines()[-1].startswith('#*# '))
            again=NativeWriter(path);again.native.set('probe','z_offset','0.125');again.native.remove_section('bed_mesh measured');again.save()
            records=recognized_root(saved,path.read_text(),parse(HARDWARE),SOURCE)
            self.assertEqual(records['probe']['z_offset'],'0.125');self.assertNotIn('bed_mesh measured',records)
            self.assertEqual((root/'hardware.cfg').read_text(),immutable)

    @unittest.skipUnless((SOURCE/'klippy/configfile.py').is_file(),'Unchanged pinned upstream configfile.py source required; no venv or MCU')
    def test_real_writer_rejects_included_calibration_option(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'hardware.cfg').write_text(HARDWARE)
            path=root/'printer.cfg';path.write_text('[include hardware.cfg]\n')
            writer=NativeWriter(path);writer.native.set('probe','z_offset','0.000')
            with self.assertRaisesRegex(ValueError,'conflicts with included value'):writer.save()
            self.assertEqual(path.read_text(),'[include hardware.cfg]\n')

    @unittest.skipUnless((SOURCE/'klippy/configfile.py').is_file(),'Unchanged pinned upstream configfile.py source required; no venv or MCU')
    def test_unrecognized_root_footer_and_unsupported_records_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'printer.cfg';baseline='[probe]\nz_offset: 0\n'
            path.write_text(baseline);writer=NativeWriter(path);writer.native.set('probe','z_offset','.1');writer.save();saved=path.read_text()
            for changed in [saved+'[probe]\nz_offset: .2\n',saved.replace('#z_offset: 0','#z_offset: 1'),saved.replace('[probe]','[bltouch]',1)]:
                with self.subTest(changed=changed),self.assertRaises(ValueError):recognized_root(baseline,changed,parse(baseline),SOURCE)
            with self.assertRaisesRegex(ValueError,'Unsupported native calibration record'):validate_records({'probe':{'pin':'PA2'}},parse(baseline))
            with self.assertRaisesRegex(ValueError,'Unsupported native calibration record'):validate_records({'probe_eddy_current custom':{'calibrate':'1,2'}},parse(baseline))

    def test_supported_registry_is_configuration_scoped_and_finite(self):
        config=parse('[input_shaper]\n[stepper_z]\nposition_endstop: 0\n[axis_twist_compensation]\n[skew_correction]\n[endstop_phase stepper_z]\n')
        validate_records({'input_shaper':{'shaper_freq_x':'55','shaper_type_x':'mzv'},'stepper_z':{'position_endstop':'0'},'axis_twist_compensation':{'z_compensations':'0, .01, .02'},'skew_correction measured':{'xy_skew':'0','xz_skew':'0','yz_skew':'0'},'endstop_phase stepper_z':{'trigger_phase':'1/64'}},config)
        for records in [{'input_shaper':{'shaper_freq_x':'nan'}},{'input_shaper':{'shaper_type_x':'unknown'}},{'stepper_a':{'position_endstop':'0'}},{'endstop_phase stepper_z':{'trigger_phase':'64/64'}}]:
            with self.assertRaises(ValueError):validate_records(records,config)
        with self.assertRaises(ValueError):validate_records({'input_shaper':{'shaper_freq_x':'55'}},{})

    def test_dynamic_profile_sections_do_not_leave_undeletable_immutable_headers(self):
        profile=dict(version='1',points='0, 0, 0\n0, 0, 0\n0, 0, 0',min_x='10',max_x='100',min_y='10',max_y='100',x_count='3',y_count='3',mesh_x_pps='2',mesh_y_pps='2',algo='lagrange',tension='.2')
        immutable,lane=split_lane(HARDWARE+render({'bed_mesh measured':profile}))
        self.assertNotIn('[bed_mesh measured]',immutable)
        self.assertEqual(parse(lane)['bed_mesh measured'],profile)
        self.assertEqual(render({'bed_mesh measured':{}}),'')

    def test_duplicate_option_refused_but_only_calibration_section_can_span_root_and_include(self):
        from sv08_printer_publish import inventory
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'hardware.cfg').write_text('[probe]\npin: PA1\n')
            (root/'printer.cfg').write_text('[include hardware.cfg]\n[probe]\nz_offset: 0\n')
            self.assertIn('probe',inventory(root)[1])
            (root/'printer.cfg').write_text('[include hardware.cfg]\n[probe]\npin: PA2\n')
            with self.assertRaisesRegex(ValueError,'Duplicate option'):inventory(root)
            (root/'printer.cfg').write_text('[include hardware.cfg]\n[probe]\nx_offset: 1\n')
            with self.assertRaisesRegex(ValueError,'outside root calibration lane'):inventory(root)

    def test_offline_cli_migration_is_exclusive_private_and_preserves_clear_markers(self):
        value=dict(format_version=1,revision=1,draft={'format_version':1,'definition_plan':{'instance_values':{'probe.z_offset':None},'snapshots':{'fixture':{'preserve':True}}}},current=None,previous=None)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'old.json';destination=root/'new.json';source.write_text(json.dumps(value));before=source.read_bytes()
            command=[sys.executable,str(ROOT/'runtime/sv08_printer_calibration.py')]
            inspected=subprocess.run(command+['inspect',str(source)],capture_output=True,text=True,check=True)
            self.assertTrue(json.loads(inspected.stdout)['legacy'])
            subprocess.run(command+['migrate',str(source),'--output',str(destination)],capture_output=True,text=True,check=True)
            migrated=json.loads(destination.read_text());self.assertEqual({**migrated,'format_version':1},value)
            self.assertEqual(source.read_bytes(),before);self.assertEqual(destination.stat().st_mode & 0o777,0o600)
            again=subprocess.run(command+['migrate',str(source),'--output',str(destination)],capture_output=True,text=True)
            self.assertNotEqual(again.returncode,0);self.assertEqual(source.read_bytes(),before)

    def test_version_migration_preserves_every_original_draft_and_candidate(self):
        value=dict(format_version=1,revision=7,draft={'format_version':1,'definition_plan':{'instance_values':{'probe.z_offset':None},'snapshots':{'old':{'unchanged':True}}}},current={'draft':{'historical':True}},previous=None)
        original=copy.deepcopy(value);migrated=migrate_envelope(value)
        self.assertEqual(value,original);self.assertEqual({**migrated,'format_version':1},original)
        self.assertEqual(inspect_envelope(migrated)['older_reader'],'opaque export/read only')
        with self.assertRaises(ValueError):inspect_envelope({**value,'extra_top_level':True})


if __name__=='__main__':unittest.main()
