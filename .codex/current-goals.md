# Current subclient goals

Updated 2026-09-23. These are bounded assignments under the existing
[remaining-work plan](../docs/remaining-work-plan.md) and
[parallel delivery plan](../docs/development/parallel-work.md). The owner has
paused optional new features; these goals finish approved work and correct
existing records. A subclient goal is complete only when its stated evidence is
delivered. It does not certify a printer or a release.

| Goal | Role and model | Owned scope | Completion evidence | Physical dependency |
| --- | --- | --- | --- | --- |
| Reconcile recovery export record — done | `project_implementer`, GPT-6 Sol / medium, then separate `feature_verifier`, GPT-6 Sol / high | `docs/features/host-recovery-export-composition/record.json` and only the evidence bookkeeping needed to bind the merged implementation | Six schema-valid offline checks and independent verdict passed; `feature_workflow.py validate` and `next` succeeded at `db33359`. | H04/H07 remain open for physical UI, media and recovery tests. |
| Finish approved inactive printer interface configuration — done | `project_implementer`, GPT-6 Sol / medium, then separate verifier | Approved `printer-interface-config` scope: inactive include and focused tests | Five pinned Klipper tests, coordinator private overlay file-output check, and independent pc-01–pc-08 verdict passed at `72000d3`; no physical claim. | H01/H02/H05/H06 for identification, boot, inputs and attended outputs. |
| Compose approved boot health — next | `project_implementer`, GPT-6 Sol / medium, then separate verifier | Approved `host-boot-health-composition` coordinator, transaction admission, unit ordering and image enablement | Source-backed Luna handoff complete; implement approved hb checks, then prove trial/normal/writable behavior in offline tests and independent review. | H02/H07 for later board boot and fallback tests. |
| Prepare the next board artifact — research done | `project_researcher`, GPT-6 Luna / high | Read-only input receipt, capacity and resource audit | About 36 GiB free at audit; canonical v6 SPL, host, data and recovery inputs absent from expected paths. Compose only after reviewed exact inputs are selected; use inspect-only assembler first. | H03 only if a later reviewed image must be written through the reader; H02/H04 for boot and UI. |

Run at most one production implementer at a time. A verifier never reviews its
own implementation. Research can proceed while the implementation lease is held.
The coordinator alone assigns build and QEMU directories, operates the printer,
updates shared records, commits and pushes. No subclient asks the owner to repeat
a physical action. Add any physical need to the existing
[H01–H08 queue](../docs/hardware/coordinated-human-tasks.md), then combine ready
checks into one session. In particular, HDMI capture pending under H04 must not
hold the offline goals above.

The VM had about 36 GiB free at the board artifact audit on 2026-09-23.
Inventory old `build/` outputs before a factory-sized image or concurrent VM
run. Retain only accepted evidence; never remove another worker's fixtures.
The recovery record and inactive printer interface have passed independent
offline review. Neither result certifies physical board behavior.
