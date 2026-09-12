#!/usr/bin/env python3
"""Stage UI files into an isolated image root; no package installation/activation.

Both modes require the separately built core/runtime and OS dependencies. Run
this after core integration. Do not treat staged UI files as a bootable image.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from prepare_host_os import REPO, work_path


def stage(work, context, execute=False):
    if context not in ('host', 'recovery'): raise ValueError('Unknown UI context')
    root = work / 'rootfs'
    if root.is_symlink() or not root.is_dir(): raise ValueError('Expected an isolated image rootfs')
    for name in ('sv08_state.py', 'sv08_admin.py', 'sv08_admin_images.py', 'sv08_admin_jobs.py', 'sv08_export.py', 'sv08_recovery.py', 'sv08_recovery_media.py', 'sv08_recovery_ui.py'):
        path = root / 'usr/lib/sv08' / name
        if not path.is_file() or path.read_bytes() != (REPO / 'runtime' / name).read_bytes():
            raise ValueError('Stage the matching reviewed core runtime before UI integration: '+name)
    target = root / ('usr/share/cockpit/sv08-host' if context == 'host' else 'usr/share/xsessions/sv08-recovery.desktop')
    if target.exists() or target.is_symlink(): raise ValueError('UI already staged; use a fresh root')
    if not execute: return dict(execute=False, context=context, root=str(root))
    if context == 'host':
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(REPO / 'ui/host', target)
        units = root / 'usr/lib/systemd/system'; units.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'configs/host-os/sv08-admin-image-worker@.service', units / 'sv08-admin-image-worker@.service')
        (root / 'usr/lib/sv08/admin-context.json').write_text(json.dumps(dict(format_version=1, context='host'))+'\n')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'configs/host-os/recovery-session.desktop', target)
        units = root / 'usr/lib/systemd/system'; units.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / 'configs/host-os/sv08-recovery-display.service', units / 'sv08-recovery-display.service')
    files = [p for p in (target.rglob('*') if target.is_dir() else [target]) if p.is_file()]
    files.extend(root / 'usr/lib/sv08' / name for name in
                 ('sv08_state.py', 'sv08_admin.py', 'sv08_admin_images.py', 'sv08_admin_jobs.py', 'sv08_export.py', 'sv08_recovery.py', 'sv08_recovery_media.py', 'sv08_recovery_ui.py'))
    if context == 'host': files.append(root / 'usr/lib/systemd/system/sv08-admin-image-worker@.service')
    files.append(root / ('usr/lib/sv08/admin-context.json' if context == 'host' else
                         'usr/lib/systemd/system/sv08-recovery-display.service'))
    return dict(execute=True, context=context, activated=False,
                payload_bytes=sum(p.stat().st_size for p in files),
                hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--context', choices=['host', 'recovery'], required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(stage(work_path(args.work), args.context, args.execute), indent=2))
