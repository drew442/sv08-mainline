"""Disposable preparation checks; no physical image or target is opened."""
import json
import http.client
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

from scripts.prepare_h616_reimage_job import LOCAL, build_claim_server, prepare
from scripts.build_h616_reimage_candidate import IMAGE_BYTES
from tests.test_h616_reimage_candidate import synthetic_policy
from tests.sv08_emmc_job import ClaimState, canonical_json, receipt_message

REPO = Path(__file__).resolve().parents[1]


class PrepareJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LOCAL.mkdir(mode=0o700, exist_ok=True)

    def inputs(self, root):
        keys = REPO / 'tests/fixtures/sd-network-root/synthetic-keys'
        receipts = REPO / 'tests/fixtures/sd-network-root/receipt-test-keys'
        files = {}
        payloads = {
            'policy_path': canonical_json(synthetic_policy()),
            'job_signing_key': (keys / 'test-signing-key.pem').read_bytes(),
            'job_verification_key': (keys / 'test-verification-key.pem').read_bytes(),
            'receipt_signing_key': (receipts / 'test-signing-key.pem').read_bytes(),
            'receipt_verification_key': (receipts / 'test-verification-key.pem').read_bytes(),
        }
        for key, payload in payloads.items():
            path = root / key
            path.write_bytes(payload)
            path.chmod(0o600)
            files[key] = path
        image = root / 'source.img'
        with image.open('wb') as stream:
            stream.truncate(IMAGE_BYTES)
        files.update(image_path=image, state_dir=root / 'state',
                     source_server='10.0.2.2', source_export='/exports/exact',
                     claim_port=12000, now=1500, synthetic_test=True,
                     image_digest=lambda _path: synthetic_policy()['image_sha256'])
        return files

    def test_prepare_is_dry_run_then_durable_once(self):
        with tempfile.TemporaryDirectory(dir=LOCAL) as temporary:
            args = self.inputs(Path(temporary))
            receipt = prepare(**args)
            self.assertEqual(receipt['status'], 'prepared-not-served')
            self.assertFalse(args['state_dir'].exists())
            actual = prepare(**args, execute=True)
            self.assertEqual(actual['image_sha256'], synthetic_policy()['image_sha256'])
            self.assertEqual(actual['automatic_rearm'], False)
            self.assertEqual(json.loads((args['state_dir'] / 'job.json').read_bytes())['job_id'],
                             actual['job_id'])
            self.assertEqual((args['state_dir'] / 'claim').stat().st_mode & 0o777, 0o700)
            job = json.loads((args['state_dir'] / 'job.json').read_bytes())
            state = ClaimState.reopen(args['state_dir'] / 'claim', job)
            request = {'job_id': job['job_id'], 'descriptor_sha256': state.descriptor_sha256,
                       'challenge': '1' * 64}
            self.assertEqual(state.consume(request)[0], 200)
            self.assertEqual(ClaimState.reopen(args['state_dir'] / 'claim', job).consume(request)[0], 409)
            with self.assertRaises(ValueError):
                prepare(**args, execute=True)

    def test_wrong_source_and_key_refuse_before_state(self):
        with tempfile.TemporaryDirectory(dir=LOCAL) as temporary:
            args = self.inputs(Path(temporary))
            with self.assertRaisesRegex(ValueError, 'exact reviewed raw'):
                prepare(**dict(args, image_digest=lambda _path: '0' * 64), execute=True)
            self.assertFalse(args['state_dir'].exists())
            args['receipt_verification_key'].write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'keys differ'):
                prepare(**args, execute=True)
            self.assertFalse(args['state_dir'].exists())

    def test_physical_cli_cannot_accept_synthetic_policy(self):
        with tempfile.TemporaryDirectory(dir=LOCAL) as temporary:
            args = self.inputs(Path(temporary))
            args['synthetic_test'] = False
            with self.assertRaisesRegex(ValueError, 'separate'):
                prepare(**args)
            self.assertFalse(args['state_dir'].exists())

    def test_listener_refuses_expired_or_consumed_claim(self):
        with tempfile.TemporaryDirectory(dir=LOCAL) as temporary:
            args = self.inputs(Path(temporary))
            prepare(**args, execute=True)
            with mock.patch('scripts.prepare_h616_reimage_job.ClaimHTTPServer',
                            side_effect=lambda address, state, **_kwargs: (address, state)):
                address, wrapper = build_claim_server(
                    state_dir=args['state_dir'], image_path=args['image_path'],
                    job_verification_key=args['job_verification_key'],
                    receipt_signing_key=args['receipt_signing_key'], bind='10.0.2.2',
                    image_digest=args['image_digest'], synthetic_test=True, now=1501)
            self.assertEqual(address, ('10.0.2.2', 12000))
            job = json.loads((args['state_dir'] / 'job.json').read_bytes())
            state = ClaimState.reopen(args['state_dir'] / 'claim', job)
            request = {'job_id': job['job_id'], 'descriptor_sha256': state.descriptor_sha256,
                       'challenge': '2' * 64}
            with mock.patch('scripts.prepare_h616_reimage_job.time.time', return_value=3300):
                self.assertEqual(wrapper.consume(request)[0], 409)
            self.assertFalse(state.claimed.exists())
            with mock.patch('scripts.prepare_h616_reimage_job.time.time', return_value=1501):
                self.assertEqual(wrapper.consume(request)[0], 200)
            with self.assertRaisesRegex(ValueError, 'consumed'):
                build_claim_server(state_dir=args['state_dir'], image_path=args['image_path'],
                                   job_verification_key=args['job_verification_key'],
                                   receipt_signing_key=args['receipt_signing_key'],
                                   bind='10.0.2.2', image_digest=args['image_digest'],
                                   synthetic_test=True, now=1501)

    def test_real_loopback_claim_signs_only_once(self):
        with tempfile.TemporaryDirectory(dir=LOCAL) as temporary:
            root = Path(temporary)
            args = self.inputs(root)
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                args['claim_port'] = probe.getsockname()[1]
            args['now'] = int(time.time())
            prepare(**args, execute=True)
            job = json.loads((args['state_dir'] / 'job.json').read_bytes())
            state = ClaimState.reopen(args['state_dir'] / 'claim', job)
            request = {'job_id': job['job_id'], 'descriptor_sha256': state.descriptor_sha256,
                       'challenge': '7' * 64}
            with self.assertRaisesRegex(ValueError, 'synthetic-test-only'):
                build_claim_server(state_dir=args['state_dir'], image_path=args['image_path'],
                                   job_verification_key=args['job_verification_key'],
                                   receipt_signing_key=args['receipt_signing_key'],
                                   bind='10.0.2.2', listen_bind='127.0.0.1')
            server = build_claim_server(state_dir=args['state_dir'],
                                        image_path=args['image_path'],
                                        job_verification_key=args['job_verification_key'],
                                        receipt_signing_key=args['receipt_signing_key'],
                                        bind='10.0.2.2', listen_bind='127.0.0.1',
                                        image_digest=args['image_digest'], synthetic_test=True,
                                        now=args['now'])
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                def post():
                    connection = http.client.HTTPConnection('127.0.0.1', args['claim_port'],
                                                            timeout=5)
                    try:
                        connection.request('POST', '/claim', body=json.dumps(request),
                                           headers={'Content-Type': 'application/json'})
                        response = connection.getresponse()
                        return response.status, response.read()
                    finally:
                        connection.close()

                status, signature_hex = post()
                self.assertEqual(status, 200)
                signature = bytes.fromhex(signature_hex.strip().decode())
                message = receipt_message(job['job_id'], state.descriptor_sha256,
                                          request['challenge'])
                message_file, signature_file = root / 'message', root / 'signature'
                message_file.write_bytes(message)
                signature_file.write_bytes(signature)
                verified = subprocess.run(['openssl', 'pkeyutl', '-verify', '-rawin',
                                           '-pubin', '-inkey', str(args['receipt_verification_key']),
                                           '-in', str(message_file), '-sigfile', str(signature_file)],
                                          capture_output=True, timeout=10)
                self.assertEqual(verified.returncode, 0, verified.stderr)
                self.assertEqual(post(), (409, b'CONSUMED\n'))
                self.assertTrue(state.claimed.exists())
            finally:
                server.shutdown()
                worker.join(timeout=5)
                server.server_close()


if __name__ == '__main__':
    unittest.main()
