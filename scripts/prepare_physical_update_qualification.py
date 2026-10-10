#!/usr/bin/env python3
"""Compose OFFLINE slot pairs for a reviewed physical update qualification.

Default only validates inputs and prints the recipe. --execute copies a public
board root, installs the supplied pinned ARM RAUC package, refreshes upstream
integration/UI, and builds healthy revision 2 / unhealthy revision 3 slot images.
No disk writer, deployment, signing key or fixture verifier is provided. Sign
manifest.raucm and its boot.img/rootfs.img externally with the release authority.
The input profile must explicitly bind context, board identity, all six device
UUIDs, measured factory geometry, compatible and Klipper commit. deployable
describes this test profile only; operation approval remains separate.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit

from integrate_host_os import stage as integrate, validate
from prepare_host_os import REPO
from stage_admin_ui import stage as admin_stage
from stage_printer_ui import payload as printer_payload

CONTEXT = 'physical-update-qualification'
MASKS = ('sv08-klipper', 'klipper', 'sv08-moonraker', 'moonraker', 'KlipperScreen')
SIZES = {'boot': 192 * 1024**2, 'rootfs': 2048 * 1024**2}
WRAPPER = '''#!/usr/bin/python3
import os, sys
if sys.argv[1:] == ['is-active', 'sv08-prepare.service']:
    print('inactive')
    raise SystemExit(3)
os.execv('/usr/bin/systemctl', ['systemctl', *sys.argv[1:]])
'''


def run(*args):
    subprocess.run([str(x) for x in args], check=True, timeout=900)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''): h.update(block)
    return h.hexdigest()


def destination(root, relative):
    path = root / relative
    for parent in (path, *path.parents):
        if parent == root: break
        if parent.is_symlink(): raise ValueError('Symlink in staging destination: ' + str(parent))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def put(root, relative, content, mode=0o644):
    path = destination(root, relative)
    path.write_text(content)
    path.chmod(mode)


def regular(path):
    if path.is_symlink() or not path.is_file() or not path.stat().st_size:
        raise ValueError('Expected nonempty regular public input: ' + str(path))


def profile_check(profile):
    board = json.loads((REPO / 'configs/host-os/recovery-test-sv08-01.json').read_text())
    devices = {p['role']: '/dev/disk/by-partuuid/' + p['partuuid'] for p in board['partitions']}
    layout = json.loads((REPO / 'configs/images/host-ab.json').read_text())
    geometry = {p['name']: p['mib'] * 1024**2 for p in layout['partitions']}
    if (profile.get('format_version') != 1 or profile.get('context') != CONTEXT or
            profile.get('hardware_profile') != 'test-sv08-01' or
            profile.get('board_mmc_device_index') != 1 or type(profile.get('board_mmc_device_index')) is not int or
            profile.get('environment_device') != '/dev/mmcblk2' or
            profile.get('environment_by_path') != '/dev/disk/by-path/platform-4022000.mmc' or
            profile.get('devices') != devices or
            profile.get('kernel_release') != board['kernel_release'] or
            profile.get('layout') != 'ab-8gb-v1' or
            profile.get('image_bytes') != layout['image_bytes'] or
            profile.get('partition_bytes') != geometry):
        raise ValueError('Explicit matching physical identity and factory geometry required')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', profile.get('compatible', '')) or profile['compatible'].startswith('sv08-offline'):
        raise ValueError('Explicit physical compatible required')
    if not re.fullmatch('[0-9a-f]{40}', profile.get('klipper_commit', '')):
        raise ValueError('Explicit pinned Klipper commit required')
    return board


def configure(root, profile, release, revision, feed, unhealthy):
    manifest = dict(release=release, release_revision=revision, state_schema=1,
                    deployable=True, devices=profile['devices'], qualification_context=CONTEXT,
                    hardware_profile=profile['hardware_profile'], test_only=True)
    policy = dict(compatible=profile['compatible'], layout='ab-8gb-v1', state_schema=1,
                  klipper_commit=profile['klipper_commit'], max_bundle_bytes=1073741824,
                  image_bytes=SIZES)
    environment = json.loads((REPO / 'configs/host-os/environment-layout.json').read_text())
    environment['board_mmc_device_index'] = profile['board_mmc_device_index']
    for name, value in [('release.json', manifest), ('update-policy.json', policy),
                        ('environment.json', environment), ('feed.json', feed),
                        ('layout.json', json.loads((REPO / 'configs/images/host-ab.json').read_text()))]:
        put(root, 'usr/lib/sv08/' + name, json.dumps(value, indent=2) + '\n')
    text = (REPO / 'configs/host-os/rauc-system.conf.in').read_text().replace('@COMPATIBLE@', policy['compatible'])
    for role in ('root-a', 'root-b', 'boot-a', 'boot-b'):
        text = text.replace('@' + role.upper().replace('-', '_') + '@', manifest['devices'][role])
    put(root, 'etc/rauc/system.conf', text)
    # The backend opens O_NOFOLLOW: use the independently observed canonical
    # Linux node, never the identity symlink or the U-Boot MMC index.
    put(root, 'etc/fw_env.config', ''.join(profile['environment_device'] + ' ' + offset + ' 0x10000\n'
                                          for offset in ('0x400000', '0x800000')))
    for name in MASKS:
        path = root / 'etc/systemd/system' / (name + '.service')
        if path.parent.is_symlink(): raise ValueError('Symlink in unit destination')
        if path.exists() or path.is_symlink(): path.unlink()
        path.symlink_to('/dev/null')
    for name in ('rauc', 'sv08-boot-health'):
        path = root / 'etc/systemd/system' / (name + '.service')
        if path.is_symlink() and os.readlink(path) == '/dev/null': path.unlink()
    # Reviewed test-only account binding: absent server-local seed fails closed.
    put(root, 'etc/systemd/system/sv08-qualification-account.service',
        '[Unit]\nDescription=Bind qualification account authentication\n'
        'Requires=sv08-prepare.service\nAfter=sv08-prepare.service\n'
        'Before=sv08-identity.service ssh.service cockpit.socket cockpit.service\n'
        '[Service]\nType=oneshot\n'
        'ExecStart=/usr/bin/mount --bind /data/sv08/system/qualification-account-shadow /etc/shadow\n'
        'RemainAfterExit=yes\n')
    for consumer in ('sv08-identity.service', 'ssh.service', 'cockpit.socket', 'cockpit.service'):
        put(root, 'etc/systemd/system/' + consumer + '.d/qualification-account.conf',
            '[Unit]\nRequires=sv08-qualification-account.service\nAfter=sv08-qualification-account.service\n')
    if unhealthy:
        put(root, 'usr/lib/sv08/qualification-bin/systemctl', WRAPPER, 0o755)
        put(root, 'etc/systemd/system/sv08-boot-health.service.d/qualification.conf',
            '[Service]\nEnvironment="PATH=/usr/lib/sv08/qualification-bin:/usr/bin:/bin"\n')
    return manifest, policy



def copy_public_root(source, target):
    """Preserve numeric ownership without importing source authentication secrets."""
    target.mkdir()
    producer = subprocess.Popen(['tar', '--exclude=./etc/shadow', '--exclude=./etc/gshadow',
        '--exclude=ssh_host_*', '--exclude=.ssh', '--exclude=./root',
        '--exclude=./etc/ssl/private', '--exclude=./etc/credstore*',
        '--exclude=./etc/NetworkManager/system-connections', '--exclude=./var/lib/NetworkManager',
        '--exclude=./var/lib/private', '--exclude=./var/cache/private', '--exclude=./var/log/private',
        '--exclude=./run/*', '--exclude=./data/*',
        '-C', str(source), '-cf', '-', '.'], stdout=subprocess.PIPE)
    consumer = subprocess.Popen(['tar', '--numeric-owner', '-C', str(target), '-xf', '-'],
                                stdin=producer.stdout)
    producer.stdout.close()
    try:
        consumer.wait(timeout=900)
        producer.wait(timeout=900)
        if consumer.returncode or producer.returncode:
            raise ValueError('Public root copy failed')
    finally:
        for process in (consumer, producer):
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
    # Locked synthetic accounts; live password persistence is coordinator-owned.
    passwd = (target / 'etc/passwd').read_text().splitlines()
    put(target, 'etc/shadow', ''.join(line.split(':')[0] + ':*:0:0:99999:7:::\n'
                                    for line in passwd if line), 0o600)


def stage_printer_capabilities(root, validation_dictionary=None):
    """Use the public image payload builder; production overlay guards stay intact."""
    files = printer_payload(validation_dictionary)
    # All backend preimages must match integration before any payload write.
    for relative, raw in files.items():
        target = destination(root, relative)
        if relative.startswith('usr/lib/sv08/') and (not target.is_file() or target.read_bytes() != raw):
            raise ValueError('Printer payload backend differs from current integrated runtime: ' + relative)
    for relative, raw in files.items():
        if relative.startswith('usr/lib/sv08/'): continue
        target = destination(root, relative)
        target.write_bytes(raw); target.chmod(0o644)
    return {relative:hashlib.sha256(raw).hexdigest() for relative,raw in files.items()}


def compose(a):
    regular(a.profile)
    profile = json.loads(a.profile.read_text()); board = profile_check(profile)
    if a.context != CONTEXT: raise ValueError('Explicit physical qualification context required')
    for path in (a.rauc_deb, a.keyring, a.owner_key, a.feed_config, a.tls_ca): regular(path)
    if a.validation_dictionary is not None:
        regular(a.validation_dictionary)
        printer_payload(a.validation_dictionary)  # Enforce the pinned public dictionary before a large copy.
    expected_package = json.loads((REPO / 'configs/host-os/rauc-package.json').read_text())
    package = subprocess.check_output(['dpkg-deb', '-f', str(a.rauc_deb), 'Package', 'Version', 'Architecture'], text=True, timeout=30)
    fields = dict(line.split(': ', 1) for line in package.splitlines())
    if fields != {'Package': 'rauc', 'Version': expected_package['version'], 'Architecture': 'arm64'}:
        raise ValueError('Supplied RAUC package differs from pinned ARM package')
    if a.board_root.is_symlink() or not a.board_root.is_dir(): raise ValueError('Public board root required')
    feed = json.loads(a.feed_config.read_text())
    if (set(feed) != {'format_version', 'url', 'channel', 'ca_file', 'signer_ca_file'} or
            feed['format_version'] != 1 or urlsplit(feed['url']).scheme != 'https' or
            not urlsplit(feed['url']).netloc or not feed['url'].endswith('/') or
            urlsplit(feed['url']).query or urlsplit(feed['url']).fragment or
            not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', feed['channel'])):
        raise ValueError('Fixed HTTPS feed configuration required')
    source_manifest_path = a.board_root / 'usr/lib/sv08/release.json'
    regular(source_manifest_path)
    source_manifest = json.loads(source_manifest_path.read_text())
    validate({**source_manifest, 'deployable': False})
    source_revision = source_manifest.get('release_revision', 1)
    if source_manifest['devices'] != profile['devices'] or source_revision != 1:
        raise ValueError('Bootstrap source must match physical partitions and revision 1')
    public_passwd = a.board_root / 'etc/passwd'
    regular(public_passwd)
    accounts = [line.split(':') for line in public_passwd.read_text().splitlines()]
    owners = [record for record in accounts if record[0] == 'sv08']
    if len(owners) != 1 or owners[0][2:4] != ['1000', '1000'] or owners[0][5:7] != ['/home/sv08', '/bin/bash']:
        raise ValueError('Public source owner identity differs from reviewed UID/GID/home/shell')
    package_release = a.board_root / 'usr/share/doc/sv08-klipper/release.json'
    regular(package_release)
    if json.loads(package_release.read_text()).get('source_commit') != profile['klipper_commit']:
        raise ValueError('Physical profile differs from packaged Klipper source')
    feed['ca_file'] = '/etc/sv08/feed-ca.pem'; feed['signer_ca_file'] = '/etc/rauc/release-keyring.pem'
    for role in ('image', 'dtb'):
        path = a.board_root / board['artifacts'][role]['path']; regular(path)
        if sha(path) != board['artifacts'][role]['sha256']: raise ValueError('Board artifact mismatch: ' + role)
    regular(a.board_root / ('boot/initrd.img-' + board['kernel_release']))
    for release in (a.healthy_release, a.unhealthy_release):
        validate(dict(release=release, state_schema=1, deployable=False, devices=profile['devices']))
    if a.healthy_release == a.unhealthy_release: raise ValueError('Distinct release identifiers required')
    if a.work.exists() or a.work.is_symlink(): raise ValueError('Use a fresh isolated output directory')
    if a.board_root.resolve() == a.work.resolve() or a.board_root.resolve() in a.work.resolve().parents:
        raise ValueError('Output must be outside public board root')
    plan = dict(context=CONTEXT, execute=a.execute, work=str(a.work), image_bytes=SIZES,
                releases=[dict(release=a.healthy_release, revision=2, healthy=True),
                          dict(release=a.unhealthy_release, revision=3, healthy=False)],
                deployable_scope='reviewed physical qualification only', signed=False,
                writes=['isolated copied rootfs', 'boot.img', 'rootfs.img', 'manifest.raucm'],
                recipe=['copy public root preserving ownership, exclude source authentication secrets', 'install pinned ARM RAUC deb',
                        'refresh integrate_host_os and regenerate matching initramfs',
                        'stage current public printer payload, then refresh stage_admin_ui and bind actual RAUC service identity',
                        'emit bootstrap source preserving revision 1',
                        'mask physical printer services in both slot roots',
                        'build healthy revision 2 and health-observation-only unhealthy revision 3',
                        'fsck both slot pairs; sign bundle directories externally'],
                signing_inputs=['healthy/bundle', 'unhealthy/bundle'],
                environment_binding=dict(device=profile['environment_device'], by_path=profile['environment_by_path'],
                    preflight='coordinator must recheck by-path identity resolves to the canonical whole root device'),
                account_preservation=dict(server_local_path='/data/sv08/system/qualification-account-shadow',
                    creation='coordinator-only 0600 no-clobber copy; never included in artifacts',
                    bootstrap_live_shadow_overwrite=False, missing_seed='authentication consumers fail closed',
                    limitation='password atomic replacement on the bind mount is not qualified'))
    if not a.execute: return plan
    if os.geteuid() != 0: raise ValueError('Root required for offline ownership-preserving composition')
    a.work.mkdir(mode=0o700, parents=True)
    healthy = a.work / 'healthy'; healthy.mkdir()
    copy_public_root(a.board_root, healthy / 'rootfs')
    root = healthy / 'rootfs'
    shutil.copyfile(a.rauc_deb, destination(root, 'tmp/qualification-rauc.deb'))
    run('chroot', root, 'dpkg', '--install', '/tmp/qualification-rauc.deb')
    (root / 'tmp/qualification-rauc.deb').unlink()
    (healthy / 'refresh-complete').touch()
    offline = dict(release=a.healthy_release, release_revision=2, state_schema=1, deployable=False, devices=profile['devices'])
    integrate(healthy, offline, refresh=True, owner_key=a.owner_key)
    plan['printer_payload'] = stage_printer_capabilities(root, a.validation_dictionary)
    admin_stage(healthy, 'host', execute=True, refresh=True)
    for source, relative in [(a.keyring, 'etc/rauc/release-keyring.pem'), (a.tls_ca, 'etc/sv08/feed-ca.pem')]:
        target=destination(root, relative)
        shutil.copyfile(source, target)
    # Save the common refreshed source for coordinator-owned bootstrap of A.
    # Its identity remains the running source release/revision; no slot writer.
    source_release = source_manifest['release']
    bootstrap_manifest, _ = configure(root, profile, source_release, source_revision, feed, False)
    bootstrap = a.work / 'bootstrap'; bootstrap.mkdir()
    run('cp', '-a', root, bootstrap / 'rootfs')
    put(bootstrap, 'release.json', json.dumps(bootstrap_manifest, indent=2)+'\n')
    configure(root, profile, a.healthy_release, 2, feed, False)
    unhealthy = a.work / 'unhealthy'; unhealthy.mkdir()
    run('cp', '-a', root, unhealthy / 'rootfs')
    configure(unhealthy / 'rootfs', profile, a.unhealthy_release, 3, feed, True)
    boot = a.work / 'boot'; (boot / 'dtb').mkdir(parents=True)
    (boot / 'Image').write_bytes(gzip.decompress((root / board['artifacts']['image']['path']).read_bytes()))
    shutil.copyfile(root / board['artifacts']['dtb']['path'], boot / 'dtb/sv08.dtb')
    shutil.copyfile(root / ('boot/initrd.img-' + board['kernel_release']), boot / 'initrd.img')
    if sum(p.stat().st_size for p in boot.rglob('*') if p.is_file()) >= 144 * 1024**2:
        raise ValueError('Boot payload exceeds factory content budget')
    entries = subprocess.check_output(['lsinitramfs', str(boot / 'initrd.img')], text=True, timeout=120).splitlines()
    if 'scripts/local-bottom/sv08-data' not in entries:
        raise ValueError('Regenerated initramfs omits persistent identity/data hook')
    run('mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none', '-n', 'SV08 qualification slot', '-d', REPO / 'configs/host-os/slot-boot.cmd', boot / 'boot.scr')
    for work, release, revision in [(healthy, a.healthy_release, 2), (unhealthy, a.unhealthy_release, 3)]:
        if sum(p.stat().st_size for p in (work/'rootfs').rglob('*') if p.is_file() and not p.is_symlink()) >= 1536 * 1024**2:
            raise ValueError('Root payload exceeds factory content budget')
        bundle = work / 'bundle'; bundle.mkdir()
        for kind, size in SIZES.items():
            image=bundle/(kind+'.img')
            if kind == 'boot' and work == unhealthy:
                # Same board payload and filesystem identity in both updates.
                shutil.copyfile(healthy/'bundle/boot.img', image)
                continue
            with image.open('xb') as stream: stream.truncate(size)
            if kind == 'boot':
                run('mkfs.vfat', '-F', '32', '-n', 'SV08QUAL', image)
                run('mcopy', '-i', image, '-s', *sorted(boot.iterdir()), '::/')
                run('fsck.vfat', '-n', image)
            else:
                run('mkfs.ext4', '-q', '-F', '-m', '1', '-d', work/'rootfs', image)
                run('e2fsck', '-fn', image)
        put(bundle, 'manifest.raucm', f'[update]\ncompatible={profile["compatible"]}\nversion={release}\n[bundle]\nformat=verity\n[image.rootfs]\nfilename=rootfs.img\n[image.boot]\nfilename=boot.img\n[meta.sv08]\nlayout=ab-8gb-v1\nstate-schema=1\nklipper-commit={profile["klipper_commit"]}\nrelease-revision={revision}\n')
    plan['bootstrap'] = dict(path='bootstrap/rootfs', release=source_release, release_revision=source_revision, raw_write=False)
    plan['inputs'] = {str(p):sha(p) for p in (a.profile,a.rauc_deb,a.keyring,a.owner_key,a.feed_config,a.tls_ca,Path(__file__),
        source_manifest_path, public_passwd, package_release, REPO/'configs/host-os/slot-boot.cmd',
        REPO/'scripts/integrate_host_os.py',REPO/'scripts/stage_admin_ui.py',
        REPO/'scripts/stage_printer_ui.py',
        *sorted((REPO/'runtime').glob('*.py')),
        *sorted(p for directory in ('ui/host','ui/printer','catalog/printer') for p in (REPO/directory).rglob('*') if p.is_file()),
        *([a.validation_dictionary] if a.validation_dictionary else []))}
    plan['boot_payloads'] = {str(p.relative_to(boot)):sha(p) for p in boot.rglob('*') if p.is_file()}
    plan['tools'] = {name:subprocess.check_output(command, stderr=subprocess.STDOUT, text=True, timeout=30).strip()
                     for name,command in {'mkimage':['mkimage','-V'], 'mkfs.ext4':['mkfs.ext4','-V'],
                                          'mcopy':['mcopy','-V'], 'dpkg':['dpkg','--version']}.items()}
    plan['artifacts'] = {str(p.relative_to(a.work)):sha(p) for work in (healthy,unhealthy) for p in (work/'bundle/boot.img',work/'bundle/rootfs.img',work/'bundle/manifest.raucm')}
    put(a.work, 'composition.json', json.dumps(plan, indent=2)+'\n')
    return plan


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('board-root','rauc-deb','keyring','owner-key','feed-config','tls-ca','profile','work'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--context', required=True, choices=[CONTEXT])
    p.add_argument('--healthy-release', required=True)
    p.add_argument('--unhealthy-release', required=True)
    p.add_argument('--validation-dictionary', type=Path, help='Optional exact pinned public MCU dictionary for configuration validation')
    p.add_argument('--execute', action='store_true')
    a=p.parse_args()
    print(json.dumps(compose(a), indent=2))


if __name__ == '__main__': main()
