#!/usr/bin/env python3
"""Guest-only real systemd admission/restoration test with simulated MCU status."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--execute', action='store_true')
a = p.parse_args()
if not a.execute:
    sys.exit('Inspection only; --execute requires a disposable QEMU guest')
if ('sv08.test=admission' not in Path('/proc/cmdline').read_text().split() or
        subprocess.check_output(['systemd-detect-virt', '--vm'], text=True).strip() != 'qemu' or
        Path('/sys/block/vda/serial').read_text().strip() != 'SV08-QEMU-DISPOSABLE' or
        json.loads(Path('/usr/lib/sv08/release.json').read_text()).get('deployable') is not False):
    sys.exit('Refusing anything other than the identified disposable guest')
sys.path.insert(0, '/usr/lib/sv08')
from sv08_admission import Admission, KLIPPER, MOONRAKER


def pid(service):
    return int(subprocess.check_output(['systemctl', 'show', '-p', 'MainPID', '--value', service], text=True))


def wait_ready():
    for attempt in range(200):
        if Path('/run/sv08/printer_data/comms/update.sock').exists() and pid(KLIPPER) and pid(MOONRAKER):
            try:
                with urllib.request.urlopen('http://127.0.0.1:7125/server/info', timeout=1) as response:
                    assert response.status == 200
                    return
            except OSError:
                pass
        time.sleep(.1)
    raise RuntimeError('Fixture services did not become ready')


try:
    directory = Path('/data/fixture'); directory.mkdir(exist_ok=True)
    status = directory/'admission-status.json'
    status.write_text('{"printing":true}')
    subprocess.run(['systemctl', 'start', KLIPPER, MOONRAKER], check=True)
    wait_ready()
    before = {name: pid(name) for name in (KLIPPER, MOONRAKER)}
    try:
        with Admission()():
            raise AssertionError('Active print was admitted')
    except ValueError as error:
        assert 'active' in str(error), str(error)
    assert {name: pid(name) for name in before} == before, 'Refusal interrupted a service'
    status.write_text('{"printing":false}')
    with Admission()():
        assert all(pid(name) == 0 for name in before)
        start = subprocess.run(['systemctl', 'start', KLIPPER], capture_output=True, text=True)
        assert start.returncode != 0 and pid(KLIPPER) == 0, 'Start escaped admission barrier'
    wait_ready()
    assert all(pid(name) != before[name] for name in before), 'Previously active service did not restart'
    try:
        with Admission()():
            raise RuntimeError('simulated installer failure')
    except RuntimeError as error:
        assert str(error) == 'simulated installer failure'
    wait_ready()
    result = dict(physical_hardware=False, hardware_status='simulated',
        real_arm64_systemd=True, real_moonraker_api=True, real_pinned_gcode_reactor=True,
        active_print_refusal_preserves_service_pids=True, acknowledged_idle_stops_services=True,
        process_start_barrier=True, services_restored_after_success_and_body_failure=True,
        package_installed_or_bundle_written=False, passed=True)
    print('SV08_QEMU_ADMISSION_RESULT '+json.dumps(result), flush=True)
    (directory/'admission-result.json').write_text(json.dumps(result)+'\n')
except BaseException as error:
    print('SV08_QEMU_ADMISSION_FAILURE '+repr(error), flush=True)
    subprocess.run(['journalctl', '-b', '-u', KLIPPER, '-u', MOONRAKER, '--no-pager'], check=False)
finally:
    subprocess.run(['systemctl', 'stop', KLIPPER, MOONRAKER], check=False)
    subprocess.run(['systemctl', 'poweroff'], check=False, timeout=20)
