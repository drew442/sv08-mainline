#!/usr/bin/env python3
"""Build a nondeployable recovery-to-RAM-writer FIT and one-shot selector.

Custom gap: the existing recovery UI cannot launch the already reviewed
trusted writer without moving the eMMC. Retire this composer if the normal
host image builder gains a supported, independently tested handoff facility.
This command writes only a fresh ignored local/ directory, never boot media.
"""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import zlib

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.build_sd_network_image import (append_commissioning_initramfs,
                                            boot_script, commissioning_bundle)

MARKER = b'SV08-REIMAGE-ONCE\n'
FIT_ADDR = 0x48000000
MARKER_ADDR = 0x4f800000
ORIGINAL_ADDR = 0x4fd00000
FIT_MAX_BYTES = 64 * 1024 * 1024


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(path):
    path = path.resolve(strict=True)
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f'Regular input required: {path}')
    return path


def script_text(job_id, bootargs, fit_size, fit_crc, *,
                fit_addr=FIT_ADDR, marker_addr=MARKER_ADDR,
                original_addr=ORIGINAL_ADDR, boot_command=None):
    if not re.fullmatch(r'[a-z0-9-]{1,64}', job_id):
        raise ValueError('Invalid job ID for recovery selector')
    if '"' in bootargs or '\n' in bootargs:
        raise ValueError('Invalid boot arguments')
    if boot_command is None:
        boot_command = f'bootm {fit_addr:#x}'
    return f'''# One-shot recovery writer; every failed check loads the original UI.
if test "${{sv08_reimage_arm}}" = "{job_id}" && test "${{sv08_env_layout}}" = "ab-8gb-v1" && test "${{BOOT_ORDER}}" = "A B" && test "${{BOOT_A_LEFT}}" = "0" && test "${{BOOT_B_LEFT}}" = "0"; then
 if load mmc ${{sv08_mmcdev}}:5 {marker_addr:#x} sv08-reimage/armed; then
  if test ${{filesize}} = {len(MARKER):x}; then
   if crc32 -v {marker_addr:#x} ${{filesize}} {zlib.crc32(MARKER):08x}; then
    if load mmc ${{sv08_mmcdev}}:5 {fit_addr:#x} sv08-reimage/writer.itb; then
     if test ${{filesize}} = {fit_size:x}; then
      if crc32 -v {fit_addr:#x} ${{filesize}} {fit_crc:08x}; then
       if iminfo {fit_addr:#x}; then
        setenv bootargs "{bootargs}"
        {boot_command}
       fi
      fi
     fi
    fi
   fi
  fi
 fi
fi
if load mmc ${{sv08_mmcdev}}:5 {original_addr:#x} sv08-reimage/recovery-original.scr; then
 source {original_addr:#x}
fi
echo "SV08 recovery unavailable; use the independent SD rescue path"
exit
'''


def build(work, kernel, initrd, dtb, bundle_root, server, export, claim_port):
    work = work.resolve()
    local = (REPO / 'local').resolve()
    if (work.exists() or not work.is_relative_to(local) or
            any(path.is_symlink() for path in (work, *work.parents) if path.is_relative_to(local))):
        raise ValueError('Fresh non-symlink output under ignored local/ required')
    kernel, initrd, dtb = (regular(path) for path in (kernel, initrd, dtb))
    server = str(ipaddress.IPv4Address(server))
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', export) or '..' in export.split('/'):
        raise ValueError('Invalid NFS export path')
    if not 1024 <= claim_port <= 65535:
        raise ValueError('Invalid claim port')
    bundle = commissioning_bundle(bundle_root, server, export)
    job = json.loads((bundle[0] / 'job.json').read_text())
    job_id = job['job_id']
    work.mkdir(mode=0o700, parents=True)
    shutil.copyfile(kernel, work / 'Image')
    shutil.copyfile(dtb, work / 'sv08.dtb')
    shutil.copyfile(initrd, work / 'writer-initrd.img')
    composition = append_commissioning_initramfs(work / 'writer-initrd.img', bundle,
                                                  server, export, work)
    hashes = {'Image': sha(work / 'Image'), 'initrd.img': sha(work / 'writer-initrd.img'),
              'sv08.dtb': sha(work / 'sv08.dtb')}
    bootcmd = boot_script(server, export, hashes, claim_port=claim_port)
    args = re.search(r'^setenv bootargs "([^"\n]+)"$', bootcmd, re.M)
    if not args:
        raise ValueError('Trusted writer boot arguments unavailable')
    bootargs = args.group(1) + ' sv08.h616_recovery_handoff=1'
    its = '''/dts-v1/;
/ { description = "SV08 one-shot recovery RAM writer"; #address-cells = <1>;
 images {
  kernel { data = /incbin/("Image"); type = "kernel"; arch = "arm64";
   os = "linux"; compression = "none"; load = <0x40080000>;
   entry = <0x40080000>; hash { algo = "sha256"; }; };
  ramdisk { data = /incbin/("writer-initrd.img"); type = "ramdisk";
   arch = "arm64"; os = "linux"; compression = "none";
   hash { algo = "sha256"; }; };
  fdt { data = /incbin/("sv08.dtb"); type = "flat_dt"; arch = "arm64";
   compression = "none"; hash { algo = "sha256"; }; };
 };
 configurations { default = "conf"; conf { kernel = "kernel";
  ramdisk = "ramdisk"; fdt = "fdt"; }; };
};
'''
    (work / 'writer.its').write_text(its)
    subprocess.run(['mkimage', '-f', 'writer.its', 'writer.itb'], cwd=work,
                   check=True, capture_output=True, timeout=120)
    fit = (work / 'writer.itb').read_bytes()
    if len(fit) > FIT_MAX_BYTES:
        raise ValueError('Writer FIT exceeds reviewed 64 MiB load budget')
    (work / 'recovery.cmd').write_text(script_text(job_id, bootargs, len(fit), zlib.crc32(fit)))
    subprocess.run(['mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none',
                    '-n', 'SV08 one-shot recovery selector', '-d', 'recovery.cmd',
                    'recovery.scr'], cwd=work, check=True, capture_output=True, timeout=120)
    (work / 'armed').write_bytes(MARKER)
    result = {'status': 'nondeployable-offline-candidate', 'job_id': job_id,
              'fit_bytes': len(fit), 'fit_crc32': f'{zlib.crc32(fit):08x}',
              'marker_bytes': len(MARKER), 'marker_crc32': f'{zlib.crc32(MARKER):08x}',
              'bootargs': bootargs, 'composition': composition,
              'files_sha256': {name: sha(work / name) for name in
                               ('Image', 'writer-initrd.img', 'sv08.dtb', 'writer.itb',
                                'recovery.scr', 'armed')}}
    (work / 'build.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('work', 'kernel', 'initrd', 'dtb', 'bundle'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--server', required=True)
    parser.add_argument('--export', required=True)
    parser.add_argument('--claim-port', required=True, type=int)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps({'execute': args.execute, 'work': str(args.work.resolve())}), flush=True)
    if args.execute:
        print(json.dumps(build(args.work, args.kernel, args.initrd, args.dtb,
                               args.bundle, args.server, args.export,
                               args.claim_port), sort_keys=True))


if __name__ == '__main__':
    main()
