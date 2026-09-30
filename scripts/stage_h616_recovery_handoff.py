#!/usr/bin/env python3
"""Offline-only recovery staging and redundant boot-policy arming primitives.

Custom gap: the installed eMMC needs a durable, ordered handoff to the RAM
writer. This module deliberately accepts only a caller-supplied filesystem
directory and a regular-file disk for arming. It has no live block-device CLI.
Retire it when the host updater owns this transaction with physical evidence.
"""
import hashlib
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import zlib

from scripts.build_h616_recovery_handoff import MARKER, script_text
from scripts.build_h616_reimage_candidate import (policy_fields, verify_signed_job,
                                                  verify_compiled_writer)
from scripts.build_sd_network_image import commissioning_bundle
from tests.sv08_emmc_job import canonical_json
from runtime.sv08_gpt import inspect as inspect_gpt


ENV_OFFSETS = (0x400000, 0x800000)
ENV_BYTES = 65536
RESERVE_BYTES = 16 * 1024 * 1024
ARCHIVE_MAX_BYTES = 128 * 1024 * 1024
MEMBER_MAX_BYTES = 64 * 1024 * 1024


def verify_initramfs_members(path, expected):
    """Stream the actual composer's single gzip/newc archive; never extract it.

    Bound the measured 55 MiB archive to 128 MiB, 64 MiB per ordinary member,
    4096-byte names and 100000 entries. Required regular members are bounded by
    their exact reviewed bytes. No new target-side executable is required.
    """
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Initramfs compressed input exceeds FIT budget')
    total, entries, found, seen = 0, 0, set(), set()
    archive_hash = hashlib.sha256()
    with gzip.open(path, 'rb') as stream:
        def read(amount):
            nonlocal total
            if total + amount > ARCHIVE_MAX_BYTES:
                raise ValueError('Initramfs archive exceeds 128 MiB budget')
            data = stream.read(amount)
            total += len(data)
            archive_hash.update(data)
            if len(data) != amount:
                raise ValueError('Truncated initramfs newc archive')
            return data
        while True:
            header = read(110)
            if header[:6] != b'070701' or not re.fullmatch(b'[0-9a-fA-F]{104}', header[6:]):
                raise ValueError('Unsupported initramfs newc header')
            fields = [int(header[6 + index * 8:14 + index * 8], 16) for index in range(13)]
            mode, nlink, size, namesize, checksum = fields[1], fields[4], fields[6], fields[11], fields[12]
            if not 2 <= namesize <= 4097 or size > MEMBER_MAX_BYTES or checksum != 0:
                raise ValueError('Invalid initramfs member/name bounds')
            raw_name = read(namesize)
            if raw_name[-1:] != b'\0' or b'\0' in raw_name[:-1]:
                raise ValueError('Malformed initramfs member name')
            try:
                name = raw_name[:-1].decode('utf-8')
            except UnicodeDecodeError as error:
                raise ValueError('Invalid initramfs member encoding') from error
            if read(-(110 + namesize) % 4).strip(b'\0'):
                raise ValueError('Invalid initramfs name padding')
            if name == 'TRAILER!!!':
                if size:
                    raise ValueError('Invalid initramfs trailer')
                # cpio pads its final block with zeros. Read through gzip EOF to
                # validate CRC and include all padding in the composition hash.
                while True:
                    padding = stream.read(65536)
                    if not padding:
                        break
                    total += len(padding)
                    if total > ARCHIVE_MAX_BYTES or padding.strip(b'\0'):
                        raise ValueError('Invalid initramfs archive tail/budget')
                    archive_hash.update(padding)
                break
            if (not name or name.startswith('/') or name in seen or
                    (name != '.' and any(part in ('', '.', '..') for part in name.split('/')))):
                raise ValueError('Duplicate or unsafe initramfs member path')
            seen.add(name)
            entries += 1
            if entries > 100000:
                raise ValueError('Too many initramfs members')
            kind = stat.S_IFMT(mode)
            if (kind not in (stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK,
                             stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO) or
                    (kind in (stat.S_IFDIR, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO) and size) or
                    (kind == stat.S_IFLNK and size > 4096)):
                raise ValueError('Unsupported initramfs member type/size')
            if name in expected:
                if kind != stat.S_IFREG or nlink != 1 or size != len(expected[name]):
                    raise ValueError(f'Actual initramfs differs from signed bundle: {name}')
                if read(size) != expected[name]:
                    raise ValueError(f'Actual initramfs differs from signed bundle: {name}')
                found.add(name)
            else:
                remaining = size
                while remaining:
                    chunk = min(remaining, 65536)
                    read(chunk)
                    remaining -= chunk
            if read(-size % 4).strip(b'\0'):
                raise ValueError('Invalid initramfs data padding')
    if found != set(expected):
        raise ValueError('Actual initramfs lacks required trusted members')
    return archive_hash.hexdigest()


class VerifiedArtifact(dict):
    """Carry the actual hash-checked initramfs path to signed revalidation."""
    def __init__(self, manifest, root):
        super().__init__(manifest)
        self.root = root


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
    if (manifest.get('status'), manifest.get('synthetic_test')) not in (
            ('nondeployable-offline-candidate', True),
            ('h12-attended-candidate', False)):
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
    return VerifiedArtifact(manifest, root)


def verify_signed_stage_bundle(manifest, bundle, verification_key, *, now=None):
    """Recheck the exact signed job/map bound into the candidate at stage time."""
    composition = manifest.get('composition')
    if not isinstance(composition, dict):
        raise ValueError('Missing writer composition')
    source = composition.get('source', '')
    if not isinstance(source, str) or ':' not in source:
        raise ValueError('Missing reviewed NFS source')
    server, export = source.split(':', 1)
    if not isinstance(manifest, VerifiedArtifact):
        raise ValueError('Actual verified artifact required for signed staging')
    for name, limit in (('sd-network-init', 4 * 1024 * 1024), ('job.json', 65536),
                        ('commissioning-target-policy.json', 65536),
                        ('job.sig', 64), ('expected.sha256', 65)):
        if regular(Path(bundle) / name).stat().st_size > limit:
            raise ValueError(f'Staging bundle input exceeds budget: {name}')
    bundle, writer_manifest, files = commissioning_bundle(Path(bundle), server, export)
    if digest(regular(bundle / 'reimage-manifest.json')) != composition.get('bundle_manifest_sha256'):
        raise ValueError('Staged artifact and signed bundle differ')
    policy_raw = regular(bundle / 'commissioning-target-policy.json').read_bytes()
    policy = policy_fields(json.loads(policy_raw))
    if server != policy['claim_server']:
        raise ValueError('NFS source must be the independently admitted claim host')
    if manifest.get('synthetic_test') != (policy['board_compatible'] == 'test,synthetic-h616'):
        raise ValueError('Artifact and signed target class differ')
    if policy_raw != canonical_json(policy):
        raise ValueError('Noncanonical target policy')
    job = verify_signed_job(regular(bundle / 'job.json').read_bytes(),
                            regular(bundle / 'job.sig').read_bytes(),
                            regular(verification_key).read_bytes(), policy, now=now,
                            preflight_only=writer_manifest.get('preflight_only', False))
    if job['job_id'] != manifest['job_id']:
        raise ValueError('Staged artifact and signed job differ')
    mode = writer_manifest.get('preflight_only', False)
    if (type(mode) is not bool or type(manifest.get('preflight_only', False)) is not bool or
            manifest.get('preflight_only', False) is not mode or
            manifest.get('job_format', 'sv08-h616-signed-reimage-v1') != job['format'] or
            writer_manifest.get('job_format', 'sv08-h616-signed-reimage-v1') != job['format'] or
            bool('sv08.h616_preflight=1' in manifest['bootargs'].split()) is not mode):
        raise ValueError('Signed staging purpose and artifact/bundle mode mismatch')
    compiled = verify_compiled_writer(bundle, writer_manifest)
    if (manifest.get('compiled_purpose_sha256') != compiled or
            manifest.get('writer_sha256') != writer_manifest['binary_sha256'] or
            composition.get('writer_sha256') != writer_manifest['binary_sha256'] or
            composition.get('initramfs_sha256') != manifest['files_sha256']['writer-initrd.img']):
        raise ValueError('Staged artifact and actual compiled writer binding differ')
    # FIT extraction already proved that this is the actual embedded initramfs.
    # Compare its trusted executable and signed inputs, not unsigned labels.
    expected_members = {destination: regular(bundle / name).read_bytes()
                        for destination, (name, _) in files.items()}
    expected_members['expected.sha256'] = regular(bundle / 'expected.sha256').read_bytes()
    expected_members['scripts/init-bottom/ORDER'] = (
        '# Trusted commissioning path; /root is data only.\nexec /trusted-writer\n'
        'echo "SV08 writer exec failed; stopping" > /dev/kmsg\n'
        'while :; do sleep 3600; done\n').encode()
    archive_digest = verify_initramfs_members(manifest.root / 'writer-initrd.img', expected_members)
    if archive_digest != composition.get('initramfs_cpio_sha256'):
        raise ValueError('Actual initramfs archive differs from composition')
    return policy


def admit_disposable_loop_recovery(image, recovery, policy):
    """Bind a mounted ext4 recovery fixture to the signed 32 GB target map."""
    image = regular(image)
    if image.stat().st_size != policy['sectors'] * 512:
        raise ValueError('Disposable target capacity differs from signed policy')
    gpt = inspect_gpt(image, allow_regular_prefix=True,
                      image_bytes=policy['image_bytes'],
                      environment_regions=tuple((offset, ENV_BYTES)
                                                for offset in ENV_OFFSETS))
    expected = policy['image_layout']
    if (gpt['disk_guid'] != expected['disk_guid'] or
            gpt['partition_records'] != expected['partitions']):
        raise ValueError('Disposable target GPT differs from signed map')
    result = subprocess.run(['findmnt', '--json', '--target', str(recovery),
                             '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS'],
                            check=True, capture_output=True, text=True, timeout=10)
    filesystems = json.loads(result.stdout).get('filesystems', [])
    if len(filesystems) != 1:
        raise ValueError('Recovery mount is ambiguous')
    mounted = filesystems[0]
    source = Path(mounted.get('source', ''))
    if (Path(mounted.get('target', '')).resolve() != recovery or
            mounted.get('fstype') != 'ext4' or
            'rw' not in mounted.get('options', '').split(',') or
            not source.name.startswith('loop') or
            not stat.S_ISBLK(source.stat().st_mode) or
            recovery.stat().st_dev != source.stat().st_rdev):
        raise ValueError('Recovery is not the expected writable loop filesystem')
    loop = Path('/sys/class/block') / source.name / 'loop'
    backing = Path((loop / 'backing_file').read_text().strip()).resolve()
    offset = int((loop / 'offset').read_text().strip())
    limit = int((loop / 'sizelimit').read_text().strip())
    partition = expected['partitions'][4]
    if (backing != image or offset != partition['offset_bytes'] or
            limit != partition['size_bytes']):
        raise ValueError('Recovery loop does not map signed partition five')
    image_stat = image.stat()
    return {'target_regular_dev': image_stat.st_dev,
            'target_regular_ino': image_stat.st_ino,
            'recovery_partuuid': partition['partuuid'],
            'recovery_offset_bytes': offset, 'recovery_size_bytes': limit}


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


def stage_mounted_recovery(recovery, artifact, journal, *,
                           bundle, verification_key, expected_build_sha256,
                           expected_original_sha256, mounted_target_image=None,
                           mounted_live_target=None, live_sysfs_root=None,
                           synthetic_live_fixture=False,
                           disposable_directory_fixture=False,
                           now=None, fault=None):
    """Stage writer files while the original boot policy remains selected."""
    if fault not in (None, 'after-original', 'after-fit', 'after-wrapper'):
        raise ValueError('Unknown file-staging interruption point')
    artifact = Path(artifact)
    recovery = Path(recovery)
    if recovery.is_symlink():
        raise ValueError('Recovery directory is a symlink')
    recovery = recovery.resolve(strict=True)
    journal = Path(journal)
    if journal.is_symlink():
        raise ValueError('Journal path is a symlink')
    journal = journal.resolve()
    if mounted_live_target is not None and journal.is_relative_to(recovery):
        raise ValueError('Live journal must be separate from recovery filesystem')
    artifact = Path(artifact)
    if (not isinstance(expected_build_sha256, str) or
            len(expected_build_sha256) != 64 or
            digest(regular(artifact / 'build.json')) != expected_build_sha256):
        raise ValueError('Handoff artifact differs from reviewed build')
    manifest = verify_artifact(artifact)
    policy = verify_signed_stage_bundle(manifest, bundle, verification_key, now=now)
    if mounted_target_image is not None:
        if disposable_directory_fixture or mounted_live_target is not None:
            raise ValueError('Choose one recovery identity mode')
        admission = admit_disposable_loop_recovery(mounted_target_image,
                                                   recovery, policy)
    elif mounted_live_target is not None:
        if disposable_directory_fixture:
            raise ValueError('Choose one recovery identity mode')
        from scripts.live_h616_recovery_stage import (
            admitted_target, HOST_SYSFS, isolate_mounts_for_write)
        if not synthetic_live_fixture:
            isolate_mounts_for_write()
        admission = admitted_target(Path(mounted_live_target), recovery, policy,
                                    host_sysfs=live_sysfs_root or HOST_SYSFS,
                                    synthetic_fixture=synthetic_live_fixture,
                                    require_writable=True)
    elif disposable_directory_fixture:
        admission = {'disposable_directory_fixture': True}
    else:
        raise ValueError('Recovery partition identity not established')
    def check_live():
        if mounted_live_target is not None:
            current = admitted_target(Path(mounted_live_target), recovery, policy,
                                      host_sysfs=live_sysfs_root or HOST_SYSFS,
                                      synthetic_fixture=synthetic_live_fixture,
                                      require_writable=True)
            if current != admission:
                raise ValueError('Live recovery identity changed during staging')
    if not recovery.is_dir() or journal.exists():
        raise ValueError('Fresh recovery directory and journal required')
    original = recovery / 'recovery.scr'
    if original.is_symlink():
        raise ValueError('Original recovery script is a symlink')
    original = regular(original)
    if (not isinstance(expected_original_sha256, str) or
            len(expected_original_sha256) != 64 or
            digest(original) != expected_original_sha256):
        raise ValueError('Original recovery script differs from reviewed input')
    stage = recovery / 'sv08-reimage'
    if stage.exists() or stage.is_symlink():
        raise ValueError('Recovery already staged')
    fit = regular(artifact / 'writer.itb')
    space = os.statvfs(recovery)
    if space.f_bavail * space.f_frsize < fit.stat().st_size + original.stat().st_size + RESERVE_BYTES:
        raise ValueError('Recovery filesystem lacks stage reserve')
    state = {'phase': 'planned', 'job_id': manifest['job_id'],
             'recovery_admission': admission,
             'build_sha256': expected_build_sha256,
             'target_policy_sha256': hashlib.sha256(canonical_json(policy)).hexdigest(),
             'fit_sha256': manifest['files_sha256']['writer.itb'],
             'original_recovery_sha256': digest(original)}
    journal_state(journal, state)
    check_live()
    stage.mkdir(mode=0o700)
    fsync_directory(recovery)
    check_live()
    exclusive_copy(original, stage / 'recovery-original.scr')
    fsync_directory(stage)
    state['phase'] = 'original-preserved';journal_state(journal, state)
    if fault == 'after-original':return state
    check_live()
    exclusive_copy(fit, stage / 'writer.itb')
    fsync_directory(stage)
    state['phase'] = 'fit-durable';journal_state(journal, state)
    if fault == 'after-fit':return state
    check_live()
    temporary = recovery / 'recovery.scr.new'
    exclusive_copy(regular(artifact / 'recovery.scr'), temporary)
    os.replace(temporary, recovery / 'recovery.scr')
    fsync_directory(recovery)
    state['phase'] = 'wrapper-durable';journal_state(journal, state)
    if fault == 'after-wrapper':return state
    check_live()
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


def arm_regular_image(image, journal, *, target_policy, fault=None):
    """Offline boot-policy exercise; regular file only, never a block device."""
    if fault not in (None, 'after-arm-copy-1', 'after-arm-copy-2'):
        raise ValueError('Unknown boot-policy interruption point')
    image = regular(image)
    if image.stat().st_size < 7_818_182_656:
        raise ValueError('Disposable target shorter than reviewed image')
    state = json.loads(regular(journal / 'state.json').read_text())
    if state.get('phase') != 'wrapper-durable':
        raise ValueError('Recovery wrapper not durably staged')
    admission = state.get('recovery_admission')
    if not isinstance(admission, dict):
        raise ValueError('Recovery target admission missing')
    if 'target_regular_dev' in admission or 'target_regular_ino' in admission:
        identity = image.stat()
        if (set(('target_regular_dev', 'target_regular_ino')) - admission.keys() or
                admission['target_regular_dev'] != identity.st_dev or
                admission['target_regular_ino'] != identity.st_ino):
            raise ValueError('Arming target differs from staged recovery target')
    elif admission.get('disposable_directory_fixture') is not True:
        raise ValueError('Recovery target admission missing')
    target_policy = policy_fields(target_policy)
    if (hashlib.sha256(canonical_json(target_policy)).hexdigest() !=
            state.get('target_policy_sha256')):
        raise ValueError('Arming policy differs from signed staged job')
    gpt = inspect_gpt(image, allow_regular_prefix=True,
                      image_bytes=target_policy['image_bytes'],
                      environment_regions=tuple((offset, ENV_BYTES)
                                                for offset in ENV_OFFSETS))
    expected = target_policy['image_layout']
    if (gpt['disk_guid'] != expected['disk_guid'] or
            gpt['partition_records'] != expected['partitions']):
        raise ValueError('Current target GPT differs from signed image map')
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


def activate_mounted_recovery(recovery, artifact, journal, *, image,
                              target_policy, disposable_directory_fixture=False,
                              live_target=False, live_sysfs_root=None,
                              synthetic_live_fixture=False):
    """Publish the one-shot marker only after both environment copies verify."""
    if live_target and not synthetic_live_fixture:
        from scripts.live_h616_recovery_stage import isolate_mounts_for_write
        isolate_mounts_for_write()
    image = Path(image) if live_target else regular(image)
    recovery = Path(recovery).resolve(strict=True)
    journal = Path(journal).resolve(strict=True)
    state = json.loads(regular(journal / 'state.json').read_text())
    if state.get('phase') != 'armed-both-verified':
        raise ValueError('Both environment copies must be verified before activation')
    policy = policy_fields(target_policy)
    if (hashlib.sha256(canonical_json(policy)).hexdigest() !=
            state.get('target_policy_sha256')):
        raise ValueError('Activation policy differs from staged job')
    admission = state.get('recovery_admission')
    if disposable_directory_fixture:
        if admission != {'disposable_directory_fixture': True}:
            raise ValueError('Wrong disposable recovery identity')
    elif live_target:
        from scripts.live_h616_recovery_stage import admitted_target, HOST_SYSFS
        current = admitted_target(image, recovery, policy,
                                  host_sysfs=live_sysfs_root or HOST_SYSFS,
                                  synthetic_fixture=synthetic_live_fixture,
                                  require_writable=True)
        if current != admission:
            raise ValueError('Mounted live recovery identity changed before activation')
    elif admit_disposable_loop_recovery(image, recovery, policy) != admission:
        raise ValueError('Mounted recovery identity changed before activation')
    manifest = verify_artifact(artifact)
    if (digest(regular(Path(artifact) / 'build.json')) != state['build_sha256'] or
            manifest['job_id'] != state['job_id'] or
            digest(regular(recovery / 'recovery.scr')) != manifest['files_sha256']['recovery.scr'] or
            digest(regular(recovery / 'sv08-reimage/recovery-original.scr')) !=
            state['original_recovery_sha256'] or
            digest(regular(recovery / 'sv08-reimage/writer.itb')) != state['fit_sha256']):
        raise ValueError('Staged handoff changed before activation')
    fd = os.open(image, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        if live_target and (not stat.S_ISBLK(os.fstat(fd).st_mode) or
                f'{os.major(os.fstat(fd).st_rdev)}:{os.minor(os.fstat(fd).st_rdev)}' != admission['dev_t']):
            raise ValueError('Opened activation target differs from admitted eMMC')
        for offset in ENV_OFFSETS:
            fields = parse_env_record(os.pread(fd, ENV_BYTES, offset))
            if (fields.get(b'sv08_env_layout') != b'ab-8gb-v1' or
                    fields.get(b'BOOT_ORDER') != b'A B' or
                    fields.get(b'BOOT_A_LEFT') != b'0' or
                    fields.get(b'BOOT_B_LEFT') != b'0' or
                    fields.get(b'sv08_reimage_arm') != state['job_id'].encode()):
                raise ValueError('Boot policy not fully armed before activation')
    finally:
        os.close(fd)
    if live_target and admitted_target(image, recovery, policy,
                                      host_sysfs=live_sysfs_root or HOST_SYSFS,
                                      synthetic_fixture=synthetic_live_fixture,
                                      require_writable=True) != admission:
        raise ValueError('Live recovery identity changed before marker')
    stage = recovery / 'sv08-reimage'
    if (stage / 'armed').exists() or (stage / 'armed.new').exists():
        raise ValueError('Recovery marker already exists')
    temporary = stage / 'armed.new'
    exclusive_copy(regular(Path(artifact) / 'armed'), temporary)
    os.replace(temporary, stage / 'armed')
    fsync_directory(stage)
    state['phase'] = 'marker-durable'
    journal_state(journal, state)
    return state
