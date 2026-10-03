#!/usr/bin/env python3
"""Bounded recovery data export; no mounting, formatting, restoration or shell.

Caller supplies a verified, quiescent source and a leased destination through an
explicit admission context. No defaults assert hardware identity or quiescence.
Original integration around Python tarfile; see ADR 0010 and export tests.
"""
from contextlib import contextmanager
import hashlib
import ctypes
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import uuid

DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
CHUNK = 1024 * 1024
TAR_BUFFER = 10240


def publish(directory_fd, partial, name):
    """Linux/glibc no-replace rename, including supported FAT destinations."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    rename.restype = ctypes.c_int
    if rename(directory_fd, os.fsencode(partial), directory_fd, os.fsencode(name), 1):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def identity(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns,
            st.st_ctime_ns, st.st_uid, st.st_gid, st.st_nlink)


@contextmanager
def opened(root, relative=(), flags=DIRECTORY):
    """Open every component relative to held directories, never through links."""
    fd = os.open('/', DIRECTORY)
    try:
        parts = (*Path(root).absolute().parts[1:], *relative)
        for index, part in enumerate(parts):
            if part in ('', '.', '..') or '/' in part: raise ValueError('Invalid export path')
            new = os.open(part, flags if index == len(parts)-1 else DIRECTORY, dir_fd=fd)
            os.close(fd); fd = new
        yield fd
    finally:
        os.close(fd)


def inventory(root, limit=100000):
    result = []
    with opened(root) as root_fd:
        device = os.fstat(root_fd).st_dev
        def visit(fd, parts):
            with os.scandir(fd) as entries:
                names = sorted(entry.name for entry in entries)
            for name in names:
                entry = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if entry.st_dev != device or not (stat.S_ISREG(entry.st_mode) or stat.S_ISDIR(entry.st_mode)):
                    raise ValueError('Export requires regular files/directories on the source filesystem; links and special files are not followed')
                relative = (*parts, name)
                result.append((relative, identity(entry)))
                if len(result) > limit: raise ValueError('Export contains too many entries')
                if stat.S_ISDIR(entry.st_mode):
                    child = os.open(name, DIRECTORY, dir_fd=fd)
                    try:
                        if identity(os.fstat(child)) != identity(entry): raise ValueError('Source directory changed')
                        visit(child, relative)
                    finally: os.close(child)
        visit(root_fd, ())
    # Read-only validation does not create or repair source lock bookkeeping.
    paths = {relative for relative, _ in result}
    for relative, stamp in result:
        if relative[-1] == 'admin-image-jobs' and stat.S_ISDIR(stamp[2]):
            if (*relative, 'jobs.json') not in paths: raise ValueError('Missing committed history export manifest')
            from sv08_admin_jobs import Jobs
            Jobs(Path(root).joinpath(*relative), '').view()
    for relative, stamp in result:
        if stat.S_ISREG(stamp[2]) and stamp[8] != 1:
            if relative[-1] not in ('ledger.lock', 'history-format-v2.lock') or relative[-2:-1] != ('admin-image-jobs',) or stamp[8] != 2:
                raise ValueError('Unexpected export hardlink relationship')
            other = (*relative[:-1], 'history-format-v2.lock' if relative[-1] == 'ledger.lock' else 'ledger.lock')
            matching = next((value for path, value in result if path == other), None)
            if matching is None or matching[:2] != stamp[:2]: raise ValueError('Incomplete exported history fence')
    return result


def history_bindings(root, entries):
    result = []
    for relative, stamp in entries:
        if relative[-1] == 'admin-image-jobs' and stat.S_ISDIR(stamp[2]):
            from sv08_admin_jobs import Jobs
            view = Jobs(Path(root).joinpath(*relative), '').view()
            if view['fenced']:
                result.append(dict(path='data/'+'/'.join(relative), revision=view['revision'],
                                   alias='history-format-v2.lock', target='ledger.lock'))
    return result


def member(relative, stamp):
    info = tarfile.TarInfo('data/'+'/'.join(relative))
    info.mode, info.uid, info.gid, info.mtime = stat.S_IMODE(stamp[2]), stamp[6], stamp[7], stamp[4]//10**9
    info.type = tarfile.DIRTYPE if stat.S_ISDIR(stamp[2]) else tarfile.REGTYPE
    info.size = 0 if info.isdir() else stamp[3]
    if len(stamp) > 8 and stamp[8] == 2 and relative[-1] == 'history-format-v2.lock':
        info.type = tarfile.LNKTYPE
        info.linkname = 'data/'+'/'.join((*relative[:-1], 'ledger.lock'))
        info.size = 0
    return info


class HashReader:
    def __init__(self, stream): self.stream, self.hash = stream, hashlib.sha256()
    def read(self, size):
        block = self.stream.read(size); self.hash.update(block); return block


class HashWriter:
    """Record the exact bytes handed to the archive file, without reading it."""
    def __init__(self, stream):
        self.stream, self.hash, self.count = stream, hashlib.sha256(), 0

    def tell(self): return self.count

    def write(self, block):
        count = self.stream.write(block)
        if count != len(block): raise OSError('Short archive write')
        self.hash.update(block); self.count += count
        return count


class ReadbackReader:
    def __init__(self, stream, size, header_bytes):
        self.stream, self.size = stream, size
        self.hash, self.count = hashlib.sha256(), 0
        self.header_depth, self.header_start = 0, 0
        self.header_budget = header_bytes + TAR_BUFFER

    def read(self, size):
        if not 0 <= size <= CHUNK: raise ValueError('Unbounded archive readback request')
        if self.header_depth and self.count - self.header_start + size > self.header_budget:
            raise ValueError('Archive metadata exceeds its readback budget')
        block = self.stream.read(size)
        self.count += len(block); self.hash.update(block)
        if self.count > self.size: raise ValueError('Archive readback size changed')
        return block



@contextmanager
def restore_archive(path):
    """Bound metadata before tarfile decodes PAX/GNU/sparse declarations."""
    with open(path, 'rb', buffering=0) as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or not TAR_BUFFER <= info.st_size <= 2**32-1:
            raise ValueError('Invalid restore archive size or type')
        reader = ReadbackReader(source, info.st_size, 65536)
        class BudgetInfo(tarfile.TarInfo):
            @classmethod
            def fromtarfile(cls, archive):
                if not reader.header_depth: reader.header_start = reader.count
                reader.header_depth += 1
                try: return super().fromtarfile(archive)
                finally: reader.header_depth -= 1
        with tarfile.open(fileobj=reader, mode='r|', bufsize=TAR_BUFFER, tarinfo=BudgetInfo) as archive:
            yield archive, info.st_size
        while reader.read(CHUNK): pass
        if reader.count != info.st_size or identity(os.fstat(source.fileno())) != identity(info):
            raise ValueError('Restore archive changed during read')

def verify_stream(stream, expected, size, checksum, header_bytes):
    """One bounded semantic and whole-byte pass over this writer's own archive.

    The trusted writer supplies size/hash and its largest serialized header.
    A public TarInfo hook bounds cumulative metadata reads, including nested PAX
    and sparse maps, before corrupt declarations can cause large allocations.
    See host-recovery-readback.md for buffering limits and upstream provenance.
    """
    if type(size) is not int or size < TAR_BUFFER or type(header_bytes) is not int or not 512 <= header_bytes <= size:
        raise ValueError('Invalid archive readback bounds')
    reader = ReadbackReader(stream, size, header_bytes)
    class BudgetInfo(tarfile.TarInfo):
        @classmethod
        def fromtarfile(cls, archive):
            if not reader.header_depth: reader.header_start = reader.count
            reader.header_depth += 1
            try: return super().fromtarfile(archive)
            finally: reader.header_depth -= 1

    found = {}
    with tarfile.open(fileobj=reader, mode='r|', bufsize=TAR_BUFFER, tarinfo=BudgetInfo) as archive:
        for item in archive:
            if item.name in found: raise ValueError('Duplicate archive member')
            if item.name not in expected: raise ValueError('Unexpected archive member')
            # Our writer emits ordinary files, even for sparse source files.
            # Reject synthetic sparse expansion before extractfile can create it.
            if item.sparse is not None: raise ValueError('Unexpected sparse archive member')
            if not 0 <= item.size <= size: raise ValueError('Invalid archive member size')
            if item.isdir():
                found[item.name] = None
                continue
            if item.islnk():
                relation = expected[item.name]
                if not isinstance(relation, dict) or relation != {'hardlink': item.linkname} or item.size != 0:
                    raise ValueError('Unexpected archive link relationship')
                found[item.name] = relation
                continue
            if not item.isfile() or isinstance(expected[item.name], dict): raise ValueError('Unexpected archive member')
            with archive.extractfile(item) as payload:
                digest = hashlib.sha256()
                while block := payload.read(CHUNK): digest.update(block)
            found[item.name] = digest.hexdigest()
    if found != expected: raise ValueError('Export readback verification failed')
    # tarfile can stop before EOF, or treat a malformed later header as EOF.
    # Already buffered bytes have been hashed; drain only the underlying reader.
    while reader.read(CHUNK): pass
    if reader.count != size: raise ValueError('Archive readback size changed')
    if reader.hash.hexdigest() != checksum: raise ValueError('Archive byte readback verification failed')
    return reader.hash.hexdigest()


def verify_archive(path, expected, size, checksum, header_bytes):
    """Read through the held destination path; never extract onto recovery."""
    with open(path, 'rb', buffering=0) as stream:
        return verify_stream(stream, expected, size, checksum, header_bytes)


class Export:
    def __init__(self, source, destinations, admission, reserve_bytes=32*1024**2,
                 max_archive_bytes=2**32-1):
        self.source = Path(source).absolute()
        self.targets = destinations
        self.admission = admission
        self.reserve_bytes, self.max_archive_bytes = reserve_bytes, max_archive_bytes
        if type(reserve_bytes) is not int or reserve_bytes < 0 or type(max_archive_bytes) is not int or max_archive_bytes < 10240:
            raise ValueError('Invalid export limits')

    def destination(self, target_id):
        if target_id not in self.targets: raise ValueError('Choose a reviewed removable destination')
        target = Path(self.targets[target_id]['path']).absolute()
        if target.is_relative_to(self.source) or self.source.is_relative_to(target):
            raise ValueError('Export source and destination must not overlap')
        return target

    def prepare(self, target_id):
        target = self.destination(target_id)
        with self.admission(target_id) as guard:
            with opened(target) as fd: destination_identity = identity(os.fstat(fd))[:2]
            with opened(self.source) as fd: source_identity = identity(os.fstat(fd))[:2]
            entries = inventory(self.source)
            # Tar record padding plus an upper bound for the checksummed manifest.
            size = 10240 + sum(len(member(p, s).tobuf(format=tarfile.PAX_FORMAT)) + ((member(p, s).size+511)//512)*512 for p,s in entries)
            size += 10240 + sum(len(json.dumps('/'.join(p)).encode())+256 for p,s in entries)
            self.space(target, size)
            if guard is not None: guard.recheck()
            return dict(destination=target_id, source_identity=source_identity,
                        destination_identity=destination_identity, entries=entries, history=history_bindings(self.source, entries), required_bytes=size,
                        media_fingerprint=guard.fingerprint if guard is not None else None)

    def space(self, target, size):
        with opened(target) as fd: fs = os.fstatvfs(fd)
        if size > self.max_archive_bytes:
            raise ValueError('Archive exceeds the destination file-size limit')
        if fs.f_bavail*(fs.f_frsize or fs.f_bsize) < size+self.reserve_bytes or (fs.f_files and fs.f_favail < 2):
            raise ValueError('Insufficient destination space or inodes')

    def execute(self, plan):
        target = self.destination(plan['destination'])
        with self.admission(plan['destination']) as guard:
            if plan.get('media_fingerprint') != (guard.fingerprint if guard is not None else None):
                raise ValueError('Recovery media changed; review the export again')
            with opened(target) as target_fd, opened(self.source) as source_fd:
                if (identity(os.fstat(target_fd))[:2] != tuple(plan['destination_identity']) or
                        identity(os.fstat(source_fd))[:2] != tuple(plan['source_identity']) or
                        inventory(self.source) != plan['entries']):
                    raise ValueError('Source or destination changed; review the export again')
                self.space(target, plan['required_bytes'])
                if guard is not None: guard.recheck()
                name = 'sv08-user-data-'+uuid.uuid4().hex+'.tar'
                partial = '.'+name+'.partial'
                expected = {}; records = []; created = False; published = False; completed = False
                try:
                    fd = os.open(partial, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=target_fd)
                    created = True
                    with os.fdopen(fd, 'w+b') as output:
                        writer = HashWriter(output)
                        header_bytes = 512
                        with tarfile.open(fileobj=writer, mode='w', format=tarfile.PAX_FORMAT) as archive:
                            for relative, stamp in plan['entries']:
                                info = member(relative, stamp)
                                header_bytes = max(header_bytes, len(info.tobuf(format=archive.format,
                                    encoding=archive.encoding, errors=archive.errors)))
                                if info.isdir():
                                    archive.addfile(info); expected[info.name] = None; continue
                                if info.islnk():
                                    archive.addfile(info); expected[info.name] = {'hardlink': info.linkname}
                                    records.append(dict(path=info.name, hardlink=info.linkname))
                                    continue
                                with opened(self.source, relative, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as source:
                                    if identity(os.fstat(source)) != stamp: raise ValueError('Source file changed')
                                    with os.fdopen(os.dup(source), 'rb') as stream:
                                        reader = HashReader(stream); archive.addfile(info, reader)
                                    if identity(os.fstat(source)) != stamp: raise ValueError('Source file changed during export')
                                    checksum = reader.hash.hexdigest()
                                    expected[info.name] = checksum
                                    records.append(dict(path=info.name, bytes=info.size, sha256=checksum))
                            manifest = json.dumps(dict(format_version=1, kind='user-data-export-not-os-image', files=records, history=plan.get('history', [])), sort_keys=True).encode()
                            info = tarfile.TarInfo('export-manifest.json'); info.size=len(manifest); info.mode=0o600
                            header_bytes = max(header_bytes, len(info.tobuf(format=archive.format,
                                encoding=archive.encoding, errors=archive.errors)))
                            archive.addfile(info, io.BytesIO(manifest))
                            expected[info.name] = hashlib.sha256(manifest).hexdigest()
                        output.flush(); os.fsync(output.fileno())
                        if output.tell() > plan['required_bytes']: raise ValueError('Archive exceeded its admitted budget')
                        partial_stat = os.fstat(output.fileno())
                        partial_identity = (partial_stat.st_dev, partial_stat.st_ino,
                                             partial_stat.st_mode, partial_stat.st_nlink)
                    if inventory(self.source) != plan['entries'] or history_bindings(self.source, plan['entries']) != plan.get('history', []): raise ValueError('Source changed during export')
                    with opened(self.source) as now:
                        if identity(os.fstat(now))[:2] != tuple(plan['source_identity']): raise ValueError('Source changed')
                    # Read via the held destination descriptor even if the mount path changes.
                    checksum = verify_archive(f'/proc/self/fd/{target_fd}/{partial}', expected,
                                              writer.count, writer.hash.hexdigest(), header_bytes)
                    # Revalidate paths before publishing into the still-held destination.
                    with opened(target) as now:
                        if identity(os.fstat(now))[:2] != tuple(plan['destination_identity']): raise ValueError('Destination changed')
                    # The pathname may have been replaced while verification used the
                    # held descriptor.  Publish only the same single-link regular file
                    # that was written and verified; never rename a replacement inode.
                    current = os.stat(partial, dir_fd=target_fd, follow_symlinks=False)
                    current_identity = (current.st_dev, current.st_ino, current.st_mode, current.st_nlink)
                    if (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1 or
                            current_identity != partial_identity):
                        raise ValueError('Archive partial changed before publication')
                    if guard is not None: guard.recheck()
                    publish(target_fd, partial, name)
                    published = True
                    os.fsync(target_fd)
                    if guard is not None: guard.recheck()
                    completed = True
                    return dict(filename=name, sha256=checksum, files=len(records),
                                message='User data saved and readback verified: '+name+'. Includes private configuration and credentials; keep the destination private.')
                finally:
                    if published and not completed:
                        # Only this operation's output; never a pre-existing file.
                        # Physical removal/power loss can still prevent cleanup.
                        os.unlink(name, dir_fd=target_fd)
                        os.fsync(target_fd)
                    if created:
                        try: os.unlink(partial, dir_fd=target_fd)
                        except (FileNotFoundError, IsADirectoryError): pass


class ExportAdapter:
    """Recovery adapter for export only; media discovery/admission are external."""
    def __init__(self, exporter): self.exporter = exporter
    def images(self): return []
    def destinations(self):
        return [dict(id=key, label=value['label']) for key, value in self.exporter.targets.items()]
    def capability(self, action, view):
        if action == 'recovery.export' and self.exporter.targets: return True, ''
        return False, 'No verified backend is available for this operation.'
    def summary(self, plan):
        digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
        return dict(fingerprint=digest, destination=plan['destination'],
                    label=self.exporter.targets[plan['destination']]['label'],
                    required_bytes=plan['required_bytes'], entries=len(plan['entries']))
    def review_export(self, target): return self.summary(self.exporter.prepare(target))
    def apply(self, plan):
        if plan['action'] != 'recovery.export': raise ValueError('Unsupported export operation')
        prepared = self.exporter.prepare(plan['arguments']['destination'])
        if self.summary(prepared) != plan['export']:
            raise ValueError('Export source or destination changed. Review again.')
        return self.exporter.execute(prepared)


def restore_history(archive_path, destination, exclusive):
    """Restore one history directory into a NEW isolated destination under lease.

    Caller must exclude live helpers, workers and open lock waiters. This is not
    a live-lock replacement or a recovery UI operation. Never extract arbitrary
    archive paths. The resulting directory is published only after validation.
    """
    from sv08_admin_jobs import Jobs
    from sv08_admin_history import OBJECT, TEMP, ENTRIES, ALLOCATED, BATCH_BYTES, METADATA_BYTES, strict_json
    from sv08_state import fsync_dir
    import re
    import shutil
    destination = Path(destination)
    if destination.exists() or destination.is_symlink(): raise ValueError('Restore requires a new isolated destination')
    with exclusive():
        with opened(destination.parent) as parent_fd:
            parent = os.fstat(parent_fd)
            if parent.st_uid != os.geteuid() or parent.st_mode & 0o022:
                raise ValueError('Unsafe isolated restore parent')
            fs = os.fstatvfs(parent_fd)
        block = fs.f_frsize or fs.f_bsize
        if fs.f_bavail*block < ALLOCATED+4*block or fs.f_favail < ENTRIES+4:
            raise ValueError('Insufficient isolated restore destination space or inodes')
        temporary = destination.parent / ('.history-restore-'+uuid.uuid4().hex)
        temporary.mkdir(mode=0o700)
        try:
            count, total, aliases, prefixes, export = 0, 0, [], set(), None
            with restore_archive(archive_path) as (archive, archive_size):
                seen = set()
                for item in archive:
                    if item.name in seen: raise ValueError('Duplicate archive member')
                    seen.add(item.name)
                    if len(seen) > 100000: raise ValueError('Too many restore archive entries')
                    parts = item.name.split('/')
                    if any(part in ('', '.', '..') for part in parts) or item.sparse is not None or not 0 <= item.size <= archive_size:
                        raise ValueError('Unsafe restore archive path')
                    if item.name == 'export-manifest.json':
                        if not item.isfile() or item.size > 32*METADATA_BYTES: raise ValueError('Invalid export manifest')
                        with archive.extractfile(item) as payload:
                            raw = bytearray()
                            while block := payload.read(CHUNK): raw.extend(block)
                        export = strict_json(raw)
                    if len(parts) < 3 or parts[-2] != 'admin-image-jobs': continue
                    prefixes.add('/'.join(parts[:-1])); name = parts[-1]
                    if name not in ('jobs.json', 'ledger.lock', 'history-format-v2.lock', 'worker.lock') and not re.fullmatch(OBJECT, name) and not re.fullmatch(TEMP, name):
                        raise ValueError('Unexpected history restore entry')
                    count += 1
                    if count+1 > ENTRIES or item.size > BATCH_BYTES or item.mode != 0o600 or item.uid != os.geteuid():
                        raise ValueError('History restore exceeds bounds or ownership')
                    total += item.size
                    if total > ALLOCATED: raise ValueError('History restore exceeds storage bound')
                    if item.islnk():
                        if name != 'history-format-v2.lock' or item.linkname != '/'.join((*parts[:-1], 'ledger.lock')) or item.size:
                            raise ValueError('Unexpected restored fence relationship')
                        aliases.append(name); continue
                    if not item.isfile(): raise ValueError('Unexpected history restore member')
                    with archive.extractfile(item) as source, (temporary / name).open('xb') as output:
                        os.fchmod(output.fileno(), 0o600)
                        checksum = hashlib.sha256(); remaining = item.size
                        while remaining:
                            block = source.read(min(CHUNK, remaining))
                            if not block: raise ValueError('Truncated history restore')
                            output.write(block); checksum.update(block); remaining -= len(block)
                        output.flush(); os.fsync(output.fileno())
            if len(prefixes) != 1 or export is None: raise ValueError('Restore needs one complete history and export manifest')
            if (not isinstance(export, dict) or set(export) != {'format_version', 'kind', 'files', 'history'} or
                    type(export['format_version']) is not int or export['format_version'] != 1 or
                    export['kind'] != 'user-data-export-not-os-image' or not isinstance(export['files'], list) or
                    len(export['files']) > 100000 or not isinstance(export['history'], list)):
                raise ValueError('Invalid complete restore inventory')
            records = {}
            prefix = next(iter(prefixes))
            for record in export['files']:
                if not isinstance(record, dict) or not isinstance(record.get('path'), str) or record['path'] in records:
                    raise ValueError('Invalid or duplicate restore inventory record')
                parts = record['path'].split('/')
                if any(part in ('', '.', '..') for part in parts): raise ValueError('Unsafe restore inventory path')
                if len(parts) >= 3 and parts[-2] == 'admin-image-jobs' and '/'.join(parts[:-1]) != prefix:
                    raise ValueError('Restore needs one history inventory')
                records[record['path']] = record
            expected_names = {name[len(prefix)+1:] for name in records if name.startswith(prefix+'/')}
            actual_names = set(os.listdir(temporary)) | set(aliases)
            if 'jobs.json' not in actual_names or expected_names != actual_names:
                raise ValueError('Incomplete committed history restore inventory')
            for name in os.listdir(temporary):
                full = prefix+'/'+name
                path = temporary / name
                if records.get(full) != dict(path=full, bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()):
                    raise ValueError('Restored history checksum mismatch')
            if aliases:
                if aliases != ['history-format-v2.lock']: raise ValueError('Duplicate restored fence')
                os.link(temporary / 'ledger.lock', temporary / aliases[0])
            view = Jobs(temporary, '').view()
            if view['fenced']:
                expected = dict(path=next(iter(prefixes)), revision=view['revision'], alias='history-format-v2.lock', target='ledger.lock')
                if export.get('history') != [expected]: raise ValueError('Restored relationship is not bound to committed history')
                alias_record = dict(path=next(iter(prefixes))+'/history-format-v2.lock', hardlink=next(iter(prefixes))+'/ledger.lock')
                if records.get(alias_record['path']) != alias_record: raise ValueError('Missing exported relationship')
            elif export['history']:
                raise ValueError('Unexpected legacy history relationship')
            fsync_dir(temporary); fsync_dir(temporary.parent)
            with opened(temporary.parent) as fd: publish(fd, temporary.name, destination.name); os.fsync(fd)
            return dict(revision=view['revision'], count=len(view['rows']))
        finally:
            if temporary.exists(): shutil.rmtree(temporary)
