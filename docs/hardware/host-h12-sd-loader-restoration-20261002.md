# H12 independent SD-loader restoration — 2026-10-02

The owner moved only the rescue SD into Beelink after disconnecting printer USB
power with PSU OFF. The installed spare and stored factory eMMC were untouched.
The preparatory move received independent GPT-6.1 Sol/high review. Beelink's
udisks2 service was temporarily stopped and runtime-masked during reader work;
its prior active/enabled state was restored after card absence was verified.

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

**Separate boot review passed with conditions at 02:27:26 UTC**, using the same
independent Sol/high session. Fresh card-closure and passive-readiness admissions
passed at 02:29:39 UTC. The receiver is active/waiting, bridge absent, no UART
owners, original log prefixes preserved and more than eleven hours left. The
owner's one-connect instruction expires at **02:59 UTC on October 2**; later
connection needs fresh readiness. A standard read-only tail of the existing raw
log is running for coordinator observation; it opens no UART.

The owner completed that exact SD reinstall and USB connection inside the ready
window. **Independent SD recovery boot passed at approximately 02:31 UTC.** No
UART command was sent. The initial boot trace begins at BL31; missed earlier
cold-start bytes remain the accepted limitation. Main U-Boot verified the SD
payloads and Linux reached authenticated wired SSH at `192.168.1.141`.

Measured boot ID is `92765d15-b74c-4864-8b39-2d8ce96b756a`, kernel
`6.18.51-sv08-candidate1`, root `/dev/mmcblk0p2` with
`ro,relatime,norecovery`, and read-only squashfs `/usr`. Ethernet `end0` reported
100 Mbps full duplex. SD SSH and recovery-display services were active, with no
failed systemd units. Service state is not a fresh human display/touch observation.
The new SSH key was enrolled under the owner's address-based trust decision.
The owner was told startup succeeded and no further physical action was needed.
Leave USB connected and PSU OFF. Beelink's reader/card absence was independently
observed before restoring udisks2 active/enabled.

## Fresh spare and clock reconciliation

The same spare is currently `/dev/mmcblk2`, device `179:8`, controller
`4022000.mmc`, capacity 31,272,730,624 bytes. CID string SHA-256 is
`08d24eb0a58bc7288c07020a0432586ea6070b78abdd86b209de362c7b42fe8a`.
An initial intake assertion incorrectly expected device 179:16 and stopped
before opening media; that failure is preserved. The corrected read-only intake
used measured 179:8 and a complete process-descriptor scan because `fuser` is
unavailable. GPT CRC/layout checks passed at the reviewed 7,818,182,656-byte image
footprint; the backup GPT remains at image end and was not relocated. No spare
partition was mounted or in use. Both 64 KiB raw environment records passed CRC,
with flags 9/8, zero A/B counters, order `A B`, and no `SV08_REIMAGE_ARM` token.
Full dictionaries and beforeimages remain private off target.

Linux initially reported April 13, 2026, and RTC January 2, 1970. A separately
reviewed exact helper bound this boot, spare and `sun6i-rtc 7000000.rtc` device
251:0 to a fresh monotonic window. Independent GPT-6.1 Sol/high review accepted
one Linux clock correction followed by one RTC write, each with readback and no
retry. At 02:45:53 UTC the operation succeeded using Beelink's synchronized UTC.
Independent later readback found Linux/RTC approximately 2.24/2.29 seconds behind
Beelink's subsequent observation, including transfer and integer quantization.
This establishes current agreement; clock retention across a future reset or
power loss remains unproven. No job or target media/environment write accompanied
this clock operation.

## Durable p5 reconciliation and next preflight route

The entire 536,870,912-byte p5 region was read through an exclusive read-only
whole-device descriptor and streamed to a durable private Beelink beforeimage.
Snapshot SHA-256 is
`305860274617a15d6958f76e3238c816c38b4f3c36392a76cb1c850ecd0c2ea3`.
Only the bound p5 span was read; the target filesystem was not mounted. Default
read-only `debugfs` inspection on the off-target snapshot found a clean filesystem
and 16,424 free 4096-byte blocks (67,272,704 bytes). The following exact files
match the previous C attempt:

| File | Bytes | SHA-256 |
| --- | --- | --- |
| `recovery.scr` | 2085 | `f1eac4024dc3b24f56af17744f42669b73aebd857b264e4e49447cd6e43caf2f` |
| `sv08-reimage/recovery-original.scr` | 720 | `57e414bec126a309085f3e2be211c6b8fe0e43f5833a5b5609f3e69457808dee` |
| `sv08-reimage/writer.itb` | 48902464 | `b5f527cbb3ee302e106316b5a41790b13db6311a8b106482f4b72fb8fdb1edb2` |

The active stage's armed marker is absent. The existing expired-job archive and
its files remain intact; no historical artifact was deleted or rearmed.

A separate source-only planner verified the accepted operation order: prepare a
fresh repaired job while this independent SD host supplies SSH, stage/arm/activate
it on p5 and the spare environment, then restore the exact accepted managed
loader `350a941…` **last**. One reviewed SSH reboot lets its default dispatch
source the p5 selector automatically. Marker consumption then selects the
preserved original p5 recovery script on return, as urh-04 requires. This needs
no new loader implementation, UART commands or repeated product approval. The
planner's initial proposed SD-first variant is superseded by its ordering
addendum and is not assigned.

Fresh source preparation passed at approximately 02:56 UTC in
`/srv/sv08-h12-preflight-20261002-sdrestore`: 27 source/input entries were verified
against accepted startup-repair commit `0708a18a2528929ad9a59c22e32d865003e95ed2`.
The new policy binds staging to measured `/dev/mmcblk2`, device 179:8, with the
accepted controller/CID runtime admission. No new job, keys, candidate artifact,
listener or target write was created. Before creating expiring inputs or launching
the next boot, owner availability for prompt USB power removal on a failed boot
is pending. Exact independent artifact/staging/arm/activation/loader/boot reviews
and current admissions remain required. Actual RAM preflight and automatic return
are still open; successful SD recovery does not pass them or grant full-image,
MCU, heater or motion authority. No further UART recovery variants or complete
cold-byte capture work are assigned.

Private source, frozen revisions, intake, provenance, beforeimage and review
records are under `local/feature-workflow/probes/h12-sd-loader-restore-20261002a/`
and the corresponding root-owned Beelink capture directory. Source records and
retained original build/composition evidence accessed 2026-10-02. Board revision
is owner-reported H616_JC_6Z_V1.2 in the managed-transfer record; this reader
inspection does not measure the printer PCB revision.
