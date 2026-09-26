# Writerless eMMC reimage readiness

Date: 2026-09-26. Profile: `test-sv08-01`. This is an offline/read-only
readiness audit for the existing H12 commissioning task. It does not authorize
or perform an eMMC write.

## H12 prerequisites

| Prerequisite | Current evidence | Status and limit |
| --- | --- | --- |
| Full-image transfer prototype | The [QEMU report](host-sd-network-emmc-reimage-qemu.md) records a passing full source hash, write, flush, full readback, and GPT check to a disposable regular-file-backed virtual USB disk. | Met for synthetic QEMU only. It hard-codes `/dev/sda`, a test-only serial, 32,000,000,000-byte target, and a non-bootable fixture hash. It is not the printer writer. |
| Target admission | [H10](host-sd-network-emmc-probe-20260926.md) measured one `MMC` under the H616 `4022000.mmc` controller, `/dev/mmcblk0`, 61,079,552 sectors (31,272,730,624 bytes), and read both environment copies without writing. The [locator improvement](host-network-emmc-target-admission.md) now requires that exact capacity and refuses malformed or additional MMC inventory. | Offline admission checks are complete. H10 did not record the card CID. The returned path and capacity alone are not sufficient write identity. The v5 A-rearm record reports that a CID was captured privately, but the live card has not been compared with it for H12. |
| Candidate image | The [v5 artifact manifest](host-board-image-20260925-v5.json) records a 7,818,182,656-byte raw image, SHA-256 `ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`, and six partition image hashes. Its compressed file on Beelink was read-only checked on 2026-09-26: 1,050,437,428 bytes and SHA-256 `09fb7efb7637e3b360bbb6c76e5b2b3cf7e0164a69082122b18a05ac567d34a1`, matching the manifest. | Available for a writer-path commissioning test only. The v5 artifact is marked `deployable: false`; it is not a supported printer release. Do not describe the synthetic QEMU image as this candidate. |
| Image/target map | [`host-board-image.md`](host-board-image.md), [`test-sv08-01-host.json`](../../configs/images/test-sv08-01-host.json), the v5 manifest, and its [offline byte review](host-board-image-20260925-v5.md) bind the 8 GB image footprint, six partition identities, SPL at byte 8192, and redundant environment regions. The physical eMMC user area measured by H10 is larger at 31,272,730,624 bytes. | Reviewed for the USB-writer v5 operation and its prior complete readback. A fresh reviewer must bind the exact network-writer behavior, candidate hash, target size/identity, and policy. The GPT remains at the 8 GB image boundary by design; the unused eMMC tail is not expanded. |
| Spare contents and recovery | The owner confirmed that the spare is installed, the factory eMMC is stored, and the existing backups are acceptable. The v5 record documents a prior complete USB-writer readback. | Owner acceptance is recorded. No new backup is needed for this readiness audit. Keep the factory eMMC stored; retain the existing USB reader as a manual recovery fallback if the writerless test leaves an uncertain target. |
| Source independence and network path | The H09/H10 [SD/NFS diagnostic](host-sd-network-root-prototype.md) booted on the printer with DHCP and a read-only NFS root; the separate image source resides on Beelink. | Only the read-only diagnostic exists. It powers down after probing. It has no one-shot writer, job trigger, or production write path. |
| Capture and current access | Beelink SSH is reachable and has 10,782,371,840 bytes free on its capture filesystem; the compressed v5 source is present there. The printer CH340 adapter enumerates as `1a86:7523` at `/dev/ttyUSB0`. | Read-only checks from Beelink and this VM found no route to printer `192.168.1.141`; no current CID or boot state was captured. The SD/NFS prototype's prior physical trace is not a current capture. |
| Write authorization and review | The existing [H12 task](coordinated-human-tasks.md) defines exact artifact/target review, recovery, stop conditions, and a separate high-consequence review immediately before a physical write. | Not yet met for a network writer. This readiness report grants no hardware-write authority. |

The v5 documentation contains one stale sentence: its write/readback note says
the spare “has not yet been booted with v5,” while the later [v5 first-boot
record](host-board-image-20260925-v5-first-boot.md) and JSON manifest record an
A-slot boot. Use the later first-boot record for the observed boot and retain
the remaining physical exclusions; the wording is corrected in the write note.

## Next work and physical gate

The next implementation must connect the existing read-only H616 admission
helper to a separately reviewed, one-shot network writer; verify the exact
compressed and expanded candidate hashes, single target identity and capacity;
preserve the immutable source/target separation; flush and read back the whole
image; validate both GPT copies and all six partitions; and stop without retry
on interruption or uncertainty. It must not be placed into the diagnostic
image until that writer is independently reviewed. The live target identity
must be confirmed against the private CID evidence before any write.

The VM has only 4.5 GiB free, below the QEMU writer report's documented 9 GB
scratch minimum; do not stage a second raw image or virtual target there. On
Beelink the measured free space is above that minimum, but the 1.05 GB
compressed source is not a raw file and the candidate has not been exercised by
the synthetic QEMU harness. Recheck free space and enforce a bound before any
candidate-specific test or extraction; the logical 7.8 GB image extent alone
does not establish the physical scratch allocation.

H12 remains the one deduplicated physical commissioning task. Once the reviewed
writer and artifact are ready, the single supervised session must capture the
live CID before the write, then record the exact hash, target, progress, flush,
full readback, GPT/partition checks and resulting boot. Until that readiness
condition is met, no eMMC movement or write is requested.
