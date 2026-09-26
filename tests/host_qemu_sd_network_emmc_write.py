#!/usr/bin/env python3
"""QEMU-only whole-image write from disposable read-only SD/NFS root.

The only host drive is a fresh regular file held by descriptor. This program
does not accept a device path, and it never constructs a production SD image.
Run --execute only in an isolated root-owned network/mount namespace with at
least 9 GiB free on the selected scratch filesystem. H616 boot is not emulated.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import struct
import subprocess
import sys
import threading
import time
import uuid
import zlib
import tracemalloc

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from prepare_host_os import layout  # noqa: E402
from sv08_emmc_job import (ClaimHTTPServer, ClaimState, canonical_json,
                           make_descriptor, sha256_bytes)  # noqa: E402

IMAGE_BYTES = 7_818_182_656
TARGET_BYTES = 32_000_000_000
SECTOR = 512
SERIAL = 'SV08_QEMU_REIMAGE_TEST_ONLY'
DISK_GUID = '8aae17d2-09b3-47ab-8e35-8e91e63cf2b0'
PART_GUIDS = (
    'ed49c82b-2455-4709-8f41-66fd41664e01',
    'ed49c82b-2455-4709-8f41-66fd41664e02',
    'ed49c82b-2455-4709-8f41-66fd41664e03',
    'ed49c82b-2455-4709-8f41-66fd41664e04',
    'ed49c82b-2455-4709-8f41-66fd41664e05',
    'ed49c82b-2455-4709-8f41-66fd41664e06',
)
# Set after deterministic generation and independent review. A changed source
# must update both this pin and the human-readable fixture record.
IMAGE_SHA256 = '7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec'


def digest(path, limit=None):
    h = hashlib.sha256()
    with path.open('rb', buffering=0) as stream:
        left = limit
        while left is None or left:
            chunk = stream.read(4 * 1024 * 1024 if left is None else min(left, 4 * 1024 * 1024))
            if not chunk:
                break
            h.update(chunk)
            if left is not None:
                left -= len(chunk)
        if left:
            raise ValueError('Truncated image')
    return h.hexdigest()


def secure_path(path, parent=None, *, exists=True):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError('Symlink path refused')
    if parent is not None and path.parent != parent:
        raise ValueError('Path outside assigned test directory')
    if exists:
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode):
            raise ValueError('Only regular files are admitted')
    return path


def fresh_work(path):
    path = secure_path(path, exists=False)
    if path.exists() or path.is_symlink():
        raise ValueError('Fresh work directory required')
    path.mkdir(mode=0o700)
    return path


def run(command, *, timeout=120, **kwargs):
    return subprocess.run([str(item) for item in command], check=True,
                          timeout=timeout, **kwargs)


def expected_layout():
    config = json.loads((REPO / 'configs/images/host-ab.json').read_text())
    if config['image_bytes'] != IMAGE_BYTES:
        raise ValueError('Board footprint changed')
    return layout(config)


def create_synthetic_source(path):
    path = secure_path(path, parent=path.parent, exists=False)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        os.ftruncate(fd, IMAGE_BYTES)
    finally:
        os.close(fd)
    parts = expected_layout()
    command = ['sgdisk', '--clear', f'--disk-guid={DISK_GUID}',
               '--move-main-table=4096']
    for index, (part, guid) in enumerate(zip(parts, PART_GUIDS), 1):
        start = part['offset_bytes'] // SECTOR
        last = (part['offset_bytes'] + part['size_bytes']) // SECTOR - 1
        command += [f'--new={index}:{start}:{last}',
                    f'--change-name={index}:{part["name"]}',
                    f'--partition-guid={index}:{guid}']
    run(command + [path])
    fd = os.open(path, os.O_WRONLY | os.O_NOFOLLOW)
    try:
        os.pwrite(fd, b'SV08-QEMU-SYNTHETIC-NONBOOTABLE\n', 8192)
        for index, part in enumerate(parts, 1):
            marker = (f'SV08-QEMU-PART-{index}-{part["name"]}\n').encode()
            os.pwrite(fd, marker, part['offset_bytes'])
            os.pwrite(fd, marker, part['offset_bytes'] + part['size_bytes'] - 4096)
        os.fsync(fd)
    finally:
        os.close(fd)
    result = inspect_gpt(path)
    if result['partition_records'] != expected_records():
        raise ValueError('Synthetic GPT layout differs from pin')
    path.chmod(0o644)  # NFS root_squash must read the image, never modify it.
    return digest(path)


def expected_records():
    return [dict(number=i, name=part['name'], partuuid=guid,
                 offset_bytes=part['offset_bytes'], size_bytes=part['size_bytes'])
            for i, (part, guid) in enumerate(zip(expected_layout(), PART_GUIDS), 1)]


def inspect_gpt(path):
    """Read both GPT copies at the 8 GB image boundary of a 32 GB model."""
    path = secure_path(path)
    if path.stat().st_size < IMAGE_BYTES:
        raise ValueError('GPT target shorter than image footprint')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        mbr = os.pread(fd, SECTOR, 0)
        if len(mbr) != SECTOR or mbr[510:512] != b'\x55\xaa' or mbr[450] != 0xee:
            raise ValueError('Missing protective MBR')
        arrays = []
        geometries = []
        for sector in (1, IMAGE_BYTES // SECTOR - 1):
            header = bytearray(os.pread(fd, SECTOR, sector * SECTOR))
            if len(header) != SECTOR or header[:8] != b'EFI PART':
                raise ValueError('Missing primary or backup GPT')
            length, checksum = struct.unpack_from('<II', header, 12)
            if not 92 <= length <= SECTOR:
                raise ValueError('GPT header length')
            struct.pack_into('<I', header, 16, 0)
            if zlib.crc32(header[:length]) != checksum:
                raise ValueError('GPT header CRC')
            current, other, first, last = struct.unpack_from('<QQQQ', header, 24)
            if current != sector or other != (IMAGE_BYTES // SECTOR - 1 if sector == 1 else 1):
                raise ValueError('GPT header location')
            table, count, entry_size, entries_crc = struct.unpack_from('<QIII', header, 72)
            if count != 128 or entry_size != 128 or (sector == 1 and table != 4096):
                raise ValueError('GPT table geometry')
            entries = os.pread(fd, count * entry_size, table * SECTOR)
            if len(entries) != count * entry_size or zlib.crc32(entries) != entries_crc:
                raise ValueError('GPT entries CRC')
            geometries.append((first, last, bytes(header[56:72])))
            arrays.append(entries)
        if geometries[0] != geometries[1] or arrays[0] != arrays[1]:
            raise ValueError('Primary and backup GPT disagree')
        if str(uuid.UUID(bytes_le=geometries[0][2])) != DISK_GUID:
            raise ValueError('Wrong disk GUID')
        records = []
        for index in range(128):
            entry = arrays[0][index * 128:(index + 1) * 128]
            if entry[:16] == bytes(16):
                continue
            start, end = struct.unpack_from('<QQ', entry, 32)
            records.append(dict(number=index + 1,
                                name=entry[56:128].decode('utf-16le').rstrip('\0'),
                                partuuid=str(uuid.UUID(bytes_le=entry[16:32])),
                                offset_bytes=start * SECTOR,
                                size_bytes=(end - start + 1) * SECTOR))
        return {'disk_guid': DISK_GUID, 'primary_gpt_crc': True,
                'backup_gpt_crc': True, 'partition_records': records}
    finally:
        os.close(fd)


def create_target(path):
    path = secure_path(path, parent=path.parent, exists=False)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    os.ftruncate(fd, TARGET_BYTES)
    os.fsync(fd)
    if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_size != TARGET_BYTES:
        os.close(fd)
        raise ValueError('Wrong target')
    return fd


def admit_target(work, target_fd, source):
    target = secure_path(work / 'target.img', parent=work)
    choices = list(work.glob('target*.img'))
    if choices != [target]:
        raise ValueError('Ambiguous target files')
    disk = os.fstat(target_fd)
    named = target.stat()
    src = secure_path(source, parent=work).stat()
    if (not stat.S_ISREG(disk.st_mode) or disk.st_size != TARGET_BYTES or
            (disk.st_dev, disk.st_ino) != (named.st_dev, named.st_ino) or
            (disk.st_dev, disk.st_ino) == (src.st_dev, src.st_ino)):
        raise ValueError('Wrong, substituted, undersized or overlapping target')
    return target


def validate_source(path):
    path = secure_path(path)
    if path.stat().st_size != IMAGE_BYTES or digest(path) != IMAGE_SHA256:
        raise ValueError('Missing, truncated or changed source')
    if inspect_gpt(path)['partition_records'] != expected_records():
        raise ValueError('Source GPT differs')
    return path


def verify_inputs(work, sd_work):
    sd_work = secure_path(sd_work, exists=False)
    if not sd_work.is_dir() or work == sd_work or work in sd_work.parents or sd_work in work.parents:
        raise ValueError('Overlapping or absent SD source')
    receipt = json.loads((sd_work / 'composition.json').read_text())
    for name in ('Image', 'initrd.img'):
        path = secure_path(sd_work / 'boot' / name)
        if digest(path) != receipt['payloads'][name]['sha256']:
            raise ValueError('Changed SD boot payload')
    cmd = (sd_work / 'boot.cmd').read_text()
    match = re.search(r'^setenv bootargs "([^"]+)"$', cmd, re.M)
    if not match or 'root=/dev/nfs ro ip=dhcp' not in match[1]:
        raise ValueError('SD command line is not read-only NFS')
    return match[1] + ' sv08.qemu_reimage=1'


def isolated():
    if os.geteuid() != 0:
        raise ValueError('Root is required for an isolated NFS/QEMU namespace')
    for name in ('net', 'mnt'):
        if os.readlink(f'/proc/self/ns/{name}') == os.readlink(f'/proc/1/ns/{name}'):
            raise ValueError(f'Private {name} namespace required')


def process_rss_bytes():
    pages = int(Path('/proc/self/statm').read_text().split()[1])
    return pages * os.sysconf('SC_PAGE_SIZE')


FAULT_MARKERS = {
    'before-write': 'SV08_QEMU_REIMAGE_INJECTED_BEFORE_WRITE',
    'partial-write': 'SV08_QEMU_REIMAGE_INJECTED_PARTIAL_WRITE',
    'flush': 'SV08_QEMU_REIMAGE_INJECTED_AFTER_FLUSH',
    'readback': 'SV08_QEMU_REIMAGE_INJECTED_DURING_READBACK',
}


def execute(work, sd_work, packages, target_fd, kernel_args, descriptor, *,
            claim_only=False, fault=None):
    isolated()
    free = os.statvfs(work).f_bavail * os.statvfs(work).f_frsize
    if free < 9_000_000_000:
        raise ValueError('Scratch filesystem needs at least 9 GB free')
    meminfo = Path('/proc/meminfo').read_text()
    available = int(re.search(r'^MemAvailable:\s+(\d+) kB$', meminfo, re.M).group(1)) * 1024
    if available < 3 * 1024 * 1024 * 1024:
        raise ValueError('QEMU host needs at least 3 GiB available memory')
    root = work / 'nfs-root'
    root.mkdir(mode=0o755)
    for name in ('dev', 'proc', 'sys', 'run', 'data', 'tmp'):
        (root / name).mkdir()
    descriptor_bytes = canonical_json(descriptor)
    descriptor_hash = sha256_bytes(descriptor_bytes)
    (root / 'job.json').write_bytes(descriptor_bytes)
    (root / 'job.json').chmod(0o444)
    writer = root / 'sd-network-init'
    compile_args = ['aarch64-linux-gnu-gcc', '-static', '-Os', '-D_FORTIFY_SOURCE=2',
         f'-DSV08_JOB_ID="{descriptor["job_id"]}"',
         f'-DSV08_JOB_DESCRIPTOR_SHA256="{descriptor_hash}"',
         '-Wall', '-Wextra', '-Werror']
    if claim_only:
        compile_args.append('-DSV08_CLAIM_ONLY=1')
    if fault:
        compile_args.append(f'-DSV08_TEST_FAULT="{fault}"')
    run(compile_args + ['-o', writer, REPO / 'tests/fixtures/sd-network-root/emmc_image_writer.c'])
    (root / 'expected.sha256').write_text(IMAGE_SHA256 + '\n')
    os.link(work / 'source.img', root / 'image.bin')
    run(['mount', '--make-rprivate', '/'])
    run(['mount', '-t', 'tmpfs', 'tmpfs', '/run'])
    run(['ip', 'link', 'set', 'lo', 'up'])
    prefix = packages / 'usr/lib/x86_64-linux-gnu'
    env = dict(os.environ, LD_LIBRARY_PATH=':'.join((str(packages / 'usr/lib/ganesha'),
                                                     str(prefix), str(prefix / 'ganesha'))))
    config = work / 'ganesha.conf'
    (work / 'idmap.conf').write_text('[General]\nDomain = localdomain\n')
    Path('/run/ganesha').mkdir()
    config.write_text(f'''NFSv4 {{ IdmapConf = "{work / 'idmap.conf'}"; UseGetpwnam = true; Graceless = true; RecoveryRoot = "/run/ganesha"; }}
NFS_CORE_PARAM {{ Protocols = 3,4; mount_path_pseudo = true; Plugins_Dir = "{prefix / 'ganesha'}"; }}
EXPORT {{ Export_Id = 1; Path = "{root}"; Pseudo = "/srv/sv08-sd-nfs"; Access_Type = RO; Squash = Root_Squash; SecType = sys; Protocols = 3,4; Transports = TCP; FSAL {{ Name = VFS; }} }}
''')
    processes = []
    state = ClaimState.arm_new(work / 'claim-state', descriptor)
    tracemalloc.start()
    memory_before = tracemalloc.get_traced_memory()[0]
    rss_before = process_rss_bytes()
    claim_server = ClaimHTTPServer(('0.0.0.0', 0), state)
    claim_thread = threading.Thread(target=claim_server.serve_forever, daemon=True)
    try:
        processes.append(subprocess.Popen([str(packages / 'sbin/rpcbind'), '-f', '-s'], env=env,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        processes.append(subprocess.Popen([str(packages / 'usr/bin/ganesha.nfsd'), '-F', '-f', str(config),
                                           '-L', str(work / 'ganesha.log'), '-p', '/run/ganesha.pid'], env=env,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        import socket
        for _ in range(50):
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('NFS service exited')
            try:
                with socket.create_connection(('127.0.0.1', 2049), timeout=.2):
                    break
            except OSError:
                time.sleep(.2)
        else:
            raise TimeoutError('NFS service did not become ready')
        # QEMU opens exactly the already admitted regular file descriptor.
        claim_thread.start()
        command = ['qemu-system-aarch64', '-machine', 'virt', '-cpu', 'cortex-a53', '-smp', '2',
                   '-m', '2048', '-kernel', sd_work / 'boot/Image',
                   '-initrd', sd_work / 'boot/initrd.img', '-append',
                   f'{kernel_args} sv08.claim_port={claim_server.server_port}',
                   '-display', 'none', '-serial', 'null', '-no-reboot',
                   '-device', 'qemu-xhci,id=xhci', '-device', 'usb-net,netdev=n0',
                   '-netdev', 'user,id=n0', '-drive',
                   f'file=/proc/self/fd/{target_fd},if=none,id=target,format=raw,cache=none,discard=unmap,detect-zeroes=unmap',
                   '-device', f'usb-storage,drive=target,serial={SERIAL}',
                   '-chardev', f'file,id=serial,path={work / "serial.log"}',
                   '-device', 'pci-serial,chardev=serial']
        with (work / 'qemu.log').open('w') as log:
            guest = subprocess.Popen([str(x) for x in command], pass_fds=(target_fd,),
                                     stdout=log, stderr=subprocess.STDOUT)
            try:
                guest.wait(timeout=4500)
            except subprocess.TimeoutExpired:
                guest.kill(); guest.wait()
                raise TimeoutError('QEMU image write timed out; result uncertain')
        serial = (work / 'serial.log').read_text(errors='replace')
        expected_marker = (FAULT_MARKERS[fault] if fault else
                           'SV08_QEMU_REIMAGE_CLAIM_ONLY_PASS' if claim_only else
                           'SV08_QEMU_REIMAGE_PASS')
        if expected_marker not in serial or (not fault and not claim_only and
                'SV08_QEMU_REIMAGE_READBACK ' not in serial):
            raise RuntimeError('Guest did not produce the expected terminal receipt')
        if fault and ('SV08_QEMU_REIMAGE_PASS' in serial or
                      'SV08_QEMU_REIMAGE_READBACK ' in serial):
            raise RuntimeError('Faulted writer emitted success evidence')
        if state.armed.exists() or not state.claimed.exists():
            raise RuntimeError('Claim state is not durably consumed')
        claim_record = json.loads(state.claimed.read_text())
        if (claim_record.get('job_id') != descriptor['job_id'] or
                claim_record.get('descriptor_sha256') != descriptor_hash or
                claim_record.get('state') != 'consumed-before-write'):
            raise RuntimeError('Persisted claim does not match immutable descriptor')
        if fault:
            target_prefix = os.pread(target_fd, 1024 * 1024, 0)
            source_fd = os.open(work / 'source.img', os.O_RDONLY | os.O_CLOEXEC)
            try:
                source_prefix = os.pread(source_fd, 1024 * 1024, 0)
            finally:
                os.close(source_fd)
            if fault == 'before-write' and target_prefix != bytes(1024 * 1024):
                raise RuntimeError('Before-write fault changed the target')
            if fault != 'before-write' and target_prefix != source_prefix:
                raise RuntimeError('Fault marker did not follow a real target write')
            retry = state.consume({'job_id': descriptor['job_id'],
                                   'descriptor_sha256': descriptor_hash})
            if retry[0] != 409 or retry[1] != b'CONSUMED\n':
                raise RuntimeError('Interrupted job was rearmed or accepted a retry')
            return {
                'fault': fault, 'terminal_marker': expected_marker,
                'success_receipt': False, 'claim_retry_status': retry[0],
                'target_prefix_matches_source': fault != 'before-write',
                'target_unchanged': fault == 'before-write',
                'claim': {'status': 'consumed-before-write',
                          'job_id': descriptor['job_id'],
                          'descriptor_sha256': descriptor_hash,
                          'persisted_bytes': sum(path.stat().st_size for path in state.state_dir.iterdir()),
                          'latency_ms': state.last_claim_ms},
            }
        memory_after, memory_peak = tracemalloc.get_traced_memory()
        claim_storage_bytes = sum(path.stat().st_size for path in state.state_dir.iterdir())
        return {
            'claim': {'status': 'consumed-before-write', 'job_id': descriptor['job_id'],
                      'descriptor_sha256': descriptor_hash,
                      'persisted_bytes': claim_storage_bytes,
                      'latency_ms': state.last_claim_ms,
                      'python_tracemalloc_delta_bytes': max(0, memory_after - memory_before),
                      'python_tracemalloc_peak_bytes': memory_peak,
                      'host_rss_delta_bytes': max(0, process_rss_bytes() - rss_before)},
        }
    finally:
        # BaseServer.shutdown() waits for serve_forever() to set its internal
        # event. If NFS setup fails before the thread starts, calling it here
        # can hang cleanup forever instead of returning a bounded test failure.
        if claim_thread.ident is not None:
            claim_server.shutdown()
            claim_thread.join(timeout=5)
        claim_server.server_close()
        tracemalloc.stop()
        for process in reversed(processes):
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--sd-work', type=Path, required=True)
    parser.add_argument('--package-root', type=Path)
    parser.add_argument('--claim-only', action='store_true',
                        help='Test QEMU claim transport without opening or writing the target')
    parser.add_argument('--fault', choices=tuple(FAULT_MARKERS),
                        help='Inject a QEMU guest interruption in the actual writer phase')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    work = fresh_work(args.work)
    try:
        kernel_args = verify_inputs(work, args.sd_work)
        source = work / 'source.img'
        actual = create_synthetic_source(source)
        if actual != IMAGE_SHA256:
            raise ValueError(f'Synthetic source hash differs from pin: {actual}')
        validate_source(source)
        target = work / 'target.img'
        fd = create_target(target)
        try:
            admit_target(work, fd, source)
            print(json.dumps({'execute': args.execute, 'source_bytes': IMAGE_BYTES,
                              'source_sha256': actual, 'target_bytes': TARGET_BYTES,
                              'target_regular_file': str(target)}), flush=True)
            if not args.execute:
                return
            if args.package_root is None:
                raise ValueError('--package-root required to execute')
            gpt_map = {'disk_guid': DISK_GUID,
                       'image_bytes': IMAGE_BYTES,
                       'backup_gpt_at_image_end': True,
                       'partitions': expected_records()}
            descriptor = make_descriptor(
                job_id='qemu-reimage-test-001', source_bytes=IMAGE_BYTES,
                source_sha256=IMAGE_SHA256, target_serial=SERIAL,
                target_bytes=TARGET_BYTES, image_bytes=IMAGE_BYTES,
                image_sha256=IMAGE_SHA256, gpt=gpt_map)
            claim_evidence = execute(work, Path(os.path.abspath(args.sd_work)),
                                     args.package_root, fd, kernel_args, descriptor,
                                     claim_only=args.claim_only, fault=args.fault)
            if args.fault:
                result = {'status': 'qemu-injected-fault-pass', 'target_serial': SERIAL,
                          'fault_evidence': claim_evidence,
                          'guest_serial_sha256': digest(work / 'serial.log')}
                (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
                print(json.dumps(result), flush=True)
                return
            if args.claim_only:
                result = {'status': 'qemu-claim-only-pass',
                          'target_opened': False,
                          'claim': claim_evidence['claim'],
                          'guest_serial_sha256': digest(work / 'serial.log')}
                (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
                print(json.dumps(result), flush=True)
                return
            os.fsync(fd)
            admit_target(work, fd, source)
            validate_source(source)
            if digest(target, IMAGE_BYTES) != IMAGE_SHA256:
                raise ValueError('Independent host full readback differs')
            gpt = inspect_gpt(target)
            if gpt['partition_records'] != expected_records():
                raise ValueError('GPT partition map differs')
            result = {'status': 'qemu-only-pass', 'source_bytes': IMAGE_BYTES,
                      'readback_bytes': IMAGE_BYTES, 'sha256': IMAGE_SHA256,
                      'target_bytes': TARGET_BYTES, 'target_serial': SERIAL,
                      'gpt': gpt, 'claim': claim_evidence['claim'],
                      'guest_serial_sha256': digest(work / 'serial.log')}
            (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result), flush=True)
        finally:
            os.close(fd)
    except Exception:
        (work / 'FAILED').write_text('No success receipt; image outcome may be uncertain.\n')
        raise


if __name__ == '__main__':
    main()
