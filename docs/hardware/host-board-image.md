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
and create a new `finalized.json` receipt with
[`finalize_diagnostic_host.py`](../../scripts/finalize_diagnostic_host.py)
before composition. This construction exception is limited to non-deployable
diagnostic roots by [decision 0016](../decisions/0016-controlled-host-restaging.md).

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
  --spl-record docs/hardware/host-spl-diagnostics-20260914-v5.json \
  --work build/board-disk-v1 --execute
```

Use a fresh output for every attempt. The composer formats and checks all six
filesystem files, creates independent recovery boot support, and records the
whole image and per-partition hashes. It does not sign a release or claim
byte-identical repeated builds. Review final disk bytes against each partition,
SPL and both raw environments, plus filesystem contents and source preservation,
before issuing the concrete [USB write procedure](flashing-emmc.md).

`--spl-record` is required. It binds the supplied loader to its non-deployable
artifact record and manifest hash, verifies the target profile and requires the
reviewed 8192-byte loader placement. It prevents a newly composed image from
silently using the historical loader record.

## Rebuilt v2 artifact and verified eMMC write

The private `0.1.0-board.2` diagnostic host root restages the corrected
first-boot persistent owner-key initializer, the immutable-mode package-backup
condition and the reviewed host UI. Its owner-key seed byte-matches the
separately preserved data tree. The root receipt confirms printer and RAUC
services remain masked and that no QEMU fixture is included. The new complete
composition binds the independent v5 diagnostic loader record rather than the
historical loader record.

The [v2 artifact record](host-board-image-20260915-v2.json) identifies the
private raw and compressed files. A standalone read-only verifier independently
checked the whole raw image, the loader span, both redundant environments, all
six embedded partition images and GPT validity. XZ integrity and a complete
decompressed byte-stream hash then matched the recorded raw hash. This remains a
non-deployable diagnostic candidate.

The identified spare was written on 2026-09-15 with the complete 7.82 GB v2
image. Before writing, its capacity, v5 loader, six PARTUUIDs and unmounted
state matched the recorded target. A separate direct-I/O readback of the entire
written footprint returned the reviewed raw hash. The six partition identities
and both raw environment copies then matched the composed image, and the reader
was powered off. The [v2 record](host-board-image-20260915-v2.json) contains the
sanitized evidence. A receive-only serial capture was armed before the first v2
physical boot.

## First v2 physical boot

The first captured v2 boot reached U-Boot, Linux `6.18.51-sv08-candidate1` and
the `sv08` login prompt. Cockpit HTTPS returned 200 and the seeded owner key
authenticated as `sv08`. The host started with its intended read-only A root and
separate writable data partition, found no failed units, and retained both the
state registry and owner key. NetworkManager obtained the reserved wired address.
Printer services remained runtime-masked and inactive; this boot issued no
heater, motion or MCU command.

Read-only runtime enumeration reports the HDMI connector connected with 1024×600
among its advertised modes, and exposes the touchscreen as
`wch.cn USB2IIC_CTP_CONTROL` on `mouse0`/`event0`. The MGS1 camera has two video
nodes while Cedrus remains `video0`; both wireless interfaces are present but
unassociated. The machine reached multi-user in 19.379 seconds (5.964 seconds
kernel plus 13.414 seconds userspace). These are inventory observations only:
the visible display, touch input, v2 camera capture, Wi-Fi association and
reliability still need their respective tests.

The same capture reports **512 MiB** DRAM, and Linux exposes 485,376 KiB after
reservations. Its successful auto-detection is one rank at 16-bit width, with
10 columns and 15 rows. The exact same v5 loader reported one rank at 32-bit
width with the same size geometry and **1 GiB** on its earlier cold boot. The
serial trace records unsuccessful rank/width candidates before each success.
This demonstrates that the rebuilt host can operate with the detected capacity,
but does not establish the physical DRAM capacity, safe memory reliability or a
solution to the differing results. The [v2 record](host-board-image-20260915-v2.json)
contains the capture and read-only host evidence.

Read-only inspection of the raw redundant U-Boot environments found both CRCs
valid. The retained primary copy is flag 1 with three A attempts, while the
newer redundant copy is flag 2 with two A attempts. This is the expected bounded
attempt decrement after the first physical A boot. It is not a health
confirmation, an A/B rollback result, or permission to spend another attempt on
an exploratory reboot.

## Second v2 A boot

A controlled warm reboot with a new receive-only console capture again reached
U-Boot, Linux, the serial login prompt and owner-key SSH. This time the loader
selected one rank at 32-bit width and reported **1 GiB**; Linux exposed 999,672
KiB after reservations. The successful size geometry remained 10 columns and 15
rows. The root was read-only, all five printer service names were inactive, and
there were no failed systemd units. Both redundant environments remained
CRC-valid: the newer primary flag-3 copy contains `BOOT_A_LEFT=1`, and its
flag-2 peer retains two A attempts. One bounded A attempt now remains. The
alternating 16-bit/512 MiB then 32-bit/1 GiB result confirms only that the
current auto-detection cannot identify the board capacity reliably.

## Exhaustion and independent recovery boot

The final A attempt again reached serial login and owner-key SSH, with the
32-bit/1 GiB result and zero failed units. Its flag-4 environment copy recorded
`BOOT_A_LEFT=0`; B was not admitted. The next captured reboot selected the
independent recovery partition as designed. Recovery ran its root from
`/dev/mmcblk1p5` read-only with `norecovery`, mounted its own squashfs `/usr`
read-only, and started `sv08-recovery-display.service` with no restart or failed
units. Its startup report showed the dedicated local GTK process active.

This recovery build intentionally has no mounted host state registry and no
`recovery-media-policy.json`, so it exposes **Check storage** only; boot, export
and restore actions remain unavailable. The normal host SSH endpoint was not
reachable from the test network. Physical display appearance and touch behavior
remain unobserved. The capture confirms independent recovery selection and its
read-only local UI startup; it does not validate recovery-media integration or
user-data restoration.

A private 128 KiB rearm pair has been built from the observed newest flag 4. It
contains independently CRC-valid flag-5 and flag-6 copies with the reviewed
diagnostic policy (`BOOT_ORDER=A`, `BOOT_A_LEFT=3`, `BOOT_B_LEFT=0`). The image
was written only to the identified spare's 4 MiB and 8 MiB environment regions.
Both copies matched direct readback with valid CRCs and flags 5/6; the loader and
six partition identities remained unchanged. The reader was powered off. The
existing factory-sized GPT warning on the larger spare was observed but not
repaired or expanded.

## Rearmed normal A boot

After reinstallation, the normal host again accepted the owner SSH key, mounted
root A read-only, retained its state registry, found zero failed units and kept
printer services inactive. The newer CRC-valid environment copy is flag 7 with
`BOOT_A_LEFT=2`; its flag-6 peer retains the seeded three-attempt state. This
confirms the rearmed normal A path was selected once.

The receive-only boot capture had been armed, but it expired before power-on.
A later capture contains only the serial login prompt. The boot therefore has
SSH, mount, state and environment evidence but no complete SPL/U-Boot trace; it
does not establish boot reliability or replace a captured test.

On this rearmed host, a non-persistent 512 MiB userspace allocation completed
three full buffer writes and SHA-256 reads using `0x00`, `0xaa` and `0x55`.
All three expected hashes matched in about 2.7 seconds each, and the host still
had zero failed units. This is a bounded check of the currently mapped 1 GiB
configuration, not a full-memory, soak, cold-boot or DRAM-capacity test.

The MGS1 UVC camera at `/dev/video1` also captured and FFmpeg-decoded 30 MJPEG
frames at 640×480 with a requested 15 fps. The 2,575,264-byte private capture
was held only in `/tmp` (tmpfs), then the camera was restored to its prior
1280×720/25 fps format. No systemd unit failed. This is a short passive camera
test; it does not establish long-duration streaming, video presentation or
behavior while printing.

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
