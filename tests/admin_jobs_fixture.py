"""Disposable process fixture. Never staged into a host image.

Real Controller/HostImages/Staging/Transaction; fake signed payload and disk backend.
The install barrier holds the real transaction state lock across browser closure.
"""
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_admin import Controller
from sv08_admin import ACTIONS
from sv08_admin_images import HostImages
from sv08_admin_jobs import Jobs
from sv08_state import Store, atomic_json
from sv08_staging import Staging
from sv08_transaction import Transaction
from test_transaction import Backend, admitted


def verify(path):
    return dict(release='release-2', bundle_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def initialize(work, boot):
    uploads = Path(tempfile.mkdtemp(prefix='.sv08-browser-upload-', dir=Path.home()))
    (work / 'upload-path.json').write_text(json.dumps(str(uploads)))
    payload = b'offline image job browser fixture only'
    digest = hashlib.sha256(payload).hexdigest()
    Staging(uploads, reserve_bytes=0, owner_uid=os.getuid()).receive(io.BytesIO(payload), len(payload), digest, verify)
    atomic_json(work / 'backend.json', dict(selected='A', states={'A':True, 'B':False}, calls=[]))


class DiskBackend(Backend):
    def __init__(self, work):
        super().__init__(); self.work = work; self.manifest = {'deployable':True}
        self.__dict__.update(json.loads((work / 'backend.json').read_text()))
    def save(self):
        atomic_json(self.work / 'backend.json', {k:getattr(self,k) for k in ('selected', 'states', 'calls')})
    def install(self, *args):
        (self.work / 'install-entered').touch()
        deadline = time.monotonic()+120
        while not (self.work / 'release-install').exists():
            if time.monotonic()>deadline: raise TimeoutError('Fixture install barrier timed out')
            time.sleep(.05)
        super().install(*args); self.save()
    def mark_active(self, slot): super().mark_active(slot); self.save()
    def mark_bad(self, slot): super().mark_bad(slot); self.save()
    def mark_good(self, slot): super().mark_good(slot); self.save()
    def writer(self): return admitted()
    def resolution_evidence(self, boot):
        return dict(owner=':1.41', package='1.15.2-0sv08.1', busy_guard='GetSlotStatus')


def resolution_worker(_identity):
    return dict(LoadState='loaded', ActiveState='failed', SubState='failed',
                InvocationID='f'*32, MainPID='0', ExecMainStartTimestampMonotonic='1',
                ExecMainExitTimestampMonotonic='2', Result='signal')


def initialize_resolution(work, boot):
    """Create one honest unknown receipt and a cancellable preserved source."""
    initialize(work, boot)
    atomic_json(work / 'backend.json', dict(selected='A', states={'A': True, 'B': True}, calls=[]))
    store = Store(work / 'state', reserve_bytes=0)
    state = store.load()
    transaction = dict(format_version=1, id='a'*32, phase='armed', slot='B', previous_slot='A',
                       previous_release=boot['release'], release='release-2', bundle_sha256='b'*64,
                       boot_id=boot['boot_id'])
    state['pending'] = dict(slot='B', release='release-2', previous_slot='A', phase='armed', id=transaction['id'])
    store.save(state)
    Transaction(store, DiskBackend(work), admitted).save(transaction, 'armed')
    jobs = Jobs(work / 'state/admin-image-jobs', boot['boot_id'], lambda identity: None)
    jobs.root.mkdir(mode=0o700)
    plan = dict(action='image.stage', arguments={'digest': hashlib.sha256(b'offline image job browser fixture only').hexdigest()},
                revision='c'*64, title=ACTIONS['image.stage'][0], effect=ACTIONS['image.stage'][1], preserves_user_data=True)
    jobs.save([dict(id='d'*32, plan=plan, boot_id=boot['boot_id'], phase='interrupted', queued_at=0,
                    message='Disposable image worker stopped before its outcome was recorded.')])


def make_controller(work, resolution=False):
    work = Path(work)
    store = Store(work / 'state', reserve_bytes=0)
    boot = json.loads((work / 'ui-fixture.json').read_text())
    def launch(identity):
        unit = 'sv08-job-fixture-'+identity
        # Test-only unit; production uses the installed fixed template.
        subprocess.run(['/usr/bin/systemd-run', '--user', '--quiet', '--collect', '--unit='+unit,
                        '/usr/bin/python3', str(Path(__file__).resolve()), str(work), identity], check=True, timeout=10)
        with (work / 'units.log').open('a') as stream: stream.write(unit+'\n')
    jobs = Jobs(work / 'state/admin-image-jobs', boot['boot_id'], launch)
    if resolution: jobs.worker_evidence = resolution_worker
    adapter = HostImages(store, boot, DiskBackend(work),
                         Staging(Path(json.loads((work / 'upload-path.json').read_text())), reserve_bytes=0, owner_uid=os.getuid()), admitted, verify)
    return Controller(store, boot, adapter=adapter, jobs=jobs)


if __name__ == '__main__':
    work = Path(sys.argv[1]); controller = make_controller(work)
    controller.jobs.work(lambda: make_controller(work), sys.argv[2])
