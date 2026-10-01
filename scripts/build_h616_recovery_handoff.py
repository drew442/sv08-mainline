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
from scripts.build_h616_reimage_candidate import verify_compiled_writer

MARKER = b'SV08-REIMAGE-ONCE\n'
FIT_ADDR = 0x48000000
MARKER_ADDR = 0x4f800000
ORIGINAL_ADDR = 0x4fd00000
FIT_MAX_BYTES = 64 * 1024 * 1024
ENV_BYTES = 64 * 1024
ENV_ADDRS = (0x4f900000, 0x4f910000)
ENV_OFFSETS = (4 * 1024 * 1024, 8 * 1024 * 1024)
GATE_NAMES = ('sv08_reimage_arm', 'sv08_env_layout', 'BOOT_ORDER',
              'BOOT_A_LEFT', 'BOOT_B_LEFT')
SCRIPT_ADDR = 0x4fc00000
SCRIPT_MAX_BYTES = 1024 * 1024


def selector_intervals(kernel_bytes, fit_bytes, selector_bytes):
    """Static load map only; bootm relocation still needs physical observation."""
    if not 0 < fit_bytes <= FIT_MAX_BYTES or not 0 < selector_bytes <= SCRIPT_MAX_BYTES:
        raise ValueError('Selector/FIT exceeds reviewed load budget')
    intervals = {'kernel': (0x40080000, 0x40080000 + kernel_bytes),
                 'fit': (FIT_ADDR, FIT_ADDR + FIT_MAX_BYTES),
                 'marker': (MARKER_ADDR, MARKER_ADDR + len(MARKER)),
                 'selector': (SCRIPT_ADDR, SCRIPT_ADDR + SCRIPT_MAX_BYTES),
                 'original_script': (ORIGINAL_ADDR, ORIGINAL_ADDR + SCRIPT_MAX_BYTES)}
    intervals.update({f'environment_{i}': (addr, addr + ENV_BYTES)
                      for i, addr in enumerate(ENV_ADDRS)})
    for name, (start, end) in intervals.items():
        if not 0x40000000 <= start < end <= 0x80000000:
            raise ValueError(f'Invalid load interval: {name}')
        for other, (lo, hi) in intervals.items():
            if other != name and start < hi and lo < end:
                raise ValueError(f'Overlapping load intervals: {name}, {other}')
    return {name: {'start': start, 'end': end} for name, (start, end) in intervals.items()}



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
                original_addr=ORIGINAL_ADDR, env_addrs=ENV_ADDRS, mmcdev="1",
                boot_command=None):
    if not re.fullmatch(r'[a-z0-9-]{1,64}', job_id):
        raise ValueError('Invalid job ID for recovery selector')
    if '"' in bootargs or '\n' in bootargs:
        raise ValueError('Invalid boot arguments')
    if boot_command is None:
        boot_command = f'bootm {fit_addr:#x}'
    if not re.fullmatch(r'[0-9a-f]+', mmcdev):
        raise ValueError('Invalid explicit MMC route')
    if (len(env_addrs) != 2 or any(addr % 512 for addr in env_addrs) or
            abs(env_addrs[1] - env_addrs[0]) < ENV_BYTES):
        raise ValueError('Invalid environment buffers')
    for addr in env_addrs:
        if any(addr < end and start < addr + ENV_BYTES for start, end in (
                (fit_addr, fit_addr + FIT_MAX_BYTES),
                (marker_addr, marker_addr + len(MARKER)),
                (original_addr, original_addr + SCRIPT_MAX_BYTES))):
            raise ValueError('Environment buffer overlaps payload')
    predicate = (f'test "${{sv08_reimage_arm}}" = "{job_id}" && '
                 'test "${sv08_env_layout}" = "ab-8gb-v1" && '
                 'test "${BOOT_ORDER}" = "A B" && '
                 'test "${BOOT_A_LEFT}" = "0" && test "${BOOT_B_LEFT}" = "0"')
    admission = (f'if test "${{sv08_mmcdev}}" = "{mmcdev}"; then\n'
                 f' if mmc dev {int(mmcdev, 16)} 0; then\n')
    for address, offset in zip(env_addrs, ENV_OFFSETS):
        admission += f'  if mmc read {address:#x} {offset // 512:x} {ENV_BYTES // 512:x}; then\n'
        admission += ''.join(f'   setenv {name}\n' for name in GATE_NAMES)
        admission += f'   if env import -c {address:#x} {ENV_BYTES:x} {" ".join(GATE_NAMES)}; then\n'
        admission += f'    if {predicate}; then\n'
    return f'''# One-shot recovery writer; every failed check loads the original UI.
{admission}
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
    manifest = bundle[1]
    preflight_only = manifest.get('preflight_only', False)
    expected_format = ('sv08-h616-signed-preflight-v1' if preflight_only else
                       'sv08-h616-signed-reimage-v1')
    if (type(preflight_only) is not bool or job.get('format') != expected_format or
            manifest.get('job_format', expected_format) != expected_format or
            (preflight_only and (manifest.get('synthetic_test') is not False or
                                 manifest.get('trusted_initramfs') is not True or
                                 manifest.get('recovery_handoff') is not True))):
        raise ValueError('Signed job purpose and compiled handoff mode mismatch')
    compiled_purpose_sha256 = verify_compiled_writer(bundle[0], manifest)
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
    if preflight_only:
        bootargs += ' sv08.h616_preflight=1'
    purpose = 'preflight' if preflight_only else 'writer'
    its = '''/dts-v1/;
/ { description = "SV08 one-shot recovery RAM PURPOSE"; #address-cells = <1>;
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
'''.replace('PURPOSE', purpose)
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
    load_intervals = selector_intervals(kernel.stat().st_size, len(fit),
                                        (work / 'recovery.scr').stat().st_size)
    (work / 'armed').write_bytes(MARKER)
    synthetic = bundle[1]['synthetic_test'] is True
    result = {'status': ('nondeployable-offline-candidate' if synthetic else
                         'h12-attended-candidate'),
              'synthetic_test': synthetic, 'job_id': job_id,
              'preflight_only': preflight_only, 'job_format': expected_format,
              'compiled_purpose_sha256': compiled_purpose_sha256,
              'writer_sha256': manifest['binary_sha256'],
              'initramfs_sha256': hashes['initrd.img'],
              'fit_sha256': hashlib.sha256(fit).hexdigest(),
              'fit_bytes': len(fit), 'fit_crc32': f'{zlib.crc32(fit):08x}',
              'initramfs_bytes': (work / 'writer-initrd.img').stat().st_size,
              'kernel_bytes': (work / 'Image').stat().st_size,
              'dtb_bytes': (work / 'sv08.dtb').stat().st_size,
              'fit_load_address': FIT_ADDR, 'fit_max_bytes': FIT_MAX_BYTES,
              'fit_load_end': FIT_ADDR + len(fit),
              'selector_load_intervals': load_intervals,
              'environment_buffer_bytes': 2 * ENV_BYTES,
              'environment_source': {'mmc_device': '1', 'hardware_partition': 0,
                                     'record_bytes': ENV_BYTES,
                                     'offsets': list(ENV_OFFSETS),
                                     'import_variables': list(GATE_NAMES)},
              'component_relocation_verified': False,
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
