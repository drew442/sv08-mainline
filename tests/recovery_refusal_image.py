#!/usr/bin/env python3
"""Construct one disposable negative image; production source is never modified."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from recovery_image import clean_path,separate,private,run,sha,write


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',required=True,type=Path);p.add_argument('--work',required=True,type=Path);p.add_argument('--case',required=True,choices=['missing-manifest','changed-manifest','missing-usr','changed-usr','wrong-uuid','writable-backing','symlink-usr','preassigned-loop']);p.add_argument('--execute',action='store_true');a=p.parse_args()
    source=clean_path(a.build);work=clean_path(a.work,output=True);separate(work,source)
    if work.exists():raise ValueError('Fresh negative output required')
    record=json.loads((source/'build.json').read_text());original=clean_path(source/'recovery.ext4')
    if sha(original)!=record['image_sha256']:raise ValueError('Source candidate changed')
    if not a.execute:print(json.dumps(dict(execute=False,case=a.case)));return
    private();work.mkdir(parents=True,mode=0o700);image=work/'negative.ext4'
    run(['cp','--sparse=always',original,image])
    def debug(command):return run(['debugfs','-w','-R',command,image],capture_output=True,text=True)
    if a.case=='preassigned-loop':
        import gzip
        import shutil
        tree=work/'initrd-tree';tree.mkdir()
        run(['cpio','-id','--no-absolute-filenames'],cwd=tree,input=gzip.decompress((source/'initrd.img').read_bytes()),capture_output=True)
        gate=tree/'init';gate_hash=sha(gate);gate.rename(tree/'verified-init')
        wrapper='#!/bin/sh\n/bin/busybox mount -t proc proc /proc\n/bin/busybox mount -t sysfs sysfs /sys\n/bin/busybox mount -t devtmpfs devtmpfs /dev\n/bin/busybox modprobe loop\n/bin/busybox dd if=/dev/zero of=/spurious bs=4096 count=1\n/bin/busybox losetup -r /dev/loop1 /spurious\necho SV08_TEST_PREASSIGNED_LOOP\n/bin/busybox cat /sys/block/loop1/loop/backing_file /sys/block/loop1/loop/offset /sys/block/loop1/loop/sizelimit /sys/block/loop1/ro\n/bin/busybox umount /dev\n/bin/busybox umount /sys\n/bin/busybox umount /proc\nexec /verified-init\n'
        write(gate,wrapper,0o755)
        names=sorted(str(p.relative_to(tree)) for p in tree.rglob('*'))
        archive=run(['cpio','--null','-o','--format=newc','--reproducible','--owner=0:0'],cwd=tree,input=('\0'.join(['.',*names])+'\0').encode(),capture_output=True).stdout
        (work/'initrd.img').write_bytes(gzip.compress(archive,mtime=0));shutil.copyfile(source/'vmlinuz',work/'vmlinuz')
        image.rename(work/'recovery.ext4');image=work/'recovery.ext4'
        record['initrd_sha256']=sha(work/'initrd.img');record['test_fixture']=dict(case=a.case,unchanged_gate_sha256=gate_hash,wrapper_sha256=sha(gate),production_initrd_sha256=sha(source/'initrd.img'))
        write(work/'build.json',json.dumps(record,indent=2)+'\n');shutil.rmtree(tree)
    elif a.case=='missing-manifest':debug('rm /etc/sv08/recovery-envelope.manifest')
    elif a.case=='missing-usr':debug('rm /usr.squashfs')
    elif a.case=='wrong-uuid':debug('set_super_value uuid 164ed891-6ec4-4a95-8762-e32c91260394')
    elif a.case=='symlink-usr':
        debug('rm /usr.squashfs');debug('symlink /usr.squashfs /boot/vmlinuz-6.12.107+deb13-arm64')
    elif a.case in ('changed-manifest','changed-usr'):
        path='/etc/sv08/recovery-envelope.manifest' if a.case=='changed-manifest' else '/usr.squashfs'
        result=run(['debugfs','-R','bmap '+path+' 0',image],capture_output=True,text=True)
        block=int(result.stdout.strip())
        if block<=0:raise ValueError('Expected allocated first data block')
        with image.open('r+b') as f:
            f.seek(block*4096);value=f.read(1);f.seek(block*4096);f.write(bytes([value[0]^1]));f.flush();os.fsync(f.fileno())
    if sha(original)!=record['image_sha256']:raise AssertionError('Source changed')
    write(work/'negative.json',json.dumps(dict(case=a.case,source_sha256=record['image_sha256'],negative_sha256=sha(image),bytes=image.stat().st_size),indent=2)+'\n')
    print(json.dumps(dict(case=a.case,image=str(image))))
if __name__=='__main__':main()
