#!/usr/bin/env python3
"""Fixed signed release discovery for the existing SV08 A/B transaction.

The feed is an optional delivery mechanism, not a disk writer. RAUC remains the
bundle and inactive-slot authority. Retire this shim if RAUC gains equivalent
signed discovery, anti-replay and printer admission support.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import tempfile
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPSHandler, HTTPHandler, HTTPRedirectHandler, build_opener, Request

from sv08_state import atomic_json, fsync_dir, identifier
from sv08_transaction import Transaction

MAX_INDEX = 16 * 1024
MAX_SIGNATURE = 32 * 1024
MIN_TRUSTED_EPOCH = 1735689600  # 2025-01-01; reject unset RTC/time sync.
FETCH_SECONDS = 120


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate signed index field')
        result[key] = value
    return result


def origin(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Feed requires a fixed HTTPS origin')
    return parsed.scheme, parsed.hostname.lower(), parsed.port or 443


class SameOrigin(HTTPRedirectHandler):
    def __init__(self, expected):
        self.expected = expected

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if origin(newurl) != self.expected:
            raise ValueError('Feed redirect left the configured HTTPS origin')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class LimitedReader:
    def __init__(self, stream, deadline):
        self.stream, self.deadline = stream, deadline

    def read(self, size):
        if time.monotonic() > self.deadline:
            raise ValueError('Feed download exceeded its deadline')
        data = self.stream.read(size)
        if time.monotonic() > self.deadline:
            raise ValueError('Feed download exceeded its deadline')
        return data


class Feed:
    def __init__(self, store, staging, transaction, boot, verify_bundle, config,
                 *, now=None, fetch=None):
        self.store, self.staging, self.tx, self.boot = store, staging, transaction, boot
        self.verify_bundle, self.config = verify_bundle, config
        self.now = now or trusted_time
        self.fetch = fetch or self._fetch
        if set(config) != {'format_version', 'url', 'channel', 'ca_file', 'signer_ca_file'} or config['format_version'] != 1:
            raise ValueError('Unsupported fixed feed configuration')
        origin(config['url'])
        if not urlsplit(config['url']).path.endswith('/') or urlsplit(config['url']).query:
            raise ValueError('Feed URL must be a fixed directory URL')
        identifier(config['channel'])
        for name in ('ca_file', 'signer_ca_file'):
            if not Path(config[name]).is_file():
                raise ValueError('Feed trust anchor is unavailable')
        self.sequence_path = store.root / 'feed-sequence.json'
        self.status_path = store.root / 'feed-status.json'

    def _fetch(self, url, limit, deadline):
        if origin(url) != origin(self.config['url']):
            raise ValueError('Feed URL left the configured origin')
        context = ssl.create_default_context(cafile=self.config['ca_file'])
        opener = build_opener(HTTPSHandler(context=context), SameOrigin(origin(self.config['url'])))
        response = opener.open(Request(url, headers={'User-Agent': 'sv08-update/1'}), timeout=15)
        if origin(response.url) != origin(self.config['url']):
            response.close()
            raise ValueError('Feed response left the configured origin')
        length = response.headers.get('Content-Length')
        if length is not None and (not length.isascii() or not length.isdecimal() or int(length) > limit):
            response.close()
            raise ValueError('Feed object exceeds its bound')
        return response

    def _small(self, suffix, limit, deadline):
        url = urljoin(self.config['url'], suffix)
        with self.fetch(url, limit, deadline) as stream:
            reader = LimitedReader(stream, deadline)
            data = reader.read(limit + 1)
            if len(data) > limit:
                raise ValueError('Feed object exceeds its bound')
            return data

    def index(self):
        deadline = time.monotonic() + FETCH_SECONDS
        document = self._small('index.json', MAX_INDEX, deadline)
        signature = self._small('index.json.p7s', MAX_SIGNATURE, deadline)
        with tempfile.TemporaryDirectory(prefix='.feed-verify-', dir=self.store.root) as directory:
            content = Path(directory) / 'index'; signed = Path(directory) / 'signature'
            content.write_bytes(document); signed.write_bytes(signature)
            result = subprocess.run(['/usr/bin/openssl', 'cms', '-verify', '-binary', '-inform', 'DER',
                                     '-in', str(signed), '-content', str(content), '-CAfile',
                                     self.config['signer_ca_file'], '-purpose', 'any', '-out', os.devnull],
                                    capture_output=True, timeout=15)
            if result.returncode:
                raise ValueError('Release index signature is invalid')
        index = json.loads(document, object_pairs_hook=unique_object)
        if not isinstance(index, dict) or set(index) != {'format_version', 'channel', 'sequence', 'issued', 'expires',
                                                       'compatible', 'release', 'bundle', 'bytes', 'sha256'}:
            raise ValueError('Invalid signed release index schema')
        if (index['format_version'] != 1 or index['channel'] != self.config['channel'] or
                type(index['sequence']) is not int or index['sequence'] < 1 or
                type(index['issued']) is not int or type(index['expires']) is not int or
                type(index['bytes']) is not int or index['bytes'] < 1 or
                not isinstance(index['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', index['sha256']) or
                not isinstance(index['bundle'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,100}\.raucb', index['bundle'])):
            raise ValueError('Invalid signed release values')
        identifier(index['release'])
        if index['compatible'] != self.tx.backend.policy['compatible']:
            raise ValueError('Release targets another hardware profile')
        now = self.now()
        if type(now) is not int or now < MIN_TRUSTED_EPOCH or not index['issued'] <= now < index['expires'] or index['expires'] - index['issued'] > 30*86400:
            raise ValueError('Trusted time is absent or signed release index is stale')
        if index['bytes'] > min(self.staging.max_bytes, self.tx.backend.policy['max_bundle_bytes']):
            raise ValueError('Release exceeds the bundle budget')
        # Bind a sequence to every signed field, not just to the payload hash.
        # Otherwise changed metadata could reuse a sequence while naming the
        # same bundle bytes.
        index['_signed_index_sha256'] = hashlib.sha256(document).hexdigest()
        return index, now

    def _sequence(self, index, checked_at):
        if self.sequence_path.is_symlink():
            raise ValueError('Invalid feed sequence state')
        if self.sequence_path.exists():
            previous = json.loads(self.sequence_path.read_text())
            if (not isinstance(previous, dict) or set(previous) != {'channel', 'sequence', 'index_sha256', 'checked_at'} or
                    previous['channel'] != self.config['channel'] or type(previous['sequence']) is not int or
                    type(previous['checked_at']) is not int or previous['checked_at'] < MIN_TRUSTED_EPOCH or
                    not isinstance(previous['index_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', previous['index_sha256'])):
                raise ValueError('Damaged feed sequence state')
            if checked_at < previous['checked_at']:
                raise ValueError('System clock moved backward since the last trusted feed check')
            if index['sequence'] < previous['sequence'] or (index['sequence'] == previous['sequence'] and index['_signed_index_sha256'] != previous['index_sha256']):
                raise ValueError('Release index replay or sequence equivocation')
        elif (self.store.root / 'feed-sequence-initialized').exists():
            raise ValueError('Feed sequence state is missing')
        marker = self.store.root / 'feed-sequence-initialized'
        if not marker.exists():
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.fsync(fd); os.close(fd); fsync_dir(self.store.root)
        atomic_json(self.sequence_path, dict(channel=index['channel'], sequence=index['sequence'],
                                             index_sha256=index['_signed_index_sha256'], checked_at=checked_at))

    def _policy(self):
        with self.store.locked():
            state = self.store.load()
            if not state['auto_update']:
                raise ValueError('Automatic updates are disabled')
            self.tx.require_source(state, self.boot)
            tx = self.tx.load()
            if state['pending'] or tx and tx['phase'] not in ('complete', 'cancelled', 'failed', 'staged'):
                raise ValueError('An update is already active or requires reconciliation')
            return tx

    def _retire_previous_bundle(self, index):
        """Reclaim only a prior, terminal automatic feed artifact."""
        with self.store.locked():
            state = self.store.load()
            tx = self.tx.load()
            if (not state['auto_update'] or state['pending'] or not tx or
                    tx['phase'] not in ('complete', 'cancelled', 'failed') or
                    tx['bundle_sha256'] == index['sha256']):
                return
            old = self.staging.path(tx['bundle_sha256'])
            if old.exists():
                self.staging.discard(old.name, lambda: self.tx.load() == tx and
                                     self.store.load()['pending'] is None)

    def _clean_interrupted_downloads(self, index):
        """Remove only unreferenced feed files left by a killed transfer.

        A partial is never a transaction artifact: publication happens only
        after the complete digest and bundle signature verify. A published
        digest file is retained if it matches this feed index or any journal.
        Hold persistent state before the staging lease, matching Transaction's
        lock order, and refuse cleanup if any update is armed or unresolved.
        """
        with self.store.locked():
            state = self.store.load()
            tx = self.tx.load()
            if (not state['auto_update'] or state['pending'] or
                    tx and tx['phase'] not in ('complete', 'cancelled', 'failed', 'staged')):
                raise ValueError('Cannot clean interrupted downloads during an active update')
            for path in self.staging.root.iterdir():
                keep_current = path.name == index['sha256'] + '.raucb'
                keep_journal = bool(tx and tx['bundle_sha256'] + '.raucb' == path.name and
                                    tx['phase'] == 'staged')
                orphan_partial = path.name.startswith('.partial-')
                orphan_published = (re.fullmatch(r'[0-9a-f]{64}\.raucb', path.name) and
                                    not keep_current and not keep_journal)
                if orphan_partial or orphan_published:
                    self.staging.discard(path.name, lambda: (
                        self.store.load()['auto_update'] and
                        self.store.load()['pending'] is None and
                        (not self.tx.load() or self.tx.load()['phase'] in
                         ('complete', 'cancelled', 'failed', 'staged'))))

    def run(self):
        """One timer poll. Same-sequence retry may resume only a known staged tx."""
        try:
            self._policy()
            index, checked_at = self.index()
            with self.store.locked():
                self.store.load()  # Invalid/damaged state must never advance sequence.
                self._sequence(index, checked_at)
            tx = self._policy()
            self._clean_interrupted_downloads(index)
            if tx and tx['phase'] == 'staged':
                if tx['bundle_sha256'] != index['sha256'] or tx['release'] != index['release']:
                    raise ValueError('Staged update differs from signed feed; resolve it first')
                self.tx.arm(self.boot, automatic=True)
                result = 'armed-next-boot'
            elif tx and tx['phase'] in ('complete', 'cancelled', 'failed') and tx['bundle_sha256'] == index['sha256']:
                result = 'already-considered'
            else:
                self._retire_previous_bundle(index)
                # Staging enforces full-file bounds, digest, signature and free-space
                # reserve. Transaction repeats policy and identity under its lock.
                deadline = time.monotonic() + FETCH_SECONDS
                url = urljoin(self.config['url'], index['bundle'])
                published = self.staging.path(index['sha256'])
                if published.exists():
                    with self.staging.lease(index['sha256'], self.verify_bundle) as (_, proof):
                        pass  # Interrupted after publication; reauthenticate exact retained file.
                else:
                    with self.fetch(url, index['bytes'], deadline) as stream:
                        _, proof = self.staging.receive(LimitedReader(stream, deadline), index['bytes'],
                                                        index['sha256'], self.verify_bundle)
                if proof['release'] != index['release'] or proof['compatible'] != index['compatible']:
                    raise ValueError('Signed bundle and channel index disagree')
                refreshed = self.now()
                if type(refreshed) is not int or refreshed < checked_at or refreshed >= index['expires']:
                    raise ValueError('Trusted time changed or index expired during download')
                self._policy()  # Recheck after potentially long network transfer.
                self.tx.stage_upload(self.staging, index['sha256'], self.verify_bundle, self.boot, automatic=True)
                self.tx.arm(self.boot, automatic=True)
                result = 'armed-next-boot'
            self._status(result, index)
            return result
        except Exception as error:
            self._status('blocked', reason=str(error)[:240])
            raise

    def _status(self, result, index=None, reason=''):
        # Status is advisory only; the transaction journal and state remain truth.
        atomic_json(self.status_path, dict(format_version=1, result=result, reason=reason,
                                          release=index['release'] if index else None,
                                          sequence=index['sequence'] if index else None,
                                          checked_at=int(time.time())))


def trusted_time():
    marker = Path('/run/systemd/timesync/synchronized')
    if not marker.is_file():
        raise ValueError('Network time has not been synchronized')
    return int(time.time())


def main():
    # Fixed paths. The timer cannot accept a browser-supplied URL or device.
    from sv08_admin import installed_controller
    controller = installed_controller()
    if controller.adapter is None:
        raise ValueError('Reviewed image backend is unavailable')
    config = json.loads(Path('/usr/lib/sv08/feed.json').read_text())
    adapter = controller.adapter
    from sv08_staging import Staging
    staging = Staging('/data/sv08/feed-bundles', max_bytes=adapter.backend.policy['max_bundle_bytes'])
    feed = Feed(controller.store, staging,
                Transaction(controller.store, adapter.backend, adapter.admission),
                controller.boot, adapter.verify, config)
    lock = os.open('/run/sv08/feed.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(feed.run())
    finally:
        os.close(lock)


if __name__ == '__main__':
    main()
