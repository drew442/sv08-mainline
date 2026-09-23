#!/usr/bin/env python3
"""Guest assertions for the disposable, host-selected A/B boot-health sequence.

The A boot prepares a *fixture* transaction for an already populated B image.
It does not claim to exercise signed bundle installation or U-Boot selection.
"""
import json
from pathlib import Path
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    require(subprocess.check_output(['systemd-detect-virt', '--vm'], text=True).strip() == 'qemu', 'not QEMU')
    require(Path('/sys/block/vda/serial').read_text().strip() == 'SV08-QEMU-DISPOSABLE', 'unexpected disk')
    manifest = json.loads(Path('/usr/lib/sv08/release.json').read_text())
    require(manifest['deployable'] is False, 'deployable manifest')
    require('sv08.test=rauc-backend' in Path('/proc/cmdline').read_text().split(), 'missing fixture guard')
    sys.path.insert(0, '/usr/lib/sv08')
    from sv08_state import Store, atomic_json
    from sv08_transaction import Transaction
    from sv08_rauc import Backend
    from sv08_admission import Admission
    from sv08_admin import disposable_backend_fixture

    store = Store('/data/sv08')
    boot = json.loads(Path('/run/sv08/boot.json').read_text())
    phase_path = store.root / 'qemu-boot-health-phase.json'
    phase = json.loads(phase_path.read_text())
    scenario, step = phase['scenario'], phase['step']
    require(scenario in ('success', 'fallback'), 'unknown scenario')
    require((scenario, step, boot['slot']) in (
        ('success', 0, 'A'), ('success', 1, 'B'),
        ('fallback', 0, 'A'), ('fallback', 1, 'A')), 'unexpected boot order')
    require(not Path('/run/sv08/printer_data/config/printer.cfg').exists(), 'printer config present')
    require(not tuple(Path('/dev').glob('ttyACM*')), 'MCU unexpectedly present')
    require(Path('/run/sv08/os-health-ready').is_file(), 'health-ready gate absent')
    require(not Path('/run/sv08/trial').exists(), 'trial gate not cleared')
    require(subprocess.check_output(['systemctl', 'is-active', 'sv08-prepare.service'], text=True).strip() == 'active', 'prepare inactive')

    policy = json.loads(Path('/usr/lib/sv08/update-policy.json').read_text())
    layout = json.loads(Path('/usr/lib/sv08/layout.json').read_text())
    environment = json.loads(Path('/usr/lib/sv08/environment.json').read_text())
    backend = Backend(manifest, policy, layout, environment,
                      fixture=disposable_backend_fixture(manifest))
    tx = Transaction(store, backend, Admission())
    if step == 0:
        require(boot['trial'] is False and tx.load() is None, 'source is not clean')
        backend.validate_context(boot)
        require(backend.primary() == 'A' and not backend.good('B'), 'initial selection differs')
        # B is an already populated fixture image. The fake bundle digest only
        # identifies this synthetic setup; the actual arm/boot/confirm path is real.
        staged = dict(format_version=1, id='b' * 32, phase='staged', slot='B',
                      previous_slot='A', previous_release=boot['release'],
                      release='qemu-boot-health-b', bundle_sha256='c' * 64,
                      boot_id=boot['boot_id'])
        atomic_json(tx.path, staged)
        tx.arm(boot)
        require(tx.load()['phase'] == 'armed' and backend.primary() == 'B', 'arm failed')
        phase['step'] = 1
    elif scenario == 'success':
        require(boot['trial'] is True, 'B was not prepared as a trial')
        require(tx.load()['phase'] == 'complete', 'B did not confirm')
        require(store.load()['pending'] is None, 'pending trial remains')
        require(backend.primary() == 'B' and backend.good('B'), 'B not good and primary')
        phase['step'] = 2
    else:
        require(boot['trial'] is False, 'source A incorrectly marked trial')
        require(tx.load()['phase'] == 'failed', 'fallback not cancelled')
        state = store.load()
        require(state['pending'] is None and state['last_failed_trial']['slot'] == 'B', 'failed trial not retained')
        require(backend.primary() == 'A' and not backend.good('B'), 'B not disarmed')
        diagnostics = store.root / 'shared/logs/journal/boot-health'
        require(any(json.loads(p.read_text())['slot'] == 'B' for p in diagnostics.glob('*.json')),
                'failed B health evidence absent')
        phase['step'] = 3
    atomic_json(phase_path, phase)
    result = dict(passed=True, scenario=scenario, step=step, slot=boot['slot'],
                  boot_id=boot['boot_id'], trial=boot['trial'],
                  health_ready=True, printer_config=False, mcu=False,
                  host_selected_root=True, physical_hardware=False)
    print('SV08_QEMU_BOOT_HEALTH_RESULT ' + json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        print('SV08_QEMU_BOOT_HEALTH_FAILURE ' + repr(error), flush=True)
        raise
    finally:
        subprocess.run(['systemctl', 'poweroff'], timeout=20, check=False)
