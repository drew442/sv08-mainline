#!/usr/bin/env python3
"""Build/run a disposable ARM64 Cockpit fixture, never a printer image.

Prepare uses a private mount namespace and exact already-downloaded archives.
Run uses a private network/PID namespace and QEMU restrict=on loopback forwarding.
Both default to inspection. No host packages, binfmt, PAM, or services are changed.
See docs/hardware/host-admin-cockpit.md for the reproducible invocation.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import signal
import stat
import shutil
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from stage_admin_ui import stage
from prepare_host_os import REPO


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, **kwargs)


def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root):
    """Content, mode, ownership and symlink fingerprint; no private contents output."""
    result = hashlib.sha256(); count = size = 0
    for path in sorted(root.rglob('*')):
        stat = path.lstat(); name = str(path.relative_to(root))
        value = os.readlink(path) if path.is_symlink() else digest(path) if path.is_file() else ''
        result.update(json.dumps([name, stat.st_mode, stat.st_uid, stat.st_gid, value]).encode())
        if path.is_file() and not path.is_symlink(): count += 1; size += stat.st_size
    return dict(sha256=result.hexdigest(), files=count, bytes=size)


def namespace(kind):
    if os.geteuid() != 0 or os.readlink('/proc/self/ns/'+kind) == os.readlink('/proc/1/ns/'+kind):
        raise ValueError('Use root in a private '+kind+' namespace (before mounting private /proc)')


def prepare(args):
    lower, work, intake = args.baseline.resolve(), args.work.resolve(), args.intake.resolve()
    for source in (lower, intake):
        if work == source or work in source.parents or source in work.parents:
            raise ValueError('Fixture output must not overlap a source tree')
    packages = json.loads((REPO / 'configs/host-os/cockpit-packages.json').read_text())
    if lower == Path('/') or not (lower / 'var/lib/dpkg/status').is_file(): raise ValueError('Expected selected isolated baseline')
    if work.exists(): raise ValueError('Use a fresh private output directory')
    for package in packages['delta']:
        if digest(intake / package['file']) != package['sha256']: raise ValueError('Package digest mismatch: '+package['package'])
    if not args.execute: return dict(execute=False, packages=len(packages['delta']), work=str(work))
    for name, expected in packages['baseline_sudo']['verified_installed_files'].items():
        path = lower / name
        if digest(path) != expected['baseline_sha256'] or oct(path.stat().st_mode & 0o7777) != expected['baseline_mode']:
            raise ValueError('Selected baseline sudo prerequisite changed: '+name)
    namespace('mnt'); namespace('pid'); namespace('net')
    # Reject provisioned owner identities before any maintainer/chroot execution.
    users = (lower / 'etc/passwd').read_text().splitlines()
    if any(1000 <= int(line.split(':')[2]) < 65534 for line in users): raise ValueError('Baseline contains a real user identity')
    run(['mount', '--make-rprivate', '/'])
    work.mkdir(parents=True, mode=0o700)
    for name in ('upper', 'overlay-work', 'rootfs'): (work / name).mkdir()
    root = work / 'rootfs'; before = inventory(lower)
    run(['mount', '-t', 'overlay', 'overlay', '-o', f'lowerdir={lower},upperdir={work}/upper,workdir={work}/overlay-work', root])
    mounted = [root]
    def mount(command, target): run(command); mounted.append(target)
    def inside(command, **kwargs): return run(['chroot', root, *command], **kwargs)
    try:
        # Entirely fresh runtime/device views. No host device or backup bind mounts.
        for name in ('run', 'tmp', 'dev'):
            mount(['mount', '-t', 'tmpfs', 'tmpfs', root / name], root / name)
        mount(['mount', '-t', 'proc', 'proc', root / 'proc'], root / 'proc')
        for name, major, minor in [('null', 1, 3), ('zero', 1, 5), ('random', 1, 8), ('urandom', 1, 9)]:
            run(['mknod', '-m', '666', root / 'dev' / name, 'c', major, minor])
        # dpkg only consumes the hash-pinned delta; no resolution/network at install.
        (root / 'tmp/debs').mkdir()
        for package in packages['delta']: shutil.copyfile(intake / package['file'], root / 'tmp/debs' / package['file'])
        policy = root / 'usr/sbin/policy-rc.d'
        if policy.exists() and policy.read_text() != '#!/bin/sh\nexit 101\n':
            # Existing selected baseline policy is retained and inspected below.
            if 'exit 101' not in policy.read_text(): raise ValueError('Baseline must inhibit service activation')
        elif not policy.exists(): policy.write_text('#!/bin/sh\nexit 101\n'); policy.chmod(0o755)
        simulation = inside(['apt-get', '-s', '--no-install-recommends', '--no-upgrade', 'install',
                             'cockpit-ws='+packages['version'], 'cockpit-bridge='+packages['version'],
                             'sudo='+packages['baseline_sudo']['Version']], capture_output=True, text=True).stdout
        (work / 'apt-simulation.txt').write_text(simulation)
        planned = set(re.findall(r'^Inst ([^ ]+)', simulation, re.MULTILINE))
        if planned != {p['package'] for p in packages['delta']} or '0 upgraded, 9 newly installed' not in simulation:
            raise ValueError('Pinned resolution differs from reviewed nine-package delta')
        with (work / 'package-install.log').open('w') as log:
            inside(['dpkg', '-i', *['/tmp/debs/'+p['file'] for p in packages['delta']]], stdout=log, stderr=subprocess.STDOUT)
        with (work / 'dpkg-audit.txt').open('w') as output: inside(['dpkg', '--audit'], stdout=output)
        runtime = root / 'usr/lib/sv08'; runtime.mkdir(parents=True, exist_ok=True)
        for path in (REPO / 'runtime').glob('*.py'): shutil.copyfile(path, runtime / path.name)
        staging = stage(work, 'host', True)
        # Fixture-only changes below are never produced by production staging.
        config = root / 'etc/cockpit/cockpit.conf'
        config.write_text(config.read_text()+'AllowUnencrypted=true\n')
        credentials = {name: secrets.token_urlsafe(24) for name in ('fixtureadmin', 'fixtureordinary')}
        with (work / 'credentials.json').open('x') as stream: json.dump(credentials, stream)
        (work / 'credentials.json').chmod(0o600)
        for name, password in credentials.items():
            inside(['useradd', '-m', '-s', '/bin/bash', name])
            inside(['chpasswd'], input=name+':'+password+'\n', text=True)
        inside(['usermod', '-aG', 'sudo', 'fixtureadmin'])
        for path in (root / 'etc/ssh').glob('ssh_host_*'): path.unlink()
        (root / 'etc/machine-id').write_text('')
        (root / 'etc/hostname').write_text('sv08-cockpit-fixture\n')
        (root / 'etc/systemd/network/80-fixture.network').write_text('[Match]\nName=en*\n[Network]\nDHCP=yes\n')
        # A test-only boot service initializes finite disposable state; no adapters,
        # devices, update backend, printer services or shipped credential grants.
        (runtime / 'cockpit-fixture.py').write_text("""import json
from pathlib import Path
from sv08_state import Store
s=Store('/data/sv08',reserve_bytes=0)
s.initialize()
b=s.prepare_boot('A','cockpit-fixture')
b['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
Path('/run/sv08').mkdir(exist_ok=True)
Path('/run/sv08/boot.json').write_text(json.dumps(b))
""")
        (root / 'usr/lib/systemd/system/cockpit-fixture.service').write_text('[Unit]\nDescription=Disposable Cockpit test state\nBefore=cockpit.service\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /usr/lib/sv08/cockpit-fixture.py\nRemainAfterExit=yes\n[Install]\nWantedBy=multi-user.target\n')
        for unit in ('systemd-networkd.service', 'cockpit.socket', 'cockpit-fixture.service'):
            run(['systemctl', '--root', root, 'enable', unit], stdout=subprocess.DEVNULL)
        for unit in ('nginx.service', 'NetworkManager.service', 'ssh.service', 'ssh.socket', 'apt-daily.timer', 'apt-daily-upgrade.timer', 'systemd-timesyncd.service'):
            run(['systemctl', '--root', root, 'mask', unit], stdout=subprocess.DEVNULL)
        with (work / 'units.txt').open('w') as output:
            inside(['systemd-analyze', 'verify', '--man=no', 'cockpit.service', 'cockpit.socket', 'cockpit-session@fixture.service', 'cockpit-fixture.service'], stdout=output, stderr=subprocess.STDOUT)
        closure = inside(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\t${Installed-Size}\n'], capture_output=True, text=True).stdout
        (work / 'installed-packages.tsv').write_text(closure)
        # Unmount volatile content before mkfs copies the tree, so /proc, devices,
        # sockets, temporary packages and host runtime cannot enter the guest.
        while len(mounted) > 1:
            run(['umount', mounted[-1]]); mounted.pop()
        policy_paths = ['etc/sudoers', 'etc/pam.d/sudo', *[str(p.relative_to(lower)) for p in (lower / 'etc/pam.d').glob('common-*')]]
        preserved_policy = all((root / name).read_bytes() == (lower / name).read_bytes() for name in policy_paths)
        cockpit_pam = digest(root / 'etc/pam.d/cockpit') == packages['source_hashes']['ws/etc/pam.d/cockpit']['sha256']
        if not preserved_policy or not cockpit_pam: raise AssertionError('PAM/sudo policy changed')
        root_inventory = inventory(root)
        owned = [root / 'usr/share/cockpit/sv08-host', *(root / 'usr/share/cockpit/sv08-host').iterdir(),
                 runtime, runtime / 'sv08_admin.py', runtime / 'admin-context.json',
                 root / 'etc/cockpit/cockpit.conf', root / 'usr/lib/systemd/system/sv08-admin-image-worker@.service']
        for path in owned:
            if path.stat().st_uid != 0 or path.stat().st_mode & 0o022: raise ValueError('Unsafe staged ownership/mode: '+str(path))
        permissions = {str(p.relative_to(root)): dict(uid=p.stat().st_uid, gid=p.stat().st_gid, mode=oct(p.stat().st_mode & 0o7777)) for p in owned}
        run(['truncate', '-s', '2G', work / 'guest.ext4'])
        run(['mkfs.ext4', '-q', '-F', '-d', root, work / 'guest.ext4'])
        kernel = lower / 'boot/vmlinuz-6.12.107+deb13-arm64'; initrd = lower / 'boot/initrd.img-6.12.107+deb13-arm64'
        report = dict(format_version=1, deployable=False, baseline=before, root=root_inventory, staging=staging,
                      permissions=permissions, pam_and_sudo_policy_preserved=preserved_policy and cockpit_pam,
                      delta_download_bytes=sum(p['bytes'] for p in packages['delta']),
                      kernel=dict(path=str(kernel), sha256=digest(kernel)), initrd=dict(path=str(initrd), sha256=digest(initrd)),
                      image_sha256=digest(work / 'guest.ext4'), baseline_preserved=None,
                      scope='offline full ARM64 QEMU fixture; synthetic accounts; no printer or production activation')
    finally:
        for path in reversed(mounted): run(['umount', path])
    report['baseline_preserved'] = inventory(lower) == before
    if not report['baseline_preserved']: raise AssertionError('Baseline changed')
    (work / 'prepare.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def host_state():
    identities = {}
    for name in ('passwd', 'group', 'shadow', 'gshadow', 'sudoers'):
        path = Path('/etc') / name
        identities[name] = (digest(path), path.stat().st_mode) if path.exists() else None
    units = subprocess.run(['systemctl', 'show', 'cockpit.service', 'cockpit.socket',
                            '-p', 'LoadState', '-p', 'ActiveState', '-p', 'UnitFileState'],
                           capture_output=True, text=True)
    return identities, (units.returncode, units.stdout, units.stderr)


def boot(args):
    work = args.work.resolve(); report = json.loads((work / 'prepare.json').read_text())
    if report.get('deployable') is not False: raise ValueError('Expected a disposable fixture')
    for name in ('kernel', 'initrd'):
        if digest(Path(report[name]['path'])) != report[name]['sha256']: raise ValueError('Boot artifact changed')
    image = work / 'guest.ext4'; image_stat = image.lstat()
    if (not stat.S_ISREG(image_stat.st_mode) or image_stat.st_nlink != 1 or
            image_stat.st_uid != os.geteuid() or image_stat.st_size != 2 * 1024**3 or
            work.stat().st_mode & 0o077): raise ValueError('Expected a private owned regular fixture image')
    if digest(image) != report['image_sha256']: raise ValueError('Fixture image changed; prepare a fresh image')
    if not args.execute: return dict(execute=False, work=str(work), loopback_port=19090)
    namespace('net'); namespace('pid')
    host_before = host_state()
    run(['ip', 'link', 'set', 'lo', 'up'])
    # Host PID is useful only to join this private net namespace with the browser.
    pid = next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('NSpid:'))
    (work / 'namespace-pid').write_text(pid)
    command = ['qemu-system-aarch64', '-M', 'virt', '-cpu', 'cortex-a53', '-m', '1024', '-smp', '2',
               '-kernel', report['kernel']['path'], '-initrd', report['initrd']['path'],
               '-append', 'root=/dev/vda rw console=ttyAMA0 systemd.unit=multi-user.target',
               '-drive', f'file={work}/guest.ext4,format=raw,if=virtio',
               '-netdev', 'user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:19090-:9090',
               '-device', 'virtio-net-pci,netdev=net0', '-display', 'none', '-monitor', 'none',
               '-serial', f'file:{work}/guest.log']
    def interrupted(_signum, _frame): raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    child = subprocess.Popen(command)
    try: child.wait()
    except KeyboardInterrupt: pass
    finally:
        child.terminate()
        try: child.wait(timeout=15)
        except subprocess.TimeoutExpired: child.kill(); child.wait()
        (work / 'namespace-pid').unlink(missing_ok=True)
    host_after = host_state()
    cleanup = dict(execute=True, qemu_stopped=True, private_pid_and_network=True,
                   host_identity_files_preserved=host_before[0] == host_after[0],
                   host_cockpit_units_preserved=host_before[1] == host_after[1], namespace_pid_removed=True)
    (work / 'cleanup.json').write_text(json.dumps(cleanup, indent=2)+'\n')
    if not cleanup['host_identity_files_preserved'] or not cleanup['host_cockpit_units_preserved']:
        raise AssertionError('Workstation identity/service state changed')
    return cleanup


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'boot'))
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--intake', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare(args) if args.operation == 'prepare' else boot(args), indent=2))
