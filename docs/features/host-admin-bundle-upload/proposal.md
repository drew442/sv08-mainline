# Authenticated browser upload of signed OS bundles

Kind: feature. Author: root-upload-design. Date: 2026-09-12.
Requirement: [decision 0010](../../../docs/decisions/0010-host-administration-and-recovery-ui.md).
Depends on the independently reviewed Cockpit shell/authentication integration.

## Problem and intended outcome

Owners currently cannot transfer an OS update through the host page. The image
adapter lists private `.raucb` uploads, but `Staging.receive()` has no browser
transport. Complete choose file → review upload → bounded transfer with progress →
signed-manifest result → separately review image staging. Uploading must never
install, arm, reboot, assert health, or initialize damaged persistent state.
Provide explicit, reviewed removal of unused or interrupted managed uploads so a
failed transfer does not require Linux commands to unblock the next attempt.

`runtime/sv08_staging.py` already bounds file size, reserves space/inodes, enforces
private ownership, authenticates the manifest, publishes atomically and shares an
exclusive lease with installation. `runtime/sv08_bundle.py:inspect` explicitly
returns `full_payload_verified=false`: a valid manifest signature plus a computed
whole-file digest is not full payload verification. Preserve RAUC's installation
verification and that distinction in the user-facing result.

## Scope and primary evidence

Use the already authenticated Cockpit bridge and one fixed installed upload
helper, with a strictly bounded metadata header and binary stdin. No new HTTP
server, caller URL, shell command, executable, raw destination path, systemd
property, or configurable verifier/keyring path. Ordinary users must be rejected
by the real privilege boundary. File names are bounded display text only; managed
storage names come from a complete server-computed SHA-256 digest.

The selected Cockpit `337-1+deb13u2` package supports binary spawn, repeated input,
streamed output and closing stdin. Its `process.input()` returns immediately and
has no drain promise. Send small independent byte chunks, with the next chunk
waiting for a bounded helper acknowledgement; do not load the entire file into
browser memory. Bound streamed JSON output and inactivity/overall transfer time.
Count acknowledged received bytes separately from manifest checking/publication.
Treat bridge loss, truncation, excess bytes, cancellation and timeout honestly.

Primary sources accessed 2026-09-12:

- [Cockpit process API](https://docs.cockpit-project.org/cockpit-guide/main/guide/cockpit-spawn.html).
- Selected archive `cockpit-bridge_337-1+deb13u2_all.deb`, SHA-256
  `8caa8c3f36d6eb2f95561614923518bc6e78d17962673d5be3d43b1967dc4961`,
  `usr/share/cockpit/base1/cockpit.js.gz` and packaged stream channel source;
  provenance is retained by the prerequisite integration.
- Existing staging, bundle admission, image adapter and transaction source in this
  repository, and [staging evidence](../../../docs/hardware/host-admin-ui.md).

Avoid a new browser hashing library just to precompute an expected digest.
Extend staging through a narrow server-computed-digest intake if appropriate,
preserving the existing explicit-digest API and verification/lease behavior.
The browser holds the reviewed File object; completion exposes the actual signed
release/profile metadata and digest. Image staging remains a separate review with
fresh current-state, signature, lease, customization and printer-idle checks.
Upload is storage intake, so do not impose an immutable-mode requirement merely
because image replacement has one. Require the reviewed fixed host policy and
keyring; unavailable identity/policy produces a useful refusal.

## Locking, interruption and cleanup

The old staging docstring requires its caller to hold the state lock throughout
receipt. A multi-minute browser transfer under that lock would block ordinary
administration. Any relaxation must be an explicit, tested contract change:
intake mutates only its private staging directory, retains the exclusive upload
lease throughout receipt/verification/publication, and never reacquires a higher
order lock while holding that lease. Brief admission must coordinate current
transaction/job state; status and job observation remain responsive during a
paused transfer. Preserve ordering between the job ledger, state and upload locks.
In particular, `Jobs.submit` holds the ledger while planning under the state lock;
adding state → ledger acquisition would create an inversion.

Exclude admission against active or ambiguous image work. Demonstrate upload,
image submission and discard races without overlapping mutations, accidental
ambiguous jobs, deadlock, or weakened install reauthentication. A possible order
is ledger → state → upload for brief intake/cleanup admission, followed by upload
lease only during streaming; capability checks must observe busy intake without
waiting. This is a candidate mechanism, not permission to bypass existing guards.

Never overwrite an existing managed file or remove a previous partial implicitly.
Graceful failed receipt may clean only its own unpublished temporary file; process
loss may retain a partial for explicit review. Reconnect shows available managed
uploads and useful interrupted/busy information. It must not replay file transfer
or image staging automatically. If completion acknowledgement is lost, inspect
managed state; do not claim completion from browser bytes sent alone.

Removal reviews the exact managed object and current revision/identity. At apply,
reauthorize under consistent exclusion and refuse active/ambiguous transaction or
job references, changed objects, hard links, symbolic links and nonmanaged paths.
Preserve bundles required for diagnosis/reconciliation. Cleanup is not a ledger
reset or transaction recovery action; ambiguous job resolution remains separately
tracked. Never interpret upload cancellation as cancellation of an OS transaction.

## Acceptance

One offline implementation task, with independent proposal approval and delivery
verification, has these checks:

- `real-upload`: Actual authenticated Cockpit browser selects a fixture file,
  reviews it and transfers it through the fixed installed helper. Show progress,
  authentic signed-manifest output, private publication and read-only listing.
  Test ordinary-user rejection and prove no slot/boot/state mutation during
  upload. Use a real small RAUC signed fixture and fixed test keyring in the
  disposable environment, not a signature callback pretending to authenticate.
- `bounds`: Demonstrate chunk/ack backpressure without whole-file buffering,
  bounded metadata/output/size/time, low-space/inode preflight, short/extra bytes,
  checksum compatibility, untrusted signatures and wrong profile/layout/MCU pins.
  Failed admission must not publish a selectable completed upload. Manifest
  authentication must never be labelled complete payload verification.
- `disconnect-cleanup`: Exercise browser cancellation, disconnect/process death,
  lost completion response and fresh authenticated reconnect. Show retained
  partial/complete state accurately, no automatic retry, separately reviewed
  cleanup and successful subsequent upload. Cancellation of cleanup changes
  nothing; stale/replaced/linked/referenced objects are refused.
- `concurrency`: Pause the real helper mid-transfer; ordinary status, job history
  and unrelated guarded policy operation stay responsive. Race second upload,
  discard and image submission; prove exclusion and absence of lock inversion.
  Confirm stage admission still reauthenticates the leased upload and preserves
  customization, current-state and idle guards. Separate upload from slot writes.
- `integration`: Stage matching helper/runtime/UI with correct ownership and fixed
  paths; missing context/policy/keyring diagnoses refusal. Measure payload delta
  and maximum temporary/persistent storage and browser buffering bounds. Run
  affected staging/bundle/image/jobs/controller/browser tests and JSON/Markdown/
  diff/indexed-gitlink consistency checks. Distinguish real authentication,
  signature tooling, test backend, emulation and hardware evidence.

## Boundaries and subsequent work

No internet download, automatic updater, new signing infrastructure, new owner
account/TLS provisioning, package catalog, network settings, job-resolution API,
physical deployment or recovery write adapter. Use the prerequisite's disposable
real Cockpit fixture; extend it rather than substitute a shim for authentication.
A disconnect need not resume upload bytes automatically; truthful state and safe
explicit recovery are required. Keep user drafts/selection and image-job durability
regressions from the prerequisite intact.

Original code fills ADR 0010's browser-to-private-intake gap using supported
Cockpit/Python APIs. Retire it if upstream supplies equivalent bounded intake,
review, signature policy and lease-preserving cleanup. Existing physical and
release work stays in the [canonical checklist](../../../docs/hardware/host-os-tasks.md#human-and-powered-printer-tasks).
No human action blocks this offline task. After completion, continue the existing
independent recovery image and identity-preserving job-resolution dependencies.
