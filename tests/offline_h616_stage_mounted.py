#!/usr/bin/env python3
"""Stage and arm an identified disposable loop-backed recovery partition.

This is an offline integration exercise only. It accepts a fresh directory
under ignored local/, constructs its own sparse regular-file target, and has
no option for a block-device target or installed printer filesystem.
"""
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
from scripts.stage_h616_recovery_handoff import (arm_regular_image,
    stage_mounted_recovery, activate_mounted_recovery,
    admit_disposable_loop_recovery, parse_env_record)
from tests.test_h616_reimage_candidate import signed_inputs
from tests.test_h616_recovery_handoff_builder import base_initrd
from tests.test_recovery_handoff_stage import create_reviewed_target
from tests.host_qemu_trusted_writer_controller import extract_staged_fit

def run(*args):
    return subprocess.run([str(arg) for arg in args], check=True,
                          capture_output=True, text=True, timeout=120)


def execute(work):
    work = work.absolute()
    if (os.geteuid() != 0 or work.exists() or
            not work.is_relative_to(REPO / 'local') or
            any(path.is_symlink() for path in (work, *work.parents))):
        raise ValueError('Root and fresh non-symlink work under ignored local/ required')
    work.mkdir(mode=0o700)
    files, policy, job = signed_inputs(work)
    bundle = work / 'bundle'
    build_writer(bundle, *files.values(), now=1500, synthetic_test=True,
                 trusted_initramfs=True, recovery_handoff=True,
                 source_server='10.0.2.2', source_export='/srv/sv08-sd-nfs')
    kernel = work / 'Image'; kernel.write_bytes(b'K' * 4096)
    dtb = work / 'board.dtb'; dtb.write_bytes(b'D' * 512)
    artifact = work / 'handoff'
    build_handoff(artifact, kernel, base_initrd(work), dtb, bundle,
                  '10.0.2.2', '/srv/sv08-sd-nfs', 12345)
    target = work / 'target.img'
    create_reviewed_target(target, policy)
    with target.open('r+b') as stream:
        stream.truncate(policy['sectors'] * 512)
    initial = work / 'initial.env'
    initial.write_text('sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A B\n'
                       'BOOT_A_LEFT=3\nBOOT_B_LEFT=0\n')
    record = work / 'initial.bin'
    run('mkenvimage', '-r', '-s', '65536', '-o', record, initial)
    with target.open('r+b') as stream:
        for offset in (0x400000, 0x800000):
            os.pwrite(stream.fileno(), record.read_bytes(), offset)
        os.fsync(stream.fileno())
    recovery_part = policy['image_layout']['partitions'][4]
    loop = run('losetup', '--find', '--show',
               '--offset', recovery_part['offset_bytes'],
               '--sizelimit', recovery_part['size_bytes'], target).stdout.strip()
    mounted = False
    recovery = work / 'recovery-mounted'
    recovery.mkdir()
    try:
        admit_disposable_loop_recovery(target, recovery, policy)
    except ValueError:
        pass
    else:
        raise RuntimeError('Unmounted recovery was admitted')
    try:
        run('mkfs.ext4', '-q', '-F', loop)
        run('mount', '-t', 'ext4', '-o', 'rw', loop, recovery)
        mounted = True
        alias = work / 'wrong-target-alias.img'
        os.link(target, alias)
        try:
            admit_disposable_loop_recovery(alias, recovery, policy)
        except ValueError:
            pass
        else:
            raise RuntimeError('Unreviewed recovery backing path was admitted')
        alias.unlink()
        (recovery / 'recovery.scr').write_bytes(b'ORIGINAL-UI')
        os.sync()
        journal = work / 'journal'
        state = stage_mounted_recovery(
            recovery, artifact, journal, bundle=bundle,
            verification_key=files['key'],
            expected_build_sha256=hashlib.sha256((artifact / 'build.json').read_bytes()).hexdigest(),
            expected_original_sha256=hashlib.sha256(b'ORIGINAL-UI').hexdigest(),
            mounted_target_image=target, now=1500)
        if (state['phase'] != 'wrapper-durable' or
                state['recovery_admission']['recovery_partuuid'] != recovery_part['partuuid'] or
                (recovery / 'sv08-reimage/armed').exists()):
            raise RuntimeError('Mounted recovery stage did not pass')
        run('umount', recovery)
        mounted = False
    finally:
        if mounted:
            run('umount', recovery)
        run('losetup', '-d', loop)
    with target.open('rb') as stream:
        for offset in (0x400000, 0x800000):
            fields = parse_env_record(os.pread(stream.fileno(), 65536, offset))
            if (fields.get(b'BOOT_A_LEFT') != b'3' or
                    fields.get(b'BOOT_B_LEFT') != b'0' or
                    b'sv08_reimage_arm' in fields):
                raise RuntimeError('File staging altered the normal slot policy')
    armed = arm_regular_image(target, work / 'journal', target_policy=policy)
    if armed['phase'] != 'armed-both-verified':
        raise RuntimeError('Redundant environment was not armed')
    loop = run('losetup', '--find', '--show',
               '--offset', recovery_part['offset_bytes'],
               '--sizelimit', recovery_part['size_bytes'], target).stdout.strip()
    try:
        run('mount', '-t', 'ext4', '-o', 'rw', loop, recovery)
        try:
            activated = activate_mounted_recovery(
                recovery, artifact, work / 'journal', image=target,
                target_policy=policy)
        finally:
            run('umount', recovery)
    finally:
        run('losetup', '-d', loop)
    if activated['phase'] != 'marker-durable':
        raise RuntimeError('Recovery marker was not durably activated')
    with target.open('rb') as stream:
        for offset in (0x400000, 0x800000):
            fields = parse_env_record(os.pread(stream.fileno(), 65536, offset))
            if (fields.get(b'sv08_reimage_arm') != job['job_id'].encode() or
                    fields.get(b'BOOT_A_LEFT') != b'0' or
                    fields.get(b'BOOT_B_LEFT') != b'0'):
                raise RuntimeError('Final environment disagrees with signed job')
    extracted = work / 'fit-extracted'
    extracted.mkdir()
    extract_staged_fit(work, extracted,
                       json.loads((artifact / 'build.json').read_text()))
    result = {'status': 'PASS', 'synthetic_target_only': True,
              'target_is_regular_file': True, 'image_bytes': policy['image_bytes'],
              'target_bytes': policy['sectors'] * 512,
              'unmounted_or_wrong_backing_refused': True,
              'recovery_partuuid': recovery_part['partuuid'],
              'staged_phase': state['phase'], 'arm_phase': armed['phase'],
              'activation_phase': activated['phase'],
              'fit_sha256': state['fit_sha256'],
              'prearm_normal_slot_policy_retained': True,
              'staged_fit_components_verified': True}
    (work / 'result.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({'execute': False, 'work': str(args.work.absolute())}))
        return
    execute(args.work)


if __name__ == '__main__':
    main()
