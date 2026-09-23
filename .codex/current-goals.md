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
| Compose approved boot health — done | `project_implementer`, GPT-6 Sol / medium, separate `project_integration`, and independent verifier | Approved `host-boot-health-composition` coordinator, transaction admission, unit ordering and image enablement | All 12 offline checks passed independent review at `316be5f`: 59 focused tests and clean-source disposable QEMU A→B/A fallback. The harness selected roots and seeded a staged transaction; signed install and U-Boot attempt decrement remain untested. | H02/H07 for later board boot and fallback tests. |
| Prepare the next board artifact — research done | `project_researcher`, GPT-6 Luna / high | Read-only input receipt, capacity and resource audit | About 36 GiB free at audit; canonical v6 SPL, host, data and recovery inputs absent from expected paths. Compose only after reviewed exact inputs are selected; use inspect-only assembler first. | H03 only if a later reviewed image must be written through the reader; H02/H04 for boot and UI. |
| Reconstruct reviewed board-image inputs — in progress | `project_researcher`, GPT-6 Luna / high, then coordinator-controlled private transfer and one Sol implementer for a bounded offline refresh | Existing host-image build receipts and assembly paths; ignored staging only | Research identified the exact v6 SPL and Beelink's retained v2 host/data/recovery input directories. The coordinator copied the v6 SPL to ignored `build/board-inputs/u-boot-sunxi-with-spl.bin` and verified its 786,105 bytes and SHA-256 `166b4251ffb3c2db6d3b90536650c399b3e5443b06e5c78a0ad2f8ca9fbf6b40`. Next: preserve and verify the retained trees/receipts, refresh the host from current source into a new directory, then run the inspect-only composer. | H03 only when a later reviewed write is ready; H02/H04 for installed boot and display. |

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
The recovery record, inactive printer interface and boot-health composition
have passed independent offline review. None certifies physical board behavior.
