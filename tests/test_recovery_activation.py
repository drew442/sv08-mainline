import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch
from sv08_state import Store
from sv08_restore import fresh_state
from sv08_recovery_activation import Activation, boot_guard, JOURNAL, PENDING, read_journal

BOOT = dict(slot='A',release='fixture-release',state_schema=1,release_revision=7)

class Guard:
    fingerprint = 'disposable-media'
    def recheck(self): pass

@contextmanager
def admission(target): yield Guard()


def state_fixture(root,configuration,identity='a'*32):
    store = Store(root); store.initialize()
    boot = store.prepare_boot('A',BOOT['release'],BOOT['state_schema'],BOOT['release_revision'])
    (Path(boot['generation'])/'config/printer.cfg').write_text(configuration)
    (root/'system/machine-id').write_text(identity+'\n')
    return boot


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('SV08_RESTORE_SCRATCH'))
        self.parent = Path(self.tmp.name)
        state_fixture(self.parent/'sv08','previous')
        (self.parent/'restored').mkdir(mode=0o700)
        state_fixture(self.parent/'restored/sv08','restored','b'*32)
        (self.parent/'restored/sibling').write_text('preserved sibling')
        self.targets = dict(target=dict(mount=str(self.parent),root=str(self.parent/'restored'),fresh_root=str(self.parent/'fresh')))
        self.activation = Activation(self.targets,admission,BOOT)
    def tearDown(self): self.tmp.cleanup()
    def configuration(self):
        store = Store(self.parent/'sv08'); state = store.load()
        return (store.generation_path(state['slots']['A'])/'config/printer.cfg').read_text()
    def test_review_cancel_then_activate_rollback_and_second_transaction(self):
        plan = self.activation.prepare('target'); self.assertEqual(self.configuration(),'previous')
        self.activation.execute(plan); boot_guard(self.parent)
        self.assertEqual(self.configuration(),'restored')
        self.assertEqual((self.parent/'restored/sibling').read_text(),'preserved sibling')
        old = self.parent/read_journal(self.parent)['backup']
        self.assertTrue(old.is_dir())
        self.activation.execute(self.activation.prepare('target',rollback=True)); boot_guard(self.parent)
        self.assertEqual(self.configuration(),'previous')
        self.activation.execute(self.activation.prepare('target')); self.assertEqual(self.configuration(),'restored')
        self.assertTrue(list(self.parent.glob('.sv08-activation-*.json')))
    def test_normal_boot_log_links_preserved_on_activation_and_rollback(self):
        # systemd's normal /var/log setup writes this into the persistent bind.
        target = '../../usr/share/doc/systemd/README.logs'
        old_link = self.parent/'sv08/shared/logs/README'
        old_link.symlink_to(target)
        self.activation.execute(self.activation.prepare('target'))
        current_link = self.parent/'sv08/shared/logs/README'
        current_link.symlink_to(target)
        # A directory link must remain opaque; its outside FIFO is never read.
        outside = self.parent/'outside'; outside.mkdir(); os.mkfifo(outside/'fifo')
        (current_link.parent/'directory-link').symlink_to(outside, target_is_directory=True)
        plan = self.activation.prepare('target', rollback=True)
        self.activation.execute(plan); boot_guard(self.parent)
        self.assertEqual(self.configuration(), 'previous')
        self.assertEqual(os.readlink(old_link), target)
        retained = self.parent/'restored/sv08/shared/logs'
        self.assertEqual(os.readlink(retained/'README'), target)
        self.assertEqual(os.readlink(retained/'directory-link'), str(outside))
        self.assertTrue((outside/'fifo').exists())

    def test_retained_log_link_retarget_after_review_refuses_without_writes(self):
        self.activation.execute(self.activation.prepare('target'))
        link = self.parent/'sv08/shared/logs/README'; link.symlink_to('original')
        plan = self.activation.prepare('target', rollback=True)
        link.unlink(); link.symlink_to('retargeted')
        with self.assertRaisesRegex(ValueError, 'contents changed'):
            self.activation.execute(plan)
        self.assertFalse((self.parent/PENDING).exists())
        self.assertEqual(read_journal(self.parent)['phase'], 'committed')
        self.assertEqual(self.configuration(), 'restored')

    def test_interrupted_fresh_activation_retains_booted_old_log_links(self):
        link = self.parent/'sv08/shared/logs/README'
        link.symlink_to('../../usr/share/doc/systemd/README.logs')
        (self.parent/'fresh').mkdir(mode=0o700)
        fd = os.open(self.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: fresh_state(fd, 'fresh')
        finally: os.close(fd)
        def cut(name):
            if name == 'saved': raise RuntimeError('fresh activation power cut')
        worker = Activation(self.targets, admission, BOOT, cut)
        with self.assertRaises(RuntimeError): worker.execute(worker.prepare('target', fresh=True))
        with self.assertRaisesRegex(ValueError, 'Interrupted'): boot_guard(self.parent)
        self.activation.execute(self.activation.prepare('target', rollback=True))
        boot_guard(self.parent)
        self.assertEqual(self.configuration(), 'previous')
        self.assertEqual(os.readlink(link), '../../usr/share/doc/systemd/README.logs')
        self.assertEqual(Store(self.parent/'fresh').load()['slots'], {})

    def test_guest_interruption_hook_survives_controller_factory_refresh(self):
        from types import SimpleNamespace
        from recovery_restore_e2e import inject_activation_boundary
        from sv08_recovery import RecoveryController
        from sv08_recovery_restore_media import Composite, RestoreAdapter
        from sv08_recovery_media import Unavailable
        (self.parent/'fresh').mkdir(mode=0o700)
        fd = os.open(self.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: fresh_state(fd, 'fresh')
        finally: os.close(fd)
        calls = []; admissions = []
        @contextmanager
        def admitted(target):
            admissions.append(target)
            yield Guard()
        targets = dict(target=dict(self.targets['target'], label='Disposable target'))
        def factory():
            adapter = Composite(Unavailable('No export fixture'),
                                RestoreAdapter(SimpleNamespace(targets=targets, archives={}, admission=admitted), BOOT))
            calls.append(adapter)
            return adapter, None
        controller = RecoveryController(Store(self.parent/'sv08'), adapter_factory=factory)
        controller.status()
        def cut(name):
            if name == 'saved': raise RuntimeError('factory-refresh power cut')
        inject_activation_boundary(controller, cut)
        plan = controller.plan('recovery.activate-fresh', dict(target='target'))
        with self.assertRaisesRegex(RuntimeError, 'factory-refresh power cut'):
            controller.apply(plan)
        self.assertGreaterEqual(len(calls), 3)
        self.assertIsNot(calls[-1], calls[-2])
        self.assertIs(calls[-1].restore.activation.boundary, cut)
        self.assertGreater(len(admissions), 3)
        self.assertEqual(read_journal(self.parent)['phase'], 'saved')
        self.assertFalse((self.parent/'sv08').exists())
        with self.assertRaisesRegex(ValueError, 'Interrupted'): boot_guard(self.parent)
        self.activation.execute(self.activation.prepare('target', rollback=True))
        boot_guard(self.parent)
        self.assertEqual(self.configuration(), 'previous')

    def test_log_link_race_during_digest_refuses(self):
        self.activation.execute(self.activation.prepare('target'))
        link = self.parent/'sv08/shared/logs/README'; link.symlink_to('original')
        readlink = os.readlink
        def retarget(*args, **kwargs):
            value = readlink(*args, **kwargs)
            link.unlink(); link.symlink_to('retargeted')
            return value
        with patch('sv08_recovery_activation.os.readlink', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'link changed'):
                self.activation.prepare('target', rollback=True)
        self.assertFalse((self.parent/PENDING).exists())

    def test_candidate_links_nonlog_links_and_special_objects_still_refuse(self):
        link = self.parent/'restored/sv08/shared/logs/README'; link.symlink_to('target')
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            self.activation.prepare('target')
        link.unlink(); self.activation.execute(self.activation.prepare('target'))
        link = self.parent/'sv08/system/alias'; link.symlink_to('machine-id')
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            self.activation.prepare('target', rollback=True)
        link.unlink(); fifo = self.parent/'sv08/shared/logs/fifo'; os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            self.activation.prepare('target', rollback=True)
        self.assertFalse((self.parent/PENDING).exists())
        self.assertEqual(self.configuration(), 'restored')

    def test_each_durable_boundary_requires_explicit_rollback(self):
        for boundary in ('pending','prepared','rename-backup','saved','rename-sv08','committed'):
            with self.subTest(boundary=boundary):
                # Each independent disposable transaction has distinct inodes and retained evidence.
                with tempfile.TemporaryDirectory(dir=self.parent) as directory:
                    parent = Path(directory); state_fixture(parent/'sv08','old')
                    (parent/'restored').mkdir(mode=0o700); state_fixture(parent/'restored/sv08','new','c'*32)
                    targets=dict(target=dict(mount=str(parent),root=str(parent/'restored'),fresh_root=str(parent/'fresh')))
                    def fail(name):
                        if name == boundary or (boundary == 'rename-backup' and name.startswith('rename-.sv08-previous-')):
                            raise RuntimeError('simulated interruption')
                    worker = Activation(targets,admission,BOOT,fail)
                    with self.assertRaises(RuntimeError): worker.execute(worker.prepare('target'))
                    with self.assertRaisesRegex(ValueError,'Interrupted'): boot_guard(parent)
                    restarted = Activation(targets,admission,BOOT)
                    restarted.execute(restarted.prepare('target',rollback=True)); boot_guard(parent)
                    store = Store(parent/'sv08')
                    self.assertEqual((store.generation_path(store.load()['slots']['A'])/'config/printer.cfg').read_text(),'old')
    def test_changed_payload_and_incompatible_revision_refuse(self):
        plan = self.activation.prepare('target')
        store = Store(self.parent/'restored/sv08'); cfg = store.generation_path(store.load()['slots']['A'])/'config/printer.cfg'
        cfg.write_text('changed')
        with self.assertRaisesRegex(ValueError,'changed'): self.activation.execute(plan)
        self.assertFalse((self.parent/PENDING).exists()); self.assertEqual(self.configuration(),'previous')
        state = store.load(); state['slots']['A']['release_revision']=8; store.save(state)
        with self.assertRaisesRegex(ValueError,'release'): self.activation.prepare('target')
    def test_damaged_or_missing_generation_and_identity_refuse(self):
        root = self.parent/'restored/sv08'; machine = root/'system/machine-id'; machine.unlink()
        with self.assertRaisesRegex(ValueError,'identity'): self.activation.prepare('target')
        machine.write_text('d'*32+'\n'); store = Store(root); state=store.load(); state['slots']['A']['generation']='missing'; store.save(state)
        with self.assertRaisesRegex(ValueError,'generation'): self.activation.prepare('target')
        (root/'state.json').write_text('damaged')
        with self.assertRaises(ValueError): self.activation.prepare('target')
    def test_fresh_activation_existing_and_absent_canonical(self):
        for absent in (False,True):
            with self.subTest(absent=absent):
                with tempfile.TemporaryDirectory(dir=self.parent) as directory:
                    parent=Path(directory)
                    if not absent: state_fixture(parent/'sv08','old')
                    (parent/'fresh').mkdir(mode=0o700)
                    fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY)
                    try: fresh_state(fd,'fresh')
                    finally: os.close(fd)
                    worker=Activation(dict(target=dict(mount=str(parent),root=str(parent/'restored'),fresh_root=str(parent/'fresh'))),admission,BOOT)
                    worker.execute(worker.prepare('target',fresh=True)); boot_guard(parent)
                    self.assertEqual(Store(parent/'sv08').load()['slots'],{})
                    worker.execute(worker.prepare('target',rollback=True)); boot_guard(parent)
                    self.assertEqual((parent/'sv08').exists(),not absent)
    def test_rollback_contents_change_and_interruption_preserve_both_trees(self):
        self.activation.execute(self.activation.prepare('target'))
        plan=self.activation.prepare('target',rollback=True)
        journal=read_journal(self.parent);previous=self.parent/journal['backup']
        store=Store(previous);cfg=store.generation_path(store.load()['slots']['A'])/'config/printer.cfg'
        cfg.write_text('changed previous')
        with self.assertRaisesRegex(ValueError,'contents changed'): self.activation.execute(plan)
        self.assertEqual(self.configuration(),'restored')
        def fail(name):
            if name=='rename-sv08': raise RuntimeError('rollback power cut')
        worker=Activation(self.targets,admission,BOOT,fail)
        with self.assertRaises(RuntimeError):worker.execute(worker.prepare('target',rollback=True))
        with self.assertRaisesRegex(ValueError,'Interrupted'):boot_guard(self.parent)
        self.activation.execute(self.activation.prepare('target',rollback=True));boot_guard(self.parent)
        self.assertEqual(self.configuration(),'changed previous')
        self.assertTrue((self.parent/'restored/sv08').is_dir())

    def test_rolled_back_pending_reconciles_after_publication_failure(self):
        self.activation.execute(self.activation.prepare('target'))
        import sv08_recovery_activation as module
        publish_journal=module.atomic_json
        def cut(path,value):
            publish_journal(path,value)
            if value['phase']=='rolled-back':raise OSError('directory fsync failure after rolled-back publication')
        with patch('sv08_recovery_activation.atomic_json',side_effect=cut):
            with self.assertRaises(OSError):self.activation.execute(self.activation.prepare('target',rollback=True))
        self.assertEqual(read_journal(self.parent)['phase'],'rolled-back')
        with self.assertRaisesRegex(ValueError,'Interrupted'):boot_guard(self.parent)
        self.activation.execute(self.activation.prepare('target',rollback=True));boot_guard(self.parent)
        self.assertEqual(self.configuration(),'previous')
        self.assertTrue((self.parent/'restored/sv08').is_dir())
        with self.assertRaisesRegex(ValueError,'already restored'):self.activation.prepare('target',rollback=True)
    def test_second_activation_pending_and_retirement_can_be_cancelled(self):
        for boundary in ('pending','retired'):
            with self.subTest(boundary=boundary):
                # Reset using a distinct child target for each interruption.
                with tempfile.TemporaryDirectory(dir=self.parent) as directory:
                    parent=Path(directory);state_fixture(parent/'sv08','old')
                    (parent/'restored').mkdir(mode=0o700);state_fixture(parent/'restored/sv08','new','c'*32)
                    targets=dict(target=dict(mount=str(parent),root=str(parent/'restored'),fresh_root=str(parent/'fresh')))
                    worker=Activation(targets,admission,BOOT)
                    worker.execute(worker.prepare('target'));worker.execute(worker.prepare('target',rollback=True))
                    def cut(name):
                        if name==boundary:raise RuntimeError('second activation interrupted')
                    failing=Activation(targets,admission,BOOT,cut)
                    with self.assertRaises(RuntimeError):failing.execute(failing.prepare('target'))
                    with self.assertRaisesRegex(ValueError,'Interrupted'):boot_guard(parent)
                    worker.execute(worker.prepare('target',rollback=True));boot_guard(parent)
                    store=Store(parent/'sv08')
                    self.assertEqual((store.generation_path(store.load()['slots']['A'])/'config/printer.cfg').read_text(),'old')
                    self.assertTrue((parent/'restored/sv08').is_dir())

    def test_persistent_journal_allows_renumbered_device(self):
        self.activation.execute(self.activation.prepare('target'))
        from sv08_recovery_activation import inode
        def renumbered(path):
            value=inode(path); return [value[0]+123,value[1]]
        with patch('sv08_recovery_activation.inode',side_effect=renumbered): boot_guard(self.parent)
    def test_foreign_canonical_inode_and_pending_symlink_refuse(self):
        self.activation.execute(self.activation.prepare('target'))
        (self.parent/'sv08').rename(self.parent/'foreign'); (self.parent/'sv08').mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError,'identity'): boot_guard(self.parent)
        (self.parent/PENDING).symlink_to('missing')
        with self.assertRaisesRegex(ValueError,'Interrupted'): boot_guard(self.parent)

if __name__ == '__main__': unittest.main()
