#!/usr/bin/env python3
"""Guest-only boot probe for a disposable QEMU image; never install on a printer.

Reports through the serial console and powers off the virtual machine. The
fixture creator must install its temporary service only in the disposable root.
"""
import errno
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import socket
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--execute', action='store_true')
parser.add_argument('--with-package', action='store_true')
args = parser.parse_args()
if not args.execute:
    print('Inspection only: this probe requires --execute inside a disposable QEMU guest.')
    sys.exit(0)
if subprocess.check_output(['systemd-detect-virt', '--vm'], text=True).strip() != 'qemu':
    sys.exit('Refusing to run outside a QEMU virtual machine')
if json.loads(Path('/usr/lib/sv08/release.json').read_text()).get('deployable') is not False:
    sys.exit('Refusing to run on a deployable image')

sys.path.insert(0, '/usr/lib/sv08')
from sv08_state import Store

try:
    store = Store('/data/sv08')
    boot = json.loads(Path('/run/sv08/boot.json').read_text())
    phase_path = Path('/data/sv08/qemu-test-phase')
    phase = int(phase_path.read_text()) if phase_path.exists() else 0
    expected = ['immutable', 'writable', 'immutable'][phase]
    assert boot['mode'] == expected, boot
    try:
        Path('/etc/qemu-root-write-test').write_text('customization')
        assert expected == 'writable', 'Immutable root accepted a write'
    except OSError as error:
        assert expected == 'immutable' and error.errno == errno.EROFS, str(error)
    if args.with_package:
        command = ['sv08-package', '--execute', 'install', '--yes', '/data/fixture/sv08-qemu-proof.deb']
        if phase == 0:
            rejected = subprocess.run(command, capture_output=True, text=True)
            assert rejected.returncode != 0 and 'writable mode' in rejected.stderr, rejected.stderr
            assert not Path('/usr/share/sv08-qemu/proof').exists()
        elif phase == 1:
            subprocess.run(command, check=True)
            assert Path('/run/sv08/qemu-package-service-started').exists(), 'Runtime package service activation was blocked'
        if phase:
            assert Path('/usr/share/sv08-qemu/proof').read_text() == 'slot-local package artifact\n'
            assert subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', 'sv08-qemu-proof'], text=True) == '1.0'
    config = Path('/run/sv08/printer_data/config/qemu-persistence.cfg')
    if phase:
        assert config.read_text() == str(phase-1), 'State did not persist'
    config.write_text(str(phase))
    identity = Path('/etc/machine-id').read_text().strip()
    assert identity == Path('/data/sv08/system/machine-id').read_text().strip()
    old_identity = Path('/data/sv08/qemu-identity')
    if old_identity.exists():
        assert old_identity.read_text() == identity, 'Identity changed between boots'
    old_identity.write_text(identity)
    assert socket.gethostname() == Path('/data/sv08/system/hostname').read_text().strip()
    keyhash = hashlib.sha256(Path('/data/sv08/system/ssh/ssh_host_ed25519_key').read_bytes()).hexdigest()
    old_key = Path('/data/sv08/qemu-ssh-keyhash')
    if old_key.exists():
        assert old_key.read_text() == keyhash, 'SSH host key changed between boots'
    old_key.write_text(keyhash)
    journal = subprocess.check_output(['journalctl', '-b', '-o', 'json', '--no-pager'], text=True)
    ids = {json.loads(line).get('_MACHINE_ID') for line in journal.splitlines()}
    ids.discard(None)
    assert ids == {identity}, ('PID 1 journal identity differs', ids, identity)
    failed = subprocess.check_output(['systemctl', '--failed', '--no-legend', '--plain'], text=True).strip()
    assert not failed, ('Failed system services', failed)
    subprocess.run(['systemctl', 'is-active', '--quiet', 'systemd-logind.service'], check=True)
    if phase == 2:
        assert Path('/etc/qemu-root-write-test').read_text() == 'customization'
        assert boot['customized'], 'Customization status was lost'
    result = {'phase': phase, 'mode': expected, 'persistent_identity': True,
              'journal_identity': True, 'persistent_config': True,
              'persistent_hostname_and_ssh_key': True,
              'package_workflow_tested': args.with_package,
              'customization_preserved': boot['customized'], 'passed': True}
    print('SV08_QEMU_RESULT '+json.dumps(result), flush=True)
    (Path('/data/sv08') / f'qemu-result-{phase}.json').write_text(json.dumps(result)+'\n')
    if phase < 2:
        store.policy(mode=['writable', 'immutable'][phase])
        phase_path.write_text(str(phase+1))
        Path('/data/sv08/system/hostname').write_text('sv08-qemu-owner\n')
except BaseException as error:
    print('SV08_QEMU_FAILURE '+repr(error), flush=True)
    subprocess.run(['journalctl', '-b', '-u', 'systemd-logind.service', '--no-pager'], check=False)
finally:
    try:
        subprocess.run(['systemctl', 'poweroff'], check=True, timeout=20)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        subprocess.run(['systemctl', '--force', 'poweroff'], check=False)
