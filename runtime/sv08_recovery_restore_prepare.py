#!/usr/bin/env python3
"""Prepare only reviewed read-only archives and distinct writable ext4 targets."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from contextlib import nullcontext
from sv08_recovery_prepare import PreparationKernel, RecoveryPreparer, find_identity, emit
from sv08_recovery_media import (MediaLease, canonical_json, fingerprint, require, reviewed_inventory,
                                same_identity, trusted_file, PROVIDER_MANIFEST, ENVELOPE_MANIFEST)
from sv08_recovery_restore_media import RestoreMediaProvider, POLICY, CONTEXT, PROTOCOL


def policy_binding(policy):
    value = dict(policy); value['image_manifest_sha256'] = ''
    return fingerprint(value)


class RestorePreparationKernel(PreparationKernel):
    def mount(self, identity, path, options, filesystem):
        fd = self._open_identity(identity,whole=False)
        try:
            subprocess.run(['/bin/mount','--no-canonicalize','-t',filesystem,'-o',options,
                            '/proc/self/fd/'+str(fd),str(path)],pass_fds=(fd,),check=True,timeout=15)
        finally: os.close(fd)


class RestorePreparer(RecoveryPreparer):
    def __init__(self,policy,*,kernel=None,context=CONTEXT,provider_factory=RestoreMediaProvider):
        self.policy, self.kernel, self.context = policy, kernel or RestorePreparationKernel(), Path(context)
        self.provider_factory = provider_factory
        from sv08_recovery_activation import validate_boot
        validate_boot(policy.get('boot'))
        # Constructor validates all choice paths/identities before mutation.
        self.provider_factory(policy,dict(format_version=1,protocol=PROTOCOL,policy_sha256=fingerprint(policy),expected={}))

    def authenticate(self):
        root_device = os.stat('/').st_dev
        args = Path('/proc/cmdline').read_text().split()
        for path,key in ((PROVIDER_MANIFEST,'image_manifest_sha256'),(ENVELOPE_MANIFEST,'envelope_manifest_sha256')):
            data = trusted_file(path); digest = hashlib.sha256(data).hexdigest()
            argument = 'sv08.recovery=' if path == PROVIDER_MANIFEST else 'sv08.envelope='
            require(os.stat(path).st_dev == root_device and digest == self.policy[key] and
                    [a for a in args if a.startswith(argument)] == [argument+digest], 'Restore immutable boot binding changed')
        manifest = json.loads(trusted_file(PROVIDER_MANIFEST))
        require(manifest['inputs'].get('restore_policy') == policy_binding(self.policy), 'Unreviewed restore policy')

    def prepare(self,lease=None):
        mounted, created = [], []
        with (nullcontext(lease) if lease is not None else MediaLease()) as lease:
            try:
                self.context.unlink(missing_ok=True); self.authenticate()
                observed = self.kernel.inventory()
                require(reviewed_inventory(observed) == self.policy['media'], 'Reviewed complete restore inventory changed')
                stable = [disk['stable'] for disk in observed]
                require(all(not same_identity(a,b) for i,a in enumerate(stable) for b in stable[i+1:]), 'Aliased restore inventory')
                recovery = find_identity(observed,self.policy['recovery'])
                selected = []
                for role in ('archives','targets'):
                    for key,spec in self.policy[role].items():
                        block = find_identity(observed,spec['identity'])
                        require(block['partition'] > 0 and block['filesystem'] in (('ext4','vfat') if role == 'archives' else ('ext4',)),
                                'Restore requires reviewed archive filesystem and ext4 target')
                        require(block['disk_device'] != recovery['disk_device'], 'Restore medium aliases recovery disk')
                        if role == 'targets':
                            require(not block['readonly'] and not block['disk_readonly'], 'Target is write protected')
                        selected.append((role,spec,block))
                require(len({b['disk_device'] for _,_,b in selected}) == len(selected), 'Restore media roles alias a whole disk')
                mounts = self.kernel.mounts()
                devices = {v['device'] for disk in observed for v in [disk,*disk['partitions']]}
                require(any(m['path'] == '/' and m['device'] == recovery['device'] for m in mounts) and
                        all(m['device'] not in devices or (m['path'] == '/' and m['device'] == recovery['device']) for m in mounts),
                        'Restore medium already mounted or recovery root differs')
                preflight = self.provider_factory(self.policy,dict(format_version=1,protocol=PROTOCOL,policy_sha256=fingerprint(self.policy),expected={}))
                preflight.kernel = self.kernel
                preflight.snapshot(preparation=True); lease.check()
                for role,spec,block in selected:
                    path = Path(spec['mount'])
                    require(str(path).startswith('/run/sv08-recovery/'+('archives/' if role == 'archives' else 'targets/')),
                            'Unreviewed restore mount path')
                    if role == 'archives': self.kernel.set_readonly(block,emit)
                    created.extend(self.kernel.create_mountpoint(path) or [])
                    options = ('ro,'+('noload,' if block['filesystem'] == 'ext4' else '')+'nosuid,nodev,noexec') if role == 'archives' else 'rw,nosuid,nodev,noexec'
                    # Mount RW ext4 through a held block descriptor: journal replay may write immediately.
                    self.kernel.mount(block,path,options,block['filesystem']); mounted.append(path)
                context = dict(format_version=1,protocol=PROTOCOL,policy_sha256=fingerprint(self.policy),expected={})
                provider = self.provider_factory(self.policy,context); provider.kernel = self.kernel
                context['expected'] = provider.snapshot(); lease.check(); self._publish(context)
                return context
            except BaseException:
                self.context.unlink(missing_ok=True)
                errors = []
                for path in reversed(mounted):
                    try: self.kernel.unmount(path)
                    except BaseException as error: errors.append(str(error))
                for path in reversed(created):
                    try: path.rmdir()
                    except FileNotFoundError: pass
                    except OSError as error: errors.append(str(error))
                if errors: raise RuntimeError('Restore preparation cleanup incomplete: '+'; '.join(errors))
                raise


def main():
    with MediaLease() as lease:
        data = trusted_file(POLICY); policy = json.loads(data)
        require(os.stat(POLICY).st_dev == os.stat('/').st_dev and data == canonical_json(policy), 'Restore policy must be canonical immutable input')
        RestorePreparer(policy).prepare(lease)


if __name__ == '__main__': main()
