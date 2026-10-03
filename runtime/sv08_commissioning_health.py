#!/usr/bin/python3
"""Opt-in initial diagnostic A confirmation; never printer readiness.

Gap: upstream mark-good has no initial-generation eligibility check. Retire this
oneshot when production composition replaces the diagnostic baseline. The only
mutation is selected libubootenv's one BOOT_A_LEFT write (see software-contract).
"""
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time
import uuid
import zlib

from sv08_state import Store, atomic_json
from sv08_boot import slot_from_cmdline, device_number
from sv08_boot_health import boot_admission
from sv08_rauc_service import Service
from sv08_rauc_bootloader import verify_environment_copies
from sv08_gpt import inspect

MASKS = ('sv08-klipper', 'sv08-moonraker', 'klipper', 'moonraker',
         'KlipperScreen', 'rauc', 'sv08-boot-health')
REGIONS = ((0x400000, 0x10000), (0x800000, 0x10000))
RECORD_LIMIT = 64 * 1024
RETAINED_LIMIT = 1024 * 1024
CONFIG_FIELDS = {'format_version', 'release', 'generation', 'disk', 'fw_config_sha256',
                 'tools', 'dependencies'}
DISK_FIELDS = {'path', 'major_minor', 'sysfs', 'physical_bytes', 'image_bytes', 'disk_guid', 'partition_records'}
TOOL_FIELDS = {'package', 'version', 'files'}
SELECTED_TOOL_SHA256 = '29d6d7b52afa4144a7f40bb9ca852c8058c0b68388904983ab076ac53d467ea0'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > RECORD_LIMIT:
        raise ValueError('Missing, linked or oversized input: ' + str(path))
    return json.loads(path.read_text())


def present(path):
    return Path(path).exists() or Path(path).is_symlink()


def disk_guid(path):
    """Read identity without extending the installed historical GPT API.

    Call only after inspect has validated both headers/arrays and reservations.
    Recheck this header's CRC because identity is read separately from inspect.
    """
    with Path(path).open('rb') as stream:
        stream.seek(512)
        header = bytearray(stream.read(512))
    if len(header) != 512 or header[:8] != b'EFI PART':
        raise ValueError('Missing GPT identity header')
    length = int.from_bytes(header[12:16], 'little')
    crc = int.from_bytes(header[16:20], 'little')
    header[16:20] = bytes(4)
    if not 92 <= length <= 512 or zlib.crc32(header[:length]) != crc:
        raise ValueError('GPT identity header CRC/length differs')
    return str(uuid.UUID(bytes_le=bytes(header[56:72])))


def validate_config(config):
    if (set(config) != CONFIG_FIELDS or config['format_version'] != 1 or
            set(config['disk']) != DISK_FIELDS or set(config['tools']) != TOOL_FIELDS or
            config['tools']['package'] != 'libubootenv-tool' or
            config['tools']['version'] != '0.3.5-0.1+b2' or
            not {'/usr/bin/fw_printenv', '/usr/bin/fw_setenv'} <= set(config['tools']['files']) or
            config['tools']['files'].get('/usr/bin/fw_printenv') != SELECTED_TOOL_SHA256 or
            config['tools']['files'].get('/usr/bin/fw_setenv') != SELECTED_TOOL_SHA256 or
            not {'/usr/lib/aarch64-linux-gnu/libubootenv.so.0.3.5',
                 '/usr/lib/aarch64-linux-gnu/libubootenv.so.0',
                 '/usr/lib/aarch64-linux-gnu/libc.so.6', '/usr/lib/aarch64-linux-gnu/libz.so.1',
                 '/usr/lib/aarch64-linux-gnu/libyaml-0.so.2', '/lib/ld-linux-aarch64.so.1'} <= set(config['tools']['files']) or
            not config['dependencies'] or len(config['disk']['partition_records']) != 6):
        raise ValueError('Unreviewed commissioning target schema/tools')
    if (type(config['disk']['physical_bytes']) is not int or
            type(config['disk']['image_bytes']) is not int or
            not 0 < config['disk']['image_bytes'] <= config['disk']['physical_bytes']):
        raise ValueError('Invalid physical capacity/GPT footprint binding')
    for paths in (config['tools']['files'], config['dependencies']):
        for path, expected in paths.items():
            if (not Path(path).is_absolute() or len(expected) != 64 or
                    any(c not in '0123456789abcdef' for c in expected)):
                raise ValueError('Invalid dependency hash binding')
    if config['disk']['path'] != str(Path(config['disk']['path']).resolve()):
        raise ValueError('Whole disk must use its reviewed canonical path')
    return config


def parse_environment(output):
    values = {}
    for line in output.splitlines():
        if '=' not in line:
            raise ValueError('Invalid selected environment output')
        name, value = line.split('=', 1)
        if not name or name in values:
            raise ValueError('Duplicate/empty environment name')
        values[name] = value
    eligible(values)
    return values


def eligible(values):
    if (values.get('sv08_env_layout') != 'ab-8gb-v1' or
            values.get('BOOT_ORDER') != 'A' or values.get('BOOT_B_LEFT') != '0' or
            values.get('BOOT_A_LEFT') not in ('1', '2', '3')):
        raise ValueError('Not an eligible nonexhausted A-only environment')


def bank(image):
    if len(image) != 0x10000 or int.from_bytes(image[:4], 'little') != zlib.crc32(image[5:]):
        raise ValueError('Bad redundant environment CRC')
    end = image[5:].find(b'\0\0')
    if end < 0:
        raise ValueError('Unterminated redundant environment')
    values = parse_environment(image[5:5+end].decode('ascii').replace('\0', '\n'))
    return image[4], values


def selected_bank(images):
    flags = [bank(image)[0] for image in images]
    if flags[0] == flags[1]:
        raise ValueError('Ambiguous equal redundant flags')
    # Selected libubootenv incremental flags on block/file storage. Boolean MTD
    # flag handling is deliberately outside this whole-disk contract.
    if flags == [255, 0]:
        return 1
    if flags == [0, 255]:
        return 0
    return int(flags[1] > flags[0])


def without_counter(values):
    return {key: value for key, value in values.items() if key != 'BOOT_A_LEFT'}


def verify_readback(before, after, values):
    old = selected_bank(before)
    new = selected_bank(after)
    if new == old or after[old] != before[old]:
        raise ValueError('Selected writer did not preserve the older bank')
    baseline = without_counter(bank(before[old])[1])
    if (values.get('BOOT_A_LEFT') != '3' or values != bank(after[new])[1] or
            any(without_counter(bank(image)[1]) != baseline for image in after)):
        raise ValueError('Counter readback/other variables differ')


def validate_baseline(boot, state, manifest, config, boot_id, cmdline, root):
    if (set(boot) != {'slot', 'release', 'mode', 'generation', 'trial', 'customized', 'boot_id'} or
            boot['boot_id'] != boot_id or str(uuid.UUID(boot_id)) != boot_id or
            not uuid.UUID(boot_id).int or slot_from_cmdline(cmdline) != 'A' or
            boot['slot'] != 'A' or boot['mode'] != 'immutable' or boot['trial'] is not False or
            boot['customized'] is not False or manifest.get('deployable') is not False or
            manifest['state_schema'] != 1 or boot['release'] != config['release'] or
            manifest['release'] != config['release'] or state['requested_mode'] != 'immutable' or
            state['pending'] is not None or set(state['slots']) != {'A'} or
            'last_failed_trial' in state):
        raise ValueError('Not an initial immutable diagnostic A baseline')
    record = state['slots']['A']
    generation = Path(root) / 'generations' / config['generation']
    if (record != dict(release=config['release'], schema=1, generation=config['generation'],
                       customized=False, parent_generation=None) or
            boot['generation'] != str(generation) or generation.is_symlink() or not generation.is_dir()):
        raise ValueError('Initial registry/generation identity differs')


class Runtime:
    def __init__(self, config, *, now=time.monotonic):
        self.config = validate_config(config)
        self.now = now
        self.deadline = now() + 60
        self.store = Store('/data/sv08')
        self.fw_config = Path('/etc/sv08/commissioning-fw_env.config')

    def command(self, arguments):
        remaining = min(3, self.deadline - self.now())
        if remaining <= 0:
            raise ValueError('Commissioning deadline exceeded')
        process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
        output = [bytearray(), bytearray()]
        stop = self.now() + remaining
        try:
            with selectors.DefaultSelector() as selector:
                for index, stream in enumerate((process.stdout, process.stderr)):
                    selector.register(stream, selectors.EVENT_READ, index)
                while selector.get_map():
                    wait = stop - self.now()
                    if wait <= 0:
                        raise ValueError('Commissioning subprocess timed out')
                    for key, _ in selector.select(wait):
                        block = os.read(key.fileobj.fileno(), 4096)
                        if not block:
                            selector.unregister(key.fileobj)
                        output[key.data].extend(block)
                        if sum(map(len, output)) > 32 * 1024:
                            raise ValueError('Commissioning subprocess output overflow')
            if process.wait(timeout=max(0, stop-self.now())):
                raise ValueError('Commissioning subprocess failed: ' + arguments[0])
            return output[0].decode('ascii')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()
            process.stderr.close()

    def tool_identity(self):
        tools = self.config['tools']
        for path, target in (('/usr/bin/fw_setenv', 'fw_printenv'),
                             ('/usr/lib/aarch64-linux-gnu/libubootenv.so.0', 'libubootenv.so.0.3.5')):
            if not Path(path).is_symlink() or os.readlink(path) != target:
                raise ValueError('Selected tool/library lookup link differs')
        if self.command(['/usr/bin/dpkg-query', '-W', '-f=${Version}', tools['package']]).strip() != tools['version']:
            raise ValueError('Selected tool package version differs')
        for files in (tools['files'], self.config['dependencies']):
            for path, expected in files.items():
                if digest(path) != expected or not os.statvfs(path).f_flag & os.ST_RDONLY:
                    raise ValueError('Selected implementation/dependency differs or is mutable')
        info = self.fw_config.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077 or
                info.st_size > RECORD_LIMIT or digest(self.fw_config) != self.config['fw_config_sha256']):
            raise ValueError('Unsafe reviewed fw_env configuration')
        expected = ''.join(f"{self.config['disk']['path']} {offset:#x} {length:#x}\n" for offset, length in REGIONS)
        if self.fw_config.read_text() != expected:
            raise ValueError('Unexpected whole-disk environment map')

    def devices(self, manifest):
        disk = self.config['disk']
        path = Path(disk['path'])
        info = path.lstat()
        if (not stat.S_ISBLK(info.st_mode) or
                f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}' != disk['major_minor'] or
                str(Path('/sys/dev/block', disk['major_minor']).resolve()) != disk['sysfs'] or
                int(Path(disk['sysfs'], 'size').read_text()) * 512 != disk['physical_bytes']):
            raise ValueError('Reviewed whole-disk identity differs')
        result = inspect(path, allow_block=True, image_bytes=disk['image_bytes'], environment_regions=REGIONS)
        if (disk_guid(path) != disk['disk_guid'] or
                result['partition_records'] != disk['partition_records'] or result['partitions'] != 6):
            raise ValueError('Reviewed six-partition GPT differs')
        records = {p['partuuid']: p for p in disk['partition_records']}
        for key, mount, option in (('root-a', '/', 'ro'), ('boot-a', '/boot', 'ro'), ('data', '/data', 'rw')):
            configured = manifest['devices'][key]
            number = device_number(configured)
            part = Path('/sys/dev/block', number).resolve()
            record = records.get(Path(configured).name.lower())
            if (part.parent != Path(disk['sysfs']) or not record or
                    int((part / 'partition').read_text()) != record['number'] or
                    int((part / 'start').read_text()) * 512 != record['offset_bytes'] or
                    int((part / 'size').read_text()) * 512 != record['size_bytes']):
                raise ValueError('Mounted partition is not on reviewed GPT/disk')
            output = self.command(['/usr/bin/findmnt', '-n', '-o', 'MAJ:MIN,OPTIONS', '--mountpoint', mount]).strip().split()
            if len(output) != 2 or output[0] != number or option not in output[1].split(','):
                raise ValueError('Mount identity/mode differs: ' + mount)

    def environment(self):
        verify_environment_copies(self.fw_config)
        fd = os.open(self.config['disk']['path'], os.O_RDONLY | os.O_NOFOLLOW)
        try:
            images = tuple(os.pread(fd, length, offset) for offset, length in REGIONS)
        finally:
            os.close(fd)
        selected = selected_bank(images)
        values = parse_environment(self.command(['/usr/bin/fw_printenv', '-c', str(self.fw_config)]))
        if values != bank(images[selected])[1] or any(without_counter(bank(image)[1]) != without_counter(values) for image in images):
            raise ValueError('Tool selection or redundant logical values differ')
        return images, values

    def probe(self):
        boot = read_json('/run/sv08/boot.json')
        manifest = read_json('/usr/lib/sv08/release.json')
        read_json(self.store.root / 'state.json')
        state = self.store.load()
        cmdline = Path('/proc/cmdline').read_text()
        validate_baseline(boot, state, manifest, self.config,
                          Path('/proc/sys/kernel/random/boot_id').read_text().strip(), cmdline, self.store.root)
        for path in ('/run/sv08/trial', '/run/sv08/rauc-operation.json',
                     '/etc/rauc/system.conf', '/usr/lib/sv08/layout.json',
                     '/usr/lib/sv08/environment.json', '/usr/lib/sv08/update-policy.json',
                     str(self.store.root / 'update.json')):
            if present(path):
                raise ValueError('Trial/update/normal backend composition is present')
        tokens = cmdline.split()
        for name in MASKS:
            unit = name + '.service'
            if ('systemd.mask=' + unit not in tokens or
                    not Path('/etc/systemd/system', unit).is_symlink() or
                    os.readlink(Path('/etc/systemd/system', unit)) != '/dev/null'):
                raise ValueError('Diagnostic filesystem/effective mask is absent')
        if self.command(['/usr/bin/systemctl', 'is-active', 'sv08-prepare.service']).strip() != 'active':
            raise ValueError('Prepare is not active')
        active = self.command(['/usr/bin/systemctl', 'show', 'rauc.service', '--property=ActiveState', '--value']).strip()
        if active not in ('inactive', 'failed'):
            raise ValueError('RAUC is active/transitioning')
        self.tool_identity()
        self.devices(manifest)
        images, values = self.environment()
        return dict(boot=boot, state=state, manifest=manifest, images=images, values=values)

    def write(self):
        # Do not pre-acquire fw_printenv.lock: libubootenv owns its standard lock.
        self.command(['/usr/bin/fw_setenv', '-c', str(self.fw_config), 'BOOT_A_LEFT', '3'])
        fd = os.open(self.config['disk']['path'], os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


class Diagnostics:
    def __init__(self, store, boot_id):
        if str(uuid.UUID(boot_id)) != boot_id or not uuid.UUID(boot_id).int:
            raise ValueError('Invalid kernel boot ID')
        self.directory = store.root / 'shared/logs/journal/commissioning-health'
        for path in (self.directory, *self.directory.parents):
            if path.is_symlink():
                raise ValueError('Linked diagnostic path')
        self.directory.mkdir(mode=0o700, exist_ok=True)  # Initialized parent is required.
        self.path = self.directory / (boot_id + '.json')
        if present(self.path):
            raise ValueError('Same-boot record exists; refusing silent retry')
        entries = list(self.directory.iterdir())
        if len(entries) >= 1024 or any(p.is_symlink() or not p.is_file() or
                                     p.stat().st_size > RECORD_LIMIT for p in entries):
            raise ValueError('Unsafe/overflowing retained diagnostics')
        used = sum(p.stat().st_size for p in entries)
        fs = os.statvfs(self.directory)
        if used + RECORD_LIMIT > RETAINED_LIMIT or fs.f_bavail * fs.f_frsize < 2 * RECORD_LIMIT or fs.f_favail < 2:
            raise ValueError('Cannot retain bounded diagnostic/unknown outcome')
        self.boot_id = boot_id
        self.save('checking')  # A killed pre-write health check also cannot silently retry.

    def save(self, status, reason=''):
        value = dict(format_version=1, boot_id=self.boot_id, status=status, reason=str(reason)[:2048])
        if len(json.dumps(value).encode()) > RECORD_LIMIT:
            raise ValueError('Per-boot diagnostic overflow')
        atomic_json(self.path, value)


def run(runtime, admission=boot_admission, writer=None, *, sleep=time.sleep, diagnostics=Diagnostics):
    writer = writer or Service().writer
    # Existing installed-compatible order, no blocking state acquisition.
    with runtime.store.locked(nonblocking=True), admission(), writer():
        boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        record = diagnostics(runtime.store, boot_id)
        try:
            first = runtime.probe()
            stable_start = runtime.now()
            while runtime.now() - stable_start < 5:
                if runtime.now() >= runtime.deadline:
                    raise ValueError('60-second commissioning deadline exceeded')
                sleep(min(0.5, 5 - (runtime.now() - stable_start)))
                if runtime.probe() != first:
                    raise ValueError('Health/identity/environment changed during stable window')
            if runtime.now() >= runtime.deadline or runtime.probe() != first:
                raise ValueError('Final health/deadline revalidation failed')
            if first['values']['BOOT_A_LEFT'] == '3':
                record.save('success-noop')
                return 'noop'
            record.save('unknown-outcome')  # fsync before the ONLY invocation.
            runtime.write()
            after = runtime.probe()
            for key in ('boot', 'state', 'manifest'):
                if after[key] != first[key]:
                    raise ValueError('Identity changed after mutation')
            verify_readback(first['images'], after['images'], after['values'])
            record.save('success')
            return 'confirmed'
        except BaseException as error:
            # Keep unknown-outcome if publication fails or the process is killed.
            try:
                record.save('failed-or-unknown', type(error).__name__ + ': ' + str(error))
            except (OSError, ValueError):
                pass
            raise


def main():
    if os.geteuid() != 0:
        raise ValueError('Commissioning health requires root')
    config_path = Path('/etc/sv08/commissioning-target.json')
    info = config_path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077 or not os.statvfs(config_path).f_flag & os.ST_RDONLY:
        raise ValueError('Target config must be private, root-owned and immutable')
    def expired(_signum, _frame):
        raise TimeoutError('Commissioning hard deadline/termination')
    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGTERM, expired)
    signal.setitimer(signal.ITIMER_REAL, 60)
    try:
        run(Runtime(read_json(config_path)))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    main()
