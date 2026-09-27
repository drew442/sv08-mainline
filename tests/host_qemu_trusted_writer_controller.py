#!/usr/bin/env python3
"""Run the actual one-shot host controller against a synthetic QEMU eMMC.

Root-only, isolated mount/network namespace, disposable regular-file target only.
The H616 SD kernel is executed on QEMU virt; this does not validate H616 boot.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import zlib

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from tests.host_qemu_sd_network_emmc_write import (
    IMAGE_BYTES, IMAGE_SHA256, SERIAL, create_synthetic_source, validate_source,
    create_target, admit_target, digest, inspect_gpt, expected_records,
    h616_synthetic_policy, synthetic_mmc_fixture, fresh_work, run)
from tests.sv08_emmc_job import canonical_json
from scripts.prepare_h616_reimage_job import prepare
from scripts.serve_h616_reimage_job import serve
from scripts.build_h616_reimage_candidate import (build, TARGET_BYTES,
                                                  V5_IMAGE_SHA256, V5_IMAGE_PARTITIONS)
from scripts.stage_h616_recovery_handoff import parse_env_record
from scripts.stage_h616_recovery_handoff import stage_mounted_recovery, arm_regular_image
from scripts.build_h616_recovery_handoff import build as build_recovery_handoff
from scripts.build_sd_network_image import commissioning_bundle, append_commissioning_initramfs, boot_script


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def copy_private(private, name, source):
    dest = private / name
    dest.write_bytes(source.read_bytes())
    dest.chmod(0o600)
    return dest


def wait_controller(thread, errors, port):
    for _ in range(150):
        if errors or not thread.is_alive():
            raise RuntimeError(f'Controller exited before ready: {errors}')
        try:
            with socket.create_connection(('127.0.0.1', 2049), timeout=.2), \
                 socket.create_connection(('127.0.0.1', port), timeout=.2):
                return
        except OSError:
            time.sleep(.2)
    raise TimeoutError('Actual controller did not become ready')


def seed_recovery_handoff_target(work, target_fd, installed_image):
    """Seed only the disposable QEMU target with reviewed v5 recovery media."""
    installed_image = installed_image.resolve(strict=True)
    if (not installed_image.is_file() or installed_image.stat().st_size != IMAGE_BYTES or
            digest(installed_image) != V5_IMAGE_SHA256):
        raise ValueError('Recovery handoff requires exact v5 regular-file source')
    target = work / 'target.img'
    _, recovery_guid, offset, length = V5_IMAGE_PARTITIONS[4]
    # The guest needs the exact boot metadata and recovery filesystem, not
    # another 8 GB allocation of unused installed-OS contents. Keep the target
    # sparse while still hashing the entire identified v5 input above.
    ranges = ((0, 16 * 1024 * 1024), (offset, length),
              (IMAGE_BYTES - 1024 * 1024, 1024 * 1024))
    with installed_image.open('rb') as source:
        for start, size in ranges:
            for position in range(start, start + size, 8 * 1024 * 1024):
                block = os.pread(source.fileno(), min(8 * 1024 * 1024,
                                                     start + size - position), position)
                if not block or os.pwrite(target_fd, block, position) != len(block):
                    raise ValueError('Short recovery seed copy')
    os.fsync(target_fd)
    if os.fstat(target_fd).st_size != TARGET_BYTES:
        raise ValueError('Target capacity changed during initial-image seed')
    return {'initial_image_sha256': V5_IMAGE_SHA256,
            'recovery_partuuid': recovery_guid, 'copied_ranges': ranges}


def stage_recovery_handoff(work, target_fd, seed, artifact, bundle, job_verify,
                           policy_value):
    """Use the same checked, journaled stager on the disposable loop mount."""
    target = work / 'target.img'
    _, _, offset, length = V5_IMAGE_PARTITIONS[4]
    mountpoint = work / 'recovery-mounted'
    mountpoint.mkdir()
    run(['mount', '-t', 'ext4', '-o', f'loop,offset={offset},sizelimit={length}',
         target, mountpoint])
    try:
        original_hash = digest(mountpoint / 'recovery.scr')
        journal = work / 'stage-journal'
        staged = stage_mounted_recovery(
            mountpoint, artifact, journal, bundle=bundle,
            verification_key=job_verify,
            expected_build_sha256=digest(artifact / 'build.json'),
            expected_original_sha256=original_hash,
            mounted_target_image=target)
    finally:
        run(['umount', mountpoint])
    armed = arm_regular_image(target, journal, target_policy=policy_value)
    if armed['phase'] != 'armed-both-verified':
        raise ValueError('Disposable recovery policy was not fully armed')
    for env_offset in (0x400000, 0x800000):
        bank = parse_env_record(os.pread(target_fd, 65536, env_offset))
        for key, value in ((b'BOOT_ORDER', b'A B'), (b'BOOT_A_LEFT', b'0'),
                           (b'BOOT_B_LEFT', b'0'),
                           (b'sv08_reimage_arm', staged['job_id'].encode())):
            if bank.get(key) != value:
                raise ValueError('Disposable recovery arm differs from staged job')
    return {**seed, 'arm_job_id': staged['job_id'],
            'stage_phase': staged['phase'], 'arm_phase': armed['phase'],
            'build_sha256': staged['build_sha256'],
            'original_recovery_sha256': original_hash}


def recovery_marker_present(work):
    _, _, offset, length = V5_IMAGE_PARTITIONS[4]
    mountpoint = work / 'recovery-check'
    mountpoint.mkdir()
    run(['mount', '-t', 'ext4', '-o', f'loop,ro,noload,offset={offset},sizelimit={length}',
         work / 'target.img', mountpoint])
    try:
        return (mountpoint / 'sv08-reimage/armed').exists()
    finally:
        run(['umount', mountpoint])


def execute(work, sd_work, sd_dtb, packages, tamper_job,
            *, recovery_handoff=False, installed_image=None,
            use_installed_source=False, fault=None):
    if os.geteuid() != 0:
        raise PermissionError('Isolated QEMU harness must run as root')
    if fault not in (None, 'after-bulk', 'after-first-env') or (fault and (tamper_job or not recovery_handoff)):
        raise ValueError('Environment-last fault requires an untampered recovery handoff')
    work = fresh_work(work)
    if use_installed_source:
        if not recovery_handoff or installed_image is None:
            raise ValueError('Installed source requires recovery handoff')
        source = installed_image.resolve(strict=True)
        if (not source.is_file() or source.stat().st_size != IMAGE_BYTES or
                digest(source) != V5_IMAGE_SHA256):
            raise ValueError('Installed source is not exact reviewed v5 image')
        source_hash = V5_IMAGE_SHA256
    else:
        source = work / 'source.img'
        if create_synthetic_source(source) != IMAGE_SHA256:
            raise ValueError('Synthetic source does not match pin')
        validate_source(source)
        source_hash = IMAGE_SHA256
    policy_value = h616_synthetic_policy(source_hash)
    if (inspect_gpt(source, policy_value['image_layout']['disk_guid'])['partition_records'] !=
            policy_value['image_layout']['partitions']):
        raise ValueError('QEMU source GPT differs from reviewed image map')
    target_fd = create_target(work / 'target.img', TARGET_BYTES)
    admit_target(work, target_fd, source, TARGET_BYTES,
                 allow_external_source=use_installed_source)
    run(['mount', '--make-rprivate', '/'])
    run(['mount', '-t', 'tmpfs', 'tmpfs', '/run'])
    run(['ip', 'link', 'set', 'lo', 'up'])
    if recovery_handoff and installed_image is None:
        raise ValueError('Recovery handoff requires an exact initial image')
    Path('/run/ganesha').mkdir()
    keys = REPO / 'tests/fixtures/sd-network-root/synthetic-keys'
    receipt_keys = REPO / 'tests/fixtures/sd-network-root/receipt-test-keys'
    with tempfile.TemporaryDirectory(dir=REPO / 'local') as tmp:
        private = Path(tmp)
        private.chmod(0o700)
        policy = private / 'policy.json'
        policy.write_bytes(canonical_json(policy_value))
        policy.chmod(0o600)
        job_sign = copy_private(private, 'job-sign.pem', keys / 'test-signing-key.pem')
        job_verify = copy_private(private, 'job-verify.pem', keys / 'test-verification-key.pem')
        receipt_sign = copy_private(private, 'receipt-sign.pem', receipt_keys / 'test-signing-key.pem')
        receipt_verify = copy_private(private, 'receipt-verify.pem', receipt_keys / 'test-verification-key.pem')
        state = private / 'state'
        port = free_port()
        # Full-device hashing and readback under software-emulated ARM can take
        # much longer than a physical transfer; this window is synthetic only.
        prepared = prepare(policy_path=policy, image_path=source, job_signing_key=job_sign,
                           job_verification_key=job_verify, receipt_signing_key=receipt_sign,
                           receipt_verification_key=receipt_verify, state_dir=state,
                           source_server='10.0.2.2', source_export='/srv/sv08-sd-nfs',
                           claim_port=port, valid_seconds=7200, execute=True,
                           synthetic_test=True)
        seed = (seed_recovery_handoff_target(work, target_fd, installed_image)
                  if recovery_handoff else None)
        initial_prefix = os.pread(target_fd, 1024 * 1024, 0)
        bundle = private / 'bundle'
        manifest = build(bundle, policy, job_verify, state / 'job.json', state / 'job.sig',
                         synthetic_test=True, trusted_initramfs=True,
                         receipt_verification_key_path=receipt_verify,
                         source_server='10.0.2.2', source_export='/srv/sv08-sd-nfs',
                         recovery_handoff=recovery_handoff, fault=fault)
        synthetic_mmc_fixture(bundle, commissioning=True)
        boot = work / 'boot'
        boot.mkdir()
        if recovery_handoff:
            artifact = private / 'handoff'
            build_recovery_handoff(artifact, sd_work / 'boot/Image',
                                   sd_work / 'boot/initrd.img', sd_dtb, bundle,
                                   '10.0.2.2', '/srv/sv08-sd-nfs', port)
            staged = stage_recovery_handoff(work, target_fd, seed, artifact,
                                             bundle, job_verify, policy_value)
        else:
            staged = None
        if tamper_job:
            raw = (bundle / 'job.json').read_bytes().replace(
                prepared['job_id'].encode(), b'0' * len(prepared['job_id']), 1)
            (bundle / 'job.json').write_bytes(raw)
            manifest['job_sha256'] = hashlib.sha256(raw).hexdigest()
            (bundle / 'reimage-manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
        if recovery_handoff and not tamper_job:
            shutil.copyfile(artifact / 'Image', boot / 'Image')
            shutil.copyfile(artifact / 'writer-initrd.img', boot / 'initrd.img')
            shutil.copyfile(artifact / 'sv08.dtb', boot / 'sv08.dtb')
            composition = json.loads((artifact / 'build.json').read_text())['composition']
        else:
            shutil.copyfile(sd_work / 'boot/Image', boot / 'Image')
            shutil.copyfile(sd_work / 'boot/initrd.img', boot / 'initrd.img')
            shutil.copyfile(sd_dtb, boot / 'sv08.dtb')
            composition = append_commissioning_initramfs(
                boot / 'initrd.img', commissioning_bundle(bundle, '10.0.2.2', '/srv/sv08-sd-nfs'),
                '10.0.2.2', '/srv/sv08-sd-nfs', work)
        hashes = {name: digest(boot / name) for name in ('Image', 'initrd.img', 'sv08.dtb')}
        bootcmd = boot_script('10.0.2.2', '/srv/sv08-sd-nfs', hashes, claim_port=port)
        (work / 'boot.cmd').write_text(bootcmd)
        kernel_args = re.search(r'^setenv bootargs "([^"]+)"$', bootcmd, re.M).group(1)
        if recovery_handoff and not tamper_job:
            kernel_args = json.loads((artifact / 'build.json').read_text())['bootargs']
        elif recovery_handoff:
            kernel_args += ' sv08.h616_recovery_handoff=1'
        stop = threading.Event()
        errors = []
        def run_controller():
            try:
                serve(state_dir=state, image=source, job_verification_key=job_verify,
                      receipt_signing_key=receipt_sign, export_dir=work / 'export',
                      printer_ip='127.0.0.1', rpcbind=packages / 'sbin/rpcbind',
                      ganesha=packages / 'usr/bin/ganesha.nfsd', execute=True,
                      synthetic_package_root=packages, stop_event=stop)
            except BaseException as error:
                if (state / 'ganesha.log').exists():
                    shutil.copyfile(state / 'ganesha.log', work / 'ganesha.log')
                if (state / 'ganesha.conf').exists():
                    shutil.copyfile(state / 'ganesha.conf', work / 'ganesha.conf')
                errors.append(repr(error))
        controller = threading.Thread(target=run_controller, daemon=True)
        controller.start()
        try:
            wait_controller(controller, errors, port)
            guest_memory_mb = 1024 if use_installed_source else 2048
            cmd = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a53',
                   '-smp', '2', '-m', str(guest_memory_mb), '-kernel', boot / 'Image',
                   '-initrd', boot / 'initrd.img', '-append', kernel_args,
                   '-display', 'none', '-serial', 'null', '-no-reboot',
                   '-device', 'qemu-xhci,id=xhci', '-device', 'usb-net,netdev=n0',
                   '-netdev', 'user,id=n0', '-drive',
                   f'file=/proc/self/fd/{target_fd},if=none,id=target,format=raw,cache=none,discard=unmap,detect-zeroes=unmap',
                   '-device', f'usb-storage,drive=target,serial={SERIAL}',
                   '-chardev', f'file,id=serial,path={work / "serial.log"}',
                   '-device', 'pci-serial,chardev=serial']
            with (work / 'qemu.log').open('w') as log:
                guest = subprocess.Popen([str(x) for x in cmd], pass_fds=(target_fd,),
                                         stdout=log, stderr=subprocess.STDOUT)
                try:
                    guest.wait(timeout=4500 if not tamper_job else 300)
                except subprocess.TimeoutExpired:
                    guest.kill(); guest.wait()
                    raise TimeoutError('Guest did not reach terminal marker')
            serial = (work / 'serial.log').read_text(errors='replace')
            prefix = 'SV08_H616_COMMISSIONING_'
            expected_status = ({'after-bulk': 'INJECTED_AFTER_BULK',
                                'after-first-env': 'INJECTED_AFTER_FIRST_ENV'}[fault]
                               if fault else 'REFUSED_BUNDLE' if tamper_job else 'PASS')
            marker = prefix + expected_status
            if marker not in serial or guest.returncode != 0:
                raise RuntimeError(f'Expected {marker}, guest rc {guest.returncode}; inspect {work / "serial.log"}')
            if tamper_job:
                if prefix + 'SOURCE_HASH_START' in serial or prefix + 'TARGET_OPEN_START' in serial:
                    raise RuntimeError('Tampered signed job reached source hash or target open')
                if (state / 'claim/claim.json').exists():
                    raise RuntimeError('Tampered job consumed claim')
                if os.pread(target_fd, 1024 * 1024, 0) != initial_prefix:
                    raise RuntimeError('Tampered job changed target')
                if recovery_handoff and recovery_marker_present(work):
                    raise RuntimeError('Early refusal left a bootable writer marker')
            elif fault:
                if not (state / 'claim/claim.json').exists() or not recovery_handoff:
                    raise RuntimeError('Fault did not consume the one-shot claim')
                if recovery_marker_present(work):
                    raise RuntimeError('Postopen fault left a writer marker')
                banks = [parse_env_record(os.pread(target_fd, 65536, offset))
                         for offset in (0x400000, 0x800000)]
                if fault == 'after-bulk':
                    for bank in banks:
                        if (bank.get(b'BOOT_A_LEFT') != b'0' or
                                bank.get(b'BOOT_B_LEFT') != b'0' or
                                bank.get(b'sv08_reimage_arm') != staged['arm_job_id'].encode()):
                            raise RuntimeError('Bulk interruption changed armed boot policy')
                else:
                    if (banks[1].get(b'BOOT_A_LEFT') != b'0' or
                            banks[1].get(b'BOOT_B_LEFT') != b'0' or
                            banks[1].get(b'sv08_reimage_arm') != staged['arm_job_id'].encode()):
                        raise RuntimeError('First-env interruption changed second record')
                prefix_before_retry = os.pread(target_fd, 1024 * 1024, 0)
                retry_cmd = cmd.copy()
                retry_cmd[-3] = f'file,id=serial,path={work / "serial-retry.log"}'
                with (work / 'qemu-retry.log').open('w') as log:
                    retry = subprocess.run([str(x) for x in retry_cmd],
                                           pass_fds=(target_fd,), stdout=log,
                                           stderr=subprocess.STDOUT, timeout=300)
                retry_serial = (work / 'serial-retry.log').read_text(errors='replace')
                if (retry.returncode != 0 or
                        prefix + 'REFUSED_RECOVERY_MARKER' not in retry_serial or
                        prefix + 'TARGET_OPEN_START' in retry_serial or
                        os.pread(target_fd, 1024 * 1024, 0) != prefix_before_retry):
                    raise RuntimeError('Postopen interruption retried or changed target')
            else:
                if prefix + 'READBACK ' not in serial or not (state / 'claim/claim.json').exists():
                    raise RuntimeError('Success lacks readback or durable claim')
                if digest(work / 'target.img', IMAGE_BYTES) != source_hash:
                    raise RuntimeError('Host readback hash differs')
                if (inspect_gpt(work / 'target.img', policy_value['image_layout']['disk_guid'])
                        ['partition_records'] != policy_value['image_layout']['partitions']):
                    raise RuntimeError('Host GPT differs')
            normal_policy = None
            if use_installed_source and not tamper_job:
                banks = [parse_env_record(os.pread(target_fd, 65536, offset))
                         for offset in (0x400000, 0x800000)]
                for bank in banks:
                    if (bank.get(b'sv08_env_layout') != b'ab-8gb-v1' or
                            bank.get(b'BOOT_ORDER') != b'A' or
                            bank.get(b'BOOT_A_LEFT') != b'3' or
                            bank.get(b'BOOT_B_LEFT') != b'0' or
                            b'sv08_reimage_arm' in bank):
                        raise RuntimeError('Replacement did not restore normal A boot policy')
                normal_policy = {'order': 'A', 'a_attempts': 3,
                                 'b_attempts': 0, 'both_copies_valid': True,
                                 'arm_token_absent': True,
                                 'normal_os_boot_tested': False}
            result = {'case': 'tampered-signed-job' if tamper_job else
                              'postopen-' + fault if fault else 'full-success',
                      'marker': marker, 'source_sha256': source_hash,
                      'kernel_sha256': hashes['Image'], 'initramfs_sha256': hashes['initrd.img'],
                      'bundle_manifest_sha256': composition['bundle_manifest_sha256'],
                      'controller_state_sha256': digest(state / 'state.json'),
                      'claim_consumed': (state / 'claim/claim.json').exists(),
                      'target_sha256': digest(work / 'target.img', IMAGE_BYTES) if not tamper_job else None,
                      'synthetic_target_only': True, 'h616_boot_tested': False,
                      'recovery_handoff': recovery_handoff,
                      'installed_source_as_replacement': use_installed_source,
                      'guest_memory_mb': guest_memory_mb,
                      'normal_policy': normal_policy,
                      'staged': staged}
            if fault:
                result['retry_marker'] = prefix + 'REFUSED_RECOVERY_MARKER'
                result['retry_serial_sha256'] = digest(work / 'serial-retry.log')
            (work / 'result.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
            print(json.dumps(result, sort_keys=True), flush=True)
        finally:
            stop.set()
            controller.join(timeout=15)
            os.close(target_fd)
            if controller.is_alive() or errors:
                raise RuntimeError(f'Controller did not finish cleanly: {errors}')
            terminal = json.loads((state / 'serve-terminal.json').read_text())
            expected = 'stopped-unclaimed' if tamper_job else 'claim-consumed'
            if terminal['status'] != expected:
                raise RuntimeError(f'Wrong controller terminal state: {terminal}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--sd-work', type=Path, required=True)
    parser.add_argument('--sd-dtb', type=Path, required=True)
    parser.add_argument('--package-root', type=Path, required=True)
    parser.add_argument('--tamper-job', action='store_true')
    parser.add_argument('--recovery-handoff', action='store_true')
    parser.add_argument('--installed-image', type=Path)
    parser.add_argument('--use-installed-source', action='store_true')
    parser.add_argument('--fault', choices=('after-bulk', 'after-first-env'))
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        print('Inspection only: pass --execute inside a fresh isolated mount/network namespace')
        return
    execute(args.work, args.sd_work, args.sd_dtb, args.package_root, args.tamper_job,
            recovery_handoff=args.recovery_handoff, installed_image=args.installed_image,
            use_installed_source=args.use_installed_source, fault=args.fault)


if __name__ == '__main__':
    main()
