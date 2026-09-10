#!/usr/bin/env python3
"""Guest-only A -> B -> A state probe; the host harness selects each kernel root.

This verifies Linux/state integration, not automatic boot selection or health.
Only a disposable QEMU disk with an explicit test serial is accepted.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--execute', action='store_true')
a = p.parse_args()
if not a.execute:
    sys.exit('Inspection only; requires --execute inside the disposable guest')
if subprocess.check_output(['systemd-detect-virt', '--vm'], text=True).strip() != 'qemu':
    sys.exit('Requires QEMU')
if Path('/sys/block/vda/serial').read_text().strip() != 'SV08-QEMU-DISPOSABLE':
    sys.exit('Unexpected disk')
if json.loads(Path('/usr/lib/sv08/release.json').read_text()).get('deployable') is not False:
    sys.exit('Refusing deployable image')
sys.path.insert(0, '/usr/lib/sv08')
from sv08_state import Store

try:
    store = Store('/data/sv08')
    boot = json.loads(Path('/run/sv08/boot.json').read_text())
    phasefile = store.root / 'qemu-rollback-phase'
    phase = int(phasefile.read_text()) if phasefile.exists() else 0
    assert boot['slot'] == ['A', 'B', 'A'][phase], boot
    assert boot['trial'] == (phase == 1), boot
    assert boot['mode'] == 'immutable' and not boot['customized']
    assert Path('/run/sv08/trial').exists() == (phase == 1)
    config = Path(boot['generation']) / 'config/rollback.cfg'
    db = Path(boot['generation']) / 'database/rollback.db'
    shared = store.root / 'shared/gcodes/rollback-test.gcode'
    state = store.load()
    if phase == 0:
        config.write_text('before staging')
        with sqlite3.connect(db) as connection:
            connection.execute('CREATE TABLE proof(value TEXT)')
            connection.execute("INSERT INTO proof VALUES ('before staging')")
        store.expect_trial('B', '0.1.0-offline.4', 'A')
        # Writes after staging must appear in B's first-boot copy.
        config.write_text('late A write')
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE proof SET value='late A database'")
        shared.write_text('; shared artifact from A\n')
        (store.root / 'qemu-rollback-machine-id').write_text(Path('/etc/machine-id').read_text())
    elif phase == 1:
        assert config.read_text() == 'late A write'
        with sqlite3.connect(db) as connection:
            assert connection.execute('SELECT value FROM proof').fetchone() == ('late A database',)
        assert config.stat().st_uid == db.stat().st_uid == 1000
        previous = store.generation_path(state['slots']['A'])
        assert str(previous) != boot['generation']
        config.write_text('B trial change')
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE proof SET value='B trial database'")
        assert (previous / 'config/rollback.cfg').read_text() == 'late A write'
        shared.write_text('; shared artifact changed in B\n')
        # Intentionally leave trial unconfirmed; next host-selected boot is A.
    else:
        assert config.read_text() == 'late A write', 'Fallback lost its original generation'
        with sqlite3.connect(db) as connection:
            assert connection.execute('SELECT value FROM proof').fetchone() == ('late A database',)
        assert shared.read_text() == '; shared artifact changed in B\n'
        assert state['pending'] is None and state['last_failed_trial']['slot'] == 'B'
        failed = store.generation_path(state['slots']['B'])
        assert (failed / 'config/rollback.cfg').read_text() == 'B trial change'
    assert Path('/etc/machine-id').read_text() == (store.root / 'qemu-rollback-machine-id').read_text()
    rootdev = subprocess.check_output(['findmnt', '-n', '-o', 'SOURCE', '--mountpoint', '/'], text=True).strip()
    bootdev = subprocess.check_output(['findmnt', '-n', '-o', 'SOURCE', '--mountpoint', '/boot'], text=True).strip()
    assert rootdev == ['/dev/vda2', '/dev/vda4', '/dev/vda2'][phase], rootdev
    assert bootdev == ['/dev/vda1', '/dev/vda3', '/dev/vda1'][phase], bootdev
    failed = subprocess.check_output(['systemctl', '--failed', '--no-legend', '--plain'], text=True).strip()
    assert not failed, failed
    result = dict(phase=phase, slot=boot['slot'], trial=boot['trial'],
                  paired_mounts=True, late_copy_and_fallback=True, passed=True,
                  automatic_boot_selection_tested=False)
    print('SV08_QEMU_ROLLBACK_RESULT '+json.dumps(result), flush=True)
    (store.root / f'qemu-rollback-result-{phase}.json').write_text(json.dumps(result)+'\n')
    phasefile.write_text(str(phase+1))
except BaseException as error:
    print('SV08_QEMU_ROLLBACK_FAILURE '+repr(error), flush=True)
finally:
    subprocess.run(['systemctl', 'poweroff'], timeout=20, check=False)
