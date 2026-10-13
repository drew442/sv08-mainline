# Current delivery goals

## Completed PR-delivery goal — Printer Hardware journey, 2026-10-11

Published [PR #7](https://github.com/drew442/sv08-mainline/pull/7) for owner review.
Visible saved/draft/prepared/application state, linked known attention, selected
questions, incomplete draft saving and truthful cancellation are delivered.
PHJ-1–7 pass: two composed browser journeys,43applicable standard tests,
syntax/navigation/diff checks and actual rendered assessment.
See [source-bound evidence](../docs/features/printer-hardware-journey/evidence.md).

The native goal ends at this review PR. The existing feature task remains
**validated awaiting owner integration**, preserving reviewed commit79b2568.
Main is unchanged; no merge, deployment or printer access occurred.
Successful application remains source-reviewed only; browser evidence uses a
session/transport shim and real Store/Budget. Small deferred scope is recorded
in the [proposal](../docs/features/printer-hardware-journey/proposal.md).

## Completed goal — Cockpit UI/UX workplan, 2026-10-11

W0–W8 delivered using named implementation, research and integration agents.
Six task sections, contextual hardware routes, guided configuration review and
application, clearer operation/status ownership, preserved drafts, accessible
connection tables and responsive keyboard/touch navigation are integrated on main.
Core functionality, authorization and backend safety checks are preserved.

Source, rendered browser and disposable native ARM64 Cockpit/PAM/sudo acceptance
passed; reusable navigation/jobs/unknown-receipt/history-pressure checks passed.
See [delivery evidence](../docs/features/cockpit-ui-ux-implementation/evidence.md)
and [regression evidence](../docs/features/cockpit-ui-ux-regression-maintenance/evidence.md).
Both feature records are done. Evidence distinguishes native and simulated
transport, transitional captures and reflow checks; no human usability study,
accessibility certification, CPU savings or printer deployment is claimed.

## Completed goal — PR #6 branch maintenance, 2026-10-10

Fast-forwarded main to PR #6; verified archive tags preserve all obsolete branch
tips before removing their branch names. Main is the sole remaining active branch
and includes PR #6. Historical worktree files remain. See
[maintenance evidence](../docs/development/branch-maintenance-20261010.md).

## Completed goal — Physical automatic-update validation, 2026-10-10

Owner authorized agents and completion of a harmless trusted automatic update,
then an unhealthy trial demonstrating actual H616 bootloader fallback. Preserve
configuration, calibration, identity and data; keep heaters/motion inactive.
Prepare the missing installed backend, exact artifacts and recovery/precondition
evidence, obtain independent operation assessment, execute the bounded journey
and publish measured results. Physical coordination: H13; source preparation:
[scope](../docs/features/physical-automatic-update-validation/proposal.md).

Actual healthy update and three-failure U-Boot fallback completed with preservation,
outputs inactive and automatic test policy disabled. Reviewed continuation repairs
and qualification limits are recorded in [completion](../docs/features/physical-automatic-update-validation/completion.md).

## Completed goal — Automatic update policy and activation, 2026-10-10

Automatic updates require trusted metadata and bundle signatures. Cockpit provides
reviewed per-operation manual provenance exceptions and separate advanced version,
compatibility-label, customization and downgrade controls. Physical target/layout,
integrity/readback, immutable source, capacity, recovery and idle protections remain
mandatory. Autonomous discovery now stages, arms and requests controlled reboot;
durable receipts handle opt-out, interrupted dispatch, confirmation and fallback.

Agents implemented and reviewed the delivery. Focused native checks passed 307 tests;
after corrections, 66 overlapping affected checks passed. Actual patched RAUC passed
16 trust/integrity cases, Chromium passed the policy/review UI checks, and a fresh
six-boot disposable ARM journey confirmed a healthy update and fallback after three
failed trial attempts with settings and identity preserved. Targeted independent
review passed candidate 1a958824b3b4938fcc84949b26e33ff0d4ea213e, preserved in main.

One initial fixture exceeded its live-storage cap; its failed receipts were retained
and one diagnosed fresh-fixture repair passed without resetting cumulative charges.
Codex/Beelink storage was checked. Cleanup reclaimed 6,646,181,888 bytes; final Codex
free space was 34,012,852,224 bytes. Carried runtime was 2772.026/3600 seconds and
cumulative allocation 24,352,382,976/32 GiB, within the revised 10 GiB live ceiling
and 16 GiB free-space floor. Shared bases and unrelated history were preserved.

Source and evidence are integrated; no physical printer update, reboot, service
change or output activation occurred. Offline boot selection and failed-health
callback limitations are explicit; physical/printing qualification remains separate.
See [evidence](../docs/features/automatic-update-policy/evidence.md) and
[product contract](../docs/development/automatic-update-policy.md).

## Completed goal — Installed H616 crypto offload comparison, 2026-10-10

Bounded existing-driver Ethernet measurements completed on test-sv08-01 without
updates, reboot, outputs, configuration changes or guest files. Nine approximately
48 MiB CE batches gave correct digests/exact task counters and median 52.76/120.50/
142.22 decimal MB/s at 4/16/28 KiB. Larger one-shot and streaming requests fell back.
Root/boot read-only, boot identity and inspected service masks/states were preserved.
Final probe processed 461,434,880 bytes in 5.340 seconds; retained preliminary and
pre-send failure bring remote command duration to 13.832 seconds. No images created.

Two research agents traced hash consumers and pinned kernel semantics. Python/OpenSSL
and dm-verity do not invoke the measured CE AHASH path, so these results establish no
end-to-end acceleration. CPU software and other update stages were deliberately not
benchmarked. Specification ceilings plus explicit planning assumptions give serial
cold-read examples; the central 620 MB bundle scenario is 7 min 45 s with an ideal
1 Gbps receiver/immediate reboot, or 8 min 29 s at the reported 100 Mbps link. These
are illustrative estimates, not observed ready times. At the measured revision, the feed armed next boot
without requesting reboot; installed diagnostic feed is absent and runtime differs.

Source/evidence/arithmetic are self-validated; source research is not independent
delivery verification. See [measurement and model](../docs/hardware/host-crypto-offload.md).
The existing offloader is unsuitable for whole-image incremental hashes; no updater
integration or policy bypass controls were changed. Recovery/update-policy product
work and physical/printing qualification remain separate goals.

## Completed goal — Assembled update and reboot reliability, 2026-10-10

Controlled reboot now closes service-start and mutation admission before systemd
acknowledgement; lost acknowledgements retain the gate. Healthy ordinary boots
restore only the running slot's attempt counter while preserving order and the
other slot. SQLite snapshots open private copies and reserve backup workspace,
preserving the live database and its sidecars.

258 native checks and twelve accepted disposable ARM boots across fourteen attempts
passed signed updates, failed-trial exhaustion/fallback, writable/customized
preservation, interrupted snapshot retry and actual no-space refusal. Both discarded
fixture failures remain in the evidence. Agent integration and independent targeted
source/evidence review passed against clean reviewed commit `8811ac2452b15f6a6bef106f50cac24471b5731f`.
See [acceptance evidence](../docs/hardware/host-reliability.md).

Codex and Beelink storage were checked before image construction. One live GPT disk
at a time, bounded allocation/runtime and exact artifact retirement avoided keeping
historic disposable copies. Cleanup reclaimed 6,025,523,200 allocated bytes and left
34,067,333,120 free bytes on Codex; shared bases and unrelated historic images remain.
Source is merged and published. No live printer operation or deployment occurred;
physical power-cut, board boot execution, printer admission and printing/release
qualification remain separate requirements.

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

## Network journey delivery — 2026-10-11

Network delivery implementation and NJ1–7 acceptance complete; source task self-validated for review publication, owner integration pending. Source task and acceptance criteria: [network-journey](../docs/features/network-journey/proposal.md). Publish a tested review PR, without merge/deployment/printer access. Prior Hardware task is integrated after owner merge of PR #7. Native Hardware delivery goal remains complete; no unrelated native goal replaced.

## Remaining Cockpit pages —2026-10-11

Remaining-page implementation and RP1–11 acceptance complete for owner review. [Scope](../docs/features/remaining-pages/proposal.md) and [source-bound results, screenshots and limitations](../docs/features/remaining-pages/evidence.md). Source task self-validated; owner integration pending. No deployment or printer operation. Native prior Hardware goal remains complete; no unrelated goal replaced. Network task integrated following owner merge of PR8.

## Completed PR-delivery goal — PR9 follow-up,2026-10-12

Published [PR10](https://github.com/drew442/sv08-mainline/pull/10), ready for owner review. All six bounded acceptance checks pass; tested immutable candidate42e1935fb489a8576a13f225b10972043a3c38e7. Final installed disposable ARM64 Cockpit/PAM journey passes12 ordinary routes, authentication/session behavior, actual200% zoom/keyboard and real signed-upload fault/reconciliation checks, browser exit0 in455.366seconds, backing unchanged. History/upload, real reserve-pressure, exact automatic-policy, staging and relevant regression checks pass. Actual rendered evidence inspected; failed attempts and fixture limitations retained in [source-bound evidence](../docs/features/pr9-follow-up/evidence.md).

The project task remains **validated awaiting owner integration**. Native PR-delivery goal is complete when this publication record is pushed; main remains unchanged. No printer operation, merge, deployment or physical qualification. Busy-review recovery is source-reviewed and supported by refusal evidence, but not exercised in the final passing run. Deferred UI scope remains small:200% header height and concurrent finite-read coordination. Effective agent telemetry and savings are not claimed. PR9 historical evidence is preserved.

## Completed PR-delivery goal — Cockpit owner notes,2026-10-12

Implement [owner notes](../docs/features/cockpit-owner-notes/proposal.md) with named task-scoped agents: network device filtering, outline object/navigation icons without heading decoration, default connection graph, button spacing and truthful traffic-light update statuses. Acceptance and2400second/256MiB primary allowance recorded before source edits. Offline browser fixtures only; no printer deployment or operations. Finish with tested review PR and source-bound evidence.

Published [PR11](https://github.com/drew442/sv08-mainline/pull/11). Immutable candidate a08a6bcbfb3465f50a7c413afd250826eee967a7 passes all four acceptance checks:36 standard checks, complete composed printer and ordinary configuration journeys, base administrator fixture, source-bound notes at supported viewports/genuine200% zoom, and final12 printer staging checks. Actual final renders inspected; failed evidence retained in [delivery evidence](../docs/features/cockpit-owner-notes/evidence.md). Project task validated awaiting owner integration. CI running at publication; no printer operations, merge or deployment. Effective agent telemetry and hardware qualification are not claimed.

Owner merged PR11; deployment completed2026-10-12 from9fd8de5411edc26d49b41e0e943581b86e7efe6d. [Installed results](../docs/features/cockpit-owner-notes/deployment-20261012.md):15 assets/all six status helpers pass, protected hardware and backends preserved, root restored read-only; no reboot/service activation. Project task now done following owner integration.

## Cockpit dark theme delivery —2026-10-12

Published [PR12](https://github.com/drew442/sv08-mainline/pull/12), candidate4350f17a2a5adce73d8e51fb5d1b1d0f6d57f3b2. System settings Appearance offers ordinary-access Light/Dark with browser-local persistence. Three acceptance checks self-validated:34 unit/staging tests, final composed normal/genuine200% browser journeys and base administrator fixture pass; actual renders inspected, draft/authority protections preserved. [Evidence](../docs/features/cockpit-dark-theme/evidence.md) records source hashes, failed attempts, reused regression limits and existing globally blocked-storage follow-up. Project task validated awaiting owner integration; no native goal changed, no deployment or printer access. One named medium-requested implementer with task-scoped UX skill; effective settings not independently observed.

Owner merged PR12; dark-theme deployment completed2026-10-12 from68cf588d8a9db574b25adb6f9f91eae7029c497c. [Installed evidence](../docs/features/cockpit-dark-theme/deployment-20261012.md):15 assets/six helpers pass, configuration/backends/services preserved, root restored read-only. No restart or printer outputs. Project task integrated following owner merge.

## Completed PR-delivery goal — recovery data restore,2026-10-12

Owner selected full exported-data restore and explicit fresh-state initialization, disposable tests and review PR; no printer operations. [Scope and acceptance](../docs/features/recovery-data-restore/proposal.md). Native goal aligned; one implementation/two-child cap,3600second/512MiB execution allowance. Existing recovery export read-only protections remain intact; no formatting or silent replacement.

Published [PR13](https://github.com/drew442/sv08-mainline/pull/13), candidate6aee2da6789e2548c7b5fadba0e3013d9e60ca17. All five acceptance checks self-validated:148 unit/regression checks and actual GTK chooser/review/cancel/restore/refusal/fresh apply pass with no source drift; actual final renders inspected. Supplemental independent source reassessment confirmed the correction to a reproduced fresh-state corrupt-success defect. [Evidence](../docs/features/recovery-data-restore/evidence.md) binds final source, results, representative visual and retained failures/limits. Project task validated awaiting owner integration. CI in progress at publication; no printer access, merge or deployment. Production target preparation/normal-boot activation and physical recovery-media qualification remain separate. V1 directory integrity and unsupported metadata fidelity explicitly disclosed.

## Completed PR-delivery goal — recovery restore end to end,2026-10-13

Owner merged PR13; previous source task integrated. Complete [preparation, activation and disposable boot scope](../docs/features/recovery-restore-e2e/proposal.md) with named task-scoped agents,7200process-second/6GiB primary allowance. No printer access, deployment or physical rescue-SD qualification. Publish tested review PR. Native goal aligned.

Published [PR16](https://github.com/drew442/sv08-mainline/pull/16), candidate 1180484d383ce400db51472bb3adfad46d1eb4b0, with all five acceptance checks self-validated: 203 root regression/installed-state checks without skips, actual GTK review/cancel/apply/error behavior and inspected renders, ten installed ARM64 QEMU guest runs including restored normal boot/reboot, rollback/previous boot, interrupted fresh activation, actual pre-PID1 normal refusal, explicit recovery rollback and successful previous boot, plus wrong-media refusal with unchanged disks. Final archive/paired boot whole-disk hashes match original fixture hashes. [Source-bound evidence](../docs/features/recovery-restore-e2e/evidence.md) retains failed attempts and supplemental assessments, budgets/cleanup and limits. Native named task-scoped agents used; no independently observed effective model/effort or savings claim. Project task validated awaiting owner integration. All three PR CI checks passed. Initial Cockpit follow-up CI failed starting Chrome before its automatic-policy browser journey; one fresh-runner retry passed without source changes. The failed log is preserved in the assigned evidence directory; no unrelated product/test code was changed. No printer access, merge or deployment. Physical rescue-media/full printer-service qualification, larger-archive performance and startup diagnostic clarity remain outside this completed PR-delivery scope.

## Active goal — recovery printer-stack qualification, 2026-10-13

Owner merged PR16; prior task integrated. Qualify [the complete installed software stack](../docs/features/recovery-printer-stack/proposal.md) in disposable systems, including necessary constrained opaque-link compatibility, real authentication/network/identity persistence and rollback. Named task-scoped agents, one implementation/two-child cap,10,800 process-second/12GiB initial allowance;29GiB local free. No printer access, deployment, merge, physical rescue-SD or printing-readiness claim. Publish tested review PR. Native goal aligned.

### Recovery printer stack qualification — blocked, 2026-10-13

[Draft PR17](https://github.com/drew442/sv08-mainline/pull/17), candidate `f57123c08fb8c7509d8139a92ac2fc0fc9b8f827`, preserves tested opaque identity/log-link recovery compatibility, a confirmed Cockpit startup-order correction, and the actual installed-stack disposable harness. Offline checks and both current image builds passed; complete source backup/restore/activation/reboots/rollback/browser acceptance remains unproven. Fresh QEMU preparation failed unchanged pinned Klipper validation: aligned-clock SIGKILL with unestablished cause, then the previously successful unaligned-clock mode exceeded readiness deadline. No production resource, calibration or TLS guards were relaxed. Private failed inputs/logs/receipts and shutdown guest handles remain under the assigned recovery-stack scratch/fixture directories. Native goal remains blocked/incomplete; task blocked and review PR draft, no merge/deployment/printer access. Next useful action is justified QEMU timing/accounting diagnosis or approved native ARM64 disposable execution. The original 10,800 process-second allowance and cumulative attempts remain; recorded generated-output continuations reach 48GiB, with 26GiB free last checked. Source-bound evidence and limitations are in the PR's `docs/features/recovery-printer-stack/evidence.{md,json}`.

Initial PR17 deterministic CI exposed an isolated-history reader v2 omission; repaired with pinned full-inventory validation and retained history gates. Final root compatibility124/124 and exact guarded history/upload82/82 passed, no skips. The coordinator’s initial local unittest driver omitted its multiprocessing main guard; assigned descendants were terminated, the invocation corrected, and failure evidence retained. Latest feature commit verified on origin; CI pending at this record update. Image builds precede this offline correction and are not final installed qualification. Latest free space25GiB; goal/task remain blocked.

Final PR17 CI: agent deterministic and actual ownership checks passed on `f57123c08fb8c7509d8139a92ac2fc0fc9b8f827`. Cockpit deterministic run38373030135 passed on fresh-runner attempt2 after unchanged automatic-policy browser failed to create DevToolsActivePort within10seconds on attempt1. The browser script/workflow were unchanged; no check was relaxed. Private remote log and actual attempt metadata retained. All assigned disposable QEMU handles are stopped with receipts. Goal/task remain blocked by installed parser qualification, not by current CI.
