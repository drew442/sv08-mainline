#!/usr/bin/env python3
"""Guest-only RAUC/U-Boot backend + idle admission; simulated printer status."""
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
    sys.exit('Inspection only; execution requires the disposable QEMU fixture')
if ('sv08.test=rauc-backend' not in Path('/proc/cmdline').read_text().split() or
        subprocess.check_output(['systemd-detect-virt', '--vm'], text=True).strip() != 'qemu' or
        Path('/sys/block/vda/serial').read_text().strip() != 'SV08-QEMU-DISPOSABLE'):
    sys.exit('Refusing anything other than the identified disposable guest')
sys.path.insert(0, '/usr/lib/sv08')
from sv08_admission import Admission, KLIPPER, MOONRAKER
from sv08_bundle import inspect as inspect_bundle
from sv08_rauc import Backend
from sv08_state import Store
from sv08_transaction import Transaction


def read(path): return json.loads(Path(path).read_text())


try:
    manifest = read('/usr/lib/sv08/release.json')
    assert manifest['deployable'] is False
    policy = read('/usr/lib/sv08/test-update-policy.json')
    layout = read('/usr/lib/sv08/test-image-layout.json')
    environment = read('/usr/lib/sv08/test-environment-layout.json')
    backend = Backend(manifest, policy, layout, environment, fixture=True)
    boot = read('/run/sv08/boot.json')
    boot['boot_id'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    bundle = Path('/data/fixture/paired.raucb')
    proof = inspect_bundle(bundle, policy, backend.keyring)
    Path('/data/fixture/admission-status.json').write_text('{"printing":false}')
    subprocess.run(['systemctl', 'start', KLIPPER, MOONRAKER], check=True)
    for attempt in range(200):
        try:
            if Path('/run/sv08/printer_data/comms/update.sock').exists():
                with urllib.request.urlopen('http://127.0.0.1:7125/server/info', timeout=1) as response:
                    assert response.status == 200
                    break
        except OSError:
            pass
        time.sleep(.1)
    else:
        raise RuntimeError('Fixture services did not become ready')
    store = Store('/data/sv08')
    transaction = Transaction(store, backend, Admission())
    transaction.stage(bundle, proof, boot)
    assert transaction.load()['phase'] == 'staged' and store.load()['pending'] is None
    assert backend.primary() == 'A' and not backend.good('B')
    transaction.arm(boot)
    assert store.load()['pending']['slot'] == 'B' and backend.primary() == 'B' and backend.good('B')
    transaction.cancel(boot)
    assert store.load()['pending'] is None and backend.primary() == 'A' and not backend.good('B')
    # Simulate the counter consumed immediately before a final B boot. The
    # running kernel remains A; this tests real backend counter semantics only.
    with store.locked(), Admission()():
        backend.validate_context(boot)
        backend.mark_active('B')
        subprocess.run(['/usr/bin/fw_setenv', 'BOOT_B_LEFT', '0'], check=True)
        assert backend.primary() == 'A' and not backend.good('B')
        backend.mark_good('B')
        assert backend.primary() == 'B' and backend.good('B')
        backend.mark_bad('B')
        assert backend.primary() == 'A' and not backend.good('B')
    result = dict(physical_hardware=False, printer_status='simulated',
        real_rauc_uboot_backend=True, real_idle_service_admission=True,
        inactive_paired_hashes_verified=True, active_paired_hashes_preserved=True,
        staged_without_activation=True, armed_then_cancelled=True,
        pending_state_cleared_after_disarming=True, final_attempt_counter_confirmation=True,
        booted_target=False, health_confirmed=False,
        bundle_sha256=proof['bundle_sha256'], passed=True)
    print('SV08_QEMU_BACKEND_RESULT '+json.dumps(result), flush=True)
    Path('/data/fixture/backend-result.json').write_text(json.dumps(result)+'\n')
except BaseException as error:
    print('SV08_QEMU_BACKEND_FAILURE '+repr(error), flush=True)
    subprocess.run(['journalctl', '-b', '-u', 'rauc.service', '-u', KLIPPER, '-u', MOONRAKER, '--no-pager'], check=False)
finally:
    subprocess.run(['systemctl', 'stop', KLIPPER, MOONRAKER, 'rauc.service'], check=False)
    subprocess.run(['systemctl', 'poweroff'], check=False, timeout=20)
