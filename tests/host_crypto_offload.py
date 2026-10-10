#!/usr/bin/env python3
"""Bounded, coordinator-run installed SHA-256 CE probe; never installs an update.

Read a JSON mapping of zero-message lengths to expected SHA-256 hex digests from
stdin. Generate that mapping on the workstation, not through a software benchmark
on the printer. Results include complete global CE statistics, so only promote
sanitized output after inspection. Requires an existing driver/debugfs/AF_ALG.
"""
import json
import mmap
import os
from pathlib import Path
import re
import resource
import signal
import socket
import subprocess
import sys
import time

STATS = Path('/sys/kernel/debug/sun8i-ce/stats')
DRIVER = 'sha256-sun8i-ce'
SIZES = (4096, 16384, 28672, 32768, 65536)
STREAM_SIZE = 8 * 1024 * 1024
ROUNDS = 3
BYTES_PER_ROUND = 48 * 1024 * 1024
DEADLINE_SECONDS = 80
MAX_PROCESSED = 512 * 1024 * 1024


def counters():
    raw = STATS.read_text()
    m = re.search(r'^sha256-sun8i-ce sha256 reqs=(\d+) fallback=(\d+)$', raw, re.M)
    if not m:
        raise RuntimeError('Missing exact SHA-256 CE statistics')
    return {'requests': int(m[1]), 'fallback': int(m[2]),
            'channel_requests': sum(map(int, re.findall(r'^Channel \d+: nreq (\d+)$', raw, re.M))),
            'raw': raw}


def temperature():
    return max(int(p.read_text()) for p in Path('/sys/class/thermal').glob('thermal_zone*/temp'))


def preserved():
    return {'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'root_readonly': bool(os.statvfs('/').f_flag & os.ST_RDONLY),
            'boot_readonly': bool(os.statvfs('/boot').f_flag & os.ST_RDONLY),
            'services': subprocess.check_output(
                ['systemctl', 'show', 'sv08-klipper.service', 'sv08-boot-health.service',
                 'sv08-rauc.service', '-p', 'Id', '-p', 'ActiveState', '-p', 'UnitFileState'], text=True)}


def timeout(_signal, _frame):
    raise TimeoutError('Bounded probe deadline exceeded')


def main():
    expected = json.load(sys.stdin)
    assert set(expected) == {str(n) for n in (*SIZES, STREAM_SIZE)}
    assert all(re.fullmatch('[0-9a-f]{64}', v) for v in expected.values())
    assert os.sysconf('SC_PAGE_SIZE') == 4096, 'Request geometry assumes 4 KiB pages'
    before = preserved()
    assert before['root_readonly'] and before['boot_readonly']
    assert before['services'].count('ActiveState=inactive') == 3
    assert 'Id=sv08-klipper.service\nActiveState=inactive\nUnitFileState=masked' in before['services']
    assert temperature() < 65000
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(DEADLINE_SECONDS)
    processed = 0
    result = {'format_version': 1, 'driver': DRIVER, 'kernel': os.uname().release,
              'page_size': 4096, 'before': before, 'temperature_before_mC': temperature(),
              'limits': {'wall_seconds': DEADLINE_SECONDS, 'processed_bytes': MAX_PROCESSED,
                         'synthetic_buffer_bytes': max(SIZES)}, 'samples': [], 'stats_initial': counters()}
    started = time.monotonic()
    try:
        with mmap.mmap(-1, max(SIZES)) as buf, socket.socket(socket.AF_ALG, socket.SOCK_SEQPACKET) as parent:
            parent.bind(('hash', DRIVER))
            op, _ = parent.accept()
            with op:
                # AF_ALG hash sockets do not supply ordinary writable polling;
                # use blocking sends bounded by SIGALRM and the SSH watchdog.
                for size in SIZES:
                    for repeat in range(ROUNDS if size <= 28672 else 1):
                        assert temperature() < 70000
                        count = max(1, BYTES_PER_ROUND // size) if size <= 28672 else 1
                        assert processed + size * count <= MAX_PROCESSED
                        stats_before = counters()
                        usage_before = resource.getrusage(resource.RUSAGE_SELF)
                        t0 = time.monotonic()
                        with memoryview(buf)[:size] as view:
                            for _ in range(count):
                                if op.send(view) != size:
                                    raise RuntimeError('Short AF_ALG send; refusing streaming repair')
                                if op.recv(32).hex() != expected[str(size)]:
                                    raise RuntimeError('Incorrect CE-selected digest')
                        elapsed = time.monotonic() - t0
                        usage_after = resource.getrusage(resource.RUSAGE_SELF)
                        stats_after = counters()
                        processed += size * count
                        result['samples'].append({'message_bytes': size, 'repeat': repeat,
                            'messages': count, 'bytes': size * count, 'wall_seconds': elapsed,
                            'process_cpu_seconds': usage_after.ru_utime + usage_after.ru_stime - usage_before.ru_utime - usage_before.ru_stime,
                            'bytes_per_second': size * count / elapsed,
                            'stats_before': stats_before, 'stats_after': stats_after,
                            'delta': {k: stats_after[k] - stats_before[k] for k in ('requests', 'fallback', 'channel_requests')},
                            'digests_match': True, 'temperature_mC': temperature()})
                # This is one whole-message streaming capability check, not a CPU
                # baseline. Independent per-chunk hashes cannot authenticate a file.
                assert processed + STREAM_SIZE <= MAX_PROCESSED
                stats_before = counters()
                t0 = time.monotonic()
                chunks = STREAM_SIZE // len(buf)
                for i in range(chunks):
                    flags = socket.MSG_MORE if i + 1 < chunks else 0
                    if op.send(buf, flags) != len(buf):
                        raise RuntimeError('Short streaming diagnostic send')
                assert op.recv(32).hex() == expected[str(STREAM_SIZE)]
                result['streaming_diagnostic'] = {'bytes': STREAM_SIZE, 'chunk_bytes': len(buf),
                    'digests_match': True, 'wall_seconds': time.monotonic() - t0,
                    'stats_before': stats_before, 'stats_after': counters()}
                processed += STREAM_SIZE
        result.update(after=preserved(), stats_final=counters(),
                      temperature_after_mC=temperature(), processed_bytes=processed,
                      wall_seconds=time.monotonic() - started)
        assert result['before'] == result['after'], 'Installed state changed during probe'
        result['status'] = 'passed'
    except Exception as exc:
        result.update(status='failed', error=str(exc), processed_bytes=processed,
                      wall_seconds=time.monotonic() - started, stats_final=counters(), after=preserved())
        raise
    finally:
        signal.alarm(0)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
