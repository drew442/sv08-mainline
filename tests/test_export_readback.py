from contextlib import contextmanager
import hashlib
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import sv08_export as export


def digest(data): return hashlib.sha256(data).hexdigest()


def archive_bytes(entries):
    output = io.BytesIO(); expected = {}; largest = 512
    with tarfile.open(fileobj=output, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for info, payload in entries:
            largest = max(largest, len(info.tobuf(format=tarfile.PAX_FORMAT)))
            archive.addfile(info, io.BytesIO(payload) if payload is not None else None)
            expected[info.name] = digest(payload) if payload is not None else None
    return output.getvalue(), expected, largest


def regular(name, payload):
    info = tarfile.TarInfo(name); info.size = len(payload)
    return info, payload


class Counted(io.BytesIO):
    def __init__(self, data):
        super().__init__(data); self.bytes_read = 0; self.requests = []

    def read(self, size=-1):
        if size < 0: raise AssertionError('Unbounded read')
        self.requests.append(size)
        value = super().read(size); self.bytes_read += len(value)
        return value

    def seek(self, *_): raise AssertionError('Readback must move forward only')


class ReadbackTests(unittest.TestCase):
    def verify(self, raw, expected, header_bytes, *, original=None):
        original = raw if original is None else original
        source = Counted(raw)
        result = export.verify_stream(source, expected, len(original), digest(original), header_bytes)
        self.assertEqual(result, digest(original))
        self.assertEqual(source.bytes_read, len(raw))
        self.assertLessEqual(max(source.requests), export.CHUNK)
        return source

    def test_exact_approved_fixture_is_read_once_including_padding(self):
        raw, expected, header = archive_bytes([regular('data/fixture.bin', b'offline-readback-measure\n' * 364722)])
        self.assertEqual(len(raw), 9123840)
        self.assertEqual(digest(raw), '0767efa76615052ca0c1506ec6c76bbdeee2ce989c44dfa5aff434872102aa72')
        self.verify(raw, expected, header)

    def test_complete_digest_includes_a_genuine_final_drain(self):
        raw, expected, header = archive_bytes([regular('data/file', b'x' * 9216)])
        self.assertEqual(len(raw), 20480)
        consumed = Counted(raw)
        with tarfile.open(fileobj=consumed, mode='r|', bufsize=export.TAR_BUFFER) as archive:
            for member in archive: archive.extractfile(member).read()
        self.assertEqual(consumed.bytes_read, 10240)
        source = self.verify(raw, expected, header)
        self.assertIn(export.CHUNK, source.requests)

    def test_valid_unicode_pax_metadata_larger_than_one_stream_buffer(self):
        raw, expected, header = archive_bytes([regular('data/' + 'é' * 20000, b'preserved')])
        self.assertGreater(header, export.TAR_BUFFER)
        self.verify(raw, expected, header)

    def test_corrupt_header_payload_valid_metadata_terminator_and_padding_refused(self):
        info, payload = regular('data/file', b'x' * 100)
        raw, expected, header = archive_bytes([(info, payload)])
        alternate = tarfile.TarInfo('data/file'); alternate.size = len(payload); alternate.uid = 123
        variants = {
            'header-checksum': bytes([raw[0] ^ 1]) + raw[1:],
            'payload': raw[:512] + b'y' + raw[513:],
            'valid-changed-metadata': alternate.tobuf() + raw[512:],
            'malformed-after-last-member': raw[:1024] + b'X' * 512 + raw[1536:],
            'trailing-padding': raw[:-1] + b'X',
        }
        for name, damaged in variants.items():
            with self.subTest(name=name), self.assertRaises((ValueError, tarfile.TarError)):
                self.verify(damaged, expected, header, original=raw)

    def test_truncated_payload_padding_and_appended_data_refused(self):
        raw, expected, header = archive_bytes([regular('data/file', b'x' * 100)])
        for changed in (raw[:550], raw[:-1], raw + b'extra'):
            with self.subTest(length=len(changed)), self.assertRaises((ValueError, tarfile.TarError)):
                self.verify(changed, expected, header, original=raw)

    def test_duplicate_unexpected_special_and_missing_members_refused(self):
        entry = regular('data/file', b'payload')
        raw, expected, header = archive_bytes([entry, entry])
        with self.assertRaisesRegex(ValueError, 'Duplicate'): self.verify(raw, expected, header)
        raw, _, header = archive_bytes([entry, regular('data/extra', b'unknown')])
        with self.assertRaisesRegex(ValueError, 'Unexpected'): self.verify(raw, expected, header)
        link = tarfile.TarInfo('data/file'); link.type = tarfile.SYMTYPE; link.linkname = '/etc/passwd'
        raw, _, header = archive_bytes([(link, None)])
        with self.assertRaisesRegex(ValueError, 'Unexpected'): self.verify(raw, expected, header)
        raw, _, header = archive_bytes([entry])
        with self.assertRaisesRegex(ValueError, 'verification'):
            self.verify(raw, {**expected, 'missing': None}, header)

    def test_pax_nested_pax_and_sparse_map_reads_stay_bounded(self):
        pax = tarfile.TarInfo('pax'); pax.type = tarfile.XHDTYPE; pax.size = 1024 * 1024
        oversized = pax.tobuf(format=tarfile.USTAR_FORMAT) + b'X' * pax.size + bytes(export.TAR_BUFFER)
        pax.size = 0
        nested = pax.tobuf(format=tarfile.USTAR_FORMAT) * 80 + bytes(export.TAR_BUFFER)
        sparse = tarfile.TarInfo('data/sparse')
        fields = b'1000000\n' + b'0\n0\n' * 20000
        sparse.size = len(fields)
        sparse.pax_headers = {'GNU.sparse.major': '1', 'GNU.sparse.minor': '0',
                              'GNU.sparse.realsize': '0', 'GNU.sparse.name': 'data/sparse'}
        sparse_raw = sparse.tobuf(format=tarfile.PAX_FORMAT) + fields + bytes(export.TAR_BUFFER)
        for raw in (oversized, nested, sparse_raw):
            source = Counted(raw)
            with self.subTest(kind=raw[:30]), self.assertRaisesRegex(ValueError, 'metadata.*budget'):
                export.verify_stream(source, {}, len(raw), digest(raw), 512)
            self.assertLessEqual(source.bytes_read, 512 + export.TAR_BUFFER)
            self.assertLessEqual(max(source.requests), export.TAR_BUFFER)

    def test_sparse_expansion_and_invalid_member_sizes_refused_before_extraction(self):
        sparse = tarfile.TarInfo('data/sparse'); sparse.size = 512
        sparse.pax_headers = {'GNU.sparse.major': '1', 'GNU.sparse.minor': '0',
                              'GNU.sparse.realsize': str(16 * 1024**2),
                              'GNU.sparse.name': sparse.name}
        sparse_raw, sparse_expected, sparse_header = archive_bytes([(sparse, b'0\n' + bytes(510))])
        self.assertEqual(len(sparse_raw), export.TAR_BUFFER)
        oversized = tarfile.TarInfo('data/oversized'); oversized.size = 16 * 1024**2
        oversized_raw = oversized.tobuf() + bytes(export.TAR_BUFFER - 512)
        negative = tarfile.TarInfo('data/negative'); negative.pax_headers = {'size': '-1'}
        negative_raw, negative_expected, negative_header = archive_bytes([(negative, b'')])
        cases = ((sparse_raw, sparse_expected, sparse_header, 'sparse'),
                 (oversized_raw, {oversized.name: digest(b'')}, 512, 'member size'),
                 (negative_raw, negative_expected, negative_header, 'member size|verification'))
        for raw, expected, header, reason in cases:
            with self.subTest(reason=reason), patch.object(tarfile.TarFile, 'extractfile') as extract:
                with self.assertRaisesRegex(ValueError, reason): self.verify(raw, expected, header)
                extract.assert_not_called()


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.source = self.root / 'source'; self.source.mkdir()
        self.target = self.root / 'destination'; self.target.mkdir()
        self.original = b'x' * 8192
        (self.source / 'fixture.bin').write_bytes(self.original)
        (self.target / 'keep').write_bytes(b'previous data')
        self.depth = 0
        @contextmanager
        def admission(target):
            self.assertEqual(target, 'test'); self.assertEqual(self.depth, 0)
            self.depth += 1
            try: yield
            finally: self.depth -= 1
        self.exporter = export.Export(self.source, {'test': {'path': self.target, 'label': 'Disposable'}},
                                      admission, reserve_bytes=0)

    def preserved(self):
        self.assertEqual({p.name: p.read_bytes() for p in self.target.iterdir()}, {'keep': b'previous data'})
        self.assertEqual((self.source / 'fixture.bin').read_bytes(), self.original)
        self.assertEqual(self.depth, 0)

    def test_actual_export_uses_one_readback_and_never_reads_the_writer(self):
        real_open, real_fdopen = open, os.fdopen
        reads = []; opened = []
        class Proxy:
            def __init__(self, stream, writing=False): self.stream, self.writing = stream, writing
            def __getattr__(self, name): return getattr(self.stream, name)
            def __enter__(self): return self
            def __exit__(self, *args): return self.stream.__exit__(*args)
            def read(self, size=-1):
                if self.writing: raise AssertionError('Separate writer digest scan')
                if size < 0: raise AssertionError('Unbounded verification read')
                value = self.stream.read(size); reads.append(len(value)); return value
            def seek(self, *_): raise AssertionError('No verification seek or second pass')
        def read_file(*args, **kwargs):
            opened.append(args[0]); return Proxy(real_open(*args, **kwargs))
        def fd_file(fd, mode, *args, **kwargs):
            stream = real_fdopen(fd, mode, *args, **kwargs)
            return Proxy(stream, True) if mode == 'w+b' else stream
        plan = self.exporter.prepare('test')
        with patch('sv08_export.open', read_file, create=True), patch('sv08_export.os.fdopen', fd_file):
            result = self.exporter.execute(plan)
        raw = (self.target / result['filename']).read_bytes()
        self.assertEqual(len(opened), 1)
        self.assertEqual(sum(reads), len(raw))
        self.assertEqual(result['sha256'], digest(raw))
        self.assertEqual((self.target / 'keep').read_bytes(), b'previous data')

    def test_real_readback_corruption_and_truncation_prevent_publication(self):
        original_verify = export.verify_archive
        for kind in ('header', 'payload', 'manifest', 'metadata', 'late-header', 'padding', 'truncate', 'append'):
            with self.subTest(kind=kind):
                def corrupt(path, *args):
                    with tarfile.open(path, 'r:') as archive: members = archive.getmembers()
                    raw = bytearray(Path(path).read_bytes())
                    if kind == 'truncate': del raw[-1:]
                    elif kind == 'append': raw += b'changed'
                    elif kind == 'metadata':
                        info = members[0]; info.uid += 1; raw[:512] = info.tobuf()
                    elif kind == 'late-header':
                        last = members[-1]; start = last.offset_data + ((last.size + 511) // 512) * 512
                        raw[start:start+512] = b'X' * 512
                    else:
                        position = {'header': 0, 'payload': members[0].offset_data,
                                    'manifest': members[-1].offset_data, 'padding': len(raw)-1}[kind]
                        raw[position] ^= 1
                    Path(path).write_bytes(raw)
                    return original_verify(path, *args)
                with patch('sv08_export.verify_archive', corrupt), self.assertRaises((ValueError, OSError, tarfile.TarError)):
                    self.exporter.execute(self.exporter.prepare('test'))
                self.preserved()

    def test_final_drain_io_error_prevents_publication(self):
        original = export.ReadbackReader.read; failure = []
        def failed(reader, size):
            if reader.count == export.TAR_BUFFER and not reader.header_depth and size == export.CHUNK:
                failure.append(reader.count); raise OSError('Final drain I/O failure')
            return original(reader, size)
        with patch.object(export.ReadbackReader, 'read', failed), self.assertRaisesRegex(OSError, 'Final drain'):
            self.exporter.execute(self.exporter.prepare('test'))
        self.assertEqual(failure, [10240]); self.preserved()

    def test_short_write_and_file_fsync_failure_prevent_publication(self):
        writer = export.HashWriter(io.BytesIO())
        with patch.object(writer.stream, 'write', return_value=0), self.assertRaisesRegex(OSError, 'Short archive'):
            writer.write(b'data')
        with patch('sv08_export.os.fsync', side_effect=OSError('File fsync failure')):
            with self.assertRaisesRegex(OSError, 'File fsync'):
                self.exporter.execute(self.exporter.prepare('test'))
        self.preserved()
