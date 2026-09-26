"""Small real-signature, local-server tests for the unattended feed boundary."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from sv08_feed import Feed, SameOrigin, origin
from sv08_staging import Staging

NOW = 1790380800
BUNDLE = b'disposable signed-bundle fixture; real RAUC authentication is delegated to verify_bundle'


def openssl(*args):
    subprocess.run(['openssl', *map(str, args)], check=True, capture_output=True)


class Store:
    def __init__(self, root):
        self.root = root
        self.state = {'auto_update': True, 'pending': None}

    @contextmanager
    def locked(self):
        yield

    def load(self):
        return self.state


class Transaction:
    def __init__(self, store):
        self.store = store
        self.backend = type('Backend', (), {'policy': {'compatible': 'sv08-test-v1', 'max_bundle_bytes': 1024}})()
        self.journal = None
        self.stages = 0
        self.arms = 0
        self.fail_stage = False
        self.fail_arm = False

    def require_source(self, state, boot):
        if boot['mode'] != 'immutable' or state.get('customized'):
            raise ValueError('Customized/writable source')

    def load(self):
        return self.journal

    def stage_upload(self, staging, digest, verify, boot, automatic):
        assert automatic
        if not self.store.state['auto_update']:
            raise ValueError('Opted out before staging')
        with staging.lease(digest, verify) as (_, proof):
            if self.fail_stage:
                raise ValueError('Injected pre-write refusal')
            self.stages += 1
            self.journal = dict(phase='staged', release=proof['release'], bundle_sha256=digest)

    def arm(self, boot, automatic):
        assert automatic
        if not self.store.state['auto_update']:
            raise ValueError('Opted out before arming')
        if self.fail_arm:
            self.journal['phase'] = 'arming'
            raise ValueError('Injected uncertain arm')
        self.arms += 1
        self.journal['phase'] = 'armed'


class Server(BaseHTTPRequestHandler):
    objects = {}
    def do_GET(self):
        body = self.objects.get(self.path)
        if body is None:
            self.send_error(404); return
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *args):
        pass


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path.home())
        root = Path(self.tmp.name)
        self.store = Store(root)
        self.stage_root = root / 'bundles'; self.stage_root.mkdir(mode=0o700)
        self.staging = Staging(self.stage_root, max_bytes=1024, reserve_bytes=0, owner_uid=os.geteuid())
        self.tx = Transaction(self.store)
        self.cert, self.key = root / 'cert.pem', root / 'key.pem'
        openssl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '2',
                '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                '-keyout', self.key, '-out', self.cert)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Server)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(self.cert, self.key)
        self.server.socket = tls.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.base = f'https://localhost:{self.server.server_port}/'
        self.objects = {}
        Server.objects = self.objects
        self.config = dict(format_version=1, url=self.base, channel='stable',
                           ca_file=str(self.cert), signer_ca_file=str(self.cert))
        self.boot = dict(mode='immutable')
        self.feed = Feed(self.store, self.staging, self.tx, self.boot, self.verify,
                         self.config, now=lambda: NOW)
        self.publish()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.tmp.cleanup()

    def verify(self, path):
        contents = path.read_bytes()
        if contents != BUNDLE:
            raise ValueError('Bundle signature invalid')
        return dict(release='release-2', compatible='sv08-test-v1',
                    bundle_sha256=hashlib.sha256(contents).hexdigest())

    def publish(self, **changes):
        index = dict(format_version=1, channel='stable', sequence=2, issued=NOW-60,
                     expires=NOW+3600, compatible='sv08-test-v1', release='release-2',
                     bundle='release-2.raucb', bytes=len(BUNDLE), sha256=hashlib.sha256(BUNDLE).hexdigest())
        index.update(changes)
        data = json.dumps(index, sort_keys=True, separators=(',', ':')).encode()
        content = self.store.root / 'to-sign'; signature = self.store.root / 'signature'
        content.write_bytes(data)
        openssl('cms', '-sign', '-binary', '-in', content, '-signer', self.cert, '-inkey', self.key,
                '-outform', 'DER', '-out', signature)
        self.objects.update({'/index.json': data, '/index.json.p7s': signature.read_bytes(),
                             '/release-2.raucb': BUNDLE})
        return index

    def test_signed_local_feed_stages_and_arms_once(self):
        self.assertEqual(self.feed.run(), 'armed-next-boot')
        self.assertEqual((self.tx.stages, self.tx.arms), (1, 1))
        with self.assertRaisesRegex(ValueError, 'already active'):
            self.feed.run()
        self.assertEqual((self.tx.stages, self.tx.arms), (1, 1))

    def test_opt_out_and_recheck_after_download(self):
        self.store.state['auto_update'] = False
        with self.assertRaisesRegex(ValueError, 'disabled'):
            self.feed.run()
        self.store.state['auto_update'] = True
        original = self.feed.fetch
        def opt_out(url, limit, deadline):
            if url.endswith('.raucb'):
                self.store.state['auto_update'] = False
            return original(url, limit, deadline)
        self.feed.fetch = opt_out
        with self.assertRaisesRegex(ValueError, 'disabled'):
            self.feed.run()
        self.assertEqual((self.tx.stages, self.tx.arms), (0, 0))

    def test_signature_expiry_future_and_clock_rollback(self):
        self.objects['/index.json'] = b'{}'
        with self.assertRaisesRegex(ValueError, 'signature'):
            self.feed.index()
        self.publish(issued=NOW+1)
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.feed.index()
        self.publish(expires=NOW)
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.feed.index()
        self.publish()
        index, at = self.feed.index()
        with self.store.locked(): self.feed._sequence(index, at)
        self.feed.now = lambda: NOW-1
        with self.assertRaisesRegex(ValueError, 'backward'):
            self.feed.run()

    def test_replay_damage_missing_and_interrupted_publication(self):
        index, at = self.feed.index()
        with self.store.locked(): self.feed._sequence(index, at)
        self.publish(sequence=1)
        with self.assertRaisesRegex(ValueError, 'replay'):
            self.feed.run()
        self.publish(sequence=2)
        self.feed.sequence_path.write_text('{broken')
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            self.feed.run()
        self.feed.sequence_path.unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.feed.run()

    def test_same_sequence_cannot_change_signed_metadata_for_same_bundle(self):
        index, at = self.feed.index()
        with self.store.locked(): self.feed._sequence(index, at)
        # Bundle bytes and their declared hash stay identical; only signed
        # metadata changes, which must still count as sequence equivocation.
        self.publish(release='different-release')
        with self.assertRaisesRegex(ValueError, 'equivocation'):
            self.feed.run()

    def test_failed_stage_reuses_authenticated_published_bundle(self):
        self.tx.fail_stage = True
        with self.assertRaisesRegex(ValueError, 'Injected'):
            self.feed.run()
        self.assertTrue(self.staging.path(hashlib.sha256(BUNDLE).hexdigest()).exists())
        self.tx.fail_stage = False
        self.assertEqual(self.feed.run(), 'armed-next-boot')
        self.assertEqual((self.tx.stages, self.tx.arms), (1, 1))

    def test_killed_download_partial_is_reclaimed_on_next_poll(self):
        orphan = self.stage_root / ('.partial-' + 'a' * 32)
        orphan.write_bytes(b'incomplete transfer')
        orphan.chmod(0o600)
        self.assertEqual(self.feed.run(), 'armed-next-boot')
        self.assertFalse(orphan.exists())

    def test_unjournaled_published_bundle_from_interrupted_poll_is_reclaimed(self):
        stale = self.staging.path('e' * 64)
        stale.write_bytes(b'complete but not journaled')
        stale.chmod(0o400)
        self.assertEqual(self.feed.run(), 'armed-next-boot')
        self.assertFalse(stale.exists())

    def test_unknown_staging_file_still_fails_closed(self):
        unexpected = self.stage_root / 'leftover.tmp'
        unexpected.write_bytes(b'not managed')
        with self.assertRaisesRegex(ValueError, 'existing staged'):
            self.feed.run()
        self.assertTrue(unexpected.exists())
        self.assertEqual((self.tx.stages, self.tx.arms), (0, 0))

    def test_staged_resume_and_uncertain_mutations_do_not_replay(self):
        digest = hashlib.sha256(BUNDLE).hexdigest()
        self.tx.journal = dict(phase='staged', release='release-2', bundle_sha256=digest)
        self.assertEqual(self.feed.run(), 'armed-next-boot')
        self.assertEqual((self.tx.stages, self.tx.arms), (0, 1))
        for phase in ('installing', 'arming', 'armed'):
            self.tx.journal['phase'] = phase
            with self.assertRaisesRegex(ValueError, 'already active'):
                self.feed.run()
        self.assertEqual((self.tx.stages, self.tx.arms), (0, 1))
        self.tx.journal['phase'] = 'staged'
        self.tx.fail_arm = True
        with self.assertRaisesRegex(ValueError, 'uncertain arm'):
            self.feed.run()
        with self.assertRaisesRegex(ValueError, 'already active'):
            self.feed.run()
        self.assertEqual((self.tx.stages, self.tx.arms), (0, 1))

    def test_busy_and_customized_refuse_before_network_or_mutation(self):
        self.store.state['pending'] = {'id': 'busy'}
        with self.assertRaisesRegex(ValueError, 'already active'):
            self.feed.run()
        self.store.state['pending'] = None
        self.store.state['customized'] = True
        with self.assertRaisesRegex(ValueError, 'Customized'):
            self.feed.run()
        self.assertEqual((self.tx.stages, self.tx.arms), (0, 0))

    def test_profile_truncation_mode_and_origin(self):
        self.publish(compatible='other')
        with self.assertRaisesRegex(ValueError, 'profile'):
            self.feed.run()
        self.publish()
        self.objects['/release-2.raucb'] = BUNDLE[:-1]
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            self.feed.run()
        self.assertEqual(self.tx.stages, 0)
        self.boot['mode'] = 'writable'
        with self.assertRaisesRegex(ValueError, 'writable'):
            self.feed.run()
        with self.assertRaisesRegex(ValueError, 'HTTPS origin'):
            origin('http://example.invalid/')
        redirects = SameOrigin(origin(self.base))
        with self.assertRaisesRegex(ValueError, 'redirect'):
            redirects.redirect_request(Request(self.base), None, 302, 'redirect', {},
                                       'https://another.example.invalid/bundle.raucb')
        with self.assertRaisesRegex(ValueError, 'HTTPS origin'):
            redirects.redirect_request(Request(self.base), None, 302, 'redirect', {},
                                       'http://127.0.0.1/bundle.raucb')


if __name__ == '__main__':
    unittest.main()
