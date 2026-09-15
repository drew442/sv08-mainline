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

If a reviewed runtime or host-UI correction is required after a diagnostic root
has been finalized, preserve that root unchanged and copy it to a fresh private
build directory. The normal staging commands reject an existing runtime/UI.
The narrowly scoped `--refresh` options may restage only the expected regular
project directories and outputs in that copied root; they reject symlinks and
unrecognized files before replacing either directory. Regenerate the initramfs
and create a new `finalized.json` receipt before composition. This construction
exception is limited to non-deployable diagnostic roots by
[decision 0016](../decisions/0016-controlled-host-restaging.md).

A clean root may receive its first-boot owner public-key seed from the separate
preserved data tree with `integrate_host_os.py --owner-key PATH`. The input must
be a non-empty regular public-key file and is copied into the runtime seed; do
not print it, add it to source control, or substitute credentials for it.

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

## Completed offline result

The first full disk passed independent byte review; the
[artifact record](host-board-image-20260913.json) contains its hashes and scope.
The raw image is **7,818,182,656 bytes**, SHA-256:

```text
8777fad2790757ff333f9c6059f75dc14f6bcbc04b56a1266a5c00e6c4e86b94
```

Review checked the whole hash, both GPT CRCs and all six exact records, every
embedded partition against its source, SPL placement, both complete raw
environments, slot scripts/kernel/initramfs/DT, independent recovery manifest
binding, filesystem checks and owner-access metadata. The finalized data
filesystem root is 0755, allowing traversal to the explicitly protected persistent
tree; private preparation-directory permissions were not assumed to be filesystem
root permissions. Source preservation and the authoritative recovery parent's
receipt were rechecked independently.

Each root retains **636,981,248 bytes** free; complete recovery, including its
independent raw kernel and DT, retains **165,109,760 bytes** free. These are initial
filesystem measurements, not full-workload/update-space acceptance. All 35 focused
recovery, boot-identity and composer tests passed. The new SPL was subsequently executed but stopped during DRAM initialization;
the complete host and recovery have not executed on the printer (see below).

On 2026-09-13 the owner moved the installed spare to a USB writer. Its measured
31,272,730,624-byte capacity and both old filesystem UUIDs matched the prior
printer inspection. The reader identified as USB `05e3:0747`; private identity
details and logs remain local. The target was unmounted and separate from the
build host's system disk.

The raw source hash was rechecked, then exactly 7,818,182,656 bytes were written
through an exclusively opened target, flushed, and completely read back using
direct I/O. The SHA-256 matched the reviewed image above. GPT readback and all
six kernel partition identities/sizes also matched. All partitions were unmounted
and the USB writer was powered off for removal. This establishes a verified spare
write, not a successful physical boot of the new loader or OS.

## Write this candidate and prepare its first boot

Obtain `test-sv08-01-ab-diagnostic-20260913.img.xz` and its matching `.sha256`
file from the private `artifacts/board-diagnostic-20260913/` directory. These
files and `owner-access.txt` are not in Git or a public release. The access file
contains the unique pilot login and identity fingerprints; keep it private.
Use this candidate's checksum, not the original single-root image's checksum.

The compressed file is **1,084,044,228 bytes** (about 1.01 GiB), SHA-256:

```text
7068ee93ea123a62bc78317cc6665eac3cbf3c37503db953be180ac346c3da82
```

Its complete expansion was checked against the raw image's size and SHA-256
above. The transferred local copy also passed the compressed-file checksum.

Verify the compressed download before selecting the USB writer:

```powershell
# Windows PowerShell: compare with the matching .sha256 file.
Get-FileHash .\test-sv08-01-ab-diagnostic-20260913.img.xz -Algorithm SHA256
```

```sh
# Linux
sha256sum -c test-sv08-01-ab-diagnostic-20260913.img.xz.sha256
# macOS
shasum -a 256 -c test-sv08-01-ab-diagnostic-20260913.img.xz.sha256
```

1. Arrange a clean printer shutdown. Disconnect mains power and every possible
   USB power source, including the console, before removing the spare module.
   Earlier switch-off with USB attached did not stop host uptime; do not assume
   the printer switch alone isolates the board.
2. Fit the spare to the unplugged USB writer, then connect the writer. Cancel
   operating-system format/initialize prompts. Writing replaces the spare's
   current bring-up system; retain the factory module unchanged.
3. Use the [graphical write and validation workflow](flashing-emmc.md#write-and-validate)
   on Windows, Linux or macOS, selecting **this A/B `.img.xz` filename**. Check
   the target's identity and capacity, and wait for successful write validation.
4. Eject the writer, unplug it, and reinstall the spare with all printer power
   sources disconnected. Keep Ethernet connected for the host test.
5. Coordinate console logging **before reconnecting USB or powering the host**.
   The logger must already be watching for the UART adapter because USB may
   itself supply power. Report which action first causes output; cold-boot
   electrical isolation remains distinct from a warm-reset capture.
6. On successful A boot, use the observed DHCP address. SSH uses **`sv08`**, the
   existing authorized owner key and the new private pilot host-key fingerprint.
   The administration pilot is at `https://<observed-address>:9090`; compare the
   certificate fingerprint and use the credentials in `owner-access.txt`.

Expect a host diagnostic system with printer services disabled. Do not request
heat or motion. Avoid repeated exploratory reboots: the seeded A budget is three
attempts, followed by recovery. The operator running the test should inspect the
actual boot/slot/devices, persistent state, service failures, network and thermal
readings before explicitly refreshing an attempt budget or testing B. Automatic
health confirmation is absent. Graphical recovery operation and the new loader
must be recorded as physical results after they run, not inferred from this file.

## First physical boot: stopped in SPL DRAM initialization

At 06:50:39 UTC on 2026-09-13, the already-running receive-only serial logger
captured 58 bytes from test-sv08-01 after the owner reinstalled and powered the
spare. The complete output was the U-Boot SPL 2026.07 banner followed by `DRAM:`.
No further output appeared during subsequent checks. The owner reported blank
HDMI. All-power isolation preceding this attempt was not independently observed;
PCB revision remains unknown.

The pinned U-Boot source (`board/sunxi/board.c`, lines 659–662, commit
`ece349ade2973e220f524ce59e59711cc919263f`, read 2026-09-13) prints this marker
immediately before `sunxi_dram_init()` and the size after its return. This locates
the observed failure before U-Boot proper, A/B dispatch, recovery and Linux;
it does not establish a display-driver problem or identify an exact failing
register. The SHA-256 of the private raw capture is recorded in the linked JSON.

Source inspection found two unbounded read-calibration polling loops in
`arch/arm/mach-sunxi/dram_sun50i_h616.c`, inside
`mctl_phy_read_calibration()`. Other waits use the one-second timeout helper in
`dram_helpers.c`. These are diagnostic leads, not proof that either loop caused
this stop. The inherited CB1 timing/drive/ODT and address-map settings remain
unvalidated on this board. Do not guess new voltages or treat the earlier Linux
clock report as proof of correct DRAM training.

Next preparation is a separately built/reviewed SPL with progress markers and
bounded training diagnostics, retaining the existing electrical settings, plus
comparison with the preserved working vendor loader. A UART adapter cannot
rewrite a processor stopped here: no U-Boot command prompt or OS is available,
and this CH340 connection is not a FEL USB connection. Return the spare to the
USB writer with mains and USB power disconnected before removal. Preserve the
current image/evidence and review any replacement loader and its write range;
do not repeat the same full image hoping to repair its verified contents.

The next [instrumented SPL attempt](host-spl-diagnostics.md) retains electrical
settings and uses a separately reviewed loader-only write. Its resulting media
identity is distinct from the complete download above.
