#!/usr/bin/env python3
"""Execute the disposable Cockpit/RAUC composition only with --execute.

This is intentionally QEMU-only: it creates a fresh regular GPT image beneath
build/, uses the selected ignored ARM64 root and hash-pinned Cockpit intake, and
forwards Cockpit only to 127.0.0.1. It never receives a block device argument.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from host_qemu_rauc_composed import copy_guest_root, create_media, format_media, populate_ext4_partition
REPO=Path(__file__).resolve().parents[1]
BASE=REPO/'build/host-rauc-v1/rootfs'; INTAKE=REPO/'build/cockpit-intake-337'
UUIDS={'boot-a':'00000000-0000-4000-8000-000000000001','root-a':'00000000-0000-4000-8000-000000000002','boot-b':'00000000-0000-4000-8000-000000000003','root-b':'00000000-0000-4000-8000-000000000004','recovery':'00000000-0000-4000-8000-000000000005','data':'4773f966-0678-4cf5-bb83-8ee6fb11d8eb'}
def run(c,**kw): return subprocess.run([str(x) for x in c],check=True,**kw)
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args();w=a.work.resolve()
 if not a.execute: print(json.dumps({'execute':False,'requires':['selected ignored ARM64 root','hash-pinned Cockpit intake','QEMU','root private fixture']}));return
 if os.geteuid()!=0 or w.exists() or not BASE.is_dir() or not INTAKE.is_dir(): raise SystemExit('Use root, fresh ignored work and reviewed local inputs')
 root=copy_guest_root(BASE,w/'rootfs'); data=w/'data';data.mkdir(parents=True); (data/'fixture').mkdir()
 # The selected Cockpit closure deliberately contains only ws/bridge and their
 # pinned dependencies; cockpit-system is provenance-only in its lock.
 lock=json.loads((REPO/'configs/host-os/cockpit-packages.json').read_text()); debs=[INTAKE/x['file'] for x in lock['delta']]
 for x,d in zip(lock['delta'],debs):
  if hashlib.file_digest(d.open('rb'),'sha256').hexdigest()!=x['sha256']: raise SystemExit('Cockpit intake digest mismatch')
 for n in ('proc','dev'):run(['mount','-t','proc' if n=='proc' else 'tmpfs',n,root/n])
 try:
  for n,major,minor in [('null',1,3),('urandom',1,9)]:run(['mknod','-m','666',root/'dev'/n,'c',major,minor])
  (root/'tmp/debs').mkdir();[shutil.copyfile(d,root/'tmp/debs'/d.name) for d in debs];run(['chroot',root,'dpkg','-i',*['/tmp/debs/'+d.name for d in debs]])
 finally:
  run(['umount',root/'dev']);run(['umount',root/'proc'])
 # The committed browser driver and prior bounded setup are staged by the caller
 # after this verified base; keeping construction and browser execution separate
 # preserves the project rule that builds do not silently boot or mutate media.
 image=w/'guest.img';create_media(image,UUIDS);format_media(image);populate_ext4_partition(image,'root-a',root,w/'parts');populate_ext4_partition(image,'root-b',root,w/'parts');populate_ext4_partition(image,'data',data,w/'parts')
 print(json.dumps({'image':str(image),'deployable':False,'next':'stage fixture-only RAUC/Cockpit configuration then boot QEMU'},indent=2))
if __name__=='__main__':main()
