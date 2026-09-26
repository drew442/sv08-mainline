# Current subclient goals

Updated 2026-09-26. These are bounded assignments under the existing
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
| Prepare the next board artifact — research done | `project_researcher`, GPT-6 Luna / high | Read-only input receipt, capacity and resource audit | Identified the exact v6 SPL and retained reviewed host/data/recovery inputs on Beelink; the resulting candidate is recorded below. | H03 for writer access; H02/H04 for boot and UI. |
| Compose and write v3 board diagnostic candidate — physical A boot observed | Coordinator with independent Sol offline byte review | Reviewed v3 composition and spare writer transfer | Complete image readback matched SHA-256 `d6dde04282cf33908a7d3f051faefbb4b027c4348b41f2beb311320b778d5d56`; [physical A boot, HDMI/KVM login and temporary Wi-Fi](../docs/hardware/host-board-v3-first-boot.md) are recorded. | Corrected image needed for persistent Wi-Fi and diagnostic boot-health; one A boot attempt remained at last read. H04 touch, H07 and output gates remain open. |
| Complete approved disposable SD/NFS diagnostic — done 2026-09-26 | Coordinator with independent artifact reviewer | Approved `host-sd-network-root` scope and one supervised physical retry | Corrected hash-verifying image passed review and direct write/readback; printer booted SD→Linux→wired DHCP→read-only NFS root and powered down on the exact pass marker. [Result](../docs/hardware/host-sd-network-first-boot-20260926.md), commits `8d964e8`–`fe39756` pushed. | H10 remains open. The owner reports the spare eMMC is currently removed, so the network probe requires its reinstallation; no current counter is assumed. Candidate adds PC3 selection for Linux and requires a separately reviewed SD reflash. |

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

`feature_workflow.py next` currently returns `null`; optional features remain
paused. The next physical dependency is H10: the reviewed image and updated NFS probe
are ready, and Beelink's restricted read-only export is verified. The disposable
SD is written and direct-I/O readback matches. The owner now needs to reinstall
the spare eMMC plus SD with the printer fully off (factory module stays stored),
stand it upright, and reconnect Ethernet. Arm receive-only serial capture before
the USB cable is reconnected, then run one read-only probe boot.
Continue offline checklist preparation while waiting.
