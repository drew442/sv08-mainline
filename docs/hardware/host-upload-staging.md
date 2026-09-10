# Private bundle upload staging

2026-09-10, offline implementation and native tests. No network endpoint, printer
connection, image installation or activation was performed by this component.

[The staging library](../../runtime/sv08_staging.py) accepts a bounded byte stream,
a declared length and SHA-256, and a required signed-verification callback. The
production caller must use `sv08_bundle.inspect` with its reviewed policy/keyring.
It creates a private partial file, checks exact length and digest, fsyncs it,
makes it owner-read-only, authenticates it, then atomically publishes it under its
content digest. A lease reauthenticates the published file and holds the staging
lock throughout the caller's installation operation.

The directory must already exist with mode 0700 and coordinator ownership; every
ancestor must be a real directory owned by root/the coordinator and unwritable
by other users. Lock/bundle symlinks, hard links, unexpected owners and writable
published bundles are rejected. Production ownership defaults to root; the
alternate owner argument exists for unprivileged tests, not service configuration.

One upload is retained at a time. The default limit is 1 GiB, with an additional
768 MiB reserved for the late state copy and operating margin, plus an inode
margin. Errors remove only the partial file created by that invocation. An
interrupted process leaves its partial file for explicit reconciliation. Cleanup
accepts only managed filenames and requires a positive transaction-clearance
callback under the staging lock; it never removes the lock inode.

The future coordinator must hold the state lock before the staging lease, impose
stream deadlines, authenticate/authorize the uploader, check automatic-update
opt-out and customization policy, and exclude live transactions before cleanup.
These functions do not implement those policies or promise filesystem quotas.
Signature inspection authenticates inline metadata; RAUC installation still has
to verify the verity payload and the backend must recheck installed hashes.

## Evidence

[Eight unit tests](../../tests/test_staging.py) cover publication/lease exclusion,
truncation/extra bytes/checksum mismatch, signature refusal, capacity refusal
before reading, stale-upload preservation, substitution attempts and explicit
cleanup clearance. The full offline suite passed 102 tests.

`build/staging-intake-test.py` additionally streamed the real 598,521,825-byte
metadata test bundle through the root-owned staging directory, authenticated it
with native RAUC 1.15.2, reauthenticated under a lease, then explicitly discarded
it. Temporary storage was removed afterward. The public
[result](host-upload-staging-20260910.json) records the bundle/source hashes and
the limits of that test. This used the existing offline-only certificate, never a
production release key. The library fills intake/ownership checks around RAUC;
retire it if upstream supplies an equivalent supported intake path. See
[decision 0006](../decisions/0006-host-state-integration.md).
