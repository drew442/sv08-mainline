"""Focused active-save/rollover faults, ENOSPC and interruption/restart."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from sv08_admin_history import History, encode
from sv08_admin_jobs import Jobs
from sv08_state import atomic_json
from test_admin_history import receipt, disposed
from test_data_budget import fixture_budget, fixture_root

POINTS=('object-create','object-write','object-flush','object-file-fsync','object-publish',
        'object-directory-fsync','manifest-create','manifest-write','manifest-flush',
        'manifest-file-fsync','manifest-replace','manifest-directory-fsync','manifest-parent-fsync',
        'cleanup','lost-ack')


class PublicationTests(unittest.TestCase):
    def test_all_mutation_classes_faults_and_repeated_restart(self):
        results=[]; written=0; max_allocated=0; max_objects=0; max_entries=0
        for scenario in ('queued','running','result','disposition','rollover'):
            for point in POINTS:
                with self.subTest(scenario=scenario,point=point), tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
                    root=Path(tmp)/'admin-image-jobs';root.mkdir(mode=0o700)
                    rows=[receipt(i) for i in range(128)]
                    atomic_json(root/'jobs.json',rows)
                    jobs=Jobs(root,'fixture',lambda identity:None,budget=fixture_budget())
                    History(jobs).apply(History(jobs).review())
                    if scenario!='rollover':
                        History(jobs).apply(History(jobs).review())
                        initial=receipt(129,'queued');initial['boot_id']='fixture'
                        if scenario in ('result','disposition'):initial['phase']='running'
                        if scenario!='queued':
                            with jobs.lock('ledger.lock'):
                                view=jobs.view();jobs.save([initial],view['revision'])
                        candidate=copy.deepcopy(initial)
                        if scenario=='running':candidate['phase']='running'
                        if scenario=='result':candidate['phase']='succeeded'
                        if scenario=='disposition':
                            from sv08_admin import revision
                            from sv08_admin_resolution import KIND
                            evidence=dict(original_sha256=revision(candidate), bounded_evidence='e'*15000)
                            candidate['disposition']=dict(outcome='unknown', evidence=evidence,
                                plan=dict(kind=KIND,id=candidate['id'],evidence_sha256=revision(evidence)))
                        candidate['message']='New durable candidate' if scenario!='disposition' else candidate['message']
                    original=jobs.load(); hit=[]
                    # A known owned orphan makes the cleanup boundary meaningful.
                    orphan=root/('snapshot-'+'f'*64+'.json');orphan.write_bytes(b'[]');orphan.chmod(0o600)
                    def fail(boundary):
                        nonlocal max_allocated,max_objects,max_entries
                        allocation=sum(p.lstat().st_blocks*512 for p in root.iterdir())+root.stat().st_blocks*512
                        max_allocated=max(max_allocated,allocation);max_entries=max(max_entries,len(list(root.iterdir()))+1)
                        max_objects=max(max_objects,sum(p.name.startswith('snapshot-') or p.name.startswith('.history-object-') for p in root.iterdir()))
                        if boundary==point and not hit:
                            hit.append(boundary)
                            if scenario in ('running','disposition'):raise SystemExit(91)
                            raise OSError(28,'Injected ENOSPC '+point)
                    jobs.history_fault=fail
                    try:
                        if scenario=='rollover':plan=History(jobs).review();History(jobs).apply(plan)
                        else:
                            with jobs.lock('ledger.lock'):
                                view=jobs.view();jobs.save([candidate],view['revision'],result=scenario!='queued')
                    except (OSError,SystemExit):pass
                    jobs.history_fault=lambda boundary:None
                    self.assertEqual(hit,[point])
                    observed=jobs.load(); expected=original if scenario=='rollover' else rows+[candidate]
                    self.assertIn(observed,(original,expected))
                    self.assertEqual(observed[:128],rows)
                    if scenario=='rollover':
                        # The same completed plan must never append the batch twice.
                        if jobs.view()['manifest']['maintenance']['plan']==plan:History(jobs).apply(plan)
                        else:History(jobs).apply(History(jobs).review())
                    else:
                        with jobs.lock('ledger.lock'):
                            view=jobs.view();jobs.save([candidate],view['revision'],result=scenario!='queued')
                    stats=jobs.view()['stats'];self.assertLessEqual(stats['objects'],16);self.assertLessEqual(stats['entries'],64)
                    written+=sum(p.stat().st_size for p in root.iterdir())
                    results.append(dict(scenario=scenario,point=point,hit=True,identities_preserved=True))
        report=dict(cases=results,fixture_encoded_bytes=written,peak_allocated_bytes=max_allocated,peak_objects=max_objects,peak_namespace_entries=max_entries)
        Path(fixture_root()).joinpath('history-faults.json').write_text(json.dumps(report,indent=2))


def _crash(root, point, scenario):
    jobs=Jobs(root,'fixture',lambda identity:None,budget=fixture_budget())
    def die(boundary):
        if boundary==point:os._exit(73)
    jobs.history_fault=die
    if scenario=='migrate':History(jobs).apply(History(jobs).review())
    elif scenario=='rollover':History(jobs).apply(History(jobs).review())
    else:
        with jobs.lock('ledger.lock'):
            view=jobs.view();rows=copy.deepcopy(view['active']);rows[-1]['message']='Crashed candidate'
            jobs.save(rows,view['revision'],result=True)


class ProcessCrashTests(unittest.TestCase):
    def test_process_exit_at_durable_boundaries(self):
        import multiprocessing
        context=multiprocessing.get_context('spawn');results=[]
        migration=('fence-link','fence-link-created','fence-validate','fence-validated','fence-file-fsync','fence-directory-fsync','fence-parent-fsync',*POINTS)
        for scenario in ('migrate','rollover','active'):
            for point in migration if scenario=='migrate' else POINTS:
                with self.subTest(scenario=scenario,point=point),tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
                    root=Path(tmp)/'admin-image-jobs';root.mkdir(mode=0o700)
                    rows=[receipt(i) for i in range(128)];atomic_json(root/'jobs.json',rows)
                    jobs=Jobs(root,'fixture',lambda identity:None,budget=fixture_budget())
                    if scenario!='migrate':History(jobs).apply(History(jobs).review())
                    if scenario=='active':
                        History(jobs).apply(History(jobs).review())
                        with jobs.lock('ledger.lock'):
                            view=jobs.view();jobs.save([receipt(128,'running')],view['revision'])
                        rows=jobs.load()
                    orphan=root/('snapshot-'+'f'*64+'.json');orphan.write_bytes(b'[]');orphan.chmod(0o600)
                    child=context.Process(target=_crash,args=(str(root),point,scenario));child.start();child.join(5)
                    if child.is_alive():child.kill();child.join(5)
                    self.assertEqual(child.exitcode,73)
                    observed=jobs.load();self.assertEqual([r['id'] for r in observed],[r['id'] for r in rows])
                    if scenario=='active':self.assertIn(observed[-1]['message'],('Original outcome','Crashed candidate'))
                    else:self.assertEqual(observed,rows)
                    # Restart always validates the current commit; never restores a saved stale view.
                    if jobs.view()['format']==1:History(jobs).apply(History(jobs).review())
                    else:
                        with jobs.lock('ledger.lock'):
                            view=jobs.view();jobs.save(view['active'],view['revision'],result=True)
                    self.assertEqual([r['id'] for r in jobs.load()],[r['id'] for r in rows])
                    self.assertLessEqual(jobs.view()['stats']['objects'],16)
                    results.append(dict(scenario=scenario,point=point,process_exit=73))
        Path(fixture_root()).joinpath('history-process-crashes.json').write_text(json.dumps(results,indent=2))


class RepeatedFailureTests(unittest.TestCase):
    def test_repeated_failure_does_not_accumulate_or_restore_stale_commit(self):
        for point in ('object-file-fsync','manifest-directory-fsync','cleanup'):
            with self.subTest(point=point),tempfile.TemporaryDirectory(dir=fixture_root()) as tmp:
                root=Path(tmp)/'admin-image-jobs';root.mkdir(mode=0o700);rows=[receipt(i) for i in range(128)]
                atomic_json(root/'jobs.json',rows);jobs=Jobs(root,'fixture',lambda i:None,budget=fixture_budget())
                History(jobs).apply(History(jobs).review());History(jobs).apply(History(jobs).review())
                with jobs.lock('ledger.lock'):
                    view=jobs.view();jobs.save([receipt(128,'running')],view['revision'])
                candidate=receipt(128,'running');candidate['message']='New candidate'
                def fail(boundary):
                    if boundary==point:raise OSError(28,'Persistent injected publication failure')
                jobs.history_fault=fail;counts=[]
                for attempt in range(3):
                    with self.assertRaises(OSError),jobs.lock('ledger.lock'):
                        view=jobs.view();jobs.save([candidate],view['revision'],result=True)
                    observed=jobs.load();self.assertEqual(observed[:128],rows);self.assertEqual(observed[-1]['id'],candidate['id'])
                    counts.append(jobs.view()['stats']['entries'])
                self.assertTrue(all(count <= counts[0] for count in counts))
                self.assertEqual(counts[1],counts[2])
                jobs.history_fault=lambda boundary:None
                with jobs.lock('ledger.lock'):
                    view=jobs.view();jobs.save([candidate],view['revision'],result=True)
                self.assertEqual(jobs.load(),rows+[candidate])
