# Current delivery goals

## Completed goal — Cockpit software management, 2026-10-09

Dedicated **Software** controls are implemented and installed: Nano/htop/tmux/vnStat
catalog, dependency/download/storage preview, reviewed durable install/remove jobs,
explicit vnStat service settings and private compatibility report/download.
Actual writable boot mode and atomic idle admission gate package/service changes.
Removal preserves configuration/user artifacts; uncertain jobs retain their outcome.
The report meets ADR 0004's first-stage reconciliation allowance and preserves
customized image activation blocking pending a validated derived image.

26 native checks, disposable Chromium/staging checks and five actual ARM APT/systemd
jobs passed. Actual printer Cockpit HTTPS/PAM/sudo preview/cancel, metadata report
completion/download and navigation passed; all eight final assets and 46 original
preservation hashes matched. The installed older Store compatibility issue was
corrected without replacing its state module. Package/mode/network/reboot/printer
outputs were unchanged; diagnostic masks, root/boot read-only and managed Mainsail
No login remain. See [delivery evidence](../docs/features/cockpit-software-management/evidence.md).

Agent implementation/integration and a targeted independent source/installation
assessment were used; completion is self-validated. The exact ARM source hash is
retained separately from later native-tested corrections. This is software/control
acceptance, not physical power-loss, heating/motion/printing or release qualification.


## Completed goal — Cockpit network administration, 2026-10-09

Dedicated **Network** controls are implemented and installed: interfaces and saved
Wi-Fi connections, DHCP/static IPv4 and DNS, hostname/FQDN, reviewed changes with
180-second confirmation and durable rollback, existing-CA certificate updates,
and reviewed restart with atomic idle admission. Backend/browser/integration and
nine actual ARM NetworkManager journeys passed. Actual printer Cockpit HTTPS
PAM/sudo status and cancelled reviews passed with all 38 preservation hashes and
current managed Mainsail **No login** policy unchanged. See [delivery evidence](../docs/features/cockpit-network-administration/evidence.md).

The network/access implementation requirement is complete. Physical network
migration, interruption, new boot-hook execution, heating/motion and release
qualification remain separate. Agent implementation/integration and a targeted
independent source/installation assessment were used; completion is self-validated.

Current October 9 state supersedes the temporary/current-boot wording in the older
identity summary: persistent Mainsail/API units are installed and have passed their
normal-boot checks. Generated hardware configuration remains applied to the
diagnostic printer; Klipper/health/RAUC remain masked, PSU OFF, no MCU session,
root/boot read-only. No network/name/restart mutation occurred for this goal.


## Completed goal — persistent printer identity, 2026-10-08

The printer now has a persistent CA signing Cockpit and Mainsail certificates,
persistent SSH host authority, and Cockpit **Printer identity** controls for CA
download, trusted public keys and reviewed identity ZIP backup/restore. Actual
Cockpit upload authorized a disposable SSH key; restoring the downloaded baseline
restored original access and rejected that key. Both service leaf certificates
changed while the original CA continued to verify them. Native Mainsail login and
websocket initialization remain usable. See [delivery evidence](../docs/features/persistent-printer-identity/evidence.md).

Recovery builders now use the owner-selected **recovery / recovery** convenience
password, verified through isolated real PAM/SSH. Existing physical recovery media
were not rewritten. Normal-host key-only policy remains in force. Granular identity
requirements are complete; unrelated onboarding/network/release and physical checks
remain open in [host tasks](../docs/hardware/host-os-tasks.md).

Current state supersedes the older October 4 inactive-config wording below:
the generated hardware configuration has been applied to the diagnostic printer
services, with Mainsail/API available through their separately installed temporary
current-boot units. Production Klipper/health/RAUC remain masked, PSU OFF, no MCU
session, root/boot read-only, hardware state unchanged. This is software identity
and access acceptance, not heating/motion/printing or normal-release qualification.


## Completed goals — sensors and component configuration, 2026-10-04

1. **Default-curve ambient baseline complete:** 12 stable no-output observations
   and concurrent chamber BLE readings passed independent closure review. Original
   factory conversion curves are unchanged. Fine calibration remains deferred.
2. **Cockpit printer hardware configuration complete:** installed board/component
   selectors, 30 sourced presets, explicit pins/limits, extensible data catalog,
   incomplete drafts and reviewed inactive candidates. Independent high software
   verification and separate installed delivery verification passed. Actual Cockpit
   login, presets, save/reopen, import/export, cancel/apply, previous restore,
   board clearing and session behavior passed on test-sv08-01.

See [installed evidence and limits](../docs/features/printer-component-configuration/installed-evidence.md)
and [ambient baseline](../docs/features/sensor-default-commissioning/intake.md#corrected-ambient-baseline-completed).
Source/review failures and both installed test-harness corrections remain recorded;
no failed result was overwritten or counted as a complete pass. The final saved
configuration contains the two default-curve sensors and remains inactive.

**Next physical work is deferred by the owner:** filament/probe transitions,
component/circuit facts and later output commissioning. Fine calibration remains
for later. No physical action is requested now. The PSU is OFF, USB-powered host
available, root/boot read-only, printer services masked and no live printer.cfg or
open MCU session. No heat, motion, printing or release qualification is claimed.
The dispatcher has no authorized ready task; broader requirements remain in the
[remaining-work plan](../docs/remaining-work-plan.md). Main/WIP and completed feature
history are published under standing push authorization.

## Completed goal — reliable commissioning host, 2026-10-04

The installed test-sv08-01 host passed independent final delivery verification:
automatic boot confirmation after a normal restart and HW-667 power cycle,
persistent SSH/Cockpit account access and simple SV08 Mainline branding, matching
host/two-MCU build metadata/dictionaries, and inactive input-only config parsing.
The initial environment-history and device-numbering defects were repaired and
independently verified; original failures remain recorded. See
[installed completion](../docs/features/commissioning-host-readiness/installed-completion.md).

Owner-authorized autonomous smartplug control now handles printer PSU on/off;
HW-667 separately controls USB power. Final PSU status OFF, H616 still USB-powered,
printer services masked, no active printer.cfg, no open MCU serial sessions.
Main/WIP publication completes the goal. This is diagnostic-host acceptance;
physical sensor/input accuracy, heating, motion, printing, full A/B/release
qualification remain subsequent work. H12 exclusions below remain authoritative.

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
