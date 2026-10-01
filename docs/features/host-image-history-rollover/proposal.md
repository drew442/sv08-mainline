# host-image-history-rollover: admit another reviewed image job without forgetting old identities

Kind: feature. Author: project_planner (required-history-rollover-plan-20261001). Date: 2026-10-01.
Coordinator imported draft for independent bounded approval; no implementation. Baseline fd2639a0b21affbc4e7d1a04d69ba207e3e88ef7.

## Problem and evidence

Owner ADR 0010 requires ordinary browser administration and image history surviving disconnects. docs/features/README.md and the host-image-job-resolution proposal/record explicitly retain finite history rollover as separate required work. Jobs LIMIT=128 and active jobs.json are the only authoritative history. Existing full-capacity tests show a newly reviewed cancellation cannot receive an identity even after the unknown receipt is explicitly retained. Old retries are correctly preserved; no archival maintenance exists. Source reading established this baseline; this planner ran no reproduction.

## Intended outcome

Review/apply history maintenance in the browser when all 128 active receipts are settled, preserve their complete immutable receipts authoritatively, reconnect and separately review another image operation. Every retained old identity remains available for identical retries; changed requests refuse and unknown outcomes stay unknown. Total storage and admissions remain finite. Complete accepted resolution remains done; this proposal neither reapproves nor replaces it.

## Scope and alternatives

Add a bounded committed archive/current-ledger format, legacy migration, deterministic crash protocol, authoritative cross-history lookup, and explicit maintenance review/apply/UI capacity reporting. Only terminal or already explicitly disposed unknown receipts can roll over. Keep active limit 128. Evaluate eight archive batches plus active (1,152 total) as the resolution proposal's illustrative candidate, **not an approved number**. Adopt only after measured encoded/allocated/temporary/inode/shared-data bounds and independent feature approval. Reuse original receipt/evidence limits; full batches alone would need 23.625 MiB retained and, conservatively, another 5.25 MiB for two batch-sized temporaries before metadata. Actual metadata and overall reserve remain to be bounded/measured.

No deletion/TTL/LRU, expiry/generation retirement of identities, rejection-only evidence compaction, export-then-delete, unlimited admissions, silent extra cancellation capacity, replay, outcome inference, transaction reconciliation, slot mutation, reboot, scheduler or new daemon. At total capacity refuse new identities while retries/observation stay usable. Original jobs approval allows capacity refusal; this bounded follow-on creates a useful reviewed finite extension without changing lifetime retention promises. An owner decision is needed only for expanded retention/destruction semantics, not this finite-preserving engineering proposal.

Use existing Python publication/fsync, systemd worker and Cockpit helper. New custom code fills project retry-retention integration absent from RAUC; retire it if supported upstream/project facilities supply equivalent behavior. No upstream or package dependency change. Raising LIMIT alone, hiding the capacity message or deleting receipts is not the proposed required outcome; no change retains the gap.

## Acceptance and task split

One production implementation task, after separate bounded approval, with persistence step preceding API/UI/staging step. Exact owned paths and review roles are in accompanying plan.md. Implementer Sol 6.1/medium; fresh independent feature_verifier_high Sol 6.1/high for multi-file commit/identity-loss risks. Planner, approver, author and integration producer cannot verify the delivery. Coordinator alone writes records and commits.

Stable proposed checks:

- pressure-journey: full-128 refusal before; explicit maintenance then reconnect and separately reviewed cancellation once afterward, with original unknown and all historical identities preserved.
- identity: full-plan deduplication before capacity across all batches, changed-plan refusal, disposition acknowledgement retry, late worker refusal, missing/corrupt/duplicate/unsafe-file/schema rejection and safe legacy migration.
- concurrency-crash: deterministic process contention and failure at every write/fsync/rename/commit/lost-ack boundary yields old/new complete view or refusal; never identity loss/replay; bounded orphan handling.
- eligibility: unresolved work blocks maintenance; full observation/disposition remain usable; archived unknown never becomes success/refusal.
- bounds: independently approved numeric count/byte budget, blocks/inodes/peak temporary/shared-data reserve/installed-byte measurements; no-space refuses without deleting receipts or artifacts; final ceiling keeps historical retries usable.
- browser-staging: real maintenance review/apply/cancel/reconnect and pending-local-ID retrieval, truthful capacity display, responsive reads during transaction lock, unchanged drafts, strict privileged RPC and matching runtime/UI wiring. Clearly label actual authenticated-helper versus shim evidence.
- regression: affected jobs/resolution/admin/transaction/staging tests and source/diff/JSON/Markdown/gitlink consistency; preserve unchanged service evidence at original revisions.

Reuse accepted jobs/resolution approvals for existing invariants and historical passed service/browser evidence, but their constraints explicitly excluded rollover and do not approve this new archive format or ceiling. If numeric/protocol scope changes after approval, amend the bounded review; do not refresh hashes or rewrite historical results.

## Human dependencies

None for required offline implementation/fixtures. No credentials, hardware, private backups or archived QEMU artifact needed. G1 reset/SD return and later physical host/recovery/UI checks remain coordinator-owned in existing human queues. No hardware/release authority follows. Optional features remain paused; this is one required delivery proposal, not a new backlog.

## Concrete proposed storage and commit contract

Active receipt limit stays 128; retain at most eight immutable full archive batches,
with a total ceiling of 1,152 identities. Refuse new identities at that total
ceiling; identical retries and observation remain usable. No eviction is permitted.
The proposed history envelope is 64 MiB allocated storage, with at most sixteen
batch-sized durable/temporary objects, each retaining the existing 2,752,512-byte
ceiling, and at most 1 MiB of aggregate pointer/lock/directory metadata. Bound
namespace entries/inodes to 64. These are explicit engineering proposal numbers,
subject to independent approval and actual implementation measurements.

Coordinator feasibility at fd2639a produced a valid complete 128-row disposed
unknown batch of 2,546,691 encoded bytes using actual Jobs.save/load. Synthetic
objects at the accepted batch read ceiling (16 files) plus a 1 MiB metadata
allowance allocated 45,088,768 bytes on coordinator ext4; 22,020,096 bytes remain
inside 64 MiB. This is conservative filesystem feasibility, not a committed
archive protocol, shared-data admission proof or full factory-image fit. The
private recipe/result are in local/feature-workflow/probes/history-capacity-20261001.

Publish a strict versioned manifest at the existing jobs.json path, so prior
list-only readers refuse the new format. It binds one active immutable snapshot
and up to eight complete immutable archive snapshots by safe relative filename,
content hash, byte length and count. Validate the entire committed view, receipt
schemas, ownership/modes/link counts, global ID uniqueness and all count/byte
bounds before using any lookup. Missing/corrupt referenced objects refuse; a
missing manifest with existing history objects must never mean empty fresh history.
Legacy valid list-only history remains readable until explicit migration. The
manifest is the sole commit point: durable objects first, then atomic manifest
publication and directory fsync. Mutations use existing lock order and preserve
the old or new complete view on failure. Bound/reclaim only demonstrably uncommitted
owned objects under exclusion; never remove committed receipts or guess recovery
from corrupt state. Migration and subsequent active saves follow the same protocol.

Rollover is explicit browser review/apply, bound to the complete committed history
revision and eligible identities, not polling or submission side effects. Only
terminal or explicitly disposed unknown active receipts are eligible. Observe
configured shared-data free-space/inode reserve before allocating publication
objects; do not count the existing reserve as available archive budget. No image
controller/RAUC/state reconciliation, slot operation or reboot occurs as maintenance.
Keep duplicate-before-capacity precedence, late-worker refusal and disposition
retry behavior across the entire retained view. Workers can only run active work.
Installed staging and existing preservation/export paths must include all new
history objects; stale assembly/update/downgrade readers must refuse incompatible
format. No old receipt/evidence is rewritten as successful.

Coordinator owns proposal/record/decision/checklist updates; implementer owns
runtime/sv08_admin_jobs.py, runtime/sv08_admin_resolution.py, runtime/sv08_admin.py,
ui/host/app.js, ui/host/index.html, scripts/stage_admin_ui.py, associated existing
admin/jobs/resolution/staging tests and browser fixtures, new focused history
tests/browser case and one dated evidence document. Expand that ownership only
after tracing a required integration path and coordinator reconciliation. One
production implementation; Sol/medium, followed by fresh Sol/high delivery review.
