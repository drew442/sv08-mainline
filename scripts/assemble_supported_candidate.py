#!/usr/bin/env python3
"""Explicit supported wrapper around the existing six-partition assembler.

Produces regular files only. Physical boot, independent recovery, installation,
commissioning and release acceptance remain mandatory separate evidence.
"""
import argparse
import json
from pathlib import Path
from assemble_board_diagnostic import compose
from prepare_host_os import work_path


def sd_payloads(recovery, work):
    """Prepare current recovery for the existing SD-only loader/assembler.

    Does not compile a loader, format a card, change the normal environment or
    promote the historical SD root. The existing assembler admits a separately
    compiled script/environment-bound loader before constructing regular files.
    """
    import gzip
    import hashlib
    import shutil
    from recovery_image import inventory, sha
    from assemble_board_diagnostic import run, RAW_IMAGE
    from build_sd_recovery_host import boot_script, PARTUUID, ROOT_UUID
    from build_sd_network_image import default_environment
    from prepare_host_os import REPO
    recovery, work = work_path(recovery), work_path(work)
    if work.exists() or work in recovery.parents or recovery in work.parents or work == recovery:
        raise ValueError('Fresh separate SD payload output required')
    source_hash = sha(recovery/'build.json')
    recipes = [Path(__file__), REPO/'scripts/recovery_image.py', REPO/'scripts/build_sd_recovery_host.py',
               REPO/'scripts/build_sd_network_image.py', REPO/'configs/host-os/supported/recovery-sd.json']
    recipe_hashes = {str(path.relative_to(REPO)):sha(path) for path in recipes}
    record = json.loads((recovery/'build.json').read_text())
    from project_license import source_state
    from recovery_image import integration_inputs
    revision, dirty = source_state(REPO)
    if (dirty or (record.get('release_manifest') or {}).get('project_source_revision') != revision or
            record.get('integration_inputs') != integration_inputs()):
        raise ValueError('Independent SD requires clean current project source/notices and runtime inputs')
    profile = record.get('board_profile', {})
    if (profile.get('format_version') != 2 or profile.get('medium') != 'independent-sd' or
            profile['recovery'] != dict(partuuid=PARTUUID,filesystem_uuid=ROOT_UUID,bytes=536870912,index=2)):
        raise ValueError('Build current recovery with the explicit independent-SD profile')
    if (sha(recovery/'recovery.ext4') != record['image_sha256'] or
            inventory(recovery/'envelope') != record['envelope'] or
            sha(recovery/'vmlinuz') != record['kernel_sha256'] or
            sha(recovery/'initrd.img') != record['initrd_sha256']):
        raise ValueError('Independent recovery changed after build')
    if not record.get('restore_profile_sha256'):
        raise ValueError('Independent recovery requires a reviewed target/owner setup policy')
    raw = gzip.decompress((recovery/'vmlinuz').read_bytes())
    if hashlib.sha256(raw).hexdigest() != RAW_IMAGE: raise ValueError('Unreviewed SD kernel Image')
    from recovery_image import board_profile
    reviewed = board_profile(Path(__file__).resolve().parents[1]/'configs/host-os/supported/recovery-sd.json')
    if profile != reviewed: raise ValueError('Independent SD board artifacts differ')
    dtb = recovery/'envelope'/profile['artifacts']['dtb']['path']
    if sha(dtb) != profile['artifacts']['dtb']['sha256']: raise ValueError('Independent SD DTB differs')
    work.mkdir(mode=0o700); boot = work/'boot'; boot.mkdir()
    (boot/'Image').write_bytes(raw)
    shutil.copyfile(recovery/'initrd.img',boot/'initrd.img');shutil.copyfile(dtb,boot/'sv08.dtb')
    payloads = {name:sha(boot/name) for name in ('Image','initrd.img','sv08.dtb')}
    script = work/'boot.cmd';script.write_text(boot_script(payloads,record['manifest_sha256']))
    run('mkimage','-A','arm64','-T','script','-C','none','-n','SV08 independent owner recovery','-d',script,boot/'boot.scr')
    (work/'loader-default.env').write_text(default_environment(sha(boot/'boot.scr')))
    shutil.copyfile(recovery/'recovery.ext4',work/'recovery.ext4')
    if (sha(recovery/'build.json') != source_hash or
            sha(recovery/'recovery.ext4') != record['image_sha256'] or
            sha(work/'recovery.ext4') != record['image_sha256'] or
            inventory(recovery/'envelope') != record['envelope'] or
            recipe_hashes != {str(path.relative_to(REPO)):sha(path) for path in recipes}):
        raise ValueError('Recovery input changed')
    result = dict(deployable=False,status='independent-sd-candidate-awaiting-qualification',
                  root_sha256=record['image_sha256'],
                  payloads={path.name:dict(sha256=sha(path),bytes=path.stat().st_size)
                            for path in sorted(boot.iterdir()) if path.is_file()},
                  source_recovery_build_sha256=source_hash,
                  recipe_inputs=recipe_hashes,board_profile=profile,physical_boot=False,printing_qualified=False)
    (work/'composition.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--medium',choices=('emmc','sd-payloads'),default='emmc')
    for name in ('host','recovery','data','spl','spl-record','work','profile'):
        parser.add_argument('--'+name, type=Path, required=name in ('recovery','work'))
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.medium == 'sd-payloads':
        if any(getattr(args,name) is not None for name in ('host','data','spl','spl_record','profile')):
            parser.error('SD payloads use only --recovery, --work and --execute')
        if not args.execute:
            print(json.dumps(dict(execute=False,medium='independent-sd',next='Build reviewed recovery with supported/recovery-sd.json, then --execute payload preparation; separately compile the SD-only loader and use build_sd_recovery_host.py assemble.')))
        else: print(json.dumps(sd_payloads(args.recovery,args.work),indent=2))
    else:
        if any(getattr(args,name) is None for name in ('host','data','spl','spl_record','profile')):
            parser.error('eMMC composition also requires --host, --data, --spl, --spl-record and --profile')
        compose(args, supported_profile=json.loads(args.profile.read_text()))


if __name__ == '__main__': main()
