# Current delivery goals

Reset: 2026-10-03, at the owner’s request. Active goal: **complete H12 using
attended SD maintenance**. The owner returned and confirmed current setup/attendance at 03:19 UTC.
Physical execution has resumed; exact operation review passed with conditions.
Prior goal/checkpoint text is preserved in
[the history through October 2](goals-history-through-20261002.md).

The [owner’s ten-point scope](../docs/decisions/20261002-h12-scope-reduction.md)
is authoritative. All commits are pushed to GitHub under standing authorization.

## H12 goals and completion evidence

| Goal | State | Deliverable and completion evidence |
| --- | --- | --- |
| H12-1 — Deliver the minimal SD flashing tool | Complete: installed ARM64 journey passed, independently verified, merged and pushed | Run from independent SD. Select image and installed eMMC, check identity/capacity/source separation/target not in use/image checksum, display image and target, ask yes/no, then write/flush/full readback. No/EOF performs no write. Focused offline tests and independent delivery verification pass. |
| H12-2 — Prepare the real SD maintenance session | In progress: source/target/tool/display preparation complete; current setup/attendance confirmed; exact action review passed; KVM repaired; keyboard correction and fresh action review passed; coordinator delegated to operate confirmation | Identify the concrete accepted tool/image and current printer storage; make them available to the SD host. Confirm the SD recovery path, actual physical setup and operator attendance. Exact hardware-operation review is complete. Source/image/target readiness is established without a separate rehearsal milestone. |
| H12-3 — Complete one attended reimage and normal boot | In progress: preparing autonomous KVM confirmation, physical write still pending | Write the identified installed eMMC from SD, flush and verify the complete image range, report the outcome, and have the operator restart manually. Observe the installed system’s normal boot. Retain actual evidence and limitations. |

H12 is complete only after all three outcomes pass. Offline acceptance is not a
physical write or boot result. Historical October 2 SD SSH/clock results are not
fresh physical admission for a later operation. SD recovery is sufficient.
Current setup/attendance is requested only when the concrete operation is ready;
answered scope choices do not require repeated approval. Existing hardware
permission remains scoped to its authorized actions; the exact full-image write
must be reconciled against that authority before execution.

## Explicit exclusions

- Abandon RAM maintenance/handoff, anti-forgery/anti-replay permission mechanisms,
  secure-randomness/claim/permission-expiry work and complete cold-boot capture.
- Drop the separate rehearsal/preflight. Integrate basic checks before flashing
  confirmation; do not reintroduce an extra boot or physical dry-run gate.
- Defer automatic maintenance launch and automatic recovery return until further
  owner instruction. Manual SD start/restart is the selected procedure.
- A fresh yes/no prompt before each write is sufficient. Repeated prompt handling
  is left to the operator; no automatic loop-detection framework is needed.
- No new MCU, heater, motion, stock qualification or broad host-product work is
  required to finish H12. No RTC correction solely for abandoned permission expiry.

## Subagent execution and ownership

Use one bounded implementation at a time. The coordinator owns shared records,
Git/pushes, physical access and operator instructions.

1. `project_planner` (Sol/medium): smallest source-backed SD implementation plan.
2. Separate `feature_approver` (Sol/medium): review the bounded implementation
   proposal against the settled owner scope; no repeat owner product approval.
3. `project_implementer` (Sol; medium for this cross-component adaptation): own
   only assigned implementation/test paths in a clean branch/worktree.
4. Fresh independent `feature_verifier_high` (Sol/high): verify delivery and
   target/confirmation/write/readback evidence; never reuse author/planner.
5. `high_consequence_reviewer` (Sol/medium, high only for material uncertainty):
   exact physical action review immediately before the identified operation.

Native subagent launch currently fails with “agent thread limit reached”. The
planner and independent approver completed in separate sessions using the documented full-role fallback;
actual model/effort are verified from runtime metadata. No global model or billing
configuration is changed. Current execution details and the bounded plan are in
[the H12 delivery plan](../docs/development/h12-sd-delivery-plan-20261003.md).

Old pending RAM-handoff/preflight/return-guard dispatcher tasks are marked blocked
with the owner’s superseding decision as the reason; their schema has no cancelled
status. Their historical completed evidence is retained. They are not blockers for
this replacement delivery and must not be resumed to satisfy H12.

## Following H12

Resume reliable commissioning-host work and the first-print goal, followed by
remaining host OS/recovery features and stock release qualification. Existing
accepted work/evidence is retained. Unrelated administration work must not
supersede ready H12 work; it may proceed only when H12 truly awaits a physical
input and it does not delay H12 or duplicate its resources.
