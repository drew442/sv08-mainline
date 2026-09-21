#!/usr/bin/env python3
"""Recovery UI controller that works without a healthy writable data registry.

Reading state is diagnostic only. A separately verified recovery adapter owns
partition identity, signed restore and boot-selection operations. Never borrow
host A/B assumptions or initialize missing state in recovery.
"""
import threading

from sv08_admin import ACTIONS, RECOVERY_ACTIONS, Controller, revision


def installed_controller():
    from sv08_recovery_media import MediaProvider, production_adapter
    from sv08_state import Store
    def refresh():
        adapter = production_adapter()
        # A successful trust refresh also selects the configured data source for
        # diagnostics. A failed refresh never invents a source path.
        store = Store(adapter.source / 'sv08') if isinstance(adapter, MediaProvider) else None
        return adapter, store
    return RecoveryController(Store('/data/sv08'), adapter_factory=refresh)


class RecoveryController(Controller):
    def __init__(self, store, adapter=None, adapter_factory=None):
        super().__init__(store, {}, 'recovery', adapter)
        self._adapter_factory = adapter_factory
        self._adapter_lock = threading.RLock()

    def status(self):
        with self._adapter_lock:
            if self._adapter_factory is not None:
                adapter, store = self._adapter_factory()
                self.adapter = adapter
                if store is not None:
                    self.store = store
            return self._status()

    def _status(self):
        try:
            state = self.store.load()  # No lock file creation on read-only data.
            diagnostic = 'The state registry is readable. Physical partition health has not been verified.'
        except (OSError, ValueError, KeyError, TypeError) as error:
            state = None
            diagnostic = 'The state registry is unavailable or damaged. No initialization or repair was attempted: '+str(error)
        view = dict(context='recovery', state=state, diagnostic=diagnostic)
        capabilities = {}
        for action in ACTIONS:
            if action == 'recovery.check':
                available, reason = True, ''
            elif action in RECOVERY_ACTIONS and self.adapter:
                available, reason = self.adapter.capability(action, view)
            else:
                available = False
                reason = ('Available after the verified recovery backend is integrated.' if action in RECOVERY_ACTIONS
                          else 'Available in the running host.')
            capabilities[action] = dict(available=available, reason=reason)
        return dict(context='recovery', revision=revision(view), boot={},
                    requested_mode=None, auto_update=None, slots=state['slots'] if state else {},
                    pending=state['pending'] if state else None, transaction=None,
                    free_bytes=None, capabilities=capabilities, diagnostic=diagnostic,
                    catalog=[], hostname='Recovery',
                    images=self.adapter.images() if self.adapter else [],
                    destinations=self.adapter.destinations() if self.adapter else [])

    def plan(self, action, arguments):
        with self._adapter_lock:
            plan = super().plan(action, arguments)
            if action == 'recovery.export':
                if self.adapter is None or not hasattr(self.adapter, 'review_export'):
                    raise ValueError('Export preflight is unavailable')
                plan['export'] = self.adapter.review_export(arguments['destination'])
                detail = plan['export']
                plan['effect'] = (f"Save user data to {detail['label']}. Allow up to "
                                  f"{detail['required_bytes'] / 1024**2:.1f} MiB for {detail['entries']} entries. "
                                  'The archive includes private configuration and credentials. Keep the destination private. '
                                  'The source and existing destination files are preserved.')
            return plan

    def apply(self, plan):
        with self._adapter_lock:
            if not isinstance(plan, dict) or plan != self.plan(plan.get('action'), plan.get('arguments')):
                raise ValueError('Recovery state changed. Review the operation again.')
            if plan['action'] == 'recovery.check':
                return dict(message=self.status()['diagnostic'])
            if self.adapter is None: raise ValueError('Verified recovery backend unavailable')
            return self.adapter.apply(plan)
