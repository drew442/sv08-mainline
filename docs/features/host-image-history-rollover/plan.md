# Finite image-job history delivery handoff

Date: 2026-10-03. Coordinator-owned completion of the accompanying plan referenced
by the approved proposal. The immutable decision in record.json governs; this
handoff does not amend scope or replace original approval/history.

## Outcome and checks

Deliver browser-reviewed archival maintenance for a complete settled active batch,
retain every original receipt/disposition and identity, then admit a separately
reviewed new image job. Deliver all seven approved checks: pressure-journey,
identity, concurrency-crash, eligibility, bounds, browser-staging and regression.
Numeric limits are those explicitly approved in record.json, superseding the
proposal's earlier provisional wording: active128, eight full archives, total1152,
64MiB allocated envelope, sixteen batch-sized objects each at most2752512bytes,
1MiB aggregate metadata and64 namespace entries/inodes. No destructive retention.

## Sequence

1. Bounded planner reconciles concrete old-reader/absent-manifest compatibility,
   shared-/data reservation/exclusion and integration ownership. It cannot approve
   changed requirements or implement. Any needed change to approved protocol gets
   bounded independent review before implementation, with original decision kept.
2. One Sol6.1/medium implementer specifies the exact format/publication state
   machine before enabling writes, then implements persistence, admission, browser
   journey, compatibility/export/staging and meaningful evidence/tests together.
3. Coordinator checks full changes, commits and pushes candidates. Fresh separate
   feature_verifier_high reviews the complete source-bound evidence against every
   constraint. Rework remains in the same lineage. Merge only after passing review.
4. Coordinator updates task/goals, main and WIP and verifies remote publication.

## Ownership reconciliation

The original inline owned runtime/UI/staging paths remain. Source inspection
confirms runtime/sv08_admin_upload.py consumes Jobs.load for raw-phase and historical
artifact gates; the implementer must own its narrowly required integration and
associated tests. Generic runtime copying in scripts/integrate_host_os.py and
scripts/recovery_image.py, strict inventory in scripts/stage_admin_ui.py, recovery
export and shared state/staging allocation paths must be traced and covered.
The coordinator will bind the final exact paths and resources in the worker packet
after planner reconciliation. No upstream, signed metadata, boot-health policy,
package dependency, hardware access or archive deletion is implied by ownership.

Coordinator alone owns this plan, record.json, shared goal/human records, Git,
publication and hardware. Workers may read Git, but never mutate Git or publish.
Implementation, planning and evidence-producing sessions cannot verify delivery.

## Resource boundary

The coordinator filesystem currently has about344MiB free. Do not compose full
images or make unbudgeted copies. Use bounded isolated file/browser fixtures and
explicit per-worker scratch; preserved prior artifacts are not cleanup targets.
Physical-power-loss, actual authenticated installed-service and factory-image-fit
claims must remain at their supported evidence levels. Offline fixtures cannot
establish a release or printer result. Printer remains on the completed H12 boot.

## Reconciliation approved — 2026-10-03

Independent approver session `01a1008d-187a-7ab0-9015-2c8563f956d2` approved the
technical fence amendment with thirteen explicit constraints. Coordinator verified
actual GPT-6.1 Sol/medium and full role loading. The prior approval is preserved;
record.json carries the current decision. All seven checks and numeric bounds
remain. The exact paired-lock exception, old public entrypoint boundary, admitted
legacy waiters and relationship-preserving export/readback are explicitly reviewed.

One implementer owns the original runtime/UI/staging paths plus narrowly necessary
sv08_admin_upload.py, sv08_state.py, sv08_staging.py, sv08_export.py and new
sv08_admin_history.py/sv08_data_budget.py. Assembly scripts may change only for
necessary matching-runtime or preservation integration. Associated existing tests,
focused new history/budget tests, browser fixtures, storage-format.md and execution.md
are assigned in the durable worker packet. Proposal, record, this plan, shared
goals and publication remain coordinator-owned. No signed-policy or boot-health
change is authorized. The accepted decision governs if earlier draft prose differs.
