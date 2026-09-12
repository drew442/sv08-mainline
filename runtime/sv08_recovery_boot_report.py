#!/usr/bin/env python3
"""Read-only serial recovery startup evidence; no device or registry mutation.

Custom boot-integration diagnostic; retire with equivalent distro reporting.
"""
import json
import os
from pathlib import Path
import subprocess
import time
from sv08_recovery import installed_controller


def report():
    processes=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        except (OSError,ProcessLookupError):continue
        if '/usr/bin/X' in command or 'sv08_recovery_ui.py' in command or 'at-spi' in command or 'dbus-daemon' in command:
            processes.append(dict(pid=int(p.name),command=command))
    unit=subprocess.run(['systemctl','show','sv08-recovery-display.service','--property=ActiveState,SubState,MainPID,NRestarts'],check=True,capture_output=True,text=True,timeout=10).stdout
    failures=subprocess.run(['systemctl','--failed','--no-legend','--no-pager'],check=True,capture_output=True,text=True,timeout=10).stdout
    result=dict(failed_units=failures,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),kernel=os.uname().release,
                status=installed_controller().status(),registry_exists=Path('/data/sv08').exists(),
                mounts=Path('/proc/self/mountinfo').read_text().splitlines(),
                memory=Path('/proc/meminfo').read_text().splitlines(),processes=processes,display_unit=unit,
                envelope_binding=Path('/run/sv08/recovery-verified').read_text().strip())
    Path('/run/sv08/boot-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print('SV08_RECOVERY_BOOT_REPORT '+json.dumps(result,sort_keys=True),flush=True)
    return result


if __name__=='__main__':
    # Permit Xorg, input and the accessibility bus to settle. This reports actual
    # process/unit state, including failure, rather than asserting UI readiness.
    time.sleep(20)
    report()
