# Writerless eMMC reimage readiness

Original audit: 2026-09-26. Read-only recheck: 2026-09-27. Profile:
`test-sv08-01`. This is a readiness audit for the existing H12 commissioning
task. The recheck accessed Beelink only; it did not boot the printer or authorize
or perform an eMMC write.

## H12 prerequisites

| Prerequisite | Current evidence | Status and limit |
| --- | --- | --- |
| Full-image transfer and H616 adapter | The [H616 adapter report](host-network-emmc-h616-adapter-offline-20260926.md) records the explicit H616 writer branch, local CID/controller/type/capacity/dev_t admission bound to one open descriptor, full write/flush/readback, and synthetic QEMU fault matrix. The [authenticated-claim report](host-network-emmc-authenticated-claim-qemu-20260927.md) adds challenge-bound receipts and records the exact v5 image map. | Implemented and independently reviewed for offline/synthetic use. The candidate builder still reports `bootable_sd_image: false` and `claim_trigger_provisioned: false`; no bootable writer artifact or production claim service exists. Do not equate QEMU H616-shaped inventory with the printer's live MMC mapping. |
| Target admission | [H10](host-sd-network-emmc-probe-20260926.md) measured one `MMC` under the H616 `4022000.mmc` controller, `/dev/mmcblk0`, 61,079,552 sectors (31,272,730,624 bytes), and read both environment copies without writing. The [locator improvement](host-network-emmc-target-admission.md) now requires that exact capacity and refuses malformed or additional MMC inventory. | Offline admission checks are complete. H10 did not record the card CID. The returned path and capacity alone are not sufficient write identity. The v5 A-rearm record reports that a CID was captured privately, but the live card has not been compared with it for H12. |
| Candidate image | The [v5 artifact manifest](host-board-image-20260925-v5.json) records a 7,818,182,656-byte raw image, SHA-256 `ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`, and six partition image hashes. On 2026-09-27, Beelink's 1,050,437,428-byte compressed source again matched SHA-256 `09fb7efb7637e3b360bbb6c76e5b2b3cf7e0164a69082122b18a05ac567d34a1`; streaming decompression produced the manifest's raw SHA-256 without staging an uncompressed copy. | Available for a commissioning test only. The v5 artifact is marked `deployable: false`; it is not a supported printer release. Do not describe the synthetic QEMU image as this candidate. |
| Image/target map | [`host-board-image.md`](host-board-image.md), [`test-sv08-01-host.json`](../../configs/images/test-sv08-01-host.json), the v5 manifest, and its [offline byte review](host-board-image-20260925-v5.md) bind the 8 GB image footprint, six partition identities, SPL at byte 8192, and redundant environment regions. The physical eMMC user area measured by H10 is larger at 31,272,730,624 bytes. | Reviewed for the USB-writer v5 operation and its prior complete readback. A fresh reviewer must bind the exact network-writer behavior, candidate hash, target size/identity, and policy. The GPT remains at the 8 GB image boundary by design; the unused eMMC tail is not expanded. |
| Spare contents and recovery | The owner confirmed that the spare is installed, the factory eMMC is stored, and the existing backups are acceptable. The v5 record documents a prior complete USB-writer readback. | Owner acceptance is recorded. No new backup is needed for this readiness audit. Keep the factory eMMC stored; retain the existing USB reader as a manual recovery fallback if the writerless test leaves an uncertain target. |
| Source independence and network path | The H09/H10 [SD/NFS diagnostic](host-sd-network-root-prototype.md) booted on the printer with DHCP and a read-only NFS root; the exact v5 compressed source remains on Beelink. | The production SD builder still emits only the read-only diagnostic. Its initramfs verifies the kernel/initramfs/DTB from SD, then executes `/sd-network-init` from NFS. The H616 writer must not be made runnable through this unauthenticated NFS-root executable path: a substituted NFS init could bypass every check inside the reviewed writer. The trusted writer and target policy must be authenticated by the SD-resident verified boot chain before execution; NFS should provide only the read-only image source. |
| Capture and current access | Read-only SSH recheck on 2026-09-27 found Beelink at `192.168.1.136`, 10,698,133,504 bytes free, and the exact compressed v5 source. The NFS-Ganesha and rpcbind services were inactive at the time of the check. | No live printer CID/dev_t comparison or current boot capture was performed. NFS service availability must be checked and deliberately prepared before any boot; prior H09/H10 traces do not establish current reachability or target identity. |
| Write authorization and review | The existing [H12 task](coordinated-human-tasks.md) defines exact artifact/target review, recovery, stop conditions, and a separate high-consequence review immediately before a physical write. | Not met. The offline adapter and claim reviews do not verify the physical initrd/U-Boot trust chain, Beelink claim-service operation, live CID/dev_t binding, or exact physical write artifact. This report grants no hardware-write authority. |

The v5 documentation contains one stale sentence: its write/readback note says
the spare “has not yet been booted with v5,” while the later [v5 first-boot
record](host-board-image-20260925-v5-first-boot.md) and JSON manifest record an
A-slot boot. Use the later first-boot record for the observed boot and retain
the remaining physical exclusions; the wording is corrected in the write note.

## Next work and physical gate

The offline H616 adapter, descriptor binding, exact v5 map and authenticated
one-shot receipt are implemented and independently reviewed. The missing step is
an authenticated boot composition that runs the reviewed H616 writer from
content protected by the SD-resident U-Boot/initramfs hash chain, mounts the NFS
root read-only as a source, and passes the commissioning-mode and bounded claim
port inputs. The current NFS-root `init` is not authenticated before execution;
do not enable the H616 writer through it. Keep the default SD diagnostic
unchanged and writer-free. A separate host-side one-shot job/claim launcher,
current live CID/dev_t capture and comparison, exact physical target policy,
and actual NFS/claim service preparation also remain outstanding.

The bounded [trusted-writer boot proposal](../features/network-emmc-trusted-writer-boot/proposal.md)
records the offline design and acceptance checks. It is pending independent
feature approval; no implementation or bootable writer artifact has been
authorized by that proposal record yet.

The development VM has 3.5 GiB free and must not receive a raw image or QEMU
target. Beelink currently has about 10.7 GB free. The compressed v5 source's
compressed and streamed raw hashes were revalidated there, but NFS services are
stopped and no physical writer tree is staged. Keep future image extraction,
large target files and QEMU runs on Beelink with a measured scratch bound; the
logical 7.8 GB image extent alone does not establish physical scratch use.

A read-only SSH attempt to printer `192.168.1.141` from both the development VM
and Beelink returned `No route to host` on 2026-09-27. No current live CID,
device number, power state or boot state was obtained. Retry that observation
from Beelink during H12 preparation; do not infer the physical target from H10.

H12 remains the one deduplicated physical commissioning task. Once the reviewed
writer and artifact are ready, the single supervised session must capture the
live CID before the write, then record the exact hash, target, progress, flush,
full readback, GPT/partition checks and resulting boot. Until that readiness
condition is met, no eMMC movement or write is requested.
