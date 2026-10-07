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
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_catalog import Catalog,empty_draft,digest
from sv08_printer_definitions import builtins
from sv08_printer_compose import select_definition
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


class StackTests(unittest.TestCase):
    def test_factory_complete_closed_bundle_and_print_integration(self):
        catalog,draft=factory(True);original=copy.deepcopy(draft);output=generate(catalog,draft,'full')
        self.assertTrue(output['complete']);self.assertTrue(output['printing_enabled']);self.assertEqual(draft,original)
        contents=output['files'];self.assertEqual(contents['moonraker.conf'],(Path(os.environ.get('SV08_PRINTER_SOURCE_ROOT','/home/drew/sv08-mainline'))/'configs/host-os/moonraker.conf').read_text())
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
            section=output['text'].split('[gcode_macro '+command+']',1)[1].split('[',1)[0]
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
            self.assertIn('action_raise_error',output['text'].split('[gcode_macro '+command+']',1)[1].split('[',1)[0])

    def test_explicit_fan_roles_override_legacy_semantics(self):
        catalog,draft=factory(True)
        for d in draft['devices']:
            if d['kind']=='fan':d['settings']['print_fan']=d['name']=='exhaust_fan'
        text=generate(catalog,draft,'full')['text'];self.assertIn('FAN=exhaust_fan',text);self.assertNotIn('FAN=part_cooling',text)

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
            args=[python,str(source/'upstream/klipper/klippy/klippy.py'),str(work/'printer.cfg'),'-a',str(work/'api'),'-o',str(work/'mcu.out'),'-d',dictionary,'-d','tool='+dictionary,'-l',str(work/'klippy.log')]
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
                        result=request('gcode/script',dict(script=command));self.assertIn('Probe calibration pending',result['error']['message'])
                    self.assertEqual(request('info',{})['result']['state'],'ready')
                finally:
                    child.terminate()
                    try:child.wait(timeout=2)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
