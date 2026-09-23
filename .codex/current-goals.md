# Current subclient goals

Updated 2026-09-23. These are bounded assignments under the existing
[remaining-work plan](../docs/remaining-work-plan.md) and
[parallel delivery plan](../docs/development/parallel-work.md). The owner has
paused optional new features; these goals finish approved work and correct
existing records. A subclient goal is complete only when its stated evidence is
delivered. It does not certify a printer or a release.

| Goal | Role and model | Owned scope | Completion evidence | Physical dependency |
| --- | --- | --- | --- | --- |
| Reconcile recovery export record | `project_implementer`, GPT-6 Sol / medium, then separate `feature_verifier`, GPT-6 Sol / high | `docs/features/host-recovery-export-composition/record.json` and only the evidence bookkeeping needed to bind the merged implementation | Six schema-valid offline check records at the committed source revision; independent verdict; `feature_workflow.py validate` and `next` succeed. Reuse the already passing VM artifacts and record their actual hashes. | H04/H07 remain open for physical UI, media and recovery tests. |
| Finish approved inactive printer interface configuration | `project_implementer`, GPT-6 Sol / medium, then separate verifier | Approved `printer-interface-config` scope: inactive include and focused tests, with exact file ownership assigned in the handoff | Pinned Klipper file-output tests of print/pause/resume/cancel and responses; no guessed pins or heater constants; private overlay evidence supplied by the coordinator where required. | H01/H02/H05/H06 for identification, boot, inputs and attended outputs. |
| Prepare approved boot-health composition | `project_researcher`, GPT-6 Luna / high, then one implementer when the printer slice releases the implementation lease | Read-only source-backed handoff for `host-boot-health-composition` | Exact service/transaction paths, acceptance checks, current tests and one minimal implementation slice; no automatic mark-good assumption. | H02/H07 for later board boot and fallback tests. |
| Prepare the next board artifact | `project_researcher`, GPT-6 Luna / high | Read-only input receipt, capacity and resource audit | One reviewable build-input matrix with exact source hashes, missing inputs, available disk and the smallest dry-run command; no duplicate full image. | H03 only if a later reviewed image must be written through the reader; H02/H04 for boot and UI. |

Run at most one production implementer at a time. A verifier never reviews its
own implementation. Research can proceed while the implementation lease is held.
The coordinator alone assigns build and QEMU directories, operates the printer,
updates shared records, commits and pushes. No subclient asks the owner to repeat
a physical action. Add any physical need to the existing
[H01–H08 queue](../docs/hardware/coordinated-human-tasks.md), then combine ready
checks into one session. In particular, HDMI capture pending under H04 must not
hold the offline goals above.

The VM had 37 GiB free on 2026-09-23. Inventory old `build/` outputs before a
factory-sized image or concurrent VM run. Retain only accepted evidence; never
remove another worker's fixtures. The recovery composition passed independent
offline review at source commit `49c7494` and was merged at `cd1bb66`; its
durable feature record still needs reconciliation before the workflow queue can
advance.
