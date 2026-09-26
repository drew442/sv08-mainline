#!/usr/bin/python3
"""Emit bounded boot-health diagnostics only in the disposable QEMU fixture."""
import subprocess
from pathlib import Path


for command in (['/usr/bin/systemctl', 'status', '--no-pager', 'sv08-boot-health.service'],
                ['/usr/bin/journalctl', '-b', '-u', 'sv08-boot-health.service', '--no-pager']):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False, timeout=15)
    print('SV08_QEMU_BOOT_HEALTH_DIAGNOSTIC ' + ' '.join(command), flush=True)
    print(result.stdout, flush=True)
failure_dir = Path('/data/sv08/shared/logs/journal/boot-health')
for path in sorted(failure_dir.glob('*.json')) if failure_dir.is_dir() else ():
    print('SV08_QEMU_BOOT_HEALTH_DETAIL ' + path.read_text(), flush=True)
fallback = Path('/run/sv08/qemu-fallback-requested.json')
if fallback.is_file():
    print('SV08_QEMU_FALLBACK_REQUEST ' + fallback.read_text(), flush=True)
print('SV08_QEMU_BOOT_HEALTH_FAILURE service did not create the ready marker', flush=True)
subprocess.run(['/usr/bin/systemctl', 'poweroff'], check=False, timeout=15)
