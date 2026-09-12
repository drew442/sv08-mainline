#!/usr/bin/env python3
"""Reproduce logical read volume against the exact reviewed pre-change source.

In-memory disposable data only. No hardware, timings or storage throughput claim.
The baseline commit and source digest are fixed, not caller-selected executable code.
"""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import types
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'runtime'))
from sv08_export import verify_stream

BASELINE = 'f7a3d53e09f3d12641639808f2cb3277d13cb6cc'
SOURCE_SHA256 = '0228d0e10d92c89012285af1cddbd0ac616345a034f125f6ac6e5c3ad3533459'


class Counted(io.BytesIO):
    def __init__(self, value):
        super().__init__(value); self.bytes_read = 0; self.largest_request = 0
        self.seeks = 0; self.eof_reads = 0
    def read(self, size=-1):
        if size < 0: raise AssertionError('Unbounded measurement read')
        self.largest_request = max(self.largest_request, size)
        value = super().read(size); self.bytes_read += len(value)
        if not value: self.eof_reads += 1
        return value
    def seek(self, *args):
        self.seeks += 1
        return super().seek(*args)


def measure():
    source = subprocess.check_output(['git', '-C', str(REPO), 'show', BASELINE + ':runtime/sv08_export.py'])
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA256
    legacy = types.ModuleType('reviewed_legacy_export')
    exec(compile(source, BASELINE + '/runtime/sv08_export.py', 'exec'), legacy.__dict__)
    payload = b'offline-readback-measure\n' * 364722
    output = io.BytesIO()
    info = tarfile.TarInfo('data/fixture.bin'); info.size = len(payload)
    with tarfile.open(fileobj=output, mode='w', format=tarfile.PAX_FORMAT) as archive:
        archive.addfile(info, io.BytesIO(payload))
    raw = output.getvalue(); expected = {info.name: hashlib.sha256(payload).hexdigest()}
    checksum = hashlib.sha256(raw).hexdigest()
    first, second, after = Counted(raw), Counted(raw), Counted(raw)
    digest = hashlib.sha256()
    while block := first.read(1024 * 1024): digest.update(block)
    opened = tarfile.open
    with patch.object(legacy.tarfile, 'open', side_effect=lambda *_: opened(fileobj=second, mode='r:')):
        legacy.verify_archive('in-memory-reviewed-fixture', expected)
    result = verify_stream(after, expected, len(raw), checksum, len(info.tobuf(format=tarfile.PAX_FORMAT)))
    assert result == digest.hexdigest() == checksum
    assert len(raw) == after.bytes_read == 9123840
    assert checksum == '0767efa76615052ca0c1506ec6c76bbdeee2ce989c44dfa5aff434872102aa72'
    assert first.bytes_read + second.bytes_read == 18242915
    assert after.seeks == 0 and after.eof_reads == 1
    return dict(baseline_commit=BASELINE, baseline_source_sha256=SOURCE_SHA256,
                archive_bytes=len(raw), archive_sha256=checksum,
                before_digest_bytes=first.bytes_read, before_semantic_bytes=second.bytes_read,
                before_total_bytes=first.bytes_read + second.bytes_read,
                after_total_bytes=after.bytes_read, after_maximum_read_request=after.largest_request,
                after_seek_calls=after.seeks, after_eof_reads=after.eof_reads,
                reduction_bytes=first.bytes_read + second.bytes_read - after.bytes_read,
                environment='in-memory workstation fixture', physical_hardware=False,
                limitations='Logical verification reads only; no elapsed time, physical throughput or exact RSS claim.')


if __name__ == '__main__':
    print(json.dumps(measure(), indent=2))
