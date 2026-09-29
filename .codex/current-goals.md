# Current subclient goals

Updated 2026-09-29. These are bounded assignments under the existing
[remaining-work plan](../docs/remaining-work-plan.md) and
[parallel delivery plan](../docs/development/parallel-work.md). The owner has
paused optional new features, but explicitly authorized the active goal to
finish a safe writerless eMMC reimage path and, on September 29, a running SD
recovery interface with SSH to replace the finite diagnostic. The work below advances that goal;
other optional features remain paused. A goal is complete only when its stated
evidence is delivered. It does not certify a printer or a release.

| Goal | Role and model | Owned scope | Completion evidence | Physical dependency |
| --- | --- | --- | --- | --- |
| Running SD recovery host-test — host-only physical boot passed | One project implementer on GPT-6 Sol/medium, separate feature approver and verifier, coordinator for artifacts/media | Explicit separately named SD composition of existing recovery userspace, pinned kernel/loader, wired DHCP and public-key SSH; readonly root/volatile runtime, no automatic eMMC/MCU/boot-policy or printer activity | [Approved scope](../docs/features/sd-recovery-host-test/proposal.md); complete userspace VM must keep normal init, GTK and authenticated SSH running, test restart/unauthorized access and root/hash refusal; exact artifact and source inventories | SanDisk is installed and host is running from SD; [H13 physical result](../docs/hardware/host-sd-recovery-host-first-boot-20260929.md) confirms GTK/native HDMI/SSH and read-only spare intake. Keep USB/Ethernet connected and PSU off; no further media move requested. Touch and printer outputs remain pending. |
| Writerless full-eMMC reimage — in progress | Coordinator, with separate feature approval and delivery verification for substantive implementation | Select and compose one authenticated writer boot route (SD-resident initramfs or kexec from the running host), then integrate the H616 writer, exact v5 source and one-shot claim path without changing the default read-only diagnostic | Current read-only audit reconfirmed the compressed v5 input and streamed raw hash on Beelink. H616 adapter/descriptor admission and signed one-shot receipt pass synthetic QEMU. The pending boot proposal is paired with a [kexec route assessment](../docs/hardware/host-network-emmc-kexec-assessment-20260927.md): the v5 6.18 kernel has kexec disabled; no H616 kexec handoff is tested. Independent feature approval is required before behavioral implementation. | The installed spare has current CID/controller/GPT/environment and read-only p5 measurements. Existing trusted initramfs writer and p5 handoff passed offline review, but current SD-only U-Boot cannot select eMMC. Prepare a bounded remotely managed boot route and required stager tools, then independently review exact SD/eMMC artifacts and operations. No repeat SD move or USB writer request. Factory eMMC stored; all physical eMMC/boot-policy gates remain open. |
| Reconcile recovery export record — done | `project_implementer`, GPT-6 Sol / medium, then separate `feature_verifier`, GPT-6 Sol / high | `docs/features/host-recovery-export-composition/record.json` and only the evidence bookkeeping needed to bind the merged implementation | Six schema-valid offline checks and independent verdict passed; `feature_workflow.py validate` and `next` succeeded at `db33359`. | H04/H07 remain open for physical UI, media and recovery tests. |
| Finish approved inactive printer interface configuration — done | `project_implementer`, GPT-6 Sol / medium, then separate verifier | Approved `printer-interface-config` scope: inactive include and focused tests | Five pinned Klipper tests, coordinator private overlay file-output check, and independent pc-01–pc-08 verdict passed at `72000d3`; no physical claim. | H01/H02/H05/H06 for identification, boot, inputs and attended outputs. |
| Compose approved boot health — done | `project_implementer`, GPT-6 Sol / medium, separate `project_integration`, and independent verifier | Approved `host-boot-health-composition` coordinator, transaction admission, unit ordering and image enablement | All 12 offline checks passed independent review at `316be5f`: 59 focused tests and clean-source disposable QEMU A→B/A fallback. The harness selected roots and seeded a staged transaction; signed install and U-Boot attempt decrement remain untested. | H02/H07 for later board boot and fallback tests. |
| Prepare the next board artifact — research done | `project_researcher`, GPT-6 Luna / high | Read-only input receipt, capacity and resource audit | Identified the exact v6 SPL and retained reviewed host/data/recovery inputs on Beelink; the resulting candidate is recorded below. | H03 for writer access; H02/H04 for boot and UI. |
| Compose and write v3 board diagnostic candidate — physical A boot observed | Coordinator with independent Sol offline byte review | Reviewed v3 composition and spare writer transfer | Complete image readback matched SHA-256 `d6dde04282cf33908a7d3f051faefbb4b027c4348b41f2beb311320b778d5d56`; [physical A boot, HDMI/KVM login and temporary Wi-Fi](../docs/hardware/host-board-v3-first-boot.md) are recorded. | Corrected image needed for persistent Wi-Fi and diagnostic boot-health; one A boot attempt remained at last read. H04 touch, H07 and output gates remain open. |
| Complete approved disposable SD/NFS diagnostic — **done 2026-09-26** | Coordinator with independent artifact reviewer | Existing SD-to-Linux-to-read-only-NFS path plus bounded H10 probe correction | Reviewed supervised boot passed DHCP, read-only NFS root checks, and both read-only U-Boot environment CRC/layout checks on installed spare eMMC. Exact measurements and private capture hash are in [H10 record](../docs/hardware/host-sd-network-emmc-probe-20260926.md). | H10 is complete; no repeated network boot or media write planned. This does not validate boot policy or printer functions. |

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

`feature_workflow.py next` returns `null` while its single approved implementation
lease is active; this is not a reason to stop authorized coordination. The earlier sandbox deferral is historical; the trusted writer and p5 handoff
now have accepted offline evidence. The running-SD boot route has an [approved bounded proposal](../docs/features/sd-managed-boot-route/proposal.md).
Main-loader assembly/component preservation, focused capture refusal checks and
ARM64/QMP success-only reboot proof passed independent verification; the bounded
implementation is complete. A separately reviewed SD transfer passed exact
readback and full FAT/root/GPT preservation. The subsequent warm return probe
failed because the coordinator used a refused serial symlink and proceeded
without controller readiness. The host reached original recovery; current SSH,
environment and RTC retention are not established. See the
[measured transfer and failed probe](../docs/hardware/host-managed-sd-transfer-20260929.md).
Correct concrete UART admission, transient collector recreation and a separately
reviewed recovery action are next; do not retry blindly or arm a writer.
Exact full-loader inspection found missing CMD_HASH and CRC32_VERIFY, so the
proposal now preserves the proven SPL and adds only required main-loader
commands. The [hardware RTC correction and readback](../docs/hardware/host-rtc-preparation-20260929.md)
passed separate review/execution. Warm-reboot retention still needs checking
before a signed job. The delivery changes `finish` only for verified handoff
PASS to request reboot; QMP reset/shutdown proof passed. Existing bulk/QEMU
second-boot evidence remains distinct from pending automatic H616 return. Do not arm a
physical whole-device write while that unattended return gap remains. H10's single
reviewed retry passed on 2026-09-26. The spare eMMC appeared as
`/dev/mmcblk0`; both U-Boot environment copies passed CRC/layout checks and the
SD/NFS read-only checks passed. The probe shut down the host. See the H10 record;
no repeat boot is planned. H10 evidence does not validate A/B activation, normal
OS operation or printer functions.


Latest H12 observation, 2026-09-29: the [stopped-prompt correction](../docs/hardware/host-stopped-prompt-resume.md)
passed independent offline verification and its reviewed continuation verified
SD identity/script hash before sourcing. The SD SSH service responds and KVM
shows recovery at1024x600. A temporary coordinator supervisor failed a malformed
nonce, so early boot/fresh SSH-key fingerprint capture was missed; the capped
receive-only collector was restored manually. Initial key enrollment awaits a
single owner decision under H12; do not bypass console-fingerprint admission or
prepare actual jobs before fresh environment/RTC inspection. The
[nonwriting physical preflight proposal](../docs/features/h616-physical-preflight/proposal.md)
addresses the remaining urh-04 gap. Neither SD GUI nor offline code completes
urh-04/05 or the writerless goal. No additional media move is requested.
