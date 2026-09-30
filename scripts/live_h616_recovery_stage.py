#!/usr/bin/env python3
"""Guarded running-host admission for the installed SV08 recovery handoff.

This module defaults to inspection. It adds the live-device boundary missing
from the disposable stager; H12 still gates every physical boot-policy action.
Retire this adapter when the supported host updater owns the transaction.
"""
from __future__ import annotations

import argparse
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from runtime.sv08_gpt import inspect as inspect_gpt
from scripts.build_h616_reimage_candidate import policy_fields, V2_FORMAT
from scripts.stage_h616_recovery_handoff import (
    ENV_BYTES, ENV_OFFSETS, activate_mounted_recovery, digest,
    journal_state, parse_env_record, regular,
    stage_mounted_recovery, verify_artifact, verify_signed_stage_bundle)
from tests.sv08_emmc_job import canonical_json


HOST_SYSFS = Path('/sys/bus/platform/devices/4022000.mmc/mmc_host')
TARGET = Path('/dev/mmcblk0')
BLKGETSIZE64 = 0x80081272
SECTOR = 512
CLONE_NEWNS = 0x00020000


def isolate_mounts_for_write() -> None:
    """Freeze this process's mount view before a physical staging operation."""
    if os.geteuid() != 0:
        raise ValueError('Mount isolation requires root')
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.unshare(CLONE_NEWNS) != 0:
        raise OSError(ctypes.get_errno(), 'Cannot isolate recovery mount namespace')
    subprocess.run(['mount', '--make-rprivate', '/'], check=True,
                   capture_output=True, timeout=15)


def local_ipv4_addresses() -> set[str]:
    result = subprocess.run(['ip', '-j', '-4', 'address', 'show'], check=True,
                            capture_output=True, text=True, timeout=10)
    return {address['local'] for link in json.loads(result.stdout)
            for address in link.get('addr_info', []) if 'local' in address}


def one_line(path: Path) -> str:
    raw = path.read_bytes()
    if not raw.endswith(b'\n') or b'\n' in raw[:-1] or b'\0' in raw or len(raw) > 128:
        raise ValueError(f'Malformed sysfs value: {path}')
    return raw[:-1].decode('ascii')


def decimal(path: Path) -> int:
    value = one_line(path)
    if not re.fullmatch(r'[0-9]+', value):
        raise ValueError(f'Malformed sysfs integer: {path}')
    return int(value)


def dev_number(path: Path) -> tuple[int, int]:
    value = one_line(path)
    if not re.fullmatch(r'[0-9]+:[0-9]+', value):
        raise ValueError(f'Malformed sysfs device number: {path}')
    major, minor = map(int, value.split(':'))
    return major, minor


def sole_mmc_card(host_sysfs: Path) -> Path:
    """Refuse every ambiguous/non-MMC card under the reviewed H616 controller."""
    hosts = [path for path in host_sysfs.iterdir()
             if re.fullmatch(r'mmc[0-9]+', path.name)]
    if len(hosts) != 1:
        raise ValueError('Expected exactly one MMC host under H616 controller')
    cards = [path for path in hosts[0].iterdir()
             if re.fullmatch(re.escape(hosts[0].name) + r':[0-9a-fA-F]+', path.name)]
    if len(cards) != 1 or one_line(cards[0] / 'type') != 'MMC':
        raise ValueError('Expected exactly one eMMC card')
    return cards[0]


def mount_record(recovery: Path) -> dict:
    result = subprocess.run(['findmnt', '--json', '--mountpoint', str(recovery),
                             '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS'],
                            check=True, capture_output=True, text=True, timeout=10)
    entries = json.loads(result.stdout).get('filesystems', [])
    if len(entries) != 1:
        raise ValueError('Recovery mount is ambiguous')
    return entries[0]


def v2_staging_snapshot(host_sysfs: Path, policy: dict) -> tuple:
    """Read one exact phase mapping; callers compare, never replace, it."""
    card = sole_mmc_card(host_sysfs)
    blocks = list((card / 'block').iterdir())
    if len(blocks) != 1 or blocks[0].name != Path(policy['target_device']).name:
        raise ValueError('Ambiguous eMMC user area')
    block = blocks[0]
    p5 = Path('/sys/class/block') / (block.name + 'p5')
    controller = host_sysfs.resolve(strict=True)
    resolved_card = card.resolve(strict=True)
    resolved_block = block.resolve(strict=True)
    resolved_p5 = p5.resolve(strict=True)
    if (not resolved_card.is_relative_to(controller) or
            resolved_block.parent != resolved_card / 'block' or
            resolved_p5.parent != resolved_block):
        raise ValueError('Controller/card/recovery ancestry differs')
    return (str(controller), str(resolved_card), str(resolved_block), str(resolved_p5),
            one_line(card / 'cid'), one_line(card / 'type'), decimal(block / 'size'),
            dev_number(block / 'dev'), dev_number(p5 / 'dev'), decimal(p5 / 'partition'),
            decimal(p5 / 'start'), decimal(p5 / 'size'), (p5 / 'uevent').read_bytes())


def admitted_target(target: Path, recovery: Path, policy: dict, *,
                    host_sysfs: Path = HOST_SYSFS,
                    synthetic_fixture: bool = False,
                    require_writable: bool = False,
                    local_addresses: set[str] | None = None) -> dict:
    """Read only; bind opened block descriptor, sysfs, GPT and exact ext4 mount."""
    policy = policy_fields(policy)
    if synthetic_fixture != (policy['board_compatible'] == 'test,synthetic-h616'):
        raise ValueError('Synthetic and physical target policies must stay separate')
    v2 = policy['format'] == V2_FORMAT
    if not synthetic_fixture and (target != Path(policy['target_device']) or host_sysfs != HOST_SYSFS):
        raise ValueError('Physical target/controller path is fixed')
    addresses = local_ipv4_addresses() if local_addresses is None else local_addresses
    if policy['claim_server'] in addresses:
        raise ValueError('NFS/claim source overlaps the running target host')
    target = Path(target)
    recovery = Path(recovery)
    if target.is_symlink() or recovery.is_symlink():
        raise ValueError('Device or mount path is a symlink')
    recovery = recovery.resolve(strict=True)
    if not recovery.is_dir():
        raise ValueError('Recovery mount directory required')
    snapshot = v2_staging_snapshot(host_sysfs, policy) if v2 else None
    fd = os.open(target, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISBLK(opened.st_mode):
            raise ValueError('Opened target is not a block device')
        size = struct.unpack('Q', fcntl.ioctl(fd, BLKGETSIZE64, bytes(8)))[0]
        if size != policy['sectors'] * SECTOR:
            raise ValueError('Opened capacity differs from signed policy')
        card = sole_mmc_card(host_sysfs)
        cid = one_line(card / 'cid')
        blocks = list((card / 'block').iterdir())
        if len(blocks) != 1 or blocks[0].name != Path(policy['target_device']).name:
            raise ValueError('Ambiguous eMMC user area')
        block = blocks[0]
        current_dev = dev_number(block / 'dev')
        if (not re.fullmatch(r'[0-9a-f]{32}', cid) or cid != policy['cid'] or
                decimal(block / 'size') != policy['sectors'] or
                current_dev != (os.major(opened.st_rdev), os.minor(opened.st_rdev)) or
                f'{current_dev[0]}:{current_dev[1]}' != policy['dev_t']):
            raise ValueError('Current eMMC identity differs from signed policy')
        if not synthetic_fixture and target != Path(policy['target_device']):
            raise ValueError('Target path differs from signed policy')
        part = policy['image_layout']['partitions'][4]
        p5 = (Path('/sys/class/block') / (block.name + 'p5') if not synthetic_fixture
              else block / (block.name + 'p5'))
        if v2 and (p5.resolve(strict=True).parent != block.resolve(strict=True) or
                   decimal(p5 / 'partition') != 5 or
                   decimal(p5 / 'start') * SECTOR != part['offset_bytes'] or
                   decimal(p5 / 'size') * SECTOR != part['size_bytes']):
            raise ValueError('Recovery parent/map differs from signed partition five')
        part_dev = dev_number(p5 / 'dev')
        uevent = (p5 / 'uevent').read_text().splitlines()
        if uevent.count('PARTUUID=' + part['partuuid']) != 1:
            raise ValueError('Kernel recovery PARTUUID differs from signed map')
        mounted = mount_record(recovery)
        source = Path(mounted.get('source', ''))
        options = mounted.get('options', '').split(',')
        if (Path(mounted.get('target', '')).resolve(strict=True) != recovery or
                mounted.get('fstype') != 'ext4' or
                not ({'ro', 'rw'} & set(options)) or
                (require_writable and 'rw' not in options) or
                not source.is_absolute() or source.is_symlink() or
                not stat.S_ISBLK(source.stat().st_mode) or
                (os.major(source.stat().st_rdev), os.minor(source.stat().st_rdev)) != part_dev or
                recovery.stat().st_dev != source.stat().st_rdev):
            raise ValueError('Recovery mount differs from signed partition five')
        gpt = inspect_gpt(Path(f'/proc/self/fd/{fd}'), allow_block=True,
                          image_bytes=policy['image_bytes'],
                          environment_regions=tuple((offset, ENV_BYTES)
                                                    for offset in ENV_OFFSETS))
        expected = policy['image_layout']
        if (gpt['disk_guid'] != expected['disk_guid'] or
                gpt['partition_records'] != expected['partitions']):
            raise ValueError('Current GPT differs from signed image map')
        if v2 and v2_staging_snapshot(host_sysfs, policy) != snapshot:
            raise ValueError('Current staging snapshot changed during admission')
        if os.fstat(fd).st_rdev != opened.st_rdev:
            raise ValueError('Opened target changed during admission')
        return {'cid': cid, 'controller': '4022000.mmc', 'card_type': 'MMC',
                'sectors': policy['sectors'], 'dev_t': policy['dev_t'],
                'target_path': str(target),
                'recovery_partuuid': part['partuuid'],
                'recovery_dev_t': f'{part_dev[0]}:{part_dev[1]}',
                'recovery_mount': str(recovery),
                'recovery_mount_mode': 'rw' if 'rw' in options else 'ro',
                'disk_guid': gpt['disk_guid'],
                'image_bytes': policy['image_bytes'],
                **({'policy_format': policy['format'], 'phase': 'staging-host',
                    'runtime_admission': policy['runtime_admission'],
                    'controller_sysfs': snapshot[0], 'card_sysfs': snapshot[1],
                    'block_sysfs': snapshot[2], 'p5_sysfs': snapshot[3]} if v2 else {})}
    finally:
        os.close(fd)


def _stage_state(journal: Path, admission: dict, policy: dict, *, phase: str) -> dict:
    state = json.loads(regular(journal / 'state.json').read_text())
    if state.get('phase') != phase or state.get('recovery_admission') != admission or \
            state.get('target_policy_sha256') != hashlib.sha256(canonical_json(policy)).hexdigest():
        raise ValueError('Staged journal phase, target or signed policy differs')
    return state


def _verify_staged_files(recovery: Path, artifact: Path, state: dict) -> dict:
    manifest = verify_artifact(artifact)
    if (digest(regular(artifact / 'build.json')) != state['build_sha256'] or
            manifest['job_id'] != state['job_id'] or
            digest(regular(recovery / 'recovery.scr')) != manifest['files_sha256']['recovery.scr'] or
            digest(regular(recovery / 'sv08-reimage/recovery-original.scr')) !=
            state['original_recovery_sha256'] or
            digest(regular(recovery / 'sv08-reimage/writer.itb')) != state['fit_sha256'] or
            (recovery / 'sv08-reimage/armed').exists()):
        raise ValueError('Staged recovery files changed or marker already exists')
    return manifest


def _verify_job(artifact: Path, bundle: Path, verification_key: Path,
                policy: dict, job_id: str, *, now=None) -> None:
    manifest = verify_artifact(artifact)
    signed = verify_signed_stage_bundle(manifest, bundle, verification_key, now=now)
    if (canonical_json(signed) != canonical_json(policy) or
            manifest['job_id'] != job_id):
        raise ValueError('Current signed job differs from staged target')


def arm_live_target(target: Path, recovery: Path, journal: Path, *,
                    target_policy: dict, artifact: Path, bundle: Path,
                    verification_key: Path, host_sysfs: Path = HOST_SYSFS,
                    synthetic_fixture: bool = False, now=None,
                    fault: str | None = None) -> dict:
    """Explicit, journaled environment arm; no marker is published here."""
    if fault not in (None, 'after-arm-copy-1', 'after-arm-copy-2') or \
            (fault and not synthetic_fixture):
        raise ValueError('Fault injection is disposable-fixture-only')
    target, recovery, journal, artifact = map(Path, (target, recovery, journal, artifact))
    policy = policy_fields(target_policy)
    if not synthetic_fixture:
        isolate_mounts_for_write()
    if journal.resolve().is_relative_to(recovery.resolve(strict=True)):
        raise ValueError('Journal must be separate from recovery filesystem')
    admission = admitted_target(target, recovery, policy,
                                host_sysfs=host_sysfs,
                                synthetic_fixture=synthetic_fixture,
                                require_writable=True)
    state = _stage_state(journal, admission, policy, phase='wrapper-durable')
    _verify_job(artifact, Path(bundle), Path(verification_key), policy,
                state['job_id'], now=now)
    _verify_staged_files(recovery, artifact, state)
    fd = os.open(target, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if (not stat.S_ISBLK(opened.st_mode) or
                f'{os.major(opened.st_rdev)}:{os.minor(opened.st_rdev)}' != admission['dev_t'] or
                admitted_target(target, recovery, policy, host_sysfs=host_sysfs,
                                synthetic_fixture=synthetic_fixture,
                                require_writable=True) != admission):
            raise ValueError('Opened arming target differs from admitted eMMC')
        for offset in ENV_OFFSETS:
            fields = parse_env_record(os.pread(fd, ENV_BYTES, offset))
            if (fields.get(b'sv08_env_layout') != b'ab-8gb-v1' or
                    fields.get(b'BOOT_ORDER') not in (b'A', b'B', b'A B', b'B A') or
                    fields.get(b'BOOT_A_LEFT') not in (b'0', b'1', b'2', b'3') or
                    fields.get(b'BOOT_B_LEFT') not in (b'0', b'1', b'2', b'3') or
                    b'sv08_reimage_arm' in fields):
                raise ValueError('Current boot environment is not a safe initial state')
        # The /proc/self/fd path binds fw_setenv to this opened descriptor.
        # Keep that process-local path off the persistent journal.
        with tempfile.TemporaryDirectory(prefix='sv08-fwenv-', dir='/run') as temporary:
            config = Path(temporary) / 'fw_env.config'
            changes = Path(temporary) / 'arm.env'
            config.write_text(''.join(f'/proc/self/fd/{fd} {offset:#x} {ENV_BYTES:#x}\n'
                                      for offset in ENV_OFFSETS))
            changes.write_text('BOOT_ORDER=A B\nBOOT_A_LEFT=0\nBOOT_B_LEFT=0\n'
                               f"sv08_reimage_arm={state['job_id']}\n")
            for index in range(2):
                if admitted_target(target, recovery, policy, host_sysfs=host_sysfs,
                                   synthetic_fixture=synthetic_fixture,
                                   require_writable=True) != admission:
                    raise ValueError('Target or recovery mount changed before environment write')
                subprocess.run(['fw_setenv', '-c', config, '-s', changes],
                               pass_fds=(fd,), check=True, capture_output=True, timeout=30)
                os.fsync(fd)
                state['phase'] = f'arm-copy-{index+1}-written'
                journal_state(journal, state)
                if fault == f'after-arm-copy-{index+1}':
                    return state
        for offset in ENV_OFFSETS:
            fields = parse_env_record(os.pread(fd, ENV_BYTES, offset))
            if any(fields.get(key) != value for key, value in (
                    (b'BOOT_ORDER', b'A B'), (b'BOOT_A_LEFT', b'0'),
                    (b'BOOT_B_LEFT', b'0'), (b'sv08_env_layout', b'ab-8gb-v1'),
                    (b'sv08_reimage_arm', state['job_id'].encode()))):
                raise ValueError('Redundant environment was not armed')
        if admitted_target(target, recovery, policy, host_sysfs=host_sysfs,
                           synthetic_fixture=synthetic_fixture,
                           require_writable=True) != admission:
            raise ValueError('Target or recovery mount changed after environment write')
        state['phase'] = 'armed-both-verified'
        journal_state(journal, state)
        return state
    finally:
        os.close(fd)


def activate_live_target(target: Path, recovery: Path, journal: Path, *,
                         target_policy: dict, artifact: Path, bundle: Path,
                         verification_key: Path, host_sysfs: Path = HOST_SYSFS,
                         synthetic_fixture: bool = False, now=None) -> dict:
    """Publish the one-shot marker only after a fresh signed and live check."""
    target, recovery, journal, artifact = map(Path, (target, recovery, journal, artifact))
    policy = policy_fields(target_policy)
    admission = admitted_target(target, recovery, policy,
                                host_sysfs=host_sysfs,
                                synthetic_fixture=synthetic_fixture,
                                require_writable=True)
    state = _stage_state(journal, admission, policy, phase='armed-both-verified')
    _verify_job(artifact, Path(bundle), Path(verification_key), policy,
                state['job_id'], now=now)
    return activate_mounted_recovery(
        recovery, artifact, journal, image=target, target_policy=policy,
        live_target=True, live_sysfs_root=host_sysfs,
        synthetic_live_fixture=synthetic_fixture)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation', choices=('inspect', 'stage', 'arm', 'activate'),
                        default='inspect')
    parser.add_argument('--policy', type=Path, required=True,
                        help='Private target policy JSON from the signed job')
    parser.add_argument('--recovery', type=Path, required=True,
                        help='Already-mounted writable partition-five directory')
    parser.add_argument('--artifact', type=Path)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--verification-key', type=Path)
    parser.add_argument('--journal', type=Path)
    parser.add_argument('--expected-build-sha256')
    parser.add_argument('--expected-original-sha256')
    parser.add_argument('--execute', action='store_true',
                        help='Explicitly apply one requested stage/arm/activate operation')
    args = parser.parse_args()
    policy_path = regular(args.policy)
    raw = policy_path.read_bytes()
    policy = policy_fields(json.loads(raw))
    if raw != canonical_json(policy):
        raise ValueError('Noncanonical target policy')
    if args.operation != 'inspect' and args.execute and (os.geteuid() != 0 or
            stat.S_IMODE(policy_path.stat().st_mode) != 0o600 or
            any(value is None for value in (args.artifact, args.bundle,
                                            args.verification_key, args.journal))):
        raise ValueError('Root, private 0600 policy, artifact, bundle, key and journal required')
    target = Path(policy['target_device'])
    result = admitted_target(target, args.recovery, policy,
                             require_writable=args.operation != 'inspect' and args.execute)
    public = {name: value for name, value in result.items() if name != 'cid'}
    public['cid_sha256'] = hashlib.sha256(result['cid'].encode()).hexdigest()
    if args.operation == 'inspect' or not args.execute:
        print(json.dumps({'operation': args.operation, 'execute': False,
                          'admission': public}, sort_keys=True))
        return
    if verify_artifact(args.artifact)['status'] != 'h12-attended-candidate':
        raise ValueError('Physical stage requires a separately reviewed H12 artifact')
    if args.operation == 'stage':
        if not args.expected_build_sha256 or not args.expected_original_sha256:
            raise ValueError('Both reviewed artifact and original-script hashes required')
        state = stage_mounted_recovery(
            args.recovery, args.artifact, args.journal,
            bundle=args.bundle, verification_key=args.verification_key,
            expected_build_sha256=args.expected_build_sha256,
            expected_original_sha256=args.expected_original_sha256,
            mounted_live_target=target)
    else:
        if (not args.expected_build_sha256 or
                digest(regular(args.artifact / 'build.json')) != args.expected_build_sha256):
            raise ValueError('Artifact differs from reviewed build')
        operation = arm_live_target if args.operation == 'arm' else activate_live_target
        state = operation(target, args.recovery, args.journal,
                          target_policy=policy, artifact=args.artifact,
                          bundle=args.bundle, verification_key=args.verification_key)
    print(json.dumps({'operation': args.operation, 'execute': True,
                      'phase': state['phase'], 'admission': public}, sort_keys=True))


if __name__ == '__main__':
    main()
