#!/usr/bin/env python3
"""Read-only actual filesystem/metadata inspection of the recovery candidate."""
import argparse
import json
import os
import errno
import stat
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from recovery_image import clean_path,separate,private,run,sha,inventory,write,KERNEL


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--assembly',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    build=clean_path(a.build);source=clean_path(a.assembly);work=clean_path(a.work,output=True);separate(work,build,source)
    if work.exists():raise ValueError('Fresh inspection output required')
    result=json.loads((build/'build.json').read_text());image=clean_path(build/'recovery.ext4')
    if sha(image)!=result['image_sha256']:raise ValueError('Candidate changed')
    if not a.execute:print(json.dumps(dict(execute=False,read_only=True)));return
    private();work.mkdir(parents=True,mode=0o700);envelope=work/'envelope';usr=work/'usr';envelope.mkdir();usr.mkdir();mounts=[]
    try:
        run(['mount','-t','ext4','-o','loop,ro,noload',image,envelope]);mounts.append(envelope)
        run(['mount','-t','squashfs','-o','loop,ro,nodev',envelope/'usr.squashfs',usr]);mounts.append(usr)
        expected=inventory(source/'rootfs/usr');observed=inventory(usr,empty_xattr_reference=source/'rootfs/usr')
        if expected!=observed:raise AssertionError('Compressed runtime content/mode/uid/gid differs from assembly')
        xattrs=[];unsupported_empty=0
        for f in [source/'rootfs/usr',*sorted((source/'rootfs/usr').rglob('*'))]:
            attrs=os.listxattr(f,follow_symlinks=False)
            other=usr/f.relative_to(source/'rootfs/usr')
            try:other_attrs=os.listxattr(other,follow_symlinks=False)
            except OSError as error:
                if error.errno!=errno.EOPNOTSUPP or attrs:raise
                other_attrs=[];unsupported_empty+=1
            if sorted(attrs)!=sorted(other_attrs):raise AssertionError('xattr names differ')
            for name in attrs:
                if os.getxattr(f,name,follow_symlinks=False)!=os.getxattr(other,name,follow_symlinks=False):raise AssertionError('xattr value differs')
                xattrs.append([str(f.relative_to(source/'rootfs/usr')),name])
        # Compare the physical ext4 envelope, including root metadata and every
        # copied package path; only mkfs-created lost+found is additional.
        expected_envelope=build/'envelope';links_a={};links_b={};count=0
        for original in [expected_envelope,*sorted(expected_envelope.rglob('*'))]:
            relative=original.relative_to(expected_envelope);actual=envelope/relative
            x=original.lstat();y=actual.lstat()
            if (x.st_mode,x.st_uid,x.st_gid)!=(y.st_mode,y.st_uid,y.st_gid):raise AssertionError('Envelope metadata differs: '+str(relative))
            attrs={n:os.getxattr(original,n,follow_symlinks=False).hex() for n in os.listxattr(original,follow_symlinks=False)}
            other={n:os.getxattr(actual,n,follow_symlinks=False).hex() for n in os.listxattr(actual,follow_symlinks=False)}
            if attrs!=other:raise AssertionError('Envelope xattrs differ: '+str(relative))
            if stat.S_ISLNK(x.st_mode) and os.readlink(original)!=os.readlink(actual):raise AssertionError('Envelope symlink differs')
            if stat.S_ISREG(x.st_mode):
                if sha(original)!=sha(actual):raise AssertionError('Envelope bytes differ')
                if (x.st_nlink,links_a.setdefault((x.st_dev,x.st_ino),str(relative)))!=(y.st_nlink,links_b.setdefault((y.st_dev,y.st_ino),str(relative))):raise AssertionError('Envelope hardlinks differ')
            count+=1
        extras={str(p.relative_to(envelope)) for p in envelope.rglob('*')}-{str(p.relative_to(expected_envelope)) for p in expected_envelope.rglob('*')}
        if extras!={'lost+found'}:raise AssertionError('Unexpected envelope files: '+repr(extras))
        for name,external in [('vmlinuz-'+KERNEL,'vmlinuz'),('initrd-recovery.img','initrd.img')]:
            if sha(envelope/'boot'/name)!=sha(build/external):raise AssertionError('Direct boot artifact differs from filesystem')
        v=os.statvfs(envelope);helper=usr/'lib/dbus-1.0/dbus-daemon-launch-helper';s=helper.stat()
        report=dict(envelope_metadata_paths_verified=count,envelope_extra_paths=sorted(extras),usr_inventory=observed,usr_matches_assembly=True,preserved_xattrs=xattrs,xattr_api_unsupported_with_empty_source=unsupported_empty,
                    free_blocks=v.f_bfree,block_size=v.f_frsize,free_bytes=v.f_bfree*v.f_frsize,
                    free_inodes=v.f_ffree,total_inodes=v.f_files,total_blocks=v.f_blocks,
                    dbus_helper=dict(uid=s.st_uid,gid=s.st_gid,mode=oct(s.st_mode&0o7777)),
                    kernel_identical=True,initrd_identical=True,
                    registry_exists=(envelope/'data/sv08').exists(),
                    mounts=Path('/proc/self/mountinfo').read_text().splitlines())
        write(work/'inspection.json',json.dumps(report,indent=2)+'\n')
    finally:
        for path in reversed(mounts):run(['umount',path])
    if sha(image)!=result['image_sha256']:raise AssertionError('Read-only inspection changed candidate')
    print(json.dumps(dict(passed=True,free_bytes=report['free_bytes'],usr_matches_assembly=True)))
if __name__=='__main__':main()
