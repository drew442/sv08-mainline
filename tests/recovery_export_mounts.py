#!/usr/bin/env python3
"""Real read-only source / disposable loop-FAT export. Run in private mount NS."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from sv08_export import Export

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work',type=Path,required=True)
parser.add_argument('--execute',action='store_true')
args=parser.parse_args();repo=Path(__file__).resolve().parents[1];work=args.work.absolute()
if not work.is_relative_to(repo/'build') or work.exists():parser.error('Use a fresh disposable build directory')
if not args.execute:
    print(json.dumps({'execute':False,'work':str(work)}));sys.exit()
if os.geteuid()!=0 or os.readlink('/proc/self/ns/mnt')==os.readlink('/proc/1/ns/mnt'):
    parser.error('Use sudo unshare --mount --propagation private')
work.mkdir();source=work/'source';source.mkdir();target=work/'fat';target.mkdir()
(source/'state.json').write_text('damaged state still exportable')
(source/'printer.cfg').write_text('private fixture configuration')
image=work/'disposable-fat.img'
with image.open('xb') as stream:stream.truncate(64*1024**2)
subprocess.run(['mkfs.vfat','-F','32',str(image)],check=True)
subprocess.run(['mount','--bind',str(source),str(source)],check=True)
try:
    subprocess.run(['mount','-o','remount,bind,ro',str(source)],check=True)
    subprocess.run(['mount','-o','loop,nosuid,nodev,noexec,umask=0077',str(image),str(target)],check=True)
    try:
        @contextmanager
        def admission(target_id):
            assert target_id=='test-fat'
            options=subprocess.check_output(['findmnt','-n','-o','OPTIONS','--mountpoint',str(source)],text=True).strip().split(',')
            assert 'ro' in options
            assert subprocess.check_output(['findmnt','-n','-o','FSTYPE','--mountpoint',str(target)],text=True).strip()=='vfat'
            yield
        exporter=Export(source,{'test-fat':{'path':target,'label':'Disposable loop FAT'}},admission)
        plan=exporter.prepare('test-fat');result=exporter.execute(plan)
        result.update(passed=True,physical_hardware=False,readonly_source=True,destination_filesystem='vfat',
                      inode_accounting=os.statvfs(target).f_files,source_registry_unchanged=(source/'state.json').read_text()=='damaged state still exportable')
        (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:subprocess.run(['umount',str(target)],check=True)
finally:subprocess.run(['umount',str(source)],check=True)
