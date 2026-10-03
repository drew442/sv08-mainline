# Current delivery goals

## Active goal — reliable commissioning host, 2026-10-03

Prepare the installed test-sv08-01 host for sensor-only commissioning: dependable
normal boot, persistent SSH, usable browser administration, matching host/MCU
software and an explicitly output-free sensor configuration. Inspect the current
system before choosing fixes; reuse accepted implementations and their valid
evidence. Require independent review of new substantive scope and delivery, and
fresh exact-operation review before boot-policy changes or hardware writes.

The owner also requested a simple SV08 Mainline Cockpit theme; include login and
host-page branding with unchanged controls and authentication.

This goal includes installed validation and publication to main and WIP. Physical
sensor accuracy/input commissioning, heat, motion, printing, full A/B failure
qualification and release qualification remain subsequent work. Preserve the SD
recovery path and all owner-selected H12 exclusions below.

Initial fresh inspection: the same installed slot-A boot remains reachable, with
read-only root, writable /data and no failed systemd units. Boot-health, RAUC and
printer units remain masked in the command line; only one MCU USB identity is
currently enumerated. These observations do not establish boot reliability or
paired-MCU readiness. Native agent launch hit its thread limit; the planner uses
the documented separate-session fallback with full role and verified Sol/medium.
The coordinator owns physical access, shared records and publication.

The bounded proposal, software repairs and exact installation actions passed
independent reviews. Cockpit login, elevation, status, logout/relogin, branding
and the owner-requested password now work and persist. The first normal restart
exposed an eMMC-numbering assumption; its independently reviewed controller/CID
repair passed a second normal restart and one HW-667 power cycle. Automatic
confirmation returned A3/B0 each time, with persistent SSH/TLS identities and
state unchanged. B and recovery partition hashes match the baseline. All printer
output services remain masked and inactive. Inactive sensor file-output parsing
passed; current paired MCU identification awaits the owner turning PSU on for
toolhead availability, followed by PSU off and independent final delivery review.

## Completed goal — finite image-job history, 2026-10-03

Completed `host-image-history-rollover:finite-history`. Explicit browser
review/apply/cancel maintenance archives settled 128-job batches while preserving
complete receipts, unknown dispositions and retry identities. New work requires
its own review. Capacity remains finite: eight archives plus one active batch,
1,152 retained identities, with the approved storage and shared-data reserves.

All seven acceptance checks and thirteen review constraints passed fresh
independent GPT-6.1 Sol/high verification. The first review found four defects;
all were repaired before acceptance. The final regression passed 310 tests.
Reviewed candidate `f77de7859aad88cf4eecd84207c8fadd79f004ea` was merged into main;
the dispatcher records the task complete and WIP includes the delivery.
All commits are published under the owner's standing push authorization.

See the [final independent review](../docs/features/host-image-history-rollover/reviews/20261003-final-findings.md)
and [source-bound repair evidence](../docs/features/host-image-history-rollover/repair-execution.md).
This completes the approved offline delivery. Current authenticated installation,
physical power-loss recovery, factory-image fit and release qualification remain
unproven. No printer operation was performed for this goal.

## Completed goal — H12

**H12 complete — 2026-10-03.** The minimal attended SD tool, exact physical
write/flush/full readback and subsequent normal installed-eMMC boot all passed.
Independent completion review passed. Operator-requested resets now use HW-667;
USB cable removal is not the normal reset procedure.
Prior goal/checkpoint text is preserved in
[the history through October 2](goals-history-through-20261002.md).

The [owner’s ten-point scope](../docs/decisions/20261002-h12-scope-reduction.md)
is authoritative. All commits are pushed to GitHub under standing authorization.

## H12 goals and completion evidence

| Goal | State | Deliverable and completion evidence |
| --- | --- | --- |
| H12-1 — Deliver the minimal SD flashing tool | Complete: installed ARM64 journey passed, independently verified, merged and pushed | Run from independent SD. Select image and installed eMMC, check identity/capacity/source separation/target not in use/image checksum, display image and target, ask yes/no, then write/flush/full readback. No/EOF performs no write. Focused offline tests and independent delivery verification pass. |
| H12-2 — Prepare the real SD maintenance session | Complete: exact source/target, independent SD, reviewed UI and KVM confirmation passed | Owner facts, identified artifacts, recovery path and independent operation reviews recorded. |
| H12-3 — Complete one attended reimage and normal boot | Complete: full write/flush/readback matched; relay restart reached eMMC slot A with SD absent and authenticated SSH | [Physical completion](../docs/features/h12-attended-sd-reimage/physical-completion.md); root identity matches accepted spare, /data mounted, KVM Debian login observed. |

All three H12 outcomes passed. Offline acceptance is not a
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

## Completion boundary

The current image is diagnostic. Boot-health/RAUC and printer output services
remain masked; no printing or release qualification is claimed. Do not repeat
power cycles unnecessarily because diagnostic boot attempts are finite. Use
HW-667 for authorized resets and hold relay power off for future media changes.
No further owner action is needed for H12. Broader project work remains governed
by its existing requirements and [remaining-work plan](../docs/remaining-work-plan.md).
