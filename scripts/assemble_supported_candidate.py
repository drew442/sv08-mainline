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


def recovery_source_check(repo, record, revision, dirty, pin):
    """Admit an ancestor producer only across the two delivery-wrapper files."""
    import hashlib
    import re
    import subprocess
    from project_license import source_files, SOURCE_DIRS, SOURCE_ROOTS
    producer = (record.get('release_manifest') or {}).get('project_source_revision')
    if dirty:
        raise ValueError('Independent SD requires clean current project source')
    if pin is None:
        if producer != revision:
            raise ValueError('Independent SD requires clean current project source revision')
        return producer
    if not isinstance(pin, str) or re.fullmatch('[0-9a-f]{40}', pin) is None:
        raise ValueError('Recovery source revision must be a lowercase SHA40 pin')
    if producer != pin:
        raise ValueError('Recovery producer source revision differs from pin')
    def git(*args, **kwargs):
        return subprocess.check_output(['git','-C',str(repo),*args],
                                       stderr=subprocess.PIPE, timeout=30, **kwargs)
    try:
        git('merge-base','--is-ancestor',pin,revision)
        try:
            git('diff','--quiet',pin,revision,'--','upstream/')
        except subprocess.CalledProcessError as error:
            raise ValueError('Recovery source pin differs in upstream gitlinks') from error
        tree = git('ls-tree','-rz',pin,'--',*SOURCE_ROOTS,*SOURCE_DIRS)
        names = []
        for entry in tree.split(b'\0'):
            if not entry: continue
            metadata, name = entry.split(b'\t',1)
            name = name.decode()
            if '__pycache__' in Path(name).parts or Path(name).suffix == '.pyc': continue
            if metadata.split()[1] != b'blob':
                raise ValueError('Non-file pinned project source')
            names.append(name)
        blobs = git('cat-file','--batch',input=''.join(f'{pin}:{name}\n' for name in names).encode())
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError('Recovery source pin must be an available ancestor') from error
    pinned = {}; offset = 0
    for name in names:
        end = blobs.index(b'\n',offset)
        header = blobs[offset:end].split()
        if len(header) != 3 or header[1] != b'blob':
            raise ValueError('Invalid pinned project source blob')
        size = int(header[2]); offset = end+1
        pinned[name] = hashlib.sha256(blobs[offset:offset+size]).hexdigest()
        offset += size+1
    current = source_files(repo)
    allowed = {'scripts/assemble_supported_candidate.py','tests/test_supported_candidate.py'}
    if any(current.get(name) != pinned.get(name) for name in current.keys() | pinned.keys() if name not in allowed):
        raise ValueError('Recovery source pin differs in protected project source')
    return producer


def sd_payloads(recovery, work, recovery_source_revision=None):
    """Prepare current recovery for the existing SD-only loader/assembler.

    Does not compile a loader, format a card, change the normal environment or
    promote the historical SD root. The existing assembler admits a separately
    compiled script/environment-bound loader before constructing regular files.
    """
    import gzip
    import hashlib
    import re
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
    producer_revision = recovery_source_check(REPO,record,revision,dirty,recovery_source_revision)
    if record.get('integration_inputs') != integration_inputs():
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
    # Builder modes have distinct topologies; invalid extra bindings are not absent.
    bindings = [record[key] for key in ('media_profile_sha256', 'restore_profile_sha256') if key in record]
    if (len(bindings) != 1 or not isinstance(bindings[0], str) or
            re.fullmatch('[0-9a-f]{64}', bindings[0]) is None):
        raise ValueError('Independent recovery requires exactly one reviewed export or restore profile SHA256 binding')
    for field, name in (('manifest_sha256', 'recovery-envelope.manifest'),
                        ('provider_manifest_sha256', 'recovery-image.json')):
        digest = record.get(field)
        if not isinstance(digest, str) or re.fullmatch('[0-9a-f]{64}', digest) is None:
            raise ValueError(f'Independent recovery requires valid {field} SHA256 binding')
        manifest = recovery/'envelope/etc/sv08'/name
        if not manifest.is_file() or sha(manifest) != digest:
            raise ValueError(f'Independent recovery {field} differs from manifest file')
    raw = gzip.decompress((recovery/'vmlinuz').read_bytes())
    if hashlib.sha256(raw).hexdigest() != RAW_IMAGE: raise ValueError('Unreviewed SD kernel Image')
    from recovery_image import board_profile
    reviewed = board_profile(Path(__file__).resolve().parents[1]/'configs/host-os/supported/recovery-sd.json')
    if profile != reviewed: raise ValueError('Independent SD board artifacts differ')
    usr = recovery/'envelope/usr.squashfs'
    usr_digest = record.get('usr_sha256')
    manifest_lines = (recovery/'envelope/etc/sv08/recovery-envelope.manifest').read_text().splitlines()
    manifest_digests = [line[len('usr_sha256='):] for line in manifest_lines if line.startswith('usr_sha256=')]
    if (not isinstance(usr_digest,str) or re.fullmatch('[0-9a-f]{64}',usr_digest) is None or
            manifest_digests != [usr_digest] or not usr.is_file() or sha(usr) != usr_digest):
        raise ValueError('Independent recovery compressed userspace binding differs')
    dtb_path = Path(profile['artifacts']['dtb']['path'])
    if dtb_path.parts[0] != 'usr' or '..' in dtb_path.parts or dtb_path.is_absolute():
        raise ValueError('Independent SD DTB must be within compressed usr')
    dtb = run('unsquashfs','-cat',usr,dtb_path.relative_to('usr').as_posix())
    if hashlib.sha256(dtb).hexdigest() != profile['artifacts']['dtb']['sha256']:
        raise ValueError('Independent SD DTB differs')
    work.mkdir(mode=0o700); boot = work/'boot'; boot.mkdir()
    (boot/'Image').write_bytes(raw)
    shutil.copyfile(recovery/'initrd.img',boot/'initrd.img');(boot/'sv08.dtb').write_bytes(dtb)
    payloads = {name:sha(boot/name) for name in ('Image','initrd.img','sv08.dtb')}
    script = work/'boot.cmd';script.write_text(boot_script(payloads,record['manifest_sha256'],record['provider_manifest_sha256']))
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
                  producer_source_revision=producer_revision,builder_source_revision=revision,
                  recipe_inputs=recipe_hashes,board_profile=profile,physical_boot=False,printing_qualified=False)
    (work/'composition.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--medium',choices=('emmc','sd-payloads'),default='emmc')
    for name in ('host','recovery','data','spl','spl-record','work','profile'):
        parser.add_argument('--'+name, type=Path, required=name in ('recovery','work'))
    parser.add_argument('--recovery-source-revision', help='Explicit ancestor producer SHA40; only delivery wrapper/test may differ')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.medium == 'sd-payloads':
        if any(getattr(args,name) is not None for name in ('host','data','spl','spl_record','profile')):
            parser.error('SD payloads use only --recovery, --work and --execute')
        if not args.execute:
            print(json.dumps(dict(execute=False,medium='independent-sd',next='Build reviewed recovery with supported/recovery-sd.json, then --execute payload preparation; separately compile the SD-only loader and use build_sd_recovery_host.py assemble.')))
        else: print(json.dumps(sd_payloads(args.recovery,args.work,args.recovery_source_revision),indent=2))
    else:
        if args.recovery_source_revision is not None:
            parser.error('--recovery-source-revision requires --medium sd-payloads')
        if any(getattr(args,name) is None for name in ('host','data','spl','spl_record','profile')):
            parser.error('eMMC composition also requires --host, --data, --spl, --spl-record and --profile')
        compose(args, supported_profile=json.loads(args.profile.read_text()))


if __name__ == '__main__': main()
