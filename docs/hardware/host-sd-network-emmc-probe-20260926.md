# Network-boot eMMC environment read candidate

Date: 2026-09-26 UTC. Hardware profile: `test-sv08-01`. Status: offline
candidate, awaiting independent boot-policy/artifact review. This is a method to
complete the existing H10 read-only environment inspection without removing
the eMMC to use a USB writer. It is not a supported recovery image. The owner
reports that the spare eMMC is currently out of the printer. It must be
reinstalled before this network test can access its environment; NFS does not
make a physically absent device available.

## Why the existing network boot could not read eMMC

The 2026-09-26 physical SD/NFS trace measured Linux messages for
`4022000.mmc` followed by `mmc2: Failed to initialize a non-removable card`.
It enumerated the disposable SD as `mmcblk0` and the Wi-Fi SDIO card, but no
eMMC block device. The trace is private on Beelink at
`/home/drew/sv08-captures/sd-network-20260925/console.raw`, SHA-256
`3594c7586321e0f9644cfa0eb10f9a9d93bdfecff3b124f0ec6d38d1ff1dc155`.

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

The NFS init then searches only under the SMHC2 sysfs controller path for one
32 GB MMC card. It opens that card's main user-area block node with
`O_RDONLY|O_NOFOLLOW`, reads exactly 64 KiB at byte offsets `0x400000` and
`0x800000` with `pread`, validates both U-Boot environment CRCs, and accepts
only the `ab-8gb-v1` layout and bounded boot-policy values. It emits the
device path, sector count, CRC validity, flags, order, and A/B counters; it
never prints raw environment data, CID, or other variables. The general
`SV08_SD_NFS_PASS` line is separate and cannot be used as H10 counter evidence.
H10 passes only if the eMMC line identifies the single expected 32 GB card and
both copies report valid CRCs and parseable policy values. Missing, ambiguous,
unreadable, corrupt, or unrecognized results fail closed and the init powers
down; it does not fall through to another boot.

The parser was exercised against synthetic valid/corrupt/invalid-policy
fixtures and a retained historical 128 KiB environment pair. That historical
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
| NFS init executable | 772,808 bytes | `428669f4d60d25edfb3ec121ddb639fee94d23845786e71516e01c7f93933502` |
| NFS root manifest | — | `26a395aa56abe83fd356895c48ce0935e172d381f21caa66c7658e8e29538fce` |

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

## Next action and stop conditions

An independent review must approve the exact image, PC3 setting, eMMC isolation
in U-Boot, NFS init, and stop behavior before media preparation. In one side-
lying session with the printer fully off, the owner moves only the disposable
SD to Beelink's writer, writes this reviewed image, and provides direct-I/O
readback matching the exact image hash. The owner reinstalls the spare eMMC in
the printer and the reviewed SD; the factory eMMC stays stored. Before power-on,
arm receive-only serial capture. One supervised SD boot should mount the
read-only NFS root, show the explicit eMMC result, then power down. Any absent
or ambiguous card, read error, CRC/layout failure, or unexpected boot path ends
the test without another reboot. If Linux still cannot see the eMMC, use the
already-approved USB-reader path for H10; do not attempt an eMMC write or
change MCU firmware.
