#!/usr/bin/env python3
"""Run signed-feed, real RAUC slot writes, trial health and fallback in QEMU.

The only writable targets are fresh regular-file disks under build/ or an
explicitly named direct child of /dev/shm. Feed transport is injected from a
read-only fixture disk; both the channel index and the paired RAUC bundle are
authenticated by disposable keys. U-Boot slot selection is modeled from the
real redundant environment with fw_printenv; the QEMU guest boots a host-selected
slot and therefore does not prove SPL/U-Boot execution on the H616 board.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent))
from host_qemu_boot_health import assets, install_root
from host_qemu_rauc_composed import create_media, format_media, partition_layout, populate_ext4_partition

REPO = Path(__file__).resolve().parents[1]
LAYOUT = json.loads((REPO / 'configs/images/host-ab.json').read_text())
SOURCE_RELEASE = '0.1.0-offline.3'
GOOD_RELEASE = 'qemu-feed-b-1'
BAD_RELEASE = 'qemu-feed-a-bad-2'
TRUSTED_NOW = 1790400000
FIXTURE_DISK_SERIAL = 'SV08-QEMU-FEED'
DISK_SERIAL = 'SV08-QEMU-TARGET'
PARTUUIDS = {
    'boot-a': 'ba55a9b4-7969-423b-a739-db62e231b7a1',
    'root-a': '26c68198-9248-47af-bbd3-643f1b604ef5',
    'boot-b': '7b6e5211-6c5f-432f-9afc-2ac7e4f80b04',
    'root-b': 'd8d04a9a-f51f-41b3-a474-e079efe97186',
    'recovery': 'b28438ed-f895-4b93-9bad-d27d3890ccd3',
    'data': '4773f966-0678-4cf5-bb83-8ee6fb11d8eb',
}
MIB = 1024 * 1024
GIB = 1024 * 1024 * 1024
SHM_ROOT = Path('/dev/shm')
SHM_PREFIX = 'sv08-host-unattended-update-'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, **kwargs):
    return subprocess.run([str(value) for value in command], check=True, **kwargs)


def put(path, value, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)
    path.chmod(mode)


def install_qemu_test_services(root, work):
    shutil.copyfile(REPO / 'tests/fixtures/boot-health/qemu-unattended-update.py',
                    root / 'usr/lib/sv08/qemu-unattended-update.py')
    shutil.copyfile(REPO / 'tests/fixtures/boot-health/qemu-fw-env-setup.py',
                    root / 'usr/lib/sv08/qemu-fw-env-setup.py')
    shutil.copyfile(REPO / 'tests/fixtures/boot-health/qemu-boot-health-diagnostic.py',
                    root / 'usr/lib/sv08/qemu-boot-health-diagnostic.py')
    shutil.copyfile(work / 'fixture-keyring.pem', root / 'usr/lib/sv08/fixture-signers.pem')
    put(root / 'usr/lib/systemd/system/qemu-fw-env-setup.service', '''[Unit]
Description=Identify disposable QEMU media for the update fixture
After=sv08-prepare.service
Before=sv08-boot-health.service
ConditionKernelCommandLine=sv08.test=rauc-backend
[Service]
Type=oneshot
TimeoutStartSec=60
ExecStart=/usr/bin/python3 /usr/lib/sv08/qemu-fw-env-setup.py
StandardOutput=journal+console
StandardError=journal+console
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
''')
    put(root / 'etc/systemd/system/sv08-boot-health.service.d/qemu-env.conf',
        '[Unit]\nRequires=qemu-fw-env-setup.service\nAfter=qemu-fw-env-setup.service\n')
    put(root / 'etc/systemd/system/sv08-boot-health.service.d/qemu-console.conf',
        '[Service]\nTimeoutStartSec=240\nStandardOutput=journal+console\nStandardError=journal+console\n')
    put(root / 'usr/lib/systemd/system/qemu-boot-health-diagnostic.service', '''[Unit]
Description=Report failed QEMU boot health and stop the fixture
After=sv08-boot-health.service
ConditionKernelCommandLine=sv08.test=rauc-backend
ConditionPathExists=!/run/sv08/os-health-ready
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/lib/sv08/qemu-boot-health-diagnostic.py
StandardOutput=journal+console
StandardError=journal+console
[Install]
WantedBy=multi-user.target
''')
    link = root / 'etc/systemd/system/multi-user.target.wants/qemu-boot-health-diagnostic.service'
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to('/usr/lib/systemd/system/qemu-boot-health-diagnostic.service')
    put(root / 'usr/lib/systemd/system/qemu-unattended-update.service', '''[Unit]
Description=Signed feed and RAUC QEMU acceptance driver
After=sv08-boot-health.service
ConditionKernelCommandLine=sv08.test=rauc-backend
ConditionPathExists=/run/sv08/os-health-ready
[Service]
Type=oneshot
TimeoutStartSec=900
ExecStart=/usr/bin/python3 /usr/lib/sv08/qemu-unattended-update.py
StandardOutput=journal+console
StandardError=journal+console
[Install]
WantedBy=multi-user.target
''')
    run(['systemctl', '--root', root, 'enable', 'qemu-fw-env-setup.service'],
        stdout=subprocess.DEVNULL)
    run(['systemctl', '--root', root, 'enable', 'qemu-unattended-update.service'],
        stdout=subprocess.DEVNULL)


def create_signed_bundle(base, work, policy, release, *, fail_health):
    root = work / ('root-' + release)
    install_root(base, root, release, policy, fail_health=fail_health, work=work)
    qemu_unit = root / 'etc/systemd/system/multi-user.target.wants/qemu-boot-health.service'
    qemu_unit.unlink(missing_ok=True)
    (root / 'usr/lib/systemd/system/qemu-boot-health.service').unlink(missing_ok=True)
    install_qemu_test_services(root, work)

    content = work / ('bundle-content-' + release)
    content.mkdir()
    root_image = content / 'rootfs.img'
    with root_image.open('xb') as stream:
        stream.truncate(2048 * MIB)
    run(['mkfs.ext4', '-q', '-F', '-d', root, root_image])
    boot_image = content / 'boot.img'
    with boot_image.open('xb') as stream:
        stream.truncate(192 * MIB)
    run(['mkfs.vfat', '-F', '16', '-n', 'SV08BOOT', boot_image])
    boot_files = sorted((root / 'boot').glob('*'))
    if not boot_files:
        raise ValueError('Target bundle has no boot artifacts')
    run(['mcopy', '-i', boot_image, *boot_files, '::/'])
    put(content / 'manifest.raucm', f'''[update]
compatible={policy['compatible']}
version={release}
description=Disposable signed feed QEMU fixture

[bundle]
format=verity

[image.rootfs]
filename=rootfs.img

[image.boot]
filename=boot.img

[meta.sv08]
layout={policy['layout']}
state-schema={policy['state_schema']}
klipper-commit={policy['klipper_commit']}
''')
    bundle = work / (release + '.raucb')
    native_rauc = base.parents[2] / 'build/rauc-native-v1/rauc'
    run([native_rauc, 'bundle', '--cert=' + str(work / 'fixture-keyring.pem'),
         '--key=' + str(work / 'fixture-tls.key'), '--signing-keyring=' + str(work / 'fixture-keyring.pem'),
         content, bundle], stdout=subprocess.DEVNULL)
    report = dict(release=release, bundle=bundle.name, bytes=bundle.stat().st_size,
                  sha256=digest(bundle), root_image_sha256=digest(root_image),
                  boot_image_sha256=digest(boot_image), target_health_fails=fail_health)
    shutil.rmtree(root)
    shutil.rmtree(content)
    return bundle, report


def sign_index(feed_dir, bundle, policy, sequence, release):
    directory = feed_dir / ('feed-' + str(sequence))
    directory.mkdir(parents=True)
    shutil.copyfile(bundle, directory / bundle.name)
    index = dict(format_version=1, channel='stable', sequence=sequence,
                 issued=TRUSTED_NOW - 60, expires=TRUSTED_NOW + 86400,
                 compatible=policy['compatible'], release=release,
                 bundle=bundle.name, bytes=bundle.stat().st_size,
                 sha256=digest(bundle))
    document = directory / 'index.json'
    document.write_text(json.dumps(index, sort_keys=True, separators=(',', ':')))
    run(['openssl', 'cms', '-sign', '-binary', '-in', document,
         '-signer', feed_dir.parent.parent / 'fixture-keyring.pem',
         '-inkey', feed_dir.parent.parent / 'fixture-tls.key',
         '-outform', 'DER', '-out', directory / 'index.json.p7s'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return index


def create_boot_partition(image, name, source, work):
    part = next(item for item in partition_layout() if item['name'] == name)
    interim = work / (name + '.img')
    with interim.open('xb') as stream:
        stream.truncate(part['size_bytes'])
    run(['mkfs.vfat', '-F', '16', '-n', name.upper(), interim])
    files = sorted(Path(source).glob('*'))
    run(['mcopy', '-i', interim, *files, '::/'])
    run(['dd', 'if=' + str(interim), 'of=' + str(image), 'bs=1M',
         'seek=' + str(part['offset_bytes'] // MIB),
         'count=' + str(part['size_bytes'] // MIB), 'conv=notrunc,sparse', 'status=none'])
    interim.unlink()


def build_fixture(base, work):
    asset_repo = base.parents[2]
    policy = json.loads((asset_repo / 'build/rauc-bundle-metadata-v1/policy.json').read_text())
    run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', work / 'fixture-key'])
    run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
         '-keyout', work / 'fixture-tls.key', '-out', work / 'fixture-keyring.pem',
         '-days', '2', '-subj', '/CN=SV08 disposable QEMU signed update'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (work / 'fixture-tls.key').chmod(0o600)
    good_bundle, good_report = create_signed_bundle(base, work, policy, GOOD_RELEASE, fail_health=False)
    bad_bundle, bad_report = create_signed_bundle(base, work, policy, BAD_RELEASE, fail_health=True)

    feed_tree = work / 'feed-tree'
    feed_tree.mkdir()
    feed_dir = feed_tree / 'sv08'
    first = sign_index(feed_dir, good_bundle, policy, 1, GOOD_RELEASE)
    second = sign_index(feed_dir, bad_bundle, policy, 2, BAD_RELEASE)
    fixture_disk = work / 'feed-fixture.img'
    with fixture_disk.open('xb') as stream:
        stream.truncate(1600 * MIB)
    run(['mkfs.ext4', '-q', '-F', '-d', feed_tree, fixture_disk])
    shutil.rmtree(feed_tree)
    good_bundle.unlink()
    bad_bundle.unlink()

    root_source = work / 'root-source'
    install_root(base, root_source, SOURCE_RELEASE, policy, fail_health=False, work=work)
    qemu_unit = root_source / 'etc/systemd/system/multi-user.target.wants/qemu-boot-health.service'
    qemu_unit.unlink(missing_ok=True)
    (root_source / 'usr/lib/systemd/system/qemu-boot-health.service').unlink(missing_ok=True)
    install_qemu_test_services(root_source, work)

    data_seed = work / 'data-seed'
    (data_seed / 'sv08').mkdir(parents=True)
    (data_seed / 'fixture').mkdir()
    (data_seed / 'fixture/user-data-sentinel').write_text('preserved fixture data\n')
    (data_seed / 'sv08/qemu-update-phase.json').write_text(json.dumps(
        dict(step=0, trusted_now=TRUSTED_NOW)) + '\n')
    disk = work / 'guest.img'
    create_media(disk, PARTUUIDS)
    format_media(disk)
    parts = partition_layout(LAYOUT)
    populate_ext4_partition(disk, 'root-a', root_source, work / 'parts', parts)
    populate_ext4_partition(disk, 'root-b', root_source, work / 'parts', parts)
    populate_ext4_partition(disk, 'data', data_seed, work / 'parts', parts)
    create_boot_partition(disk, 'boot-a', root_source / 'boot', work)
    create_boot_partition(disk, 'boot-b', root_source / 'boot', work)
    shutil.rmtree(root_source)
    shutil.rmtree(data_seed)
    shutil.rmtree(work / 'parts')
    env_config = work / 'fw_env.config'
    put(env_config, f'{disk} 0x400000 0x10000\n{disk} 0x800000 0x10000\n')
    seed = work / 'fw-seed'
    # Match the measured H10 environment: A selected, with B excluded and bad.
    put(seed, 'sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A\nBOOT_A_LEFT=3\nBOOT_B_LEFT=0\n')
    run(['fw_setenv', '-c', env_config, '-f', seed, '-s', seed])
    report = dict(policy=policy, disk_sha256_before=digest(disk),
                  feed_disk_sha256=digest(fixture_disk), bundles=[good_report, bad_report],
                  feed_indexes=[first, second], physical_hardware=False)
    return disk, fixture_disk, env_config, report


def read_environment(config):
    values = {}
    output = subprocess.check_output(['fw_printenv', '-c', config], text=True)
    for line in output.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
    return values


def select_and_consume_attempt(config):
    values = read_environment(config)
    order = values.get('BOOT_ORDER', '').split()
    if not 1 <= len(order) <= 2 or len(set(order)) != len(order) or not set(order) <= {'A', 'B'}:
        raise ValueError('Invalid test U-Boot order')
    for slot in order:
        key = 'BOOT_' + slot + '_LEFT'
        remaining = int(values[key])
        if remaining > 0:
            subprocess.run(['fw_setenv', '-c', config, key, str(remaining - 1)], check=True)
            return slot, dict(before=values, consumed_slot=slot, before_count=remaining,
                              after_count=remaining - 1)
    raise ValueError('No boot attempts remain in either slot')


def boot(base, disk, fixture_disk, slot, work, number):
    root_uuid = PARTUUIDS['root-' + slot.lower()]
    log = work / f'boot-{number}-{slot}.log'
    command = ['qemu-system-aarch64', '-machine', 'virt', '-accel', 'tcg,thread=multi',
               '-cpu', 'cortex-a53', '-smp', '4', '-m', '1536',
               '-nographic', '-no-reboot', '-nic',
               f'user,hostfwd=tcp:127.0.0.1:{22220 + number}-:22',
               '-kernel', base / 'boot/vmlinuz-6.12.107+deb13-arm64',
               '-initrd', base / 'boot/initrd.img-6.12.107+deb13-arm64',
               '-drive', f'file={disk},format=raw,if=none,id=disk',
               '-device', 'virtio-blk-device,drive=disk,serial=' + DISK_SERIAL,
               '-drive', f'file={fixture_disk},format=raw,if=none,id=feed,readonly=on',
               '-device', 'virtio-blk-device,drive=feed,serial=' + FIXTURE_DISK_SERIAL,
               '-append', f'console=ttyAMA0 root=PARTUUID={root_uuid} rootwait ro panic=10 systemd.setenv=SYSTEMD_LOG_LEVEL=debug rauc.slot={slot} sv08.test=rauc-backend']
    with log.open('w') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
    if log.stat().st_size > 3 * 1024**2:
        raise ValueError('Guest serial output exceeded fixture limit')
    text = log.read_text(errors='replace')
    for marker in ('SV08_QEMU_ENV_SETUP_FAILURE ', 'SV08_QEMU_SIGNED_FEED_FAILURE '):
        if marker in text:
            raise ValueError('Guest fixture failed: ' + text[text.index(marker):].splitlines()[0])
    if ('SV08_QEMU_BOOT_HEALTH_FAILURE ' in text and
            'SV08_QEMU_FALLBACK_REQUEST ' not in text):
        raise ValueError('Guest boot-health failure did not record an expected fallback request')
    return dict(slot=slot, log=str(log), log_sha256=digest(log), log_bytes=log.stat().st_size,
                exit_status=result.returncode, log_text=text)


def hash_region(path, offset, length):
    value = hashlib.sha256()
    with Path(path).open('rb', buffering=0) as stream:
        stream.seek(offset)
        remaining = length
        while remaining:
            chunk = stream.read(min(8 * MIB, remaining))
            if not chunk:
                raise ValueError('Short fixture disk read')
            value.update(chunk)
            remaining -= len(chunk)
    return value.hexdigest()


def execute(work, first_stage_only=False):
    source = assets()
    base = source / 'build/host-rauc-v1/rootfs'
    for path in (base / 'usr/bin/rauc', base / 'boot/vmlinuz-6.12.107+deb13-arm64',
                 base / 'boot/initrd.img-6.12.107+deb13-arm64',
                 source / 'build/rauc-bundle-metadata-v1/policy.json',
                 source / 'build/rauc-native-v1/rauc'):
        if not path.is_file():
            raise ValueError('Missing reviewed QEMU input: ' + str(path))
    scratch_root = SHM_ROOT if work.parent == SHM_ROOT else REPO
    scratch_free = shutil.disk_usage(scratch_root).free
    minimum = 6 * GIB if work.parent == SHM_ROOT else 8 * GIB
    if scratch_free < minimum:
        raise ValueError(f'Need {minimum // GIB} GiB free on the selected QEMU scratch filesystem')
    work.mkdir(mode=0o700, parents=True)
    disk, fixture_disk, env_config, report = build_fixture(base, work)
    initial_free = shutil.disk_usage(work).free
    reserve = 1 * GIB if work.parent == SHM_ROOT else 2 * GIB
    if initial_free < reserve:
        raise ValueError('Fixture construction fell below its scratch-space reserve')
    parts = partition_layout(LAYOUT)
    recovery = next(item for item in parts if item['name'] == 'recovery')
    recovery_before = hash_region(disk, recovery['offset_bytes'], recovery['size_bytes'])
    primary_gpt_before = hash_region(disk, 0, 34 * 512)
    backup_gpt_before = hash_region(disk, LAYOUT['image_bytes'] - 33 * 512, 33 * 512)
    boots = []
    for number in range(1, 2 if first_stage_only else 7):
        slot, attempt = select_and_consume_attempt(env_config)
        run_result = boot(base, disk, fixture_disk, slot, work, number)
        boots.append(dict(number=number, slot=slot, attempt=attempt,
                          log_sha256=run_result['log_sha256'], log_bytes=run_result['log_bytes'],
                          exit_status=run_result['exit_status']))
        marker_arm = 'SV08_QEMU_SIGNED_FEED_ARM '
        marker_complete = 'SV08_QEMU_SIGNED_FEED_COMPLETE '
        if 'SV08_QEMU_SIGNED_FEED_FAILURE ' in run_result['log_text']:
            raise ValueError('Feed/RAUC guest failed at boot ' + str(number) + ': ' + str(work / run_result['log']))
        if slot == 'A' and number == 1:
            if marker_arm not in run_result['log_text']:
                raise ValueError('First signed feed did not install/arm B')
            if first_stage_only:
                break
        elif slot == 'B' and number == 2:
            if marker_arm not in run_result['log_text']:
                raise ValueError('Second signed feed did not install/arm A')
        elif slot == 'A' and number in (3, 4, 5):
            if marker_arm in run_result['log_text'] or marker_complete in run_result['log_text']:
                raise ValueError('Failed trial incorrectly reached the feed runner')
            if ('SV08_QEMU_BOOT_HEALTH_FAILURE ' not in run_result['log_text'] or
                    'SV08_QEMU_FALLBACK_REQUEST ' not in run_result['log_text'] or
                    'Host OS health was not stable within deadline' not in run_result['log_text']):
                raise ValueError('Failed trial lacks a bounded health failure and fallback record')
        elif slot == 'B' and number == 6:
            if marker_complete not in run_result['log_text']:
                raise ValueError('Final B fallback assertions did not pass')
            break
        else:
            raise ValueError(f'Unexpected environment-selected slot {slot} on boot {number}')
    if not boots or (not first_stage_only and boots[-1]['slot'] != 'B'):
        raise ValueError('Did not reach preserved B after A trial failures')
    if not first_stage_only and primary_gpt_before != hash_region(disk, 0, 34 * 512):
        raise ValueError('Primary GPT changed')
    if not first_stage_only and backup_gpt_before != hash_region(disk, LAYOUT['image_bytes'] - 33 * 512, 33 * 512):
        raise ValueError('Backup GPT changed')
    if not first_stage_only and recovery_before != hash_region(disk, recovery['offset_bytes'], recovery['size_bytes']):
        raise ValueError('Recovery partition changed')
    report.update(boots=boots, primary_gpt_sha256=primary_gpt_before,
                  backup_gpt_sha256=backup_gpt_before, recovery_sha256=recovery_before,
                  disk_sha256_after=digest(disk), free_after=shutil.disk_usage(work).free,
                  boot_selection='Host test model read real redundant environment and consumed attempts; QEMU kernel slot argument was host supplied.',
                  assertions=dict(first_stage_only=first_stage_only,
                      full_journey_passed=False if first_stage_only else True,
                      signed_index_cms=True, signed_rauc_bundles=True,
                      real_rauc_inactive_pair_install=True, stage_environment_copies_unchanged=True,
                      arm_environment_delta_allowlisted=True,
                      target_boot_health_confirmed=not first_stage_only,
                      failed_target_health_retries_then_falls_back=not first_stage_only,
                      fallback_transaction_cancelled=not first_stage_only, active_source_preserved=True,
                      primary_and_backup_gpt_unchanged=not first_stage_only,
                      recovery_partition_unchanged=not first_stage_only,
                      user_data_sentinel_preserved=not first_stage_only, mcu_artifacts_written=False,
                      automatic_uboot_execution=False, physical_hardware=False))
    result_path = work / 'result.json'
    result_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    shutil.rmtree(work / 'root-source', ignore_errors=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--first-stage-only', action='store_true',
                        help='stop after real signed A-to-B install/arm; does not test repeated update or fallback')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    raw = Path(os.path.abspath(args.work))
    if any(path.is_symlink() for path in (raw, *raw.parents)):
        raise SystemExit('Symlink work paths are not supported')
    work = raw.resolve()
    if not args.execute:
        print(json.dumps(dict(execute=False, target='fresh regular file only', hardware=False,
                              requires=['QEMU', 'ARM64 host root', 'RAUC test signer',
                                        '6 GiB free in /dev/shm tmpfs']), indent=2))
        return
    build_work = work.is_relative_to(REPO / 'build') and work != REPO / 'build'
    shm_work = (work.parent == SHM_ROOT and work.name.startswith(SHM_PREFIX) and
                ' /dev/shm tmpfs ' in (' '+Path('/proc/mounts').read_text().replace('\t', ' ')+' '))
    if os.geteuid() != 0 or work.exists() or not (build_work or shm_work):
        raise SystemExit('Use root and a fresh build/ directory or named /dev/shm tmpfs directory')
    execute(work, args.first_stage_only)


if __name__ == '__main__':
    main()
