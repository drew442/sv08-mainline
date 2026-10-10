#!/usr/bin/env python3
"""One durable controlled restart for an authenticated automatic transaction.

The reboot receipt records dispatch uncertainty, never health. Existing boot
preparation and health own confirmation/fallback. Caller retries may perform
fresh idle admission only before dispatch could have reached systemd.
"""
import json
from pathlib import Path
from sv08_state import atomic_json
from sv08_restart import controlled_restart, require_restart, require_running
from sv08_update_policy import effective, policy_revision

STATES = {'ready', 'dispatching', 'queued', 'uncertain', 'suppressed', 'observed'}


class AutoReboot:
    def __init__(self, store, transaction, boot, *, network=None, command=None, admission=None):
        self.store, self.tx, self.boot = store, transaction, boot
        if network is None:
            from sv08_network import Network
            network = Network(store.root, runtime=store.runtime, boot_id=store.boot_id, budget=store.budget)
        self.network = network
        self.command = command or network.command
        self.admission = admission
        self.path = store.root / 'automatic-reboot.json'

    def load(self):
        if self.path.is_symlink(): raise ValueError('Invalid automatic reboot receipt')
        if not self.path.exists(): return None
        if self.path.stat().st_size > 4096: raise ValueError('Invalid automatic reboot receipt')
        record = json.loads(self.path.read_text())
        keys = {'format_version', 'id', 'boot_id', 'slot', 'release', 'policy_revision', 'state', 'shutdown_id'}
        if (not isinstance(record, dict) or set(record) != keys or record['format_version'] != 1 or
                record['state'] not in STATES or record['slot'] not in ('A', 'B') or
                any(not isinstance(record[k], str) or not 0 < len(record[k]) <= 80
                    for k in ('id', 'boot_id', 'release', 'policy_revision')) or
                not isinstance(record['shutdown_id'], str) or len(record['shutdown_id']) not in (0, 32)):
            raise ValueError('Invalid automatic reboot receipt')
        return record

    def save(self, record, state, intent=None):
        record = dict(record, state=state)
        if intent: record['shutdown_id'] = intent['id']
        atomic_json(self.path, record)
        return record

    def run(self):
        # Shared order: state -> network/allocation -> idle admission. Holding
        # state through dispatch excludes policy edits and competing image jobs.
        with self.store.locked(nonblocking=True), self.network.locked():
            record = self.load()
            tx = self.tx.load()
            boot_id = self.store.boot_id.read_text().strip()
            if (record and tx and tx['id'] != record['id'] and
                    record['state'] in ('ready', 'suppressed')):
                # A new admitted transaction can replace only a terminal
                # predecessor. These states precede dispatch; an outstanding
                # shutdown barrier still refuses replacement after interruption.
                require_running(self.store.runtime, self.store.boot_id)
                record = None
            if record and record['boot_id'] != boot_id and record['state'] == 'observed' and tx and tx['id'] != record['id']:
                record = None  # A prior, reconciled update does not block future releases.
            if record and record['boot_id'] != boot_id:
                if tx and tx['id'] == record['id'] and tx['phase'] in ('complete', 'failed', 'cancelled'):
                    self.save(record, 'observed')
                    return 'reboot-observed'
                return 'awaiting-health-reconciliation'
            if record and record['state'] in ('dispatching', 'queued', 'uncertain'):
                return 'reboot-queued' if record['state'] == 'queued' else 'reboot-uncertain'
            if not tx or tx['phase'] != 'armed' or tx.get('automatic') is not True:
                raise ValueError('Automatic restart requires an armed automatic transaction')
            expected = dict(format_version=1, id=tx['id'], boot_id=tx['boot_id'], slot=tx['slot'],
                            release=tx['release'], policy_revision=tx['policy_revision'],
                            state='ready', shutdown_id='')
            if record and any(record[k] != expected[k] for k in ('id', 'boot_id', 'slot', 'release', 'policy_revision')):
                raise ValueError('Automatic reboot receipt differs from transaction; reconcile first')
            if tx['boot_id'] != boot_id: raise ValueError('Automatic transaction belongs to another boot')
            state = self.store.load()
            if not state['auto_update']:
                self.save(expected, 'suppressed')
                return 'reboot-suppressed'
            options = effective(state.get('update_policy'), automatic=True)
            if policy_revision(options) != tx['policy_revision']:
                raise ValueError('Automatic policy changed after staging; cancel or reconcile the transaction')
            if tx['update_policy'] != options or tx['admission_proof'].get('signer_trusted') is not True:
                raise ValueError('Automatic restart lacks trusted admission proof')
            require_running(self.store.runtime, self.store.boot_id)
            require_restart(self.store)
            self.tx.require_source(state, self.boot, policy=options)
            if self.network.pending(): raise ValueError('Confirm or roll back network changes before restarting')
            record = self.save(expected, 'ready')
            controlled_restart(self.command, self.store.runtime, self.store.boot_id, self.admission,
                               before_dispatch=lambda value: self.save(record, 'dispatching', value),
                               acknowledged=lambda value: self.save(record, 'queued', value),
                               launch_failed=lambda value: self.save(record, 'ready'),
                               uncertain=lambda value: self.save(record, 'uncertain', value))
            return 'reboot-queued'
