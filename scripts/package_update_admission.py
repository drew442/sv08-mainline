#!/usr/bin/env python3
"""Build a separate pinned Klipper extension package without enabling it.

The package owns an extra-module symlink in the installed Klipper tree; it never
edits the upstream checkout or replaces a core source file.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from prepare_host_os import REPO, work_path


def build(work, execute=False):
    config = json.loads((REPO / 'configs/apps/update-admission.json').read_text())
    source = REPO / config['source']
    if hashlib.sha256(source.read_bytes()).hexdigest() != config['source_sha256']:
        raise ValueError('Extension differs from reviewed source hash')
    klipper = json.loads((REPO / 'configs/apps/klipper.json').read_text())
    if (config['klipper_commit'] != klipper['source_commit'] or
            config['klipper_package_version'] != klipper['version']):
        raise ValueError('Extension requires a matching reviewed Klipper package')
    if work.exists():
        raise ValueError('Use a new disposable build directory')
    if not execute:
        return dict(execute=False, work=str(work), package=config['name'])
    work.mkdir(parents=True)
    root = work / 'package'
    extra = root / 'usr/lib/sv08/klipper-extras/sv08_update.py'
    extra.parent.mkdir(parents=True); shutil.copyfile(source, extra)
    link = root / 'opt/sv08-mainline/klipper/klippy/extras/sv08_update.py'
    link.parent.mkdir(parents=True); link.symlink_to('/usr/lib/sv08/klipper-extras/sv08_update.py')
    doc = root / 'usr/share/doc/sv08-update-admission'; doc.mkdir(parents=True)
    (doc / 'release.json').write_text(json.dumps(config, indent=2)+'\n')
    (doc / 'README').write_text('Offline candidate. Enabling [sv08_update] requires reviewed host integration.\n'
        'No configuration, service activation or MCU firmware is installed.\n')
    meta = root / 'DEBIAN'; meta.mkdir()
    size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())
    (meta / 'control').write_text(f"Package: {config['name']}\nVersion: {config['version']}\nArchitecture: all\n"
        'Maintainer: SV08 Mainline project <noreply@localhost>\nSection: misc\nPriority: optional\n'
        f"Depends: sv08-klipper (= {config['klipper_package_version']})\nInstalled-Size: {(size+1023)//1024}\n"
        'Description: Local atomic idle admission for the pinned Klipper host\n'
        ' Provides a separately packaged extension; no activation or MCU changes.\n')
    epoch = config['source_date_epoch']
    for path in sorted(root.rglob('*'), reverse=True): os.utime(path, (epoch, epoch), follow_symlinks=False)
    os.utime(root, (epoch, epoch))
    output = work / f"{config['name']}_{config['version']}_all.deb"
    subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(root), str(output)],
                   check=True, env=dict(os.environ, SOURCE_DATE_EPOCH=str(epoch)))
    result = dict(config=config, package=output.name,
                  sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  enables_extension=False, changes_mcu=False)
    (work/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    print(json.dumps(build(work_path(a.work), a.execute), indent=2))
