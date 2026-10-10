#!/usr/bin/python3
"""Resolve the reviewed physical environment medium without fixing Linux numbering."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

METADATA = Path('/usr/lib/sv08/environment-device.json')
CONFIG = Path('/etc/fw_env.config')
RUNTIME = Path('/run/sv08')


def document(path, *, require_immutable=True):
    path = Path(path)
    entry = path.lstat()
    if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != 0 or entry.st_mode & 0o022 or
            (require_immutable and not os.statvfs(path).f_flag & os.ST_RDONLY)):
        raise ValueError('Environment identity input must be immutable and root-owned')
    return json.loads(path.read_text())


def binding(metadata=METADATA, *, require_immutable=True):
    from sv08_boot import slot_from_cmdline, verify_devices
    from sv08_rauc import block_info, validate_geometry
    from sv08_gpt import inspect
    identity = document(metadata, require_immutable=require_immutable)
    if (set(identity) != {'format_version', 'identity_path', 'expected_cid_sha256'} or
            identity['format_version'] != 1 or
            identity['identity_path'] != '/dev/disk/by-path/platform-4022000.mmc' or
            not re.fullmatch('[0-9a-f]{64}', identity['expected_cid_sha256'])):
        raise ValueError('Unreviewed environment physical identity')
    base = Path('/usr/lib/sv08')
    release, layout, policy, environment = [document(base / name, require_immutable=require_immutable) for name in
        ('release.json', 'layout.json', 'update-policy.json', 'environment.json')]
    if (release.get('deployable') is not True or environment['layout_id'] != 'ab-8gb-v1' or
            environment['medium'] != 'mmc-user-area' or environment['size_bytes'] != 65536 or
            environment['copy_offsets_bytes'] != [4194304, 8388608]):
        raise ValueError('Unreviewed physical environment layout')
    slot = slot_from_cmdline(Path('/proc/cmdline').read_text())
    verify_devices(release, slot)
    info = {name: block_info(path) for name, path in release['devices'].items()}
    parent = validate_geometry(info, layout, policy)
    root = os.stat('/')
    root_parent = (Path('/sys/dev/block') / f'{os.major(root.st_dev)}:{os.minor(root.st_dev)}').resolve(strict=True).parent
    target = Path(identity['identity_path']).resolve(strict=True)
    if not re.fullmatch(r'/dev/mmcblk[0-9]+', str(target)):
        raise ValueError('Physical alias must resolve to a canonical whole MMC node')
    entry = target.lstat()
    number = f'{os.major(entry.st_rdev)}:{os.minor(entry.st_rdev)}'
    physical = (Path('/sys/dev/block') / number).resolve(strict=True)
    if (not stat.S_ISBLK(entry.st_mode) or physical != parent or root_parent != parent or
            (parent / 'dev').read_text().strip() != number or
            int((parent / 'removable').read_text()) != 0 or
            int((parent / 'size').read_text()) * 512 < layout['image_bytes']):
        raise ValueError('Environment alias is not the reviewed whole root medium')
    cid = (parent / 'device/cid').read_bytes()
    if len(cid) != 33 or hashlib.sha256(cid).hexdigest() != identity['expected_cid_sha256']:
        raise ValueError('Environment medium CID differs from the reviewed identity')
    gpt = inspect(target, allow_block=True, image_bytes=layout['image_bytes'],
                  environment_regions=[(4194304, 65536), (8388608, 65536)])
    expected = [dict(number=info[p['name']]['partition'], name=p['name'],
                     partuuid=release['devices'][p['name']].rsplit('/', 1)[-1],
                     offset_bytes=info[p['name']]['start'], size_bytes=info[p['name']]['size'])
                for p in layout['partitions']]
    if gpt['partition_records'] != expected:
        raise ValueError('Environment medium GPT identities differ from the reviewed map')
    return target


def content(target):
    return f'{target} 0x400000 0x10000\n{target} 0x800000 0x10000\n'


def recheck(config=CONFIG):
    config = Path(config)
    entry = config.lstat()
    if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != 0 or entry.st_mode & 0o022 or
            not os.statvfs(config).f_flag & os.ST_RDONLY):
        raise ValueError('Canonical environment map must remain read-only and root-owned')
    target = binding(require_immutable=False)
    if config.read_text() != content(target):
        raise ValueError('Canonical environment configuration differs from current physical binding')
    return target


def prepare(config=CONFIG, runtime=RUNTIME, *, resolve=binding, command=subprocess.run, verify=None):
    if os.geteuid() != 0:
        raise ValueError('Environment preparation requires root')
    config, runtime = Path(config), Path(runtime)
    for path in (config, *config.parents, runtime, *runtime.parents):
        if path.is_symlink():
            raise ValueError('Environment preparation paths must not contain symlinks')
    entry = config.lstat()
    if not stat.S_ISREG(entry.st_mode) or entry.st_uid != 0 or entry.st_mode & 0o022:
        raise ValueError('Environment bind destination must be a root-owned regular file')
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    entry = runtime.stat()
    if entry.st_uid != 0 or entry.st_mode & 0o022:
        raise ValueError('Environment runtime directory is unsafe')
    target = resolve()
    if verify is None:
        from sv08_rauc_bootloader import verify_environment_copies
        verify = verify_environment_copies
    fd, temporary = tempfile.mkstemp(prefix='.fw-env-', dir=runtime)
    temporary = Path(temporary)
    published = runtime / 'fw_env.config'
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content(target)); stream.flush(); os.fsync(stream.fileno())
        verify(config=temporary)
        if published.is_symlink():
            raise ValueError('Environment runtime map must not be a symlink')
        os.replace(temporary, published)
        command(['mount', '--bind', str(published), str(config)], check=True)
        command(['mount', '-o', 'remount,bind,ro', str(config)], check=True)
        if not os.statvfs(config).f_flag & os.ST_RDONLY or config.read_text() != content(resolve()):
            raise ValueError('Environment map was not bound read-only to the current physical medium')
    finally:
        temporary.unlink(missing_ok=True)
