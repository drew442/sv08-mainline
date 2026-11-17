"""Offline firmware assignment, read-only transport and observed status outcomes."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from sv08_printer_catalog import Catalog,digest
from sv08_printer_calibration import KLIPPER_REVISION
from sv08_printer_definitions import builtins,validate_definition
from sv08_printer_firmware import (EXTENSION,release_assignment,validate_assignment,
                                   applied_boards,status,observe,installed_assignment)
from test_printer_configuration import sensor_draft,full_draft,primary_source
from test_data_budget import fixture_budget,fixture_root
from sv08_state import Store,fingerprint,atomic_json


class Firmware(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=fixture_root());self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.catalog=Catalog(ROOT/'catalog/printer/catalog.json')
        self.records=builtins(self.catalog)
        self.assignment=release_assignment('r1',KLIPPER_REVISION,self.records)
        self.boards=applied_boards(sensor_draft(),self.catalog)
        self.publisher=type('Applied',(),{'active_calibration':lambda _,context:(dict(native=dict(binding=dict(firmware_boards=self.boards))),None,None,None)})()
        atomic_json(self.root/'mcu-firmware.json',self.assignment)

    def result(self,versions):
        return status(self.root,'r1',self.publisher,{},observer=lambda:{k:dict(mcu_version=v) for k,v in versions.items()})

    def test_release_definitions_match_generated_catalog_and_versions_are_immutable(self):
        published=json.loads((ROOT/'catalog/printer/definitions/builtin.json').read_text())['records']
        self.assertEqual(published,self.records)
        for row in self.assignment['definitions']:
            self.assertEqual(row['reference']['sha256'],digest(row['definition']))
            validate_definition(row['definition'],self.catalog)
            self.assertEqual(row['definition']['version'],'0.3.0')
        tampered=copy.deepcopy(self.assignment);tampered['definitions'][0]['definition']['extensions'][EXTENSION]['klipper_commit']='a'*40
        with self.assertRaisesRegex(ValueError,'digest'):validate_assignment(tampered,'r1')
        with self.assertRaises(ValueError):validate_assignment(self.assignment,'r2')
        with self.assertRaisesRegex(ValueError,'pinned release host'):release_assignment('r2','a'*40,self.records)
        for commit in ('latest','f0892d8','A'*40,None):
            bad=copy.deepcopy(self.assignment['definitions'][0]['definition']);bad['extensions'][EXTENSION]['klipper_commit']=commit
            with self.assertRaisesRegex(ValueError,'exact Klipper'):validate_definition(bad,self.catalog)

    def test_actual_versions_match_mismatch_dirty_unknown_and_observation_failure(self):
        versions={'mcu':'v0.13.0-1-g'+KLIPPER_REVISION[:12],'mcu tool':'v0.13.0-1-g'+KLIPPER_REVISION}
        before=fingerprint(self.root)
        result=self.result(versions);self.assertEqual(result['state'],'match')
        self.assertTrue(all(b['expected_commit']==KLIPPER_REVISION for b in result['boards']))
        versions['mcu tool']='v0.13.0-1-g'+'a'*40
        result=self.result(versions);self.assertEqual(result['state'],'mismatch');self.assertIn('do not flash',result['message'])
        for version in ('v0.13.0-1-g'+KLIPPER_REVISION[:7]+'-dirty','unknown','',None,'v0.13.0-1-gf0892d'):
            versions['mcu tool']=version
            with self.subTest(version=version):self.assertEqual(self.result(versions)['state'],'unknown')
        failed=status(self.root,'r1',self.publisher,{},observer=lambda:(_ for _ in ()).throw(ConnectionRefusedError()))
        self.assertEqual(failed['state'],'unknown');self.assertEqual(fingerprint(self.root),before)

    def test_legacy_missing_applied_mapping_and_changed_board_never_match(self):
        versions={'mcu':'v1-1-g'+KLIPPER_REVISION,'mcu tool':'v1-1-g'+KLIPPER_REVISION}
        self.boards['tool']['mapping_sha256']='a'*64
        self.assertEqual(self.result(versions)['state'],'unknown')
        self.assertIsNone(next(b for b in self.result(versions)['boards'] if b['role']=='tool')['expected_commit'])
        self.boards.clear();self.assertEqual(self.result(versions)['state'],'unknown')
        (self.root/'mcu-firmware.json').unlink()
        self.assertEqual(self.result(versions)['state'],'unknown')
        (self.root/'mcu-firmware.json').symlink_to(self.root/'other')
        self.assertEqual(self.result(versions)['state'],'unknown')

    def test_fixed_socket_calls_only_list_and_query_without_private_fields(self):
        sent=[]
        class Client:
            def __enter__(client):return client
            def __exit__(client,*args):pass
            def settimeout(client,value):pass
            def connect(client,path):self.assertEqual(path,'/run/sv08/printer_data/comms/klippy.sock')
            def sendall(client,raw):sent.append(json.loads(raw[:-1]))
            def recv(client,size):
                request=sent[-1]
                result={'objects':['mcu','mcu tool','extruder','mcu ../evil']} if request['id']==1 else {'status':{'mcu':{'mcu_version':'v1-1-g'+KLIPPER_REVISION[:12]}}}
                return json.dumps(dict(id=request['id'],result=result)).encode()+b'\x03'
        with patch('sv08_printer_firmware.socket.socket',return_value=Client()):
            result=observe()
        self.assertEqual([s['method'] for s in sent],['objects/list','objects/query'])
        self.assertEqual(sent[-1]['params'],{'objects':{'mcu':['mcu_version'],'mcu tool':['mcu_version']}})
        self.assertEqual(result['mcu']['mcu_version'],'v1-1-g'+KLIPPER_REVISION[:12])

    def test_shared_deadline_prevents_second_send_after_first_response_consumes_budget(self):
        clock=[0.0];sent=[];timeouts=[]
        import sv08_printer_firmware as firmware
        original_parser=firmware.strict_json
        class Client:
            def __enter__(client):return client
            def __exit__(client,*args):pass
            def settimeout(client,seconds):timeouts.append(seconds)
            def connect(client,path):clock[0]+=.4
            def sendall(client,raw):sent.append(json.loads(raw[:-1]));clock[0]+=.3
            def recv(client,size):
                clock[0]+=.9
                return json.dumps(dict(id=1,result={'objects':['mcu']})).encode()+b'\x03'
        def parse(raw,limit):
            result=original_parser(raw,limit);clock[0]+=.5
            return result
        with patch.object(firmware.time,'monotonic',side_effect=lambda:clock[0]),patch.object(firmware.socket,'socket',return_value=Client()),patch.object(firmware,'strict_json',side_effect=parse):
            with self.assertRaisesRegex(TimeoutError,'timed out'):observe()
        self.assertEqual([request['method'] for request in sent],['objects/list'])
        self.assertEqual(timeouts[0],2)
        self.assertAlmostEqual(timeouts[1],1.6)
        self.assertTrue(all(0<seconds<=2 for seconds in timeouts))
        self.assertGreater(clock[0],2)

    def test_publication_status_uses_applied_mapping_and_never_saved_draft(self):
        from sv08_printer_store import PrinterStore
        from sv08_printer_publish import Publisher
        store=Store(self.root/'data',reserve_bytes=0,budget=fixture_budget());store.initialize()
        with patch('sv08_printer_firmware.installed_assignment',return_value=self.assignment):boot=store.prepare_boot('A','r1')
        context=self.root/'boot.json';atomic_json(context,boot)
        view=self.root/'config-view';view.symlink_to(Path(boot['generation'])/'config')
        service=PrinterStore(store,context,view,self.catalog,privileged=lambda:True,
                             publication_admit=lambda:True,publication_validate=lambda p,r:dict(validated=True),
                             native_source=primary_source('upstream/klipper/klippy/configfile.py').parents[1])
        version='v1-1-g'+KLIPPER_REVISION
        with patch('sv08_printer_firmware.observe',return_value={'mcu':{'mcu_version':version},'mcu tool':{'mcu_version':version}}):
            loaded=service.request({'action':'status'})
            self.assertEqual(loaded['mcu_firmware']['state'],'unknown')
            saved=service.request(dict(action='save',draft=full_draft(),expected_revision=loaded['state']['revision'],expected_identity=loaded['loaded_identity']))
            loaded=service.request({'action':'status'})
            review=service.request(dict(action='review',mode='full',expected_identity=loaded['loaded_identity']))
            service.request(dict(action='apply',review=review['review'],mode='full',expected_identity=loaded['loaded_identity']))
            loaded=service.request({'action':'status'})
            request=dict(expected_revision=loaded['state']['revision'],expected_identity=loaded['loaded_identity'])
            preview=service.request(dict(action='publication_review',**request))
            service.request(dict(action='publication_apply',review=preview['review'],**request))
            loaded=service.request({'action':'status'})
            self.assertEqual(loaded['mcu_firmware']['state'],'match')
            receipt=Publisher(Path(boot['generation'])/'config').receipt()
            self.assertEqual(receipt['native']['binding']['firmware_boards'],self.boards)
            # A saved tentative board mapping cannot relabel an applied MCU.
            tentative=copy.deepcopy(loaded['state']['draft']);tentative['boards']['main']['id']='octopus-v1.1-non-pro'
            with service.locked():
                envelope=service.load();envelope['draft']=tentative;service.publish(envelope,store.load()['slots']['A'])
            before=fingerprint(Path(boot['generation']))
            again=service.request({'action':'status'})
            self.assertEqual(again['mcu_firmware']['state'],'match')
            self.assertEqual(fingerprint(Path(boot['generation'])),before)
            self.assertEqual(again['mcu_firmware']['boards'][0]['definition']['id'],'sv08-main.board')

    def test_installed_assignment_is_bound_and_bounded(self):
        manifest=self.root/'release.json';manifest.write_text(json.dumps(dict(release='r1',state_schema=1,mcu_firmware=self.assignment)))
        self.assertEqual(installed_assignment('r1',1,manifest),self.assignment)
        self.assertIsNone(installed_assignment('r2',1,manifest))
        manifest.write_text(' '*65537)
        with self.assertRaises(ValueError):installed_assignment('r1',1,manifest)

    def test_staging_binds_before_mutation_and_rejects_supplied_drift(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from integrate_host_os import firmware_manifest
        manifest=dict(release='r1',state_schema=1)
        self.assertEqual(firmware_manifest(manifest)['mcu_firmware'],self.assignment)
        self.assertNotIn('mcu_firmware',manifest)
        with self.assertRaisesRegex(ValueError,'pin differs'):firmware_manifest({**manifest,'klipper_commit':'a'*40})
        with self.assertRaisesRegex(ValueError,'differs'):firmware_manifest({**manifest,'mcu_firmware':{}})
        with self.assertRaisesRegex(ValueError,'metadata bound'):firmware_manifest({**manifest,'oversized':'x'*65536})
        serialized=json.dumps(firmware_manifest(manifest),indent=2).encode()
        self.assertLess(len(serialized),65536)


class GenerationAssignment(unittest.TestCase):
    def test_new_release_assignment_rollback_and_legacy_do_not_reassign(self):
        with tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
            store=Store(Path(tmp)/'data',reserve_bytes=0,budget=fixture_budget());store.initialize()
            catalog=Catalog(ROOT/'catalog/printer/catalog.json')
            records=builtins(catalog)
            old=release_assignment('r1',KLIPPER_REVISION,records)
            newer_records=copy.deepcopy(records)
            for d in newer_records:
                if EXTENSION in d.get('extensions',{}):
                    d['version']='0.4.0';d['extensions'][EXTENSION]['klipper_commit']='a'*40
            new=release_assignment('r2','a'*40,newer_records)
            with patch('sv08_printer_firmware.installed_assignment',return_value=old):a=store.prepare_boot('A','r1')
            oldpath=Path(a['generation'])/'mcu-firmware.json';original=oldpath.read_bytes()
            store.expect_trial('B','r2','A')
            with patch('sv08_printer_firmware.installed_assignment',return_value=new):b=store.prepare_boot('B','r2')
            self.assertEqual(json.loads((Path(b['generation'])/'mcu-firmware.json').read_text()),new)
            self.assertNotEqual(old['host_klipper_commit'],new['host_klipper_commit'])
            self.assertEqual(json.loads(oldpath.read_text())['host_klipper_commit'],KLIPPER_REVISION)
            before=fingerprint(Path(b['generation']))
            with patch('sv08_printer_firmware.installed_assignment',return_value=old):rolled=store.prepare_boot('A','r1')
            self.assertEqual(rolled['generation'],a['generation']);self.assertEqual(oldpath.read_bytes(),original)
            self.assertEqual(json.loads(oldpath.read_text())['host_klipper_commit'],KLIPPER_REVISION)
            self.assertEqual(fingerprint(Path(b['generation'])),before)
            altered=copy.deepcopy(old);altered['definitions']=[]
            with patch('sv08_printer_firmware.installed_assignment',return_value=altered):
                with self.assertRaisesRegex(ValueError,'differs from assigned'):store.prepare_boot('A','r1')
            self.assertEqual(oldpath.read_bytes(),original)
            registry=(store.root/'state.json').read_bytes()
            corrupted=copy.deepcopy(old);corrupted['definitions'][0]['reference']['sha256']='0'*64
            atomic_json(oldpath,corrupted)
            with patch('sv08_printer_firmware.installed_assignment',return_value=old):
                with self.assertRaisesRegex(ValueError,'digest'):store.prepare_boot('A','r1')
            self.assertEqual((store.root/'state.json').read_bytes(),registry)
            oldpath.write_bytes(original)
            # An existing legacy generation is never silently upgraded in place.
            oldpath.unlink()
            with patch('sv08_printer_firmware.installed_assignment',return_value=old):store.prepare_boot('A','r1')
            self.assertFalse(oldpath.exists())


if __name__=='__main__':unittest.main()
