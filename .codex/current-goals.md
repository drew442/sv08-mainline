# Current delivery state

PR38 merged as `47e265e21b3382ddc921317097e53991fffd6035`. The native
first-supported-release goal is active; the existing
[supported candidate task](../docs/features/supported-release-candidate/proposal.md)
is running. The earlier recovery qualification remains complete at its recorded
scope. No physical deployment, MCU flashing or output operation occurred in this goal.

Draft [PR39](https://github.com/drew442/sv08-mainline/pull/39) publishes the supported
candidate/clean-owner source checkpoint at
`3f86bd2ea82ea173d25bc9a1cb0e9282b02224b4`. All four applicable CI workflows pass at
that exact source. Root source checks, six disposable mode/slot boots and rendered
800x480 owner interaction checks pass; installed native PAM and supported board
artifacts remain to qualify. These are source/software results, not printing or
release acceptance. The full native goal is not complete at this PR checkpoint.

Native work is assigned to `/run/a733-guests/sv08-release-20261117` on the existing
ARM64/KVM runner, with a private inode-rich workspace and extracted tools. The
separate allowance is 10,800 process-seconds /64GiB generated, including the logical
32GiB workspace; source work retains its 7,200seconds /1GiB cumulative allowance.
[The execution ledger](https://github.com/drew442/sv08-mainline/blob/3f86bd2ea82ea173d25bc9a1cb0e9282b02224b4/docs/features/supported-release-candidate/execution.json)
retains prior charges and attempts. A fresh normal baseline is in progress; the
first attempt's missing private wget prerequisite was corrected without a host
installation and its failed log retained. Actual validator/owner integration
precedes expensive final assembly. No TCG substitution or simulated native pass.

Read-only target preflight found saved hardware revision13 selecting a Funssor/CN3D
bed. Fitted-hardware confirmation is pending; saved selections are not physical
proof. The target remains on release0.1.0-physical-update.2, slotB, immutable. Exact
physical-operation authority/review, recovery readiness and attendance remain
required before changing the printer.

## Contract and next milestone

Use [the canonical release route](../docs/remaining-work-plan.md). Initial support is the actual test printer's fitted configuration, not assumed factory bed/hotend. LAN signed delivery suffices initially. Preserve immutable/writable modes, data/identity, safety/admission and independent recovery. System releases assign immutable definition-based MCU recommendations; older-system boot never reflashes, and observed mismatch/unknown is visible. Passive target preflight is recorded in the candidate execution ledger; recheck safety-relevant state before any physical operation.

Current milestone: finish native candidate/clean-owner qualification and freeze/assemble one supported candidate; then execute attended configured-printer commissioning and remaining candidate-specific acceptance, and publish the qualified release with source/notices. Current diagnostic and KVM images do not establish board release or printing acceptance. Required first physical action waits for exact configuration/target/recovery review and separate authority.

## Reuse

[PR17 native recovery](../docs/features/recovery-printer-stack/native-evidence.md), [H13 update/fallback](../docs/features/physical-automatic-update-validation/completion.md), [H12 SD reimage](../docs/features/h12-attended-sd-reimage/physical-completion.md), [configuration/calibration](../docs/features/stock-printer-readiness/evidence.md), [package reproduction](../docs/features/package-reproducibility-qualification/evidence.md), [notices](../docs/features/release-qualification-closure/evidence.md). Recheck affected inputs/assumptions, not everything after a docs commit. Historical counters/results remain at their original revisions.

## Goal prompt for the remaining milestone

> Deliver the first supported release for the actual configured test printer using docs/remaining-work-plan.md and the existing feature/H records. Implement the supported candidate/clean-owner/commissioning path in existing composition and runtime tools; preserve all mandatory requirements, working components, LAN trust and release-bound MCU definition policy with no automatic flashing on rollback. Reuse applicable evidence, freeze/build one source-bound factory-capacity candidate, and prepare the single commissioning session. Perform physical installation, flashing, outputs and destructive tests only with separate exact-operation authority/review; stop at the precise missing human action when necessary. Complete candidate-specific install/print/update/recovery/peripheral acceptance and publish installable artifacts with corresponding source, notices and recovery instructions only when authorised and qualified. Follow AGENTS.md for mechanics; no optional feature expansion or fabricated health/release markers. Finish at the supported public release, or preserve work and report the concrete blocker and next action.

## Authority and history

Source PR publication is not physical-operation or release-publication authority. The active native full-release goal and running source feature-task have distinct completion criteria. Physical dependencies remain in [one H queue](../docs/hardware/coordinated-human-tasks.md). [Historical goal narratives](../docs/history/current-goals-through-20261116.md) are evidence, not current instructions.
