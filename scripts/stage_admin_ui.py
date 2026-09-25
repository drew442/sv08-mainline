#!/usr/bin/env python3
"""Stage UI files into an isolated image root; no package installation/activation.

Both modes require the separately built core/runtime and OS dependencies. Run
this after core integration. Do not treat staged UI files as a bootable image.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from prepare_host_os import REPO, work_path


def stage(work, context, execute=False, refresh=False):
    if context not in ('host', 'recovery'): raise ValueError('Unknown UI context')
    if refresh and context != 'host':
        raise ValueError('UI refresh is only supported for the host context')
    root = work / 'rootfs'
    if root.is_symlink() or not root.is_dir(): raise ValueError('Expected an isolated image rootfs')
    for name in ('sv08_state.py', 'sv08_admin.py', 'sv08_admin_images.py', 'sv08_admin_jobs.py', 'sv08_admin_resolution.py', 'sv08_rauc_service.py', 'sv08_admin_upload.py', 'sv08_staging.py', 'sv08_bundle.py', 'sv08_rauc.py', 'sv08_boot.py', 'sv08_export.py', 'sv08_recovery.py', 'sv08_recovery_media.py', 'sv08_recovery_ui.py'):
        path = root / 'usr/lib/sv08' / name
        if not path.is_file() or path.read_bytes() != (REPO / 'runtime' / name).read_bytes():
            raise ValueError('Stage the matching reviewed core runtime before UI integration: '+name)
    target = root / ('usr/share/cockpit/sv08-host' if context == 'host' else 'usr/share/xsessions/sv08-recovery.desktop')
    target_exists = target.exists() or target.is_symlink()
    if target_exists:
        if not refresh:
            raise ValueError('UI already staged; use a fresh root')
        if target.is_symlink() or not target.is_dir():
            raise ValueError('Existing host UI target is not a regular directory')
    extra = [root / 'usr/lib/systemd/system' / ('sv08-admin-image-worker@.service' if context == 'host' else 'sv08-recovery-display.service')]
    if context == 'host':
        extra.extend([root / 'etc/cockpit/cockpit.conf', root / 'usr/lib/sv08/admin-context.json', root / 'usr/lib/sv08/rauc-service-policy.json', root / 'etc/dbus-1/system.d/zz-sv08-rauc.conf', root / 'etc/systemd/system/rauc.service.d/sv08.conf'])
        cert_dir = root / 'etc/cockpit/ws-certs.d'
        extra.append(cert_dir)
        persistent_cert_dir = '/data/sv08/system/cockpit/ws-certs.d'
        if cert_dir.is_symlink():
            if os.readlink(cert_dir) != persistent_cert_dir:
                raise ValueError('Unexpected Cockpit certificate directory link')
        elif cert_dir.exists():
            if not cert_dir.is_dir() or any(cert_dir.iterdir()):
                raise ValueError('Cockpit certificate directory must be empty before persistence staging')
        packages = root / 'usr/share/cockpit'
        allowed_packages = {'base1', 'static', 'branding', 'issue', 'motd'}
        if refresh:
            allowed_packages.add('sv08-host')
        if packages.is_dir() and any(p.name not in allowed_packages for p in packages.iterdir()):
            raise ValueError('Unexpected Cockpit packages; use the reviewed ws/bridge-only root')
    for path in [target, *extra]:
        for parent in [path, *path.parents]:
            if parent == root: break
            if parent.is_symlink():
                if (context == 'host' and path == root / 'etc/cockpit/ws-certs.d' and
                        parent == path and os.readlink(parent) == '/data/sv08/system/cockpit/ws-certs.d'):
                    continue
                raise ValueError('Symlink in UI staging target: '+str(parent))
        if path.exists() or path.is_symlink():
            if context == 'host' and path == root / 'etc/cockpit/ws-certs.d':
                if path.is_symlink() and os.readlink(path) == '/data/sv08/system/cockpit/ws-certs.d':
                    continue
                if path.is_dir() and not any(path.iterdir()):
                    continue
            allowed_refresh_output = refresh and (
                path == target or (not path.is_symlink() and path.is_file()))
            if not allowed_refresh_output:
                raise ValueError('Existing UI/configuration conflicts with staging: '+str(path))
    if not execute: return dict(execute=False, context=context, root=str(root))
    if context == 'host':
        if target_exists:
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(REPO / 'ui/host', target)
        target.chmod(0o755)
        config = root / 'etc/cockpit/cockpit.conf'; config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('[WebService]\nShell=/sv08-host/index.html\n')
        cert_dir = root / 'etc/cockpit/ws-certs.d'
        if cert_dir.exists() and not cert_dir.is_symlink():
            cert_dir.rmdir()
        if not cert_dir.is_symlink():
            cert_dir.symlink_to('/data/sv08/system/cockpit/ws-certs.d')
        units = root / 'usr/lib/systemd/system'; units.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'configs/host-os/sv08-admin-image-worker@.service', units / 'sv08-admin-image-worker@.service')
        for source, destination in [('rauc-service-policy.json', 'usr/lib/sv08/rauc-service-policy.json'), ('sv08-rauc-policy.conf', 'etc/dbus-1/system.d/zz-sv08-rauc.conf'), ('sv08-rauc-service.conf', 'etc/systemd/system/rauc.service.d/sv08.conf')]:
            path = root / destination; path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / 'configs/host-os' / source, path)
        (root / 'usr/lib/sv08/admin-context.json').write_text(json.dumps(dict(format_version=1, context='host'))+'\n')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'configs/host-os/recovery-session.desktop', target)
        units = root / 'usr/lib/systemd/system'; units.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'configs/host-os/sv08-recovery-display.service', units / 'sv08-recovery-display.service')
    files = [p for p in (target.rglob('*') if target.is_dir() else [target]) if p.is_file()]
    if context == 'host': files.extend(root / name for name in ('etc/cockpit/cockpit.conf', 'usr/lib/sv08/rauc-service-policy.json', 'etc/dbus-1/system.d/zz-sv08-rauc.conf', 'etc/systemd/system/rauc.service.d/sv08.conf'))
    for path in files: path.chmod(0o644)
    files.extend(root / 'usr/lib/sv08' / name for name in
                 ('sv08_state.py', 'sv08_admin.py', 'sv08_admin_images.py', 'sv08_admin_jobs.py', 'sv08_admin_resolution.py', 'sv08_rauc_service.py', 'sv08_admin_upload.py', 'sv08_staging.py', 'sv08_bundle.py', 'sv08_rauc.py', 'sv08_boot.py', 'sv08_export.py', 'sv08_recovery.py', 'sv08_recovery_media.py', 'sv08_recovery_ui.py'))
    if context == 'host': files.append(root / 'usr/lib/systemd/system/sv08-admin-image-worker@.service')
    files.append(root / ('usr/lib/sv08/admin-context.json' if context == 'host' else
                         'usr/lib/systemd/system/sv08-recovery-display.service'))
    hashes = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    if context == 'host':
        hashes['etc/cockpit/ws-certs.d'] = hashlib.sha256(
            os.readlink(root / 'etc/cockpit/ws-certs.d').encode()).hexdigest()
    return dict(execute=True, context=context, activated=False,
                payload_bytes=sum(p.stat().st_size for p in files), hashes=hashes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--context', choices=['host', 'recovery'], required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--refresh', action='store_true',
                        help='Replace reviewed host UI files in a copied image root')
    args = parser.parse_args()
    print(json.dumps(stage(work_path(args.work), args.context, args.execute, args.refresh), indent=2))
