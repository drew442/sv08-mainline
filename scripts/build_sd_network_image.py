#!/usr/bin/env python3
"""Compose an offline SD/NFS diagnostic image in a regular file only.

Gap: the A/B composer uses eMMC RAUC policy and cannot safely make SD media.
Retire this prototype when a reviewed removable-media build path replaces it.
No block device is ever accepted as an output or build input.
"""
import argparse
import gzip
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / 'configs/host-os/sv08-sd-network-inputs.json'
FRAGMENT = REPO / 'configs/host-os/sv08-sd-network.fragment'
PATCH = REPO / 'patches/u-boot/0005-sv08-sd-network-diagnostic.patch'
PROBE = REPO / 'tests/fixtures/sd-network-root/init.c'
EMMC_LOCATOR = REPO / 'tests/fixtures/sd-network-root/emmc_locator.h'
KERNEL_RELEASE = '6.18.51-sv08-candidate1'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(*args, cwd=None, env=None, output=None):
    command = [str(arg) for arg in args]
    if output:
        with output.open('a') as log:
            subprocess.run(command, cwd=cwd, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=1200)
        return ''
    return subprocess.check_output(command, cwd=cwd, env=env,
                                   stderr=subprocess.STDOUT, text=True, timeout=1200)


def regular_input(path):
    path = path.resolve(strict=True)
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f'Regular file required: {path}')
    return path


def fresh_directory(path):
    path = path.resolve()
    if path.exists() or path == Path('/'):
        raise ValueError('Output must be a fresh directory')
    return path


def extract_one(archive, destination):
    destination.mkdir()
    with tarfile.open(archive) as tar:
        tar.extractall(destination, filter='data')
    children = list(destination.iterdir())
    if len(children) != 1 or not children[0].is_dir():
        raise ValueError('Source archive must contain one root directory')
    source = children[0]
    source.rename(destination.parent / destination.name.replace('-extract', ''))
    destination.rmdir()
    return destination.parent / destination.name.replace('-extract', '')


def boot_script(server, export, hashes):
    # Explicit addresses are below 0x60000000 in the observed 1 GiB DRAM map.
    return f'''# Read only the SD FAT partition. Any failure returns to U-Boot console.
setenv bootargs "console=ttyS0,115200 root=/dev/nfs ro ip=dhcp nfsroot={server}:{export},nfsvers=3,timeo=10,retrans=1,soft rootdelay=8 panic=0 init=/sd-network-init"
if fatload mmc 0:1 ${{kernel_addr_r}} Image; then
  if hash -v sha256 ${{kernel_addr_r}} ${{filesize}} {hashes['Image']}; then
    if fatload mmc 0:1 ${{ramdisk_addr_r}} initrd.img; then
      setenv sd_initrd_size ${{filesize}}
      if hash -v sha256 ${{ramdisk_addr_r}} ${{sd_initrd_size}} {hashes['initrd.img']}; then
        if fatload mmc 0:1 ${{fdt_addr_r}} sv08.dtb; then
          if hash -v sha256 ${{fdt_addr_r}} ${{filesize}} {hashes['sv08.dtb']}; then
            booti ${{kernel_addr_r}} ${{ramdisk_addr_r}}:${{sd_initrd_size}} ${{fdt_addr_r}}
          fi
        fi
      fi
    fi
  fi
fi
echo "SV08 SD diagnostic: verified boot failed; stop here"
exit
'''


def default_environment(script_sha):
    return f'''bootdelay=3
baudrate=115200
stdin=serial
stdout=serial
stderr=serial
kernel_addr_r=0x40080000
fdt_addr_r=0x4fa00000
ramdisk_addr_r=0x4ff00000
scriptaddr=0x4fc00000
bootcmd=if mmc dev 0; then if fatload mmc 0:1 ${{scriptaddr}} boot.scr; then if hash -v sha256 ${{scriptaddr}} ${{filesize}} {script_sha}; then source ${{scriptaddr}}; fi; fi; fi; echo "SV08 SD diagnostic: no verified boot; stop here"
'''


def inspect_config(config):
    values = {}
    for line in config.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:-11]] = 'n'
    expected = {
        'CONFIG_ENV_IS_NOWHERE': 'y', 'CONFIG_ENV_IS_IN_MMC': 'n',
        'CONFIG_ENV_IS_IN_FAT': 'n', 'CONFIG_ENV_IS_IN_EXT4': 'n',
        'CONFIG_ENV_REDUNDANT': 'n', 'CONFIG_BOOTMETH_RAUC': 'n',
        'CONFIG_BOOTSTD': 'n', 'CONFIG_CMD_SAVEENV': 'n',
        'CONFIG_CMD_HASH': 'y', 'CONFIG_HASH_VERIFY': 'y',
        'CONFIG_SHA256': 'y',
        'CONFIG_MMC_SUNXI_SLOT_EXTRA': '-1',
        'CONFIG_DEFAULT_DEVICE_TREE': '"allwinner/sun50i-h616-sovol-sv08-sd-network"',
        'CONFIG_ENV_DEFAULT_ENV_TEXT_FILE': '"sv08-sd-network.env"',
    }
    failures = {key: (values.get(key), val) for key, val in expected.items()
                if values.get(key, 'n') != val}
    if failures:
        raise ValueError(f'Unsafe effective U-Boot configuration: {failures}')
    return {key: values.get(key, 'n') for key in expected}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('work', 'uboot-archive', 'tfa-archive', 'armbian-patch-dir',
                 'kernel-gzip', 'initrd', 'dtb'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--server', required=True, help='Reserved NFS server IPv4 address')
    p.add_argument('--export', required=True, help='Absolute read-only NFS export path')
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    spec = json.loads(SPEC.read_text())
    if spec['deployable'] is not False or spec['image_bytes'] > spec['card_capacity_bytes']:
        raise ValueError('Unsafe image capacity/status')
    server = str(ipaddress.IPv4Address(a.server))
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', a.export) or '..' in a.export.split('/'):
        raise ValueError('Export must be a simple absolute path')
    work = fresh_directory(a.work)
    sources = {name: regular_input(getattr(a, name)) for name in
               ('uboot_archive', 'tfa_archive', 'kernel_gzip', 'initrd', 'dtb')}
    patch_dir = a.armbian_patch_dir.resolve(strict=True)
    for name, expected in [('uboot_archive', spec['u_boot_archive_sha256']),
                           ('tfa_archive', spec['tf_a_archive_sha256']),
                           ('kernel_gzip', spec['kernel_gzip_sha256']),
                           ('initrd', spec['initrd_sha256']),
                           ('dtb', spec['dtb_sha256'])]:
        if digest(sources[name]) != expected:
            raise ValueError(f'{name} hash mismatch')
    for name, expected in spec['armbian_patches']:
        if digest(regular_input(patch_dir / name)) != expected:
            raise ValueError(f'Board patch hash mismatch: {name}')
    inputs = {str(path): digest(path) for path in
              [*sources.values(), SPEC, FRAGMENT, PATCH, PROBE, EMMC_LOCATOR,
               *[patch_dir / name for name, _ in spec['armbian_patches']]]}
    print(json.dumps({'execute': a.execute, 'regular_file_only': True,
                      'image_bytes': spec['image_bytes'], 'work': str(work)}), flush=True)
    if not a.execute:
        return
    # The generated root is deliberately public diagnostic content, exported
    # with root_squash; anonymous NFS reads must traverse this directory.
    work.mkdir(mode=0o755, parents=True)
    log = work / 'build.log'
    nfs_root = work / 'nfs-root'
    for name in ('dev', 'proc', 'sys', 'data', 'run', 'tmp'):
        (nfs_root / name).mkdir(parents=True)
        (nfs_root / name).chmod(0o755)
    nfs_root.chmod(0o755)
    run('aarch64-linux-gnu-gcc', '-static', '-Os', '-Wall', '-Wextra',
        '-o', nfs_root / 'sd-network-init', PROBE, output=log)
    (nfs_root / 'sd-network-init').chmod(0o755)
    root_manifest = {'files': {'sd-network-init': {
        'bytes': (nfs_root / 'sd-network-init').stat().st_size,
        'sha256': digest(nfs_root / 'sd-network-init'), 'mode': '0755'}},
        'directories': ['data', 'dev', 'proc', 'run', 'sys', 'tmp']}
    (work / 'nfs-root-manifest.json').write_text(
        json.dumps(root_manifest, sort_keys=True, indent=2) + '\n')
    boot = work / 'boot'
    boot.mkdir()
    with gzip.open(sources['kernel_gzip'], 'rb') as src, (boot / 'Image').open('wb') as dest:
        shutil.copyfileobj(src, dest)
    if digest(boot / 'Image') != spec['kernel_raw_sha256']:
        raise ValueError('Candidate raw Image differs from reviewed source')
    shutil.copyfile(sources['initrd'], boot / 'initrd.img')
    shutil.copyfile(sources['dtb'], boot / 'sv08.dtb')
    if (boot / 'Image').stat().st_size > 48 * 1024**2 or (boot / 'initrd.img').stat().st_size > 32 * 1024**2:
        raise ValueError('Payload exceeds fixed memory/address budget')
    hashes = {path.name: digest(path) for path in boot.iterdir()}
    (work / 'boot.cmd').write_text(boot_script(server, a.export, hashes))
    run('mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none', '-n',
        'SV08 SD NFS diagnostic', '-d', work / 'boot.cmd', boot / 'boot.scr', output=log)
    script_sha = digest(boot / 'boot.scr')
    env_text = default_environment(script_sha)
    if any(token in env_text + (work / 'boot.cmd').read_text() for token in
           ('saveenv', 'fw_setenv', 'rauc', 'BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT',
            'mmc 1', 'mmc1', 'mmc 2', 'mmc2')):
        raise ValueError('Forbidden eMMC or A/B operation in generated commands')

    tf_a = extract_one(sources['tfa_archive'], work / 'tf-a-extract')
    uboot = extract_one(sources['uboot_archive'], work / 'u-boot-extract')
    build_env = dict(os.environ, SOURCE_DATE_EPOCH=str(spec['source_date_epoch']),
                     UBOOT_BUILD_USER='sv08', UBOOT_BUILD_HOST='offline')
    run('make', '-C', tf_a, '-j2', 'CROSS_COMPILE=aarch64-linux-gnu-',
        'PLAT=sun50i_h616', 'DEBUG=1', 'bl31', env=build_env, output=log)
    bl31 = tf_a / 'build/sun50i_h616/debug/bl31.bin'
    for name, _ in spec['armbian_patches']:
        run('patch', '--batch', '--forward', '-d', uboot, '-p1', '-i',
            patch_dir / name, output=log)
    run('patch', '--batch', '--forward', '-d', uboot, '-p1', '-i', PATCH,
        output=log)
    run('make', '-C', uboot, 'CROSS_COMPILE=aarch64-linux-gnu-',
        'bigtreetech_cb1_defconfig', env=build_env, output=log)
    shutil.copyfile(work / 'boot.cmd', uboot / 'sv08-sd-network.cmd')
    (uboot / 'sv08-sd-network.env').write_text(env_text)
    run('bash', uboot / 'scripts/kconfig/merge_config.sh', '-m', '-O', uboot,
        uboot / '.config', FRAGMENT, env=build_env, output=log)
    run('make', '-C', uboot, 'CROSS_COMPILE=aarch64-linux-gnu-', 'olddefconfig',
        env=build_env, output=log)
    effective = inspect_config(uboot / '.config')
    run('make', '-C', uboot, '-j2', 'CROSS_COMPILE=aarch64-linux-gnu-',
        'BL31=' + str(bl31), env=build_env, output=log)
    loader = uboot / 'u-boot-sunxi-with-spl.bin'
    loader_size = loader.stat().st_size
    if loader.read_bytes()[4:12] != b'eGON.BT0' or 8192 + loader_size > 1048576:
        raise ValueError('SPL/FIT header or reserved range invalid')
    # DT compilation is checked again against the binary used by this loader.
    dt = uboot / 'dts/upstream/src/arm64/allwinner/sun50i-h616-sovol-sv08-sd-network.dts'
    if not dt.exists() or not all(token in dt.read_text() for token in
                                   ('&mmc1 { status = "disabled"; };',
                                    '&mmc2 { status = "disabled"; };')):
        raise ValueError('SD-only DT unavailable')
    shutil.copyfile(loader, work / 'u-boot-sunxi-with-spl.bin')
    shutil.copyfile(uboot / '.config', work / 'u-boot.config')
    fat = work / 'boot.fat'
    with fat.open('xb') as f:
        f.truncate(spec['boot_partition_bytes'])
    run('mkfs.vfat', '-F', '32', '-n', 'SV08_SD_NET', fat, output=log)
    for path in sorted(boot.iterdir()):
        run('mcopy', '-i', fat, path, '::/' + path.name, output=log)
    run('fsck.vfat', '-n', fat, output=log)
    disk = work / 'sv08-sd-network.img'
    with disk.open('xb') as f:
        f.truncate(spec['image_bytes'])
    first = spec['boot_partition_offset_bytes'] // 512
    last = first + spec['boot_partition_bytes'] // 512 - 1
    run('sgdisk', '--clear', '--move-main-table=4096', f'--new=1:{first}:{last}',
        '--change-name=1:sd-boot', '--typecode=1:0700', disk, output=log)
    run('sgdisk', '--verify', disk, output=log)
    if not (8192 + loader_size <= 1048576 < 4096 * 512 < spec['boot_partition_offset_bytes']
            and spec['boot_partition_offset_bytes'] + spec['boot_partition_bytes'] < spec['image_bytes'] - 65536):
        raise ValueError('SPL/GPT/partition overlap or missing backup GPT room')
    with disk.open('r+b') as target:
        for offset, source in [(8192, loader), (spec['boot_partition_offset_bytes'], fat)]:
            target.seek(offset)
            with source.open('rb') as stream:
                shutil.copyfileobj(stream, target)
        target.flush()
        os.fsync(target.fileno())
    run('sgdisk', '--verify', disk, output=log)
    if any(digest(path) != expected for path, expected in
           [(Path(name), expected) for name, expected in inputs.items()]):
        raise ValueError('An input changed during build')
    receipt = {
        'status': 'offline-prototype-awaiting-independent-review',
        'hardware_profile': spec['hardware_profile'], 'physical_boot': False,
        'image_bytes': disk.stat().st_size, 'card_capacity_bytes': spec['card_capacity_bytes'],
        'image_sha256': digest(disk), 'loader_offset_bytes': 8192,
        'loader_bytes': loader_size, 'loader_sha256': digest(loader),
        'partition_offset_bytes': spec['boot_partition_offset_bytes'],
        'partition_bytes': spec['boot_partition_bytes'], 'environment_regions': [],
        'default_environment': env_text, 'effective_config': effective,
        'payloads': {path.name: {'bytes': path.stat().st_size, 'sha256': digest(path)}
                     for path in boot.iterdir()}, 'inputs': inputs,
        'nfs_root_init_sha256': digest(nfs_root / 'sd-network-init'),
        'nfs_root_contents': ['sd-network-init', 'dev/', 'proc/', 'sys/',
                              'data/', 'run/', 'tmp/'],
        'nfs_root_manifest_sha256': digest(work / 'nfs-root-manifest.json'),
        'compiler': run('aarch64-linux-gnu-gcc', '--version').splitlines()[0],
        'tfa_bl31_sha256': digest(bl31), 'u_boot_config_sha256': digest(uboot / '.config'),
        'export_path': a.export, 'server_address': server,
    }
    (work / 'composition.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('status', 'image_bytes', 'image_sha256')}))


if __name__ == '__main__':
    main()
