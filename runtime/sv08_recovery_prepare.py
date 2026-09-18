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
                                 PROVIDER_MANIFEST, MediaLease, MediaProvider,
                                 PROTOCOL, WRITER_MODEL, canonical_json,
                                 fingerprint, mount_table, require, same_identity,
                                 trusted_file)


class PreparationKernel:
    """Narrow block and mount interface; no label-cache or scan-driven mount."""
    def _probe(self, node):
        result = subprocess.run(['/usr/sbin/blkid', '-p', '-o', 'export', str(node)],
                                check=False, capture_output=True, text=True, timeout=5)
        if result.returncode not in (0, 2):
            raise ValueError('Block identity probe failed: '+str(node))
        return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

    def _flag(self, path):
        value = path.read_text().strip()
        require(value in ('0', '1'), 'Unknown kernel block property: '+path.name)
        return value == '1'

    def inventory(self):
        result = []
        for link in sorted(Path('/sys/class/block').iterdir()):
            disk = link.resolve(strict=True)
            if (disk / 'partition').exists() or disk.name.startswith(('ram', 'zram')):
                continue
            if disk.name.startswith('loop'):
                backing = disk / 'loop/backing_file'
                if backing.is_file() and backing.read_text().strip():
                    require(backing.read_text().strip() == '/usr.squashfs' and
                            (disk / 'ro').read_text().strip() == '1' and
                            (disk / 'loop/offset').read_text().strip() == '0',
                            'Unexpected active virtual block medium')
                continue
            require(not list((disk / 'slaves').iterdir()) and not list((disk / 'holders').iterdir()),
                    'Unsupported active or stacked block medium')
            path_text = str(disk)
            if '/usb' in path_text:
                transport = 'usb-scsi'
            elif '/target' in path_text:
                transport = 'scsi'
            elif '/virtio' in path_text:
                transport = 'virtio'
            elif '/mmc' in path_text:
                transport = 'mmc'
            else:
                raise ValueError('Unsupported block transport: '+disk.name)
            stable = {}
            for name in ('wwid', 'device/wwid', 'device/cid', 'device/serial', 'serial'):
                item = disk / name
                if item.is_file() and item.read_text().strip():
                    stable[name] = item.read_text().strip()
            require(stable, 'Stable medium identity is unavailable: '+disk.name)
            partitions = []
            children = sorted((p.resolve() for p in Path('/sys/class/block').iterdir()
                               if (p.resolve().parent == disk and (p.resolve() / 'partition').exists())),
                              key=lambda p: int((p / 'partition').read_text()))
            for child in children:
                partitions.append(self._identity(child))
            whole = self._identity(disk)
            result.append(dict(name=disk.name, device=whole['device'], sysfs=str(disk),
                               sysfs_inode=disk.stat().st_ino, diskseq=whole['diskseq'],
                               stable=stable, sectors=whole['sectors'], readonly=whole['readonly'],
                               removable=whole['removable'], transport=transport,
                               filesystem_uuid=whole['filesystem_uuid'], filesystem=whole['filesystem'],
                               partitions=partitions))
        require(1 <= len(result) <= 8, 'Recovery requires a bounded complete media inventory')
        return result

    def _identity(self, sysfs):
        for topology in ('holders', 'slaves'):
            directory = sysfs / topology
            require(not directory.exists() or not list(directory.iterdir()),
                    'Block device has an unexpected '+topology[:-1])
        device = (sysfs / 'dev').read_text().strip()
        uevent = dict(line.split('=', 1) for line in (sysfs / 'uevent').read_text().splitlines())
        name = uevent['DEVNAME']
        require(re.fullmatch(r'[A-Za-z0-9_-]+', name) is not None, 'Unsupported block device name')
        node = Path('/dev') / name
        info = os.stat(node, follow_symlinks=False)
        require(stat.S_ISBLK(info.st_mode) and
                f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}' == device,
                'Block device node identity changed')
        probe = self._probe(node)
        partition = int((sysfs / 'partition').read_text()) if (sysfs / 'partition').exists() else 0
        disk = sysfs.parent if partition else sysfs
        return dict(node=str(node), device=device, sysfs=str(sysfs),
                    sysfs_inode=sysfs.stat().st_ino,
                    disk=str(disk), disk_device=(disk / 'dev').read_text().strip(),
                    diskseq=int((disk / 'diskseq').read_text()), partition=partition,
                    start=int((sysfs / 'start').read_text()) if partition else 0,
                    sectors=int((sysfs / 'size').read_text()), readonly=self._flag(sysfs / 'ro'),
                    disk_readonly=self._flag(disk / 'ro'), removable=self._flag(disk / 'removable'),
                    filesystem_uuid=probe.get('UUID', ''), filesystem=probe.get('TYPE', ''),
                    partuuid=probe.get('PART_ENTRY_UUID', ''))

    def mounts(self):
        return mount_table(Path('/proc/self/mountinfo').read_text())

    def set_readonly(self, identity):
        # Whole-medium exclusion is established before the selected partition.
        disk_name = Path(identity['disk']).name
        subprocess.run(['/sbin/blockdev', '--setro', '/dev/'+disk_name], check=True, timeout=5)
        subprocess.run(['/sbin/blockdev', '--setro', identity['node']], check=True, timeout=5)
        require((Path(identity['disk']) / 'ro').read_text().strip() == '1' and
                (Path(identity['sysfs']) / 'ro').read_text().strip() == '1',
                'Source whole medium and partition did not become read-only')

    def mount(self, identity, path, options, filesystem):
        path.mkdir(parents=True, exist_ok=False)
        subprocess.run(['/bin/mount', '-t', filesystem, '-o', options, identity['node'], str(path)],
                       check=True, timeout=15)

    def unmount(self, path):
        subprocess.run(['/bin/umount', str(path)], check=True, timeout=15)


def reviewed_inventory(observed):
    """Drop observations that change per boot; retain every trust-relevant field."""
    result = []
    for disk in observed:
        result.append(dict(stable=disk['stable'], sectors=disk['sectors'],
                           removable=disk['removable'], transport=disk['transport'],
                           filesystem_uuid=disk['filesystem_uuid'], filesystem=disk['filesystem'],
                           partitions=[{name: part[name] for name in
                                       ('partition', 'start', 'sectors', 'filesystem_uuid',
                                        'filesystem', 'partuuid')}
                                      for part in disk['partitions']]))
    return sorted(result, key=lambda value: json.dumps(value['stable'], sort_keys=True))


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
                stable = [disk['stable'] for disk in observed]
                require(all(not same_identity(left, right) for index, left in enumerate(stable)
                            for right in stable[index+1:]), 'Duplicate or aliased stable media identities')
                recovery = find_identity(observed, self.policy['recovery'])
                source = find_identity(observed, self.policy['source'])
                require(source['filesystem'] == 'ext4' and source['partition'] > 0,
                        'Reviewed source must be a selected ext4 partition')
                mounts = self.kernel.mounts()
                require(any(m['path'] == '/' and m['device'] == recovery['device'] for m in mounts),
                        'Reviewed recovery root is not the running root')
                media_devices = {value['device'] for disk in observed
                                 for value in [disk, *disk['partitions']]}
                require(all(m['device'] not in media_devices or
                            (m['device'] == recovery['device'] and m['path'] == '/') for m in mounts),
                        'Reviewed media has an unexpected active mount')
                selected_devices = {source['device']}
                destinations = {}
                for key, spec in self.policy['destinations'].items():
                    require(re.fullmatch(r'[A-Za-z0-9_-]{1,64}', key) is not None and
                            set(spec) == {'identity', 'path', 'label'}, 'Invalid reviewed destination policy')
                    identity = find_identity(observed, spec['identity'])
                    require(identity['filesystem'] == 'vfat' and identity['partition'] > 0 and
                            identity['removable'] and not identity['readonly'] and
                            not identity['disk_readonly'],
                            'Reviewed destination must be a writable removable FAT partition')
                    require(identity['device'] not in selected_devices, 'Prepared media roles alias')
                    selected_devices.add(identity['device'])
                    destinations[key] = (spec, identity)
                protected = []
                for item in self.policy['protected']:
                    require(set(item) == {'role', 'identity'} and
                            re.fullmatch(r'[A-Za-z0-9_-]{1,64}', item['role']) is not None,
                            'Invalid protected-media role')
                    protected.append(find_identity(observed, item['identity']))
                require(len({item['device'] for item in protected}) == len(protected) and
                        not selected_devices.intersection(item['device'] for item in protected),
                        'Protected media roles are duplicate or alias prepared media')
                leaf_devices = {item['device'] for disk in observed
                                for item in (disk['partitions'] if disk['partitions'] else [disk])}
                require(leaf_devices == selected_devices | {recovery['device']} |
                        {item['device'] for item in protected},
                        'Protected media inventory is incomplete')
                require(not any(m['device'] in selected_devices for m in mounts),
                        'Source or destination is already mounted')
                self.kernel.set_readonly(source)
                source_path = Path(self.policy['source_path'])
                require(str(source_path) == '/run/sv08-recovery/source', 'Unreviewed source mount path')
                created.append(source_path)
                self.kernel.mount(source, source_path, 'ro,noload,nosuid,nodev,noexec', 'ext4')
                mounted.append(source_path)
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
