# Current delivery state

## Current continuation — recovery media ready, 2026-11-19

The native first-supported-release goal remains active. The actual 31,014,191,104-byte
FAT32 USB and blank SC16G SD on Beelink are identified and remain unmounted/unwritten.
Preserve the USB filesystem and tested rescue SD. No printer outputs, services,
firmware, boot or physical storage were changed during preparation.

Production source is frozen at `c69618ea9ac060b8714d68c1751fd36bb653988c`.
Normal six-partition image, internal recovery and signed revision5 OTA pass actual
construction/readbacks and the selected-software public source/notice gate. The
normal image is hash-verified at Beelink's existing read-only NFS source. Export SD
image is hash-verified in Beelink's private staging; it is not written to the card.
All artifacts remain unqualified for public release or printing.

Delivery-only wrapper correction: `766b0257c55be3675493e7cc38bb05bd2b73af66`.
Native execution exposed a DTB lookup into already-compressed usr. The correction
extracts only the sealed DTB. Explicit ancestor pinning proves all other shipped
source and upstream gitlinks unchanged; integration inputs must match. Original
production images/receipts are untouched, with producer and delivery revisions
recorded separately. For later restore-SD composition use the frozen c696 runtime
builder/root, then766's delivery wrapper with the explicit producer pin; never
relabel an old image or bypass source/notices admission.

63 media checks,12 supported checks, eight unchanged SD-loader checks and9 root
preservation/ownership checks pass at their recorded inputs. Native helper CLI
passed against actual731 GPT normal-A with synthetic data; real-backup preparation
against the final image remains mandatory before installation. The archive helper
preserves original data/identity and quarantines inherited startup permission.
[Current delivery evidence](https://github.com/drew442/sv08-mainline/blob/feature/supported-sd-provider-binding/docs/features/supported-release-candidate/sd-delivery-evidence.json)
records source/receipt hashes and limitations; earlier proofs retain their revisions.

Source worktree: `local/feature-workflow/worktrees/supported-release-boot-fix`,
branch `feature/supported-sd-provider-binding`, run
`c58c1f75e9ff4db9b256ae38823629a7`, lease base `f356beb`.
The authoritative feature record governs source-task status. The complete release
goal has separate physical acceptance. Native checkout is now the delivery766
revision deliberately; do not advance it for record-only commits.

Carried source ceiling7,200process-seconds/1.25GiB, conservative charge5,200seconds/
1,220MiB. Native ceiling18,000seconds/168GiB, conservative charge17,000seconds/166GiB,
including all attempts, SD loader, transfers and logical32GiB workspace. No deletion
credits. One verified compressed731 prototype and all receipts are retained;
superseded generated roots are retired after validated replacements. Caches remain.

Next: obtain explicit authority to write only the reviewed738,197,504-byte export
image to the exact blank SD; require fresh whole-card/child usage/CID/capacity checks
and exact-prefix direct readback. Writer assertions must remain enabled. Independent
assessment passes with conditions, including preserved rescue SD, current idle/source
state and orderly original-system shutdown before removing PSU/USB back-power for
attended media moves. Neither authority nor current printer state is inferred.
Actual inventory must match the immutable export policy, including SD removable
status; mismatches stop admission. Independently preserve the completed original
backup, then verify target-bound derived archive before any later installation.
No eMMC image write, MCU/heater/motion action or public binary release is authorised.
PR39 reports hosted CI separately; query its actual current head/status.

## Historical 2026-11-17 preparation (superseded only where stated above)

## Current continuation — new SD and eMMC topology repair

Current owned source worktree: `local/feature-workflow/worktrees/supported-recovery-boot-areas`,
branch `feature/supported-recovery-final`, run `fb32f83d8733428da23740228bcceeaa`.
Previous protected-area run/branch is preserved at `dcde29c`.
Earlier source worktrees and all evidence remain preserved.

Owner supplied a new blank SC16G SD (15,931,539,456 bytes), identified read-only
on Beelink as `/dev/mmcblk0`; it is unmounted with no holders and has not been
written. The separate backup drive is still requested. Current recovery requires
backup, SD root and eMMC target to be distinct physical disks.

Actual read-only invocation of the unchanged installed media inventory reader
failed on `mmcblk2boot0`. The eMMC exposes boot0/boot1 as readonly 4MiB hardware
areas, not independently identified user disks. Protected nonselectable auxiliary topology is repaired at 7317a89: 54 focused
checks plus 99 related checks (three repaired fixture/input failures) pass. The
candidate reader succeeds in memory against the actual eMMC without deployment.
See `docs/features/supported-release-candidate/boot-area-evidence.json`. Source/native passes below remain
historical at their stated inputs; DD65 images are not deployment candidates.
No card, eMMC, MCU, service or printer-output changes have occurred.

The SD root and loader source/TF-A preparation exist, but final SD composition
waits for actual backup-media policy and refreshed source-bound artifacts. Reuse cached packages
and the recorded normal/recovery roots; no unchanged OS bootstrap. Source ceiling
stays7,200seconds/1GiB. Native ceiling is now18,000process-seconds/124GiB after a
bounded continuation for this demonstrated repair and affected artifact refresh;
current conservative charges are source 3,900 seconds/880 MiB and native
12,100 seconds/98 GiB, including all prior attempts, inputs and the logical
32 GiB workspace, with no deletion credit. The existing execution
ledger records the full continuation. No physical write or release is authorised.

## Preserved source checkpoint (before this topology finding)

PR38 merged as `47e265e21b3382ddc921317097e53991fffd6035`. The native
first-supported-release goal remains active. The existing
[supported candidate task](../docs/features/supported-release-candidate/proposal.md)
records source ownership/acceptance; its completion is distinct from the full
release goal. Recovery qualification remains complete at its recorded scope.

[PR39](https://github.com/drew442/sv08-mainline/pull/39) contains the supported
candidate/clean-owner path and source-bound evidence under
`docs/features/supported-release-candidate/`. Current claimed worktree:
`local/feature-workflow/worktrees/supported-release-boot-fix`; integration PR branch:
`feature/supported-release-integration`. Preserve both tips and the native runner.

Repaired production source is frozen at `dd65c33f51d535c1f9f3ff7a15482fc5bb4c008d`.
All four hosted workflows pass there. Source checks pass, including 49 focused
commissioning/health tests and 62 related passes/one explicit opt-in namespace skip.
Two distinct ARM64/KVM boots passed six explicit STUB-health/permission activation
cases each. Native pinned factory/selected validators and 29 synthetic owner/PAM
checks retain their original evidence; compared validator/owner runtime and final
normal PAM inputs are unchanged. These checks do not establish normal board boot.

The repaired normal six-partition disk (7,818,182,656 bytes), internal recovery and
signed revision 5 OTA (545,122,734 bytes) are built. Six partition/SPL/environment
readbacks, trusted signature, streamed payload/inner-release checks and the default
selected-software public source/notice gate pass. `candidate-build-evidence.json`
and `boot-lifecycle-evidence.json` in PR39 hold exact hashes/commands/limitations.
The 66dce8d prototype is superseded/not for deployment; one round-trip-verified
compressed archive and all historical receipts remain, redundant raw components
were retired. The final candidates remain private and unqualified for release.

Cumulative allowances remain source 7,200 process-seconds/1 GiB and native 14,400 seconds/
96 GiB. Conservative charges are source 3,500 seconds/704 MiB and native 11,000 seconds/
93 GiB, including the logical32 GiB ARM workspace and every prior attempt; no deletion
credits. Private native workspace has 8,468,197,376 bytes available after verified redundant-component retirement.
The PR39 execution ledger carries all continuations, failures and receipts.

Owner confirmed Funssor/CN3D bed, factory mainboard/toolhead/hotend, filament sensor
and exhaust fan matching saved hardware revision 13. Passive target preflight remains
release 0.1.0-physical-update.2, stable immutable slotB,32GB spare; candidate geometry
still fits factory capacity. No printer configuration/service/boot/output change,
MCU flashing, deployment or public binary release occurred.

**Next dependency:** identify the spare SD and removable backup drive and their
read-only identification location; keep the tested rescue SD unchanged. The
current recovery base is ready, but independent-SD target/owner admission policy
must bind actual media. Then finish that SD artifact and the existing commissioning
packet, obtain exact-operation authority/assessment and attendance, and qualify the
configured printer and candidate-specific update/recovery/peripheral boundaries.
Do not fast-forward the frozen native build checkout merely for evidence updates.

## Contract and next milestone

Use [the canonical release route](../docs/remaining-work-plan.md). Initial support is the actual test printer's fitted configuration, not assumed factory bed/hotend. LAN signed delivery suffices initially. Preserve immutable/writable modes, data/identity, safety/admission and independent recovery. System releases assign immutable definition-based MCU recommendations; older-system boot never reflashes, and observed mismatch/unknown is visible. Passive target preflight is recorded in the candidate execution ledger; recheck safety-relevant state before any physical operation.

Current milestone: finish identified independent-SD composition and prepare attended configured-printer commissioning; then complete remaining candidate-specific acceptance and publish the qualified release with source/notices. Current diagnostic and KVM images do not establish board release or printing acceptance. Required first physical action waits for exact configuration/target/recovery review and separate authority.

## Reuse

[PR17 native recovery](../docs/features/recovery-printer-stack/native-evidence.md), [H13 update/fallback](../docs/features/physical-automatic-update-validation/completion.md), [H12 SD reimage](../docs/features/h12-attended-sd-reimage/physical-completion.md), [configuration/calibration](../docs/features/stock-printer-readiness/evidence.md), [package reproduction](../docs/features/package-reproducibility-qualification/evidence.md), [notices](../docs/features/release-qualification-closure/evidence.md). Recheck affected inputs/assumptions, not everything after a docs commit. Historical counters/results remain at their original revisions.

## Goal prompt for the remaining milestone

> Deliver the first supported release for the actual configured test printer using docs/remaining-work-plan.md and the existing feature/H records. Implement the supported candidate/clean-owner/commissioning path in existing composition and runtime tools; preserve all mandatory requirements, working components, LAN trust and release-bound MCU definition policy with no automatic flashing on rollback. Reuse applicable evidence, freeze/build one source-bound factory-capacity candidate, and prepare the single commissioning session. Perform physical installation, flashing, outputs and destructive tests only with separate exact-operation authority/review; stop at the precise missing human action when necessary. Complete candidate-specific install/print/update/recovery/peripheral acceptance and publish installable artifacts with corresponding source, notices and recovery instructions only when authorised and qualified. Follow AGENTS.md for mechanics; no optional feature expansion or fabricated health/release markers. Finish at the supported public release, or preserve work and report the concrete blocker and next action.

## Authority and history

Source PR publication is not physical-operation or release-publication authority. The active native full-release goal and source feature-task have distinct completion criteria. Physical dependencies remain in [one H queue](../docs/hardware/coordinated-human-tasks.md). [Historical goal narratives](../docs/history/current-goals-through-20261116.md) are evidence, not current instructions.
