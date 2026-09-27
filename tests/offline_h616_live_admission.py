#!/usr/bin/env python3
"""Exercise read-only live-style admission on disposable loop block devices."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.build_h616_reimage_candidate import build as build_writer
from scripts.build_h616_recovery_handoff import build as build_handoff
from scripts.live_h616_recovery_stage import (
    admitted_target, arm_live_target, activate_live_target)
from scripts.stage_h616_recovery_handoff import parse_env_record, stage_mounted_recovery
from tests.sv08_emmc_job import canonical_json
from tests.test_h616_reimage_candidate import signed_inputs, synthetic_job
from tests.test_h616_recovery_handoff_builder import base_initrd
from tests.test_recovery_handoff_stage import create_reviewed_target


def run(*args):
    return subprocess.run([str(arg) for arg in args], check=True,
                          capture_output=True, text=True, timeout=120).stdout.strip()


def device_number(path):
    info = path.stat()
    return f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}'


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(value) + '\n')


def refuse(label, call):
    try:
        call()
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError):
        return label
    raise AssertionError(f'Unsafe {label} was admitted')


def execute(work, fault=None):
    work = work.absolute()
    if (os.geteuid() != 0 or work.exists() or
            not work.is_relative_to(REPO / 'local') or
            any(path.is_symlink() for path in (work, *work.parents))):
        raise ValueError('Root and fresh non-symlink work under ignored local/ required')
    work.mkdir(mode=0o700)
    files, policy, _ = signed_inputs(work)
    target = work / 'target.img'
    create_reviewed_target(target, policy)
    with target.open('r+b') as stream:
        stream.truncate(policy['sectors'] * 512)
    part = policy['image_layout']['partitions'][4]
    whole = Path(run('losetup', '--find', '--show', target))
    recovery_loop = None
    mounted = False
    recovery = work / 'recovery-mounted'
    recovery.mkdir()
    try:
        recovery_loop = Path(run('losetup', '--find', '--show', '--offset',
                                 part['offset_bytes'], '--sizelimit',
                                 part['size_bytes'], target))
        run('mkfs.ext4', '-q', '-F', recovery_loop)
        run('mount', '-t', 'ext4', '-o', 'rw', recovery_loop, recovery)
        mounted = True
        policy = dict(policy, dev_t=device_number(whole))
        files['policy'].write_bytes(canonical_json(policy))
        job = synthetic_job(policy)
        files['job'].write_bytes(canonical_json(job))
        run('openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', work / 'signer.pem',
            '-in', files['job'], '-out', files['signature'])
        host_sysfs = work / 'sys/bus/platform/devices/4022000.mmc/mmc_host'
        card = host_sysfs / 'mmc7/mmc7:0001'
        block = card / 'block/mmcblk0'
        p5 = block / 'mmcblk0p5'
        put(card / 'type', 'MMC')
        put(card / 'cid', policy['cid'])
        put(block / 'size', policy['sectors'])
        put(block / 'dev', device_number(whole))
        put(p5 / 'dev', device_number(recovery_loop))
        put(p5 / 'uevent', 'PARTUUID=' + part['partuuid'])
        call = lambda: admitted_target(whole, recovery, policy,
                                       host_sysfs=host_sysfs,
                                       synthetic_fixture=True)
        admitted = call()
        cases = []
        cases.append(refuse('source-overlaps-target-host',
                            lambda: admitted_target(
                                whole, recovery, policy, host_sysfs=host_sysfs,
                                synthetic_fixture=True,
                                local_addresses={policy['claim_server']})))
        put(card / 'cid', 'f' * 32)
        cases.append(refuse('wrong-cid', call))
        put(card / 'cid', policy['cid'])
        put(card / 'type', 'SD')
        cases.append(refuse('wrong-type', call))
        put(card / 'type', 'MMC')
        put(block / 'size', policy['sectors'] - 1)
        cases.append(refuse('wrong-capacity', call))
        put(block / 'size', policy['sectors'])
        put(block / 'dev', '1:1')
        cases.append(refuse('wrong-dev-t', call))
        put(block / 'dev', device_number(whole))
        put(p5 / 'dev', '1:2')
        cases.append(refuse('wrong-mount-source', call))
        put(p5 / 'dev', device_number(recovery_loop))
        put(p5 / 'uevent', 'PARTUUID=' + '0' * 36)
        cases.append(refuse('wrong-partuuid', call))
        put(p5 / 'uevent', 'PARTUUID=' + part['partuuid'])
        extra = host_sysfs / 'mmc8/mmc8:0001'
        put(extra / 'type', 'MMC')
        cases.append(refuse('ambiguous-card', call))
        (extra / 'type').unlink(); extra.rmdir(); extra.parent.rmdir()
        with target.open('r+b') as stream:
            original = os.pread(stream.fileno(), 1, 512 + 56)
            os.pwrite(stream.fileno(), bytes([original[0] ^ 1]), 512 + 56)
            stream.flush(); os.fsync(stream.fileno())
        cases.append(refuse('wrong-gpt-crc', call))
        with target.open('r+b') as stream:
            os.pwrite(stream.fileno(), original, 512 + 56)
            stream.flush(); os.fsync(stream.fileno())
        assert call() == admitted
        initial = work / 'initial.env'
        initial.write_text('sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A B\n'
                           'BOOT_A_LEFT=3\nBOOT_B_LEFT=0\n')
        env = work / 'initial.bin'
        run('mkenvimage', '-r', '-s', '65536', '-o', env, initial)
        with target.open('r+b') as stream:
            for offset in (0x400000, 0x800000):
                os.pwrite(stream.fileno(), env.read_bytes(), offset)
            os.fsync(stream.fileno())
        (recovery / 'recovery.scr').write_bytes(b'ORIGINAL-UI')
        os.sync()
        bundle = work / 'bundle'
        build_writer(bundle, *files.values(), now=1500, synthetic_test=True,
                     trusted_initramfs=True, recovery_handoff=True,
                     source_server='10.0.2.2', source_export='/srv/sv08-sd-nfs')
        kernel = work / 'Image'; kernel.write_bytes(b'K' * 4096)
        dtb = work / 'board.dtb'; dtb.write_bytes(b'D' * 512)
        artifact = work / 'handoff'
        build_handoff(artifact, kernel, base_initrd(work), dtb, bundle,
                      '10.0.2.2', '/srv/sv08-sd-nfs', 12345)
        journal = work / 'journal'
        staged = stage_mounted_recovery(
            recovery, artifact, journal, bundle=bundle,
            verification_key=files['key'], now=1500,
            expected_build_sha256=hashlib.sha256((artifact / 'build.json').read_bytes()).hexdigest(),
            expected_original_sha256=hashlib.sha256(b'ORIGINAL-UI').hexdigest(),
            mounted_live_target=whole, live_sysfs_root=host_sysfs,
            synthetic_live_fixture=True,
            fault=fault if fault in ('after-original', 'after-fit', 'after-wrapper') else None)
        if (recovery / 'sv08-reimage/armed').exists():
            raise AssertionError('File stage published writer marker early')
        armed = None
        activated = None
        if fault not in ('after-original', 'after-fit', 'after-wrapper'):
            if staged['phase'] != 'wrapper-durable':
                raise AssertionError('Live-style stage did not complete')
            armed = arm_live_target(
                whole, recovery, journal, target_policy=policy,
                artifact=artifact, bundle=bundle, verification_key=files['key'],
                host_sysfs=host_sysfs, synthetic_fixture=True, now=1500,
                fault=fault)
            if (recovery / 'sv08-reimage/armed').exists():
                raise AssertionError('Live-style arm published writer marker early')
            if fault:
                refuse('activation-after-' + fault,
                       lambda: activate_live_target(
                           whole, recovery, journal, target_policy=policy,
                           artifact=artifact, bundle=bundle,
                           verification_key=files['key'], host_sysfs=host_sysfs,
                           synthetic_fixture=True, now=1500))
                refuse('automatic-rearm-after-' + fault,
                       lambda: arm_live_target(
                           whole, recovery, journal, target_policy=policy,
                           artifact=artifact, bundle=bundle,
                           verification_key=files['key'], host_sysfs=host_sysfs,
                           synthetic_fixture=True, now=1500))
            else:
                if armed['phase'] != 'armed-both-verified':
                    raise AssertionError('Both environment records were not verified')
                activated = activate_live_target(
                    whole, recovery, journal, target_policy=policy,
                    artifact=artifact, bundle=bundle,
                    verification_key=files['key'], host_sysfs=host_sysfs,
                    synthetic_fixture=True, now=1500)
                if activated['phase'] != 'marker-durable':
                    raise AssertionError('Live-style activation did not publish marker')
        with target.open('rb') as stream:
            banks = [parse_env_record(os.pread(stream.fileno(), 65536, offset))
                     for offset in (0x400000, 0x800000)]
        if fault in ('after-original', 'after-fit', 'after-wrapper'):
            if any(bank.get(b'BOOT_A_LEFT') != b'3' or b'sv08_reimage_arm' in bank
                   for bank in banks):
                raise AssertionError('File-stage fault changed initial boot policy')
        elif fault:
            if (sum(bank.get(b'sv08_reimage_arm') == job['job_id'].encode()
                    for bank in banks) != (1 if fault == 'after-arm-copy-1' else 2)):
                raise AssertionError('Arm fault changed wrong number of environment records')
        run('umount', recovery)
        mounted = False
        cases.append(refuse('unmounted-recovery', call))
        run('mount', '-t', 'ext4', '-o', 'ro,noload', recovery_loop, recovery)
        mounted = True
        ro = call()
        if ro['recovery_mount_mode'] != 'ro':
            raise AssertionError('Read-only recovery mount not reported')
        cases.append(refuse('read-only-mount-for-write',
                            lambda: admitted_target(
                                whole, recovery, policy, host_sysfs=host_sysfs,
                                synthetic_fixture=True, require_writable=True)))
        run('umount', recovery)
        mounted = False
        result = {'status': 'PASS', 'synthetic_loop_only': True, 'fault': fault,
                  'opened_target_is_block': True, 'admission': admitted,
                  'refusals': cases, 'stage_phase': staged['phase'],
                  'arm_phase': armed['phase'] if armed else None,
                  'activation_phase': activated['phase'] if activated else None,
                  'marker_present': activated is not None,
                  'read_only_probe_passed': True,
                  'physical_eMMC_tested': False}
        (work / 'result.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
        print(json.dumps(result, sort_keys=True))
    finally:
        if mounted:
            run('umount', recovery)
        if recovery_loop:
            run('losetup', '-d', recovery_loop)
        run('losetup', '-d', whole)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--fault', choices=('after-original', 'after-fit',
                                            'after-wrapper', 'after-arm-copy-1',
                                            'after-arm-copy-2'))
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({'execute': False, 'work': str(args.work.absolute())}))
        return
    execute(args.work, args.fault)


if __name__ == '__main__':
    main()
