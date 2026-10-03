#!/usr/bin/env python3
"""Attended SD whole-image writer. Linux admission + stdlib; no boot actions.

Original SD-specific glue; retire when upstream recovery supports this journey.
Configuration is coordinator-prepared, never entered as a device path in the UI.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat

BUFFER = 1024 * 1024
BLKGETSIZE64 = 0x80081272
BLKFLSBUF = 0x1261
EFFECT = ('The complete image range, including image-contained user data and '
          'environment, will be replaced. Files are not preserved.')
FAILURE = 'The installed image may be unusable. Keep SD as the manual recovery route.'
CONFIG = Path('/run/sv08/sd-reimage.json')


def digest(fd, size):
    result = hashlib.sha256()
    offset = 0
    while offset < size:
        data = os.pread(fd, min(BUFFER, size-offset), offset)
        if not data:
            raise ValueError('Image truncated or readback incomplete')
        result.update(data)
        offset += len(data)
    return result.hexdigest()


def devnum(value):
    return f'{os.major(value)}:{os.minor(value)}'


class LinuxAdmission:
    """Fail closed for unknown storage ancestry; inspect current mount namespace."""
    def __init__(self, sys=Path('/sys'), proc=Path('/proc'), marker=Path('/run/sv08/recovery-verified')):
        self.sys, self.proc, self.marker = sys, proc, marker

    def node(self, dev):
        path = self.sys/'dev/block'/dev
        if not path.exists():
            raise ValueError('Unknown block-device ancestry: '+dev)
        return path.resolve()

    def depends(self, dev, target, seen=None):
        # Non-block mounts (tmpfs, NFS, proc) have major zero.
        if dev.startswith('0:'):
            return False
        seen = set() if seen is None else seen
        if dev in seen:
            raise ValueError('Cyclic storage ancestry')
        seen = seen | {dev}
        node = self.node(dev)
        if node == target or target in node.parents:
            return True
        slaves = list((node/'slaves').glob('*'))
        if any(self.depends((s/'dev').read_text().strip(), target, seen) for s in slaves):
            return True
        backing = node/'loop/backing_file'
        if backing.exists():
            name = backing.read_text().strip()
            return self.depends(devnum(os.stat('/'+name.lstrip('/')).st_dev), target, seen)
        return False

    def check(self, cfg, source, target):
        ts = os.fstat(target)
        if not stat.S_ISBLK(ts.st_mode):
            raise ValueError('Production requires a block target')
        if devnum(ts.st_rdev) != cfg['dev_t'] or os.stat(cfg['target']).st_rdev != ts.st_rdev:
            raise ValueError('Stale target dev_t')
        node = self.node(cfg['dev_t'])
        if (node/'partition').exists() or not re.fullmatch(r'mmcblk[0-9]+', node.name):
            raise ValueError('Whole eMMC user area required; boot partitions forbidden')
        device = (node/'device').resolve()
        if ((device/'type').read_text().strip() != 'MMC' or
                (device/'cid').read_text().strip() != cfg['cid'] or
                str(device.parent) != cfg['controller']):
            raise ValueError('Controller/CID mismatch')
        matches = []
        for candidate in (self.sys/'class/block').glob('mmcblk*'):
            if not re.fullmatch(r'mmcblk[0-9]+', candidate.name): continue
            d = (candidate/'device').resolve()
            if (str(d.parent) == cfg['controller'] and
                    (d/'cid').read_text().strip() == cfg['cid']):
                matches.append(candidate.resolve())
        if matches != [node]:
            raise ValueError('Ambiguous or missing controller/CID identity')
        if not self.marker.is_file():
            raise ValueError('Independent recovery gate missing')
        mounts = (self.proc/'self/mountinfo').read_text().splitlines()
        source_stat = os.fstat(source)
        if self.depends(devnum(source_stat.st_dev), node):
            raise ValueError('Source on target')
        # Source must be a coordinator-mounted read-only filesystem, not tmpfs.
        matching = [m.split() for m in mounts if m.split()[2] == devnum(source_stat.st_dev)
                    and Path(cfg['source']).resolve().is_relative_to(Path(m.split()[4]))]
        if not matching or any('ro' not in m[5].split(',') for m in matching):
            raise ValueError('Source needs independent read-only mount')
        for m in mounts:
            if self.depends(m.split()[2], node):
                raise ValueError('Target mounted/in use')
        for child in [node, *node.glob(node.name+'p*')]:
            if list((child/'holders').glob('*')):
                raise ValueError('Target held/in use')
        for line in (self.proc/'swaps').read_text().splitlines()[1:]:
            ss = os.stat(line.split()[0])
            if self.depends(devnum(ss.st_rdev if stat.S_ISBLK(ss.st_mode) else ss.st_dev), node):
                raise ValueError('Target swap/in use')
        capacity = int.from_bytes(fcntl.ioctl(target, BLKGETSIZE64, bytes(8)), 'little')
        if capacity < cfg['size']:
            raise ValueError('Insufficient target capacity')


class FileFixtureAdmission:
    """Explicit disposable tests only. Never selected by production config."""
    def check(self, cfg, source, target):
        ss, ts = os.fstat(source), os.fstat(target)
        current = os.stat(cfg['target'])
        if not stat.S_ISREG(ts.st_mode) or (ts.st_dev, ts.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError('Stale fixture target')
        if (ss.st_dev, ss.st_ino) == (ts.st_dev, ts.st_ino):
            raise ValueError('Source on target')
        if ts.st_size < cfg['size']:
            raise ValueError('Insufficient target capacity')


class Session:
    def __init__(self, cfg, admission=None):
        self.cfg = dict(cfg)
        self.admission = admission if admission is not None else LinuxAdmission()
        self.source = self.target = None
        self.used = False
        try:
            if (type(cfg['size']) is not int or cfg['size'] <= 0 or
                    not re.fullmatch('[0-9a-f]{64}', cfg['sha256'])):
                raise ValueError('Expected positive image size and SHA-256 required')
            self.source = os.open(cfg['source'], os.O_RDONLY | os.O_NOFOLLOW)
            if not stat.S_ISREG(os.fstat(self.source).st_mode):
                raise ValueError('Regular source file required')
            self.target = os.open(cfg['target'], os.O_RDWR | os.O_NOFOLLOW | os.O_EXCL)
            fcntl.flock(self.target, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.recheck()
            if digest(self.source, cfg['size']) != cfg['sha256']:
                raise ValueError('Source checksum mismatch')
        except Exception:
            self.close()
            raise

    def recheck(self):
        ss = os.fstat(self.source)
        current = os.stat(self.cfg['source'])
        if ss.st_size != self.cfg['size'] or (ss.st_dev, ss.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError('Source missing, stale or wrong size')
        self.admission.check(self.cfg, self.source, self.target)

    def review(self):
        return (f"Image: {self.cfg['source']}\nSize: {self.cfg['size']} bytes\n"
                f"SHA-256: {self.cfg['sha256']}\nTarget: {self.cfg['target']}\n"
                f"Controller: {self.cfg.get('controller', 'TEST FIXTURE')}\n"
                f"CID: {self.cfg.get('cid', 'TEST FIXTURE')}\n"
                f"dev_t: {self.cfg.get('dev_t', 'TEST FIXTURE')}\n\n{EFFECT}")

    def apply(self, yes=False):
        if self.used:
            raise ValueError('This invocation has already answered')
        self.used = True
        if yes is not True:
            self.close()
            return 'No write. Restart manually only when ready.'
        try:
            self.recheck()  # under held exclusive descriptor/lock, after Yes
            transferred = hashlib.sha256()
            offset = 0
            while offset < self.cfg['size']:
                data = os.pread(self.source, min(BUFFER, self.cfg['size']-offset), offset)
                if not data:
                    raise ValueError('Source truncated during transfer')
                done = 0
                while done < len(data):
                    count = os.pwrite(self.target, data[done:], offset+done)
                    if count <= 0:
                        raise OSError('Zero-length write')
                    done += count
                transferred.update(data)
                offset += len(data)
            if transferred.hexdigest() != self.cfg['sha256'] or os.fstat(self.source).st_size != self.cfg['size']:
                raise ValueError('Transferred source checksum/size mismatch')
            os.fsync(self.target)
            if stat.S_ISBLK(os.fstat(self.target).st_mode):
                fcntl.ioctl(self.target, BLKFLSBUF)
            else:
                os.posix_fadvise(self.target, 0, self.cfg['size'], os.POSIX_FADV_DONTNEED)
            if digest(self.target, self.cfg['size']) != self.cfg['sha256']:
                raise ValueError('Full readback checksum mismatch')
            return ('Complete image-range write, flush and readback matched. '+EFFECT+
                    ' Restart manually when ready; SD remains the recovery route.')
        except Exception as exc:
            raise ValueError(str(exc)+'. '+FAILURE) from exc
        finally:
            self.close()

    def close(self):
        for name in ('source', 'target'):
            fd = getattr(self, name, None)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)


def installed_session():
    return Session(json.loads(CONFIG.read_text()))
