# Parallel delivery assignments

Assigned 2026-09-18 under the owner's request for parallel goals and deduplicated
human work. This coordinates the [remaining work plan](../remaining-work-plan.md);
it does not change its acceptance requirements or authorize new product scope.

## Goals and ownership

| Lane / agent | Delivery goal | First bounded assignment | Completion gate |
| --- | --- | --- | --- |
| Recovery / `recovery_delivery` | Independent recovery usable on the supported media, with preserved data | Turn approved export composition into an exact source-backed implementation and validation packet | Approved export checks independently verified; subsequent restore/release work separately scoped |
| Printer / `printer_delivery` | Safe attended first print on test-sv08-01 | Map actual configuration gaps and prepare ordered offline configuration/commissioning slices | Reviewed matching host/MCU configuration, measured inputs/outputs, homing, heat and representative print evidence |
| Host / `host_delivery` | Reliable bootable A/B host with complete administration and release composition | Map existing boot/admin/package evidence to concrete remaining integration slices | Board boot/health, A/B rollback, preservation, interfaces, complete capacity and release checks pass |
| Coordinator | Integrate lanes without duplicate human work or conflicting changes | Maintain shared dependencies, task ownership and review sequence | Each requirement has delivery evidence or an explicit remaining dependency; no unsupported completion claims |

The initial parallel assignments own only their respective work-packet documents:
[recovery](parallel-recovery-work.md), [printer](parallel-printer-work.md), and
[host](parallel-host-work.md). This is a justified separation of documentation
ownership, not three concurrent writers to the host runtime. Each child sets a
bounded session goal for that packet. The delivery goals above remain open until
their acceptance evidence exists; finishing a packet is not finishing a lane.

## Execution order and shared resources

Execution started 2026-09-18. The recovery feature is claimed under session
`recovery-composition-20260918` in the dedicated
`feature/host-recovery-export-composition` worktree. Its implementer owns the
preparer/provider, staging unit and focused tests identified in the recovery
packet. The coordinator holds the heavy-build lease for the locked ARM64
baseline and real guest media-identity capture; no printer access is involved.
Printer preparation owns commissioning forms and configuration intake only;
host preparation owns the boot-health intake only. Their completion does not
change the feature's running status or imply code delivery.

The [commissioning form](../hardware/test-sv08-01-commissioning-session.md),
[sanitized section inventory](printer-candidate-sections.md),
[printer intake](printer-configuration-intake.md) and
[boot-health intake](host-boot-health-intake.md) are the resulting preparation
artifacts. Boot-health safety/order changes require independent proposal review
before implementation; trial markers must not be bypassed just to report health.

Checkpoint: recovery source commits `265c1ed` and corrective `e0e6dab` are on
`feature/host-recovery-export-composition`, not merged as a completed delivery.
Independent component review reproduced 29 focused tests and confirmed fixes for
whole-disk destination/protected separation and stale assembly provenance.
The integration agent now owns the exclusive build/VM lease and fresh assembly
from `e0e6dab`. Full dirty-journal, installed GTK, failure and resource acceptance
remain open. Human H04/H07 tasks are not requested by this offline checkpoint.

The [printer interface feature](../features/printer-interface-config/record.json)
is independently approved with constraints and queued behind the active recovery
implementation. Private-overlay validation stays with the coordinator. The host
boot-health intake records a selected callback/lock contract and explicit
success marker; it remains preparation pending formal implementation approval.

1. Complete the three independent source-backed packets in parallel. Each must
   name actual paths, existing reusable evidence, smallest next slice and checks.
2. Assign the implementation lease to the approved recovery export composition.
   Its full approved constraints remain authoritative. Printer and host lanes
   can continue read-only research, configuration review and test preparation.
3. Hand a stable recovery revision and execution evidence to a separate verifier.
   Release the implementation lease to the minimal printer configuration slice
   while independent review proceeds, if their files/resources do not overlap.
4. Build the board commissioning candidate after its required configuration and
   boot/health changes. Run hardware gates when their exact prerequisites pass;
   continue host administration/recovery/release offline slices while waiting.
5. Prioritize first-print blockers, then remaining required host/recovery features,
   then stock/release qualification. A hardware blocker holds only its consumers.

Only one production implementation is active unless the coordinator records
explicit nonoverlapping ownership. Separate review sessions must not certify their
own code or execution evidence. Existing approvals are reused; new substantive
slices use the existing feature workflow. New optional features remain paused.

The coordinator allocates one heavy build/VM lease at a time: source revision,
fixture directory, disk images, ports, process handles and evidence output path.
No heavy lease is allocated during the initial packet preparation. Never start
another QEMU instance against a shared image, duplicate a timed-out build, or
delete another lane's output. Use passed evidence when inputs remain applicable.
Commit and record source changes before claiming evidence for that revision.

## One human-work queue

The [coordinated human tasks](../hardware/coordinated-human-tasks.md) are the single
dispatch queue. Existing hardware checklists retain the detailed acceptance
criteria and history; this queue groups their physical actions rather than
creating alternative requirements. All lanes refer to its stable H IDs.

Children report dependencies to the coordinator, never separately ask the owner
to move media, power-cycle, inspect a board or repeat a measurement. The coordinator
merges by physical action, target/profile, state and prerequisites, then records
all consuming acceptance checks. Similar-looking actions with different safety
states or materially changed artifacts remain separate controlled substeps.

Before requesting an action, prepare scripts, reviewed artifacts, captures and
all ready consumers. Reuse observations only when target, configuration and test
conditions remain applicable. Record evidence once and link it to each consuming
task. Invalidate only the affected checks when hardware, firmware, image, wiring
or environmental conditions change. Do not repeat factory/MCU backups already
accepted by the owner as a new development prerequisite.

At a hardware session boundary, do all ready safe work possible in the current
setup before changing it. Do not defer a ready first-print test merely to bundle
it with an unrelated unfinished release feature. If a new defect requires a
second flash or observation, record why the previous evidence is insufficient.

## Durable handoff and truthful status

For each implementation slice record the lane, owned paths, approval reference,
source revision, checks, resource lease, result/evidence and H IDs. The canonical
feature records remain execution/acceptance authority for tracked features.
Untracked remaining requirements first receive a bounded work packet/proposal;
this table does not preapprove mutable implementation plans.

Subagent sessions are finite. A completed preparation goal must be followed by a
new explicit assignment to execute its slice; this document is not a scheduler
and does not promise background progress after the active session ends. During
execution the coordinator continues the next authorized ready assignment while
other lanes wait for human evidence. Report pending, in progress, offline verified,
physically verified and release qualified distinctly.
