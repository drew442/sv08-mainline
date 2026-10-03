# H12 attended SD delivery plan — 2026-10-03

The owner requested active goals to complete H12 under the
[ten-point decision](../decisions/20261002-h12-scope-reduction.md), using subagents.
The [current goals](../../.codex/current-goals.md) define completion; the single
[implementation record](../features/h12-attended-sd-reimage/proposal.md) supplies
owned paths and checks. This replaces the old H12 physical dependency chain.

## Three outcomes

1. **Deliver SD maintenance:** reuse the independent SD composer, its pinned
   loader/kernel/root and GTK closure. Add one small SD-only backend/screen with
   integrated target/image checks and explicit Yes/No, then bounded write/flush/
   complete readback. Test refusal/No, success, transfer/readback failure and
   relaunch; exercise the actual installed ARM64 composition on disposable storage.
   Obtain fresh independent software delivery verification.
2. **Prepare the attended session:** identify the accepted actual tool/image and
   current spare, establish independent SD/source access and operator attendance,
   and obtain exact hardware review. Request physical facts only after the
   concrete operation is ready. Existing October 2 observations are historical.
3. **Complete the real outcome:** operator confirms Yes; actual full write/flush/
   image-range readback passes; operator manually restarts; observe normal boot
   from the installed image. H12 remains incomplete until this outcome passes.

No separate rehearsal or extra trial boot is introduced. SD is sufficient
recovery. Do not retire old tokens, fix RTC or operate old claim services merely
to satisfy withdrawn requirements. RAM maintenance, anti-forgery/replay,
randomness/permission expiry and complete cold capture are abandoned; automatic
launch/return are deferred. Factory storage is left as found, not an extra gate.

## Source-backed bounded choice

Planner tracing found that `scripts/build_sd_recovery_host.py` already composes
independent SD/GTK/SSH userspace. Its existing recovery provider exposes export
only; enabling the existing Restore button would not implement whole-disk reimage.
The old C writer is coupled to abandoned RAM/claim machinery. Reuse the installed
GTK patterns and Python standard-library/Linux primitives in a small dedicated
SD path; do not retrofit another mode into the old writer or alter host A/B update
controllers. Ordinary owners retain the accepted native recovery interface.

The backend/UI/composer and focused unit, GTK and installed-fixture paths are
listed exactly in the implementation proposal. A fixed coordinator-prepared
independent read-only source file avoids new upload/discovery/server work. Reuse
existing NFS transport if its installed tools are present; a fitting independent
SD/USB file is the bounded alternative. This closure is to be checked, not assumed.
New runtime bytes must invalidate the compressed usr cache. UI wording must say
whole-image replacement and cannot promise preservation of data inside that image.

## Delegation and current progress

- Planning completed in separate `project_planner` session
  `01a0ff48-6bd1-7942-9b68-1276d0cb13b8`. Actual GPT-6.1 Sol/medium,
  full-access/never and complete role instructions were verified from runtime
  metadata. It performed source reading only, zero experiments and no hardware
  access or tracked-file edits.
- Native launch failed with “agent thread limit reached”; the documented separate
  full-role session fallback is used. Private packets/runtime/results are under
  `local/feature-workflow/probes/h12-sd-goal-reset-20261003/`.
- Independent feature approver session `01a0ff4e-0995-7383-9a2a-5dcd87c53d07`
  approved the bounded implementation with four acceptance constraints. Actual
  GPT-6.1 Sol/medium and full role/runtime settings were verified. The constraints
  cover transfer-time source integrity, native/installed confirmation, composition
  cache/resource bounds and honest whole-image replacement/failure messaging.
  This does not reopen the owner’s settled product choices. The planner suggested
  no repeated approval; the coordinator uses the existing workflow’s independent
  bounded implementation review and one replacement record to ensure dispatch.
- Use one `project_implementer` at Sol/medium for device/source
  binding and composition. No parallel production implementation. Use direct
  prescribed checks first; a bounded integration agent is available for a concrete
  installed-environment issue. A fresh independent delivery verifier must not be
  the planner, author or evidence-producing session.
- Coordinator alone imports results, maintains records, commits/pushes and
  operates hardware. Exact physical reviews remain separate from software review.

The old pending `physical-read-only`/`physical-reimage` RAM-handoff tasks and
expired-preflight return guard are recorded as blocked with explicit supersession
reasons because the dispatcher schema has no cancelled state. They must not be
resumed as prerequisites. Completed evidence and old reviews are preserved.
The replacement record has priority 1; unrelated history-rollover work is lower
priority and must not displace ready H12 work.

## Evidence boundary

This goal reset is planning/dispatch preparation, not delivered software or a
physical success. Last measured SD boot/SSH was October 2; no current printer
access, media mutation, image write, new boot or attendance has been performed or
assumed in this reset. Full-image authorization is reconciled against the exact
prepared action before execution, without asking again for settled scope choices.

## Active implementation assignment

The approved task is claimed as `h12-attended-sd-reimage:implement`, run
`f05281148f074ef5a85f8a6ba15f9d83`, coordinator session
`h12-sd-implement-20261003`. One project_implementer is active on
`feature/h12-attended-sd-reimage` at baseline `5834dd4`, with only proposal-owned
files assigned. Separate-session runtime 01a0ff51-a356-73a0-b226-7babab5c5721 confirms
GPT-6.1 Sol/medium, full-access/never and the complete role contract. Primary
assignment is 20 minutes of implementation/focused checks with 128 MiB scratch;
full SD/QEMU artifacts are excluded from the space-limited local checkout and
need a separately budgeted coordinator/integration run. No hardware/network
access, shared-record edits, commits, pushes or additional agents are delegated.
Installed ARM64 evidence and independent verification remain required before
software completion; physical preparation and acceptance follow afterward.

## Implementation handoff and installed execution

The implementation session completed its bounded assignment. Coordinator inspected
all ten changed paths and committed/pushed candidate `dd080df` on
`feature/h12-attended-sd-reimage`. No unowned files changed. Worker evidence:
11 backend unit tests, seven composer tests and eight native GTK fixture journeys
passed. These are offline results; delivery verification remains pending.

Coordinator staged the exact committed source on Beelink in
`/home/drew/sv08-h12-sd-delivery-20261003/candidate-dd080df`. Preserved source
recovery root and public package inputs were freshly hashed. Existing build tools
and about 26 GiB free were observed. A fresh test-key composition is assigned a
600-second build limit and existing 3,500 MiB allocation cap; installed QEMU
execution uses a separate disposable disk and 768 MiB RAM. No old compressed usr
cache is reused. The worker's installed driver is inspected but not yet passed.

A coordinator read-only observation also found the existing physical SD host still
on its October 2 boot, kernel 6.18.51-sv08-candidate1, with SD root read-only and
display service active. Kernel NFS modules and modprobe are available, but
mount.nfs is absent. No module was loaded, source mounted, media written or restart
performed. Current physical setup/attendance remains unconfirmed. Source transport
closure will be resolved before the concrete physical session; this is not an
extra rehearsal milestone. Local detailed evidence is kept under
`local/feature-workflow/probes/h12-sd-delivery-20261003/integration/`.

### Fresh composition and first installed run

Fresh fixture composition of `dd080df` passed in 59.4 seconds. Root SHA-256 is
`024389440bc3ac7176bc121cac0bbbe9d6d529da07285842e9f5e55f1ecba848`;
peak additional allocated build bytes were 1,326,407,680. This is explicitly a
fixture-key image, not the owner-only physical medium.

The first VM run reached the verified envelope, SSH, installed production
service/hash checks and independent read-only ext4 source mount. It then failed
when the shared SSH helper's 20-second timeout expired during systemd reload.
The driver terminated its own QEMU process; this is a terminal failed run, not a
live process to restart. Coordinator also found that the fixture drop-in sorted
before the production reimage drop-in. The same implementer session received a
bounded eight-minute test-driver repair assignment; production behavior and
acceptance checks are unchanged. The corrected installed run is still required.

The source transport limitation is resolved on the existing physical SD host.
Coordinator used existing `mount -i` and kernel NFS support. An initial NFSv4
attempt refused; server inspection showed NFSv3 enabled and v4 disabled. Explicit
numeric NFSv3/TCP options mounted `/srv/sv08-sd-nfs` read-only at
`/run/h12-source`; the image file is visible with 7,818,182,656 bytes. No packages
or server configuration changed. This created a volatile mountpoint and loaded
NFS modules; no SD/eMMC media write or restart occurred. The server-side image
was freshly hashed as
`ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`.
Full client-side checking remains part of integrated Review before confirmation.
The pre-existing hostname-resolution warning did not prevent these numeric-address
operations; DNS repair is not an H12 prerequisite.
