#!/usr/bin/env python3
"""Admission for explicitly prepared recovery media; never mounts or repairs.

Only a reviewed, dedicated recovery userspace may supply the production policy
and per-boot context. All its media mutators must use MediaLease. Kernel checks
verify that contract's current root, namespace and simple block topology; flock
does not constrain arbitrary privileged software. See host-recovery-media.md.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from sv08_export import Export, ExportAdapter, opened

PROTOCOL = 'sv08-recovery-media-v1'
POLICY = Path('/etc/sv08/recovery-media-policy.json')
CONTEXT = Path('/run/sv08-recovery/media-context.json')
LOCK = Path('/run/sv08-recovery/media.lock')
PROVIDER_MANIFEST = Path('/etc/sv08/recovery-image.json')
ENVELOPE_MANIFEST = Path('/etc/sv08/recovery-envelope.manifest')
WRITER_MODEL = 'reviewed-recovery-only; all-media-mutators-use-MediaLease'
PROC_DISAPPEARED = (FileNotFoundError, ProcessLookupError)

# systemd v257.13 creates these kernel API mounts before ordinary units. Keep
# this selected-userspace composition finite: a filesystem type alone never
# authorizes another path, and generic /sys or /dev ancestry is insufficient.
KERNEL_API_MOUNTS = {
    '/sys/kernel/security': ('securityfs', 'securityfs',
        ('nodev', 'noexec', 'nosuid', 'relatime', 'rw'), ('rw',)),
    '/sys/fs/pstore': ('pstore', 'pstore',
        ('nodev', 'noexec', 'nosuid', 'relatime', 'rw'), ('rw',)),
    '/sys/fs/bpf': ('bpf', 'bpf',
        ('nodev', 'noexec', 'nosuid', 'relatime', 'rw'), ('mode=700', 'rw')),
    '/dev/mqueue': ('mqueue', 'mqueue',
        ('nodev', 'noexec', 'nosuid', 'relatime', 'rw'), ('rw',)),
    '/sys/kernel/tracing': ('tracefs', 'tracefs',
        ('nodev', 'noexec', 'nosuid', 'relatime', 'rw'), ('rw',)),
    '/sys/kernel/debug': ('debugfs', 'debugfs',
        ('nodev', 'noexec', 'nosuid', 'relatime', 'rw'), ('rw',)),
    '/dev/hugepages': ('hugetlbfs', 'hugetlbfs',
        ('nodev', 'nosuid', 'relatime', 'rw'), ('pagesize=2M', 'rw')),
    '/sys/fs/fuse/connections': ('fusectl', 'fusectl',
        ('nodev', 'noexec', 'nosuid', 'relatime', 'rw'), ('rw',)),
    '/sys/kernel/config': ('configfs', 'configfs',
        ('nodev', 'noexec', 'nosuid', 'relatime', 'rw'), ('rw',)),
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def clean_path(value):
    require(isinstance(value, str) and value.startswith('/') and
            str(Path(value)) == value and '..' not in Path(value).parts,
            'Media paths must be explicit, normalized absolute paths')
    return Path(value)


def trusted_file(path):
    """No symlinks, writable ancestors or non-root ownership in trust inputs."""
    require(os.geteuid() == 0, 'Recovery media admission requires the trusted root service')
    path = clean_path(str(path))
    for parent in reversed(path.parents):
        with opened(parent) as fd:
            info = os.fstat(fd)
            require(info.st_uid == 0 and not info.st_mode & 0o022,
                    'Untrusted recovery configuration directory: '+str(parent))
    with opened(path, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as fd:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and
                not info.st_mode & 0o022 and info.st_nlink == 1 and info.st_size <= 1024*1024,
                'Untrusted recovery configuration file: '+str(path))
        with os.fdopen(os.dup(fd), 'rb') as stream:
            return stream.read(1024*1024+1)


def mount_table(text):
    """Keep VFS options distinct from filesystem-superblock options."""
    def unescape(value):
        return re.sub(r'\\(040|011|012|134)', lambda m: chr(int(m[1], 8)), value)
    result = []
    for line in text.splitlines():
        left, right = line.split(' - ')
        fields, fs = left.split(), right.split()
        require(len(fields) >= 6 and len(fs) == 3, 'Invalid kernel mount information')
        result.append(dict(id=int(fields[0]), parent=int(fields[1]), device=fields[2],
                           root=unescape(fields[3]), path=unescape(fields[4]),
                           options=sorted(fields[5].split(',')), optional=sorted(fields[6:]),
                           filesystem=fs[0], source=unescape(fs[1]),
                           super_options=sorted(fs[2].split(','))))
    require(len({m['id'] for m in result}) == len(result) and
            len({m['path'] for m in result}) == len(result), 'Ambiguous overmounted paths')
    return result


def admitted_system_mount(mount, selected_paths):
    """Admit selected mounts or the exact measured kernel API composition."""
    if mount['path'] in selected_paths:
        return True
    expected = KERNEL_API_MOUNTS.get(mount['path'])
    if expected is not None:
        filesystem, source, options, super_options = expected
        return (mount['root'] == '/' and mount['filesystem'] == filesystem and
                mount['source'] == source and tuple(mount['options']) == options and
                tuple(mount['super_options']) == super_options)
    kernel_filesystems = {'proc', 'sysfs', 'devtmpfs', 'tmpfs', 'devpts', 'cgroup2'}
    return (mount['filesystem'] in kernel_filesystems and
            any(Path(mount['path']).is_relative_to(base)
                for base in ('/proc', '/sys', '/dev', '/run', '/tmp')))


class MediaLease:
    """The one admission protocol for export AND premount/change/eject tools.

    Never remove or replace the lock file. Production uses the fixed global path;
    fixture callers may pass a private path under their explicitly marked root.
    A lease alone grants no target identity or authorization to change hardware.
    """
    def __init__(self, path=LOCK):
        self.path, self.fd = Path(path), None

    def __enter__(self):
        with opened(self.path.parent) as parent:
            info = os.fstat(parent)
            require(info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700,
                    'Shared media admission directory must be root-owned and private')
            fd = os.open(self.path.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                         0o600, dir_fd=parent)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and
                    stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1,
                    'Untrusted shared media lease')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('Another recovery media operation owns admission') from None
            self.fd = fd
            self.check()
            return self
        except BaseException:
            self.fd = None
            os.close(fd)
            raise

    def check(self):
        require(self.fd is not None, 'Media lease is not held')
        now = os.stat(self.path, follow_symlinks=False)
        held = os.fstat(self.fd)
        require((now.st_dev, now.st_ino, now.st_mode, now.st_nlink) ==
                (held.st_dev, held.st_ino, held.st_mode, 1), 'Shared media lease was replaced')

    def __exit__(self, *_):
        os.close(self.fd)
        self.fd = None


class Kernel:
    def mounts(self):
        return mount_table(Path('/proc/self/mountinfo').read_text())

    @staticmethod
    def _pinned_stat(directory_fd):
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
        fd = os.open('stat', flags, dir_fd=directory_fd)
        try:
            data = os.read(fd, 4097)
            require(len(data) <= 4096 and os.read(fd, 1) == b'',
                    'Malformed process stat information')
        finally:
            os.close(fd)
        try:
            fields = data.decode().rsplit(')', 1)[1].split()
            require(len(fields) > 6 and fields[0] in
                    ('R', 'S', 'D', 'Z', 'T', 't', 'X', 'x', 'K', 'W', 'P', 'I'),
                    'Malformed process stat information')
            int(fields[6])
        except (UnicodeDecodeError, IndexError, ValueError):
            raise ValueError('Malformed process stat information') from None
        return fields

    def _pinned_terminated(self, directory_fd):
        try:
            return self._pinned_stat(directory_fd)[0] in ('Z', 'X', 'x')
        except PROC_DISAPPEARED:
            return True

    def _pinned_process(self, process_fd, namespace, pid_namespace):
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
        try:
            task_fd = os.open('task', directory_flags, dir_fd=process_fd)
        except PROC_DISAPPEARED:
            if self._pinned_terminated(process_fd):
                return
            raise
        try:
            try:tasks = os.listdir(task_fd)
            except PROC_DISAPPEARED:
                if self._pinned_terminated(process_fd):
                    return
                raise
            for name in tasks:
                if not name.isdecimal():
                    raise ValueError('Invalid process task identity')
                try:thread_fd = os.open(name, directory_flags, dir_fd=task_fd)
                except PROC_DISAPPEARED:continue
                try:
                    try:
                        # PF_KTHREAD (include/linux/sched.h): kernel tasks have
                        # no userspace mount namespace.
                        fields = self._pinned_stat(thread_fd)
                        if fields[0] in ('Z', 'X', 'x') or int(fields[6]) & 0x00200000:
                            continue
                        mount_namespace = os.readlink('ns/mnt', dir_fd=thread_fd)
                        task_pid_namespace = os.readlink('ns/pid', dir_fd=thread_fd)
                    except PROC_DISAPPEARED:
                        if self._pinned_terminated(thread_fd):
                            continue
                        raise
                    require(mount_namespace == namespace and task_pid_namespace == pid_namespace,
                            'Unexpected process namespace; source-writer assumptions unverified')
                finally:
                    os.close(thread_fd)
        finally:
            os.close(task_fd)

    def _namespace_census(self, namespace, pid_namespace, proc='/proc'):
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
        proc_fd = os.open(proc, directory_flags)
        try:
            for name in os.listdir(proc_fd):
                if not name.isdecimal():
                    continue
                try:process_fd = os.open(name, directory_flags, dir_fd=proc_fd)
                except PROC_DISAPPEARED:continue
                try:self._pinned_process(process_fd, namespace, pid_namespace)
                finally:os.close(process_fd)
        finally:
            os.close(proc_fd)

    def session(self):
        require(os.geteuid() == 0, 'Recovery admission requires root')
        namespace = os.readlink('/proc/self/ns/mnt')
        pid_namespace = os.readlink('/proc/self/ns/pid')
        require(namespace == os.readlink('/proc/1/ns/mnt') and
                pid_namespace == os.readlink('/proc/1/ns/pid'),
                'Recovery must share PID 1 mount and PID namespaces')
        root = os.stat('/')
        init_root = os.stat('/proc/1/root')
        require((root.st_dev, root.st_ino) == (init_root.st_dev, init_root.st_ino),
                'Recovery process root differs from PID 1')
        # No hidepid/proc subset, unreadable tasks or other mount namespaces are
        # supported. Block RO below prevents ordinary filesystem/raw writers;
        # reviewed userspace must prohibit uncoordinated RO-flag/namespace changes.
        self._namespace_census(namespace, pid_namespace)
        return dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    mount_namespace=namespace, pid_namespace=pid_namespace,
                    process_root=[root.st_dev, root.st_ino])

    def block(self, mount, fixture=None):
        """Simple physical disks/partitions only; resolve only selected mounts."""
        device = mount['device']
        require(re.fullmatch(r'[1-9][0-9]*:[0-9]+', device), 'Unsupported non-block filesystem')
        node = (Path('/sys/dev/block') / device).resolve(strict=True)
        require(node.is_relative_to('/sys/devices') and (node / 'dev').read_text().strip() == device,
                'Unresolved block topology')
        partition = (node / 'partition').exists()
        disk = node.parent if partition else node
        require(not (disk / 'partition').exists(), 'Unsupported nested block topology')
        for item in {node, disk}:
            require(not list((item / 'slaves').iterdir()) if (item / 'slaves').exists() else True,
                    'Unsupported stacked storage')
            require(not list((item / 'holders').iterdir()), 'Block device has an unexpected holder')
        virtual = node.is_relative_to('/sys/devices/virtual')
        if virtual:
            require(fixture is not None and node == disk and (disk / 'loop').is_dir(),
                    'Unsupported virtual/stacked storage')
            backing = (disk / 'loop/backing_file').read_text().strip()
            require(backing in fixture['images'], 'Loop is not an explicitly identified disposable medium')
            info = os.stat(backing, follow_symlinks=False)
            require(stat.S_ISREG(info.st_mode) and [info.st_dev, info.st_ino, info.st_size] ==
                    fixture['images'][backing], 'Disposable loop backing identity changed')
            require((disk / 'loop/offset').read_text().strip() == '0' and
                    (disk / 'loop/sizelimit').read_text().strip() == '0', 'Unsupported loop mapping')
            stable = dict(disposable_backing=backing, identity=fixture['images'][backing])
        else:
            stable = {}
            for name in ('wwid', 'device/wwid', 'device/cid', 'device/serial', 'serial'):
                file = disk / name
                if file.is_file() and file.read_text().strip():
                    stable[name] = file.read_text().strip()
            require(bool(stable), 'Stable physical medium identity is unavailable')
        sequence = int((disk / 'diskseq').read_text())
        require(sequence > 0, 'Kernel disk sequence is unavailable')
        uevent = dict(line.split('=', 1) for line in (node / 'uevent').read_text().splitlines())
        name = uevent['DEVNAME']
        require('/' not in name and re.fullmatch(r'[a-zA-Z0-9_-]+', name), 'Unsupported device node')
        path = Path('/dev') / name
        info = os.stat(path, follow_symlinks=False)
        require(stat.S_ISBLK(info.st_mode) and f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}' == device,
                'Mounted block node identity changed')
        # Low-level probe reads only this already identified node, never a label
        # cache or a scan of other devices. Ambivalent probe results fail closed.
        probe = subprocess.run(['/usr/sbin/blkid', '-p', '-o', 'export', str(path)],
                               check=True, capture_output=True, text=True, timeout=5)
        filesystem = dict(line.split('=', 1) for line in probe.stdout.splitlines() if '=' in line)
        require(filesystem.get('TYPE') == mount['filesystem'] and bool(filesystem.get('UUID')),
                'Mounted filesystem identity could not be verified')
        def flag(path):
            value = path.read_text().strip()
            require(value in ('0', '1'), 'Unknown kernel block property: '+path.name)
            return value == '1'
        return dict(device=device, sysfs=str(node), sysfs_inode=node.stat().st_ino,
                    disk=str(disk), disk_device=(disk / 'dev').read_text().strip(),
                    diskseq=sequence, stable=stable, partition=int((node / 'partition').read_text()) if partition else 0,
                    start=int((node / 'start').read_text()) if partition else 0,
                    sectors=int((node / 'size').read_text()),
                    readonly=flag(node / 'ro'), disk_readonly=flag(disk / 'ro'),
                    removable=flag(disk / 'removable'),
                    filesystem_uuid=filesystem['UUID'], filesystem=filesystem['TYPE'],
                    partuuid=filesystem.get('PART_ENTRY_UUID', ''))

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

    def _identity(self, sysfs):
        require(sysfs.is_relative_to('/sys/devices'), 'Unresolved block topology')
        topology_value = {}
        for topology in ('holders', 'slaves'):
            directory = sysfs / topology
            topology_value[topology] = (sorted(item.name for item in directory.iterdir())
                                        if directory.exists() else [])
            require(not topology_value[topology],
                    'Block device has an unexpected '+topology[:-1])
        device = (sysfs / 'dev').read_text().strip()
        uevent = dict(line.split('=', 1) for line in (sysfs / 'uevent').read_text().splitlines())
        name = uevent['DEVNAME']
        require(re.fullmatch(r'[A-Za-z0-9_-]+', name) is not None, 'Unsupported block device name')
        path = Path('/dev') / name
        info = os.stat(path, follow_symlinks=False)
        require(stat.S_ISBLK(info.st_mode) and
                f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}' == device,
                'Block device node identity changed')
        probe = self._probe(path)
        partition = int((sysfs / 'partition').read_text()) if (sysfs / 'partition').exists() else 0
        disk = sysfs.parent if partition else sysfs
        sequence = int((disk / 'diskseq').read_text())
        require(sequence > 0, 'Kernel disk sequence is unavailable')
        return dict(node=str(path), device=device, sysfs=str(sysfs),
                    sysfs_inode=sysfs.stat().st_ino,
                    disk=str(disk), disk_device=(disk / 'dev').read_text().strip(),
                    diskseq=sequence, partition=partition,
                    start=int((sysfs / 'start').read_text()) if partition else 0,
                    sectors=int((sysfs / 'size').read_text()), readonly=self._flag(sysfs / 'ro'),
                    disk_readonly=self._flag(disk / 'ro'), removable=self._flag(disk / 'removable'),
                    filesystem_uuid=probe.get('UUID', ''), filesystem=probe.get('TYPE', ''),
                    partuuid=probe.get('PART_ENTRY_UUID', ''), **topology_value)

    def inventory(self):
        result = []
        links = list(Path('/sys/class/block').iterdir())
        for link in sorted(links):
            disk = link.resolve(strict=True)
            if (disk / 'partition').exists() or disk.name.startswith(('loop', 'ram', 'zram')):
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
                if item.is_file():
                    value = item.read_text().strip()
                    if value:
                        stable[name] = value
            require(stable, 'Stable medium identity is unavailable: '+disk.name)
            children = sorted((link.resolve() for link in links
                               if (link.resolve().parent == disk and
                                   (link.resolve() / 'partition').exists())),
                              key=lambda child: int((child / 'partition').read_text()))
            require(len(children) <= 16, 'Recovery medium has too many partitions')
            whole = self._identity(disk)
            result.append(dict(**whole, name=disk.name, stable=stable, transport=transport,
                               partitions=[self._identity(child) for child in children]))
        require(1 <= len(result) <= 8, 'Recovery requires a bounded complete media inventory')
        require(sum(1 + len(disk['partitions']) for disk in result) <= 64,
                'Recovery media topology is too large')
        return result

    def active_loops(self):
        result = []
        for link in sorted(Path('/sys/class/block').iterdir()):
            node = link.resolve(strict=True)
            if not node.name.startswith('loop') or not (node / 'loop/backing_file').is_file():
                continue
            require(node.is_relative_to('/sys/devices/virtual/block'),
                    'Unsupported active loop topology')
            backing = (node / 'loop/backing_file').read_text().strip()
            if not backing:
                continue
            device = (node/'dev').read_text().strip()
            uevent = dict(line.split('=', 1) for line in (node/'uevent').read_text().splitlines())
            name = uevent['DEVNAME']
            require(re.fullmatch(r'loop[0-9]+', name) is not None,
                    'Unsupported active loop device name')
            device_path = Path('/dev')/name
            device_info = os.stat(device_path, follow_symlinks=False)
            require(stat.S_ISBLK(device_info.st_mode) and
                    f'{os.major(device_info.st_rdev)}:{os.minor(device_info.st_rdev)}' == device,
                    'Active loop device node identity changed')
            sequence = int((node/'diskseq').read_text())
            require(sequence > 0, 'Active loop disk sequence is unavailable')
            info = os.stat(backing, follow_symlinks=False)
            result.append(dict(node=str(device_path), device=device, sysfs=str(node),
                               sysfs_inode=node.stat().st_ino,
                               diskseq=sequence, backing=backing,
                               backing_identity=[info.st_dev, info.st_ino, info.st_size],
                               backing_mode=info.st_mode, backing_uid=info.st_uid,
                               backing_gid=info.st_gid, backing_nlink=info.st_nlink,
                               readonly=self._flag(node/'ro'),
                               offset=int((node/'loop/offset').read_text()),
                               sizelimit=int((node/'loop/sizelimit').read_text()),
                               sectors=int((node/'size').read_text()),
                               holders=sorted(item.name for item in (node/'holders').iterdir()),
                               slaves=sorted(item.name for item in (node/'slaves').iterdir())))
        return result


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


def validate_usr_loop_inventory(loops):
    require(type(loops) is list and len(loops) == 1,
            'Exactly one active compressed-userspace loop is required')
    loop = loops[0]
    size = loop['backing_identity'][2]
    require(loop['backing'] == '/usr.squashfs' and
            stat.S_ISREG(loop['backing_mode']) and loop['backing_uid'] == loop['backing_gid'] == 0 and
            loop['backing_nlink'] == 1 and loop['readonly'] and loop['offset'] == 0 and
            loop['sizelimit'] in (0, size) and not loop['holders'] and not loop['slaves'] and
            size <= loop['sectors'] * 512 < size + 512,
            'Active compressed-userspace loop identity or extent changed')
    return loop


def durable_identity(block):
    return {name: block[name] for name in ('stable', 'partition', 'start', 'sectors', 'filesystem_uuid')}


def same_identity(left, right):
    # Keep every value: two differently named attributes may normalize to the
    # same key, and either value can identify a protected system medium.
    return any(left_key.removeprefix('device/') == right_key.removeprefix('device/') and
               left_value == right_value
               for left_key, left_value in left.items()
               for right_key, right_value in right.items())


def strict_envelope_manifest(data):
    """Parse the fixed early-boot manifest without shell or JSON ambiguity."""
    try:
        text = data.decode('ascii')
    except (AttributeError, UnicodeDecodeError):
        raise ValueError('Invalid recovery envelope manifest encoding') from None
    lines = text.splitlines()
    require(len(lines) == 6 and text.endswith('\n'), 'Invalid recovery envelope manifest schema')
    pairs = []
    for line in lines:
        require(line.count('=') == 1, 'Invalid recovery envelope manifest schema')
        pairs.append(line.split('=', 1))
    require([key for key, _ in pairs] ==
            ['format', 'root_uuid', 'root_bytes', 'usr_path', 'usr_bytes', 'usr_sha256'],
            'Invalid recovery envelope manifest schema')
    value = dict(pairs)
    require(value['format'] == 'sv08-recovery-usr-v1' and value['usr_path'] == '/usr.squashfs' and
            value['root_bytes'].isdigit() and int(value['root_bytes']) > 0 and
            value['usr_bytes'].isdigit() and int(value['usr_bytes']) > 0 and
            re.fullmatch(r'[0-9a-f]{64}', value['usr_sha256']) is not None,
            'Invalid recovery envelope manifest values')
    value['root_bytes'] = int(value['root_bytes'])
    value['usr_bytes'] = int(value['usr_bytes'])
    return value


class MediaProvider(ExportAdapter):
    """No production fixtures, guessed identities or implicit trust inputs."""
    def __init__(self, policy, context, *, fixture=None, policy_sha256=None):
        self.policy, self.context, self.fixture = policy, context, fixture
        self.policy_sha256 = policy_sha256 or hashlib.sha256(canonical_json(policy)).hexdigest()
        self.kernel = Kernel()
        require(type(policy) is dict and type(context) is dict, 'Invalid recovery configuration objects')
        require(type(policy['format_version']) is int and type(context['format_version']) is int and
                policy['format_version'] == context['format_version'] and policy['format_version'] in (1, 2) and
                policy['protocol'] == context['protocol'] == PROTOCOL and
                policy['writer_model'] == WRITER_MODEL and
                context['policy_sha256'] == fingerprint(policy), 'Invalid recovery preparation contract')
        require(policy['kind'] == ('disposable-recovery-fixture' if fixture else 'independent-recovery'),
                'This is not an approved independent recovery context')
        if policy['format_version'] == 2:
            require(set(policy) == {'format_version', 'kind', 'protocol', 'writer_model',
                    'envelope_manifest_sha256', 'recovery',
                    'source', 'source_path', 'media', 'protected', 'destinations'} and
                    set(context) in ({'format_version', 'protocol', 'policy_sha256', 'source',
                                      'destinations'},
                                     {'format_version', 'protocol', 'policy_sha256', 'source',
                                      'destinations', 'expected'}),
                    'Invalid composed recovery policy/context schema')
        if policy['format_version'] == 1:
            system_media = policy['system_media']
        else:
            system_media = [policy['recovery']['stable'], policy['source']['stable'],
                            *[value['identity']['stable'] for value in policy['protected']]]
            system_media = [value for index, value in enumerate(system_media)
                            if value not in system_media[:index]]
            destination_media = [value['identity']['stable']
                                 for value in policy['destinations'].values()]
            require(all(not any(same_identity(destination, protected)
                                for protected in system_media)
                        for destination in destination_media) and
                    all(not same_identity(left, right)
                        for index, left in enumerate(destination_media)
                        for right in destination_media[index+1:]),
                    'Destination whole disk aliases protected or another destination media')
        require(type(system_media) is list and 1 <= len(system_media) <= 8 and
                all(type(medium) is dict and medium for medium in system_media),
                'An independently reviewed inventory of all system media is required')
        self.system_media = system_media
        self.root = clean_path(fixture['root']) if fixture else Path('/')
        self.lock = clean_path(fixture['lock']) if fixture else LOCK
        if fixture:
            base = clean_path(fixture['base'])
            repository = Path(__file__).resolve().parents[1]
            require(base.is_relative_to(repository / 'build') and self.root == base / 'recovery' and
                    self.lock == base / 'run/media.lock' and
                    json.loads((base / 'disposable-recovery-fixture.json').read_text()) == fixture and
                    all(clean_path(p).parent == base for p in fixture['images']),
                    'Use an explicitly marked disposable build fixture')
        self.source = clean_path(context['source'])
        require(type(context['destinations']) is dict and bool(context['destinations']) and len(context['destinations']) <= 8,
                'No bounded pre-mounted destinations are configured')
        targets = {}
        for key, value in context['destinations'].items():
            require(type(value) is dict and re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', key) and
                    isinstance(value['label'], str) and 0 < len(value['label']) <= 120 and
                    all(ord(c) >= 32 for c in value['label']), 'Invalid destination selection')
            targets[key] = dict(path=clean_path(value['path']), label=value['label'])
        require(len({v['path'] for v in targets.values()}) == len(targets), 'Duplicate destinations')
        if policy['format_version'] == 2:
            reviewed_targets = {key: dict(path=clean_path(value['path']), label=value['label'])
                                for key, value in policy['destinations'].items()}
            require(self.source == clean_path(policy['source_path']) and targets == reviewed_targets,
                    'Per-boot context differs from immutable source/destination policy')
        super().__init__(Export(self.source, targets, self.admission))

    def complete_inventory(self):
        if self.policy['format_version'] == 1:
            return None
        observed = self.kernel.inventory()
        require(reviewed_inventory(observed) == self.policy['media'],
                'Observed media topology differs from immutable reviewed policy')
        stable = [disk['stable'] for disk in observed]
        require(all(not same_identity(left, right) for index, left in enumerate(stable)
                    for right in stable[index+1:]),
                'Duplicate or aliased stable media identities')
        loops = self.kernel.active_loops()
        validate_usr_loop_inventory(loops)
        return dict(media=observed, active_loops=loops)

    def snapshot(self):
        complete_inventory = self.complete_inventory()
        active_usr_loop = (complete_inventory['active_loops'][0]
                           if complete_inventory is not None else None)
        mounts = self.kernel.mounts()
        require(not any(m['optional'] for m in mounts), 'Recovery mounts must be private and unambiguous')
        proc = [m for m in mounts if m['path'] == '/proc']
        require(len(proc) == 1 and proc[0]['filesystem'] == 'proc' and proc[0]['root'] == '/' and
                not any(o.startswith(('hidepid=', 'subset=')) for o in proc[0]['super_options']),
                'Complete process namespace visibility is required')
        require(any(m['path'] == '/sys' and m['filesystem'] == 'sysfs' and m['root'] == '/'
                    for m in mounts), 'Kernel sysfs block topology is unavailable')
        session = self.kernel.session()

        def bind_complete_inventory(block):
            if complete_inventory is None:
                return
            matches = []
            for disk in complete_inventory['media']:
                for item in [disk, *disk['partitions']]:
                    if item['device'] == block['device']:
                        matches.append((disk, item))
            require(len(matches) == 1, 'Selected block is absent or ambiguous in complete inventory')
            disk, item = matches[0]
            observed = dict(device=item['device'], sysfs=item['sysfs'],
                            sysfs_inode=item['sysfs_inode'], disk=item['disk'],
                            disk_device=item['disk_device'], diskseq=item['diskseq'],
                            stable=disk['stable'], partition=item['partition'], start=item['start'],
                            sectors=item['sectors'], readonly=item['readonly'],
                            disk_readonly=item['disk_readonly'], removable=item['removable'],
                            filesystem_uuid=item['filesystem_uuid'], filesystem=item['filesystem'],
                            partuuid=item['partuuid'])
            require(observed == {name:block[name] for name in observed},
                    'Selected block differs from complete inventory observation')

        def selected(path, role):
            match = [m for m in mounts if m['path'] == str(path)]
            require(len(match) == 1, role+' must be an exact, present mountpoint')
            mount = match[0]
            require(mount['root'] == '/', role+' cannot be a bind subtree')
            require(sum(m['device'] == mount['device'] for m in mounts) == 1,
                    role+' has an unexpected filesystem alias')
            if role != 'Recovery root':
                require(not any(Path(m['path']).is_relative_to(path) and m != mount for m in mounts),
                        role+' has an unexpected submount')
            readonly = role != 'Destination'
            expected = 'ro' if readonly else 'rw'
            require(expected in mount['options'] and expected in mount['super_options'] and
                    ('rw' if readonly else 'ro') not in mount['options']+mount['super_options'],
                    role+' requires consistent '+expected+' mount and filesystem-superblock state')
            require(mount['filesystem'] == ('ext4' if readonly else 'vfat'),
                    role+' uses an unsupported filesystem')
            with opened(path) as fd:
                info, fs = os.fstat(fd), os.fstatvfs(fd)
            require(f'{os.major(info.st_dev)}:{os.minor(info.st_dev)}' == mount['device'] and
                    bool(fs.f_flag & os.ST_RDONLY) == readonly, role+' mount identity/options changed')
            block = self.kernel.block(mount, self.fixture)
            bind_complete_inventory(block)
            if readonly:
                require(block['readonly'] and block['disk_readonly'],
                        role+' requires premounted read-only partition AND whole medium')
                require('norecovery' in mount['super_options'] or 'noload' in mount['super_options'],
                        role+' must be prepared without ext4 journal replay')
            else:
                require(not block['readonly'] and not block['disk_readonly'], 'Destination block device is read-only')
                require(block['removable'] or (self.fixture is not None and
                        'disposable_backing' in block['stable']), 'Destination is not a removable medium')
            return dict(mount=mount, directory=[info.st_dev, info.st_ino], block=block)

        recovery = selected(self.root, 'Recovery root')
        source = selected(self.source, 'Source')
        require(durable_identity(recovery['block']) == self.policy['recovery'] and
                durable_identity(source['block']) == self.policy['source'],
                'Running recovery or source does not match independently reviewed identities')
        require(all(item['block']['stable'] in self.system_media for item in (recovery, source)),
                'Reviewed system media inventory omits recovery or source')
        manifest = self.root / PROVIDER_MANIFEST.relative_to('/')
        with opened(manifest, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as fd:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_dev == recovery['directory'][0] and
                    info.st_size <= 1024*1024, 'Recovery image manifest is outside its reviewed root')
            with os.fdopen(os.dup(fd), 'rb') as stream:
                manifest_data = stream.read(1024*1024+1)
                digest = hashlib.sha256(manifest_data).hexdigest()
        if self.policy['format_version'] == 1:
            require(digest == self.policy['image_manifest_sha256'],
                    'Recovery image manifest does not match review')
        else:
            try:
                provider_manifest = json.loads(manifest_data)
            except (OSError, ValueError, TypeError):
                raise ValueError('Invalid recovery provider manifest') from None
            require(manifest_data == canonical_json(provider_manifest) and
                    set(provider_manifest) == {'format_version', 'kind', 'protocol',
                    'policy_sha256', 'inputs'} and provider_manifest['format_version'] == 2 and
                    provider_manifest['kind'] == 'sv08-independent-recovery-provider' and
                    provider_manifest['protocol'] == PROTOCOL and
                    type(provider_manifest['inputs']) is dict and provider_manifest['inputs'] and
                    provider_manifest['policy_sha256'] == self.policy_sha256,
                    'Recovery provider manifest does not bind the reviewed policy')
        if not self.fixture:
            args = Path('/proc/cmdline').read_text().split()
            require([a for a in args if a.startswith('sv08.recovery=')] == ['sv08.recovery='+digest],
                    'Kernel boot selection does not identify the reviewed recovery image')
            with opened(POLICY, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as fd:
                require(os.fstat(fd).st_dev == recovery['directory'][0], 'Recovery policy is outside the immutable recovery root')
        compressed = None
        if self.policy['format_version'] == 2:
            envelope_path = self.root / ENVELOPE_MANIFEST.relative_to('/')
            envelope_data = trusted_file(envelope_path)
            envelope_digest = hashlib.sha256(envelope_data).hexdigest()
            require(envelope_digest == self.policy['envelope_manifest_sha256'],
                    'Recovery envelope manifest does not match review')
            args = Path('/proc/cmdline').read_text().split()
            require([a for a in args if a.startswith('sv08.envelope=')] ==
                    ['sv08.envelope='+envelope_digest],
                    'Kernel boot selection does not identify the reviewed recovery envelope')
            envelope = strict_envelope_manifest(envelope_data)
            require(envelope['root_uuid'] == recovery['block']['filesystem_uuid'] and
                    envelope['root_bytes'] == recovery['block']['sectors'] * 512,
                    'Recovery envelope root identity differs from the mounted root')
            compressed = self.compressed_userspace(mounts, recovery, envelope)
            require(active_usr_loop['device'] == compressed['loop_device'] and
                    active_usr_loop['sysfs'] == compressed['loop_sysfs'] and
                    active_usr_loop['sysfs_inode'] == compressed['loop_sysfs_inode'] and
                    active_usr_loop['backing_identity'] == compressed['backing'],
                    'Active compressed-userspace loop differs from the /usr mount')
        destinations = {key: selected(value['path'], 'Destination') for key, value in self.exporter.targets.items()}
        if not self.fixture:
            selected_paths = {'/', str(self.source), *(str(v['path']) for v in self.exporter.targets.values())}
            if compressed is not None:
                selected_paths.add('/usr')
            require(all(admitted_system_mount(m, selected_paths) for m in mounts),
                    'Unexpected recovery system mount; independent userspace is unverified')
        protected = {recovery['block']['disk'], source['block']['disk']}
        require(len({d['block']['disk'] for d in destinations.values()}) == len(destinations),
                'Destination aliases another destination medium')
        require(all(d['block']['disk'] not in protected and
                    not any(same_identity(d['block']['stable'], medium) for medium in self.system_media)
                    for d in destinations.values()), 'Destination shares a system/source medium')
        # Bind every mount, including expected system mounts, so topology changes
        # outside the chosen directory also invalidate the reviewed operation.
        result = dict(session=session, mounts=fingerprint(mounts), recovery=recovery,
                      source=source, destinations=destinations)
        if compressed is not None:
            result['compressed_userspace'] = compressed
            result['complete_inventory'] = complete_inventory
        return result

    def compressed_userspace(self, mounts, recovery, envelope):
        """Admit only the independently reviewed ext4/file/loop/SquashFS chain."""
        backing = self.root / envelope['usr_path'].removeprefix('/')
        with opened(backing, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as fd:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == info.st_gid == 0 and
                    info.st_nlink == 1 and info.st_dev == recovery['directory'][0] and
                    info.st_size == envelope['usr_bytes'],
                    'Compressed userspace backing identity changed')
            with os.fdopen(os.dup(fd), 'rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        require(digest == envelope['usr_sha256'], 'Compressed userspace digest changed')
        matches = [m for m in mounts if m['path'] == '/usr']
        require(len(matches) == 1, 'Compressed userspace must be an exact mountpoint')
        mount = matches[0]
        require(mount['root'] == '/' and mount['filesystem'] == 'squashfs' and
                'ro' in mount['options'] and 'ro' in mount['super_options'] and
                'rw' not in mount['options'] + mount['super_options'] and
                not any(Path(m['path']).is_relative_to('/usr') and m != mount for m in mounts),
                'Compressed userspace mount identity/options changed')
        require(sum(m['device'] == mount['device'] for m in mounts) == 1,
                'Compressed userspace has an unexpected mount alias')
        node = (Path('/sys/dev/block') / mount['device']).resolve(strict=True)
        require(node.is_relative_to('/sys/devices/virtual/block') and node.name.startswith('loop') and
                (node / 'loop').is_dir() and (node / 'ro').read_text().strip() == '1',
                'Compressed userspace requires a read-only loop')
        require(not list((node / 'holders').iterdir()) and not list((node / 'slaves').iterdir()),
                'Compressed userspace loop has unexpected topology')
        loop = node / 'loop'
        require((loop / 'offset').read_text().strip() == '0', 'Compressed userspace loop offset changed')
        limit = int((loop / 'sizelimit').read_text().strip())
        require(limit in (0, info.st_size), 'Compressed userspace loop extent changed')
        sectors = int((node / 'size').read_text().strip())
        require(info.st_size <= sectors * 512 < info.st_size + 512,
                'Compressed userspace loop exceeds its immutable backing file')
        kernel_backing = (loop / 'backing_file').read_text().strip()
        require(kernel_backing == '/usr.squashfs', 'Compressed userspace loop backing path changed')
        backing_info = os.stat(kernel_backing, follow_symlinks=False)
        require((backing_info.st_dev, backing_info.st_ino, backing_info.st_size) ==
                (info.st_dev, info.st_ino, info.st_size),
                'Compressed userspace loop backing inode changed')
        return dict(mount=mount, backing=[info.st_dev, info.st_ino, info.st_size],
                    sha256=digest, loop_device=mount['device'], loop_sysfs=str(node),
                    loop_sysfs_inode=node.stat().st_ino, offset=0, sizelimit=limit,
                    sectors=sectors)

    @contextmanager
    def admission(self, destination):
        require(destination in self.exporter.targets, 'Choose a configured removable destination')
        with MediaLease(self.lock) as lease:
            initial = self.snapshot()
            require(initial == self.context['expected'], 'Recovery context or media changed; prepare and review again')
            provider = self
            class Guard:
                fingerprint = fingerprint(initial)
                def recheck(self):
                    lease.check()
                    require(provider.snapshot() == initial, 'Recovery mount or medium changed during export')
            yield Guard()

    def capability(self, action, view):
        if action != 'recovery.export':
            return False, 'No verified backend is available for this operation.'
        try:
            with self.admission(next(iter(self.exporter.targets))):
                pass
            return True, ''
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            return False, 'User-data export unavailable: '+str(error)


class Unavailable:
    def __init__(self, reason): self.reason = reason
    def images(self): return []
    def destinations(self): return []
    def capability(self, action, view): return False, self.reason


def production_adapter():
    """Fixed installed trust paths; no CLI/env override enables fixture media."""
    try:
        policy_data, context_data = trusted_file(POLICY), trusted_file(CONTEXT)
        policy, context = json.loads(policy_data), json.loads(context_data)
        require(policy_data == canonical_json(policy), 'Recovery policy is not canonical reviewed input')
        provider = MediaProvider(policy, context, policy_sha256=hashlib.sha256(policy_data).hexdigest())
        with provider.admission(next(iter(provider.exporter.targets))):
            pass
        return provider
    except KeyError as error:
        return Unavailable('User-data export unavailable: recovery configuration is missing required field '+str(error))
    except (OSError, ValueError, TypeError, StopIteration, subprocess.SubprocessError) as error:
        return Unavailable('User-data export unavailable: '+str(error))
