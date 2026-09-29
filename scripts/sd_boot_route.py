#!/usr/bin/env python3
"""Bounded managed-loader preparation and SD admission. Inspection is default.

Project gap: retained H616 main U-Boot lacks verification commands. Retire with
supported recovery boot selection. No full-media copies, FAT or eMMC operations.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.sv08_gpt import inspect as inspect_gpt

START, LIMIT, SPL_BYTES = 8192, 1048576, 40960
OLD_SHA = '166b4251ffb3c2db6d3b90536650c399b3e5443b06e5c78a0ad2f8ca9fbf6b40'
SPL_SHA = 'c4fe12c6f2d344ac48cf39d1711d30734110ee3a55bb0eda1df2fccf80610a8d'
CONFIG_SHA = '52959a1a8761b00927b04cc460182527c7add51e50019d3b397438f98f7b2fb8'
PRESERVED = {'atf': '36a39a1859a9c95d3e79239afe798e9fa6f805dcec8685ed2dbbd1ca1133d237',
             'fdt': 'fdea9963522bc09efe3cbac8ebf33e01f730c3b1d2158ce2bb222b72a83f5ff4'}
ENV_SHA = '7b09c2d72a8cb60402187e4ac8904f79fc5b11d552a04d11ce416504561f08bf'
SOURCE = 'ece349ade2973e220f524ce59e59711cc919263f'
CHUNK = 1048576


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular_bytes(path, limit=8*CHUNK):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('Bounded regular input required')
        data = os.read(fd, limit+1)
        if len(data) != info.st_size:
            raise ValueError('Input changed/short read')
        return data
    finally:
        os.close(fd)


def exclusive(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        if os.write(fd, data) != len(data):
            raise OSError('Short receipt/artifact write')
        os.fsync(fd)
    finally:
        os.close(fd)


def config(data):
    result = {}
    for line in data.decode().splitlines():
        match = re.fullmatch(r'(CONFIG_\w+)=(.*)', line)
        disabled = re.fullmatch(r'# (CONFIG_\w+) is not set', line)
        if match:
            result[match[1]] = match[2]
        elif disabled:
            result[disabled[1]] = 'n'
    return result


def config_delta(old, new):
    before, after = config(old), config(new)
    changes = {key: [before.get(key, 'n'), after.get(key, 'n')]
               for key in before.keys() | after.keys()
               if before.get(key, 'n') != after.get(key, 'n')}
    required = {'CONFIG_CMD_HASH', 'CONFIG_HASH_VERIFY', 'CONFIG_CRC32_VERIFY'}
    # CMD_HASH selects HASH in this pinned cmd/Kconfig; no other dependency drift.
    if not required <= changes.keys() or changes.keys() - required - {'CONFIG_HASH'}:
        raise ValueError('Unrelated/missing effective config change')
    if any(value != ['n', 'y'] for value in changes.values()):
        raise ValueError('Only enabling approved verification options is permitted')
    return changes


def fit_properties(data):
    """Parse inline-data FIT properties; reject unsupported external FIT data."""
    if len(data) < 40:
        raise ValueError('Short FIT')
    magic, total, off, strings, _, _, _, _, size_strings, size_struct = struct.unpack_from('>10I', data)
    if magic != 0xd00dfeed or total != len(data) or off+size_struct > total or strings+size_strings > total:
        raise ValueError('Invalid FIT bounds')
    names = data[strings:strings+size_strings]
    stop, stack, result = off+size_struct, [], {}
    while off < stop:
        token = struct.unpack_from('>I', data, off)[0]; off += 4
        if token == 1:
            end = data.index(b'\0', off, stop)
            stack.append(data[off:end].decode()); off = (end+4)&~3
        elif token == 2:
            if not stack: raise ValueError('FIT nesting')
            stack.pop()
        elif token == 3:
            length, name = struct.unpack_from('>II', data, off); off += 8
            if off+length > stop or name >= len(names): raise ValueError('FIT property bounds')
            end = names.index(b'\0', name)
            key = '/'.join(stack)+'/'+names[name:end].decode()
            if key in result: raise ValueError('Duplicate FIT property')
            result[key] = data[off:off+length]; off = (off+length+3)&~3
        elif token == 4:
            continue
        elif token == 9:
            if stack: raise ValueError('Unclosed FIT')
            return result
        else:
            raise ValueError('Unknown FIT token')
    raise ValueError('Missing FIT end')


def check_fit(old, new):
    before, after = fit_properties(old), fit_properties(new)
    # Preserve all configuration wiring and every image load/entry/type property.
    stable = {k: v for k, v in before.items() if k.startswith('/configurations/') or
              k.rsplit('/', 1)[-1] in ('load', 'entry', 'type', 'arch', 'os', 'compression')}
    if stable != {k: v for k, v in after.items() if k.startswith('/configurations/') or
                  k.rsplit('/', 1)[-1] in ('load', 'entry', 'type', 'arch', 'os', 'compression')}:
        raise ValueError('FIT boot integration/load address drift')
    hashes = {}
    for label, expected in PRESERVED.items():
        keys = [k for k in before if k.startswith('/images/'+label) and k.endswith('/data')]
        if len(keys) != 1 or keys[0] not in after:
            raise ValueError('Missing/ambiguous preserved FIT component')
        key = keys[0]
        if sha(before[key]) != expected or sha(after[key]) != expected:
            raise ValueError('Preserved FIT component differs')
        hashes[label] = expected
    if not any(k.startswith('/images/uboot') and k.endswith('/data') for k in after):
        raise ValueError('Missing inline main U-Boot')
    return hashes


def prepare(old_loader, old_config, new_config, new_fit, elf, environment,
            old_provenance, new_provenance, output, receipt):
    old, fit = regular_bytes(old_loader), regular_bytes(new_fit)
    before, after = regular_bytes(old_config), regular_bytes(new_config)
    if len(old) != 786105 or sha(old) != OLD_SHA or sha(old[:SPL_BYTES]) != SPL_SHA or sha(before) != CONFIG_SHA:
        raise ValueError('Not the exact retained loader/SPL/config')
    if old[4:12] != b'eGON.BT0': raise ValueError('Missing eGON SPL')
    delta = config_delta(before, after)
    preserved = check_fit(old[SPL_BYTES:], fit)
    env = regular_bytes(environment)
    binary = regular_bytes(elf)
    compiled_env = env.rstrip(b'\n').replace(b'\n', b'\0') + b'\0\0'
    if sha(env) != ENV_SHA or binary.count(compiled_env) != 1:
        raise ValueError('Default environment is changed/not uniquely linked')
    elf_path = Path(elf)
    # nm evidence comes from the actual ELF, never a separately supplied text log.
    symbols = subprocess.run(['nm', '--defined-only', str(elf_path)], check=True,
                             capture_output=True, text=True).stdout
    needed = ('do_hash', 'hash_command', 'do_mem_crc', '_u_boot_list_2_cmd_2_hash', '_u_boot_list_2_cmd_2_crc32')
    if any(not re.search(r'\b'+name+r'$', symbols, re.M) for name in needed):
        raise ValueError('Verification commands are not linked')
    boot_data = [v for k,v in fit_properties(fit).items() if k.startswith('/images/uboot') and k.endswith('/data')]
    if len(boot_data) != 1 or compiled_env not in boot_data[0]:
        raise ValueError('Environment absent from deployed main stage')
    with tempfile.TemporaryDirectory(prefix='sv08-managed-main-') as work:
        raw = Path(work)/'main.bin'
        subprocess.run(['aarch64-linux-gnu-objcopy','--gap-fill=0xff','-R','.hash','-O','binary',str(elf_path),str(raw)],check=True,capture_output=True)
        if regular_bytes(raw) != boot_data[0]:
            raise ValueError('FIT main stage differs from linked ELF (upstream objcopy rules)')
    old_p = json.loads(regular_bytes(old_provenance))
    new_p = json.loads(regular_bytes(new_provenance))
    for key in ('config', 'compiler'):
        if key not in old_p or old_p[key] != new_p.get(key):
            raise ValueError('Build provenance changed: '+key)
    if old_p['config']['u_boot']['commit'] != SOURCE:
        raise ValueError('Unexpected U-Boot source pin')
    if old_p['artifacts']['bl31.bin']['sha256'] != PRESERVED['atf'] or new_p['artifacts']['bl31.bin']['sha256'] != PRESERVED['atf']:
        raise ValueError('BL31 provenance differs')
    if new_p.get('effective_config_sha256') != sha(after) or new_p.get('base_provenance_sha256') != sha(regular_bytes(old_provenance)):
        raise ValueError('New build provenance does not bind inputs')
    loader = old[:SPL_BYTES]+fit
    if START+len(loader) > LIMIT: raise ValueError('Absolute loader reservation exceeded')
    result = dict(format='sv08-managed-loader-v1', physical_boot_validated=False,
                  loader_sha256=sha(loader), loader_bytes=len(loader), config_delta=delta,
                  preserved=preserved, spl_sha256=SPL_SHA, environment_sha256=ENV_SHA,
                  provenance=new_p, linked_symbols=list(needed),
                  assembler_sha256=sha(regular_bytes(__file__)),
                  nm_evidence_sha256=sha(symbols.encode()),
                  main_stage_matches_linked_elf=True,
                  inputs_sha256={str(p): sha(regular_bytes(p)) for p in
                      (old_loader,old_config,new_config,new_fit,elf,environment,old_provenance,new_provenance)})
    exclusive(output, loader)
    exclusive(receipt, (json.dumps(result, sort_keys=True, indent=2)+'\n').encode())
    return result


def hash_range(fd, start, length):
    digest = hashlib.sha256()
    for offset in range(start, start+length, CHUNK):
        n = min(CHUNK, start+length-offset)
        data = os.pread(fd, n, offset)
        if len(data) != n: raise OSError('Short preservation read')
        digest.update(data)
    return digest.hexdigest()


class LinuxSD:
    """Production admission adapter; fixture adapters exist only in tests."""
    def __init__(self, policy):
        self.policy = policy

    def ranges(self, fd):
        return preservation_ranges(fd,self.policy)

    def admission(self, fd):
        p, info = self.policy, os.fstat(fd)
        if not stat.S_ISBLK(info.st_mode) or f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}' != p['dev_t']:
            raise ValueError('SD device identity changed')
        sysdev = Path('/sys/dev/block')/p['dev_t']
        card = (sysdev/'device').resolve()
        if card.joinpath('type').read_text().strip() != 'SD' or card.joinpath('cid').read_text().strip() != p['cid'] or p['controller'] not in [x.name for x in card.parents]:
            raise ValueError('SD controller/CID/type mismatch')
        capacity = struct.unpack('Q', fcntl.ioctl(fd, 0x80081272, bytes(8)))[0]
        if capacity != p['capacity']: raise ValueError('SD capacity changed')
        children = [sysdev.resolve()]+[x for x in sysdev.resolve().iterdir() if (x/'partition').exists()]
        devices = {x.joinpath('dev').read_text().strip():x for x in children}
        if p['root_dev_t'] not in devices or p['boot_dev_t'] not in devices:
            raise ValueError('Missing SD partition identities')
        if devices[p['root_dev_t']].joinpath('partition').read_text().strip() != '2' or devices[p['boot_dev_t']].joinpath('partition').read_text().strip() != '1':
            raise ValueError('SD root/boot partition numbering changed')
        for path in children:
            if list((path/'holders').iterdir()): raise ValueError('SD holder present')
        mounts = []
        for line in Path('/proc/self/mountinfo').read_text().splitlines():
            fields = line.split(); sep = fields.index('-')
            if fields[2] in devices:
                mounts.append((fields[2],fields[4],set(fields[5].split(',')),fields[sep+1],set(fields[sep+3].split(','))))
        if len(mounts) != 1 or mounts[0][:2] != (p['root_dev_t'],'/') or 'ro' not in mounts[0][2] or mounts[0][3] != 'ext4' or not {'ro','norecovery'} <= mounts[0][4]:
            raise ValueError('Require sole ro,norecovery SD root; boot unmounted')
        root = os.open('/dev/block/'+p['root_dev_t'], os.O_RDONLY|os.O_CLOEXEC)
        try:
            root_info=os.fstat(root)
            if not stat.S_ISBLK(root_info.st_mode) or f'{os.major(root_info.st_rdev)}:{os.minor(root_info.st_rdev)}' != p['root_dev_t']:
                raise ValueError('Root partition device changed')
            if struct.unpack('I',fcntl.ioctl(root,0x125e,bytes(4)))[0] != 1:
                raise ValueError('Root partition lacks kernel readonly protection')
        finally: os.close(root)
        # Open descriptors in all visible processes; exclusion is advisory, never O_EXCL.
        for process in Path('/proc').iterdir():
            if not process.name.isdigit(): continue
            try:
                # Other mount namespaces may hide writable users from self/mountinfo.
                for line in (process/'mountinfo').read_text().splitlines():
                    fields=line.split(); sep=fields.index('-')
                    if fields[2] in devices and (fields[2] != p['root_dev_t'] or 'ro' not in fields[5].split(',') or 'ro' not in fields[sep+3].split(',')):
                        raise ValueError('Competing namespace SD mount')
                descriptors = list((process/'fd').iterdir())
            except FileNotFoundError: continue
            except PermissionError: raise ValueError('Cannot inspect competing users')
            for descriptor in descriptors:
                if process.name == str(os.getpid()) and descriptor.name == str(fd): continue
                try: other = descriptor.stat()
                except FileNotFoundError: continue
                if stat.S_ISBLK(other.st_mode) and f'{os.major(other.st_rdev)}:{os.minor(other.st_rdev)}' in devices:
                    raise ValueError('Competing SD descriptor')
        path = Path('/proc/self/fd')/str(fd)
        layout = inspect_gpt(path, allow_block=True, image_bytes=p['image_bytes'])
        if layout['disk_guid'] != p['disk_guid'] or layout['partition_records'] != p['partitions']:
            raise ValueError('SD GPT map changed')
        return {'dev_t':p['dev_t'],'capacity':capacity,'layout':layout,
                'controller':p['controller'],'cid_sha256':sha(p['cid'].encode())}


def preservation_ranges(fd, policy):
    ranges = [(0,512)]
    for lba in (1,policy['image_bytes']//512-1):
        h=os.pread(fd,512,lba*512)
        if len(h)!=512 or h[:8]!=b'EFI PART': raise ValueError('Missing GPT at range gate')
        table,count,size=struct.unpack_from('<QII',h,72)
        ranges += [(lba*512,512),(table*512,count*size)]
    ranges += [(p['offset_bytes'],p['size_bytes']) for p in policy['partitions']]
    return sorted(set(ranges))


def transfer(device, loader, receipt, policy, preimage, *, apply=False, adapter=None):
    data = regular_bytes(loader)
    receipt_data = regular_bytes(receipt)
    prepared = json.loads(receipt_data)
    if policy.get('loader_sha256') != sha(data) or policy.get('receipt_sha256') != sha(receipt_data):
        raise ValueError('Reviewed policy does not bind exact loader/receipt')
    if prepared.get('format') != 'sv08-managed-loader-v1' or prepared['loader_bytes'] != len(data) or prepared['loader_sha256'] != sha(data) or START+len(data)>LIMIT:
        raise ValueError('Loader receipt/range mismatch')
    if not policy.get('capture_and_users_released') or policy.get('device') != str(device):
        raise ValueError('Explicit current exclusion/device policy required')
    adapter = adapter or LinuxSD(policy)
    flags = os.O_NOFOLLOW|os.O_CLOEXEC
    # Inspection always opens read-only. Admission binds inode/dev_t before reopening.
    lock = os.open(policy['ownership_lock'],os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    fd = os.open(device, os.O_RDONLY|flags)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
        admitted = adapter.admission(fd)
        identity = os.fstat(fd)
        span = os.pread(fd,len(data),START)
        if len(span)!=len(data) or sha(span)!=policy['preimage_sha256']:
            raise ValueError('Overwrite preimage differs')
        # Preserve all bytes outside loader span, streaming instead of image copies.
        ranges = adapter.ranges(fd)
        for begin,length in ranges:
            if begin<0 or length<=0 or begin+length>policy['capacity'] or max(begin,START)<min(begin+length,START+len(data)):
                raise ValueError('Loader overlaps preservation map')
        before = [hash_range(fd,*r) for r in ranges]
        if not apply:
            return dict(admission=admitted,planned_bytes=len(data),preimage_sha256=sha(span),preservation_ranges=ranges,preserved_sha256=before,ownership='advisory flock only',written=False)
        if regular_bytes(preimage, LIMIT) != span:
            raise ValueError('Retained complete overwrite-span preimage required')
        # Upgrade requires another FD, then discard the readonly FD immediately;
        # all writable operations remain bound to this checked descriptor.
        writefd = os.open(device, os.O_RDWR|flags)
        new = os.fstat(writefd)
        if (identity.st_rdev,identity.st_dev,identity.st_ino)!=(new.st_rdev,new.st_dev,new.st_ino):
            os.close(writefd); raise ValueError('Device replaced at write boundary')
        os.close(fd); fd = writefd
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if adapter.admission(fd)!=admitted or os.pread(fd,len(data),START)!=span:
            raise ValueError('Admission/preimage changed at write boundary')
        if [hash_range(fd,*r) for r in ranges] != before:
            raise ValueError('Preservation changed before write')
        # A partial write is uncertain: never complete/retry/rollback it.
        if os.pwrite(fd,data,START)!=len(data): raise OSError('Uncertain partial loader write; stop')
        os.fsync(fd)
        if isinstance(adapter,LinuxSD): fcntl.ioctl(fd,0x1261,0)  # BLKFLSBUF
        if adapter.admission(fd)!=admitted or os.pread(fd,len(data),START)!=data:
            raise OSError('Loader readback/admission differs; stop')
        after = [hash_range(fd,*r) for r in ranges]
        if before!=after: raise OSError('SD preservation differs; stop')
        return dict(admission=admitted,loader_sha256=sha(data),preimage_sha256=sha(span),preservation_ranges=ranges,preserved_sha256=after,
                    ownership='advisory flock only',written=True)
    finally:
        os.close(fd)
        os.close(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    prep = commands.add_parser('prepare')
    for name in ('old-loader','old-config','new-config','new-fit','elf','environment','old-provenance','new-provenance','output','receipt'):
        prep.add_argument('--'+name,required=True,type=Path)
    inspect = commands.add_parser('sd')
    for name in ('device','loader','receipt','policy','preimage'):
        inspect.add_argument('--'+name,required=True,type=Path)
    inspect.add_argument('--apply',action='store_true')
    args = vars(parser.parse_args()); command=args.pop('command')
    if command=='prepare': result=prepare(**args)
    else:
        args['policy']=json.loads(regular_bytes(args['policy']))
        result=transfer(**args)
    print(json.dumps(result,sort_keys=True,indent=2))


if __name__=='__main__':
    main()
