# Current delivery state

PR38 merged as `47e265e21b3382ddc921317097e53991fffd6035`. The native
first-supported-release goal is active; the existing
[supported candidate task](../docs/features/supported-release-candidate/proposal.md)
is running. The earlier recovery qualification remains complete at its recorded
scope. No physical deployment, MCU flashing or output operation occurred in this goal.

Draft [PR39](https://github.com/drew442/sv08-mainline/pull/39) contains the supported
candidate/clean-owner path. Current claimed worktree:
`local/feature-workflow/worktrees/supported-release-boot-fix`, branch
`feature/supported-release-boot-fix`; prior integration worktree/tips remain intact.
The native full-release goal is active; source and hardware acceptance stay separate.

The66dce8d prototype normal/recovery images and signed revision5 OTA passed their
construction, byte-readback, trusted-signature, payload-hash and selected-software
source/notice checks. Native factory/selected hardware validators and29 owner/PAM
checks passed at their recorded inputs. These prototypes are **not for deployment**:
source tracing found missing commissioned reboot startup and stale post-confirmation
trial metadata. All receipts, failures and source identities are preserved.

Both lifecycle defects have source repairs. Supported boot activation checks the
existing persistent permission after real health; Klipper keeps its own guards.
Confirmation atomically publishes normal boot metadata before releasing trial/ready
gates.49 focused tests pass, plus62 related passes/one opt-in namespace skip.
Next: native STUB unit-contract evidence, freeze repaired source and refresh affected
normal/recovery/update outputs; never relabel old prototype proof as new-source proof.
Actual installed fresh boot/browser/physical printing and release acceptance remain.

[Execution](../docs/features/supported-release-candidate/execution.json): source
ceiling7,200process-seconds/1GiB, conservative charge3,000seconds/640MiB. Native
ceiling14,400seconds/96GiB after recorded continuations, with all prior charges and
attempts carried forward; includes the logical32GiB private ARM workspace. Preserve
one verified compressed prototype archive, not redundant historical raw components.

Owner confirmed Funssor/CN3D bed, factory mainboard/toolhead/hotend, filament sensor
and exhaust fan matching saved hardware revision13. Target passive preflight remains
release0.1.0-physical-update.2, stable immutable slotB,32GB spare; artifacts must fit
factory7,818,182,656bytes. Independent SD/backup media identities are requested.
No printer configuration/service/boot/output change occurred. Exact-operation
review/authority, usable recovery and attendance precede physical work.

## Contract and next milestone

Use [the canonical release route](../docs/remaining-work-plan.md). Initial support is the actual test printer's fitted configuration, not assumed factory bed/hotend. LAN signed delivery suffices initially. Preserve immutable/writable modes, data/identity, safety/admission and independent recovery. System releases assign immutable definition-based MCU recommendations; older-system boot never reflashes, and observed mismatch/unknown is visible. Passive target preflight is recorded in the candidate execution ledger; recheck safety-relevant state before any physical operation.

Current milestone: finish native candidate/clean-owner qualification and freeze/assemble one supported candidate; then execute attended configured-printer commissioning and remaining candidate-specific acceptance, and publish the qualified release with source/notices. Current diagnostic and KVM images do not establish board release or printing acceptance. Required first physical action waits for exact configuration/target/recovery review and separate authority.

## Reuse

[PR17 native recovery](../docs/features/recovery-printer-stack/native-evidence.md), [H13 update/fallback](../docs/features/physical-automatic-update-validation/completion.md), [H12 SD reimage](../docs/features/h12-attended-sd-reimage/physical-completion.md), [configuration/calibration](../docs/features/stock-printer-readiness/evidence.md), [package reproduction](../docs/features/package-reproducibility-qualification/evidence.md), [notices](../docs/features/release-qualification-closure/evidence.md). Recheck affected inputs/assumptions, not everything after a docs commit. Historical counters/results remain at their original revisions.

## Goal prompt for the remaining milestone

> Deliver the first supported release for the actual configured test printer using docs/remaining-work-plan.md and the existing feature/H records. Implement the supported candidate/clean-owner/commissioning path in existing composition and runtime tools; preserve all mandatory requirements, working components, LAN trust and release-bound MCU definition policy with no automatic flashing on rollback. Reuse applicable evidence, freeze/build one source-bound factory-capacity candidate, and prepare the single commissioning session. Perform physical installation, flashing, outputs and destructive tests only with separate exact-operation authority/review; stop at the precise missing human action when necessary. Complete candidate-specific install/print/update/recovery/peripheral acceptance and publish installable artifacts with corresponding source, notices and recovery instructions only when authorised and qualified. Follow AGENTS.md for mechanics; no optional feature expansion or fabricated health/release markers. Finish at the supported public release, or preserve work and report the concrete blocker and next action.

## Authority and history

Source PR publication is not physical-operation or release-publication authority. The active native full-release goal and running source feature-task have distinct completion criteria. Physical dependencies remain in [one H queue](../docs/hardware/coordinated-human-tasks.md). [Historical goal narratives](../docs/history/current-goals-through-20261116.md) are evidence, not current instructions.
