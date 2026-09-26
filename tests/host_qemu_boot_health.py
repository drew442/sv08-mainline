#!/usr/bin/env python3
"""Disposable ARM64 QEMU exercise of installed SV08 prepare and boot-health units.

The harness chooses root A/B explicitly. It tests real Linux units, state,
RAUC/U-Boot environment operations and persistent disk across guest boots, but
does not test signed installation, automatic U-Boot selection or hardware.
Default invocation is inspection only. ``--execute`` requires root and a fresh
ignored build directory; only a new regular-file disk is ever written.
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
from host_qemu_rauc_composed import copy_guest_root, create_media, format_media, populate_ext4_partition

REPO = Path(__file__).resolve().parents[1]
GUEST = REPO / 'tests/fixtures/boot-health/qemu-boot-health.py'
UUIDS = {
    'boot-a': 'ba55a9b4-7969-423b-a739-db62e231b7a1',
    'root-a': '26c68198-9248-47af-bbd3-643f1b604ef5',
    'boot-b': '7b6e5211-6c5f-432f-9afc-2ac7e4f80b04',
    'root-b': 'd8d04a9a-f51f-41b3-a474-e079efe97186',
    'recovery': 'b28438ed-f895-4b93-9bad-d27d3890ccd3',
    'data': '4773f966-0678-4cf5-bb83-8ee6fb11d8eb',
}
RAUC_SHA256 = '51d7c057c7fb00917287b5324303c747e71c5406f4c1363a678578ac7a3b12e3'
RUNTIME_REVISION = 'a2f0b8f'


def assets():
    listing = subprocess.check_output(['git', '-C', str(REPO), 'worktree', 'list', '--porcelain'], text=True)
    for line in listing.splitlines():
        if line.startswith('worktree '):
            candidate = Path(line.removeprefix('worktree '))
            if (candidate / 'build/host-rauc-v1/rootfs/usr/bin/rauc').is_file():
                return candidate
    raise ValueError('Reviewed ignored ARM64 root is unavailable')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, **kwargs):
    return subprocess.run([str(item) for item in command], check=True, **kwargs)


def write(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(mode)


def prerequisites(source):
    base = source / 'build/host-rauc-v1/rootfs'
    required = [base / 'usr/bin/rauc', base / 'boot/vmlinuz-6.12.107+deb13-arm64',
                base / 'boot/initrd.img-6.12.107+deb13-arm64',
                source / 'build/rauc-bundle-metadata-v1/policy.json', GUEST]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError('Missing reviewed input: ' + ', '.join(missing))
    if digest(base / 'usr/bin/rauc') != RAUC_SHA256:
        raise ValueError('RAUC executable differs from reviewed fixture')
    run(['git', '-C', REPO, 'merge-base', '--is-ancestor', RUNTIME_REVISION, 'HEAD'])
    changed = run(['git', '-C', REPO, 'diff', '--name-only', RUNTIME_REVISION, '--',
                   'runtime', 'configs/host-os/systemd'],
                  capture_output=True, text=True).stdout.strip()
    changed += run(['git', '-C', REPO, 'diff', '--name-only', 'HEAD', '--',
                    'runtime', 'configs/host-os/systemd'], capture_output=True, text=True).stdout.strip()
    if changed:
        raise ValueError('Runtime or installed units changed after reviewed revision: ' + changed)
    return base


def install_root(base, root, release, policy, *, fail_health, work):
    copy_guest_root(base, root)
    for name in ('qemu-rauc.service', 'qemu-probe.service'):
        (root / 'etc/systemd/system/multi-user.target.wants' / name).unlink(missing_ok=True)
    runtime = root / 'usr/lib/sv08'
    for source in (REPO / 'runtime').glob('*.py'):
        shutil.copyfile(source, runtime / source.name)
    (runtime / 'sv08_rauc_bootloader.py').chmod(0o755)
    for name in ('sv08-prepare.service', 'sv08-boot-health.service', 'sv08-klipper.service'):
        shutil.copyfile(REPO / 'configs/host-os/systemd' / name,
                        root / 'etc/systemd/system' / name)
    manifest = dict(release=release, state_schema=1, deployable=False,
                    devices={name: '/dev/disk/by-partuuid/' + uuid for name, uuid in UUIDS.items()})
    environment = json.loads((REPO / 'configs/host-os/environment-layout.json').read_text())
    environment['board_mmc_device_index'] = 10
    for name, value in [('release.json', manifest), ('update-policy.json', policy),
                        ('layout.json', json.loads((REPO / 'configs/images/host-ab.json').read_text())),
                        ('environment.json', environment)]:
        write(runtime / name, json.dumps(value) + '\n')
    service_policy = json.loads((REPO / 'configs/host-os/rauc-service-policy.json').read_text())
    write(runtime / 'rauc-service-policy.json', json.dumps(service_policy) + '\n')
    seed = runtime / 'seed/authorized_keys'
    write(seed, (work / 'fixture-key.pub').read_text())
    shutil.copyfile(GUEST, runtime / 'qemu-boot-health.py')
    write(root / 'etc/fstab', 'rootfs / ext4 ro 0 1\n')
    write(root / 'etc/fw_env.config', '/dev/vda 0x400000 0x10000\n/dev/vda 0x800000 0x10000\n')
    config = (REPO / 'configs/host-os/rauc-system.conf.in').read_text()
    for token, value in [('COMPATIBLE', policy['compatible']),
                         *[(name.upper().replace('-', '_'), manifest['devices'][name])
                           for name in ('root-a', 'boot-a', 'root-b', 'boot-b')]]:
        config = config.replace('@' + token + '@', value)
    write(root / 'etc/rauc/system.conf', config)
    (root / 'etc/rauc').mkdir(exist_ok=True)
    shutil.copyfile(work / 'fixture-keyring.pem', root / 'etc/rauc/release-keyring.pem')
    for source, destination in [
        (REPO / 'configs/host-os/sv08-rauc-policy.conf', root / 'etc/dbus-1/system.d/zz-sv08-rauc.conf'),
        (REPO / 'configs/host-os/sv08-rauc-service.conf', root / 'etc/systemd/system/rauc.service.d/sv08.conf')]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    write(root / 'usr/lib/systemd/system/rauc.service', '''[Unit]
After=dbus.service
[Service]
Type=dbus
BusName=de.pengutronix.rauc
ExecStart=/usr/bin/rauc --mount=/run/rauc service
''')
    write(root / 'usr/lib/systemd/system/qemu-boot-health.service', '''[Unit]
Description=Disposable QEMU boot-health assertion
Requires=sv08-boot-health.service
After=multi-user.target sv08-boot-health.service
ConditionKernelCommandLine=sv08.test=rauc-backend
[Service]
Type=oneshot
TimeoutStartSec=120
ExecStart=/usr/bin/python3 /usr/lib/sv08/qemu-boot-health.py
StandardOutput=journal+console
StandardError=journal+console
[Install]
WantedBy=multi-user.target
''')
    if fail_health:
        # Fail only HostHealth's prepare-unit observation. Keep the real unit
        # active and RAUC identity/configuration intact so fallback can recheck
        # the target before requesting its reboot.
        wrapper = runtime / 'qemu-test-bin/systemctl'
        write(wrapper, '''#!/usr/bin/python3
import os, sys
if sys.argv[1:] == ['is-active', 'sv08-prepare.service']:
    print('inactive')
    raise SystemExit(3)
os.execv('/usr/bin/systemctl', ['systemctl', *sys.argv[1:]])
''', 0o755)
        write(root / 'etc/systemd/system/sv08-boot-health.service.d/qemu-fail-health.conf',
              '[Service]\nEnvironment="PATH=/usr/lib/sv08/qemu-test-bin:/usr/bin:/bin"\n')
    write(root / 'etc/systemd/system/sv08-boot-health.service.d/console.conf',
          '[Service]\nStandardOutput=journal+console\nStandardError=journal+console\n')
    write(root / 'etc/systemd/system/data.mount', '''[Unit]
Description=SV08 persistent data (prepared by initramfs)
[Mount]
What=/dev/disk/by-partuuid/4773f966-0678-4cf5-bb83-8ee6fb11d8eb
Where=/data
Type=ext4
Options=nodev,nosuid
[Install]
WantedBy=local-fs.target
''')
    (root / 'etc/machine-id').write_text('')
    for path in (root / 'etc/ssh').glob('ssh_host_*'):
        path.unlink()
    for name in ('sv08-prepare.service', 'sv08-boot-health.service',
                 'qemu-boot-health.service', 'data.mount', 'rauc.service'):
        run(['systemctl', '--root', root, 'enable', name], stdout=subprocess.DEVNULL)
    return manifest


def make_disk(work, root_a, root_b, scenario):
    disk = work / 'guest.img'
    data = work / 'data-seed'
    data.mkdir()
    (data / 'sv08').mkdir()
    write(data / 'sv08/qemu-boot-health-phase.json', json.dumps({'scenario': scenario, 'step': 0}) + '\n')
    create_media(disk, UUIDS)
    format_media(disk)
    parts = work / 'parts'
    populate_ext4_partition(disk, 'root-a', root_a, parts)
    populate_ext4_partition(disk, 'root-b', root_b, parts)
    populate_ext4_partition(disk, 'data', data, parts)
    write(work / 'fw_env.config', f'{disk} 0x400000 0x10000\n{disk} 0x800000 0x10000\n')
    write(work / 'fw-seed', 'sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A B\nBOOT_A_LEFT=3\nBOOT_B_LEFT=0\n')
    run(['fw_setenv', '-c', work / 'fw_env.config', '-f', work / 'fw-seed', '-s', work / 'fw-seed'])
    return disk


def boot(base, disk, work, scenario, slot, number):
    root_uuid = UUIDS['root-' + slot.lower()]
    log = work / f'{scenario}-boot-{number}.log'
    command = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a53', '-smp', '2', '-m', '1024',
               '-nographic', '-no-reboot', '-nic', 'none', '-kernel', base / 'boot/vmlinuz-6.12.107+deb13-arm64',
               '-initrd', base / 'boot/initrd.img-6.12.107+deb13-arm64',
               '-drive', f'file={disk},format=raw,if=none,id=disk',
               '-device', 'virtio-blk-device,drive=disk,serial=SV08-QEMU-DISPOSABLE',
               '-append', f'console=ttyAMA0 root=PARTUUID={root_uuid} rootwait ro panic=10 rauc.slot={slot} sv08.test=rauc-backend']
    with log.open('w') as stream:
        run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=480)
    if log.stat().st_size > 2 * 1024**2:
        raise ValueError('Boot serial output exceeded the 2 MiB fixture bound')
    lines = log.read_text(errors='replace').splitlines()
    results = [json.loads(line.split('SV08_QEMU_BOOT_HEALTH_RESULT ', 1)[1])
               for line in lines if 'SV08_QEMU_BOOT_HEALTH_RESULT ' in line]
    failures = [line for line in lines if 'SV08_QEMU_BOOT_HEALTH_FAILURE ' in line]
    if scenario == 'fallback' and slot == 'B':
        if results or failures or not any('Rebooting' in line or 'reboot' in line.lower() for line in lines[-100:]):
            raise ValueError('Failed target did not request a clean fallback reboot: ' + str(log))
        result = {'scenario': scenario, 'slot': slot, 'fallback_reboot_observed': True}
    elif len(results) == 1 and results[0]['passed'] is True and not failures:
        result = results[0]
    else:
        raise ValueError('No single passing guest assertion: ' + str(log))
    return dict(result=result, log_sha256=digest(log), log=str(log),
                log_bytes=log.stat().st_size, exit_status=0,
                command=[str(item) for item in command])


def execute(work, base, source):
    run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', work / 'fixture-key'])
    run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
         '-keyout', work / 'fixture-tls.key', '-out', work / 'fixture-keyring.pem',
         '-days', '2', '-subj', '/CN=SV08 disposable QEMU boot health'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    policy = json.loads((source / 'build/rauc-bundle-metadata-v1/policy.json').read_text())
    a, good, bad = (work / name for name in ('root-a', 'root-b-good', 'root-b-bad'))
    install_root(base, a, '0.1.0-offline.3', policy, fail_health=False, work=work)
    install_root(base, good, 'qemu-boot-health-b', policy, fail_health=False, work=work)
    reports = {}
    # Keep only one target-root copy at a time. The old fixture retained A,
    # good B and bad B together, forcing a 20 GiB guard despite each scenario
    # using only one B image. This sequence preserves the same checks while
    # fitting the project's constrained VM.
    minimum_free = 2 * 1024**3
    for scenario, root_b, slots in [('success', good, ('A', 'B'))]:
        disk = make_disk(work, a, root_b, scenario)
        reports[scenario] = [boot(base, disk, work, scenario, slot, i)
                             for i, slot in enumerate(slots)]
        reports[scenario + '_disk_sha256'] = digest(disk)
        disk.unlink()
        shutil.rmtree(work / 'parts')
        shutil.rmtree(work / 'data-seed')
        shutil.rmtree(good)
        stat = os.statvfs(work)
        if stat.f_bavail * stat.f_frsize < minimum_free:
            raise ValueError('QEMU fixture fell below the 2 GiB free-space safety reserve')
    install_root(base, bad, 'qemu-boot-health-b', policy, fail_health=True, work=work)
    scenario, root_b, slots = 'fallback', bad, ('A', 'B', 'A')
    disk = make_disk(work, a, root_b, scenario)
    reports[scenario] = [boot(base, disk, work, scenario, slot, i)
                         for i, slot in enumerate(slots)]
    reports[scenario + '_disk_sha256'] = digest(disk)
    disk.unlink()
    shutil.rmtree(work / 'parts')
    shutil.rmtree(work / 'data-seed')
    source_commit = run(['git', '-C', REPO, 'rev-parse', 'HEAD'],
                        capture_output=True, text=True).stdout.strip()
    dirty_state = run(['git', '-C', REPO, 'status', '--short'],
                      capture_output=True, text=True).stdout.splitlines()
    qemu_version = run(['qemu-system-aarch64', '--version'],
                       capture_output=True, text=True).stdout.splitlines()[0]
    report = dict(source_commit=source_commit, reviewed_runtime_commit=RUNTIME_REVISION,
                  source_dirty_state=dirty_state, qemu_version=qemu_version,
                  base_rauc_sha256=digest(base / 'usr/bin/rauc'),
                  kernel_sha256=digest(base / 'boot/vmlinuz-6.12.107+deb13-arm64'),
                  initrd_sha256=digest(base / 'boot/initrd.img-6.12.107+deb13-arm64'),
                  physical_hardware=False, health_failure_injection='health-probe-systemctl-wrapper',
                  automatic_boot_selection_tested=False,
                  signed_installation_tested=False, scenarios=reports)
    write(work / 'result.json', json.dumps(report, indent=2) + '\n', 0o600)
    # Keep only reproducible small evidence. Root-tree copies, signing keys and
    # the disposable GPT have served their purpose and otherwise consume most
    # of the workstation filesystem between runs.
    shutil.rmtree(a)
    shutil.rmtree(bad)
    for name in ('fixture-key', 'fixture-key.pub', 'fixture-tls.key', 'fixture-keyring.pem',
                 'fw-seed', 'fw_env.config'):
        (work / name).unlink(missing_ok=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    source = assets()
    base = prerequisites(source)
    work = args.work.resolve()
    if not work.is_relative_to(source / 'build') or work == source / 'build':
        raise ValueError('Fixture must use a fresh ignored build directory')
    required_peak_bytes = 8 * 1024**3
    print(json.dumps(dict(execute=args.execute, work=str(work), source_commit=RUNTIME_REVISION,
                          physical_hardware=False, required_peak_bytes=required_peak_bytes,
                          retained_target_root_copies=1, free_space_reserve_bytes=2*1024**3), indent=2))
    if not args.execute:
        return
    if os.geteuid() != 0 or work.exists():
        raise ValueError('Execution needs root and an unoccupied fixture directory')
    stat = os.statvfs(source / 'build')
    if stat.f_bavail * stat.f_frsize < required_peak_bytes:
        raise ValueError('Less than 8 GiB free for sequential isolated QEMU construction')
    if subprocess.run(['pgrep', '-f', '^qemu-system-aarch64'], stdout=subprocess.DEVNULL).returncode == 0:
        raise ValueError('Another QEMU process is active')
    work.mkdir(mode=0o700)
    print(json.dumps(execute(work, base, source), indent=2))


if __name__ == '__main__':
    main()
