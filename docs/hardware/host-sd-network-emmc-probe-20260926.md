# Network-boot eMMC environment read candidate

Date: 2026-09-26 UTC. Hardware profile: `test-sv08-01`. Status: the first supervised attempt stopped before the eMMC probe. The corrected
read-only init is served, and a separate GPT-6 Sol review permits one further
supervised attempt with conditions. The diagnostic is not a supported recovery
image; current eMMC counters remain unknown.

Beelink is measured at `192.168.1.136`. Its NFSv3/TCP export of
`/srv/sv08-sd-nfs` is currently read-only with root-squash and limited to
Beelink (`192.168.1.136`) and the expected printer reservation (`192.168.1.141`).
A local NFSv3/TCP mount initially used an explicit mountd port and did not prove
default port discovery. The printer attempt showed repeated connection refusal
before the init executable ran. Beelink's mountd was restarted and registered
with rpcbind on TCP/UDP port 20048; a local default NFSv3/TCP mount (without an
explicit mountd port) then read the deployed init at the hash below, and a write
probe was refused with `Read-only file system`. Printer-side mount success is
still unmeasured. The reviewed SD image was written to the disposable SU02G
card and passed full image-sized direct-I/O readback; see the [write
receipt](host-sd-network-emmc-probe-card-write-20260926.md).

## Why the existing network boot could not read eMMC

The 2026-09-26 supervised attempt booted the reviewed SD loader and Linux,
obtained wired DHCP at `192.168.1.141`, then halted after NFSv3 root mount
refusals. The probe did not run, so it produced no eMMC environment/counter
result. The measured MMC trace reports controllers `4021000`, `4022000`, and
`4020000` initialized; `mmc0` failed to initialize a non-removable card,
`mmc2` enumerated the disposable SU02G SD, and `mmc1` enumerated SDIO. This
shows that Linux host numbering does not match the assumed controller-local
`mmc2` path. The full receive-only trace is private on Beelink at
`/home/drew/sv08-captures/h10-emmc-read-20260926/console.raw`, SHA-256
`89dc52360d9c242d5b5348c3abc1ec3e902ad8bd6dbd7248457ca2108c54d4c5` (28,893
bytes). No second boot has occurred.

The candidate Linux DTB has `/soc/mmc@4022000` enabled as H616 eMMC; its
kernel configuration has `CONFIG_MMC_SUNXI=y` and `CONFIG_MMC_BLOCK=y`. These
are offline configuration facts and do not by themselves prove card visibility.
The physical failed initialization is the measured result.

Source inspection explains the gap: the SD U-Boot fragment sets
`CONFIG_MMC_SUNXI_SLOT_EXTRA=-1`, which prevents U-Boot from initializing
another MMC slot. In the pinned CB1 U-Boot source, the vendor PC3 input and
pull-down that selects the eMMC path is nested in `mmc_pinmux_setup(2)`, so
that setup did not run in the SD image. The patch pinned by
[`sv08-sd-network-inputs.json`](../../configs/host-os/sv08-sd-network-inputs.json)
contains that CB1 selector change (SHA-256
`1fe801e57ce115f9d91dde132f1e756d2cf4a97284db4e4aa85c3bb0905eac81`). This is
source evidence from a related CB1 boot implementation, not a new electrical
measurement of the SV08 PC3 net.

## Candidate behavior and limits

The new SD U-Boot patch mirrors the vendor's PC3 input/pull-down, but leaves
`CONFIG_MMC_SUNXI_SLOT_EXTRA=-1`, disables `mmc1` and `mmc2` in the U-Boot DT,
keeps `ENV_IS_NOWHERE`, and excludes `saveenv`. It does not initialize or read
eMMC in U-Boot. Its purpose is to leave the eMMC selected for the Linux DT's
SMHC2 probe. Whether this brings up the installed module on this board remains
unmeasured until a reviewed physical test.

The NFS init searches host directories below only the exact SMHC2/eMMC
controller sysfs path and does not assume a Linux `mmcN` index. It accepts
exactly one 32 GB MMC card under that controller, rejecting ambiguous matches.
It opens that card's main user-area block node with
`O_RDONLY|O_NOFOLLOW`, reads exactly 64 KiB at byte offsets `0x400000` and
`0x800000` with `pread`, validates both U-Boot environment CRCs, and accepts
only the `ab-8gb-v1` layout and bounded boot-policy values. It emits the
device path, sector count, CRC validity, flags, order, and A/B counters; it
never prints raw environment data, CID, or other variables. It reports
`READ_ONLY_VALID_PAIR` only if both copies have valid CRCs and parseable policy
values; otherwise it reports `READ_ONLY_INCOMPLETE_PAIR` or a specific
discovery/read/format failure. The general `SV08_SD_NFS_PASS` line is separate
and cannot be used as H10 counter evidence. H10 passes only if the eMMC line
identifies the single expected 32 GB card and both copies report valid CRCs and
parseable policy values. Missing, ambiguous,
unreadable, corrupt, or unrecognized results fail closed and the init powers
down; it does not fall through to another boot.

The parser was exercised against synthetic valid/corrupt/invalid-policy
fixtures. New locator fixtures put the target beneath `mmc0`, an unrelated
small SD beneath `mmc2`, and verify ambiguity rejection. A retained historical
128 KiB environment pair was also parsed. That historical
pair parsed as CRC-valid flags 3 and 2, `BOOT_ORDER=A`, A counters 3 and 2,
and B counter 0; it does not describe the current eMMC state. The current
counter remains unknown.

## Offline artifact evidence

The physical-network candidate is the 201,326,592-byte regular file
`build/sd-network-emmc-probe-v3-physical/sv08-sd-network.img`, SHA-256
`cea51e9c0731c664563bf16a54fef585f1609ef90da03358eefd4d077b7aab28`. The
builder receipt is private under ignored `build/`; the public inputs and
configuration are source-controlled. Key outputs:

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| SPL/TF-A/U-Boot loader | 743,753 bytes | `c08b246194fd5f4a7427969f6789a2a283f2c78a4b9cad79ae616f48734a54ef` |
| U-Boot `boot.scr` | 1,099 bytes | `73ec145ec92dbdb68e3f2590e055cc1af48e08ac8925736e7a06a4e96d674826` |
| Linux `Image` | 33,405,440 bytes | `5bc7c62df2b521610d0dea0a82b38aceb54af7d340a44b02a27428d6ea28dc34` |
| Linux initramfs | 15,233,015 bytes | `8be88ee081ad61c64de216425b031b8988447d6fb009022edeffaf53f115d09e` |
| Linux DTB | 48,208 bytes | `571288762747007542bb00c7ce04c2e0994678422e441975d928022588da9d3f` |
| Init executable used in failed physical attempt | 772,784 bytes | `18271a75e14af6b2c8351c6fce697d77877b64dab7ffa5f8a65d1888a16833ad` |
| Corrected init executable currently served | 772,864 bytes | `1e7afa9aaf337ccffdb4c7431648f7aba934dcc600b04e11751743e345e1dc11` |
| Corrected NFS root manifest | — | `47928b1378278af64a307effe6c35d2ffe54d5b187172f23a4d0e77e5b131007` |

The patched U-Boot source was inspected after build: `board_mmc_init()` applies
the PC3 input/pull-down, and the effective configuration still has
`CONFIG_MMC_SUNXI_SLOT_EXTRA=-1`. The candidate's U-Boot DT disables MMC1/MMC2;
its script loads only SD partition `mmc 0:1`. These are build/source checks, not
physical evidence.

Focused checks passed: seven SD-image and environment-probe unit tests,
cross-compilation of the static AArch64 init with `-Wall -Wextra -Werror`, and
the QEMU NFS-root harness using the same kernel/initramfs and probe source. In
QEMU the probe reported no 32 GB card on SMHC2, while the independent NFS root
checks passed. With NFS unavailable, DHCP completed, the kernel halted without
running the probe, and the harness cleaned up QEMU and server processes. QEMU
does not model the H616 PC3 selector or eMMC and cannot validate the H10 read.

The refreshed NFS executable is served over the network, so a probe-only
correction does not change the SD image hash. The manifest and composition
receipt must bind any new executable to the same image. The QEMU harness now
removes stale serial logs
before each launch; a fresh run completed online NFS-root checks in 28.02 seconds
and server-missing DHCP/halt checks in 35.03 seconds. Both are offline results.

## Next action and stop conditions

The first high-consequence review authorized one supervised boot of the exact
SD image above. That authorization is consumed. The measured boot stopped at
NFS root mount and MMC numbering contradicted the probe's hard-coded host
index. The corrected executable is now served, and Beelink verifies its hash
through a default NFSv3/TCP mount with no explicit mountd port. A write attempt
was refused as read-only. The server reports mountd versions 1–3 over TCP on
port 20048; `/var/lib/nfs/etab` contains the expected printer address
`192.168.1.141` with `ro,root_squash`. The NFS mount test originated on Beelink
(`192.168.1.136`), so it does not prove a client request from the printer
address. A separate GPT-6 Sol high-consequence review approved exactly one further
supervised read-only attempt with the checks and stop conditions in the
[retry review](host-sd-network-emmc-probe-review-20260926.md). Immediately
before that attempt, recheck mountd registration, the `.141` export and deployed
init hash, then arm fresh receive-only capture. If the non-removable-card
initialization failure repeats, stop using network boot for H10 and use the
USB-reader path. Do not interpret the halted boot as an eMMC read result or
infer current A/B counters. Keep the factory module stored and do not change MCU
firmware.


## Current physical precondition

After the retry review, the owner clarified that the spare eMMC is currently not
installed in the printer. No second boot has occurred. Keep USB serial
disconnected while reinstalling the spare with all host power removed; leave the
written SD card in place and the factory eMMC stored. The reviewer subsequently confirmed the same PASS WITH CONDITIONS applies
once that precondition is met; no new review is needed solely for reinstalling
the same module. Repeat the NFS/hash/capture checks immediately before the boot.
The owner subsequently reported reinstalling the spare eMMC and same SD card
with USB serial disconnected. Beelink has reconfirmed the mountd service,
`.141` export and executable hash; fresh receive-only capture is waiting. The
remaining action is one serial reconnect to start the reviewed boot.
