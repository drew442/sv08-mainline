# Durable browser image operations

2026-09-12. Offline implementation for [decision 0010](../decisions/0010-host-administration-and-recovery-ui.md),
reviewed under the [bounded proposal](../features/host-admin-image-jobs/proposal.md).
No printer writes, network activation, authenticated Cockpit login or physical
acceptance are established by this work.

## Owner workflow

Review staging and confirm once. The page displays the durable receipt identifier,
queued/running phase and eventual result. Closing the page leaves the independently
supervised worker running. Reopen any host page to inspect the same receipt. Arm
and cancel each require their own fresh review; neither restarts the printer.
A cancelled review submits nothing. The browser keeps an unacknowledged submission
locally and offers an explicit check using the original identity; refresh never
submits or replays it. Successful receipt discovery removes that local reminder.

The existing private fixture upload is used here. Authenticated browser upload is
a separate dependent delivery. Unavailable/non-deployable image adapters remain
unavailable. Cancellation still uses the existing safe-source capability, including
when customization prevents replacement; it does not impose an immutable-only
check before cancellation.

## Fixed worker and durability

Cockpit's privileged helper admits only `image.stage`, `image.arm` and
`image.cancel`. `image.submit` binds a validated 32-character hexadecimal retry
identity to every field of the reviewed operation. Duplicate requests return the
same receipt, including after completion; changed content rejects. The direct RPC
`apply` route cannot bypass jobs when the host worker is configured.

The fixed systemd template
[`sv08-admin-image-worker@.service`](../../configs/host-os/sv08-admin-image-worker@.service)
executes `/usr/bin/python3 /usr/lib/sv08/sv08_admin_jobs.py %i`. Only the validated
receipt identity substitutes for `%i`. Requests cannot supply executable paths,
commands, properties, environment or target devices. The worker reconstructs the
root-only installed context and boot identity and claims only its matching queued
receipt. It does not restart automatically and is not enabled at boot.

A private `/data/sv08/admin-image-jobs/jobs.json` retains at most 128 receipts;
new identities refuse at capacity. No history is evicted, so an old retry cannot
become a new mutation. Records are bounded to 512 KiB, with one replacement
publication temporarily requiring another ledger-sized file. Locks and records
are owner-only. Corruption, unexpected ledger/lock types or permissions, and no-space errors
refuse; there is no automatic repair or truncation. History never edits the ledger.

Admission publishes and fsyncs the queued receipt before requesting systemd start.
The worker publishes running before invoking the controller. It repeats current
review/capability/boot checks, then the existing `HostImages`/`Transaction` path
rechecks revision and capability under the state lock, authenticates the private
upload lease, and obtains idle admission before backend writes. Successful jobs
mean the existing adapter returned and the result was durably published; they do
not assert boot health, a completed rollback, printing or release readiness.

Ledger locks are short and distinct from the execution and transaction locks.
The page reads and renders jobs before ordinary status. Ordinary status now uses
a nonblocking state lock and reports busy, avoiding the race where a transaction
starts after the jobs read. Job polling never needs the transaction lock.

## Interrupted or full history

An unclaimed queue expires after 30 seconds of the same boot's monotonic clock.
Reads then display interrupted; a late worker refuses it. This bounds the case
where the helper dies before launching, systemd acknowledges a start that cannot
execute, or installed context is missing. Boot changes also make unresolved work
interrupted. A running receipt whose execution lock is no longer held is displayed
as interrupted. Failed launch acknowledgement is conservative even if systemd may
have accepted the start. Backend exceptions, worker death, or failure to durably
publish the result never automatically repeat an operation.

Unresolved work blocks all new image jobs. The transaction journal remains the
source of slot state; receipt observation never repairs it or declares success.
Preserve the receipt, `update.json`, `state.json`, current boot identity and matching
unit status/journal before any recovery. Confirm the matching unit has stopped, no execution lock is held, and the RAUC
D-Bus service reports no installation still in progress. An exited RAUC CLI or
inactive worker cgroup alone does not establish service-side inactivity. Use
read-only journal, boot and backend observations against the independently
identified backend and preserved source. Do not call `Transaction.reconcile` as
a read-only check: it can promote arming to armed and obtains admission. Do not infer
an installation from the receipt, delete the ledger, reset an identity, automatically
retry staging, or declare a trial healthy. Physical actions retain the existing
[hardware requirements](host-os-tasks.md#human-and-powered-printer-tasks).

There is currently no browser receipt-resolution or history-rollover action.
A bounded follow-on for ambiguous receipts and capacity rollover must retain original identities and uncertain outcomes, bind
resolution to the captured journal/boot/unit evidence, and separately review any
subsequent cancellation or recovery action. Until that path is delivered and
reviewed, ambiguous or full ledgers remain closed to new job admission. This
limitation does not change the independent recovery interface or grant hardware
authority.

## Offline reproduction and evidence boundaries

Selected ARM64 installed-entry diagnostics can be repeated with:

```sh
sudo unshare --mount --propagation private python3 tests/admin_jobs_installed.py --lower SELECTED_BASELINE_ROOTFS --work build/image-jobs-installed-new
```

This uses a small disposable overlay, checks absent/malformed/recovery context,
missing boot and invalid receipt diagnostics, and unmounts it afterward.

Run the Python administration/staging/transaction/admission regressions and
`systemd-analyze verify configs/host-os/sv08-admin-image-worker@.service`.
The real browser fixture uses a disposable backend and signature verifier with
real Controller, HostImages, private Staging and Transaction. Its user systemd
service runs a separate Python process; its install barrier holds the real state
lock while the browser target is closed and recreated.

```sh
python3 scripts/preview_admin_ui.py --work build/image-jobs-new --image-jobs-fixture --execute
node tests/admin_jobs_browser.mjs CHROMIUM_BINARY build/image-jobs-new build/image-jobs-browser-new
```

Use the selected Node 22 and existing Chromium binary. The preview is loopback-only
and uses a marked Cockpit bridge shim, not authenticated Cockpit. The fixture
creates a private `.sv08-browser-upload-*` directory under the invoking user's home
because real staging rejects writable ancestry; its path is recorded in the
fixture's `upload-path.json`. Stop the preview and remove that exact disposable
upload directory after testing. Never stage either fixture script into a host.
Browser screenshots, profiles and raw logs remain ignored under `build/`.

The public [evidence record](host-admin-image-jobs-20260912.json) records commands,
results, payload measurements and source hashes. Unit syntax validation, a real
user-service fixture, and selected ARM64 installed-entry diagnostics are separate
claims. The complete factory 8 GB fit gate, authenticated production session,
assembled ARM64 host image, real board backend/idle behavior and physical
power/disconnect tests remain open in the canonical host checklist.

Original code fills ADR 0010's project-specific review/durability gap using Python,
systemd and Cockpit supported interfaces without new runtime dependencies or
upstream changes. Retire it if upstream provides equivalent persistence, review
binding, admission and reconnect semantics; retain the crash and retry regressions.

## Independent review correction: preserve unfinished edits

Independent browser verification rejected candidate
`7afb16911aadcbbbb98a2986df3c79c08f7fd925`: the 1.5-second status poll rebuilt
editable controls. A hostname draft `owner-draft`, writable-mode selection and
unchecked automatic-update policy reverted within two seconds to the host's empty
hostname, immutable mode and enabled policy. The earlier fast-click browser test
did not expose that loss. The [original evidence](host-admin-image-jobs-20260912.json)
remains historical evidence for that rejected candidate, not acceptance of its UI.

The correction keeps each unfinished control separate from current server status.
Polling updates capability/revision information and untouched controls while
preserving local edits, including when another session changes the host. Cancelled
or failed reviews keep drafts. A successful apply clears only its own unchanged
draft; edits made while the response is pending and drafts in other controls stay.
Every new review still uses the backend's current state revision.

Image and package selections survive polls when their identifiers remain offered.
If a selection disappears, the page shows an explicit unavailable-selection
placeholder and disables the corresponding action until the user chooses again.
Later polls do not silently select a different item. Unchanged option lists retain
their existing DOM nodes so polling does not disturb native keyboard interaction.

[Correction evidence](host-admin-image-jobs-drafts-20260912.json) preserves the
failed before/after observation and records the new real-browser dwell regression,
external-state changes, stale/cancelled reviews, delayed apply acknowledgement and
selection removal/reselection checks. Reproduce with a fresh ordinary preview:

```sh
python3 scripts/preview_admin_ui.py --work build/image-drafts-new --execute
node tests/admin_drafts_browser.mjs CHROMIUM_BINARY build/image-drafts-new build/image-drafts-browser-new
```

The browser test uses the actual disposable controller for policy/name writes.
Its image/package lists are explicitly test-only status projections; it does not
simulate successful image/package mutation. Unchanged worker, ARM64 diagnostic and
transaction evidence is inherited from the original candidate with matching
runtime hashes; it was not rerun or upgraded into production acceptance by this
UI correction.
