# Test printer 01: uploaded backup and ST-Link intake

Date: 2026-09-06. Read-only workstation file inspection and SSH host queries.
Physical PCB revisions, module markings and programmer power wiring remain
unverified. No debugger connection, MCU reset, flash read/write, option-byte
operation, service restart or printer command was issued during this intake.

## Uploaded eMMC image

The uploaded private file is 7,818,182,656 bytes. Its SHA-256 is
`7a90da463b04d19e3325d6c9e1f40cf7b82a78a31007879f05c19ab8f261e5f6`,
matching the owner's supplied hash. Read-only FAT and ext4 checks both exited
zero. The image was exposed through a read-only loop mapping and never mounted;
`debugfs` read its OS identification. Inspection used e2fsprogs 1.47.0 and
fsck.fat 4.2 on the workstation.

Despite the upload directory's `new-emmc` label, the contents identify
**SPI-XI 2.3.3 / Debian 11 bullseye**. Its size and DOS partition layout match
our original-module observations: FAT starts at sector 8192 with 524288 sectors;
ext4 starts at sector 532480 with 14409728 sectors (512-byte sectors).
The owner subsequently confirmed on 2026-09-06 that the source was the factory
module. That report agrees with the file evidence; the directory label is
misleading and is not the source identity. The uploaded file was not renamed or changed.

This establishes file integrity against the supplied hash and clean filesystem
checks. Capture method, source mount/power state, a matching second read, a separate
storage copy and a successful restore are still unrecorded. Boot areas, eMMC
settings/RPMB and MCU flash are not contained in this user-area image. The prior
separate boot-region captures remain private supporting evidence.

The private inspection manifest is beside the upload under
`backups/emmc/2026-09-06-new-emmc/`; raw inspection logs are in
`local/test-sv08-01/inspection-20260906/`. Follow the
[image capture guide](imaging-emmc.md) for additional capture evidence.

## New host checked remotely

The running host reports Debian 13.6 trixie, kernel `5.16.17-sun50iw9` aarch64,
and a **31,272,730,624-byte** eMMC user area. Its boot partition is 268,435,456
bytes and root partition is 8,317,304,832 bytes. This agrees with the built
image's partition sizes, leaving the remaining capacity unused.

SSH and noninteractive sudo work. No failed systemd units were listed; SSH,
networkd and time synchronization services were active. Klipper and Moonraker
were inactive. Kernel and selected device-tree SHA-256 values match the
[built image](test-sv08-01-image.md). The staged Klipper source commit matches
`f0892d82b0f1c1228454f09eb508eddde2250f4b`.

These observations extend the owner's boot report with remote evidence. They
do not establish repeated-boot reliability, HDMI/touch operation, temperature
accuracy, motion, or recovery by swapping modules.

## ST-Link detection and power discrepancy

The host enumerates USB `0483:3748`, reporting ST-LINK/V2. This confirms USB
detection, not programmer authenticity, physical pinout, target voltage or SWD
communication. The owner reports connection to the mainboard's four-pin header.

Sovol's [motherboard/adapter-board flashing guide](https://wiki.sovol3d.com/en/How-to-burn-firmware-to-the-motherboard-adapter-board)
(accessed 2026-09-06; no revision shown) maps 3.3V to 3V3, GND to G, SWDIO to IO
and SWCLK to CK. Its warning explicitly requires the printer to be powered off,
and its procedure uses a separate computer's USB port. That differs from using
the powered printer host as the programmer's USB source. The owner confirmed the printer is powered on. Whether the 3.3 V wire is
connected still needs confirmation. MCU attachment is paused until the power
arrangement is corrected/reviewed. Before changing wiring, cleanly shut down
the host, disconnect printer power and unplug the programmer USB. The documented
arrangement then uses a separate computer with the printer powered off.
Do not assume the listed programmer's 3.3 V pin is a voltage-sense-only input.

The page is a firmware-writing procedure. Its claim of a common vendor binary
for both boards does not establish recovery compatibility for this machine's
different running MCU builds. No linked installer or firmware was downloaded or run.

Neither `stlink-tools` nor OpenOCD is installed on the new host. The configured,
pinned Debian snapshot offers `stlink-tools` 1.8.0-1.1 and OpenOCD 0.12.0-3+b2;
these were inspected as available packages only. No tool has queried the target.
After power/wiring review, identify the MCU and protection state before choosing
its full readout range. Do not unlock, erase, or change option bytes to read it.

The [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-06-backup-and-stlink.json)
records this scope. The [hands-on task list](test-sv08-01-recovery-tasks.md)
tracks the outstanding physical checks.

Follow-up: the owner moved programmer USB to a separate workstation with the
printer powered down. The [mainboard SWD attempt](test-sv08-01-mainboard-swd.md)
records failed target connection and the next physical checks.
