#!/usr/bin/env python3
"""Host administration adapter for the existing verified A/B transaction layer.

No recovery-mode shortcut or disk paths from the UI. An image is addressed by its
private upload digest; the fixed backend identifies actual devices independently.
"""
from contextlib import contextmanager
from sv08_admin import revision, snapshot
from sv08_bundle import inspect as inspect_bundle
from sv08_transaction import Transaction


class HostImages:
    def __init__(self, store, boot, backend, staging, admission, verify=None):
        self.store, self.boot, self.backend = store, boot, backend
        self.staging, self.admission = staging, admission
        self.verify = verify or (lambda path: inspect_bundle(path, backend.policy, backend.keyring, lease_fd=staging.lease_fd))

    def catalog(self): return []
    def destinations(self): return []
    def hostname(self):
        path = self.store.root / 'system/hostname'
        return path.read_text().strip() if path.is_file() else 'Not configured'

    def images(self):
        # An upload is reauthenticated when staging. Listing never asserts trust.
        return [{'id': p.stem, 'label': 'Uploaded image '+p.stem[:12]+'… (verification required)'}
                for p in sorted(self.staging.root.glob('*.raucb'))
                if len(p.stem) == 64 and all(c in '0123456789abcdef' for c in p.stem)]

    def capability(self, action, view, leased=False):
        if action not in ('image.stage', 'image.arm', 'image.cancel'):
            return False, 'This operation requires its reviewed host service integration.'
        if self.backend.manifest.get('deployable') is not True:
            return False, 'The board image is not approved for hardware writes.'
        state, tx, boot = view['state'], view['transaction'], view['boot']
        live = tx and tx['phase'] not in ('complete', 'cancelled', 'failed')
        if action == 'image.cancel':
            if live and boot['slot'] == tx['previous_slot'] and boot['release'] == tx['previous_release']:
                return True, ''
            return False, 'No cancellable update is running from the preserved source.'
        if boot['mode'] != 'immutable' or state['requested_mode'] != 'immutable' or any(r['customized'] for r in state['slots'].values()):
            return False, 'Image replacement requires immutable mode and reconciliation of all customizations.'
        if action == 'image.stage':
            if not leased and self.staging.busy():
                return False, 'Bundle intake or another upload lease is active; wait before staging.'
            return (False, 'Finish or cancel the pending update first.') if live or state['pending'] else (True, '')
        if (live and tx['phase'] == 'staged' and boot['slot'] == tx['previous_slot'] and
                boot['release'] == tx['previous_release'] and boot['boot_id'] == tx['boot_id']):
            return True, ''
        return False, 'Stage a release in this boot before selecting it for the next boot.'

    def apply(self, plan):
        @contextmanager
        def admitted():
            # Transaction acquired the state lock already; no nested status call.
            view = snapshot(self.store, self.boot, 'host')
            if revision(view) != plan['revision']:
                raise ValueError('System state changed. Refresh and review again.')
            allowed, reason = self.capability(plan['action'], view, leased=plan['action'] == 'image.stage')
            if not allowed: raise ValueError(reason)
            with self.admission(): yield
        tx = Transaction(self.store, self.backend, admitted)
        if plan['action'] == 'image.stage':
            tx.stage_upload(self.staging, plan['arguments']['digest'], self.verify, self.boot)
            message = 'Image verified and staged. The current system remains selected.'
        elif plan['action'] == 'image.arm':
            tx.arm(self.boot)
            message = 'Staged image selected for the next normal boot. No restart was requested.'
        elif plan['action'] == 'image.cancel':
            tx.cancel(self.boot)
            message = 'Update cancelled. The preserved source remains selected.'
        else:
            raise ValueError('Unsupported image operation')
        return dict(message=message)
