# Unattended eMMC writer handoff: bounded offline research

Date: 2026-09-27. Target profile: `test-sv08-01`, reported mainboard
`H616_JC_6Z_V1.2`. This document contains offline source and regular-file
measurements. It is not a printer boot or write result.

The [handoff proposal](../features/network-emmc-unattended-recovery-handoff/proposal.md)
received an independent `needs-research` decision. The following checks answer
the currently available source, dispatch and capacity questions; marker
consumption, actual RAM-writer entry and physical boot remain unproven.

## Recovery selection already exercised

`tests/uboot_environment.py` previously ran the actual
`configs/host-os/boot-dispatch.cmd` through U-Boot 2026.07 sandbox with raw,
redundant MMC environment copies and real libubootenv/RAUC commands. Its
retained `build/uboot-environment-v4/result.json` reports exhausted A/B
attempts, both corrupt environment copies, and invalid order/counter/layout
states selecting a recovery-script **marker** rather than an A/B boot marker.
The sandbox U-Boot SHA-256 was
`7e62a7f1f38eeb60bcdc8a83ca03b71085cb68508613f408cde193c614a8a1cd`.
The exhausted log shows RAUC's `No valid slot found`, followed by
`SV08_TEST_RECOVERY`; the both-corrupt log shows default-environment fallback
and the same marker. This is a disposable FAT recovery fixture, not the v5
ext4 recovery UI or a physical H616 execution. The linked ARM64 candidate
default environment is separately checked by `tests/uboot_board_candidate.py`;
the v5 physical record has only an A-slot boot. Fresh physical recovery
selection remains H12 read-only evidence.

## Exact v5 source and recovery capacity

On Beelink, the retained compressed v5 source again matched its pinned
SHA-256 `09fb7efb7637e3b360bbb6c76e5b2b3cf7e0164a69082122b18a05ac567d34a1`.
The raw expansion was staged only on the dedicated scratch LV as
`/mnt/sv08-qemu-trusted/physical-prep-v5/source.img`: size 7,818,182,656,
SHA-256 `ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`.
It is mode 0644 inside a private directory, satisfying the existing one-shot
NFS controller's source-mode and same-filesystem hard-link preconditions if
an export is later created there. No claim service is armed. `sgdisk -v`
reported no GPT problem within the 8 GB image, with its intentional table
gap. This is a nonrelease candidate and has not been compared to a current
live eMMC CID.

A read-only extraction of the v5 `recovery` extent at byte 4,714,397,696
produced a 536,870,912-byte ext4 image, SHA-256
`c83975508e1cafca51e23c6ad9e19408fa01b5d35be583b39a38c5b13ad2345c`.
`dumpe2fs` reported 40,310 free 4 KiB blocks (165,109,760 bytes, about
157.5 MiB) and 31,039 free inodes; `e2fsck -fn` completed its five passes
without reporting a repair need. The existing recovery files include
`/boot/Image` (33,405,440 bytes), `/boot/initrd-recovery.img` (2,712,499),
`/boot/sv08.dtb` (48,208) and `/recovery.scr` (720). This is an image measurement,
not proof of the partition's present installed free space or ext4 write
behavior. A roughly 15 MiB RAM-writer initramfs plus the existing 33 MiB
kernel appears to fit that image's free blocks, but the final FIT/staging
workspace must be measured rather than inferred from these sizes.

The configured U-Boot load addresses are kernel `0x40080000`, DTB
`0x4fa00000`, script `0x4fc00000`, and ramdisk `0x4ff00000`. The existing
kernel and measured recovery ramdisk fit without those direct load ranges
overlapping. A composed writer FIT has not been loaded at these addresses on
the board; compressed/uncompressed handoff and the 512 MiB DRAM case remain
physical checks.

## Payload integrity available in the current loader

The ARM64 v5 U-Boot build config has `CONFIG_CMD_HASH` and
`CONFIG_FIT_SIGNATURE` disabled. It has `CONFIG_FIT_FULL_CHECK`, `CONFIG_SHA256`,
`CONFIG_CMD_IMI`, `CONFIG_CMD_BOOTM`, `CONFIG_CMD_CRC32` and ext4 load enabled.
An isolated U-Boot sandbox `iminfo` probe of a small FIT with SHA-256 nodes
reported all three payload hashes valid. Flipping one byte of its kernel data
reported `sha256 error` and `Bad hash in FIT image`. The valid FIT SHA-256 was
`1c4c74b0d212d493b3b0caeadb3ea818336e34dbd71a52a9d5a8618a3070b463`;
the retained good/corrupt sandbox logs have SHA-256
`fb12cb5dad6b359238c1c6a69e4c41186a50196fa224e472a8cb310115cf7c04`
and `f06b4f675fad109307503f87b603a385cce2c1c692dc7d34b8cfc66cd9077371`.
FIT hashes detect changed payload bytes, but without FIT signatures or an SoC
trust root they do **not** authenticate a substituted FIT. The host must
verify the staged artifact before arming, and the embedded writer must still
verify its signed job and exact source/target before a whole-device open.
This sandbox probe does not prove the ARM64 U-Boot binary's FIT handoff.

## Remaining exit evidence

The proposal should specify a temporary recovery script that checks a
one-shot marker, verifies the loaded FIT and falls through to the original
recovery UI when absent or malformed. A separately exercised consumption
protocol must make the marker durably unusable before the first target open,
including interrupted boots. The stage sequence must place and hash all
payloads before its final journaled boot-policy change. Then the exact
dispatcher/recovery script and actual one-shot controller need a disposable
QEMU success/refusal/fault journey, including a second boot after the image
replaces the temporary recovery script and environment. An independent review
must approve that evidence before any H12 physical boot-policy operation.

The physical read-only handoff and subsequent full eMMC write are distinct
H12 actions, each requiring its immediate high-consequence review. Only the
latter can establish that the installed spare can be reflashed without a
reader; neither action alone proves the unattended return path is reliable.
