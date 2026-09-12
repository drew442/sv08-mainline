#!/usr/bin/env python3
"""Full ARM64 read-only recovery VM; disposable files, unix QMP, no network.

Inspection by default. QMP/input evidence is separate from physical input evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import tempfile
import stat
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from recovery_image import clean_path, separate, private, sha, write, SIZE

class QMP:
    def __init__(self,path):
        self.sock=socket.socket(socket.AF_UNIX);self.sock.settimeout(5);self.sock.connect(str(path));self.file=self.sock.makefile('rwb');self.read();self.call('qmp_capabilities')
    def read(self):return json.loads(self.file.readline())
    def call(self,command,arguments=None):
        deadline=time.monotonic()+10
        self.file.write((json.dumps(dict(execute=command,arguments=arguments or {}))+'\n').encode());self.file.flush()
        while True:
            if time.monotonic()>deadline:raise TimeoutError('QMP command deadline')
            response=self.read()
            if 'error' in response:raise ValueError(response)
            if 'return' in response:return response['return']
    def key(self,*keys):
        self.call('input-send-event',dict(events=[dict(type='key',data=dict(down=True,key=dict(type='qcode',data=k))) for k in keys]))
        self.call('input-send-event',dict(events=[dict(type='key',data=dict(down=False,key=dict(type='qcode',data=k))) for k in reversed(keys)]))
    def click(self,x,y):
        self.call('input-send-event',dict(events=[dict(type='abs',data=dict(axis='x',value=int(x*32767/1024))),dict(type='abs',data=dict(axis='y',value=int(y*32767/768))),dict(type='btn',data=dict(down=True,button='left'))]))
        self.call('input-send-event',dict(events=[dict(type='btn',data=dict(down=False,button='left'))]))
    def touch(self,x,y):
        # QEMU8.2 InputMultiTouchEvent -> Linux ABS_MT_SLOT/TRACKING_ID/
        # POSITION_X/Y and BTN_TOUCH, routed to the direct virtio touch device.
        def mtt(kind,axis,value,tracking):
            return dict(type='mtt',data={'type':kind,'slot':0,'tracking-id':tracking,'axis':axis,'value':value})
        self.call('input-send-event',dict(device='video0',events=[
            dict(type='btn',data=dict(down=True,button='touch')),
            mtt('begin','x',0,1),mtt('data','x',int(x*32767/1024),1),mtt('data','y',int(y*32767/768),1)]))
        time.sleep(.15)
        self.call('input-send-event',dict(device='video0',events=[mtt('end','x',0,-1),dict(type='btn',data=dict(down=False,button='touch'))]))
    def shot(self,path):self.call('screendump',dict(filename=str(path)))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',required=True,type=Path);p.add_argument('--work',required=True,type=Path);p.add_argument('--execute',action='store_true');p.add_argument('--seconds',type=int,default=240);p.add_argument('--image',type=Path);p.add_argument('--binding');p.add_argument('--inputs',action='store_true');p.add_argument('--writable',action='store_true',help='Negative test only: writable disposable copy, never production candidate');a=p.parse_args()
    if not 5 <= a.seconds <= 600:raise ValueError('VM duration must be5..600 seconds')
    source=clean_path(a.build);work=clean_path(a.work,output=True);separate(work,source)
    image=clean_path(a.image) if a.image else clean_path(source/'recovery.ext4');separate(work,image)
    if work.exists():raise ValueError('Fresh VM output required')
    report=json.loads((source/'build.json').read_text())
    if not stat.S_ISREG(image.stat().st_mode):raise ValueError('Regular candidate file required')
    if image.stat().st_size!=SIZE:raise ValueError('Expected512MiB regular recovery image')
    if a.image is None and sha(image)!=report['image_sha256']:raise ValueError('Candidate image changed')
    for name in ('vmlinuz','initrd.img'):
        key='kernel_sha256' if name=='vmlinuz' else 'initrd_sha256'
        artifact=clean_path(source/name)
        if not stat.S_ISREG(artifact.stat().st_mode):raise ValueError('Regular boot artifact required')
        if sha(artifact)!=report[key]:raise ValueError('Boot artifact changed')
    if a.writable:
        owners={0,int(os.environ.get('SUDO_UID',os.getuid()))}
        if image.stat().st_uid not in owners:raise ValueError('Writable copy is not owned by caller/root')
        for ancestor in image.parents:
            if ancestor.stat().st_uid not in owners or ancestor.stat().st_mode & 0o002:raise ValueError('Untrusted writable image ancestry')
            if ancestor==Path(__file__).resolve().parents[1]/'build':break
        if a.image is None or not image.is_relative_to(Path(__file__).resolve().parents[1]/'build') or image.stat().st_nlink!=1:
            raise ValueError('Writable negative test requires separate owned single-link image')
        for candidate in source.rglob('*'):
            if candidate.is_file() and os.path.samefile(candidate,image):raise ValueError('Writable input aliases a build artifact')
    if not a.execute:print(json.dumps(dict(execute=False,root=str(image),memory_mib=768,network=False)));return
    private()
    # Match /proc to this PID namespace before sampling the guest process.
    subprocess.run(['mount','-t','proc','proc','/proc'],check=True,timeout=10)
    work.mkdir(parents=True,mode=0o700)
    endpoint=Path(tempfile.mkdtemp(prefix='sv08-recovery-'))
    endpoint.chmod(0o700);qmp=endpoint/'qmp.sock'
    before=sha(image);log=(work/'serial.log').open('wb')
    command=['qemu-system-aarch64','-machine','virt','-cpu','cortex-a53','-accel','tcg,thread=multi','-smp','2','-m','768','-kernel',str(source/'vmlinuz'),'-initrd',str(source/'initrd.img'),'-append','console=ttyAMA0 root=/dev/vda ro sv08.envelope='+(a.binding or report['manifest_sha256'])+' systemd.log_target=console systemd.show_status=yes','-drive','if=none,id=recovery,format=raw,file='+str(image)+',readonly='+('off' if a.writable else 'on'),'-device','virtio-blk-pci,drive=recovery','-device','virtio-gpu-pci,id=video0,xres=1024,yres=768','-device','virtio-multitouch-pci,display=video0','-device','qemu-xhci','-device','usb-kbd','-device','usb-mouse','-device','usb-tablet','-nic','none','-display','none','-serial','stdio','-qmp','unix:'+str(qmp)+',server=on,wait=off','-no-reboot']
    write(work/'command.json',json.dumps(command,indent=2)+'\n')
    process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    peak=0;started=time.monotonic();q=None;ready=False
    try:
        while process.poll() is None and time.monotonic()-started<a.seconds:
            try:
                status=Path('/proc')/str(process.pid)/'status'
                for line in status.read_text().splitlines():
                    if line.startswith('VmRSS:'):peak=max(peak,int(line.split()[1])*1024)
            except FileNotFoundError:pass
            if q is None and qmp.exists():q=QMP(qmp)
            serial=(work/'serial.log').read_text(errors='replace')
            for line in serial.splitlines():
                if 'SV08_RECOVERY_BOOT_REPORT ' not in line:continue
                try:boot=json.loads(line.split('SV08_RECOVERY_BOOT_REPORT ',1)[1])
                except json.JSONDecodeError:continue
                ready=('ActiveState=active' in boot['display_unit'] and 'SubState=running' in boot['display_unit'] and not boot['failed_units'] and any('sv08_recovery_ui.py' in p['command'] for p in boot['processes']) and 'SpiRegistry daemon is running' in serial)
            if ready and q:
                time.sleep(2);break
            time.sleep(1)
        actions=[];mice=[]
        if q and process.poll() is None:
            mice=q.call('query-mice')
            q.shot(work/'display.ppm')
            if a.inputs:
                if not ready:raise AssertionError('Installed display/accessibility readiness deadline expired')
                def step(name,action):
                    action();time.sleep(2);q.shot(work/(name+'.ppm'));actions.append(name)
                step('keyboard-tab',lambda:q.key('tab'))
                step('keyboard-shift-tab',lambda:q.key('shift','tab'))
                step('keyboard-review',lambda:q.key('alt','c'))
                step('keyboard-cancel',lambda:q.key('esc'))
                # Coordinates are for the explicit1024x768 VM profile and are
                # reviewed against the initial real installed UI screenshot.
                step('mouse-review',lambda:q.click(250,300))
                step('diagnostic-apply',lambda:(q.key('tab'),q.key('ret')))
                step('touch-refresh',lambda:q.touch(760,300))
                step('touch-review',lambda:q.touch(250,300))
                step('touch-cancel',lambda:q.touch(360,470))
                step('touch-review-again',lambda:q.touch(250,300))
                step('touch-apply',lambda:q.touch(650,470))
        write(work/'run.json',json.dumps(dict(seconds=time.monotonic()-started,peak_qemu_rss_bytes=peak,ram_mib=768,installed_service_and_accessibility_ready=ready,exit_code=process.poll(),image_before_sha256=before,boot_id_independent_process=True,input_steps=actions,virtual_pointers=mice,independent_touch_events_injected=all(name in actions for name in ('touch-refresh','touch-review','touch-cancel','touch-review-again','touch-apply'))),indent=2)+'\n')
    finally:
        if process.poll() is None:
            if q:
                try:q.call('quit')
                except (ValueError,OSError):pass
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        log.close()
        if qmp.exists() and stat.S_ISSOCK(qmp.lstat().st_mode):qmp.unlink()
        endpoint.rmdir()
    if a.inputs and len(actions)!=11:raise AssertionError('Requested input journey incomplete')
    after=sha(image)
    if after!=before:raise AssertionError('Recovery candidate changed')
    report=json.loads((work/'run.json').read_text());report.update(image_after_sha256=after,image_preserved=True)
    write(work/'run.json',json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
