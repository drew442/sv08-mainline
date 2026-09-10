#!/usr/bin/env python3
"""Read-only backend admission probe, exclusively for the disposable ARM64 VM."""
import json
from pathlib import Path
import subprocess
import sys

if (sys.argv[1:] != ['--execute'] or
        'sv08.test=rauc-backend' not in Path('/proc/cmdline').read_text().split() or
        subprocess.check_output(['systemd-detect-virt', '--vm'], text=True).strip() != 'qemu' or
        Path('/sys/block/vda/serial').read_text().strip() != 'SV08-QEMU-DISPOSABLE'):
    sys.exit('Requires the identified disposable QEMU guest and --execute')
sys.path.insert(0, '/usr/lib/sv08')
from sv08_rauc import Backend


def read(name):
    return json.loads(Path('/usr/lib/sv08', name).read_text())


try:
    backend = Backend(read('release.json'), read('test-update-policy.json'),
        read('test-image-layout.json'), read('test-environment-layout.json'), fixture=True)
    boot = json.loads(Path('/run/sv08/boot.json').read_text())
    boot['boot_id'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    negative = 'sv08.test=bad-gpt' in Path('/proc/cmdline').read_text().split()
    try:
        backend.validate_context(boot)
    except ValueError as error:
        if not negative or 'Environment overlaps GPT' not in str(error):
            raise
    else:
        if negative:
            raise AssertionError('Overlapping GPT was admitted')
    print('SV08_QEMU_GPT_RESULT '+json.dumps(dict(passed=True,
        overlapping_gpt=negative, backend_writes=False, physical_hardware=False)), flush=True)
except BaseException as error:
    print('SV08_QEMU_GPT_FAILURE '+repr(error), flush=True)
finally:
    subprocess.run(['systemctl', 'poweroff'], check=False, timeout=20)
