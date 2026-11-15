#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inventory an actual image through coordinator-owned, kernel-verified RO mounts.

Managed mode creates read-only loop mounts; it never extracts, chroots or executes
image contents. Raw ext4, DOS and GPT images are supported. Optional --root checks
an existing kernel-verified read-only mount; --partition selects its table index
(zero for raw ext4). Managed mode inspects every supported software partition.
"""
import argparse
from contextlib import contextmanager
import tempfile
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_gpt import inspect as inspect_gpt


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def file_hash(path, offset=0, length=None):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        stream.seek(offset)
        remaining = length
        while remaining is None or remaining:
            data = stream.read(1024 * 1024 if remaining is None else min(remaining, 1024 * 1024))
            if not data:
                if remaining: raise ValueError('Truncated image partition')
                break
            h.update(data)
            if remaining is not None: remaining -= len(data)
    return h.hexdigest()


def regular(path):
    path = Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Expected regular non-symlink image')
    return path


def geometry(image):
    image = regular(image); size = image.stat().st_size
    with image.open('rb') as stream:
        header = stream.read(2048)
    if header[1080:1082] == b'\x53\xef':
        return [dict(number=0, offset_bytes=0, size_bytes=size, format='ext4')]
    if len(header) < 1024 or header[510:512] != b'\x55\xaa':
        raise ValueError('Unsupported or truncated image')
    if header[512:520] == b'EFI PART':
        return inspect_gpt(image)['partition_records']
    parts = []
    for i in range(4):
        entry = header[446+i*16:462+i*16]
        kind = entry[4]; start, count = struct.unpack_from('<II', entry, 8)
        if not kind: continue
        if kind in (5, 15, 0x85, 0xee) or not start or not count:
            raise ValueError('Unsupported DOS partition type or geometry')
        parts.append(dict(number=i+1, offset_bytes=start*512, size_bytes=count*512, type=kind))
    ranges = sorted((p['offset_bytes'], p['offset_bytes']+p['size_bytes']) for p in parts)
    if not ranges or ranges[-1][1] > size or any(a[1] > b[0] for a,b in zip(ranges,ranges[1:])):
        raise ValueError('Overlapping or truncated partitions')
    return parts


def filesystem_identity(image, part):
    with Path(image).open('rb') as stream:
        stream.seek(part['offset_bytes']+1024);superblock=stream.read(1024)
    if len(superblock)!=1024 or superblock[56:58]!=b'\x53\xef': raise ValueError('Missing ext4 superblock')
    shift=struct.unpack_from('<I',superblock,24)[0]
    if shift>6: raise ValueError('Invalid ext4 block size')
    blocks=struct.unpack_from('<I',superblock,4)[0]
    if struct.unpack_from('<I',superblock,96)[0]&0x80:
        blocks+=struct.unpack_from('<I',superblock,336)[0]<<32
    size=blocks*(1024<<shift)
    if size<2048 or size>part['size_bytes']: raise ValueError('Truncated ext4 filesystem')
    return dict(format='ext4',bytes=size,sha256=file_hash(image,part['offset_bytes'],size))


def command_json(args):
    return json.loads(subprocess.check_output(args, text=True, timeout=30))


def verified_mount(target, backing, offset, length, fstype):
    target = Path(target).resolve(); backing = Path(backing).resolve()
    mounts = command_json(['findmnt', '--json', '--target', str(target), '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS'])['filesystems']
    if len(mounts) != 1: raise ValueError('Ambiguous mount')
    mount = mounts[0]; options = set(mount['options'].split(','))
    if Path(mount['target']) != target or mount['fstype'] != fstype or 'ro' not in options:
        raise ValueError('Exact read-only filesystem mount required')
    if fstype == 'ext4' and not options.intersection({'noload','norecovery'}):
        raise ValueError('ext4 journal replay must be disabled (noload)')
    loops = command_json(['losetup', '--json', '--list', '--output', 'NAME,BACK-FILE,OFFSET,SIZELIMIT,RO'])['loopdevices']
    matches = [v for v in loops if v['name'] == mount['source']]
    if len(matches) != 1: raise ValueError('Mount must use a verifiable read-only loop device')
    loop = matches[0]
    if (not loop['ro'] or Path(loop['back-file']).resolve() != backing or
            int(loop['offset']) != offset or int(loop['sizelimit']) not in (length, 0)):
        raise ValueError('Loop mount does not match exact image bytes')
    if int(loop['sizelimit']) == 0 and backing.stat().st_size-offset != length:
        raise ValueError('Unbounded loop does not match partition length')
    return dict(filesystem=fstype, offset_bytes=offset, size_bytes=length, read_only=True, journal_replay=False)


def safe_file(root, relative):
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()): raise ValueError('Image symlink escapes root')
    if not path.is_file(): raise ValueError('Missing image file: '+relative)
    return path


def tree_inventory(root):
    """Hash installed software only; never traverse data, configuration or keys."""
    result = []
    for prefix in ('usr', 'bin', 'sbin', 'lib', 'lib64', 'var/lib/dpkg', 'opt/sv08-mainline'):
        if prefix.startswith('opt/') and (root/'opt').is_symlink():
            # Never traverse an ancestor link into arbitrary opt or host data.
            result.append(dict(path='opt',kind='symlink',target=os.readlink(root/'opt'),coverage='not-followed'))
            continue
        base = root/prefix
        if base.is_symlink():
            # Absolute image links must never resolve against the inspector host.
            result.append(dict(path=prefix,kind='symlink',target=os.readlink(base),coverage='not-followed'))
            continue
        for directory, dirs, files in os.walk(base, followlinks=False):
            for name in sorted(dirs+files):
                path = Path(directory)/name; relative = path.relative_to(root).as_posix()
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode):
                    result.append(dict(path=relative, kind='symlink', target=os.readlink(path)))
                elif stat.S_ISREG(mode):
                    result.append(dict(path=relative,kind='file',bytes=path.stat().st_size,sha256=file_hash(path)))
                elif not stat.S_ISDIR(mode):
                    result.append(dict(path=relative,kind='special',mode=stat.S_IFMT(mode)))
    return sorted(result,key=lambda item:item['path'])


def installed_packages(root):
    if not (root/'var/lib/dpkg/status').exists(): return []
    status = safe_file(root, 'var/lib/dpkg/status')
    packages = []
    for stanza in status.read_text().split('\n\n'):
        fields = {}; key = None
        for line in stanza.splitlines():
            if line.startswith((' ', '\t')) and key: fields[key] += '\n'+line
            elif ': ' in line: key, value = line.split(': ',1); fields[key] = value
        if fields.get('Status') != 'install ok installed': continue
        name = fields['Package']; version = fields['Version']; architecture = fields['Architecture']
        if '/' in name or name in ('.','..'): raise ValueError('Unsafe dpkg package name')
        notice = root/'usr/share/doc'/name/'copyright'
        record = dict(name=name, version=version, architecture=architecture, source=fields.get('Source'),
                      notice=None, notice_status='missing')
        if notice.exists():
            notice = safe_file(root, notice.relative_to(root).as_posix())
            record.update(notice=dict(path=notice.relative_to(root).as_posix(),sha256=file_hash(notice)),notice_status='present')
        packages.append(record)
    if not packages: raise ValueError('No installed dpkg packages found')
    identities = [(p['name'],p['architecture']) for p in packages]
    if len(set(identities)) != len(identities): raise ValueError('Duplicate installed package identity')
    return sorted(packages,key=lambda p:(p['name'],p['architecture']))


def inspect_image(image, root, partition=0, image_hash=None, partition_hashes=None):
    image = regular(image); root = Path(root).resolve()
    before = image_hash or file_hash(image); parts = geometry(image)
    selected = [p for p in parts if p['number'] == partition]
    if len(selected) != 1: raise ValueError('Selected image partition is missing')
    part = selected[0]
    binding = verified_mount(root,image,part['offset_bytes'],part['size_bytes'],'ext4')
    # Reject unrelated nested mounts; only the image's own usr payload is allowed.
    nested = command_json(['findmnt','--json','--list','--output','TARGET'])['filesystems']
    allowed = {root, root/'usr'}
    for item in nested:
        target = Path(item['target'])
        if target.is_relative_to(root) and target not in allowed:
            raise ValueError('Unrelated nested mount in image root')
    payload = root/'usr.squashfs'; usr = None
    if payload.exists():
        payload = safe_file(root,'usr.squashfs')
        usr = verified_mount(root/'usr',payload,0,payload.stat().st_size,'squashfs')
        usr.update(sha256=file_hash(payload),bytes=payload.stat().st_size)
    elif (root/'usr').is_mount(): raise ValueError('Unbound usr mount')
    files = tree_inventory(root); packages = installed_packages(root)
    provenance = root/'usr/share/doc/sv08-mainline/project-source.json'
    project = None; unknowns = []
    if provenance.exists():
        from project_license import validate
        try: project = validate(root)
        except (ValueError,OSError,KeyError,TypeError) as error:
            unknowns.append('invalid-project-source-provenance:'+str(error))
    else: unknowns.append('missing-project-source-provenance')
    if not packages: unknowns.append('missing-installed-dpkg-database')
    unknowns += ['missing-package-notice:'+p['name'] for p in packages if p['notice'] is None]
    unknowns += ['Third-party corresponding-source completeness is not established.',
                 'Vendor kernel/bootloader source reproduction is not established.',
                 'Non-dpkg application license coverage requires separate source inventory.',
                 'Only usr, bin/sbin/lib/lib64, opt/sv08-mainline application software and dpkg metadata are enumerated; other opt paths, configuration, credentials and data are excluded.']
    for p in parts: p['sha256'] = (partition_hashes or {}).get(p['number']) or file_hash(image,p['offset_bytes'],p['size_bytes'])
    if file_hash(image) != before: raise ValueError('Image changed during inspection')
    verified_mount(root,image,part['offset_bytes'],part['size_bytes'],'ext4')
    if usr: verified_mount(root/'usr',payload,0,payload.stat().st_size,'squashfs')
    return dict(format_version=1,scope='actual-image-inventory',overall_release_qualified=False,
                image=dict(sha256=before,bytes=image.stat().st_size),partitions=parts,selected_partition=partition,
                mount=binding,filesystem=filesystem_identity(image,part),usr_payload=usr,files=files,files_sha256=hashlib.sha256(encoded(files)).hexdigest(),
                packages=packages,project=project,unknowns=unknowns)


@contextmanager
def mounted_image(image, part, scratch=None):
    """Privileged coordinator interface; only RO loops and no journal replay."""
    with tempfile.TemporaryDirectory(prefix='sv08-image-inventory-', dir=scratch) as temporary:
        root = Path(temporary)/'root'; root.mkdir()
        mounts = []
        try:
            device = subprocess.check_output(['losetup','--find','--show','--read-only',
                '--offset',str(part['offset_bytes']),'--sizelimit',str(part['size_bytes']),str(Path(image).resolve())],
                text=True,timeout=30).strip()
            mounts.append([device, None])
            subprocess.run(['mount','-t','ext4','-o','ro,noload',device,str(root)],check=True,timeout=30)
            mounts[-1][1] = root
            verified_mount(root,image,part['offset_bytes'],part['size_bytes'],'ext4')
            payload = root/'usr.squashfs'
            if payload.exists():
                safe_file(root,'usr.squashfs')
                usr = root/'usr'
                if usr.is_symlink() or not usr.is_dir(): raise ValueError('Unsafe usr mountpoint')
                device = subprocess.check_output(['losetup','--find','--show','--read-only',str(payload)],text=True,timeout=30).strip()
                mounts.append([device, None])
                subprocess.run(['mount','-t','squashfs','-o','ro',device,str(usr)],check=True,timeout=30)
                mounts[-1][1] = usr
            yield root
        finally:
            # Inner backing files hold the outer filesystem busy until their loops
            # are detached, even after unmount. Include loops whose mount failed.
            # A failed unmount stops cleanup before detaching its loop or parents.
            for device, target in reversed(mounts):
                if target is not None:
                    subprocess.run(['umount',str(target)],check=True,timeout=30)
                subprocess.run(['losetup','--detach',device],check=True,timeout=30)


def inspect_artifact(image, scratch=None, public_source=None):
    """Inspect every ext4 software partition; retain opaque boot/data coverage."""
    image = regular(image); before = file_hash(image); parts = geometry(image)
    hashes = {p['number']:file_hash(image,p['offset_bytes'],p['size_bytes']) for p in parts}
    roots = []; coverage = []
    for part in parts:
        name = part.get('name','')
        with image.open('rb') as stream:
            stream.seek(part['offset_bytes']+1080); ext4 = stream.read(2) == b'\x53\xef'
        # Data may be ext4 but is deliberately never mounted or inventoried.
        software = ext4 and (part['number'] == 0 or name.startswith(('root','recovery')) or
                             (not name and part.get('type') == 0x83))
        inspected=None
        if software:
            with mounted_image(image,part,scratch) as root:
                inspected = inspect_image(image,root,part['number'],before,hashes)
                if public_source is not None:
                    from qualify_project_source import qualify
                    inspected['source_qualification'] = qualify(root,public_source)
                roots.append(inspected)
        coverage.append(dict(part,sha256=hashes[part['number']],
            coverage=('software-files-and-installed-package-metadata' if inspected['packages'] else
                      'software-files-only; installed-package-metadata-missing') if software else 'opaque-partition-hash-only'))
    if not roots: raise ValueError('No supported software filesystem in artifact')
    if file_hash(image) != before: raise ValueError('Image changed during inspection')
    return dict(format_version=1,scope='actual-image-inventory',overall_release_qualified=False,
        image=dict(sha256=before,bytes=image.stat().st_size),partitions=coverage,roots=roots,
        limitations=['Boot/data partitions are opaque; their contents and licensing are not qualified.',
                     'Inventory is not hardware, legal, reproducibility or overall release qualification.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True); parser.add_argument('--root')
    parser.add_argument('--partition',type=int,default=0)
    parser.add_argument('--scratch',help='Existing coordinator-owned temporary mount parent')
    args=parser.parse_args()
    try:
        result = inspect_image(args.image,args.root,args.partition) if args.root else inspect_artifact(args.image,args.scratch)
        print(encoded(result).decode(),end='')
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        parser.exit(1,'Image inventory refused: '+str(error)+'\n')

if __name__ == '__main__': main()
