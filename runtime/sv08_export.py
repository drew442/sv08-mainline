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
            st.st_ctime_ns, st.st_uid, st.st_gid)


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
    return result


def member(relative, stamp):
    info = tarfile.TarInfo('data/'+'/'.join(relative))
    info.mode, info.uid, info.gid, info.mtime = stat.S_IMODE(stamp[2]), stamp[6], stamp[7], stamp[4]//10**9
    info.type = tarfile.DIRTYPE if stat.S_ISDIR(stamp[2]) else tarfile.REGTYPE
    info.size = 0 if info.isdir() else stamp[3]
    return info


class HashReader:
    def __init__(self, stream): self.stream, self.hash = stream, hashlib.sha256()
    def read(self, size):
        block = self.stream.read(size); self.hash.update(block); return block


def verify_archive(path, expected):
    """Full file-content readback, never extract an archive onto the recovery OS."""
    found = {}
    with tarfile.open(path, 'r:') as archive:
        for item in archive:
            if item.name in found: raise ValueError('Duplicate archive member')
            if item.isdir():
                found[item.name] = None
                continue
            if not item.isfile(): raise ValueError('Unexpected archive member')
            stream = archive.extractfile(item)
            digest = hashlib.sha256()
            while block := stream.read(1024*1024): digest.update(block)
            found[item.name] = digest.hexdigest()
    if found != expected: raise ValueError('Export readback verification failed')


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
        with self.admission(target_id):
            with opened(target) as fd: destination_identity = identity(os.fstat(fd))[:2]
            with opened(self.source) as fd: source_identity = identity(os.fstat(fd))[:2]
            entries = inventory(self.source)
            # Tar record padding plus an upper bound for the checksummed manifest.
            size = 10240 + sum(len(member(p, s).tobuf(format=tarfile.PAX_FORMAT)) + ((member(p, s).size+511)//512)*512 for p,s in entries)
            size += 10240 + sum(len(json.dumps('/'.join(p)).encode())+256 for p,s in entries)
            self.space(target, size)
            return dict(destination=target_id, source_identity=source_identity,
                        destination_identity=destination_identity, entries=entries, required_bytes=size)

    def space(self, target, size):
        with opened(target) as fd: fs = os.fstatvfs(fd)
        if size > self.max_archive_bytes:
            raise ValueError('Archive exceeds the destination file-size limit')
        if fs.f_bavail*(fs.f_frsize or fs.f_bsize) < size+self.reserve_bytes or (fs.f_files and fs.f_favail < 2):
            raise ValueError('Insufficient destination space or inodes')

    def execute(self, plan):
        target = self.destination(plan['destination'])
        with self.admission(plan['destination']):
            with opened(target) as target_fd, opened(self.source) as source_fd:
                if (identity(os.fstat(target_fd))[:2] != tuple(plan['destination_identity']) or
                        identity(os.fstat(source_fd))[:2] != tuple(plan['source_identity']) or
                        inventory(self.source) != plan['entries']):
                    raise ValueError('Source or destination changed; review the export again')
                self.space(target, plan['required_bytes'])
                name = 'sv08-user-data-'+uuid.uuid4().hex+'.tar'
                partial = '.'+name+'.partial'
                expected = {}; records = []; created = False
                try:
                    fd = os.open(partial, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=target_fd)
                    created = True
                    with os.fdopen(fd, 'w+b') as output:
                        with tarfile.open(fileobj=output, mode='w', format=tarfile.PAX_FORMAT) as archive:
                            for relative, stamp in plan['entries']:
                                info = member(relative, stamp)
                                if info.isdir():
                                    archive.addfile(info); expected[info.name] = None; continue
                                with opened(self.source, relative, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as source:
                                    if identity(os.fstat(source)) != stamp: raise ValueError('Source file changed')
                                    with os.fdopen(os.dup(source), 'rb') as stream:
                                        reader = HashReader(stream); archive.addfile(info, reader)
                                    if identity(os.fstat(source)) != stamp: raise ValueError('Source file changed during export')
                                    checksum = reader.hash.hexdigest()
                                    expected[info.name] = checksum
                                    records.append(dict(path=info.name, bytes=info.size, sha256=checksum))
                            manifest = json.dumps(dict(format_version=1, kind='user-data-export-not-os-image', files=records), sort_keys=True).encode()
                            info = tarfile.TarInfo('export-manifest.json'); info.size=len(manifest); info.mode=0o600
                            archive.addfile(info, io.BytesIO(manifest))
                            expected[info.name] = hashlib.sha256(manifest).hexdigest()
                        output.flush(); os.fsync(output.fileno())
                        if output.tell() > plan['required_bytes']: raise ValueError('Archive exceeded its admitted budget')
                        output.seek(0)
                        digest = hashlib.sha256()
                        while block := output.read(1024*1024): digest.update(block)
                    if inventory(self.source) != plan['entries']: raise ValueError('Source changed during export')
                    with opened(self.source) as now:
                        if identity(os.fstat(now))[:2] != tuple(plan['source_identity']): raise ValueError('Source changed')
                    # Read via the held destination descriptor even if the mount path changes.
                    verify_archive(f'/proc/self/fd/{target_fd}/{partial}', expected)
                    # Revalidate paths before publishing into the still-held destination.
                    with opened(target) as now:
                        if identity(os.fstat(now))[:2] != tuple(plan['destination_identity']): raise ValueError('Destination changed')
                    publish(target_fd, partial, name)
                    os.fsync(target_fd)
                    return dict(filename=name, sha256=digest.hexdigest(), files=len(records),
                                message='User data saved and readback verified: '+name+'. Includes private configuration and credentials; keep the destination private.')
                finally:
                    if created:
                        try: os.unlink(partial, dir_fd=target_fd)
                        except FileNotFoundError: pass


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
