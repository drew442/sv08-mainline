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
| Complete approved disposable SD/NFS diagnostic — base path passed; H10 follow-up active | Coordinator with independent artifact reviewer | Existing SD-to-Linux-to-read-only-NFS path plus the bounded H10 probe correction | The SD image passed physical write/readback and booted Linux with wired DHCP. The 2026-09-26 H10 attempt then failed before probe execution because NFSv3 mount requests were refused; the receive-only trace also shows `mmc0` non-removable-card initialization failure and the disposable SD as `mmc2`. No current eMMC counter was read. See [H10 record](../docs/hardware/host-sd-network-emmc-probe-20260926.md). | H10 follow-up: finish default NFSv3 and expected `.141` export verification, refresh served init hash/manifest, obtain fresh independent Sol high-consequence review, then one supervised attempt. Spare eMMC remains installed; factory eMMC remains stored. |

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

`feature_workflow.py next` returns `null`; optional features remain paused. H10's
first supervised attempt failed before the probe due NFS mountd registration;
current eMMC counters remain unknown. The spare eMMC is installed and the printer
is halted with receive-only serial capture available on Beelink. The bounded
probe correction is approved with constraints; offline NFS/default-port and
`.141` export and refreshed manifest checks pass. A fresh Sol high-consequence
review approved exactly one further read-only boot with conditions. Immediately
recheck NFS registration/export/hash and arm receive-only capture; the owner then
unplugs and reconnects USB serial once to reset the halted host. If MMC
initialization still fails, stop network probing and use the USB-reader path.
