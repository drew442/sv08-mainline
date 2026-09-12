# 0014: Independent recovery with compressed `/usr`

Date: 2026-09-12. Status: accepted within the bounded offline
[feature approval](../features/host-recovery-independent-image/proposal.md).

## Problem and decision

[Decision 0010](0010-host-administration-and-recovery-ui.md) requires an independent
GTK recovery environment with touch, keyboard, mouse and accessibility support.
The fixed [factory-capacity layout](../../configs/images/host-ab.json) allocates
512 MiB to recovery within 7,818,182,656 bytes. The complete selected Debian
package closure exceeds that partition before filesystem metadata.

Use the distro's standard SquashFS filesystem for the entire `/usr` tree inside
a read-only ext4 recovery envelope. Keep package runtime, translations, manuals,
fonts, copyright files and common licenses. Preserve numeric ownership and modes.
The envelope also contains its independent kernel and initramfs, `/etc`, the dpkg
database and a small external manifest. No A/B root, data filesystem, host runtime,
writable overlay or whole-root RAM decompression supplies indispensable content.

The current profile is explicitly Debian ARM64 on QEMU `virt`, Cortex-A53, virtio
storage/graphics, USB keyboard/mouse/tablet and direct virtio multitouch. It establishes neither H616 board
support nor a complete release size budget. Board boot firmware, DTB and missing
hardware firmware/driver integration remain separately measured additions.

## Boot contract

The self-contained [early boot program](../../configs/host-os/recovery-init) uses
its own installed BusyBox, blkid/loader/library closure and selected distro kernel
module dependency closure. It does not execute anything from compressed `/usr`
until verification completes. The selected kernel and initramfs are present inside
the envelope; direct QEMU loading is compared to those contents.

The reviewed caller supplies `sv08.envelope=<sha256>` for the external fixed
six-line manifest at `/etc/sv08/recovery-envelope.manifest`. That manifest binds the
format version, expected filesystem UUID and byte capacity, fixed `/usr.squashfs`
path, exact byte size and SHA-256. It contains no executable shell text and is never
sourced. The manifest is outside the compressed image, avoiding circular hashing.
A supplied hash does **not** establish authenticated or secure boot.

Before switching root, the gate requires a read-only block device with the expected
capacity/UUID, ext4 mounted read-only without journal replay, regular single-link
root-owned manifest and compressed image, expected backing filesystem and exact
content hashes, no unexpected root submounts or preassigned loop mappings, and a
read-only zero-offset/unlimited-size loop with the exact backing path. It then
mounts SquashFS read-only and checks the resulting source/type/options. An
independent 180-second guest watchdog bounds this early journey. Failures print a
specific refusal on the serial console and power off before display activation.

The verified marker under `/run/sv08` is produced after this gate. It adds a service
condition; it does not replace verification or make a marker on an unverified root
sufficient to execute merged-`/usr` binaries. The physical envelope and `/usr` stay
read-only. `/dev` (16 MiB, 4,096 inodes), `/dev/shm` (32 MiB), `/run` (96 MiB)
and `/tmp` (64 MiB) have explicit memory limits; mutable log/cache
and service state uses explicit `/run` paths. There is no persistent state registry
initialization, login account or network service in this offline profile.

## Unsupported recovery operations

The existing production media provider is unchanged. Its established mount and
media identity contract does not support this compressed `/usr` chain. Diagnostic
status and Check storage remain useful; export, restore and slot selection stay
unavailable without a verified backend. This image supplies no synthetic verified
media context, fixture mode, loop exception, trust bypass or media premounter.

A later separately reviewed composition must support the exact compressed backing
chain and preserve source/destination admission before any recovery operation can
be called complete. Physical HDMI/touch/keyboard/mouse and board boot remain in the
[canonical task list](../hardware/host-os-tasks.md).

## Implementation and retirement

[The builder](../../scripts/recovery_image.py) separates unprivileged hash-pinned
intake, offline package assembly, filesystem construction and the
[VM harness](../../tests/recovery_vm.py). Commands inspect by default. Privileged
preparation uses private mount, PID and network namespaces, fresh ignored paths,
service suppression and finite subprocess deadlines; it refuses raw-device,
symlink and overlapping inputs/outputs. It does not modify upstream or a baseline.

Custom code fills the gap between the reviewed immutable recovery layout and
distro boot integration. Prefer replacing it with equivalent supported
initramfs/image-builder integration when that can preserve this verified backing
contract. Retire the VM-specific UUID/device/graphics profile when an explicit
board profile supplies verified equivalents; never generalize it into guessed
SV08 hardware identity. Changes to the production provider require their own
review and regression evidence.

Primary sources, revisions, source archives and binary hashes are pinned in the
[package lock](../../configs/host-os/recovery-packages.json) and
[authenticated source inventory](../../configs/host-os/recovery-sources.json),
accessed 2026-09-12. Source archives are indexed, not rebuilt or downloaded by this
delivery. Package license texts remain in the filesystem; their inventory and
actual build/boot findings are in the [recovery image evidence](../hardware/host-recovery-image.md).
