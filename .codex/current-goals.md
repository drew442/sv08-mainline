# Current delivery state

PR38 is merged. Native goal active: deliver the first supported release for the actual configured test printer, through installation, commissioning/printing, LAN update/recovery and qualified artifact/source/notice publication. The source-overhaul goal is complete; this full release goal is not.

## Current phase

[supported-release-candidate](../docs/features/supported-release-candidate/proposal.md): source/candidate path and clean-owner setup, claimed in `local/feature-workflow/worktrees/supported-release-candidate`, branch `feature/supported-release-candidate`, base f854623. Main/record ownership remains coordinator-only. [Intake](../docs/features/supported-release-candidate/intake.json) records relevant hashes, source allowance, assignments and prerequisite observations. No new build or physical operation yet.

Owner implementation: existing recovery GTK reviewed enrollment/explicit password reset and persistent normal PAM identity. Supported composition will extend existing integration/assembly with exact measured target policy; retain diagnostic entry points and real OS health. Physical services remain explicitly gated. No automatic MCU flashing.

Source allowance 7,200 cumulative process-seconds / 1 GiB, including owner implementation ceiling 3,000 seconds / 384 MiB. Full-image work is excluded locally (9.6 GiB free). ARM64 host has 196 GiB free but only 15,136 free inodes; native/image work needs its own bounded allocation and private inode-rich filesystem. No earlier attempts are reset.

## Remaining release route

Follow [the canonical contract](../docs/remaining-work-plan.md). Finish source checks and rendered owner setup; freeze one source-bound factory-capacity candidate; qualify changed installation/authentication/activation boundaries natively; prepare exact attended [commissioning session](../docs/hardware/test-sv08-01-commissioning-session.md); obtain separate current-target/recovery authority and consequential review before physical operations. Then execute configured-printer commissioning/printing, peripherals, candidate-specific update/recovery and publication acceptance. Missing physical observations are dependencies, not fabricated software passes.

## Reuse and limits

[PR17 native recovery](../docs/features/recovery-printer-stack/native-evidence.md), [H13 update/fallback](../docs/features/physical-automatic-update-validation/completion.md), [H12 SD reimage](../docs/features/h12-attended-sd-reimage/physical-completion.md), [configuration/calibration](../docs/features/stock-printer-readiness/evidence.md), [package reproduction](../docs/features/package-reproducibility-qualification/evidence.md), [notices](../docs/features/release-qualification-closure/evidence.md). Recheck affected inputs/assumptions; preserve original counters, failures and hashes. Native prior recovery success is not board or printing acceptance.

## Authority

Source/disposable work and publication follow [the recorded request](../docs/features/supported-release-candidate/owner-request.md). Exact physical operations remain separately authorised/reviewed. All physical dependencies stay in [the single H queue](../docs/hardware/coordinated-human-tasks.md). No printer access, deployment, flashing, heater or motion operation has occurred in this goal.
