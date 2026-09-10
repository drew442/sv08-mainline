#!/usr/bin/env python3
"""Crash-recoverable ordering for paired installation, boot selection and state.

Integration library, not a hardware CLI. The caller must provide a validated RAUC
backend, authenticated bundle proof and quiescence/health checks. No default check
assumes an idle or healthy printer. See ADR 0006 and transaction regression tests.
"""
import json
import re
import uuid
from sv08_state import atomic_json, identifier


class Transaction:
    def __init__(self, store, backend, admission):
        self.store, self.backend, self.admission = store, backend, admission
        self.path = store.root / 'update.json'

    def load(self):
        if self.path.is_symlink():
            raise ValueError('Update journal must not be a symlink')
        if not self.path.exists():
            return None
        tx = json.loads(self.path.read_text())
        if tx['format_version'] != 1 or tx['phase'] not in (
                'installing', 'staged', 'arming', 'armed', 'confirming', 'complete', 'cancelled', 'failed'):
            raise ValueError('Unsupported update journal')
        if tx['slot'] not in ('A', 'B') or tx['previous_slot'] not in ('A', 'B') or tx['slot'] == tx['previous_slot']:
            raise ValueError('Invalid transaction slots')
        for name in ('id', 'release', 'previous_release', 'boot_id'):
            identifier(tx[name])
        if not re.fullmatch('[0-9a-f]{64}', tx['bundle_sha256']):
            raise ValueError('Invalid bundle identity')
        return tx

    def save(self, tx, phase):
        tx['phase'] = phase
        atomic_json(self.path, tx)

    def require_source(self, state, boot):
        record = state['slots'].get(boot['slot'])
        if not record or record['release'] != boot['release']:
            raise ValueError('Running release differs from state registry')
        if (boot['mode'] != 'immutable' or state['requested_mode'] != 'immutable' or
                any(record['customized'] for record in state['slots'].values())):
            raise ValueError('Customized/writable slots require reconciliation before image replacement')
        self.backend.validate_context(boot)
        # Must obtain a shared admission lease and inspect service/print state;
        # the callback's context manager keeps the lease through the operation.

    def stage(self, bundle, proof, boot):
        identifier(proof['release'])
        if not re.fullmatch('[0-9a-f]{64}', proof['bundle_sha256']):
            raise ValueError('Missing authenticated bundle identity')
        with self.store.locked(), self.admission():
            state = self.store.load()
            self.require_source(state, boot)
            previous = self.load()
            if state['pending'] or previous and previous['phase'] not in ('complete', 'cancelled', 'failed'):
                raise ValueError('Resolve the outstanding transaction before staging')
            if any(record['release'] == proof['release'] for record in state['slots'].values()):
                raise ValueError('Use a unique new release; reinstalling an existing generation is not supported')
            self.store.check_copy_budget(state['slots'][boot['slot']], reserve_full_copy=True)
            target = 'B' if boot['slot'] == 'A' else 'A'
            if self.backend.primary() != boot['slot']:
                raise ValueError('Boot selection differs from the running source')
            tx = dict(format_version=1, id=uuid.uuid4().hex, phase='installing',
                      slot=target, previous_slot=boot['slot'], previous_release=boot['release'],
                      release=proof['release'], bundle_sha256=proof['bundle_sha256'],
                      boot_id=identifier(boot['boot_id']))
            self.save(tx, 'installing')
            # Backend must verify this exact proof/file and both inactive hashes,
            # preserve source devices, and use activate-installed=false.
            self.backend.install(bundle, proof, target)
            if self.backend.primary() != boot['slot'] or self.backend.good(target):
                raise ValueError('Installer must retain the source primary and leave target bad')
            self.save(tx, 'staged')
            return tx

    def arm(self, boot):
        with self.store.locked(), self.admission():
            state, tx = self.store.load(), self.load()
            self.require_source(state, boot)
            if (not tx or tx['phase'] not in ('staged', 'arming', 'armed') or
                    boot['slot'] != tx['previous_slot'] or boot['release'] != tx['previous_release'] or
                    boot['boot_id'] != tx['boot_id']):
                raise ValueError('Activation requires the original staging boot; reconcile after a reboot')
            if state['pending'] and (state['pending']['id'] != tx['id'] or
                    state['pending']['phase'] != 'armed' or state['pending']['slot'] != tx['slot'] or
                    state['pending']['release'] != tx['release']):
                raise ValueError('Another state trial is pending')
            if tx['phase'] == 'armed':
                if not state['pending'] or self.backend.primary() != tx['slot']:
                    raise ValueError('Armed state/bootloader disagreement requires reconciliation')
                return tx  # Never replenish an already armed trial's counters.
            self.save(tx, 'arming')
            state['pending'] = dict(slot=tx['slot'], release=tx['release'],
                                    previous_slot=tx['previous_slot'], phase='armed', id=tx['id'])
            self.store.save(state)  # Durable before any bootloader selection.
            self.backend.mark_active(tx['slot'])
            if self.backend.primary() != tx['slot'] or not self.backend.good(tx['slot']):
                raise ValueError('Bootloader did not select the staged trial')
            self.save(tx, 'armed')
            return tx

    def cancel(self, boot):
        """Disarm before clearing pending state; interrupted calls are retryable."""
        with self.store.locked(), self.admission():
            state, tx = self.store.load(), self.load()
            if not tx or tx['phase'] in ('complete', 'cancelled', 'failed'):
                return tx
            self.backend.validate_context(boot)
            if boot['slot'] != tx['previous_slot'] or boot['release'] != tx['previous_release']:
                raise ValueError('Cannot cancel from the target slot; boot the preserved source')
            pending = state['pending']
            if pending and (pending['id'] != tx['id'] or pending['phase'] != 'armed'):
                raise ValueError('Prepare fallback state before cancelling a started trial')
            self.backend.mark_bad(tx['slot'])
            if self.backend.good(tx['slot']) or self.backend.primary() == tx['slot']:
                raise ValueError('Bootloader did not disarm the target')
            state['pending'] = None
            self.store.save(state)
            failed = state.get('last_failed_trial', {}).get('id') == tx['id']
            self.save(tx, 'failed' if failed else 'cancelled')
            return tx

    def confirm(self, boot, health):
        """Health callback must check this boot; success is never inferred here."""
        with self.store.locked(), self.admission():
            state, tx = self.store.load(), self.load()
            if (not tx or tx['phase'] not in ('armed', 'confirming') or
                    boot['slot'] != tx['slot'] or boot['release'] != tx['release']):
                raise ValueError('No matching running trial')
            self.require_source(state, boot)
            pending = state['pending']
            if pending is not None and (pending['id'] != tx['id'] or pending['phase'] != 'trial'):
                raise ValueError('Trial state has not been prepared')
            if pending is None and tx['phase'] != 'confirming':
                raise ValueError('Missing trial state')
            if health(boot) is not True:
                raise ValueError('Trial health has not passed')
            self.save(tx, 'confirming')
            self.backend.mark_good(tx['slot'])  # Durable before application gate release.
            # The last running attempt has already consumed its counter. Its
            # next primary may therefore be the fallback until mark-good resets
            # the counter. Check resulting priority only after that write.
            if not self.backend.good(tx['slot']) or self.backend.primary() != tx['slot']:
                raise ValueError('Bootloader did not confirm the target as primary')
            state['pending'] = None
            self.store.save(state)
            self.save(tx, 'complete')
            # Caller may release /run/sv08/trial only after this returns.
            return tx
