# Current delivery state

## Current continuation — new SD and eMMC topology repair

Owner supplied a new blank SC16G SD (15,931,539,456 bytes), identified read-only
on Beelink as `/dev/mmcblk0`; it is unmounted with no holders and has not been
written. The separate backup drive is still requested. Current recovery requires
backup, SD root and eMMC target to be distinct physical disks.

Actual read-only invocation of the unchanged installed media inventory reader
failed on `mmcblk2boot0`. The eMMC exposes boot0/boot1 as readonly 4MiB hardware
areas, not independently identified user disks. Reopen the existing source task
for protected, nonselectable auxiliary topology; retain alias, holder, mount,
read-only and complete-inventory protections. Source/native passes below remain
historical at their stated inputs; DD65 images are not deployment candidates.
No card, eMMC, MCU, service or printer-output changes have occurred.

The SD root and loader source/TF-A preparation exist, but final SD composition
waits for repaired source and actual backup-media policy. Reuse cached packages
and the recorded normal/recovery roots; no unchanged OS bootstrap. Source ceiling
stays7,200seconds/1GiB. Native ceiling is now18,000process-seconds/124GiB after a
bounded continuation for this demonstrated repair and affected artifact refresh;
conservative prior charges11,800seconds/96GiB include all prior attempts, inputs
and the logical32GiB workspace, with no deletion credit. The existing execution
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
