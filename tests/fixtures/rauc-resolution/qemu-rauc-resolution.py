#!/usr/bin/env python3
"""Run only from the marked disposable ARM64 RAUC-resolution guest.

This fixture proves the boundary that a killed RAUC client is not proof that
the service stopped.  The host-side harness constructs the disk, signed bundle,
and test-only hook; this program is never staged into a host image.
"""
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def output(command):
    return subprocess.check_output(command, text=True).strip()


def wait(description, condition, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(.1)
    raise TimeoutError('Timed out waiting for ' + description)


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    command_line = Path('/proc/cmdline').read_text().split()
    if ('sv08.test=rauc-resolution' not in command_line or
            output(['systemd-detect-virt', '--vm']) != 'qemu' or
            Path('/sys/block/vda/serial').read_text().strip() != 'SV08-QEMU-DISPOSABLE'):
        raise ValueError('Refusing anything other than the marked disposable QEMU guest')
    if json.loads(Path('/usr/lib/sv08/release.json').read_text()).get('deployable') is not False:
        raise ValueError('Fixture metadata must be non-deployable')
    if not Path('/data').is_mount() or not (Path('/proc/mounts').read_text().splitlines()):
        raise ValueError('Fixture data filesystem is not mounted')

    sys.path.insert(0, '/usr/lib/sv08')
    from sv08_admin import ACTIONS, Controller
    from sv08_admin_jobs import Jobs
    from sv08_rauc_service import Service
    from sv08_state import Store
    from sv08_transaction import Transaction

    fixture = Path('/data/fixture')
    expected = json.loads((fixture / 'expected.json').read_text())
    service = Service()
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    boot = None
    installer = None
    try:
        run(['systemctl', 'start', 'rauc.service'])
        wait('the selected RAUC service', lambda: output(['systemctl', 'is-active', 'rauc.service']) == 'active')
        policy = service.policy()
        if policy['version'] != '1.15.2-0sv08.1':
            raise ValueError('The selected RAUC package changed')
        if output(['/usr/bin/rauc', '--version']) != 'rauc 1.15.2':
            raise ValueError('The selected RAUC executable changed')

        # The assembled D-Bus policy denies an ordinary local client.  Root is
        # intentionally retained as the service owner and privileged helper.
        ordinary = subprocess.run(['runuser', '-u', 'nobody', '--', 'busctl', '--system', 'call',
                                   policy['bus_name'], '/', policy['bus_name'] + '.Installer',
                                   'GetSlotStatus'], text=True, capture_output=True)
        if ordinary.returncode == 0:
            raise AssertionError('Ordinary D-Bus caller reached RAUC')

        class Backend:
            def writer(self):
                return service.writer()

            def resolution_evidence(self, current_boot):
                if current_boot != boot:
                    raise ValueError('Unexpected boot evidence')
                return service.observe()

            def validate_context(self, current_boot):
                if current_boot != boot:
                    raise ValueError('Unexpected cancellation boot')

            def primary(self):
                return 'A'

            def good(self, slot):
                return False

            def mark_bad(self, slot):
                if slot != 'B':
                    raise ValueError('Unexpected fixture target')
                # This is the real service-side cancellation/boot-mark route.
                return output(['/usr/bin/rauc', 'status', 'mark-bad', 'rootfs.1'])

        backend = Backend()
        store = Store('/data/sv08', reserve_bytes=0)
        store.initialize()
        boot = dict(store.prepare_boot('A', 'fixture-source'), boot_id=boot_id)
        transaction = Transaction(store, backend, nullcontext)
        tx = dict(format_version=1, id='a' * 32, phase='armed', slot='B', previous_slot='A',
                  previous_release='fixture-source', release='fixture-target',
                  bundle_sha256='b' * 64, boot_id=boot_id)
        state = store.load()
        state['pending'] = dict(slot='B', release='fixture-target', previous_slot='A', phase='armed', id=tx['id'])
        store.save(state)
        transaction.save(tx, 'armed')

        class Adapter:
            admission = nullcontext
            def __init__(self): self.backend = backend

        jobs = Jobs('/data/sv08/admin-image-jobs', boot_id, lambda identity: None)
        jobs.root.mkdir(mode=0o700)
        jobs.worker_evidence = lambda identity: {
            'LoadState': 'loaded', 'ActiveState': 'failed', 'SubState': 'failed',
            'InvocationID': 'c' * 32, 'MainPID': '0',
            'ExecMainStartTimestampMonotonic': '1', 'ExecMainExitTimestampMonotonic': '2',
            'Result': 'signal',
        }
        plan = dict(action='image.cancel', arguments={}, revision='d' * 64,
                    title=ACTIONS['image.cancel'][0], effect=ACTIONS['image.cancel'][1],
                    preserves_user_data=True)
        jobs.save([dict(id='e' * 32, plan=plan, boot_id=boot_id, phase='interrupted',
                        queued_at=0, message='Disposable worker was interrupted.')])
        controller = Controller(store, boot, adapter=Adapter(), jobs=jobs)

        # This first inspection establishes a same-owner idle observation before
        # the actual signed RAUC install starts.  It changes no receipt/journal.
        initial = controller.request({'method': 'image.inspect', 'id': 'e' * 32})
        initial_owner = initial['evidence']['service']['owner']
        if initial['evidence']['service']['busy_guard'] != 'GetSlotStatus':
            raise AssertionError('The selected internal busy guard was not recorded')
        before_busy = (jobs.root / 'jobs.json').read_bytes()

        installer = subprocess.Popen(['/usr/bin/rauc', 'install', str(fixture / 'signed.raucb')],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait('the signed RAUC pre-install hook', lambda: (fixture / 'barrier-entered').is_file())
        installer.kill()
        installer.wait(timeout=10)
        installer = None
        if output(['systemctl', 'is-active', 'rauc.service']) != 'active':
            raise AssertionError('RAUC service died when its client was killed')

        owner = service.owner(policy['bus_name'])
        operation = service.call(owner, 'org.freedesktop.DBus.Properties', 'Get', 'ss',
                                 policy['bus_name'] + '.Installer', 'Operation')[0]
        if not isinstance(operation, dict) or operation.get('data') != 'installing':
            raise AssertionError('Service did not report the held install')
        with service.writer():
            try:
                service.observe()
            except ValueError as error:
                if 'busy' not in str(error):
                    raise
            else:
                raise AssertionError('Busy RAUC service was accepted as idle')
            try:
                service.call(owner, policy['bus_name'] + '.Installer', 'GetSlotStatus')
            except ValueError as error:
                if 'internally busy' not in str(error):
                    raise
            else:
                raise AssertionError('Internal busy guard accepted a held install')

        second = subprocess.run(['/usr/bin/rauc', 'install', str(fixture / 'signed.raucb')],
                                text=True, capture_output=True)
        if second.returncode == 0:
            raise AssertionError('A second RAUC install started while the first was held')
        for request in ({'method': 'image.inspect', 'id': 'e' * 32},
                        {'method': 'image.dispose', 'plan': initial['plan']}):
            try:
                controller.request(request)
            except ValueError as error:
                if 'busy' not in str(error):
                    raise
            else:
                raise AssertionError('Interrupted-receipt action passed while RAUC was busy')
        if (jobs.root / 'jobs.json').read_bytes() != before_busy:
            raise AssertionError('Busy receipt review changed the ledger')
        try:
            transaction.cancel(boot)
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError('Cancellation completed while RAUC reported busy')
        if store.load()['pending'] is None or transaction.load()['phase'] != 'armed':
            raise AssertionError('Failed cancellation changed durable transaction state')

        # Writer exclusion covers every project participant, including marks.
        contender = Service()
        with service.writer():
            try:
                with contender.writer():
                    pass
            except ValueError as error:
                if 'writer is active' not in str(error):
                    raise
            else:
                raise AssertionError('A second supported writer acquired the lease')

        (fixture / 'release-barrier').touch()
        def idle():
            try:
                current_owner = service.owner(policy['bus_name'])
                value = service.call(current_owner, 'org.freedesktop.DBus.Properties', 'Get', 'ss',
                                     policy['bus_name'] + '.Installer', 'Operation')[0]
                return isinstance(value, dict) and value.get('data') == 'idle'
            except ValueError:
                return False
        wait('the surviving RAUC service to finish', idle, seconds=90)
        with service.writer():
            fresh_service = service.observe()
        if fresh_service['owner'] != initial_owner:
            raise AssertionError('RAUC service owner changed after the orphaned install')
        if any(sha256(fixture / 'slots' / (name + '-B.img')) != expected['installed'][name]
               for name in ('rootfs', 'boot')):
            raise AssertionError('Inactive paired images do not match the signed fixture')
        if any(sha256(fixture / 'slots' / (name + '-A.img')) != expected['source'][name]
               for name in ('rootfs', 'boot')):
            raise AssertionError('Active paired images changed during the install')

        # The previous plan is stale because it was intentionally observed
        # before the service transition.  A fresh same-owner observation can
        # now be explicitly retained as unknown, once and only once.
        fresh = controller.request({'method': 'image.inspect', 'id': 'e' * 32})
        retained = controller.request({'method': 'image.dispose', 'plan': fresh['plan']})
        if retained['phase'] != 'interrupted' or jobs.history()['blocked']:
            raise AssertionError('Unknown outcome was not durably retained')
        result = dict(passed=True, physical_hardware=False, selected_rauc=policy['version'],
                      signed_paired_install=True, client_killed_service_survived=True,
                      ordinary_dbus_client_denied=True, operation_while_held=operation['data'],
                      internal_busy_guard_refused=True, receipt_and_cancel_refused_while_busy=True,
                      writer_exclusion=True, same_owner_idle_observation=True,
                      fresh_review_disposition_retained=True,
                      active_pair_preserved=True, inactive_pair_verified=True)
        print('SV08_QEMU_RAUC_RESOLUTION_RESULT ' + json.dumps(result), flush=True)
        (fixture / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        if installer is not None and installer.poll() is None:
            installer.kill()
        subprocess.run(['systemctl', 'stop', 'rauc.service'], check=False)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        print('SV08_QEMU_RAUC_RESOLUTION_FAILURE ' + repr(error), flush=True)
        try:
            Path('/data/fixture/failure.txt').write_text(traceback.format_exc())
        except OSError:
            pass
        subprocess.run(['journalctl', '-b', '-u', 'rauc.service', '--no-pager'], check=False)
    finally:
        subprocess.run(['systemctl', 'poweroff'], check=False, timeout=20)
