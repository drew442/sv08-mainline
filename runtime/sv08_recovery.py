#!/usr/bin/env python3
"""Recovery UI controller that works without a healthy writable data registry.

Reading state is diagnostic only. A separately verified recovery adapter owns
partition identity, signed restore and boot-selection operations. Never borrow
host A/B assumptions or initialize missing state in recovery.
"""
from sv08_admin import ACTIONS, RECOVERY_ACTIONS, Controller, revision


class RecoveryController(Controller):
    def __init__(self, store, adapter=None):
        super().__init__(store, {}, 'recovery', adapter)

    def status(self):
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

    def apply(self, plan):
        if not isinstance(plan, dict) or plan != self.plan(plan.get('action'), plan.get('arguments')):
            raise ValueError('Recovery state changed. Review the operation again.')
        if plan['action'] == 'recovery.check':
            return dict(message=self.status()['diagnostic'])
        if self.adapter is None: raise ValueError('Verified recovery backend unavailable')
        return self.adapter.apply(plan)
