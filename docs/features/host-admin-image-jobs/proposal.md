# Image operations survive browser disconnection

Kind: feature. Author: `host_next_task`. Date: 2026-09-12.
Requirement: [decision 0010](../../decisions/0010-host-administration-and-recovery-ui.md).

## Problem and evidence

At `8eba1749d792c1f37bd3ee1bbe891899f80f10dd`, `ui/host/app.js` invokes a fresh
Cockpit process for each request and awaits the full synchronous apply response.
Its busy state exists only in browser memory. `runtime/sv08_admin.py` exposes
status/plan/apply; `runtime/sv08_admin_images.py` performs stage/arm/cancel directly
through the transaction layer. There is no durable browser-operation identity,
reconnectable history or separately supervised image worker. Actual Cockpit
disconnect behavior has not yet been measured.

The accepted UI requirement explicitly calls for jobs surviving disconnection.
`tests/test_admin_images.py` already provides a small real controller, private
staging and transaction fixture. Completing this existing journey has priority
over new health criteria or speculative services. No ready delivery is displaced.

## Intended outcome and scope

An administrator reviews an uploaded image operation, confirms once and receives
a durable job identifier. Host supervision runs the work independently of the
browser; refresh/reconnection shows its current phase and result without repeating
the mutation. Demonstrate stage → reconnect → inspect outcome → separately review
arm → inspect outcome → separately review cancel. Selection remains next-boot only.

- Private, bounded persistent records for `image.stage`, `image.arm` and
  `image.cancel`, with deduplicated retries and one admitted image operation.
- Fixed supervised worker invocation through existing systemd; no new network
  daemon, task platform or runtime package dependency.
- Fresh capability, state revision, boot identity and idle checks at execution,
  preserving signature reauthentication, upload leases and transaction ordering.
- Read-only job status/history through the privileged Cockpit helper, with queued,
  running, terminal and interrupted outcomes visible after reload.
- Truthful launch/worker failure handling. Never replay a mutation automatically
  when its outcome is uncertain. The transaction journal remains authoritative
  for OS slot state; a job record cannot assert health or invent rollback.
- Matching runtime/service staging and non-deployable-image refusal. Record the
  actual added payload; the complete image capacity gate stays open.

Reuse `Controller`, `HostImages`, `Transaction`, upload and idle admission. A
request cannot supply an executable, shell command, raw path or systemd property.
Use a fixed service/template or equivalently fixed systemd invocation rather than
backgrounding a browser-owned process. Job status must remain observable while
an image transaction holds the state lock. History must be bounded without
evicting active/ambiguous work or silently weakening retry deduplication.

Likely files: administration/image runtime, new job runtime and worker unit,
host UI, runtime/UI staging, preview bridge and browser/process tests. The
coordinator owns queue bookkeeping; the implementer uses an isolated worktree.

Browser upload transport, owner onboarding, network activation, package jobs,
automatic scheduling, reboot, health promotion and physical deployment are outside
this task. Use existing fixture uploads to complete the image-job journey. Upload
transport is the next dependent feature, not a reason to stop this implementation.

## Acceptance

One offline task, `implement`, has these required checks:

1. **disconnect**: Actual browser confirms staging to a real separate worker using
   the existing disposable controller/staging/transaction fixture. Close/reopen
   while a deterministic barrier holds execution; release it and observe the same
   job completing with one installation. Arm and cancel require separate reviews.
2. **submission**: Duplicate submission/lost acknowledgement returns the same job;
   reused identity with different content rejects. Concurrent operations cannot
   bypass exclusion. Cancelling review submits nothing.
3. **admission**: Stale state, changed boot, customized/writable images,
   non-deployable manifests and idle failure refuse before backend mutation.
   Existing signature/lease checks remain in the actual execution path.
4. **interruption**: Inject launch failure, worker exit and interruption around
   record publication and mutation/result recording. Uncertain outcomes remain
   interrupted/reconciliation-required, never success or automatic retry.
   Corrupt records and no-space failures refuse safely.
5. **staging**: Check fixed production worker wiring in isolation, service-unit
   validity, runtime consistency, absent-input diagnostics, bounded history and
   measured payload delta. A synchronous callback double alone is insufficient.
6. **regression**: Relevant administration, image, staging, transaction and
   admission tests pass, together with JSON/Markdown/diff/gitlink consistency.

Use small directory fixtures and the existing browser executable. Distinguish a
real worker process, real service supervision, a test bridge and actual Cockpit
authentication. Full authenticated login/ARM64 image and physical tests remain
separate where unavailable; do not imply those passed from a browser shim.

## Dependencies, human work and retirement

Existing image adapters and signed private staging are implemented. No new owner
decision or hardware access is needed for this offline task. Keep reviewed-image
boot, physical interaction and power-interruption acceptance in the
[canonical checklist](../../hardware/host-os-tasks.md#human-and-powered-printer-tasks).
The online bring-up image provides no authority to activate these image operations.

Original coordination fills decision 0010's disconnect/durability gap around
supported systemd and Cockpit facilities. Retire it if upstream supplies equivalent
review binding, admission, persistent history and reconnect behavior; retain the
preservation and crash regressions.

After completion, proceed to bounded authenticated upload, then Cockpit package
closure/identity integration, and explicit boot reconciliation/health wiring.
