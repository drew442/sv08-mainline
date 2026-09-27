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

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from tests.host_qemu_sd_network_emmc_write import (
    IMAGE_BYTES, IMAGE_SHA256, SERIAL, create_synthetic_source, validate_source,
    create_target, admit_target, digest, inspect_gpt, expected_records,
    h616_synthetic_policy, synthetic_mmc_fixture, fresh_work, run)
from tests.sv08_emmc_job import canonical_json
from scripts.prepare_h616_reimage_job import prepare
from scripts.serve_h616_reimage_job import serve
from scripts.build_h616_reimage_candidate import build, TARGET_BYTES
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


def execute(work, sd_work, sd_dtb, packages, tamper_job):
    if os.geteuid() != 0:
        raise PermissionError('Isolated QEMU harness must run as root')
    work = fresh_work(work)
    source = work / 'source.img'
    if create_synthetic_source(source) != IMAGE_SHA256:
        raise ValueError('Synthetic source does not match pin')
    validate_source(source)
    target_fd = create_target(work / 'target.img', TARGET_BYTES)
    admit_target(work, target_fd, source, TARGET_BYTES)
    run(['mount', '--make-rprivate', '/'])
    run(['mount', '-t', 'tmpfs', 'tmpfs', '/run'])
    run(['ip', 'link', 'set', 'lo', 'up'])
    Path('/run/ganesha').mkdir()
    keys = REPO / 'tests/fixtures/sd-network-root/synthetic-keys'
    receipt_keys = REPO / 'tests/fixtures/sd-network-root/receipt-test-keys'
    with tempfile.TemporaryDirectory(dir=REPO / 'local') as tmp:
        private = Path(tmp)
        private.chmod(0o700)
        policy = private / 'policy.json'
        policy.write_bytes(canonical_json(h616_synthetic_policy()))
        policy.chmod(0o600)
        job_sign = copy_private(private, 'job-sign.pem', keys / 'test-signing-key.pem')
        job_verify = copy_private(private, 'job-verify.pem', keys / 'test-verification-key.pem')
        receipt_sign = copy_private(private, 'receipt-sign.pem', receipt_keys / 'test-signing-key.pem')
        receipt_verify = copy_private(private, 'receipt-verify.pem', receipt_keys / 'test-verification-key.pem')
        state = private / 'state'
        port = free_port()
        prepared = prepare(policy_path=policy, image_path=source, job_signing_key=job_sign,
                           job_verification_key=job_verify, receipt_signing_key=receipt_sign,
                           receipt_verification_key=receipt_verify, state_dir=state,
                           source_server='10.0.2.2', source_export='/srv/sv08-sd-nfs',
                           claim_port=port, valid_seconds=3600, execute=True,
                           synthetic_test=True)
        bundle = private / 'bundle'
        manifest = build(bundle, policy, job_verify, state / 'job.json', state / 'job.sig',
                         synthetic_test=True, trusted_initramfs=True,
                         receipt_verification_key_path=receipt_verify,
                         source_server='10.0.2.2', source_export='/srv/sv08-sd-nfs')
        synthetic_mmc_fixture(bundle, commissioning=True)
        if tamper_job:
            raw = (bundle / 'job.json').read_bytes().replace(
                prepared['job_id'].encode(), b'0' * len(prepared['job_id']), 1)
            (bundle / 'job.json').write_bytes(raw)
            manifest['job_sha256'] = hashlib.sha256(raw).hexdigest()
            (bundle / 'reimage-manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
        boot = work / 'boot'
        boot.mkdir()
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
            cmd = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a53',
                   '-smp', '2', '-m', '2048', '-kernel', boot / 'Image',
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
            marker = prefix + ('REFUSED_BUNDLE' if tamper_job else 'PASS')
            if marker not in serial or guest.returncode != 0:
                raise RuntimeError(f'Expected {marker}, guest rc {guest.returncode}; inspect {work / "serial.log"}')
            if tamper_job:
                if prefix + 'SOURCE_HASH_START' in serial or prefix + 'TARGET_OPEN_START' in serial:
                    raise RuntimeError('Tampered signed job reached source hash or target open')
                if (state / 'claim/claim.json').exists():
                    raise RuntimeError('Tampered job consumed claim')
                if (work / 'target.img').open('rb').read(1024 * 1024).strip(b'\0'):
                    raise RuntimeError('Tampered job changed target')
            else:
                if prefix + 'READBACK ' not in serial or not (state / 'claim/claim.json').exists():
                    raise RuntimeError('Success lacks readback or durable claim')
                if digest(work / 'target.img', IMAGE_BYTES) != IMAGE_SHA256:
                    raise RuntimeError('Host readback hash differs')
                if inspect_gpt(work / 'target.img')['partition_records'] != expected_records():
                    raise RuntimeError('Host GPT differs')
            result = {'case': 'tampered-signed-job' if tamper_job else 'full-success',
                      'marker': marker, 'source_sha256': IMAGE_SHA256,
                      'kernel_sha256': hashes['Image'], 'initramfs_sha256': hashes['initrd.img'],
                      'bundle_manifest_sha256': composition['bundle_manifest_sha256'],
                      'controller_state_sha256': digest(state / 'state.json'),
                      'claim_consumed': (state / 'claim/claim.json').exists(),
                      'target_sha256': digest(work / 'target.img', IMAGE_BYTES) if not tamper_job else None,
                      'synthetic_target_only': True, 'h616_boot_tested': False}
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
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        print('Inspection only: pass --execute inside a fresh isolated mount/network namespace')
        return
    execute(args.work, args.sd_work, args.sd_dtb, args.package_root, args.tamper_job)


if __name__ == '__main__':
    main()
