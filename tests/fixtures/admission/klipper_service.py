#!/usr/bin/env python3
"""Disposable guest daemon: real reactor/dispatcher/extension, simulated hardware.

Never a replacement Klipper implementation. Only tests the real systemd/socket
boundary without connecting an MCU or writing any heater/motion commands.
"""
import json
from pathlib import Path
import subprocess
import sys

if ('sv08.test=admission' not in Path('/proc/cmdline').read_text().split() or
        subprocess.check_output(['systemd-detect-virt', '--vm'], text=True).strip() != 'qemu' or
        Path('/sys/block/vda/serial').read_text().strip() != 'SV08-QEMU-DISPOSABLE' or
        json.loads(Path('/usr/lib/sv08/release.json').read_text()).get('deployable') is not False):
    sys.exit('Requires the explicitly identified disposable QEMU fixture')
sys.path.insert(0, '/opt/sv08-admission-test/tests')
from test_update_admission import AdmissionTests

case = AdmissionTests('test_pending_gcode_cannot_start_after_atomic_admission')
case.setUp()
case.extension.path = '/run/sv08/printer_data/comms/update.sock'
case.objects['virtual_sdcard'].is_active = lambda: json.loads(
    Path('/data/fixture/admission-status.json').read_text())['printing']
try:
    case.extension.ready()
    case.reactor.run()
    if case.exit_result != 'exit':
        raise RuntimeError('Unexpected fixture exit: '+str(case.exit_result))
finally:
    case.doCleanups()
