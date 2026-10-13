"""Explicit canonical-directory activation with retained, inode-bound rollback.

All callers hold the restore MediaLease. A durable pending sentinel precedes
journal publication and every rename. Normal initramfs refuses that sentinel.
No reconciliation silently chooses new state: only explicit rollback is allowed.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid
from sv08_export import opened, publish, identity
from sv08_state import Store, atomic_json, fsync_dir
from sv08_restore import require

JOURNAL = '.sv08-activation.json'
PENDING = '.sv08-activation-pending'


def inode(path):
    with opened(path) as fd:
        info = os.fstat(fd)
        require(stat.S_ISDIR(info.st_mode), 'Activation path must be a real directory')
        return [info.st_dev, info.st_ino]


def durable_inode(path):
    # Filesystem inode persists across boots; device major/minor does not.
    # Callers admit the data partition via policy or normal verify_devices first.
    return inode(path)[1]


def optional_inode(path):
    return inode(path) if os.path.lexists(path) else None


def tree_digest(root, logs_links=False):
    """Bind reviewed bytes; retained log links are opaque, never traversed.

    Normal systemd startup creates shared/logs/README. Only existing state
    and rollback admit links within that log subtree; candidates stay strict.
    Store, generation and identity paths still cannot be symlink-backed.
    """
    digest = hashlib.sha256()
    for path in [root, *sorted(root.rglob('*'))]:
        info = path.lstat()
        relative = path.relative_to(root)
        link = stat.S_ISLNK(info.st_mode)
        require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode) or
                (link and logs_links and relative.parts[:2] == ('shared','logs') and len(relative.parts) > 2),
                'Unsupported activation object')
        digest.update(json.dumps([str(relative), info.st_mode, info.st_uid,
                                 info.st_gid, info.st_size if stat.S_ISREG(info.st_mode) or link else 0,
                                 info.st_mtime_ns, info.st_ino], separators=(',', ':')).encode())
        if link:
            with opened(path.parent) as directory:
                before = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
                require(identity(before) == identity(info), 'Activation link changed while reading')
                target = os.readlink(os.fsencode(path.name), dir_fd=directory)
                require(identity(os.stat(path.name, dir_fd=directory, follow_symlinks=False)) == identity(before),
                        'Activation link changed while reading')
                digest.update(json.dumps(identity(before), separators=(',', ':')).encode())
                digest.update(target)
        elif stat.S_ISREG(info.st_mode):
            with opened(path, flags=os.O_RDONLY | os.O_NOFOLLOW) as fd:
                before = os.fstat(fd)
                while chunk := os.read(fd, 1024*1024): digest.update(chunk)
                require(identity(os.fstat(fd)) == identity(before), 'Activation contents changed while reading')
    return digest.hexdigest()


def validate_boot(boot):
    require(type(boot) is dict and set(boot) == {'slot','release','state_schema','release_revision'} and
            boot['slot'] in ('A','B') and boot['state_schema'] == 1, 'Missing reviewed normal boot binding')
    from sv08_state import identifier
    from sv08_update_policy import release_revision
    identifier(boot['release']); release_revision(boot['release_revision'])


def compatible(root, boot, fresh):
    validate_boot(boot)
    store = Store(root); state = store.load()
    require(state['pending'] is None, 'Archived trial state cannot be activated')
    if fresh:
        require(state == dict(format_version=1, requested_mode='immutable', auto_update=True, slots={}, pending=None),
                'Fresh state differs from immutable defaults')
        require(not (root/'system/machine-id').exists(), 'Fresh state already has an identity')
    else:
        record = state['slots'].get(boot['slot'])
        require(record and record['release'] == boot['release'] and record['schema'] == boot['state_schema'] and
                record.get('release_revision') == boot['release_revision'], 'Restored state differs from reviewed normal release')
        for item in state['slots'].values():
            generation = store.generation_path(item)
            require(all((generation/name).is_dir() and not (generation/name).is_symlink()
                        for name in ('config','database','ui')), 'Incomplete restored generation')
        machine = root/'system/machine-id'
        require(machine.is_file() and not machine.is_symlink() and
                re.fullmatch('[0-9a-f]{32}\n?', machine.read_text()), 'Restored machine identity is unavailable or invalid')
    return state


def boot_guard(parent):
    """Also defend direct Python boot entry; initramfs checks before PID 1."""
    parent = Path(parent)
    require(not os.path.lexists(parent/PENDING), 'Interrupted activation requires recovery rollback')
    if os.path.lexists(parent/JOURNAL):
        journal = read_journal(parent)
        require(journal['phase'] in ('committed','rolled-back'), 'Interrupted activation requires recovery rollback')
        expected = journal['new'] if journal['phase'] == 'committed' else journal['old']
        require(expected is None or (durable_inode(parent/'sv08') if os.path.lexists(parent/'sv08') else None) == expected, 'Canonical activation identity changed')


def read_journal(parent):
    path = parent/JOURNAL
    with opened(path, flags=os.O_RDONLY | os.O_NOFOLLOW) as fd:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size < 8192,
                'Invalid activation journal')
        value = json.loads(os.read(fd,8192))
    require(type(value) is dict and set(value) == {'format_version','id','phase','source','backup','new','old','parent'} and
            value['format_version'] == 1 and value['phase'] in ('prepared','saved','committed','rolling-back','rolled-back') and
            re.fullmatch('[0-9a-f]{32}', value['id']) and value['backup'] == '.sv08-previous-'+value['id'] and
            type(value['source']) is str and not Path(value['source']).is_absolute() and
            '..' not in Path(value['source']).parts and value['source'] != 'sv08' and
            all(type(value[k]) is int and value[k] > 0 for k in ('new','parent')) and
            (value['old'] is None or (type(value['old']) is int and value['old'] > 0)), 'Invalid activation journal protocol')
    require(value['parent'] == durable_inode(parent), 'Activation journal parent changed')
    return value


class Activation:
    def __init__(self, targets, admission, boot, boundary=lambda name: None):
        self.targets, self.admission, self.boot, self.boundary = targets, admission, boot, boundary

    def paths(self, target, fresh=False):
        require(target in self.targets, 'Choose a configured activation target')
        spec = self.targets[target]; parent = Path(spec['mount'])
        source = Path(spec['fresh_root']) if fresh else Path(spec['root'])/'sv08'
        canonical = parent/'sv08'
        require(source.is_relative_to(parent) and not source.is_relative_to(canonical) and
                not canonical.is_relative_to(source), 'Activation source overlaps canonical state')
        return parent, source

    def prepare(self, target, fresh=False, rollback=False):
        parent, source = self.paths(target, fresh)
        with self.admission(target) as guard:
            if rollback:
                if not os.path.lexists(parent/JOURNAL):
                    require(os.path.lexists(parent/PENDING), 'No activation to roll back')
                    detail = dict(journal=None, parent=inode(parent), old=optional_inode(parent/'sv08'))
                    guard.recheck()
                    return dict(detail,target=target,fresh=fresh,rollback=True,media_fingerprint=guard.fingerprint)
                journal = read_journal(parent)
                require(journal['phase'] != 'rolled-back' or os.path.lexists(parent/PENDING), 'Previous state is already restored')
                found = self.locations(parent, journal)
                detail = dict(journal=journal, digests={key:tree_digest(path, logs_links=True) for key,path in found.items()})
            else:
                boot_guard(parent)
                require(not os.path.lexists(parent/JOURNAL) or read_journal(parent)['phase'] == 'rolled-back', 'Retained activation exists; rollback before another activation')
                compatible(source,self.boot,fresh)
                detail = dict(source=str(source), new=inode(source), old=optional_inode(parent/'sv08'),
                              parent=inode(parent), digest=tree_digest(source), old_digest=tree_digest(parent/'sv08', logs_links=True) if os.path.lexists(parent/'sv08') else None)
            guard.recheck()
            return dict(detail, target=target, fresh=fresh, rollback=rollback, media_fingerprint=guard.fingerprint)

    def locations(self, parent, journal):
        found = {}
        for path in [parent/'sv08', parent/journal['source'], parent/journal['backup']]:
            if os.path.lexists(path):
                value = durable_inode(path)
                require(value in (journal['new'],journal['old']), 'Activation location contains unexpected state')
                key = 'new' if value == journal['new'] else 'old'
                require(key not in found, 'Activation inode has aliased locations')
                found[key] = path
        require(set(found) == ({'new','old'} if journal['old'] is not None else {'new'}), 'Activation state is missing; preserve media for recovery')
        return found

    def pending(self, parent):
        path = parent/PENDING
        if os.path.lexists(path):
            require(path.is_file() and not path.is_symlink() and path.read_bytes() == b'sv08-activation-pending-v1\n',
                    'Invalid activation pending sentinel')
        else:
            with path.open('xb') as stream:
                os.chmod(path,0o600); stream.write(b'sv08-activation-pending-v1\n'); stream.flush(); os.fsync(stream.fileno())
        fsync_dir(parent); self.boundary('pending')

    def write(self,parent,journal,phase):
        journal['phase'] = phase; atomic_json(parent/JOURNAL,journal); self.boundary(phase)

    def move(self,source,dest):
        with opened(source.parent) as src, opened(dest.parent) as dst:
            # Same Linux/glibc no-replace mechanism as upstream publish, across parents.
            libc = ctypes.CDLL(None, use_errno=True)
            rename = libc.renameat2
            rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
            if rename(src,os.fsencode(source.name),dst,os.fsencode(dest.name),1):
                error = ctypes.get_errno(); raise OSError(error,os.strerror(error))
            os.fsync(src); os.fsync(dst)
        self.boundary('rename-'+dest.name)

    def execute(self,plan):
        with self.admission(plan['target']) as guard:
            require(guard.fingerprint == plan['media_fingerprint'], 'Activation media changed')
            parent, source = self.paths(plan['target'],plan['fresh'])
            if plan['rollback']:
                if plan['journal'] is None:
                    require(not os.path.lexists(parent/JOURNAL) and inode(parent) == plan['parent'] and
                            optional_inode(parent/'sv08') == plan['old'], 'Activation state changed')
                    guard.recheck(); self.pending(parent); (parent/PENDING).unlink(); fsync_dir(parent)
                    return dict(message='Unstarted activation cancelled. Previous configuration is unchanged.')
                journal = read_journal(parent)
                require(journal == plan['journal'], 'Activation journal changed; review rollback again')
                found = self.locations(parent,journal)
                require({key:tree_digest(path, logs_links=True) for key,path in found.items()} == plan['digests'], 'Rollback contents changed; review again')
                guard.recheck(); self.pending(parent)
                self.write(parent,journal,'rolling-back')
                if found['new'] == parent/'sv08':
                    self.move(found['new'],parent/journal['source'])
                if 'old' in found and found['old'] != parent/'sv08': self.move(found['old'],parent/'sv08')
                self.write(parent,journal,'rolled-back')
            else:
                require(self.prepare_unlocked(parent,source,plan), 'Activation state changed; review again')
                guard.recheck(); self.pending(parent)
                if os.path.lexists(parent/JOURNAL):
                    previous = read_journal(parent)
                    with opened(parent) as fd:
                        publish(fd,JOURNAL,'.sv08-activation-'+previous['id']+'.json'); os.fsync(fd)
                    self.boundary('retired')
                token = uuid.uuid4().hex
                journal = dict(format_version=1,id=token,phase='prepared',source=str(source.relative_to(parent)),
                               backup='.sv08-previous-'+token,new=plan['new'][1],old=plan['old'][1] if plan['old'] else None,parent=plan['parent'][1])
                self.write(parent,journal,'prepared')
                if journal['old'] is not None: self.move(parent/'sv08',parent/journal['backup'])
                self.write(parent,journal,'saved')
                self.move(source,parent/'sv08'); self.write(parent,journal,'committed')
            guard.recheck(); (parent/PENDING).unlink(); fsync_dir(parent); self.boundary('cleared')
            boot_guard(parent)
            return dict(message=('Previous state restored. Reboot uses the previous configuration.' if plan['rollback'] else
                                 'State activated. Normal reboot uses this configuration. Previous state is retained for rollback.'))

    def prepare_unlocked(self,parent,source,plan):
        boot_guard(parent)
        require(not os.path.lexists(parent/JOURNAL) or read_journal(parent)['phase'] == 'rolled-back', 'Retained activation already exists')
        compatible(source,self.boot,plan['fresh'])
        return (inode(source) == plan['new'] and optional_inode(parent/'sv08') == plan['old'] and inode(parent) == plan['parent'] and
                tree_digest(source) == plan['digest'] and (tree_digest(parent/'sv08', logs_links=True) if os.path.lexists(parent/'sv08') else None) == plan['old_digest'])
