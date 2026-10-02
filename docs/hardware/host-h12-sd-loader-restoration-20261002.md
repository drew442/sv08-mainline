# H12 independent SD-loader restoration — 2026-10-02

The owner moved only the rescue SD into Beelink after disconnecting printer USB
power with PSU OFF. The installed spare and stored factory eMMC were untouched.
The preparatory move received independent GPT-6.1 Sol/high review. Beelink's
udisks2 service is temporarily stopped and runtime-masked; restore its prior
active state after the card is safely removed.

## Measured reader intake and candidate

Read-only admission identified the recorded SanDisk SC16G, 15,931,539,456 bytes,
on Beelink's USB reader, currently `/dev/mmcblk0`. The private full CID, by-id,
sysfs path, host boot ID and device number bind this reader session. Both
partitions were unmounted, without holders, users or swap. GPT and filesystem
identities match the [prepared recovery card](host-sd-recovery-host-write-20260929.md).
The known backup-GPT-at-image-end warning was observed; no repair was made.

The current 786,225-byte loader span at byte 8192 matches the
[managed transfer](host-managed-sd-transfer-20260929.md): SHA-256
`350a941a7ec67b541308d235bffa4b937b8171f683f3e96b0c51dd32fab64544`.
A durable 738,197,504-byte current-prefix beforeimage was saved off-card.
Protective MBR, both GPT headers/arrays, full FAT and full root hashes match
historical preservation evidence. SD raw environment records were also read.
No target filesystem was mounted.

The proposed restoration replaces that span with its exact original bytes,
SHA-256 `b364979ca29a6f9eba28c20cc8da6d75b95af7c03d6911e3da402b753f5c826f`.
It contains the original 743,753-byte independent loader, SHA-256
`4def569998f4315d78687450276f9c1499b9d9b1eed03015044bf4177f8603e3`,
and the original trailing bytes overwritten by the managed transfer. Patching
only this span in the beforeimage reproduces the exact original recovery-image
prefix SHA-256 `2b0a6fa177515652722b53c0a7f306c3fb452c84b1af1ffa4dc01ab5c8ed0040`.

The actual compiled configuration, default environment and generated header
match the retained original build receipt. That loader ignores saved MMC
environments, disables U-Boot eMMC enumeration and automatically loads the
hash-verified SD script. The four FAT payloads were extracted from the off-card
snapshot and hashed; `boot.scr` remains 1075 bytes with SHA-256
`ce18bf74e3d8ae840bfb90129ba28515ba89cbd2759bc32ecd0418f6987d1ddd`.
The [original physical SD boot](host-sd-recovery-host-first-boot-20260929.md)
previously reached recovery Linux and authenticated SSH with the spare installed.
These facts support the restoration candidate; they do not prove this boot.

## Operation boundaries and current result

The first write helper was rejected during review because it continued after a
positive partial write. It was not executed. Its preserved successor performs
one bounded span write, stops on any partial write, and requires flush plus a
full direct prefix readback matching the original image. No automatic rollback,
GPT repair, resize, tail write, eMMC/MCU write or printer-output operation is part
of this restoration. A separate exact review precedes writing; reinstall/boot is
a distinct reviewed operation. The current beforeimage supplies a rollback span
only through a separately reviewed action.

**Restoration passed at 02:20:27 UTC.** Independent GPT-6.1 Sol/high exact
review accepted v2 with conditions (native session
`01a0fa22-6734-7a32-b72f-6263c117b3e8`, effective tier observed). Fresh independent
pre-write admission passed. The single write completed and a direct
738,197,504-byte readback matched the original image hash above. Separate
post-write reconciliation verified durable receipts, unchanged source/card
identity, no surviving writer/readback process and no mounts/users/holders.
This measures preservation throughout that prefix; the remainder of the 16 GB
card was not fully read back and was excluded by the helper's write boundary.

**Physical reinstall/boot is being reviewed separately and has not occurred.**
The existing receive-only collector is active and waiting with no UART owners,
the bridge absent, preserved original logs and more than eleven hours left.
The owner will receive the exact safe SD move/one-connect instruction after
fresh readiness and boot review. No serial command sequence is part of this boot.
Physical recovery/preflight and automatic return remain open. No further UART
recovery variants or complete cold-byte capture work are assigned.

Private source, frozen revisions, intake, provenance, beforeimage and review
records are under `local/feature-workflow/probes/h12-sd-loader-restore-20261002a/`
and the corresponding root-owned Beelink capture directory. Source records and
retained original build/composition evidence accessed 2026-10-02. Board revision
is owner-reported H616_JC_6Z_V1.2 in the managed-transfer record; this reader
inspection does not measure the printer PCB revision.
