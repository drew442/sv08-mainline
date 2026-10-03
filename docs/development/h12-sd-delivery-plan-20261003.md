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
