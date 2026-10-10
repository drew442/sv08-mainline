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
from stage_printer_ui import compose_host, NAV, root_lock


def package_service_policy(root):
    """Bind the built RAUC package to this image's service identity policy."""
    policy = json.loads((REPO/'configs/host-os/rauc-service-policy.json').read_text())
    provenance = root/'usr/share/doc/rauc/sv08-source.json'
    if not provenance.exists():
        return policy  # The separately recorded legacy package stays strict.
    expected = json.loads((REPO/'configs/host-os/rauc-package.json').read_text())
    if provenance.is_symlink() or json.loads(provenance.read_text()) != expected:
        raise ValueError('RAUC package provenance differs from the pinned source and patches')
    executable = root/'usr/bin/rauc'
    status = root/'var/lib/dpkg/status'
    if executable.is_symlink() or not executable.is_file() or not status.is_file():
        raise ValueError('Built RAUC package identity is incomplete')
    records = [dict(line.split(': ',1) for line in section.splitlines() if ': ' in line)
               for section in status.read_text().split('\n\n')]
    package = next((r for r in records if r.get('Package') == 'rauc'), {})
    if (package.get('Version') != expected['version'] or package.get('Architecture') != 'arm64' or
            package.get('Status') != 'install ok installed'):
        raise ValueError('Built RAUC package version or architecture differs')
    policy['version'] = expected['version']
    policy['executable_sha256'] = hashlib.sha256(executable.read_bytes()).hexdigest()
    return policy


def stage(work, context, execute=False, refresh=False):
    with root_lock(work / 'rootfs'):
        return _stage(work, context, execute, refresh)


def _stage(work, context, execute=False, refresh=False):
    if context not in ('host', 'recovery'): raise ValueError('Unknown UI context')
    if refresh and context != 'host':
        raise ValueError('UI refresh is only supported for the host context')
    root = work / 'rootfs'
    if root.is_symlink() or not root.is_dir(): raise ValueError('Expected an isolated image rootfs')
    for name in ('sv08_identity.py', 'sv08_state.py', 'sv08_update_policy.py', 'sv08_restart.py', 'sv08_admin.py', 'sv08_admin_images.py', 'sv08_admin_jobs.py', 'sv08_admin_history.py', 'sv08_data_budget.py', 'sv08_admin_resolution.py', 'sv08_rauc_service.py', 'sv08_admin_upload.py', 'sv08_staging.py', 'sv08_bundle.py', 'sv08_rauc.py', 'sv08_rauc_bootloader.py', 'sv08_boot.py', 'sv08_export.py', 'sv08_recovery.py', 'sv08_recovery_media.py', 'sv08_recovery_ui.py'):
        path = root / 'usr/lib/sv08' / name
        if not path.is_file() or path.read_bytes() != (REPO / 'runtime' / name).read_bytes():
            raise ValueError('Stage the matching reviewed core runtime before UI integration: '+name)
        if name == 'sv08_rauc_bootloader.py' and not path.stat().st_mode & 0o111:
            raise ValueError('The RAUC custom bootloader handler must be executable')
    if context == 'host':
        for name in ('sv08_software.py', 'sv08_network.py', 'sv08_admission.py', 'sv08_feed.py', 'sv08_auto_reboot.py', 'sv08_web.py', 'sv08_printer_stack.py', 'sv08_mainsail_access.py'):
            path = root / 'usr/lib/sv08' / name
            if not path.is_file() or path.read_bytes() != (REPO / 'runtime' / name).read_bytes():
                raise ValueError('Stage the matching reviewed core runtime before UI integration: '+name)
    if context == 'host':
        catalog = root / 'usr/lib/sv08/software-catalog.json'
        if catalog.exists() and (catalog.is_symlink() or not catalog.is_file() or catalog.read_bytes() != (REPO / 'configs/host-os/software-catalog.json').read_bytes()):
            raise ValueError('Stage the matching reviewed software catalog before UI integration')
    target = root / ('usr/share/cockpit/sv08-host' if context == 'host' else 'usr/share/xsessions/sv08-recovery.desktop')
    target_exists = target.exists() or target.is_symlink()
    if target_exists:
        if not refresh:
            raise ValueError('UI already staged; use a fresh root')
        if target.is_symlink() or not target.is_dir():
            raise ValueError('Existing host UI target is not a regular directory')
    extra = [root / 'usr/lib/systemd/system' / ('sv08-admin-image-worker@.service' if context == 'host' else 'sv08-recovery-display.service')]
    if context == 'host':
        extra.extend([root / 'usr/lib/sv08/software-catalog.json', root / 'usr/lib/systemd/system/sv08-software-worker@.service'])
        extra.extend([root / 'etc/cockpit/cockpit.conf', root / 'usr/lib/sv08/admin-context.json', root / 'usr/lib/sv08/rauc-service-policy.json', root / 'etc/dbus-1/system.d/zz-sv08-rauc.conf', root / 'etc/systemd/system/rauc.service.d/sv08.conf'])
        extra.extend(root / name for name in ('usr/lib/systemd/system/sv08-feed.service',
                                               'usr/lib/systemd/system/sv08-feed.timer',
                                               'etc/systemd/system/timers.target.wants/sv08-feed.timer'))
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
        allowed_packages = {'base1', 'static', 'branding', 'issue', 'motd', 'sv08-printer'}
        if refresh:
            allowed_packages.add('sv08-host')
        if packages.is_dir() and any(p.name not in allowed_packages for p in packages.iterdir()):
            raise ValueError('Unexpected Cockpit packages; use the reviewed ws/bridge-only root')
    branding = []
    if context == 'host':
        branding = [root / 'usr/share/cockpit/branding/debian' / p.name
                    for p in sorted((REPO / 'configs/host-os/cockpit-branding').iterdir())]
        extra.extend(branding)
    for path in [target, *extra]:
        for parent in [path, *path.parents]:
            if parent == root: break
            if parent.is_symlink():
                if (context == 'host' and path == root / 'etc/cockpit/ws-certs.d' and
                        parent == path and os.readlink(parent) == '/data/sv08/system/cockpit/ws-certs.d'):
                    continue
                if (context == 'host' and refresh and parent == path and
                        path == root / 'etc/systemd/system/timers.target.wants/sv08-feed.timer' and
                        os.readlink(parent) == '/usr/lib/systemd/system/sv08-feed.timer'):
                    continue
                raise ValueError('Symlink in UI staging target: '+str(parent))
        if path.exists() or path.is_symlink():
            if (context == 'host' and refresh and
                    path == root / 'etc/systemd/system/timers.target.wants/sv08-feed.timer' and
                    path.is_symlink() and os.readlink(path) == '/usr/lib/systemd/system/sv08-feed.timer'):
                continue
            if context == 'host' and path == root / 'etc/cockpit/ws-certs.d':
                if path.is_symlink() and os.readlink(path) == '/data/sv08/system/cockpit/ws-certs.d':
                    continue
                if path.is_dir() and not any(path.iterdir()):
                    continue
            allowed_refresh_output = refresh and (
                path == target or (not path.is_symlink() and path.is_file()))
            allowed_branding_output = path in branding and not path.is_symlink() and path.is_file()
            if not (allowed_refresh_output or allowed_branding_output):
                raise ValueError('Existing UI/configuration conflicts with staging: '+str(path))
    if context == 'host' and (root/'usr/share/cockpit/sv08-printer').exists():
        for name in ('app.js','style.css','panel.html'):
            path=root/'usr/share/cockpit/sv08-printer'/name
            if not path.is_file() or path.read_bytes()!=(REPO/'ui/printer'/name).read_bytes():raise ValueError('Stage matching printer assets before integrated host refresh')
    service_policy = package_service_policy(root) if context == 'host' else None
    if not execute: return dict(execute=False, context=context, root=str(root))
    if context == 'host':
        if target_exists:
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(REPO / 'ui/host', target)
        target.chmod(0o755)
        entry=target/'index.html'
        package=root/'usr/share/cockpit/sv08-printer'
        if package.exists():
            for name in ('app.js','style.css','panel.html'):
                if not (package/name).is_file() or (package/name).read_bytes() != (REPO/'ui/printer'/name).read_bytes():
                    raise ValueError('Stage matching printer assets before integrated host refresh')
            entry.write_bytes(compose_host(entry.read_bytes()))
        else:
            entry.write_bytes(entry.read_bytes().replace(NAV,b''))
        config = root / 'etc/cockpit/cockpit.conf'; config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('[WebService]\nShell=/sv08-host/index.html\n')
        cert_dir = root / 'etc/cockpit/ws-certs.d'
        if cert_dir.exists() and not cert_dir.is_symlink():
            cert_dir.rmdir()
        if not cert_dir.is_symlink():
            cert_dir.symlink_to('/data/sv08/system/cockpit/ws-certs.d')
        units = root / 'usr/lib/systemd/system'; units.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'configs/host-os/sv08-admin-image-worker@.service', units / 'sv08-admin-image-worker@.service')
        shutil.copyfile(REPO / 'configs/host-os/systemd/sv08-software-worker@.service', units / 'sv08-software-worker@.service')
        for unit in ('sv08-feed.service', 'sv08-feed.timer'):
            shutil.copyfile(REPO / 'configs/host-os' / unit, units / unit)
        wanted = root / 'etc/systemd/system/timers.target.wants'
        wanted.mkdir(parents=True, exist_ok=True)
        if not (wanted / 'sv08-feed.timer').is_symlink():
            (wanted / 'sv08-feed.timer').symlink_to('/usr/lib/systemd/system/sv08-feed.timer')
        for source, destination in [('rauc-service-policy.json', 'usr/lib/sv08/rauc-service-policy.json'), ('sv08-rauc-policy.conf', 'etc/dbus-1/system.d/zz-sv08-rauc.conf'), ('sv08-rauc-service.conf', 'etc/systemd/system/rauc.service.d/sv08.conf')]:
            path = root / destination; path.parent.mkdir(parents=True, exist_ok=True)
            if source == 'rauc-service-policy.json' and (root/'usr/share/doc/rauc/sv08-source.json').exists():
                path.write_text(json.dumps(service_policy, indent=2)+'\n')
            else:
                shutil.copyfile(REPO / 'configs/host-os' / source, path)
        for destination in branding:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / 'configs/host-os/cockpit-branding' / destination.name, destination)
        for unit in ('cockpit.socket',):
            directory = root / 'etc/systemd/system' / (unit+'.d'); directory.mkdir(parents=True,exist_ok=True)
            (directory/'sv08-identity.conf').write_text('[Unit]\nRequires=sv08-identity.service\nAfter=sv08-identity.service\n')
        shutil.copyfile(REPO / 'configs/host-os/software-catalog.json', root / 'usr/lib/sv08/software-catalog.json')
        (root / 'usr/lib/sv08/admin-context.json').write_text(json.dumps(dict(format_version=1, context='host'))+'\n')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'configs/host-os/recovery-session.desktop', target)
        units = root / 'usr/lib/systemd/system'; units.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'configs/host-os/sv08-recovery-display.service', units / 'sv08-recovery-display.service')
    files = [p for p in (target.rglob('*') if target.is_dir() else [target]) if p.is_file()]
    if context == 'host': files.extend(root / name for name in ('etc/cockpit/cockpit.conf', 'usr/lib/sv08/rauc-service-policy.json', 'etc/dbus-1/system.d/zz-sv08-rauc.conf', 'etc/systemd/system/rauc.service.d/sv08.conf', 'usr/lib/systemd/system/sv08-feed.service', 'usr/lib/systemd/system/sv08-feed.timer'))
    files.extend(branding)
    for path in files: path.chmod(0o644)
    files.extend(root / 'usr/lib/sv08' / name for name in
                 ('sv08_identity.py', 'sv08_state.py', 'sv08_update_policy.py', 'sv08_restart.py', 'sv08_admin.py', 'sv08_admin_images.py', 'sv08_admin_jobs.py', 'sv08_admin_history.py', 'sv08_data_budget.py', 'sv08_admin_resolution.py', 'sv08_rauc_service.py', 'sv08_admin_upload.py', 'sv08_staging.py', 'sv08_bundle.py', 'sv08_rauc.py', 'sv08_rauc_bootloader.py', 'sv08_boot.py', 'sv08_export.py', 'sv08_recovery.py', 'sv08_recovery_media.py', 'sv08_recovery_ui.py'))
    if context == 'host':
        files.append(root / 'usr/lib/systemd/system/sv08-admin-image-worker@.service')
        files.append(root / 'usr/lib/systemd/system/sv08-software-worker@.service')
        files.append(root / 'usr/lib/sv08/software-catalog.json')
    if context == 'host':
        files.extend(root / 'usr/lib/sv08' / name for name in
                     ('sv08_software.py', 'sv08_network.py', 'sv08_admission.py', 'sv08_feed.py', 'sv08_auto_reboot.py', 'sv08_web.py', 'sv08_printer_stack.py', 'sv08_mainsail_access.py'))
    files.append(root / ('usr/lib/sv08/admin-context.json' if context == 'host' else
                         'usr/lib/systemd/system/sv08-recovery-display.service'))
    hashes = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    if context == 'host':
        hashes['etc/cockpit/ws-certs.d'] = hashlib.sha256(
            os.readlink(root / 'etc/cockpit/ws-certs.d').encode()).hexdigest()
        hashes['etc/systemd/system/timers.target.wants/sv08-feed.timer'] = hashlib.sha256(
            os.readlink(root / 'etc/systemd/system/timers.target.wants/sv08-feed.timer').encode()).hexdigest()
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
