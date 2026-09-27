#!/usr/bin/env python3
"""Offline-only recovery staging and redundant boot-policy arming primitives.

Custom gap: the installed eMMC needs a durable, ordered handoff to the RAM
writer. This module deliberately accepts only a caller-supplied filesystem
directory and a regular-file disk for arming. It has no live block-device CLI.
Retire it when the host updater owns this transaction with physical evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import zlib

from scripts.build_h616_recovery_handoff import MARKER, script_text


ENV_OFFSETS = (0x400000, 0x800000)
ENV_BYTES = 65536
RESERVE_BYTES = 16 * 1024 * 1024


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f'Regular file required: {path}')
    path = path.resolve(strict=True)
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f'Regular file required: {path}')
    return path


def verify_artifact(root):
    root = Path(root)
    if root.is_symlink():
        raise ValueError('Artifact directory required')
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Artifact directory required')
    manifest = json.loads(regular(root / 'build.json').read_text())
    if manifest.get('status') != 'nondeployable-offline-candidate':
        raise ValueError('Wrong artifact status')
    expected = manifest.get('files_sha256')
    if not isinstance(expected, dict) or set(expected) != {
            'Image', 'writer-initrd.img', 'sv08.dtb', 'writer.itb',
            'recovery.scr', 'armed'}:
        raise ValueError('Incomplete artifact inventory')
    for name, hash_value in expected.items():
        path = root / name
        if path.is_symlink() or digest(regular(path)) != hash_value:
            raise ValueError(f'Changed artifact: {name}')
    fit = (root / 'writer.itb').read_bytes()
    if (len(fit) != manifest.get('fit_bytes') or
            f'{zlib.crc32(fit):08x}' != manifest.get('fit_crc32') or
            (root / 'armed').read_bytes() != MARKER):
        raise ValueError('FIT or marker mismatch')
    expected_script = script_text(manifest['job_id'], manifest['bootargs'],
                                  len(fit), zlib.crc32(fit))
    if (root / 'recovery.cmd').read_text() != expected_script:
        raise ValueError('Selector does not bind the verified FIT and job')
    # The staged object is recovery.scr, not recovery.cmd. A self-consistent
    # build.json hash cannot establish that the compiled U-Boot script carries
    # the reviewed selector, so extract and compare its actual payload.
    with tempfile.TemporaryDirectory() as temporary:
        extracted = Path(temporary) / 'selector.bin'
        subprocess.run(['dumpimage', '-T', 'script', '-p', '0', '-o',
                        str(extracted), str(root / 'recovery.scr')],
                       check=True, capture_output=True, timeout=30)
        payload = extracted.read_bytes()
        command = expected_script.encode()
        if (len(payload) != len(command) + 8 or
                payload[:4] != len(command).to_bytes(4, 'big') or
                payload[4:8] != b'\0' * 4 or payload[8:] != command):
            raise ValueError('Compiled recovery selector differs from reviewed source')
        for index, name in enumerate(('Image', 'writer-initrd.img', 'sv08.dtb')):
            member = Path(temporary) / f'fit-{index}'
            subprocess.run(['dumpimage', '-T', 'flat_dt', '-p', str(index),
                            '-o', str(member), str(root / 'writer.itb')],
                           check=True, capture_output=True, timeout=30)
            if digest(member) != expected[name]:
                raise ValueError(f'FIT component differs from reviewed {name}')
    return manifest


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exclusive_copy(source, destination):
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        with source.open('rb') as stream, os.fdopen(fd, 'wb', closefd=False) as out:
            shutil.copyfileobj(stream, out, 1024 * 1024)
            out.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def journal_state(journal, state):
    journal.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = journal / 'state.tmp'
    if temporary.exists():
        raise ValueError('Unresolved journal temporary file')
    payload = json.dumps(state, sort_keys=True, indent=2).encode() + b'\n'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(payload)
            stream.flush()
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, journal / 'state.json')
    fsync_directory(journal)


def stage_mounted_recovery(recovery, artifact, journal, *, fault=None):
    """Stage files on a disposable mounted recovery filesystem, marker last."""
    artifact = Path(artifact)
    recovery = Path(recovery)
    if recovery.is_symlink():
        raise ValueError('Recovery directory is a symlink')
    recovery = recovery.resolve(strict=True)
    journal = Path(journal)
    if journal.is_symlink():
        raise ValueError('Journal path is a symlink')
    journal = journal.resolve()
    manifest = verify_artifact(artifact)
    if not recovery.is_dir() or journal.exists():
        raise ValueError('Fresh recovery directory and journal required')
    original = recovery / 'recovery.scr'
    if original.is_symlink():
        raise ValueError('Original recovery script is a symlink')
    original = regular(original)
    stage = recovery / 'sv08-reimage'
    if stage.exists() or stage.is_symlink():
        raise ValueError('Recovery already staged')
    fit = regular(artifact / 'writer.itb')
    space = os.statvfs(recovery)
    if space.f_bavail * space.f_frsize < fit.stat().st_size + original.stat().st_size + RESERVE_BYTES:
        raise ValueError('Recovery filesystem lacks stage reserve')
    state = {'phase': 'planned', 'job_id': manifest['job_id'],
             'fit_sha256': manifest['files_sha256']['writer.itb'],
             'original_recovery_sha256': digest(original)}
    journal_state(journal, state)
    stage.mkdir(mode=0o700)
    fsync_directory(recovery)
    exclusive_copy(original, stage / 'recovery-original.scr')
    fsync_directory(stage)
    state['phase'] = 'original-preserved';journal_state(journal, state)
    if fault == 'after-original':return state
    exclusive_copy(fit, stage / 'writer.itb')
    fsync_directory(stage)
    state['phase'] = 'fit-durable';journal_state(journal, state)
    if fault == 'after-fit':return state
    temporary = recovery / 'recovery.scr.new'
    exclusive_copy(regular(artifact / 'recovery.scr'), temporary)
    os.replace(temporary, recovery / 'recovery.scr')
    fsync_directory(recovery)
    state['phase'] = 'wrapper-durable';journal_state(journal, state)
    if fault == 'after-wrapper':return state
    temporary = stage / 'armed.new'
    exclusive_copy(regular(artifact / 'armed'), temporary)
    os.replace(temporary, stage / 'armed')
    fsync_directory(stage)
    state['phase'] = 'marker-durable';journal_state(journal, state)
    return state


def parse_env_record(record):
    if len(record) != ENV_BYTES or int.from_bytes(record[:4], 'little') != zlib.crc32(record[5:]):
        raise ValueError('Environment CRC invalid')
    fields = {}
    for item in record[5:].split(b'\0'):
        if not item:
            break
        if b'=' not in item:
            raise ValueError('Environment field malformed')
        key, value = item.split(b'=', 1)
        if key in fields:
            raise ValueError('Duplicate environment field')
        fields[key] = value
    return fields


def arm_regular_image(image, journal, *, fault=None):
    """Offline boot-policy exercise; regular file only, never a block device."""
    image = regular(image)
    if image.stat().st_size < 7_818_182_656:
        raise ValueError('Disposable target shorter than reviewed image')
    state = json.loads(regular(journal / 'state.json').read_text())
    if state.get('phase') != 'marker-durable':
        raise ValueError('Marker not durably staged')
    job_id = state['job_id']
    with image.open('rb') as stream:
        for offset in ENV_OFFSETS:
            fields = parse_env_record(os.pread(stream.fileno(), ENV_BYTES, offset))
            if (fields.get(b'sv08_env_layout') != b'ab-8gb-v1' or
                    fields.get(b'BOOT_ORDER') not in (b'A', b'B', b'A B', b'B A') or
                    fields.get(b'BOOT_A_LEFT') not in (b'0', b'1', b'2', b'3') or
                    fields.get(b'BOOT_B_LEFT') not in (b'0', b'1', b'2', b'3') or
                    b'sv08_reimage_arm' in fields):
                raise ValueError('Current boot environment is not a safe initial state')
    config = journal / 'fw_env.config'
    config.write_text(''.join(f'{image} {offset:#x} {ENV_BYTES:#x}\n'
                              for offset in ENV_OFFSETS))
    changes = journal / 'arm.env'
    changes.write_text('BOOT_ORDER=A B\nBOOT_A_LEFT=0\nBOOT_B_LEFT=0\n'
                       f'sv08_reimage_arm={job_id}\n')
    for index in range(2):
        subprocess.run(['fw_setenv', '-c', config, '-s', changes],
                       check=True, capture_output=True, timeout=30)
        state['phase'] = f'arm-copy-{index+1}-written';journal_state(journal, state)
        if fault == f'after-arm-copy-{index+1}':return state
    with image.open('rb') as stream:
        for offset in ENV_OFFSETS:
            record = os.pread(stream.fileno(), ENV_BYTES, offset)
            fields = parse_env_record(record)
            for key, expected in ((b'BOOT_ORDER', b'A B'), (b'BOOT_A_LEFT', b'0'),
                                  (b'BOOT_B_LEFT', b'0'),
                                  (b'sv08_env_layout', b'ab-8gb-v1'),
                                  (b'sv08_reimage_arm', job_id.encode())):
                if fields.get(key) != expected:
                    raise ValueError('Redundant environment was not armed')
    state['phase'] = 'armed-both-verified';journal_state(journal, state)
    return state
