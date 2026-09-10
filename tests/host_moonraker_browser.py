#!/usr/bin/env python3
"""Run the packaged ARM64 Moonraker/browser fixture in an isolated namespace.

Invoke through sudo unshare --mount --net --pid --fork --mount-proc. Defaults to
inspection; accepts build-directory fixtures only, with deployable=false.
"""
from pathlib import Path
import argparse,subprocess,os,json,time,urllib.request,shutil
p=argparse.ArgumentParser(description=__doc__)
for name in ('rootfs','output','node','chrome','dist'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--execute',action='store_true')
a=p.parse_args()
repo=Path(__file__).resolve().parents[1]
for value in (a.rootfs,a.output,a.dist):
    if not value.resolve().is_relative_to(repo/'build'):raise ValueError('Use disposable build paths')
if not a.execute:
    print('Inspection only: isolated packaged API/browser fixture');raise SystemExit(0)
root=a.rootfs.resolve()
assert os.geteuid()==0 and os.getpid()==1, "Run as PID 1 inside the requested unshare fixture"
assert json.loads((root/'usr/lib/sv08/release.json').read_text())['deployable'] is False
assert [link['ifname'] for link in json.loads(subprocess.check_output(['ip','-j','link'],text=True))]==['lo']
data=root/'tmp/sv08-browser-api-fixture'
output=a.output.resolve()
assert not data.exists() and not output.exists()
subprocess.run(['ip','link','set','lo','up'],check=True)
subprocess.run(['mount','--make-rprivate','/'],check=True)
subprocess.run(['mount','-t','proc','proc',str(root/'proc')],check=True)
for name in ['config','logs','comms','gcodes']: (data/name).mkdir(parents=True,exist_ok=True)
(data/'config/moonraker.conf').write_text('[server]\nhost: 127.0.0.1\nport: 7125\nklippy_uds_address: /tmp/sv08-browser-api-fixture/comms/absent-klippy.sock\n[machine]\nprovider: none\n[file_manager]\nenable_object_processing: False\n[authorization]\ntrusted_clients:\n  127.0.0.1\ncors_domains:\n  http://127.0.0.1:*\n')
for p in [data,*data.rglob('*')]:os.chown(p,1000,1000)
output.mkdir()
log=(output/'moonraker.log').open('w')
child=subprocess.Popen(['chroot','--userspec=1000:1000',str(root),'/opt/sv08-mainline/venvs/moonraker-985c1d0/bin/python','/opt/sv08-mainline/moonraker/moonraker/moonraker.py','-d','/tmp/sv08-browser-api-fixture','-l','/tmp/sv08-browser-api-fixture/logs/moonraker.log'],stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
try:
 for _ in range(900):
  if child.poll() is not None:raise RuntimeError('Moonraker exited; inspect log')
  try:
   with urllib.request.urlopen('http://127.0.0.1:7125/server/info',timeout=1) as response:info=json.load(response)
   break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Moonraker did not start')
 (output/'server-info.json').write_text(json.dumps(info,indent=2)+'\n')
 assert not info['result']['failed_components'] and not info['result']['warnings']
 subprocess.run([str(a.node.resolve()),str(repo/'tests/mainsail_browser_startup.mjs'),'--execute',str(a.chrome.resolve()),str(a.dist.resolve()),str(output/'browser'),'7125'],check=True,timeout=90)
finally:
 child.terminate()
 try:child.wait(timeout=10)
 except subprocess.TimeoutExpired:child.kill();child.wait()
 log.close()
 shutil.rmtree(data)
 subprocess.run(['umount',str(root/'proc')],check=True)
