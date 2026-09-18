#!/usr/bin/env python3
"""Prepare the one reviewed recovery-export topology and publish observations.

Policy is immutable input.  This program never derives trust from discovered
devices: it compares a complete supported inventory to the reviewed policy,
then mounts only the policy-selected source and destination while holding the
same MediaLease used by export.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from contextlib import nullcontext

from sv08_recovery_media import (CONTEXT, ENVELOPE_MANIFEST, POLICY,
                                 PROVIDER_MANIFEST, Kernel, MediaLease, MediaProvider,
                                 PROTOCOL, WRITER_MODEL, canonical_json,
                                 fingerprint, require, reviewed_inventory, same_identity,
                                 trusted_file, validate_usr_loop_inventory)


def emit(event, **fields):
    print('SV08_RECOVERY_PREPARE '+json.dumps(dict(event=event, **fields),
                                              sort_keys=True, separators=(',', ':')),
          flush=True)


class PreparationKernel(Kernel):
    """Narrow block and mount interface; no label-cache or scan-driven mount."""
    def set_readonly(self, identity, observer=emit):
        # Whole-medium exclusion is established before the selected partition.
        disk_name = Path(identity['disk']).name
        subprocess.run(['/sbin/blockdev', '--setro', '/dev/'+disk_name], check=True, timeout=5)
        require((Path(identity['disk']) / 'ro').read_text().strip() == '1',
                'Source whole medium did not become read-only')
        observer('source-whole-ro', device=identity['disk_device'], readonly=True)
        subprocess.run(['/sbin/blockdev', '--setro', identity['node']], check=True, timeout=5)
        require((Path(identity['sysfs']) / 'ro').read_text().strip() == '1',
                'Source partition did not become read-only')
        observer('source-partition-ro', device=identity['device'], readonly=True)

    def mount(self, identity, path, options, filesystem):
        path.mkdir(parents=True, exist_ok=False)
        subprocess.run(['/bin/mount', '-t', filesystem, '-o', options, identity['node'], str(path)],
                       check=True, timeout=15)

    def unmount(self, path):
        subprocess.run(['/bin/umount', str(path)], check=True, timeout=15)


def find_identity(observed, expected):
    matches = []
    for disk in observed:
        values = [disk] + disk['partitions']
        for value in values:
            candidate = dict(stable=disk['stable'], partition=value.get('partition', 0),
                             start=value.get('start', 0), sectors=value['sectors'],
                             filesystem_uuid=value['filesystem_uuid'])
            if candidate == expected:
                matches.append(value)
    require(len(matches) == 1, 'Reviewed media identity is absent or ambiguous')
    return matches[0]


class RecoveryPreparer:
    def __init__(self, policy, *, kernel=None, context=CONTEXT, policy_sha256=None):
        self.policy = policy
        self.kernel = kernel or PreparationKernel()
        self.context = Path(context)
        self.policy_sha256 = policy_sha256 or hashlib.sha256(canonical_json(policy)).hexdigest()
        require(type(policy) is dict and set(policy) == {
                'format_version', 'kind', 'protocol', 'writer_model',
                'envelope_manifest_sha256', 'recovery',
                'source', 'source_path', 'media', 'protected', 'destinations'} and
                policy.get('format_version') == 2 and
                policy.get('protocol') == PROTOCOL and policy.get('kind') == 'independent-recovery' and
                policy.get('writer_model') == WRITER_MODEL,
                'Invalid trusted recovery preparation policy')
        require(type(policy.get('media')) is list and 1 <= len(policy['media']) <= 8 and
                type(policy.get('destinations')) is dict and policy['destinations'] and
                type(policy.get('protected')) is list,
                'Trusted recovery policy lacks a bounded complete topology')

    def authenticate(self):
        root_device = os.stat('/').st_dev
        arguments = Path('/proc/cmdline').read_text().split()
        bindings = ((PROVIDER_MANIFEST, 'sv08.recovery='),
                    (ENVELOPE_MANIFEST, 'sv08.envelope='))
        for path, argument in bindings:
            data = trusted_file(path)
            digest = hashlib.sha256(data).hexdigest()
            require(os.stat(path, follow_symlinks=False).st_dev == root_device,
                    'Immutable recovery manifest is outside the recovery root: '+path.name)
            require([value for value in arguments if value.startswith(argument)] == [argument+digest],
                    'Kernel boot selection does not bind immutable '+path.name)
            if path == PROVIDER_MANIFEST:
                try:
                    value = json.loads(data)
                except (ValueError, TypeError):
                    raise ValueError('Invalid recovery provider manifest') from None
                require(data == canonical_json(value) and
                        set(value) == {'format_version', 'kind', 'protocol', 'policy_sha256', 'inputs'} and
                        value['format_version'] == 2 and
                        value['kind'] == 'sv08-independent-recovery-provider' and
                        value['protocol'] == PROTOCOL and
                        type(value['inputs']) is dict and value['inputs'] and
                        value['policy_sha256'] == self.policy_sha256,
                        'Recovery provider manifest does not bind the reviewed policy')
            else:
                require(digest == self.policy['envelope_manifest_sha256'],
                        'Immutable recovery envelope differs from reviewed policy')

    def _publish(self, value):
        parent = self.context.parent
        parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        info = parent.stat()
        require(info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700,
                'Recovery preparation runtime must be root-owned and private')
        temporary = parent / ('.'+self.context.name+'.new')
        payload = (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                os.write(fd, payload)
                os.fsync(fd)
            finally:
                os.close(fd)
            os.replace(temporary, self.context)
            directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def prepare(self, lease=None):
        mounted, created = [], []
        with (nullcontext(lease) if lease is not None else MediaLease()) as lease:
            try:
                self.context.unlink(missing_ok=True)
                self.authenticate()
                observed = self.kernel.inventory()
                require(reviewed_inventory(observed) == self.policy['media'],
                        'Observed media topology differs from immutable reviewed policy')
                validate_usr_loop_inventory(self.kernel.active_loops())
                stable = [disk['stable'] for disk in observed]
                require(all(not same_identity(left, right) for index, left in enumerate(stable)
                            for right in stable[index+1:]), 'Duplicate or aliased stable media identities')
                recovery = find_identity(observed, self.policy['recovery'])
                source = find_identity(observed, self.policy['source'])
                require(source['filesystem'] == 'ext4' and source['partition'] > 0,
                        'Reviewed source must be a selected ext4 partition')
                protected = []
                for item in self.policy['protected']:
                    require(set(item) == {'role', 'identity'} and
                            re.fullmatch(r'[A-Za-z0-9_-]{1,64}', item['role']) is not None,
                            'Invalid protected-media role')
                    protected.append(find_identity(observed, item['identity']))
                selected_devices = {source['device']}
                protected_disks = {recovery['disk_device'], source['disk_device'],
                                   *(item['disk_device'] for item in protected)}
                destinations = {}
                for key, spec in self.policy['destinations'].items():
                    require(re.fullmatch(r'[A-Za-z0-9_-]{1,64}', key) is not None and
                            set(spec) == {'identity', 'path', 'label'}, 'Invalid reviewed destination policy')
                    identity = find_identity(observed, spec['identity'])
                    require(identity['filesystem'] == 'vfat' and identity['partition'] > 0 and
                            identity['removable'] and not identity['readonly'] and
                            not identity['disk_readonly'],
                            'Reviewed destination must be a writable removable FAT partition')
                    require(identity['device'] not in selected_devices and
                            identity['disk_device'] not in protected_disks and
                            all(identity['disk_device'] != other['disk_device']
                                for _, other in destinations.values()),
                            'Destination whole disk aliases protected or another prepared medium')
                    selected_devices.add(identity['device'])
                    destinations[key] = (spec, identity)
                require(len({item['device'] for item in protected}) == len(protected) and
                        not selected_devices.intersection(item['device'] for item in protected),
                        'Protected media roles are duplicate or alias prepared media')
                leaf_devices = {item['device'] for disk in observed
                                for item in (disk['partitions'] if disk['partitions'] else [disk])}
                require(leaf_devices == selected_devices | {recovery['device']} |
                        {item['device'] for item in protected},
                        'Protected media inventory is incomplete')
                mounts = self.kernel.mounts()
                require(any(m['path'] == '/' and m['device'] == recovery['device'] for m in mounts),
                        'Reviewed recovery root is not the running root')
                media_devices = {value['device'] for disk in observed
                                 for value in [disk, *disk['partitions']]}
                require(all(m['device'] not in media_devices or
                            (m['device'] == recovery['device'] and m['path'] == '/') for m in mounts),
                        'Reviewed media has an unexpected active mount')
                require(not any(m['device'] in selected_devices for m in mounts),
                        'Source or destination is already mounted')
                self.kernel.set_readonly(source, emit)
                source_path = Path(self.policy['source_path'])
                require(str(source_path) == '/run/sv08-recovery/source', 'Unreviewed source mount path')
                created.append(source_path)
                source_options = 'ro,noload,nosuid,nodev,noexec'
                emit('source-mount-begin', device=source['device'], path=str(source_path),
                     filesystem='ext4', options=source_options)
                self.kernel.mount(source, source_path, source_options, 'ext4')
                mounted.append(source_path)
                emit('source-mount-complete', device=source['device'], path=str(source_path),
                     filesystem='ext4', options=source_options)
                context_targets = {}
                for key, (spec, identity) in destinations.items():
                    path = Path(spec['path'])
                    require(str(path) == '/run/sv08-recovery/destinations/'+key,
                            'Unreviewed destination mount path')
                    created.append(path)
                    self.kernel.mount(identity, path, 'rw,nosuid,nodev,noexec,umask=0077', 'vfat')
                    mounted.append(path)
                    context_targets[key] = dict(path=str(path), label=spec['label'])
                context = dict(format_version=2, protocol=PROTOCOL,
                               policy_sha256=fingerprint(self.policy), source=str(source_path),
                               destinations=context_targets)
                provider = MediaProvider(self.policy, context, policy_sha256=self.policy_sha256)
                context['expected'] = provider.snapshot()
                lease.check()
                self._publish(context)
                return context
            except BaseException:
                self.context.unlink(missing_ok=True)
                cleanup = []
                for path in reversed(mounted):
                    try:
                        self.kernel.unmount(path)
                    except BaseException as error:
                        cleanup.append(str(error))
                for path in reversed(created):
                    try:
                        path.rmdir()
                    except FileNotFoundError:
                        pass
                    except BaseException as error:
                        cleanup.append(str(error))
                if cleanup:
                    raise RuntimeError('Recovery preparation failed and cleanup was incomplete: '+'; '.join(cleanup))
                raise


def main():
    with MediaLease() as lease:
        require(os.stat(POLICY, follow_symlinks=False).st_dev == os.stat('/').st_dev,
                'Recovery media policy is outside the immutable recovery root')
        policy_data = trusted_file(POLICY)
        policy = json.loads(policy_data)
        require(policy_data == canonical_json(policy), 'Recovery policy is not canonical reviewed input')
        RecoveryPreparer(policy, policy_sha256=hashlib.sha256(policy_data).hexdigest()).prepare(lease)


if __name__ == '__main__':
    main()
