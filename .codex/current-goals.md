# Current delivery state

PR38 merged as `47e265e21b3382ddc921317097e53991fffd6035`. The native
first-supported-release goal is active; the existing
[supported candidate task](../docs/features/supported-release-candidate/proposal.md)
is running. The earlier recovery qualification remains complete at its recorded
scope. No physical deployment, MCU flashing or output operation occurred in this goal.

Draft [PR39](https://github.com/drew442/sv08-mainline/pull/39) contains the supported
candidate/clean-owner source path. All four CI workflows passed at3f86bd2;
subsequent source repair88fe387 and final branch CI require separate observation.
The actual native KVM factory and captured-hardware validators passed unchanged
production limits. The owner/PAM probe passed29 checks after one fixture-permissions
repair. [Native evidence](../docs/features/supported-release-candidate/native-evidence.json)
distinguishes real installed PAM in synthetic roots from normal boot/browser and
physical acceptance. Root source, six disposable mode/slot boots and800x480 rendered
owner checks also pass. This source/software checkpoint is not release completion.

Native work: `/run/a733-guests/sv08-release-20261117` on the existing ARM64/KVM
runner, private mounts/tools and a logical32GiB inode-rich workspace. Source
ceiling7,200process-seconds/1GiB, conservative charge2,500seconds/384MiB. Separate
native ceiling10,800seconds/72GiB after a recorded8GiB output continuation; conservative charge6,600seconds/62GiB including
logical container plus generated files and removed attempts. [Execution](../docs/features/supported-release-candidate/execution.json)
retains cumulative attempts. Bootstrap/security refresh and exact application,
Cockpit/RAUC and board-package checks passed. The revision4 six-partition candidate is assembled at the factory size; readback of all partitions/SPL/environments and the selected-software release gate pass. It is not physically booted or printing/release qualified.
Current normal-root finalization and provenance pass after the canonical certificate link fix. A distinct revision5 signed OTA payload is being prepared from unchanged source for the update/fallback campaign; no second whole normal disk is planned.

Owner confirmed the fitted Funssor/CN3D bed, factory mainboard/toolhead/hotend,
filament sensor and exhaust fan matching saved hardware revision13. Passive target
preflight: release0.1.0-physical-update.2, slotB, immutable, no trial; target32GB spare,
candidate revision4. Artifacts still must fit the factory7,818,182,656-byte layout.
Independent SD/backup-medium identities are requested for the final reviewed policy.
No physical configuration/service/boot/output change has occurred. Exact-operation
authority/review, recovery readiness and attendance remain required before changes.

## Contract and next milestone

Use [the canonical release route](../docs/remaining-work-plan.md). Initial support is the actual test printer's fitted configuration, not assumed factory bed/hotend. LAN signed delivery suffices initially. Preserve immutable/writable modes, data/identity, safety/admission and independent recovery. System releases assign immutable definition-based MCU recommendations; older-system boot never reflashes, and observed mismatch/unknown is visible. Passive target preflight is recorded in the candidate execution ledger; recheck safety-relevant state before any physical operation.

Current milestone: finish native candidate/clean-owner qualification and freeze/assemble one supported candidate; then execute attended configured-printer commissioning and remaining candidate-specific acceptance, and publish the qualified release with source/notices. Current diagnostic and KVM images do not establish board release or printing acceptance. Required first physical action waits for exact configuration/target/recovery review and separate authority.

## Reuse

[PR17 native recovery](../docs/features/recovery-printer-stack/native-evidence.md), [H13 update/fallback](../docs/features/physical-automatic-update-validation/completion.md), [H12 SD reimage](../docs/features/h12-attended-sd-reimage/physical-completion.md), [configuration/calibration](../docs/features/stock-printer-readiness/evidence.md), [package reproduction](../docs/features/package-reproducibility-qualification/evidence.md), [notices](../docs/features/release-qualification-closure/evidence.md). Recheck affected inputs/assumptions, not everything after a docs commit. Historical counters/results remain at their original revisions.

## Goal prompt for the remaining milestone

> Deliver the first supported release for the actual configured test printer using docs/remaining-work-plan.md and the existing feature/H records. Implement the supported candidate/clean-owner/commissioning path in existing composition and runtime tools; preserve all mandatory requirements, working components, LAN trust and release-bound MCU definition policy with no automatic flashing on rollback. Reuse applicable evidence, freeze/build one source-bound factory-capacity candidate, and prepare the single commissioning session. Perform physical installation, flashing, outputs and destructive tests only with separate exact-operation authority/review; stop at the precise missing human action when necessary. Complete candidate-specific install/print/update/recovery/peripheral acceptance and publish installable artifacts with corresponding source, notices and recovery instructions only when authorised and qualified. Follow AGENTS.md for mechanics; no optional feature expansion or fabricated health/release markers. Finish at the supported public release, or preserve work and report the concrete blocker and next action.

## Authority and history

Source PR publication is not physical-operation or release-publication authority. The active native full-release goal and running source feature-task have distinct completion criteria. Physical dependencies remain in [one H queue](../docs/hardware/coordinated-human-tasks.md). [Historical goal narratives](../docs/history/current-goals-through-20261116.md) are evidence, not current instructions.
