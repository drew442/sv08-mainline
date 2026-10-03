"""Cooperative /data allocation admission; no higher-lock or device operations."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat

MIB = 1024 * 1024
BATCH_BYTES = 2752512
METADATA_BYTES = MIB
HISTORY_INODES = 64


def rounded(value, block):
    return ((value + block - 1) // block) * block


class Budget:
    def __init__(self, root, state_reserve=512*MIB, copy_limit=256*MIB,
                 staging_reserve=768*MIB):
        self.root = Path(root).absolute()
        self.floor = max(state_reserve + copy_limit, staging_reserve)

    @contextmanager
    def directory(self):
        for path in (self.root, *self.root.parents):
            info = path.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, os.geteuid()) or info.st_mode & 0o022):
                raise ValueError('Invalid allocation ancestry')
        directory_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(directory_fd)
            # Boot deliberately permits application traversal through /data/sv08.
            # The allocation lock remains administrator-only, owned and single-link.
            if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) not in (0o700, 0o711):
                raise ValueError('Allocation directory must be owned and private or traverse-only')
            yield directory_fd
        finally:
            os.close(directory_fd)

    @contextmanager
    def locked(self):
        from sv08_state import fsync_dir
        with self.directory() as directory_fd:
            fd = None
            try:
                fd = os.open('allocation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                        info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
                    raise ValueError('Invalid allocation lock')
                try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise ValueError('Shared data allocation is busy; refresh and review again') from None
                bound = os.stat('allocation.lock', dir_fd=directory_fd, follow_symlinks=False)
                if (bound.st_dev, bound.st_ino, bound.st_mode, bound.st_uid, bound.st_nlink) != (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink):
                    raise ValueError('Allocation lock changed')
                os.fsync(fd); os.fsync(directory_fd); fsync_dir(self.root.parent)
                yield self
            finally:
                if fd is not None: os.close(fd)

    def check(self, delta, inodes=0, result=False, byte_floor=0, inode_floor=0, fs=None):
        if fs is None:
            with self.directory() as fd: fs = os.fstatvfs(fd)
        block = fs.f_frsize or fs.f_bsize
        headroom = 0 if result else 2*rounded(BATCH_BYTES, block)+rounded(METADATA_BYTES, block)
        need = max(byte_floor, self.floor + rounded(delta, block)) + headroom
        inode_need = max(inode_floor, inodes + HISTORY_INODES)
        if fs.f_bavail*block < need or fs.f_favail < inode_need:
            raise ValueError('Insufficient shared data space or inodes; history and user data retained')
        return dict(required_bytes=need, required_inodes=inode_need, headroom_bytes=headroom)
