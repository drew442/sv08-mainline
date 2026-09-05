# 0002: First spare-eMMC image uses a fresh userland and captured boot support

Date: 2026-09-05. Status: accepted for the test-sv08-01 host bring-up candidate,
not a supported printer release.

## Decision

The owner will retain the factory eMMC unchanged as the host rollback baseline
and write a new image to an existing blank nominal 32 GB module. A factory-disk
backup file and restoration onto the spare are no longer prerequisites for this
host-only experiment. Physical spare compatibility still requires a boot test.
MCU preservation remains required before replacing either MCU's firmware.

Build a fresh Debian 13 (trixie) arm64 userland from the dated Debian snapshot
`20260901T000000Z`, retaining the captured bootloader prefix, Linux
`5.16.17-sun50iw9`, modules and matching SV08 device tree as an interim platform.
Do not substitute CB1, SV08 Max or Zero device trees. Rebuild the initramfs for
the new userland. Keep the original partition start offsets, use new filesystem
identities, and fit the image within 8 GiB so a nominal 32 GB destination has
ample room without needing its exact sector count at build time.

Ethernet uses DHCP; the `sovol` account uses the owner's existing authorized SSH
keys and passwordless sudo. Password login is disabled. No Wi-Fi credentials,
factory passwords, printer calibration or factory SSH host keys are inherited.
The image is private because its access keys and captured platform binaries are
machine-specific inputs. Host SSH keys are generated on first boot.

No Klipper, Moonraker or touchscreen service is activated in this first image.
The selected Klipper source is staged for subsequent work; matching host/MCU
builds and a reviewed configuration remain separate milestones. This image
establishes boot, storage and remote access before any change to MCU firmware.

## Why

The printer's physical host revision is unknown. The installed boot support is
an observed working input on its original eMMC, while an unrelated generic
H616 image would add unresolved board wiring, DRAM and storage assumptions.
Fresh userland avoids carrying vendor installers, reset scripts and locally
modified application services into the new system. Keeping printer services
absent preserves separation between host bring-up and printer activation.

This is an image assembly workflow, not a source-reproduced kernel/bootloader.
Input hashes, package versions, build commands and output checks establish
provenance; byte-identical rebuilds are not claimed. A later OS/boot-chain
selection must retire the captured platform inputs in favor of a maintained,
source-built and hardware-tested stack.

## Implementation and validation

Use standard debootstrap, QEMU user emulation, initramfs-tools, U-Boot mkimage,
mtools and e2fsprogs. Project code only assembles/checks ordinary image files;
it must not select or write hardware block devices. Default to a build plan
unless execution is explicitly selected. Tests cover partition layout and
input/output rejection, with filesystem checks on the resulting artifact.
The integration belongs here rather than in third-party source; retire it if
a selected upstream image builder supports the verified board directly.

Offline acceptance covers partition bounds, FAT/ext4 integrity, boot references,
arm64 execution under QEMU, package state, SSH settings and absence of active
printer services. Hardware boot, network, storage stability, HDMI and recovery
remain unverified until the owner writes and boots the spare.

## Sources

- Private test-sv08-01 boot-support capture, 2026-09-05; PCB revision unknown.
- [Debian debootstrap manual](https://manpages.debian.org/trixie/debootstrap/debootstrap.8.en.html),
  accessed 2026-09-05: foreign-architecture bootstrap and second-stage operation.
- [Dated Debian snapshot](https://snapshot.debian.org/archive/debian/20260901T000000Z/),
  accessed 2026-09-05; signed Release/package metadata checked during bootstrap.
- [OpenSSH ssh-keygen manual](https://manpages.debian.org/trixie/openssh-client/ssh-keygen.1.en.html),
  accessed 2026-09-05: `-A` generates missing host keys. The small first-boot unit
  orders this supported command before Debian's SSH service; remove it when a
  selected upstream image builder supplies equivalent per-device key generation.
- [systemd network configuration](https://manpages.debian.org/trixie/systemd/systemd.network.5.en.html),
  accessed 2026-09-05: interface matching and DHCP configuration.
