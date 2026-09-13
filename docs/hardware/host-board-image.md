# First complete board A/B diagnostic image

2026-09-13, test-sv08-01. This continues authorized physical host testing. It is
not a supported printing release. The [kernel trials](host-kernel-trial.md)
passed using the original loader; the [new SPL/U-Boot](host-sv08-ab-boot.md)
requires its own physical boot and console capture.

## Composition contract

[The diagnostic composer](../../scripts/assemble_board_diagnostic.py) accepts
finalized host/data trees, a completed [board recovery build](host-recovery-board.md)
and the exact reviewed SPL/FIT binary. It operates on regular files below
`build/`, defaults to inspection, rejects overlapping sources/output and never
opens a printer device. It verifies source inventories, receipts and input hashes
before and after composition. Whole-image byte review remains a separate step.

The image occupies **7,818,182,656 bytes**, within the original 8 GB footprint:

| Partition | Size | Purpose |
| --- | --- | --- |
| 1, boot-a | 192 MiB | A raw Image, raw initramfs, diagnostic DT, slot script |
| 2, root-a | 2048 MiB | Finalized Debian host |
| 3, boot-b | 192 MiB | Mirrored initial boot payload |
| 4, root-b | 2048 MiB | Mirrored initial host payload |
| 5, recovery | 512 MiB | Independent compressed recovery OS, kernel and script |
| 6, data | 2447 MiB | Persistent identity, owner access and user artifacts |

The first partition starts at 16 MiB. Primary GPT entries are relocated to sector
4096; SPL/FIT begins at byte 8192, while two complete 64 KiB environments occupy
4 MiB and 8 MiB. Collision and exact partition-record checks run before and after
payload insertion. **Those environment offsets overlap the current single-root
printer image's boot filesystem. Write only the complete new image through the
USB writer; do not transplant the raw environment onto that installed layout.**

Persistent environments contain all compiled default commands and load addresses,
plus `sv08_env_layout=ab-8gb-v1`, `BOOT_ORDER=A`, `BOOT_A_LEFT=3` and
`BOOT_B_LEFT=0`. This gives three bounded A attempts, then independent recovery.
B is populated for subsequent testing, but is not automatically tried or declared
healthy. No automatic health confirmation is installed. Source and real
libubootenv CRC tests verify that seeding retains the complete dispatch policy,
including fallback to the second environment copy after corruption.

## Host finalization

Start from the clean packaged application baseline, not a historical QEMU root
containing `qemu-probe.service`. Install the exact kernel/board pair, RAUC 1.15.2,
its pinned squashfs-tools/liblzo dependencies and the nine locked Cockpit delta
packages. Remove the superseded kernel/meta-package only from that private copy;
require clean `dpkg --audit` and `apt-get check`. Select the installed upstream
regulatory alternative and verify the complete board artifact inventory.

Run [core integration](../../scripts/integrate_host_os.py) with the six explicit
PARTUUIDs and a non-deployable diagnostic release, then
[host UI staging](../../scripts/stage_admin_ui.py). Regenerate the host initramfs
after installing the rendered data-mount hook and `FSTYPE=ext4`; inspect its
fsck/logsave closure and exact persistent partition identity. The boot slots use
decompressed **raw Image** and raw gzip initramfs with an explicit byte count,
not packaged gzip `vmlinuz` or the earlier legacy `uInitrd` wrapper.

Enable data/prepare, NetworkManager, SSH and the Cockpit socket. Mask both actual
`sv08-klipper`/`sv08-moonraker` units and legacy printer-service names; this pilot
also masks RAUC activation. Reset construction-time machine identity, host keys,
random seed and logs. Seed only the owner's existing public access keys into
the private data tree for **`sv08` UID/GID 1000**, with correct SSH permissions.
Private pilot password/TLS/SSH identity provisioning is recorded with the image,
not in Git. It is not completed production onboarding or credential migration.

Early boot now records the kernel's canonical boot UUID in `/run/sv08/boot.json`.
The administration job controller requires that identity; earlier fixtures supplied
it themselves, exposing a missing connection during clean-image integration.
The regression verifies distinct runtime job identities across boots without
adding a boot ID to persistent slot records.

The non-deployable manifest keeps hardware update operations unavailable during
this initial host test. Installed UI files and pilot login do not establish the
remaining software/network adapters, production TLS/account persistence, signed
release delivery or physical recovery operations.

## Assemble and review

After producing the private host `finalized.json` inventory receipt:

```sh
sudo python3 scripts/assemble_board_diagnostic.py \
  --host build/board-host-v1 \
  --data build/board-data-v1 \
  --recovery build/board-recovery-image-v1 \
  --spl build/board-inputs/u-boot-sunxi-with-spl.bin \
  --work build/board-disk-v1 --execute
```

Use a fresh output for every attempt. The composer formats and checks all six
filesystem files, creates independent recovery boot support, and records the
whole image and per-partition hashes. It does not sign a release or claim
byte-identical repeated builds. Review final disk bytes against each partition,
SPL and both raw environments, plus filesystem contents and source preservation,
before issuing the concrete [USB write procedure](flashing-emmc.md).

The human step is to power down and isolate the printer, connect its spare eMMC
to the USB writer, write the reviewed complete file with verification, reinstall
it, and boot with console logging already running. Retain the factory module.
Do not auto-expand/repartition this diagnostic layout on the 32 GB spare. Exact
artifact location and digest must accompany the write task; this page alone is
not an instruction to write an unfinished artifact.
