"""Failure and concurrency tests for the QEMU-only one-shot claim service."""
import json
import os
import subprocess
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path
from urllib import error, request
from tests import sv08_emmc_job as job_module

ClaimHTTPServer = job_module.ClaimHTTPServer
ClaimState = job_module.ClaimState
canonical_json = job_module.canonical_json
make_descriptor = job_module.make_descriptor


def descriptor():
    return make_descriptor(job_id='qemu-reimage-test-001', source_bytes=7818182656,
                           source_sha256='a' * 64, target_serial='SV08_QEMU_REIMAGE_TEST_ONLY',
                           target_bytes=32000000000, image_bytes=7818182656,
                           image_sha256='b' * 64,
                           gpt={'sha256': 'c' * 64, 'partitions': 6})


def payload(desc):
    return {'job_id': desc['job_id'],
            'descriptor_sha256': job_module.sha256_bytes(canonical_json(desc)),
            'challenge': '01' * 32}


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
        saved = json.loads((self.state_dir / 'claim.json').read_text())
        self.assertEqual(saved['challenge'], payload(self.desc)['challenge'])
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

    def test_http_success_is_a_valid_signature_over_the_persisted_challenge(self):
        server = ClaimHTTPServer(('127.0.0.1', 0), self.state)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        data = canonical_json(payload(self.desc))
        events = []
        original_sync = job_module.fsync_directory
        original_sign = job_module.sign_receipt

        def observed_sync(path):
            original_sync(path)
            events.append('directory-synced')

        def observed_sign(message, key):
            self.assertGreaterEqual(events.count('directory-synced'), 2)
            self.assertTrue((self.state_dir / 'claim.json').exists())
            self.assertFalse((self.state_dir / 'armed.json').exists())
            events.append('signed')
            return original_sign(message, key)

        try:
            with mock.patch.object(job_module, 'fsync_directory', side_effect=observed_sync), \
                    mock.patch.object(job_module, 'sign_receipt', side_effect=observed_sign):
                response = request.urlopen(request.Request(
                    f'http://127.0.0.1:{server.server_port}/claim', data=data, method='POST'), timeout=2)
            self.assertEqual(response.status, 200)
            signature = bytes.fromhex(response.read().decode().strip())
            self.assertEqual(len(signature), 64)
            state = json.loads((self.state_dir / 'claim.json').read_text())
            message = (f"SV08-EMMC-CLAIM-RECEIPT-v1\njob_id={state['job_id']}\n"
                       f"descriptor_sha256={state['descriptor_sha256']}\n"
                       f"challenge={state['challenge']}\n").encode()
            keys = Path(__file__).parent / 'fixtures/sd-network-root/receipt-test-keys'
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / 'message').write_bytes(message)
                (root / 'signature').write_bytes(signature)
                result = subprocess.run([
                    'openssl', 'pkeyutl', '-verify', '-rawin', '-pubin', '-inkey',
                    str(keys / 'test-verification-key.pem'), '-in', str(root / 'message'),
                    '-sigfile', str(root / 'signature')], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            self.assertEqual(events[-1], 'signed')
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_forged_http_success_does_not_consume_claim_state(self):
        server = ClaimHTTPServer(('127.0.0.1', 0), self.state, receipt_fault='forged-200')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        data = canonical_json(payload(self.desc))
        try:
            response = request.urlopen(request.Request(
                f'http://127.0.0.1:{server.server_port}/claim', data=data, method='POST'), timeout=2)
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), bytes(64))
            self.assertTrue((self.state_dir / 'armed.json').exists())
            self.assertFalse((self.state_dir / 'claim.json').exists())
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_signing_failure_happens_after_durable_consumption_and_never_rearms(self):
        server = ClaimHTTPServer(('127.0.0.1', 0), self.state,
                                 receipt_signing_key=self.state_dir / 'missing-key.pem')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        data = canonical_json(payload(self.desc))
        try:
            with self.assertRaises(error.HTTPError) as response:
                request.urlopen(request.Request(
                    f'http://127.0.0.1:{server.server_port}/claim', data=data, method='POST'), timeout=2)
            self.assertEqual(response.exception.code, 503)
            self.assertTrue((self.state_dir / 'claim.json').exists())
            self.assertFalse((self.state_dir / 'armed.json').exists())
            reopened = ClaimState.reopen(self.state_dir, self.desc)
            self.assertEqual(reopened.consume(payload(self.desc))[0], 409)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_process_interruption_after_durable_publication_cannot_rearm(self):
        self.assertTrue(hasattr(os, 'fork'), 'POSIX process interruption test required')
        pid = os.fork()
        if pid == 0:
            original_sync = job_module.fsync_directory

            def exit_after_publication(path):
                original_sync(path)
                os._exit(73)

            job_module.fsync_directory = exit_after_publication
            self.state.consume(payload(self.desc))
            os._exit(74)
        _, status = os.waitpid(pid, 0)
        self.assertTrue(os.WIFEXITED(status))
        self.assertEqual(os.WEXITSTATUS(status), 73)
        self.assertTrue((self.state_dir / 'claim.json').exists())
        self.assertTrue((self.state_dir / 'armed.json').exists())
        restarted = ClaimState.reopen(self.state_dir, self.desc)
        self.assertEqual(restarted.consume(payload(self.desc))[0], 409)

    def test_process_interruption_before_file_fsync_fails_closed(self):
        self.assertTrue(hasattr(os, 'fork'), 'POSIX process interruption test required')
        pid = os.fork()
        if pid == 0:
            original_write = job_module.write_all

            def exit_before_sync(fd, data):
                original_write(fd, data)
                os._exit(72)

            job_module.write_all = exit_before_sync
            self.state.consume(payload(self.desc))
            os._exit(74)
        _, status = os.waitpid(pid, 0)
        self.assertTrue(os.WIFEXITED(status))
        self.assertEqual(os.WEXITSTATUS(status), 72)
        self.assertTrue((self.state_dir / 'claim.json').exists())
        self.assertTrue((self.state_dir / 'armed.json').exists())
        restarted = ClaimState.reopen(self.state_dir, self.desc)
        self.assertEqual(restarted.consume(payload(self.desc))[0], 409)

    def test_wrong_challenge_cannot_replay_a_durable_claim(self):
        first = payload(self.desc)
        self.assertEqual(self.state.consume(first)[0], 200)
        replay = dict(first, challenge='02' * 32)
        self.assertEqual(self.state.consume(replay)[0], 409)
        saved = json.loads((self.state_dir / 'claim.json').read_text())
        self.assertEqual(saved['challenge'], first['challenge'])

    def test_consumed_claim_cannot_be_rearmed_after_service_restart(self):
        self.assertEqual(self.state.consume(payload(self.desc))[0], 200)
        restarted = ClaimState.reopen(self.state_dir, self.desc)
        self.assertEqual(restarted.consume(payload(self.desc))[0], 409)
        self.assertFalse((self.state_dir / 'armed.json').exists())

    def test_file_sync_error_leaves_claim_consumed(self):
        with mock.patch.object(job_module.os, 'fsync', side_effect=OSError('injected fsync error')):
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
