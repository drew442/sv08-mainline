"""Finite recovery owner setup using the existing verified restore admission."""
import hashlib
import json
import os
from pathlib import Path
from sv08_export import opened, identity
from sv08_owner import Owner, require
from sv08_state import Store
from sv08_recovery_activation import boot_guard

ACTION = 'recovery.owner'
STATES = {'current': 'Current state', 'fresh': 'Fresh state', 'restored': 'Restored state'}


class RecoveryOwner:
    def __init__(self, targets, admission, root_uid=0, reserve_bytes=512*1024**2):
        self.targets, self.admission, self.root_uid = targets, admission, root_uid
        self.reserve_bytes = reserve_bytes

    def root(self, target, state):
        require(target in self.targets and state in STATES, 'Choose configured storage and state.')
        spec = self.targets[target]; mount = Path(spec['mount'])
        root = mount/'sv08' if state == 'current' else Path(spec['fresh_root']) if state == 'fresh' else Path(spec['root'])/'sv08'
        require(root != mount and root.is_relative_to(mount), 'Owner state must be below the reviewed target.')
        boot_guard(mount)
        Store(root).load()  # Read only. Missing or damaged state is never created.
        return root

    def inspect(self, target, state, reset, guard):
        root = self.root(target, state)
        with opened(root) as fd: stamp = list(identity(os.fstat(fd)))
        state_revision = hashlib.sha256(json.dumps(Store(root).load(),sort_keys=True).encode()).hexdigest()
        fs = os.statvfs(root)
        require(fs.f_bavail*fs.f_frsize >= self.reserve_bytes+4096 and fs.f_favail >= 2,
                'Insufficient owner enrollment space or inode reserve.')
        owner = Owner(root, self.root_uid).status()
        require(owner['enrolled'] == reset,
                'This state already has an owner. Choose explicit password reset.' if owner['enrolled'] else
                'This state has no owner. Choose initial password setup.')
        guard.recheck()
        return dict(target=target, state=state, reset=reset, owner=owner, root_stamp=stamp,
                    media_fingerprint=guard.fingerprint, state_revision=state_revision)

    def prepare(self, arguments):
        with self.admission(arguments['target']) as guard:
            return self.inspect(arguments['target'], arguments['state'], arguments['reset'], guard)

    def execute(self, review, password, confirmation):
        with self.admission(review['target']) as guard:
            require(self.inspect(review['target'], review['state'], review['reset'], guard) == review,
                    'Storage or owner enrollment changed; review again.')
            Owner(self.root(review['target'], review['state']), self.root_uid).save(
                password, confirmation, review['owner'], review['reset'], guard.recheck)
            guard.recheck()
        return dict(message='Owner password saved for sv08. Fresh or restored state still requires explicit activation. '
                    'The password takes effect at the next normal boot; running authentication is unchanged. Sign in to Cockpit as sv08. Change it through local recovery password reset.')
