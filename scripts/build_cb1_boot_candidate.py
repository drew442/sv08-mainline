#!/usr/bin/env python3
"""Compile an explicitly unverified CB1 boot-source candidate; default inspection.

This fills source/fit/capacity validation around pinned upstream builds. No image
assembly or hardware writes. Retire when the reviewed board build pipeline owns
these checks. The compiled DRAM/PMIC/GPIO configuration is not hardware evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from prepare_host_os import REPO, work_path


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('work','uboot_archive','tfa_archive','patch_directory'):
        p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    config=json.loads((REPO/'configs/host-os/cb1-boot-compile-candidate.json').read_text())
    if config['deployable'] is not False or config['board_mmc_device_index'] is not None:
        raise ValueError('This builder is exclusively an unverified compile fixture')
    work=work_path(a.work)
    if work.exists():raise ValueError('Use a fresh build directory')
    archives=[(a.uboot_archive,'u_boot','u-boot-source'),(a.tfa_archive,'tf_a','tf-a-source')]
    for archive,key,_ in archives:
        if sha(archive)!=config[key]['archive_sha256']:raise ValueError('Source archive hash mismatch')
    for patch in config['board_patches']:
        if sha(a.patch_directory/patch['name'])!=patch['sha256']:raise ValueError('Board patch hash mismatch')
    print(json.dumps(dict(execute=a.execute,deployable=False,work=str(work),config=config)))
    if not a.execute:return
    work.mkdir(parents=True)
    for archive,_,name in archives:
        temporary=work/(name+'-unpack');temporary.mkdir()
        with tarfile.open(archive) as tar:tar.extractall(temporary,filter='data')
        children=list(temporary.iterdir())
        if len(children)!=1 or not children[0].is_dir():raise ValueError('Expected a single source root')
        children[0].rename(work/name);temporary.rmdir()
    env=dict(os.environ,SOURCE_DATE_EPOCH=str(config['source_date_epoch']),
        UBOOT_BUILD_USER='sv08',UBOOT_BUILD_HOST='offline',GIT_CEILING_DIRECTORIES=str(work))
    def run(log_name,*args):
        with (work/log_name).open('a') as log:
            subprocess.run([str(x) for x in args],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    tfa=work/'tf-a-source';uboot=work/'u-boot-source'
    run('tf-a-build.log','make','-C',tfa,'-j2','CROSS_COMPILE=aarch64-linux-gnu-',
        'PLAT='+config['tf_a']['platform'],'DEBUG='+str(config['tf_a']['debug']),
        'BUILD_STRING='+config['tf_a']['commit'],'BUILD_MESSAGE_TIMESTAMP="'+config['build_timestamp']+'"','bl31')
    bl31=tfa/'build/sun50i_h616/debug/bl31.bin'
    for patch in config['board_patches']:
        run('u-boot-build.log','patch','--batch','--forward','-d',uboot,'-p1','-i',(a.patch_directory/patch['name']).resolve())
    run('u-boot-build.log','make','-C',uboot,'CROSS_COMPILE=aarch64-linux-gnu-',config['u_boot']['defconfig'])
    run('u-boot-build.log','make','-C',uboot,'-j2','CROSS_COMPILE=aarch64-linux-gnu-','BL31='+str(bl31))
    binary=uboot/'u-boot-sunxi-with-spl.bin';fit=uboot/'u-boot-sunxi-with-spl.fit.fit'
    if binary.read_bytes()[4:12]!=b'eGON.BT0' or 8192+binary.stat().st_size>1048576:
        raise ValueError('SPL header or reserved bootloader capacity check failed')
    run('fit-inspection.log',uboot/'tools/dumpimage','-l',fit)
    for node in ('/images/uboot','/images/atf','/images/fdt-1','/configurations/config-1'):
        run('fit-inspection.log','fdtget','-p',fit,node)
    artifacts=work/'artifacts';artifacts.mkdir()
    for source in (binary,bl31,uboot/'.config',fit,uboot/'u-boot-sunxi-with-spl.map'):
        shutil.copyfile(source,artifacts/source.name)
    result=dict(config=config,deployable=False,physical_hardware=False,
        spl_header_valid=True,reservation_bytes=[8192,1048576],
        compiler=subprocess.check_output(['aarch64-linux-gnu-gcc','--version'],text=True).splitlines()[0],
        artifacts={f.name:dict(bytes=f.stat().st_size,sha256=sha(f)) for f in artifacts.iterdir()},
        ab_policy_integrated=False,licenses_fully_audited=False)
    (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
