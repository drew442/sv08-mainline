"""Bounded full export restore into an absent, configured directory.

No tar extraction API, merge, repair or activation. Version 1 exports do not
checksum directory metadata; modes/uid/gid are validated and preserved, while
ACLs, xattrs, sparse allocation and subsecond timestamps are not represented.
Failed staging is retained as a private .sv08-restore-*.partial directory.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tarfile
import uuid

from sv08_export import CHUNK, identity, opened, publish, restore_archive
from sv08_state import Store

MAX_ENTRIES = 100000
MAX_BYTES = 2**32 - 1
MAX_MANIFEST = 16 * 1024**2


def require(condition, reason):
    if not condition: raise ValueError(reason)


def parts(name):
    require(isinstance(name, str) and len(name.encode()) <= 4096 and
            '\\' not in name and all(ord(c) >= 32 for c in name), 'Unsafe restore path')
    result = name.split('/')
    require(result[0] == 'data' and len(result) > 1 and
            all(p not in ('', '.', '..') and len(p.encode()) <= 255 for p in result), 'Unsafe restore path')
    return tuple(result[1:])


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate manifest field')
        result[key] = value
    return result


@contextmanager
def pinned_archive(path):
    with opened(path, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as fd:
        stamp = identity(os.fstat(fd))
        require(stat.S_ISREG(stamp[2]) and stamp[8] == 1 and 10240 <= stamp[3] <= MAX_BYTES,
                'Invalid restore archive size, type or links')
        yield fd, stamp
        require(identity(os.fstat(fd)) == stamp, 'Restore archive changed')
        with opened(path, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as current:
            require(identity(os.fstat(current)) == stamp, 'Restore archive pathname changed')


def scan(fd, stage=None, max_bytes=MAX_BYTES, max_entries=MAX_ENTRIES, history_root=None):
    """Validate every payload and inventory; optionally write a private stage."""
    members, files, manifest, total, end = {}, {}, None, 0, 0
    links = []
    with restore_archive('/proc/self/fd/'+str(fd)) as (archive, size):
        for item in archive:
            require(item.name not in members and len(members) <= max_entries, 'Duplicate or too many restore members')
            require(item.sparse is None and 0 <= item.size <= max_bytes, 'Invalid restore payload bounds')
            end = item.offset_data + ((item.size+511)//512)*512
            if item.name == 'export-manifest.json':
                require(item.isfile() and item.size <= MAX_MANIFEST, 'Invalid restore manifest size or type')
                manifest = json.loads(archive.extractfile(item).read(), object_pairs_hook=unique_object)
                members[item.name] = None
                continue
            relative = parts(item.name)
            require(item.isdir() or item.isfile() or item.islnk(), 'Unsupported restore member type')
            require(type(item.mode) is int and 0 <= item.mode <= 0o777 and
                    type(item.uid) is int and 0 <= item.uid <= 2**31-1 and
                    type(item.gid) is int and 0 <= item.gid <= 2**31-1 and
                    0 <= item.mtime <= 2**32-1,
                    'Unsafe restore metadata (special permission bits are refused)')
            require(os.geteuid() == 0 or (item.uid == os.geteuid() and item.gid == os.getegid()),
                    'Cannot preserve archive ownership')
            require(all('data/'+'/'.join(relative[:n]) in members and
                        members['data/'+'/'.join(relative[:n])]['type'] == 'directory'
                        for n in range(1, len(relative))), 'Missing directory ancestor')
            kind = 'directory' if item.isdir() else ('hardlink' if item.islnk() else 'file')
            members[item.name] = dict(type=kind, mode=item.mode, uid=item.uid, gid=item.gid, mtime=item.mtime, bytes=item.size)
            if item.isdir():
                require(item.size == 0, 'Directory has a payload')
                if stage: stage.joinpath(*relative).mkdir(mode=0o700)
                continue
            total += item.size
            require(total <= max_bytes, 'Restore exceeds payload bound')
            if item.islnk():
                require(relative[-2:] == ('admin-image-jobs', 'history-format-v2.lock') and
                        item.linkname == 'data/'+'/'.join((*relative[:-1], 'ledger.lock')) and not item.size,
                        'Unexpected restore hardlink fence')
                links.append((item.name, item.linkname))
                files[item.name] = dict(path=item.name, hardlink=item.linkname)
                continue
            checksum = hashlib.sha256()
            stream = archive.extractfile(item)
            output = stage.joinpath(*relative).open('xb') if stage else None
            try:
                remaining = item.size
                while remaining:
                    block = stream.read(min(CHUNK, remaining))
                    require(bool(block), 'Truncated restore payload')
                    checksum.update(block); remaining -= len(block)
                    if output:
                        require(output.write(block) == len(block), 'Short restore write')
                if output: output.flush(); os.fsync(output.fileno())
            finally:
                stream.close()
                if output: output.close()
            files[item.name] = dict(path=item.name, bytes=item.size, sha256=checksum.hexdigest())
    # tarfile tolerates missing terminators and garbage after its EOF. Require
    # the canonical writer's zero-filled trailing records explicitly.
    require(os.fstat(fd).st_size - end >= 1024, 'Missing archive terminator')
    os.lseek(fd, end, os.SEEK_SET)
    while block := os.read(fd, CHUNK): require(not any(block), 'Nonzero trailing archive data')
    require(type(manifest) is dict and set(manifest) == {'format_version', 'kind', 'files', 'history'} and
            type(manifest['format_version']) is int and manifest['format_version'] == 1 and
            manifest['kind'] == 'user-data-export-not-os-image' and type(manifest['files']) is list and
            len(manifest['files']) <= max_entries and type(manifest['history']) is list,
            'Invalid complete restore manifest')
    records = {}
    for record in manifest['files']:
        require(type(record) is dict and type(record.get('path')) is str and record['path'] not in records,
                'Invalid or duplicate restore inventory')
        parts(record['path'])
        require((set(record) == {'path','bytes','sha256'} and type(record['bytes']) is int and 0 <= record['bytes'] <= max_bytes and
                 type(record['sha256']) is str and re.fullmatch('[0-9a-f]{64}',record['sha256'])) or
                (set(record) == {'path','hardlink'} and type(record['hardlink']) is str), 'Invalid restore inventory fields')
        records[record['path']] = record
    require(records == files, 'Restore inventory or checksum mismatch')
    histories = {}
    for binding in manifest['history']:
        require(type(binding) is dict and set(binding) == {'path', 'revision', 'alias', 'target'} and
                type(binding['path']) is str and binding['path'] not in histories and
                parts(binding['path'])[-1] == 'admin-image-jobs' and
                binding['alias'] == 'history-format-v2.lock' and binding['target'] == 'ledger.lock' and
                re.fullmatch('[0-9a-f]{64}', binding['revision']) is not None, 'Invalid history binding')
        histories[binding['path']] = binding
    require({name.rsplit('/', 1)[0] for name, _ in links} == set(histories), 'History fence binding mismatch')
    for name, target in links:
        require(members.get(target, {}).get('type') == 'file' and
                {key: members[name][key] for key in ('mode', 'uid', 'gid', 'mtime')} ==
                {key: members[target][key] for key in ('mode', 'uid', 'gid', 'mtime')}, 'Invalid history fence target or metadata')
        if stage: os.link(stage.joinpath(*parts(target)), stage.joinpath(*parts(name)))
    if stage:
        # Verify actual destination bytes before permissions become restrictive.
        for name, record in files.items():
            path=stage.joinpath(*parts(name))
            current=os.stat(path,follow_symlinks=False)
            if 'hardlink' in record:
                target=os.stat(stage.joinpath(*parts(record['hardlink'])),follow_symlinks=False)
                require(current.st_nlink == target.st_nlink == 2 and
                        (current.st_dev,current.st_ino) == (target.st_dev,target.st_ino), 'Staged history fence changed')
                continue
            require(stat.S_ISREG(current.st_mode) and current.st_size == record['bytes'], 'Staged restore file size changed')
            with path.open('rb') as payload:
                checksum=hashlib.sha256()
                while block := payload.read(CHUNK): checksum.update(block)
            require(checksum.hexdigest() == record['sha256'], 'Staged restore checksum mismatch')
    if stage:
        # Apply restrictive directory modes last so nested writes remain possible.
        for name, metadata in reversed(list(members.items())):
            if metadata is None: continue
            path = stage.joinpath(*parts(name))
            child = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                if os.geteuid() == 0: os.fchown(child, metadata['uid'], metadata['gid'])
                os.fchmod(child, metadata['mode'])
                os.utime(child, (metadata['mtime'], metadata['mtime']))
                os.fsync(child)
                actual = os.fstat(child)
                require((stat.S_IMODE(actual.st_mode),actual.st_uid,actual.st_gid,int(actual.st_mtime)) ==
                        (metadata['mode'],metadata['uid'],metadata['gid'],int(metadata['mtime'])), 'Staged restore metadata mismatch')
            finally: os.close(child)
        from sv08_admin_jobs import Jobs
        # Upstream history's safe ancestry walk uses the real pathname, only
        # for read-only validation. Bind it to our held parent before and after.
        with opened(history_root) as check:
            require((os.fstat(check).st_dev, os.fstat(check).st_ino) ==
                    (stage.stat().st_dev, stage.stat().st_ino), 'History stage pathname changed')
        for name, metadata in members.items():
            if metadata and metadata['type'] == 'directory' and parts(name)[-1] == 'admin-image-jobs':
                view = Jobs(history_root.joinpath(*parts(name)), '').view()
                require((histories.get(name, {}).get('revision') == view['revision']) if view['fenced'] else name not in histories,
                        'Restored history does not match its committed binding')
        with opened(history_root) as check:
            require((os.fstat(check).st_dev, os.fstat(check).st_ino) ==
                    (stage.stat().st_dev, stage.stat().st_ino), 'History stage pathname changed')
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while block := os.read(fd, CHUNK): digest.update(block)
    return dict(sha256=digest.hexdigest(), entries=len(members)-1, bytes=total,
                required_bytes=total+4096*(len(members)+1), required_inodes=len(members)+1,
                metadata_sha256=hashlib.sha256(json.dumps(members, sort_keys=True).encode()).hexdigest())


def verify_fresh(root, directories, payloads, state):
    """Read the bounded fresh layout through held descriptors before commit."""
    owner = (os.geteuid(), os.getegid())
    expected = {(): ('directory', 0o700)}
    expected.update({path: ('directory', mode) for path, mode in directories.items()})
    expected.update({(name,): ('file', 0o600) for name in payloads})
    seen = set()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    def visit(fd, relative):
        info = os.fstat(fd)
        require(expected.get(relative) == ('directory', stat.S_IMODE(info.st_mode)) and
                (info.st_uid, info.st_gid) == owner, 'Fresh state directory metadata mismatch')
        seen.add(relative)
        for name in os.listdir(fd):
            path = (*relative, name)
            require(path in expected, 'Unexpected fresh state entry')
            kind, mode = expected[path]
            child = os.open(name, flags if kind == 'directory' else os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                if kind == 'directory':
                    visit(child, path)
                    continue
                before = os.fstat(child)
                payload = payloads[name]
                require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == len(payload) and
                        stat.S_IMODE(before.st_mode) == mode and (before.st_uid, before.st_gid) == owner,
                        'Fresh state file metadata mismatch')
                actual = os.read(child, len(payload)+1)
                require(actual == payload and not os.read(child, 1) and identity(os.fstat(child)) == identity(before),
                        'Fresh state readback mismatch')
                if name == 'state.json':
                    require(json.loads(actual, object_pairs_hook=unique_object) == state, 'Fresh state defaults mismatch')
                seen.add(path)
            finally: os.close(child)
    visit(root, ())
    require(seen == set(expected), 'Incomplete fresh state layout')


def fresh_state(parent, name):
    """Existing Store.initialize layout/defaults, pinned to an absent private stage.

    Parity is checked against the upstream Store method. That method prohibits
    proc descriptor ancestors, so recovery writes through directory descriptors.
    """
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open(name, flags, dir_fd=parent)
    try:
        expected_directories = {}
        directories = ('generations', 'shared/gcodes', 'shared/timelapse', 'shared/logs', 'shared/logs/journal',
            'system/ssh', 'system/network-connections', 'system/network-state', 'system/rauc', 'system/timesync',
            'system/rfkill', 'system/linger', 'system/cockpit/ws-certs.d', 'users/sv08', 'feed-bundles', 'uploads')
        for path in directories:
            fd = os.dup(root)
            try:
                components = path.split('/')
                for index, part in enumerate(components):
                    try: os.mkdir(part, 0o700 if index == len(components)-1 else 0o777, dir_fd=fd)
                    except FileExistsError: pass
                    child = os.open(part, flags, dir_fd=fd)
                    try:
                        entry = os.fstat(child)
                        relative = tuple(components[:index+1])
                        mode = expected_directories.get(relative, 0o700 if index == len(components)-1 else stat.S_IMODE(entry.st_mode))
                        require((entry.st_uid, entry.st_gid) == (os.geteuid(), os.getegid()) and
                                stat.S_IMODE(entry.st_mode) == mode and not mode & ~0o777,
                                'Unsafe fresh directory ownership or mode')
                        expected_directories[relative] = mode
                        os.fsync(fd)
                    except BaseException:
                        os.close(child)
                        raise
                    os.close(fd); fd = child
                os.fsync(fd)
            finally: os.close(fd)
        state = dict(format_version=1, requested_mode='immutable', auto_update=True, slots={}, pending=None)
        payloads = {'.lock': b'', 'state.json': (json.dumps(state, indent=2)+'\n').encode()}
        for filename, payload in payloads.items():
            fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root)
            try:
                with os.fdopen(os.dup(fd),'wb') as output: output.write(payload); output.flush()
                os.fsync(fd)
            finally: os.close(fd)
        os.fsync(root)
        verify_fresh(root, expected_directories, payloads, state)
    finally: os.close(root)


class Restore:
    def __init__(self, archives, targets, admission, reserve_bytes=32*1024**2, max_bytes=MAX_BYTES, max_entries=MAX_ENTRIES):
        self.archives, self.targets, self.admission = archives, targets, admission
        self.reserve_bytes, self.max_bytes, self.max_entries = reserve_bytes, max_bytes, max_entries
        require(type(reserve_bytes) is int and reserve_bytes >= 0 and type(max_bytes) is int and 0 <= max_bytes <= MAX_BYTES and
                type(max_entries) is int and 0 < max_entries <= MAX_ENTRIES, 'Invalid restore limits')

    def root(self, target, fresh=False):
        require(target in self.targets, 'Choose a configured restore target')
        root = Path(self.targets[target]['fresh_root' if fresh else 'root'])
        require(root.is_absolute() and str(root) == str(self.targets[target]['fresh_root' if fresh else 'root']) and
                root.name not in ('', '.', '..') and '..' not in root.parts, 'Invalid configured restore root')
        return root

    def absent(self, root):
        with opened(root.parent) as fd:
            try: os.stat(root.name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError: return [os.fstat(fd).st_dev, os.fstat(fd).st_ino]
            raise ValueError('Destination already exists; merge, overwrite and repair are refused')

    def space(self, root, detail):
        with opened(root.parent) as fd: fs = os.fstatvfs(fd)
        require(not fs.f_flag & os.ST_RDONLY and fs.f_bavail*(fs.f_frsize or fs.f_bsize) >= detail['required_bytes']+self.reserve_bytes and
                (not fs.f_files or fs.f_favail >= detail['required_inodes']), 'Insufficient restore space or inodes')

    def prepare(self, target, archive=None, fresh=False):
        root = self.root(target, fresh)
        with self.admission(target) as guard:
            parent = self.absent(root)
            if fresh:
                detail = dict(required_bytes=256*1024, required_inodes=64)
            else:
                require(archive in self.archives, 'Choose a configured archive')
                path = Path(self.archives[archive]['path'])
                require(not path.is_relative_to(root) and not root.is_relative_to(path), 'Archive and restore root overlap')
                with pinned_archive(path) as (fd, stamp): detail = dict(scan(fd, max_bytes=self.max_bytes, max_entries=self.max_entries), archive_identity=list(stamp))
            self.space(root, detail); guard.recheck()
            return dict(detail, target=target, archive=archive, fresh=fresh, root=str(root), parent=parent,
                        media_fingerprint=guard.fingerprint)

    def execute(self, plan):
        root = Path(plan['root'])
        with self.admission(plan['target']) as guard:
            require(plan['media_fingerprint'] == guard.fingerprint and self.absent(root) == plan['parent'], 'Restore media or parent changed')
            self.space(root, plan); guard.recheck()
            partial = '.sv08-restore-'+uuid.uuid4().hex+'.partial'
            with opened(root.parent) as parent:
                current = os.fstat(parent)
                require([current.st_dev, current.st_ino] == plan['parent'], 'Restore parent changed before staging')
                os.mkdir(partial, 0o700, dir_fd=parent)
                stage = Path('/proc/self/fd') / str(parent) / partial
                stage_identity = os.stat(partial, dir_fd=parent, follow_symlinks=False)
                # Leave failed staging identifiable, never promote it on retry.
                if plan['fresh']:
                    fresh_state(parent, partial)
                else:
                    with pinned_archive(self.archives[plan['archive']]['path']) as (fd, stamp):
                        require(list(stamp) == plan['archive_identity'], 'Restore archive identity changed')
                        detail = scan(fd, stage, self.max_bytes, self.max_entries, root.parent / partial)
                        require(all(plan[key] == value for key, value in detail.items()), 'Restore archive changed since review')
                fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try: os.fsync(fd)
                finally: os.close(fd)
                require(self.absent(root) == plan['parent'], 'Restore parent changed')
                now = os.stat(partial, dir_fd=parent, follow_symlinks=False)
                require((now.st_dev, now.st_ino) == (stage_identity.st_dev, stage_identity.st_ino), 'Restore staging directory changed')
                guard.recheck()
                publish(parent, partial, root.name)
                try:
                    os.fsync(parent); guard.recheck()
                    with opened(root) as reported:
                        current = os.fstat(reported)
                        require((current.st_dev, current.st_ino) == (stage_identity.st_dev, stage_identity.st_ino),
                                'Published restore pathname changed')
                    with opened(root.parent) as reported_parent:
                        current = os.fstat(reported_parent)
                        require([current.st_dev, current.st_ino] == plan['parent'], 'Published restore parent changed')
                except BaseException:
                    # Withdraw only our published inode; never an existing root.
                    current = os.stat(root.name, dir_fd=parent, follow_symlinks=False)
                    if (current.st_dev, current.st_ino) == (stage_identity.st_dev, stage_identity.st_ino):
                        publish(parent, root.name, partial); os.fsync(parent)
                    raise
        registry = root if plan['fresh'] else root / 'sv08'
        try: Store(registry).load(); condition = 'readable'
        except (OSError, ValueError, KeyError, TypeError): condition = 'unavailable or damaged; bytes preserved without repair'
        return dict(root=str(root), registry=condition, message=f"{'Fresh state created' if plan['fresh'] else 'User data restored'} at {root}. Registry: {condition}. No automatic boot selection or service activation.")
