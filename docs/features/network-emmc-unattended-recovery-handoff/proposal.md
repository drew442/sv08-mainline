# network-emmc-unattended-recovery-handoff: Enter and leave the RAM writer without moving media

Kind: feature. Author: root/coordinator. Date: 2026-09-27.

## Problem and current evidence

The approved SD trusted-writer path now passes a complete controller-integrated
synthetic QEMU write and refusal test. It still requires selecting a prepared
SD card and does not automatically return to normal eMMC boot. It therefore
does not meet the owner's goal of reflashing the installed spare without a
USB writer **or human action for each write**. No physical writer boot or eMMC
write has occurred.

The v5 eMMC's compiled U-Boot dispatcher already scans the A/B slots and then
loads `recovery.scr` from partition 5 when neither slot can boot; see
`configs/host-os/sv08-default.env` and `configs/host-os/boot-dispatch.cmd`.
That 512 MiB ext4 recovery partition has a separate kernel and initramfs.
The v5 first-boot record proves only an A-slot boot, not physical recovery
selection. The physically booted kernel has `CONFIG_KEXEC` disabled. The SD
loader disables U-Boot's eMMC controller, so simply chaining back to eMMC
from the current SD script is not a supported return path. The existing SD
card remains a useful independent rescue path.

Beelink now holds the exact v5 raw source in a private directory on its
dedicated scratch volume: 7,818,182,656 bytes, SHA-256
`ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`.
Its compressed parent matched the pinned v5 compressed hash before extraction.
This is a nonrelease diagnostic candidate, not proof of an installed artifact
or a physical write.

## Proposed bounded route

Use the existing eMMC recovery selection to load an explicitly staged writer
kernel/initramfs/DTB into RAM. The writer's trusted inputs, exact target policy,
job verifier and signed job stay in that initramfs; NFS supplies only the exact
read-only image. The running host stages and verifies one job and boot payload
on the *installed* spare eMMC, then makes a separately journaled one-shot boot
selection only after every file is durable. No eMMC removal, USB writer, SD
insertion or physical switch action is part of a normal reflash attempt.

The recovery script must keep the existing recovery UI as the default. It
selects the RAM writer only while a bounded job marker and exact boot payload
are present. The writer consumes and fsyncs that marker before it can open the
target, unmounts the recovery filesystem, obtains the durable Beelink one-shot
claim, hashes the full NFS source and checks the current CID/controller/type,
capacity and `dev_t`. Its source and running root must no longer depend on any
eMMC mount before the first whole-device write. On a successful complete
flush/readback/GPT check, the written image replaces the temporary recovery
script, marker and boot environment; a controlled reboot should boot the new
image's normal slot. Any uncertain post-open result halts with no retry. An
early refusal with the marker consumed selects the ordinary recovery UI on a
later boot, preserving a path to inspect and repair the spare. The factory
eMMC remains stored, and the existing SD diagnostic/USB reader remain manual
recovery options for a damaged full image.

This is a **design to test**, not a claim that the current U-Boot will follow
it. In particular, zeroing both slot attempts may interact with RAUC bootmeth
and the redundant environment in a way the existing A-slot observation does
not prove. The recovery partition's actual writable space, U-Boot load
addresses, live MMC mapping, and pre-open marker durability also need checks.
Do not alter the normal A/B updater or persistent recovery UI merely to make
an offline test pass.

## Rejected shortcuts and alternatives

Launching a full-device writer from the running eMMC root risks overwriting
its own mounted source. A kexec handoff would avoid the recovery selector but
requires a newly built/physically tested kernel and a board-specific H616
handoff not yet demonstrated. Keeping the current SD writer as the automatic
route would require an always-installed SD boot manager that can select and
boot the eMMC OS; the current SD U-Boot deliberately leaves eMMC unavailable.
The recovery RAM handoff reuses more measured boot behavior while preserving
SD as an independent rescue route. If offline tests disprove the recovery
selector or the marker cannot be safely consumed before target open, return
to a separate route decision rather than silently weakening the invariant.

## Acceptance and boundaries

| Check | Environment | Required evidence |
| --- | --- | --- |
| `urh-01` | Offline | Exact U-Boot sandbox dispatch with both valid and exhausted A/B states proves the writer is selected only by an explicit, durable one-shot marker; marker absent/malformed/mismatched payload chooses the unchanged recovery UI. No staged file or policy write can make an unarmed normal boot run the writer. |
| `urh-02` | Offline | The stage operation admits only the identified eMMC recovery partition, private signed job and exact image/map; it preserves original recovery files, verifies all payload hashes and capacity, and changes boot policy only after durable file staging. Fault injection at each stage leaves either normal boot or recovery, never an automatic post-open retry. |
| `urh-03` | Offline | QEMU boots the actual RAM writer through the proposed recovery handoff and actual one-shot controller; success writes and reads back the full synthetic image, restarts into a normal synthetic slot, and failure/refusal paths cannot reopen the target automatically. The default SD diagnostic and normal A/B update remain unchanged. |
| `urh-04` | Hardware | One separately reviewed read-only recovery handoff on `test-sv08-01` captures current CID/dev_t, marker behavior, recovery fallback and normal return without opening the eMMC for whole-device write. This is part of H12, not a new human task. |
| `urh-05` | Hardware | Only after `urh-04`, exact artifact/target/recovery comparison and an immediate independent Sol high-consequence review, one attended physical full-image write/readback and next boot are recorded. This remains H12; no offline result alone establishes it. |

The offline implementation may be delegated under the owner's existing
writerless goal, but this proposal grants no boot-policy or eMMC write
authority. Every physical boot-policy change and write retains its separate
high-consequence review and the owner's standing hardware authorization.
No private CID, key, machine serial, Wi-Fi credential or image bytes may be
committed. Do not stage the raw 8 GB source on the space-limited development VM.
