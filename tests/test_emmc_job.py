"""Failure and concurrency tests for the QEMU-only one-shot claim service."""
import json
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path
from urllib import error, request

from sv08_emmc_job import ClaimHTTPServer, ClaimState, canonical_json, make_descriptor


def descriptor():
    return make_descriptor(job_id='qemu-reimage-test-001', source_bytes=7818182656,
                           source_sha256='a' * 64, target_serial='SV08_QEMU_REIMAGE_TEST_ONLY',
                           target_bytes=32000000000, image_bytes=7818182656,
                           image_sha256='b' * 64,
                           gpt={'sha256': 'c' * 64, 'partitions': 6})


def payload(desc):
    from sv08_emmc_job import sha256_bytes
    return {'job_id': desc['job_id'],
            'descriptor_sha256': sha256_bytes(canonical_json(desc))}


class ClaimStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temp.name) / 'state'
        self.desc = descriptor()
        self.state = ClaimState.arm_new(self.state_dir, self.desc)

    def tearDown(self):
        self.temp.cleanup()

    def test_one_claim_is_durable_across_reopen(self):
        self.assertEqual(self.state.consume(payload(self.desc))[0], 200)
        self.assertFalse((self.state_dir / 'armed.json').exists())
        state = ClaimState.reopen(self.state_dir, self.desc)
        self.assertEqual(state.consume(payload(self.desc))[0], 409)

    def test_concurrent_callers_get_exactly_one_claim(self):
        states = [ClaimState.reopen(self.state_dir, self.desc) for _ in range(12)]
        barrier = threading.Barrier(len(states))
        outcomes = []
        lock = threading.Lock()

        def call(state):
            barrier.wait()
            result = state.consume(payload(self.desc))[0]
            with lock:
                outcomes.append(result)

        threads = [threading.Thread(target=call, args=(state,)) for state in states]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(outcomes.count(200), 1)
        self.assertEqual(outcomes.count(409), len(states) - 1)

    def test_wrong_descriptor_and_missing_service_do_not_consume(self):
        wrong = payload(self.desc)
        wrong['descriptor_sha256'] = 'd' * 64
        self.assertEqual(self.state.consume(wrong)[0], 409)
        self.assertTrue((self.state_dir / 'armed.json').exists())
        (self.state_dir / 'armed.json').unlink()
        self.assertEqual(self.state.consume(payload(self.desc))[0], 503)

    def test_missing_or_corrupt_persisted_state_fails_closed(self):
        (self.state_dir / 'armed.json').unlink()
        with self.assertRaisesRegex(ValueError, 'missing claim state'):
            ClaimState.reopen(self.state_dir, self.desc)
        (self.state_dir / 'claim.json').write_text('{partial')
        reopened = ClaimState.reopen(self.state_dir, self.desc)
        self.assertEqual(reopened.consume(payload(self.desc))[0], 409)

    def test_changed_armed_descriptor_fails_closed(self):
        (self.state_dir / 'armed.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'descriptor changed'):
            ClaimState.reopen(self.state_dir, self.desc)

    def test_lost_acknowledgment_cannot_replay(self):
        server = ClaimHTTPServer(('127.0.0.1', 0), self.state, drop_first_ack=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}/claim'
        data = canonical_json(payload(self.desc))
        try:
            with self.assertRaises((error.URLError, ConnectionError, TimeoutError)):
                request.urlopen(request.Request(url, data=data, method='POST'), timeout=2)
            with self.assertRaises(error.HTTPError) as response:
                request.urlopen(request.Request(url, data=data, method='POST'), timeout=2)
            self.assertEqual(response.exception.code, 409)
            self.assertTrue((self.state_dir / 'claim.json').exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_no_automatic_rearm_after_interrupted_writer(self):
        for phase in ('before-write', 'partial-write', 'flush', 'readback'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp) / 'state'
                state = ClaimState.arm_new(directory, self.desc)
                self.assertEqual(state.consume(payload(self.desc))[0], 200)
                # Simulate process/power loss at each write boundary. The
                # consumed marker outlives the writer and no success result.
                (directory / 'uncertain-phase').write_text(phase)
                restarted = ClaimState.reopen(directory, self.desc)
                self.assertEqual(restarted.consume(payload(self.desc))[0], 409)
                self.assertFalse((directory / 'armed.json').exists())

    def test_file_sync_error_leaves_claim_consumed(self):
        with mock.patch('sv08_emmc_job.os.fsync', side_effect=OSError('injected fsync error')):
            status, _ = self.state.consume(payload(self.desc))
        self.assertEqual(status, 503)
        self.assertTrue((self.state_dir / 'claim.json').exists())
        # Even when the response was uncertain, restart must not arm a retry.
        reopened = ClaimState.reopen(self.state_dir, self.desc)
        self.assertEqual(reopened.consume(payload(self.desc))[0], 409)

    def test_unexpected_state_file_fails_closed(self):
        (self.state_dir / 'unexpected').write_text('unknown')
        self.assertEqual(self.state.consume(payload(self.desc))[0], 503)


if __name__ == '__main__':
    unittest.main()
