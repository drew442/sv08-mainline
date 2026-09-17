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
 # Stage only fixed QEMU fixture inputs; production paths never select this mode.
 runtime=root/'usr/lib/sv08';runtime.mkdir(parents=True,exist_ok=True)
 for source in (REPO/'runtime').glob('*.py'):shutil.copyfile(source,runtime/source.name)
 def put(path,text,mode=0o644):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);path.chmod(mode)
 manifest={'release':'0.1.0-offline.3','state_schema':1,'deployable':False,'devices':{n:'/dev/disk/by-partuuid/'+v for n,v in UUIDS.items()}}
 policy=json.loads((REPO/'build/rauc-bundle-metadata-v1/policy.json').read_text());env=json.loads((REPO/'configs/host-os/environment-layout.json').read_text());env['board_mmc_device_index']=10
 for name,value in [('release.json',manifest),('update-policy.json',policy),('layout.json',json.loads((REPO/'configs/images/host-ab.json').read_text())),('environment.json',env),('admin-context.json',{'format_version':1,'context':'host'})]:put(runtime/name,json.dumps(value)+'\n')
 put(root/'etc/fstab','rootfs / ext4 ro 0 1\n');put(root/'etc/fw_env.config','/dev/vda 0x400000 0x10000\n/dev/vda 0x800000 0x10000\n')
 conf=(REPO/'configs/host-os/rauc-system.conf.in').read_text()
 for key,name in [('COMPATIBLE','compatible'),('ROOT_A','root-a'),('BOOT_A','boot-a'),('ROOT_B','root-b'),('BOOT_B','boot-b')]:conf=conf.replace('@'+key+'@',policy[name] if key=='COMPATIBLE' else manifest['devices'][name])
 put(root/'etc/rauc/system.conf',conf)
 for src,dst in [(REPO/'configs/host-os/sv08-rauc-policy.conf',root/'etc/dbus-1/system.d/zz-sv08-rauc.conf'),(REPO/'configs/host-os/sv08-rauc-service.conf',root/'etc/systemd/system/rauc.service.d/sv08.conf')]:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 put(root/'usr/lib/systemd/system/rauc.service','[Unit]\nAfter=dbus.service\n[Service]\nType=dbus\nBusName=de.pengutronix.rauc\nExecStart=/usr/bin/rauc --mount=/run/rauc service\n')
 shutil.copyfile(REPO/'configs/host-os/rauc-service-policy.json',runtime/'rauc-service-policy.json')
 put(root/'etc/cockpit/cockpit.conf','[WebService]\nShell=/sv08-host/index.html\nAllowUnencrypted=true\n')
 put(root/'usr/lib/sv08/composed-fixture.py',"""import json\nfrom pathlib import Path\nfrom sv08_state import Store\ns=Store('/data/sv08',reserve_bytes=0);s.initialize();Path('/data/sv08/uploads').mkdir(mode=0o700,exist_ok=True)\nb=s.prepare_boot('A','0.1.0-offline.3');b['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip();Path('/run/sv08').mkdir(exist_ok=True);Path('/run/sv08/boot.json').write_text(json.dumps(b))\nt=Path('/data/sv08/update.json')\nif t.exists():v=json.loads(t.read_text());v['boot_id']=b['boot_id'];t.write_text(json.dumps(v))\n""",0o755)
 put(root/'usr/lib/systemd/system/sv08-composed-fixture.service','[Unit]\nAfter=local-fs.target\nBefore=cockpit.service\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /usr/lib/sv08/composed-fixture.py\n[Install]\nWantedBy=multi-user.target\n')
 put(root/'etc/systemd/system/data.mount','[Mount]\nWhat=/dev/disk/by-partuuid/4773f966-0678-4cf5-bb83-8ee6fb11d8eb\nWhere=/data\nType=ext4\nOptions=rw\n[Install]\nWantedBy=local-fs.target\n')
 for unit in ('cockpit.socket','sv08-composed-fixture.service','data.mount','systemd-networkd.service'):run(['systemctl','--root',root,'enable',unit],stdout=subprocess.DEVNULL)
 put(root/'etc/systemd/network/10-fixture.network','[Match]\nName=enp0s1\n[Network]\nDHCP=yes\n')
 put(w/'credentials.json',json.dumps({'fixtureadmin':'sv08-compose-admin','fixtureordinary':'sv08-compose-user'}),0o600)
 image=w/'guest.img';create_media(image,UUIDS);format_media(image);populate_ext4_partition(image,'root-a',root,w/'parts');populate_ext4_partition(image,'root-b',root,w/'parts');populate_ext4_partition(image,'data',data,w/'parts')
 put(w/'fw_env.config',str(image)+' 0x400000 0x10000\n'+str(image)+' 0x800000 0x10000\n');put(w/'fw_seed','sv08_env_layout=ab-8gb-v1\nBOOT_ORDER=A B\nBOOT_A_LEFT=3\nBOOT_B_LEFT=0\n');run(['fw_setenv','-c',w/'fw_env.config','-f',w/'fw_seed','-s',w/'fw_seed'])
 print(json.dumps({'image':str(image),'deployable':False,'browser':'tests/cockpit_composed_browser.mjs'},indent=2))
if __name__=='__main__':main()
