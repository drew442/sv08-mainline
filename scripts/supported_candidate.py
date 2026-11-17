"""Supported named-printer composition policy; never deployment authority.

Public inputs bind the measured medium and pinned board artifacts. Credentials
and per-printer identity are created on the device, outside immutable images.
"""
import hashlib
import json
from pathlib import Path
import re
import stat
import sys

from prepare_host_os import REPO, layout
sys.path.insert(0, str(REPO/'runtime'))

FIELDS = {'format_version', 'purpose', 'hardware_profile', 'release',
          'release_revision', 'project_source_revision', 'compatible',
          'expected_cid_sha256', 'board_mmc_device_index', 'klipper_commit'}


def profile_check(value):
    from integrate_host_os import validate
    from sv08_printer_calibration import KLIPPER_REVISION
    if (not isinstance(value, dict) or set(value) != FIELDS or
            type(value['format_version']) is not int or value['format_version'] != 1 or
            value['purpose'] != 'supported-configured-printer-candidate' or
            value['hardware_profile'] != 'test-sv08-01' or
            type(value['board_mmc_device_index']) is not int or value['board_mmc_device_index'] != 1 or
            value['klipper_commit'] != KLIPPER_REVISION or
            not re.fullmatch('[0-9a-f]{40}', value['project_source_revision']) or
            not re.fullmatch('[0-9a-f]{64}', value['expected_cid_sha256']) or
            not re.fullmatch(r'sv08-test-sv08-01-[A-Za-z0-9._-]{1,48}', value['compatible'])):
        raise ValueError('Explicit supported target, measured CID and pinned source required')
    board = json.loads((REPO/'configs/host-os/recovery-test-sv08-01.json').read_text())
    manifest = dict(release=value['release'], release_revision=value['release_revision'],
                    state_schema=1, deployable=True, owner_setup='recovery-v1',
                    commissioning='explicit-v1', hardware_profile=value['hardware_profile'],
                    project_source_revision=value['project_source_revision'],
                    klipper_commit=value['klipper_commit'],
                    devices={p['role']: '/dev/disk/by-partuuid/'+p['partuuid'] for p in board['partitions']})
    validate(manifest, supported=True)
    return manifest


def backend_documents(profile):
    manifest = profile_check(profile)
    config = json.loads((REPO/'configs/images/host-ab.json').read_text())
    layout(config)
    environment = json.loads((REPO/'configs/host-os/environment-layout.json').read_text())
    environment['board_mmc_device_index'] = profile['board_mmc_device_index']
    policy = dict(compatible=profile['compatible'], layout='ab-8gb-v1', state_schema=1,
                  klipper_commit=profile['klipper_commit'], max_bundle_bytes=1073741824,
                  image_bytes={'boot': 192*1024**2, 'rootfs': 2048*1024**2})
    identity = dict(format_version=1, identity_path='/dev/disk/by-path/platform-4022000.mmc',
                    expected_cid_sha256=profile['expected_cid_sha256'])
    return {'release.json': manifest, 'layout.json': config, 'environment.json': environment,
            'environment-device.json': identity, 'update-policy.json': policy,
            'supported-profile.json': profile}


def rauc_configuration(profile):
    manifest = profile_check(profile)
    text = (REPO/'configs/host-os/rauc-system.conf.in').read_text().replace('@COMPATIBLE@', profile['compatible'])
    for role in ('root-a', 'root-b', 'boot-a', 'boot-b'):
        text = text.replace('@'+role.upper().replace('-', '_')+'@', manifest['devices'][role])
    if '@' in text: raise ValueError('Unrendered supported RAUC configuration')
    return text


def regular(root, relative):
    path = root/relative
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Linked supported image input: '+relative)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1024*1024:
        raise ValueError('Invalid supported image input: '+relative)
    return path.read_bytes()


def public_account_checks(root):
    """No inherited login, host identity or network secrets in a public root."""
    accounts = [line.split(':') for line in regular(root, 'etc/passwd').decode().splitlines()]
    owners = [row for row in accounts if row[0] == 'sv08']
    if (len(owners) != 1 or len(owners[0]) != 7 or owners[0][2:4] != ['1000', '1000'] or
            any(int(row[2]) >= 1000 and row[0] not in ('sv08', 'nobody') for row in accounts)):
        raise ValueError('Supported image requires only the fixed sv08 owner account')
    shadow = [line.split(':') for line in regular(root, 'etc/shadow').decode().splitlines()]
    if any(len(row) != 9 or row[1] not in ('', '*', '!', '!*', '!!') for row in shadow):
        raise ValueError('Supported image contains an inherited account password')
    # Empty passwords are never an acceptable shipped account, including root.
    if any(not row[1] for row in shadow): raise ValueError('Supported account must be locked')
    owner = [row for row in shadow if row[0] == 'sv08']
    if len(owner) != 1 or owner[0][2] != '' or any(owner[0][i] for i in (6, 7, 8)):
        raise ValueError('Supported owner aging must allow PAM login without forced password writes')
    if regular(root, 'etc/machine-id').strip() or regular(root, 'usr/lib/sv08/seed/authorized_keys').strip():
        raise ValueError('Supported image must not contain an owner key or machine identity')
    for relative in ('etc/NetworkManager/system-connections', 'var/lib/NetworkManager',
                     'etc/cockpit/ws-certs.d', 'etc/ssl/private'):
        directory = root/relative
        if directory.is_symlink() or directory.exists() and any(directory.iterdir()):
            raise ValueError('Supported image contains private state: '+relative)
    for pattern in ('etc/ssh/ssh_host_*', 'home/*/.ssh/authorized_keys', 'root/.ssh/*'):
        if any(root.glob(pattern)): raise ValueError('Supported image contains inherited SSH access/identity')
    if (root/'home/sovol').exists(): raise ValueError('Historical pilot owner tree is not a supported baseline')
    for path in (root/'usr/lib/sv08').glob('*'):
        if any(token in path.name for token in ('qualification', 'qemu-probe', 'stack-disposable')):
            raise ValueError('Disposable qualification inputs must not ship')
    units = root/'etc/systemd/system'
    if any('qualification' in str(p.relative_to(units)) or 'qemu-probe' in p.name for p in units.rglob('*')):
        raise ValueError('Disposable service fixture must not ship')
    return dict(owner_locked=True, owner_key_absent=True, inherited_identity_absent=True)


def public_certificate(certificate):
    import subprocess
    if certificate is None: raise ValueError('Public release certificate is required')
    path = Path(certificate)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError('Public release certificate must be a bounded regular file')
    raw = path.read_bytes()
    if b'PRIVATE KEY' in raw or raw.count(b'-----BEGIN CERTIFICATE-----') != 1:
        raise ValueError('Supply exactly one public release authority certificate')
    result = subprocess.run(['openssl', 'x509', '-in', str(path), '-outform', 'PEM'],
                            check=True, capture_output=True, timeout=10)
    if raw.strip() != result.stdout.strip():
        raise ValueError('Release certificate must contain only the public PEM certificate')
    return raw


def install_backend(root, profile, certificate):
    """Called only by explicit supported integration after public preconditions."""
    raw = public_certificate(certificate)
    for name, document in backend_documents(profile).items():
        if name == 'release.json': continue  # Integration adds the immutable MCU assignment.
        (root/'usr/lib/sv08'/name).write_text(json.dumps(document, indent=2)+'\n')
    directory = root/'etc/rauc'; directory.mkdir(exist_ok=True)
    (directory/'system.conf').write_text(rauc_configuration(profile))
    (directory/'release-keyring.pem').write_bytes(raw)
    (root/'etc/fw_env.config').write_text('# Bound read-only at boot after physical identity verification.\n')
    return hashlib.sha256(raw).hexdigest()
