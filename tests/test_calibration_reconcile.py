"""Offline observer tests: finite RPC acknowledgement and atomic feature state."""
import copy
import json
import os
import socket
import subprocess
import time
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'))
from sv08_calibration_reconcile import reconcile_once,expected_config,GUARD,AdmissionBusy,serve,failure_feedback
from sv08_printer_calibration import KLIPPER_REVISION,parse,dependency_binding,compatible_records,calibration_sources
from sv08_printer_publish import Publisher
from sv08_printer_generate import generate
from test_printer_calibration import SOURCE,NativeWriter
from test_printer_stack import factory
import test_printer_configuration as configuration


class SimulatedConnection:
    def __init__(self,publisher,path):
        self.publisher=publisher;self.path=str(path);self.calls=[];self.ack=[];self.reconnect=False
    def call(self,method,params=None):
        self.calls.append(method)
        if self.reconnect and len(self.calls)>2:raise ConnectionError('simulated reconnect boundary')
        if method=='info':return dict(state='ready',config_file=self.path,software_version='v0.13.0-1-g'+KLIPPER_REVISION[:7])
        if method=='objects/query':
            receipt,records,root,found=self.publisher.active_calibration()
            config=expected_config(found,records)
            settings=copy.deepcopy(config)
            return {'status':{'configfile':dict(config=config,settings=settings,save_config_pending=False),GUARD:{'ready':0,'setup':0}}}
        raise AssertionError('Unexpected RPC')
    def guard(self,ready):self.ack.append(ready)


@unittest.skipUnless((SOURCE/'klippy/configfile.py').is_file(),'Unchanged pinned upstream configfile.py source required; no venv or MCU')
class Reconciliation(unittest.TestCase):
    def setUp(self):
        configuration.PersistenceTests.setUp(self)
        self.service.native_source=SOURCE
        self.service.request({'action':'status'})
        catalog,draft=factory()
        self.context,_=self.service.context()
        self.publisher=Publisher(self.service.directory.parent,lambda:True,validate=lambda *a:{'validated':True},source=SOURCE,binding={'calibration_sources':calibration_sources(draft,catalog)})
        self.files={'hardware.cfg':generate(catalog,draft,'full')['text']}
        preview=self.publisher.preview(self.files,self.context,'fixture')
        self.receipt=self.publisher.apply(preview['review'],self.files,self.context,'fixture')
        self.config=self.service.directory.parent/'printer.cfg'
        self.connection=SimulatedConnection(self.publisher,self.config)
        self.save(draft)
    def tearDown(self):self.tmp.cleanup()
    def request(self,**request):
        status=self.service.request({'action':'status'})
        request.setdefault('expected_identity',status['loaded_identity'])
        if request['action'] in ('save','component'):request.setdefault('expected_revision',status['state']['revision'])
        return self.service.request(request)
    def save(self,draft):return self.request(action='save',draft=draft)
    def state(self):return self.service.request({'action':'status'})['state']
    def persist_zero(self):
        native=NativeWriter(self.config);native.native.set('probe','z_offset','0.000');native.save()
    def reconcile(self):return reconcile_once(self.service,self.connection,self.config,SOURCE)
    @unittest.skipUnless(os.environ.get('SV08_PRINTER_VALIDATION_PYTHON'),'Explicit pinned Klippy file-output venv/dictionary required; simulated MCU only')
    def test_real_same_pid_save_config_restart_and_profile_lifecycle(self):
        from sv08_calibration_reconcile import Connection
        catalog,draft=factory()
        mesh='\n[bed_mesh seed]\nversion: 1\npoints:\n  0, 0, 0\n  0, 0, 0\n  0, 0, 0\nmin_x: 10\nmax_x: 100\nmin_y: 10\nmax_y: 100\nx_count: 3\ny_count: 3\nmesh_x_pps: 2\nmesh_y_pps: 2\nalgo: lagrange\ntension: .2\n'
        self.files={'hardware.cfg':generate(catalog,draft,'full')['text']+mesh}
        preview=self.publisher.preview(self.files,self.context,'real-native')
        active=self.publisher.apply(preview['review'],self.files,self.context,'real-native')
        immutable={name:(self.service.directory.parent/name).read_bytes() for name in active['after'] if name!='printer.cfg'}
        python=os.environ['SV08_PRINTER_VALIDATION_PYTHON'];source=SOURCE
        dictionary=Path(os.environ['SV08_PRINTER_SOURCE_ROOT'])/'artifacts/test-sv08-01-mcu-usb-v1/klipper.dict'
        work=self.root/'native';work.mkdir()
        args=[python,str(source/'klippy/klippy.py'),str(self.config),'-I',str(work/'tty'),'-a',str(work/'api'),'-o',str(work/'mcu.out'),'-d',str(dictionary),'-d','tool='+str(dictionary),'-l',str(work/'klippy.log')]
        with (work/'process.log').open('w') as log:
            child=subprocess.Popen(args,stdout=log,stderr=log)
            connection=None
            try:
                def ready():
                    for _ in range(200):
                        candidate=None
                        try:
                            candidate=Connection(work/'api')
                            if candidate.call('info')['state']=='ready':return candidate
                        except (OSError,ValueError,ConnectionError):pass
                        if candidate:candidate.close()
                        if child.poll() is not None:self.fail('Klippy exited: '+(work/'klippy.log').read_text()[-1000:])
                        time.sleep(.05)
                    self.fail('Klippy did not reach ready: '+(work/'klippy.log').read_text()[-1000:])
                def restart(current):
                    try:current.call('gcode/script',{'script':'SAVE_CONFIG'})
                    except (OSError,ValueError,ConnectionError):pass
                    current.close()
                    # Wait for this native RESTART to close its old API first.
                    time.sleep(.1)
                    fresh=ready();self.assertEqual(fresh.call('info')['process_id'],child.pid)
                    self.assertEqual(fresh.call('objects/query',{'objects':{GUARD:None}})['status'][GUARD]['ready'],0)
                    return fresh
                connection=ready()
                with self.assertRaisesRegex(ValueError,'starting offset'):reconcile_once(self.service,connection,self.config,SOURCE)
                for command in ('PRINT_START BED_TEMP=60 EXTRUDER_TEMP=200','M24','RESUME','SDCARD_PRINT_FILE FILENAME=none.gcode'):
                    with self.assertRaises(ValueError):connection.call('gcode/script',{'script':command})
                connection.call('gcode/script',{'script':'SET_GCODE_OFFSET Z=-0.25\nZ_OFFSET_APPLY_PROBE'})
                connection=restart(connection)
                # Simulate an OS reboot identity while keeping the exact active
                # publication; this fresh native Klipper load still starts shut.
                boot=json.loads(self.boot_path.read_text());boot['boot_id']='native-reboot-fixture'
                self.boot_path.write_text(json.dumps(boot))
                reconcile_once(self.service,connection,self.config,SOURCE)
                self.assertEqual(float(self.state()['draft']['native_calibration']['records']['probe']['z_offset']),.25)
                connection.call('gcode/script',{'script':'SET_GCODE_OFFSET Z=0.25\nZ_OFFSET_APPLY_PROBE'})
                connection=restart(connection)
                reconcile_once(self.service,connection,self.config,SOURCE)
                self.assertEqual(connection.call('objects/query',{'objects':{GUARD:None}})['status'][GUARD]['ready'],1)
                self.assertEqual(float(self.state()['draft']['native_calibration']['records']['probe']['z_offset']),0)
                connection.call('gcode/script',{'script':'BED_MESH_PROFILE LOAD=seed\nBED_MESH_PROFILE SAVE=measured'})
                connection=restart(connection);reconcile_once(self.service,connection,self.config,SOURCE)
                self.assertIn('bed_mesh measured',self.state()['draft']['native_calibration']['records'])
                connection.call('gcode/script',{'script':'BED_MESH_PROFILE REMOVE=measured'})
                connection=restart(connection);reconcile_once(self.service,connection,self.config,SOURCE)
                self.assertNotIn('bed_mesh measured',self.state()['draft']['native_calibration']['records'])
                revision=self.state()['revision'];reconcile_once(self.service,connection,self.config,SOURCE)
                self.assertEqual(self.state()['revision'],revision)
                for name,raw in immutable.items():self.assertEqual((self.service.directory.parent/name).read_bytes(),raw)
                config=connection.call('objects/query',{'objects':{'configfile':None}})['status']['configfile']['config']
                self.assertEqual(config['heater_bed']['control'],'watermark')
            finally:
                if connection:connection.close()
                child.terminate()
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:child.kill();child.wait()

    def test_reboot_reconciles_existing_publication_without_republishing(self):
        self.persist_zero();self.reconcile()
        state=self.state();root=self.config.read_bytes()
        receipt_path=self.publisher.directory/'receipt.json';receipt=receipt_path.read_bytes()
        review=self.publisher.preview(self.files,self.context,'next-review')
        restore=self.publisher.restore_preview(self.context)
        boot=json.loads(self.boot_path.read_text());boot['boot_id']='second-os-boot'
        self.boot_path.write_text(json.dumps(boot))
        current_context,_=self.service.context()
        fresh=SimulatedConnection(self.publisher,self.config)
        result=reconcile_once(self.service,fresh,self.config,SOURCE)
        self.assertFalse(result['changed']);self.assertEqual(fresh.ack,[True])
        self.assertEqual(self.state(),state)
        self.assertNotIn('boot_id',self.state()['draft']['native_calibration']['context'])
        self.assertEqual(self.config.read_bytes(),root);self.assertEqual(receipt_path.read_bytes(),receipt)
        with self.assertRaisesRegex(ValueError,'stale'):
            self.publisher.apply(review['review'],self.files,current_context,'next-review')
        with self.assertRaisesRegex(ValueError,'stale'):
            self.publisher.restore(restore['review'],current_context)

    def test_wrong_current_root_and_invalid_store_context_are_refused(self):
        self.persist_zero();self.reconcile()
        with self.assertRaisesRegex(ValueError,'current configuration root'):
            self.publisher.active_calibration({**self.context,'generation':self.context['generation']+'-different'})
        original=json.loads(self.boot_path.read_text())
        for field,value in [('slot','B'),('generation',self.context['generation']+'-different'),('release','different-release')]:
            with self.subTest(field=field):
                self.boot_path.write_text(json.dumps({**original,field:value}))
                fresh=SimulatedConnection(self.publisher,self.config)
                with self.assertRaises(ValueError):reconcile_once(self.service,fresh,self.config,SOURCE)
                self.assertNotIn(True,fresh.ack)
                self.boot_path.write_text(json.dumps(original))

    def test_actual_store_generation_fork_and_mode_change_preserve_native_calibration(self):
        self.persist_zero();self.reconcile()
        previous=self.state();old_config=self.config
        receipt_bytes=(self.publisher.directory/'receipt.json').read_bytes();root_bytes=self.config.read_bytes()
        boot=self.store.prepare_boot('B','r1');boot['boot_id']='forked-os-boot'
        self.assertNotEqual(boot['generation'],self.context['generation'])
        self.boot_path.write_text(json.dumps(boot));self.view.unlink();self.view.symlink_to(Path(boot['generation'])/'config')
        current,_=self.service.context();new_root=Path(boot['generation'])/'config'
        with self.assertRaisesRegex(ValueError,'current configuration root'):self.publisher.active_calibration(current)
        publisher=Publisher(new_root,source=SOURCE)
        config=new_root/'printer.cfg'
        self.assertEqual(config.read_bytes(),root_bytes)
        self.assertEqual((publisher.directory/'receipt.json').read_bytes(),receipt_bytes)
        fresh=SimulatedConnection(publisher,config)
        reconcile_once(self.service,fresh,config,SOURCE)
        self.assertEqual(fresh.ack,[True])
        state=self.state();self.assertEqual(state['draft']['native_calibration']['records'],previous['draft']['native_calibration']['records'])
        self.assertEqual(state['current'],previous['current']);self.assertEqual(state['previous'],previous['previous'])
        self.assertEqual(old_config.read_bytes(),root_bytes)
        with self.store.locked():
            registry=self.store.load();registry['requested_mode']='writable';self.store.save(registry)
        boot['mode']='writable';self.boot_path.write_text(json.dumps(boot))
        mode_connection=SimulatedConnection(publisher,config)
        reconcile_once(self.service,mode_connection,config,SOURCE)
        self.assertEqual(mode_connection.ack,[True]);self.assertEqual(self.state()['draft']['native_calibration']['context']['mode'],'writable')
        self.assertEqual((publisher.directory/'receipt.json').read_bytes(),receipt_bytes)
        self.assertFalse(reconcile_once(self.service,mode_connection,config,SOURCE)['changed'])

    def test_mid_attempt_current_boot_or_view_change_never_acknowledges(self):
        self.persist_zero()
        original_boot=self.boot_path.read_bytes();original_view=os.readlink(self.view)
        for change in ('boot','view'):
            with self.subTest(change=change):
                self.boot_path.write_bytes(original_boot)
                if self.view.is_symlink():self.view.unlink()
                self.view.symlink_to(original_view)
                connection=SimulatedConnection(self.publisher,self.config);call=connection.call
                def changed_call(method,params=None):
                    result=call(method,params)
                    if method=='info' and connection.calls.count('info')==2:
                        if change=='boot':
                            boot=json.loads(original_boot);boot['boot_id']='changed-during-attempt';self.boot_path.write_text(json.dumps(boot))
                        else:
                            self.view.unlink();self.view.symlink_to(self.root/'different-config')
                    return result
                connection.call=changed_call
                with self.assertRaises(ValueError):reconcile_once(self.service,connection,self.config,SOURCE)
                self.assertNotIn(True,connection.ack)
        self.boot_path.write_bytes(original_boot);self.view.unlink();self.view.symlink_to(original_view)

    def test_starting_zero_refused_persisted_zero_acknowledged_and_idempotent(self):
        before=self.state()
        with self.assertRaisesRegex(ValueError,'starting offset'):self.reconcile()
        self.assertEqual(self.connection.ack,[]);self.assertEqual(self.state(),before)
        self.persist_zero();result=self.reconcile();self.assertTrue(result['changed'])
        self.assertEqual(self.connection.ack[-1],True)
        state=self.state();self.assertEqual(state['format_version'],2)
        self.assertEqual(state['draft']['native_calibration']['records']['probe']['z_offset'],'0.000')
        self.assertFalse(self.reconcile()['changed']);self.assertEqual(self.state(),state)
    def test_active_publication_survives_many_inactive_candidates_and_draft_edits(self):
        self.persist_zero()
        draft=self.state()['draft'];fan=next(d for d in draft['devices'] if d['kind']=='fan');fan['settings']['max_power']=.8
        self.save(draft)
        for _ in range(3):
            review=self.request(action='review',mode='full')
            self.request(action='apply',mode='full',review=review['review'])
        before=self.state();self.reconcile();after=self.state()
        self.assertEqual(after['current'],before['current']);self.assertEqual(after['previous'],before['previous'])
        self.assertEqual(after['draft']['devices'],before['draft']['devices']);self.assertEqual(after['draft']['definition_plan'],before['draft']['definition_plan'])
        self.assertEqual(after['draft']['native_calibration']['publication'],self.receipt['review'])
    def test_reconnect_never_acknowledges_partial_attempt(self):
        self.persist_zero();self.connection.reconnect=True
        with self.assertRaises(ConnectionError):self.reconcile()
        self.assertNotIn(True,self.connection.ack)
        fresh=SimulatedConnection(self.publisher,self.config)
        reconcile_once(self.service,fresh,self.config,SOURCE)
        self.assertEqual(fresh.ack,[True])
    def test_immutable_root_and_loaded_drift_close_guard(self):
        self.persist_zero();self.reconcile();self.config.write_text(self.config.read_text()+'# manual edit\n')
        with self.assertRaises(ValueError):self.reconcile()
        self.assertFalse(self.connection.ack[-1])
    def test_calibration_dependency_preserves_fan_change_and_invalidates_probe_mapping(self):
        self.persist_zero();self.reconcile();mirror=self.state()['draft']['native_calibration']
        config=copy.deepcopy(self.receipt['native']['config'])
        config['fan_generic unrelated']={'pin':'PA9','max_power':'.2'}
        self.assertIn('probe',compatible_records(mirror,config,self.receipt['native']['binding']['calibration_sources']))
        config['probe']['pin']='PA8'
        self.assertNotIn('probe',compatible_records(mirror,config,self.receipt['native']['binding']['calibration_sources']))
    @unittest.skipUnless(os.environ.get('SV08_PREVIOUS_RELEASE_RUNTIME'),'Explicit archived previous-release runtime required; actual older reader opt-in')
    def test_actual_previous_reader_exports_new_envelope_and_refuses_mutation(self):
        self.persist_zero();self.reconcile();original=(self.service.directory/'state.json').read_bytes()
        script="""import sys,json
from pathlib import Path
args=json.loads(sys.stdin.read());sys.path.insert(0,args['runtime'])
from sv08_state import Store
from sv08_printer_store import PrinterStore
from sv08_printer_catalog import Catalog
service=PrinterStore(Store(args['data']),args['boot'],args['view'],Catalog(args['catalog']),privileged=lambda:True)
status=service.request({'action':'status'})
try:service.load(writable=True)
except ValueError as error:refusal=str(error)
else:raise AssertionError('older reader accepted writable new state')
print(json.dumps({'state':status['state'],'definitions':status['definitions'],'refusal':refusal}))
"""
        args=dict(runtime=os.environ['SV08_PREVIOUS_RELEASE_RUNTIME'],data=str(self.store.root),boot=str(self.boot_path),view=str(self.view),catalog=str(ROOT/'catalog/printer/catalog.json'))
        result=subprocess.run([sys.executable,'-I','-c',script],input=json.dumps(args),text=True,capture_output=True,check=True)
        old=json.loads(result.stdout);self.assertEqual(old['state'],self.state());self.assertEqual(old['definitions'],[])
        self.assertIn('Unsupported stored schema',old['refusal']);self.assertEqual((self.service.directory/'state.json').read_bytes(),original)

    def test_wrong_loaded_version_path_and_settings_never_acknowledge(self):
        self.persist_zero()
        for field,value in [('software_version','f0892d8-dirty'),('software_version','another-revision'),('config_file','/different/printer.cfg')]:
            connection=SimulatedConnection(self.publisher,self.config);original=connection.call
            def call(method,params=None):
                result=original(method,params)
                if method=='info':result[field]=value
                return result
            connection.call=call
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):reconcile_once(self.service,connection,self.config,SOURCE)
            self.assertNotIn(True,connection.ack)
        connection=SimulatedConnection(self.publisher,self.config);original=connection.call
        def call(method,params=None):
            result=original(method,params)
            if method=='objects/query':result['status']['configfile']['settings']['probe']['z_offset']='.5'
            return result
        connection.call=call
        with self.assertRaisesRegex(ValueError,'setting disagrees'):reconcile_once(self.service,connection,self.config,SOURCE)
        self.assertNotIn(True,connection.ack)

    def test_failure_status_retains_good_values_and_repeated_failure_is_read_only(self):
        self.persist_zero();self.reconcile();good=copy.deepcopy(self.state()['draft']['native_calibration']['records'])
        self.config.write_text(self.config.read_text()+'[probe]\npin: PA8\n')
        with self.assertRaises(ValueError):self.reconcile()
        status=self.service.request({'action':'status'})
        self.assertEqual(status['native_calibration_status']['state'],'conflict')
        self.assertEqual(status['state']['draft']['native_calibration']['records'],good)
        revision=status['state']['revision'];raw=(self.service.directory/'state.json').read_bytes()
        with self.assertRaises(ValueError):self.reconcile()
        self.assertEqual(self.state()['revision'],revision);self.assertEqual((self.service.directory/'state.json').read_bytes(),raw)

    def test_mirror_cannot_be_forged_through_draft_save(self):
        self.persist_zero();self.reconcile();draft=self.state()['draft']
        draft['native_calibration']['records']['probe']['z_offset']='1.0'
        with self.assertRaisesRegex(ValueError,'maintained by the reconciler'):self.save(draft)

    def test_same_mapping_new_definition_identity_does_not_reuse_measurement(self):
        from sv08_printer_compose import select_definition
        from sv08_printer_catalog import digest
        self.persist_zero();self.reconcile();draft=self.state()['draft']
        record=copy.deepcopy(next(d for d in draft['definition_plan']['snapshots'].values() if d['id']=='sv08-tool.probe'))
        record['id']='new-physical-probe'
        ref=dict(source='fixture',id=record['id'],version=record['version'],sha256=digest(record),commit='fixture')
        changed=select_definition(self.c,draft,ref,{'fixture::'+record['id']+'@'+record['version']:record})
        config=copy.deepcopy(self.receipt['native']['config'])
        self.assertNotIn('probe',compatible_records(draft['native_calibration'],config,calibration_sources(changed,self.c)))

    def test_explicit_clear_and_reselect_same_hardware_do_not_restore_native_measurement(self):
        self.persist_zero();self.reconcile();draft=self.state()['draft']
        generated=generate(self.c,draft,'full');self.assertTrue(generated['printing_enabled'])
        self.assertIn('#*# z_offset = 0.000',generated['files']['printer.cfg'])
        self.assertNotIn('z_offset:',generated['files']['hardware.cfg'])
        changed=self.request(action='component',draft=draft,role='main',preset='bed_assembly')['draft']
        self.assertIsNone(changed['definition_plan']['instance_values']['probe.z_offset'])
        self.assertIn('probe.z_offset',changed['calibration_edits'])
        generated=generate(self.c,changed,'full');self.assertFalse(generated['printing_enabled'])
        self.assertNotIn('#*# z_offset',generated['files']['printer.cfg'])
        self.assertTrue(any('does not match' in message for message in generated['warnings']))
        self.assertEqual(changed['native_calibration'],draft['native_calibration'])

    def test_software_motion_limits_preserve_persisted_probe_calibration(self):
        self.persist_zero();self.reconcile();draft=self.state()['draft'];draft['geometry']['max_velocity']=250
        generated=generate(self.c,draft,'full')
        self.assertTrue(generated['printing_enabled']);self.assertIn('#*# z_offset = 0.000',generated['files']['printer.cfg'])
        self.assertFalse(any('does not match' in message for message in generated['warnings']))

    def test_status_values_and_explicit_json_calibration_edit_are_source_bound(self):
        self.persist_zero();self.reconcile()
        status=self.service.request({'action':'status'})
        self.assertEqual(float(status['native_calibration_status']['values']['probe']['z_offset']),0)
        draft=status['state']['draft'];next(d for d in draft['devices'] if d['kind']=='probe')['settings']['z_offset']=.4
        self.save(draft);saved=self.state()['draft']
        self.assertIn('probe.z_offset',saved['calibration_edits'])
        generated=generate(self.c,saved,'full')
        self.assertIn('z_offset: 0.4',generated['text']);self.assertIn('#*# z_offset = 0.4',generated['files']['printer.cfg']);self.assertEqual(generated['calibration_origins']['probe.z_offset'],'user-reported')
        self.assertNotIn('probe',self.service.request({'action':'status'})['native_calibration_status']['values'])

    def test_busy_store_is_not_an_ongoing_printing_availability_dependency(self):
        from unittest.mock import patch
        self.persist_zero();self.reconcile();state=self.state()
        self.assertEqual(self.connection.ack,[True])
        with patch.object(self.service,'locked',side_effect=ValueError('System state is busy. Image job progress remains available; refresh shortly.')):
            with self.assertRaises(AdmissionBusy):self.reconcile()
        self.assertEqual(self.connection.ack,[True]);self.assertEqual(self.state(),state)
        self.reconcile();self.assertEqual(self.connection.ack,[True])

    def test_known_unsaved_calibration_closes_guard_even_when_store_is_busy(self):
        from unittest.mock import patch
        self.persist_zero();self.reconcile();original=self.connection.call
        def call(method,params=None):
            result=original(method,params)
            if method=='objects/query':result['status']['configfile']['save_config_pending']=True
            return result
        self.connection.call=call
        with patch.object(self.service,'locked',side_effect=ValueError('System state is busy. Image job progress remains available; refresh shortly.')):
            with self.assertRaisesRegex(ValueError,'unsaved changes'):self.reconcile()
        self.assertFalse(self.connection.ack[-1])

    def test_manual_reported_zero_offset_and_pid_persist_and_acknowledge(self):
        self.service.publication_admit=lambda:True;self.service.publication_validate=lambda *a:{'validated':True}
        for offset in (0,.4):
            draft=self.state()['draft'];probe=next(d for d in draft['devices'] if d['kind']=='probe');probe['settings']['z_offset']=offset
            heater=next(d for d in draft['devices'] if d['kind']=='bed');heater['settings'].update(control='pid',pid_kp=20,pid_ki=1,pid_kd=50)
            self.save(draft)
            review=self.request(action='review',mode='full');self.request(action='apply',mode='full',review=review['review'])
            publication=self.request(action='publication_review',expected_revision=self.state()['revision'])
            self.request(action='publication_apply',expected_revision=self.state()['revision'],review=publication['review'])
            fresh=SimulatedConnection(self.publisher,self.config);reconcile_once(self.service,fresh,self.config,SOURCE)
            self.assertEqual(fresh.ack,[True]);mirror=self.state()['draft']['native_calibration']
            self.assertEqual(float(mirror['records']['probe']['z_offset']),offset)
            self.assertEqual(mirror['origins']['probe.z_offset'],'user-reported')
            self.assertEqual(mirror['origins']['heater_bed.pid_kp'],'user-reported')

    def test_one_manual_pid_gain_retains_native_remaining_tuple_and_probe(self):
        native=NativeWriter(self.config);native.native.set('probe','z_offset','0.000')
        for field,value in [('control','pid'),('pid_kp','20'),('pid_ki','1'),('pid_kd','50')]:native.native.set('heater_bed',field,value)
        native.save();self.reconcile();draft=self.state()['draft']
        next(d for d in draft['devices'] if d['kind']=='bed')['settings']['pid_kp']=30
        self.save(draft);saved=self.state()['draft'];heater=next(d for d in saved['devices'] if d['kind']=='bed')['settings']
        self.assertEqual((heater['control'],heater['pid_kp'],heater['pid_ki'],heater['pid_kd']),('pid',30,1,50))
        generated=generate(self.c,saved,'full');self.assertTrue(generated['complete'],generated['blockers'])
        self.assertIn('pid_kp: 30',generated['text']);self.assertIn('#*# z_offset = 0.000',generated['files']['printer.cfg'])
        self.assertEqual(generated['manual_calibration']['heater_bed']['control'],'pid')

    def test_expected_pending_states_and_legacy_do_not_send_unknown_guard_script(self):
        from unittest.mock import patch
        self.persist_zero();self.reconcile();before=self.state()['draft']['native_calibration']['records']
        legacy=SimulatedConnection(self.publisher,self.config);call=legacy.call
        def legacy_call(method,params=None):
            result=call(method,params)
            if method=='objects/query':result['status']['configfile']['config'].pop(GUARD,None)
            return result
        legacy.call=legacy_call
        with self.assertRaisesRegex(ValueError,'Legacy configuration'):reconcile_once(self.service,legacy,self.config,SOURCE)
        self.assertEqual(legacy.ack,[])
        state=self.state();self.assertEqual(state['draft']['native_calibration']['status']['state'],'pending')
        self.assertEqual(state['draft']['native_calibration']['records'],before)
        for message in ('Setup configuration cannot acknowledge printing','Probe starting offset is not persisted native calibration','PID gains require persisted native calibration'):
            self.assertEqual(failure_feedback(ValueError(message))['state'],'pending')
        self.assertEqual(failure_feedback(ValueError('Unsupported native calibration record'))['state'],'conflict')

    def test_unchanged_disconnect_logs_once_and_retains_good_values_without_revision_churn(self):
        from unittest.mock import patch
        self.persist_zero();self.reconcile();before=self.state();connect=lambda:(_ for _ in ()).throw(ConnectionError('private sentinel'))
        with patch('sv08_calibration_reconcile.time.sleep',side_effect=[None,None,StopIteration]),patch('sv08_calibration_reconcile.logging.warning') as warning:
            with self.assertRaises(StopIteration):serve(self.service,connect=connect)
        self.assertEqual(warning.call_count,1);self.assertNotIn('private sentinel',str(warning.call_args))
        state=self.state();self.assertEqual(state['revision'],before['revision']+1)
        self.assertEqual(state['draft']['native_calibration']['records'],before['draft']['native_calibration']['records'])
        self.assertEqual(state['draft']['native_calibration']['status']['state'],'pending')

    def test_intentional_watermark_after_native_pid_is_not_shadowed(self):
        native=NativeWriter(self.config);native.native.set('probe','z_offset','0.000')
        for field,value in [('control','pid'),('pid_kp','20'),('pid_ki','1'),('pid_kd','50')]:native.native.set('heater_bed',field,value)
        native.save();self.reconcile();draft=self.state()['draft'];heater=next(d for d in draft['devices'] if d['kind']=='bed')
        heater['settings']['control']='watermark'
        for field in ('pid_kp','pid_ki','pid_kd'):
            heater['settings'].pop(field,None);draft.setdefault('calibration_edits',{})['heater_bed.'+field]={'value':None,'nonce':'f'*32}
        self.save(draft);generated=generate(self.c,self.state()['draft'],'full')
        self.assertTrue(generated['complete'],generated['blockers']);self.assertIn('control: watermark',generated['text'])
        self.assertNotIn('heater_bed',generated['manual_calibration'])
        self.assertIn('#*# z_offset = 0.000',generated['files']['printer.cfg'])

    def test_pid_first_imports_valid_pending_mirror_before_probe_acknowledgement(self):
        native=NativeWriter(self.config)
        for field,value in [('control','pid'),('pid_kp','20'),('pid_ki','1'),('pid_kd','50')]:native.native.set('heater_bed',field,value)
        native.save();result=self.reconcile()
        self.assertEqual(result['pending']['state'],'pending');self.assertNotIn(True,self.connection.ack)
        mirror=self.state()['draft']['native_calibration'];self.assertIn('heater_bed',mirror['records']);self.assertNotIn('probe',mirror['records'])
        self.assertEqual(self.service.request({'action':'status'})['native_calibration_status']['values']['heater_bed']['control'],'pid')
        native=NativeWriter(self.config);native.native.set('probe','z_offset','0.000');native.save()
        self.reconcile();self.assertEqual(self.connection.ack[-1],True)

    def test_setup_imports_recognized_calibration_but_never_acknowledges_printing(self):
        catalog,draft=factory();files={'hardware.cfg':generate(catalog,draft,'setup')['text']}
        preview=self.publisher.preview(files,self.context,'setup');self.publisher.apply(preview['review'],files,self.context,'setup')
        native=NativeWriter(self.config)
        for field,value in [('control','pid'),('pid_kp','20'),('pid_ki','1'),('pid_kd','50')]:native.native.set('heater_bed',field,value)
        native.native.set('probe','z_offset','0.000');native.save()
        fresh=SimulatedConnection(self.publisher,self.config);result=reconcile_once(self.service,fresh,self.config,SOURCE)
        self.assertEqual(result['pending']['state'],'pending');self.assertNotIn(True,fresh.ack)
        mirror=self.state()['draft']['native_calibration'];self.assertEqual(mirror['records']['probe']['z_offset'],'0.000');self.assertIn('heater_bed',mirror['records'])
        status=self.service.request({'action':'status'})['native_calibration_status'];self.assertEqual(status['state'],'pending');self.assertEqual(status['values']['heater_bed']['control'],'pid')

    def test_redacted_import_preserves_local_mirror_and_refuses_foreign_mirror(self):
        self.persist_zero();self.reconcile();before=self.state();draft=copy.deepcopy(before['draft']);draft.pop('native_calibration')
        result=self.request(action='import',draft=draft,expected_revision=before['revision'])
        self.assertEqual(result['draft']['native_calibration'],before['draft']['native_calibration'])
        foreign=copy.deepcopy(result['draft']);foreign['native_calibration']['publication']='f'*64
        with self.assertRaisesRegex(ValueError,'maintained by the reconciler'):self.request(action='import',draft=foreign,expected_revision=before['revision'])
        self.assertEqual(self.state(),before)

    def test_restore_review_is_stale_after_a_new_native_save(self):
        self.persist_zero();self.reconcile()
        review=self.publisher.restore_preview(self.context)
        receipt_path=self.publisher.directory/'receipt.json';receipt=receipt_path.read_bytes()
        native=NativeWriter(self.config);native.native.set('probe','z_offset','0.400');native.save()
        newer=self.config.read_bytes()
        with self.assertRaisesRegex(ValueError,'Restoration review is stale'):self.publisher.restore(review['review'],self.context)
        self.assertEqual(self.config.read_bytes(),newer);self.assertEqual(receipt_path.read_bytes(),receipt)
        self.assertFalse((self.publisher.directory/'journal.json').exists())

    def test_stopped_republication_carries_native_zero_and_restore_keeps_own_footer(self):
        self.persist_zero();self.reconcile()
        preview=self.publisher.preview(self.files,self.context,'second')
        self.assertIn('#*# z_offset = 0.000',preview['activation'])
        self.assertLess(preview['activation'].index('[include printer-managed/'),preview['activation'].index('#*# <'))
        self.publisher.apply(preview['review'],self.files,self.context,'second')
        native=NativeWriter(self.config);native.native.set('probe','z_offset','.2');native.save()
        restore=self.publisher.restore_preview(self.context);self.publisher.restore(restore['review'],self.context)
        records=self.publisher.active_calibration(self.context)[1]
        self.assertEqual(records['probe']['z_offset'],'0.000')


if __name__=='__main__':unittest.main()
