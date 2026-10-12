"""Distinct reviewed writable-ext4 restore admission; no device preparation.

Fixed production policy/context inputs are intentionally not provisioned here.
Reviewed recovery userspace must prepare mounts and publish the observed context.
All media mutators share MediaLease; arbitrary privileged writers are outside that
contract. Physical target provisioning and boot activation require qualification.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from sv08_export import opened
from sv08_recovery_media import (Kernel, MediaLease, LOCK, WRITER_MODEL, trusted_file,
    canonical_json, clean_path, fingerprint, require, durable_identity,
    same_identity, admitted_system_mount, PROVIDER_MANIFEST, ENVELOPE_MANIFEST,
    strict_envelope_manifest, reviewed_inventory, validate_usr_loop_inventory, MediaProvider)
from sv08_restore import Restore

POLICY = Path('/etc/sv08/recovery-restore-policy.json')
CONTEXT = Path('/run/sv08-recovery/restore-context.json')
PROTOCOL = 'sv08-recovery-data-restore-v1'
ID = r'[a-zA-Z0-9][a-zA-Z0-9._+-]{0,79}'


class RestoreAdapter:
    def __init__(self, restorer): self.restorer = restorer
    def images(self): return []
    def destinations(self): return []
    def archives(self): return [dict(id=k, label=v['label']) for k,v in self.restorer.archives.items()]
    def restore_targets(self): return [dict(id=k, label=v['label']) for k,v in self.restorer.targets.items()]
    def capability(self, action, view):
        if action not in ('recovery.data-restore', 'recovery.initialize'):
            return False, 'No verified backend is available for this operation.'
        try:
            with self.restorer.admission(next(iter(self.restorer.targets))) as guard: guard.recheck()
            return bool(self.restorer.targets) and (action == 'recovery.initialize' or bool(self.restorer.archives)), ''
        except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as error:
            return False, 'Data recovery unavailable: '+str(error)
    def review_restore(self, action, args):
        return self.restorer.prepare(args['target'], args.get('archive'), action == 'recovery.initialize')
    def apply(self, plan):
        prepared = self.review_restore(plan['action'], plan['arguments'])
        require(prepared == plan['restore'], 'Archive or target changed; review again')
        return self.restorer.execute(prepared)


class RestoreMediaProvider(RestoreAdapter):
    def __init__(self, policy, context):
        require(type(policy) is dict and set(policy) == {'format_version','protocol','writer_model','recovery','recovery_path',
                'image_manifest_sha256','envelope_manifest_sha256','media','archives','targets'} and
                type(policy['format_version']) is int and policy['format_version'] == 1 and
                policy['protocol'] == PROTOCOL and policy['writer_model'] == WRITER_MODEL, 'Invalid restore policy')
        require(type(context) is dict and set(context) == {'format_version','protocol','policy_sha256','expected'} and
                context['format_version'] == 1 and context['protocol'] == PROTOCOL and context['policy_sha256'] == fingerprint(policy),
                'Invalid restore preparation context')
        require(type(policy['media']) is list and 1 <= len(policy['media']) <= 8, 'Missing reviewed complete media inventory')
        for key in ('image_manifest_sha256', 'envelope_manifest_sha256'):
            require(type(policy[key]) is str and re.fullmatch('[0-9a-f]{64}', policy[key]), 'Missing immutable recovery binding')
        self.policy, self.context, self.kernel, self.lock = policy, context, Kernel(), LOCK
        self.root = clean_path(policy['recovery_path'])
        require(self.root == Path('/'), 'Production restore must run from the reviewed recovery root')
        archives, targets = {}, {}
        for role, result in [('archives', archives), ('targets', targets)]:
            require(type(policy[role]) is dict and (0 if role == 'archives' else 1) <= len(policy[role]) <= 8, 'Invalid bounded restore choices')
            for key, value in policy[role].items():
                expected = {'label','mount','identity','path'} if role == 'archives' else {'label','mount','identity','root','fresh_root'}
                require(type(key) is str and re.fullmatch(ID, key) and type(value) is dict and set(value) == expected and
                        type(value['label']) is str and 0 < len(value['label']) <= 120 and
                        all(ord(c) >= 32 for c in value['label']), 'Invalid restore choice')
                mount = clean_path(value['mount'])
                require(mount != self.root, 'Restore medium overlaps recovery')
                for field in ('path',) if role == 'archives' else ('root','fresh_root'):
                    path = clean_path(value[field])
                    require(path != mount and path.is_relative_to(mount), 'Restore path must be below its exact reviewed mount')
                result[key] = value
        require(len({v['mount'] for v in targets.values()}) == len(targets), 'Duplicate restore target mounts')
        for target in targets.values():
            require(all(not same_identity(target['identity']['stable'], archive['identity']['stable']) and
                        not Path(target['mount']).is_relative_to(archive['mount']) and
                        not Path(archive['mount']).is_relative_to(target['mount']) for archive in archives.values()),
                    'Restore target overlaps archive medium')
        super().__init__(Restore(archives, targets, self.admission))

    def snapshot(self):
        mounts = self.kernel.mounts()
        require(not any(m['optional'] for m in mounts), 'Recovery mounts must be private')
        require(any(m['path'] == '/proc' and m['filesystem'] == 'proc' and m['root'] == '/' and
                    not any(o.startswith(('hidepid=', 'subset=')) for o in m['super_options']) for m in mounts),
                    'Complete process visibility required')
        require(any(m['path'] == '/sys' and m['filesystem'] == 'sysfs' and m['root'] == '/' for m in mounts), 'Missing kernel topology')
        session = self.kernel.session()
        inventory = self.kernel.inventory()
        require(reviewed_inventory(inventory) == self.policy['media'], 'Complete media inventory changed')
        stable = [disk['stable'] for disk in inventory]
        require(all(not same_identity(left,right) for i,left in enumerate(stable) for right in stable[i+1:]), 'Aliased media identities')
        def selected(path, expected, writable):
            found = [m for m in mounts if m['path'] == str(path)]
            require(len(found) == 1, 'Restore media must be exact mountpoints')
            mount = found[0]
            require(mount['root'] == '/' and sum(m['device'] == mount['device'] for m in mounts) == 1,
                    'Restore mount alias or bind subtree')
            if str(path) != '/':
                require(not any(Path(m['path']).is_relative_to(path) and m != mount for m in mounts), 'Restore submount')
            mode, other = ('rw','ro') if writable else ('ro','rw')
            require(mode in mount['options'] and mode in mount['super_options'] and other not in mount['options']+mount['super_options'] and
                    mount['filesystem'] in (('ext4',) if writable or str(path) == '/' else ('ext4','vfat')), 'Unsafe restore mount mode or filesystem')
            block = self.kernel.block(mount)
            require(durable_identity(block) == expected, 'Restore medium differs from reviewed identity')
            require(block['readonly'] == block['disk_readonly'] == (not writable), 'Restore whole-medium write protection changed')
            if not writable and mount['filesystem'] == 'ext4':
                require('norecovery' in mount['super_options'] or 'noload' in mount['super_options'], 'Read-only archive/recovery must suppress journal replay')
            with opened(path) as fd: info, fs = os.fstat(fd), os.fstatvfs(fd)
            require(f'{os.major(info.st_dev)}:{os.minor(info.st_dev)}' == mount['device'] and bool(fs.f_flag & os.ST_RDONLY) == (not writable), 'Mounted identity changed')
            matches = [item for disk in inventory for item in [disk,*disk['partitions']] if item['device'] == block['device']]
            require(len(matches) == 1 and all(matches[0][key] == block[key] for key in
                    ('sysfs','sysfs_inode','disk','disk_device','diskseq','partition','start','sectors','readonly','disk_readonly','filesystem_uuid','filesystem','partuuid')),
                    'Selected block differs from inventory')
            return dict(mount=mount, block=block, directory=[info.st_dev, info.st_ino])
        recovery = selected(self.root, self.policy['recovery'], False)
        archive_media = {v['mount']: selected(v['mount'],v['identity'],False) for v in self.restorer.archives.values()}
        targets = {k: selected(v['mount'],v['identity'],True) for k,v in self.restorer.targets.items()}
        protected = [recovery, *archive_media.values()]
        require(all(not same_identity(t['block']['stable'], p['block']['stable']) and t['block']['disk'] != p['block']['disk']
                    for t in targets.values() for p in protected) and
                all(not same_identity(a['block']['stable'], b['block']['stable']) for i,a in enumerate(targets.values())
                    for b in list(targets.values())[i+1:]), 'Writable restore target aliases protected media')
        manifest_data = trusted_file(PROVIDER_MANIFEST)
        manifest = json.loads(manifest_data)
        require(hashlib.sha256(manifest_data).hexdigest() == self.policy['image_manifest_sha256'] and
                manifest_data == canonical_json(manifest) and manifest.get('kind') == 'sv08-independent-recovery-provider', 'Running recovery manifest changed')
        require(set(manifest) == {'format_version','kind','protocol','policy_sha256','inputs'} and
                manifest['format_version'] == 2 and manifest['protocol'] == 'sv08-recovery-media-v1' and
                type(manifest['inputs']) is dict, 'Invalid immutable provider manifest')
        for name in ('sv08_restore.py','sv08_recovery_restore_media.py','sv08_recovery.py','sv08_recovery_ui.py',
                     'sv08_admin.py','sv08_export.py','sv08_recovery_media.py','sv08_state.py','sv08_admin_history.py','sv08_admin_jobs.py',
                     'sv08_data_budget.py','sv08_update_policy.py'):
            installed = Path('/usr/lib/sv08') / name
            data = trusted_file(installed)
            require(manifest['inputs'].get('runtime/'+name) == hashlib.sha256(data).hexdigest(),
                    'Restore runtime differs from immutable manifest: '+name)
        args = Path('/proc/cmdline').read_text().split()
        require([a for a in args if a.startswith('sv08.recovery=')] == ['sv08.recovery='+self.policy['image_manifest_sha256']], 'Recovery boot binding changed')
        envelope_data = trusted_file(ENVELOPE_MANIFEST)
        digest = hashlib.sha256(envelope_data).hexdigest()
        require(digest == self.policy['envelope_manifest_sha256'] and
                [a for a in args if a.startswith('sv08.envelope=')] == ['sv08.envelope='+digest], 'Recovery envelope binding changed')
        envelope = strict_envelope_manifest(envelope_data)
        require(envelope['root_uuid'] == recovery['block']['filesystem_uuid'] and envelope['root_bytes'] == recovery['block']['sectors']*512, 'Recovery envelope extent changed')
        # Reuse the selected compressed-userspace verification unchanged.
        compressed = MediaProvider.compressed_userspace(self, mounts, recovery, envelope)
        loop = validate_usr_loop_inventory(self.kernel.active_loops())
        require(loop['device'] == compressed['loop_device'] and loop['backing_identity'] == compressed['backing'], 'Userspace loop changed')
        paths = {'/','/usr', *archive_media, *(v['mount'] for v in self.restorer.targets.values())}
        require(all(admitted_system_mount(m, paths) for m in mounts), 'Unexpected recovery mount')
        for path in (POLICY, PROVIDER_MANIFEST, ENVELOPE_MANIFEST):
            with opened(path, flags=os.O_RDONLY | os.O_NOFOLLOW) as fd:
                require(os.fstat(fd).st_dev == recovery['directory'][0], 'Trust input outside immutable recovery')
        return dict(session=session, mounts=mounts, media=inventory, recovery=recovery, archives=archive_media, targets=targets, compressed=compressed)

    @contextmanager
    def admission(self, target):
        require(target in self.restorer.targets, 'Choose a configured restore target')
        with MediaLease(self.lock) as lease:
            initial = self.snapshot()
            require(initial == self.context['expected'], 'Prepared restore context changed')
            provider = self
            class Guard:
                fingerprint = fingerprint(initial)
                def recheck(self):
                    lease.check()
                    require(provider.snapshot() == initial, 'Restore media changed during operation')
            yield Guard()


class Composite:
    def __init__(self, export, restore): self.export, self.restore = export, restore
    def images(self): return self.export.images()
    def destinations(self): return self.export.destinations()
    def archives(self): return self.restore.archives() if hasattr(self.restore,'archives') else []
    def restore_targets(self): return self.restore.restore_targets() if hasattr(self.restore,'restore_targets') else []
    def selected(self, action): return self.restore if action in ('recovery.data-restore','recovery.initialize') else self.export
    def capability(self, action, view): return self.selected(action).capability(action,view)
    def review_export(self, target): return self.export.review_export(target)
    def review_restore(self, action,args): return self.restore.review_restore(action,args)
    def apply(self, plan): return self.selected(plan['action']).apply(plan)


def production_adapter():
    from sv08_recovery_media import Unavailable
    try:
        data = trusted_file(POLICY); policy = json.loads(data)
        require(data == canonical_json(policy), 'Restore policy is not canonical reviewed input')
        provider = RestoreMediaProvider(policy,json.loads(trusted_file(CONTEXT)))
        with provider.admission(next(iter(provider.restorer.targets))) as guard: guard.recheck()
        return provider
    except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as error:
        return Unavailable('Data recovery unavailable: '+str(error))
