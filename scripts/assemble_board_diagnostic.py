#!/usr/bin/env python3
"""Compose regular-file test-sv08-01 boot media; never flash or activate it.

Custom gap: join reviewed board boot artifacts to the existing six-slot layout.
Retire this diagnostic composer when the release builder owns these checks.
Host/account finalization is a separate input stage. See host-board-image.md.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_host_os import layout, work_path
from recovery_image import REPO, board_profile, check_board_artifacts, inventory, sha
sys.path.insert(0, str(REPO / 'runtime'))
from sv08_gpt import inspect

RAW_IMAGE = '5bc7c62df2b521610d0dea0a82b38aceb54af7d340a44b02a27428d6ea28dc34'
MASKS = ('sv08-klipper', 'sv08-moonraker', 'klipper', 'moonraker', 'KlipperScreen')


def run(*args):
    return subprocess.check_output([str(x) for x in args], stderr=subprocess.STDOUT, timeout=900)


def recovery_script(profile, manifest):
    if len(manifest) != 64 or any(c not in '0123456789abcdef' for c in manifest):
        raise ValueError('Invalid recovery manifest binding')
    partuuid = profile['recovery']['partuuid']
    return f'''# Independent recovery kernel/root; no dependency on A/B/data.
setenv bootargs "root=PARTUUID={partuuid} ro panic=10 console=tty0 console=ttyS0,115200 sv08.envelope={manifest}"
if load mmc ${{sv08_mmcdev}}:5 ${{kernel_addr_r}} boot/Image; then
    if load mmc ${{sv08_mmcdev}}:5 ${{ramdisk_addr_r}} boot/initrd-recovery.img; then
        setenv sv08_recovery_initrd_size ${{filesize}}
        if load mmc ${{sv08_mmcdev}}:5 ${{fdt_addr_r}} boot/sv08.dtb; then
            booti ${{kernel_addr_r}} ${{ramdisk_addr_r}}:${{sv08_recovery_initrd_size}} ${{fdt_addr_r}}
        fi
    fi
fi
exit
'''


def seed_environment():
    lines = (REPO / 'configs/host-os/sv08-default.env').read_text().splitlines()
    env = dict(line.split('=', 1) for line in lines)
    if len(lines) != len(env) or any(k in env for k in ('BOOT_ORDER', 'BOOT_A_LEFT', 'BOOT_B_LEFT', 'sv08_env_layout')):
        raise ValueError('Default environment contract changed')
    env.update(sv08_env_layout='ab-8gb-v1', BOOT_ORDER='A', BOOT_A_LEFT='3', BOOT_B_LEFT='0')
    env['sv08_consoleargs'] += ''.join(' systemd.mask='+name+'.service' for name in MASKS)
    return ''.join(key+'='+value+'\n' for key, value in env.items())


def expected_partitions(profile, parts):
    identities = {p['index']: p for p in profile['partitions']}
    result = []
    for index, part in enumerate(parts, 1):
        identity = identities[index]
        if identity['role'] != part['name']:
            raise ValueError('Partition role/index mismatch')
        if part['name'] == 'recovery' and (index != profile['recovery']['index'] or part['size_bytes'] != profile['recovery']['bytes']):
            raise ValueError('Recovery capacity/index differs from its boot profile')
        result.append(dict(number=index, name=part['name'], partuuid=identity['partuuid'], offset_bytes=part['offset_bytes'], size_bytes=part['size_bytes']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host', 'recovery', 'data', 'spl', 'work'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    a = parser.parse_args()
    work = work_path(a.work)
    if work.exists(): raise ValueError('Fresh output required')
    sources = {name: work_path(getattr(a, name)) for name in ('host', 'recovery', 'data', 'spl')}
    for path in sources.values():
        if work == path or work in path.parents or path in work.parents:
            raise ValueError('Overlapping input/output')
    input_paths = [Path(__file__), sources['spl'], sources['host'] / 'finalized.json', sources['recovery'] / 'build.json',
                   *[REPO / p for p in ('configs/host-os/recovery-test-sv08-01.json', 'configs/images/host-ab.json',
                       'configs/host-os/sv08-default.env', 'configs/host-os/slot-boot.cmd', 'docs/hardware/host-sv08-ab-boot-20260913.json')]]
    inputs = {str(path): sha(path) for path in input_paths}
    root = sources['host'] / 'rootfs'
    profile = board_profile(REPO / 'configs/host-os/recovery-test-sv08-01.json')
    config = json.loads((REPO / 'configs/images/host-ab.json').read_text())
    parts = layout(config)
    identities = {p['index']: p for p in profile['partitions']}
    expected = expected_partitions(profile, parts)
    host = json.loads((sources['host'] / 'finalized.json').read_text())
    if host['root'] != inventory(root): raise ValueError('Host changed after finalization')
    release = json.loads((root / 'usr/lib/sv08/release.json').read_text())
    devices = {p['role']: '/dev/disk/by-partuuid/'+p['partuuid'] for p in profile['partitions']}
    if release['devices'] != devices or release['deployable'] is not False:
        raise ValueError('Unexpected diagnostic release identities')
    for name in MASKS:
        if os.readlink(root / 'etc/systemd/system' / (name+'.service')) != '/dev/null':
            raise ValueError('Printer service must be masked')
    if (root / 'usr/lib/sv08/qemu-probe.py').exists() or (root / 'etc/systemd/system/qemu-probe.service').exists():
        raise ValueError('Do not ship the historical QEMU fixture')
    check_board_artifacts(root, profile)
    recovery = sources['recovery']
    record = json.loads((recovery / 'build.json').read_text())
    if record['board_profile'] != profile or record['envelope'] != inventory(recovery / 'envelope'):
        raise ValueError('Recovery build changed')
    if sha(recovery / 'recovery.ext4') != record['image_sha256']:
        raise ValueError('Recovery image changed')
    spl_record = json.loads((REPO / 'docs/hardware/host-sv08-ab-boot-20260913.json').read_text())['artifacts']['u-boot-sunxi-with-spl.bin']
    if sha(sources['spl']) != spl_record['sha256'] or sources['spl'].stat().st_size != spl_record['bytes']:
        raise ValueError('Wrong SPL/FIT artifact')
    data_before = inventory(sources['data'])
    print(json.dumps(dict(execute=a.execute, image_bytes=config['image_bytes'], work=str(work))), flush=True)
    if not a.execute: return
    if os.geteuid() != 0: raise ValueError('Root needed to preserve image file ownership')
    work.mkdir(mode=0o700)
    boot = work / 'boot'; boot.mkdir(); (boot / 'dtb').mkdir()
    raw = gzip.decompress((root / profile['artifacts']['image']['path']).read_bytes())
    if hashlib.sha256(raw).hexdigest() != RAW_IMAGE: raise ValueError('Unreviewed raw Image')
    (boot / 'Image').write_bytes(raw)
    shutil.copyfile(root / ('boot/initrd.img-'+profile['kernel_release']), boot / 'initrd.img')
    shutil.copyfile(root / profile['artifacts']['dtb']['path'], boot / 'dtb/sv08.dtb')
    run('mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none', '-n', 'SV08 diagnostic slot', '-d', REPO / 'configs/host-os/slot-boot.cmd', boot / 'boot.scr')
    if sum(p.stat().st_size for p in boot.rglob('*') if p.is_file()) >= config['boot_content_budget_mib']*1024**2:
        raise ValueError('Boot content budget exceeded')
    envelope = work / 'recovery-envelope'
    run('cp', '-a', recovery / 'envelope', envelope)
    shutil.copyfile(boot / 'Image', envelope / 'boot/Image')
    shutil.copyfile(boot / 'dtb/sv08.dtb', envelope / 'boot/sv08.dtb')
    command = work / 'recovery.cmd'; command.write_text(recovery_script(profile, record['manifest_sha256']))
    run('mkimage', '-A', 'arm64', '-T', 'script', '-C', 'none', '-n', 'SV08 independent recovery', '-d', command, envelope / 'recovery.scr')
    env_text = work / 'environment.txt'; env_text.write_text(seed_environment())
    env_bin = work / 'environment.bin'
    run('mkenvimage', '-r', '-s', '65536', '-o', env_bin, env_text)
    images = {}
    for index, part in enumerate(parts, 1):
        role = part['name']; image = work / (role+'.img')
        with image.open('xb') as stream: stream.truncate(part['size_bytes'])
        if role.startswith('boot-'):
            run('mkfs.vfat', '-F', '32', '-n', role.upper().replace('-', '_'), image)
            run('mcopy', '-i', image, '-s', *sorted(boot.iterdir()), '::/')
            (work / (role+'-fsck.txt')).write_bytes(run('fsck.vfat', '-n', image))
        else:
            tree = root if role.startswith('root-') else envelope if role == 'recovery' else sources['data']
            fsuuid = profile['recovery']['filesystem_uuid'] if role == 'recovery' else identities[index]['partuuid']
            run('mkfs.ext4', '-q', '-F', '-b', '4096', '-m', '0', '-U', fsuuid, '-L', role, '-E', 'lazy_itable_init=0,lazy_journal_init=0', '-d', tree, image)
            (work / (role+'-fsck.txt')).write_bytes(run('e2fsck', '-fn', image))
            (work / (role+'-filesystem.txt')).write_bytes(run('dumpe2fs', '-h', image))
        images[role] = image
    disk = work / 'sv08-board-diagnostic.img'
    with disk.open('xb') as stream: stream.truncate(config['image_bytes'])
    args = ['sgdisk', '--clear', '--move-main-table=4096']
    for index, part in enumerate(parts, 1):
        first = part['offset_bytes']//512; last = first+part['size_bytes']//512-1
        args += [f'--new={index}:{first}:{last}', f'--change-name={index}:{part["name"]}', f'--partition-guid={index}:{identities[index]["partuuid"]}', f'--typecode={index}:'+('0700' if part['name'].startswith('boot-') else '8300')]
    run(*args, disk)
    regions = [(4194304, 65536), (8388608, 65536)]
    geometry = inspect(disk, environment_regions=regions)
    if not geometry['collision_free'] or geometry['partition_records'] != expected:
        raise ValueError('Unsafe or inconsistent image geometry')
    with disk.open('r+b') as stream:
        for offset, source in [(8192, sources['spl']), *[(offset, env_bin) for offset, size in regions], *[(p['offset_bytes'], images[p['name']]) for p in parts]]:
            stream.seek(offset)
            with source.open('rb') as payload: shutil.copyfileobj(payload, stream, 8*1024**2)
        stream.flush(); os.fsync(stream.fileno())
    if host['root'] != inventory(root) or data_before != inventory(sources['data']) or record['envelope'] != inventory(recovery / 'envelope'):
        raise ValueError('Source changed during composition')
    if inputs != {str(path): sha(path) for path in input_paths}:
        raise ValueError('Composition inputs changed')
    if inspect(disk, environment_regions=regions)['partition_records'] != expected:
        raise ValueError('Final partition table changed')
    result = dict(status='diagnostic-awaiting-independent-byte-review', image_bytes=disk.stat().st_size, image_sha256=sha(disk), geometry=inspect(disk, environment_regions=regions), partition_images={role: dict(bytes=p.stat().st_size, sha256=sha(p)) for role,p in images.items()}, host_root=host['root'], data=data_before, recovery_build_sha256=sha(recovery / 'build.json'), recovery_envelope=inventory(envelope), spl=spl_record, environment_sha256=sha(env_bin), sources_preserved=True, physical_boot_validated=False)
    result['input_files'] = inputs
    (work / 'composition.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
