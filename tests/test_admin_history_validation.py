"""Reject the whole committed view before even a historical retry."""
import copy
import json
import os
from pathlib import Path
import unittest
from sv08_admin_history import History, encode, digest
from sv08_state import atomic_json
from test_admin_history import HistoryTests


class StrictHistoryTests(unittest.TestCase):
    setUp=HistoryTests.setUp
    migrate=HistoryTests.migrate
    rollover=HistoryTests.rollover

    def test_manifest_strict_fields_types_bounds_and_token_binding(self):
        self.rollover();original=self.jobs.view()['manifest'];path=self.root/'jobs.json'
        cases=[]
        for key,value in (('format_version',True),('format_version',3),('generation',True),('generation',0),('generation',2**63),('parent_revision',None),('archives',{}),('maintenance',{})):
            item=copy.deepcopy(original);item[key]=value;cases.append(item)
        item=copy.deepcopy(original);item['unexpected']=1;cases.append(item)
        for key,value in (('name','../jobs.json'),('bytes',True),('bytes',2752513),('count',True),('count',1),('sha256','f'*64)):
            item=copy.deepcopy(original);item['active'][key]=value;cases.append(item)
        item=copy.deepcopy(original);item['archives']*=9;cases.append(item)
        item=copy.deepcopy(original);item['maintenance']['archive_sha256']='f'*64;cases.append(item)
        for item in cases:
            with self.subTest(item=item):
                atomic_json(path,item)
                with self.assertRaises((ValueError,OSError,TypeError)):
                    self.jobs.submit(self.rows[1]['id'],self.rows[1]['plan'],None)
        path.write_bytes(b'{"format_version":2,"format_version":2}');path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.jobs.load()
        path.write_bytes(encode(original));path.chmod(0o644)
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.jobs.load()

    def test_duplicate_global_ids_and_unsafe_snapshots(self):
        self.rollover();view=self.jobs.view();manifest=copy.deepcopy(view['manifest'])
        raw=encode([self.rows[1]]);sha=__import__('hashlib').sha256(raw).hexdigest();name='snapshot-'+sha+'.json'
        path=self.root/name;path.write_bytes(raw);path.chmod(0o600)
        manifest['active']=dict(name=name,sha256=sha,bytes=len(raw),count=1);atomic_json(self.root/'jobs.json',manifest)
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.jobs.load()
        atomic_json(self.root/'jobs.json',view['manifest']);path.unlink()
        active=self.root/view['manifest']['active']['name'];raw=active.read_bytes();active.unlink();active.symlink_to('/dev/null')
        with self.assertRaises((ValueError,OSError)):self.jobs.load()
        active.unlink();active.write_bytes(raw);active.chmod(0o600);os.link(active,self.root/'unexpected-link')
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.jobs.load()

    def test_fence_alias_substitution_third_link_missing_and_mode(self):
        self.migrate();alias=self.root/'history-format-v2.lock'
        alias.chmod(0o640)
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.jobs.history()
        alias.chmod(0o600);os.link(alias,self.base/'outside-alias')
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.jobs.history()
        (self.base/'outside-alias').unlink();alias.unlink();alias.write_bytes(b'');alias.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.jobs.history()

    def test_no_active_identity_deletion_or_combined_save(self):
        self.rollover();view=self.jobs.view()
        with self.jobs.lock('ledger.lock'):
            with self.assertRaisesRegex(ValueError,'Archived'):self.jobs.save(self.jobs.load(),view['revision'])
            row=copy.deepcopy(self.rows[1]);row['id']='f'*32;self.jobs.save([row],view['revision'])
            with self.assertRaisesRegex(ValueError,'preserved'):self.jobs.save([],self.jobs.view()['revision'])
