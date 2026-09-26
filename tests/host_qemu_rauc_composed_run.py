#!/usr/bin/env python3
"""Build and exercise a disposable Cockpit/RAUC ARM64 QEMU composition.

``--execute`` accepts only a fresh directory under build/.  It creates a regular
GPT file, not a host block device, and exposes Cockpit only on 127.0.0.1.  The
fixture has an explicitly non-deployable release manifest and the guest requires
the QEMU-only kernel marker before the real RAUC backend accepts an operation.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from host_qemu_rauc_composed import copy_guest_root, create_media, format_media, populate_ext4_partition

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'build/host-rauc-v1/rootfs'
INTAKE = REPO / 'build/cockpit-intake-337'
CHROME = Path('/home/drew/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome')
UUIDS = {
    'boot-a': '00000000-0000-4000-8000-000000000001',
    'root-a': '00000000-0000-4000-8000-000000000002',
    'boot-b': '00000000-0000-4000-8000-000000000003',
    'root-b': '00000000-0000-4000-8000-000000000004',
    'recovery': '00000000-0000-4000-8000-000000000005',
    'data': '4773f966-0678-4cf5-bb83-8ee6fb11d8eb',
}


def run(command, **kwargs):
    return subprocess.run([str(item) for item in command], check=True, **kwargs)


def digest(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def put(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)


def install_cockpit(root):
    lock = json.loads((REPO / 'configs/host-os/cockpit-packages.json').read_text())
    debs = [INTAKE / item['file'] for item in lock['delta']]
    for item, deb in zip(lock['delta'], debs):
        if digest(deb) != item['sha256']:
            raise RuntimeError('Cockpit intake digest mismatch: ' + deb.name)
    for name in ('proc', 'dev'):
        run(['mount', '-t', 'proc' if name == 'proc' else 'tmpfs', name, root / name])
    try:
        for name, major, minor in [('null', 1, 3), ('urandom', 1, 9)]:
            run(['mknod', '-m', '666', root / 'dev' / name, 'c', major, minor])
        (root / 'tmp/debs').mkdir()
        for deb in debs:
            shutil.copyfile(deb, root / 'tmp/debs' / deb.name)
        run(['chroot', root, 'dpkg', '-i', *('/tmp/debs/' + deb.name for deb in debs)])
        for user in ('fixtureadmin', 'fixtureordinary'):
            run(['chroot', root, 'useradd', '-m', '-s', '/bin/bash', user])
        run(['chroot', root, 'chpasswd'], input=(
            'fixtureadmin:sv08-compose-admin\nfixtureordinary:sv08-compose-user\n'), text=True)
        run(['chroot', root, 'usermod', '-aG', 'sudo', 'fixtureadmin'])
    finally:
        run(['umount', root / 'dev'])
        run(['umount', root / 'proc'])


def prepare(work):
    root = copy_guest_root(BASE, work / 'rootfs')
    data = work / 'data'
    data.mkdir(parents=True)
    (data / 'fixture').mkdir()
    put(data / 'fixture/user-data-sentinel', 'preserved fixture data\n', 0o600)
    install_cockpit(root)

    # These service-only inputs are deliberately incomplete.  Mask the selected
    # image preparer rather than weaken its production A/B checks, and remove
    # previous disposable test services inherited from the selected root.
    for name in ('qemu-rauc.service', 'qemu-probe.service'):
        (root / 'etc/systemd/system/multi-user.target.wants' / name).unlink(missing_ok=True)
    preparer = root / 'etc/systemd/system/sv08-prepare.service'
    preparer.unlink(missing_ok=True)
    preparer.symlink_to('/dev/null')
    (root / 'etc/systemd/system/cockpit.service.d').mkdir(parents=True, exist_ok=True)

    runtime = root / 'usr/lib/sv08'
    runtime.mkdir(parents=True, exist_ok=True)
    for source in (REPO / 'runtime').glob('*.py'):
        shutil.copyfile(source, runtime / source.name)
    (runtime / 'sv08_rauc_bootloader.py').chmod(0o755)
    sys.path.insert(0, str(REPO / 'scripts'))
    spec = importlib.util.spec_from_file_location('stage_admin_ui', REPO / 'scripts/stage_admin_ui.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.stage(work, 'host', True)

    manifest = {'release': '0.1.0-offline.3', 'state_schema': 1, 'deployable': False,
                'devices': {name: '/dev/disk/by-partuuid/' + uuid for name, uuid in UUIDS.items()}}
    policy = json.loads((REPO / 'build/rauc-bundle-metadata-v1/policy.json').read_text())
    environment = json.loads((REPO / 'configs/host-os/environment-layout.json').read_text())
    environment['board_mmc_device_index'] = 10  # explicit QEMU virtio fixture
    for name, value in [
        ('release.json', manifest),
        ('update-policy.json', policy),
        ('layout.json', json.loads((REPO / 'configs/images/host-ab.json').read_text())),
        ('environment.json', environment),
        ('admin-context.json', {'format_version': 1, 'context': 'host'}),
    ]:
        put(runtime / name, json.dumps(value) + '\n')

    put(root / 'etc/fstab', 'rootfs / ext4 ro 0 1\n')
    put(root / 'etc/fw_env.config', '/dev/vda 0x400000 0x10000\n/dev/vda 0x800000 0x10000\n')
    conf = (REPO / 'configs/host-os/rauc-system.conf.in').read_text()
    for key, name in [('COMPATIBLE', 'compatible'), ('ROOT_A', 'root-a'), ('BOOT_A', 'boot-a'),
                      ('ROOT_B', 'root-b'), ('BOOT_B', 'boot-b')]:
        conf = conf.replace('@' + key + '@', policy[name] if key == 'COMPATIBLE' else manifest['devices'][name])
    put(root / 'etc/rauc/system.conf', conf)
    for source, destination in [
        (REPO / 'configs/host-os/sv08-rauc-policy.conf', root / 'etc/dbus-1/system.d/zz-sv08-rauc.conf'),
        (REPO / 'configs/host-os/sv08-rauc-service.conf', root / 'etc/systemd/system/rauc.service.d/sv08.conf'),
    ]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    put(root / 'usr/lib/systemd/system/rauc.service', '''[Unit]
After=dbus.service
[Service]
Type=dbus
BusName=de.pengutronix.rauc
ExecStart=/usr/bin/rauc --mount=/run/rauc service
''')
    shutil.copyfile(REPO / 'configs/host-os/rauc-service-policy.json', runtime / 'rauc-service-policy.json')

    cert = root / 'etc/cockpit/ws-certs.d/0-fixture.cert'
    cert.parent.mkdir(parents=True, exist_ok=True)
    key = work / 'cockpit.key'
    run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key,
         '-out', cert, '-days', '2', '-subj', '/CN=sv08-composed-fixture'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cert.write_bytes(cert.read_bytes() + key.read_bytes())
    cert.chmod(0o600)
    (root / 'etc/rauc').mkdir(exist_ok=True)
    shutil.copyfile(cert, root / 'etc/rauc/release-keyring.pem')
    put(root / 'etc/cockpit/cockpit.conf', '[WebService]\nShell=/sv08-host/index.html\nAllowUnencrypted=true\n')

    put(root / 'usr/lib/sv08/composed-fixture.py', '''import json
from pathlib import Path
from sv08_state import Store
store=Store('/data/sv08', reserve_bytes=0); store.initialize()
Path('/data/sv08/uploads').mkdir(mode=0o700, exist_ok=True)
boot=store.prepare_boot('A', '0.1.0-offline.3')
boot['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
Path('/run/sv08').mkdir(exist_ok=True); Path('/run/sv08/boot.json').write_text(json.dumps(boot))
transaction=Path('/data/sv08/update.json')
if transaction.exists():
 value=json.loads(transaction.read_text()); value['boot_id']=boot['boot_id']; transaction.write_text(json.dumps(value))
''', 0o755)
    put(root / 'usr/lib/systemd/system/sv08-composed-fixture.service', '''[Unit]
After=local-fs.target
Before=cockpit.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/lib/sv08/composed-fixture.py
[Install]
WantedBy=multi-user.target
''')
    put(root / 'etc/systemd/system/data.mount', '''[Mount]
What=/dev/disk/by-partuuid/4773f966-0678-4cf5-bb83-8ee6fb11d8eb
Where=/data
Type=ext4
Options=rw,nosuid,nodev
[Install]
WantedBy=local-fs.target
''')
    for unit in ('sv08-klipper', 'sv08-moonraker'):
        put(root / ('usr/lib/systemd/system/' + unit + '.service'), '[Service]\nType=oneshot\nExecStart=/usr/bin/true\nRemainAfterExit=no\n')
    put(root / 'etc/systemd/network/10-fixture.network', '[Match]\nName=enp0s1\n[Network]\nDHCP=yes\n')
    for unit in ('cockpit.socket', 'sv08-composed-fixture.service', 'data.mount', 'systemd-networkd.service'):
        run(['systemctl', '--root', root, 'enable', unit], stdout=subprocess.DEVNULL)
    put(work / 'credentials.json', json.dumps({'fixtureadmin': 'sv08-compose-admin',
                                                'fixtureordinary': 'sv08-compose-user'}), 0o600)

    sys.path.insert(0, str(REPO / 'runtime'))
    from sv08_state import Store
    from sv08_admin import snapshot, revision, ACTIONS
    from sv08_admin_jobs import Jobs
    store = Store(data / 'sv08', reserve_bytes=0)
    store.initialize()
    boot = store.prepare_boot('A', '0.1.0-offline.3')
    boot['boot_id'] = 'a' * 32
    plan = {'action': 'image.cancel', 'arguments': {}, 'revision': revision(snapshot(store, boot, 'host')),
            'title': ACTIONS['image.cancel'][0], 'effect': ACTIONS['image.cancel'][1],
            'preserves_user_data': True}
    put(data / 'sv08/update.json', json.dumps({'format_version': 1, 'id': 'b' * 32, 'phase': 'staged',
        'slot': 'B', 'previous_slot': 'A', 'previous_release': '0.1.0-offline.3',
        'release': '0.1.0-offline.4', 'bundle_sha256': 'c' * 64, 'boot_id': 'a' * 32}))
    jobs = Jobs(data / 'sv08/admin-image-jobs', 'a' * 32)
    with jobs.lock('ledger.lock'):
        jobs.save([{'id': 'd' * 32, 'plan': plan, 'boot_id': 'previousboot', 'phase': 'interrupted',
                    'message': 'worker interrupted', 'queued_at': 0}])

    image = work / 'guest.img'
    create_media(image, UUIDS)
    format_media(image)
    populate_ext4_partition(image, 'root-a', root, work / 'parts')
    populate_ext4_partition(image, 'root-b', root, work / 'parts')
    populate_ext4_partition(image, 'data', data, work / 'parts')
    put(work / 'fw_env.config', f'{image} 0x400000 0x10000\n{image} 0x800000 0x10000\n')
    put(work / 'fw_seed', 'sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A B\nBOOT_A_LEFT=3\nBOOT_B_LEFT=0\n')
    run(['fw_setenv', '-c', work / 'fw_env.config', '-f', work / 'fw_seed', '-s', work / 'fw_seed'])
    return {'guest_sha256': digest(image), 'base_rauc_sha256': digest(BASE / 'usr/bin/rauc'),
            'cockpit_delta_sha256': {item['file']: item['sha256'] for item in json.loads((REPO / 'configs/host-os/cockpit-packages.json').read_text())['delta']}}


def wait_for_cockpit(process, log, port=19091):
    import urllib.error
    import urllib.request
    for _ in range(180):
        if process.poll() is not None:
            raise RuntimeError('QEMU exited before Cockpit was ready')
        if _ < 35:
            time.sleep(1)
            continue
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/cockpit/login', timeout=1) as response:
                if response.status in (200, 401):
                    return
        except urllib.error.HTTPError as error:
            if error.code == 401:
                return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError('Timed out waiting for loopback Cockpit')


def execute(work):
    report = prepare(work)
    kernel = BASE / 'boot/vmlinuz-6.12.107+deb13-arm64'
    initrd = BASE / 'boot/initrd.img-6.12.107+deb13-arm64'
    if not CHROME.is_file() or not kernel.is_file() or not initrd.is_file():
        raise RuntimeError('Reviewed local Chromium/kernel/initrd input is unavailable')
    log = work / 'boot.log'
    command = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a53', '-smp', '2', '-m', '1024',
        '-display', 'none', '-monitor', 'none', '-serial', 'file:' + str(log), '-no-reboot', '-kernel', kernel, '-initrd', initrd,
        '-append', 'root=/dev/vda2 ro rootwait console=ttyAMA0 ip=dhcp systemd.volatile=overlay sv08.test=rauc-backend rauc.slot=A',
        '-drive', f'file={work / "guest.img"},format=raw,if=none,id=root',
        '-device', 'virtio-blk-device,drive=root,serial=SV08-QEMU-DISPOSABLE',
        '-netdev', 'user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:19091-:9090',
        '-device', 'virtio-net-pci,netdev=net0']
    with log.open('w') as stream:
        process = subprocess.Popen([str(item) for item in command], stdout=stream, stderr=subprocess.STDOUT)
    try:
        wait_for_cockpit(process, log)
        run(['node', REPO / 'tests/cockpit_composed_browser.mjs', work, CHROME], timeout=240)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=20)
    browser = json.loads((work / 'composed-result.json').read_text())
    if not browser.get('passed'):
        raise RuntimeError('Composed browser journey did not pass')
    report.update(browser=browser['composed'], browser_result_sha256=digest(work / 'composed-result.json'),
                  boot_log_sha256=digest(log), source_commit=run(['git', 'rev-parse', 'HEAD'], capture_output=True,
                  text=True).stdout.strip(), physical_hardware=False)
    put(work / 'result.json', json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    work = args.work.resolve()
    if not args.execute:
        print(json.dumps({'execute': False, 'requires': ['selected ignored ARM64 root', 'hash-pinned Cockpit intake',
              'QEMU', 'root private fixture'], 'hardware': False}, indent=2))
        return
    if os.geteuid() != 0 or work.exists() or not work.is_relative_to(REPO / 'build') or not BASE.is_dir() or not INTAKE.is_dir():
        raise SystemExit('Use root, a fresh build/ directory, and reviewed local inputs')
    work.mkdir(mode=0o700)
    print(json.dumps(execute(work), indent=2))


if __name__ == '__main__':
    main()
