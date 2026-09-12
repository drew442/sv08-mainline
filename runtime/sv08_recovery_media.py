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
WRITER_MODEL = 'reviewed-recovery-only; all-media-mutators-use-MediaLease'


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


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
        for process in Path('/proc').iterdir():
            if process.name.isdecimal():
                for task in (process / 'task').iterdir():
                    # PF_KTHREAD (include/linux/sched.h): kernel tasks have no
                    # userspace mount namespace. Do not excuse missing userspace
                    # task information or infer this from a display name.
                    fields = (task / 'stat').read_text().rsplit(')', 1)[1].split()
                    if int(fields[6]) & 0x00200000:
                        continue
                    require(os.readlink(task / 'ns/mnt') == namespace and
                            os.readlink(task / 'ns/pid') == pid_namespace,
                            'Unexpected process namespace; source-writer assumptions unverified')
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
            for name in ('wwid', 'device/wwid', 'device/cid', 'device/serial'):
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
                    filesystem_uuid=filesystem['UUID'])


def durable_identity(block):
    return {name: block[name] for name in ('stable', 'partition', 'start', 'sectors', 'filesystem_uuid')}


def same_identity(left, right):
    # Keep every value: two differently named attributes may normalize to the
    # same key, and either value can identify a protected system medium.
    return any(left_key.removeprefix('device/') == right_key.removeprefix('device/') and
               left_value == right_value
               for left_key, left_value in left.items()
               for right_key, right_value in right.items())


class MediaProvider(ExportAdapter):
    """No production fixtures, guessed identities or implicit trust inputs."""
    def __init__(self, policy, context, *, fixture=None):
        self.policy, self.context, self.fixture = policy, context, fixture
        self.kernel = Kernel()
        require(type(policy) is dict and type(context) is dict, 'Invalid recovery configuration objects')
        require(type(policy['format_version']) is int and type(context['format_version']) is int and
                policy['format_version'] == context['format_version'] == 1 and
                policy['protocol'] == context['protocol'] == PROTOCOL and
                policy['writer_model'] == WRITER_MODEL and
                context['policy_sha256'] == fingerprint(policy), 'Invalid recovery preparation contract')
        require(policy['kind'] == ('disposable-recovery-fixture' if fixture else 'independent-recovery'),
                'This is not an approved independent recovery context')
        require(type(policy['system_media']) is list and 1 <= len(policy['system_media']) <= 8 and
                all(type(medium) is dict and medium for medium in policy['system_media']),
                'An independently reviewed inventory of all system media is required')
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
        super().__init__(Export(self.source, targets, self.admission))

    def snapshot(self):
        mounts = self.kernel.mounts()
        require(not any(m['optional'] for m in mounts), 'Recovery mounts must be private and unambiguous')
        proc = [m for m in mounts if m['path'] == '/proc']
        require(len(proc) == 1 and proc[0]['filesystem'] == 'proc' and proc[0]['root'] == '/' and
                not any(o.startswith(('hidepid=', 'subset=')) for o in proc[0]['super_options']),
                'Complete process namespace visibility is required')
        require(any(m['path'] == '/sys' and m['filesystem'] == 'sysfs' and m['root'] == '/'
                    for m in mounts), 'Kernel sysfs block topology is unavailable')
        session = self.kernel.session()

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
        require(all(item['block']['stable'] in self.policy['system_media'] for item in (recovery, source)),
                'Reviewed system media inventory omits recovery or source')
        manifest = self.root / 'etc/sv08/recovery-image.json'
        with opened(manifest, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as fd:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_dev == recovery['directory'][0] and
                    info.st_size <= 1024*1024, 'Recovery image manifest is outside its reviewed root')
            with os.fdopen(os.dup(fd), 'rb') as stream:
                digest = hashlib.sha256(stream.read(1024*1024+1)).hexdigest()
        require(digest == self.policy['image_manifest_sha256'], 'Recovery image manifest does not match review')
        if not self.fixture:
            args = Path('/proc/cmdline').read_text().split()
            require([a for a in args if a.startswith('sv08.recovery=')] == ['sv08.recovery='+digest],
                    'Kernel boot selection does not identify the reviewed recovery image')
            with opened(POLICY, flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as fd:
                require(os.fstat(fd).st_dev == recovery['directory'][0], 'Recovery policy is outside the immutable recovery root')
        destinations = {key: selected(value['path'], 'Destination') for key, value in self.exporter.targets.items()}
        if not self.fixture:
            selected_paths = {'/', str(self.source), *(str(v['path']) for v in self.exporter.targets.values())}
            kernel_filesystems = {'proc', 'sysfs', 'devtmpfs', 'tmpfs', 'devpts', 'cgroup2'}
            require(all(m['path'] in selected_paths or (m['filesystem'] in kernel_filesystems and
                        any(Path(m['path']).is_relative_to(base) for base in ('/proc', '/sys', '/dev', '/run', '/tmp')))
                        for m in mounts), 'Unexpected recovery system mount; independent userspace is unverified')
        protected = {recovery['block']['disk'], source['block']['disk']}
        require(len({d['block']['disk'] for d in destinations.values()}) == len(destinations),
                'Destination aliases another destination medium')
        require(all(d['block']['disk'] not in protected and
                    not any(same_identity(d['block']['stable'], medium) for medium in self.policy['system_media'])
                    for d in destinations.values()), 'Destination shares a system/source medium')
        # Bind every mount, including expected system mounts, so topology changes
        # outside the chosen directory also invalidate the reviewed operation.
        return dict(session=session, mounts=fingerprint(mounts), recovery=recovery,
                    source=source, destinations=destinations)

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
        policy, context = json.loads(trusted_file(POLICY)), json.loads(trusted_file(CONTEXT))
        provider = MediaProvider(policy, context)
        with provider.admission(next(iter(provider.exporter.targets))):
            pass
        return provider
    except KeyError as error:
        return Unavailable('User-data export unavailable: recovery configuration is missing required field '+str(error))
    except (OSError, ValueError, TypeError, StopIteration, subprocess.SubprocessError) as error:
        return Unavailable('User-data export unavailable: '+str(error))
