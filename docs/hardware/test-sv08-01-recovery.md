# Test printer 01: recovery preparation

Status: partial preservation; spare boot owner-reported 2026-09-06. The owner reports an ST-Link, an eMMC USB reader and
a spare nominal 32 GB eMMC module. Models, connector compatibility and recovery
operation have not been independently verified. The owner reports that the
new image has booted on the new eMMC; no MCU write or completed restore test
is established by that report.

The owner has selected a new-image workflow: retain the factory eMMC unchanged
as the host rollback baseline and write the new host image to the blank spare.
A full factory image file and restoration onto the spare are optional additional
preservation, not prerequisites for this host-only experiment. See the
[image decision](../decisions/0002-first-emmc-image.md) and
[image guide](test-sv08-01-image.md). MCU replacement remains separate and still
requires its own preservation and recovery evidence.

The owner's ST-Link listing is [Amazon ASIN B0C7QG6LHQ](https://www.amazon.com.au/dp/B0C7QG6LHQ),
described as “ST-Link V2 Emulator Downloader Programmer STM32F103C8T6 STM8 STM32
with 4Pin GPIO Cable”. Source: owner, 2026-09-05; direct listing access failed
on that date. This identifies the purchase listing, not the delivered adapter's
pinout, genuine ST provenance, firmware, voltage behavior or target MCU identity.
The STM32F103C8T6 in the listing must not be recorded as either printer MCU.

## Existing preservation evidence

| Item | Current state | Next evidence |
| --- | --- | --- |
| Configuration, logs, services, selected boot files | Private archive readable; 30 non-log hashes rechecked | Second private copy; log capture is not atomic |
| Loaded Klipper configuration | All 116 parsed archived sections match captured API values | Preserve local calibration when converting |
| eMMC user area | Factory-module image uploaded; owner confirmed source; supplied SHA-256 and read-only filesystem checks pass | Repeat-read/capture record, second storage copy and restore test |
| eMMC boot areas | Both 4,194,304-byte regions captured twice; reads match, all zero | Second storage copy; restore interpretation |
| eMMC settings | Decoded EXT_CSD and partition table captured read-only | Review settings against identified spare; RPMB not captured |
| Mainboard firmware | Two matching full 512 KiB SWD reads and option-byte captures; vendor binary matches installed prefix | Physical markings and restore test |
| Toolhead firmware | Two matching full 128 KiB SWD reads and option captures; embedded identity matches runtime | Physical markings and restore test |
| Spare eMMC | Owner reports 32 GB capacity | Model, electrical/mechanical compatibility, actual capacity and restore test |

See [discovery](test-sv08-01-discovery.md) and
[firmware evidence](test-sv08-01-firmware.md) for the completed checks.

## Latest intake

The [2026-09-06 backup and ST-Link intake](test-sv08-01-backup-and-stlink.md)
validates the uploaded factory-system image and remotely confirms the new host
on a 31,272,730,624-byte module. ST-Link USB detection succeeded; MCU attachment
was initially paused because the powered-on printer differed from Sovol's
four-wire procedure. The owner subsequently powered down and moved programmer
USB to a separate workstation. After wiring confirmation and USB extension
removal, [OpenOCD direct SWD](test-sv08-01-mainboard-swd.md) succeeded with the
ST-Link/V2. Two full mainboard flash reads and option-byte captures match;
[Toolhead preservation](test-sv08-01-toolhead-swd.md) subsequently completed with
two matching full reads; restoration tests remain outstanding. See the
[Katapult assessment](test-sv08-01-katapult.md) for the proposed next step.

## Completed remote preparation

On 2026-09-05, SSH inspection found ready/standby, zero heater targets, hotend
31.62°C and bed 29.68°C. Root resolved to the same recorded eMMC identity and
7,818,182,656-byte user area; the physical PCB revision remains unknown.

Both boot regions were read twice with `dd` over SSH, with `force_ro=1` retained.
Each is 4,194,304 zero bytes with SHA-256
`bb9f8df61474d25e71fa00722318cd387396ca1736605e1248821cc0de3d3af8`.
The first partition starts at sector 8192 (512-byte sectors). The preceding
4,194,304 bytes were also captured twice and matched, SHA-256
`cc3136983e9611667cd4fbda329c2b6c168a9b7097da59665083c8fd37e2b71a`.
This prefix includes a literal `eGON.BT0` at byte 8196; that string alone does
not establish the complete boot chain or a working restore method.

Read-only `mmc extcsd read` reports `PARTITION_CONFIG=0x00`,
`BOOT_BUS_CONDITIONS=0x00`, `BOOT_WP=0x00`, `BOOT_WP_STATUS=0x00`,
`RST_N_FUNCTION=0x00`, and `PARTITION_SETTING_COMPLETED=0x00`.
The reported RPMB size multiplier is `0x04`; RPMB contents were not captured.
Do not replay settings to the spare without field-by-field review.
Tools: printer coreutils 8.32-4 and mmc-utils 0+git20180327.b4fe0c8c-1.
The [kernel MMC tools documentation](https://cdn.kernel.org/doc/html/latest/driver-api/mmc/mmc-tools.html)
describes EXT_CSD inspection (accessed 2026-09-05).

The installed Klipper, Moonraker and KlipperScreen directories, including their
Git metadata and local modifications, were archived privately (76,685,388 bytes;
3,693 archive members). Every regular member was read successfully. This is a
live, non-atomic source preservation copy; symlink targets outside those trees,
Python environments and other host state are not included.

Private files, identities, commands, sizes, hashes and repeat-read results are
in `backups/test-sv08-01/recovery-20260905/manifest.json`; runtime evidence is
in `local/test-sv08-01/recovery-20260905/`. These live partial reads do not
capture the filesystems or constitute a full disk backup. At that stage no MCU backup or
restoration test was complete. No hardware writes or operating changes were made
during those host reads. The later mainboard capture is recorded above.

The [hands-on task list](test-sv08-01-recovery-tasks.md) provides ordered work,
and the [image capture guide](imaging-emmc.md) covers offline reads on Windows,
Linux and macOS, with reader region limits explicit. Writing/booting the spare, SWD attachment and spare identification require
physical access. A separate copy and offline factory imaging remain optional
additional host preservation under the owner-selected workflow.

## Host preservation sequence

1. Keep the factory eMMC installed while gathering read-only build inputs. Do
   not write or reconfigure it for migration.
2. Build and inspect the new image as an ordinary workstation file. Confirm
   its hash and that the blank spare is large enough and mechanically/electrically
   compatible. Identify the USB writer's destination independently.
3. Write only the new spare, using a whole-device image writer and readback
   verification. The original module is not a writing target.
4. Once ready to swap, confirm idle/zero targets, cleanly shut down the host,
   disconnect power, remove and label the factory module, and insert the spare
   with the verified orientation. Retain the original unchanged.
5. Boot the new host and check Ethernet/SSH, storage, boot logs and HDMI. Printer
   services are not installed in the host bring-up candidate. Record actual
   results before extending the image or activating any printer service.
6. If host bring-up fails, power down and reinstall the original. This rollback
   assumes both MCUs have remained unchanged. Record a successful swap-back test
   separately; retained media alone is not demonstrated recovery.

An optional offline factory image can still follow the
[general preservation workflow](discovery-and-backup.md), including boot regions,
metadata, repeat reads and a separate storage copy. It is not a gate for building
or boot-testing this spare image.

Linux exposes MMC boot areas separately as `mmcblkXboot0` and `mmcblkXboot1`,
with writes disabled by default. A user-area image alone does not capture those
areas. Keep that protection in place during reads. See the
[Linux MMC partition documentation](https://cdn.kernel.org/doc/html/latest/driver-api/mmc/mmc-dev-parts.html)
(checked 2026-09-05). Reader exposure and the SV08's actual boot requirements
still need verification; do not assume every USB reader exposes native MMC regions.

On this printer, the same-size eMMC appeared as `mmcblk2` in the initial capture
and `mmcblk1` after reboot. The later root/boot sources were `mmcblk1p2` and
`mmcblk1p1`. These observations are not reusable backup or restore targets.

## MCU preservation sequence

For **each board separately**, record PCB revision, MCU marking, flash capacity,
SWD connector/pad mapping and orientation, voltage reference and power arrangement.
Compare against the corresponding [stock hardware references](stock-sv08.md).
The mainboard and toolhead must retain separate backup records.

Use an identified ST-Link and a recorded tool version; ST's
[STM32CubeProgrammer](https://www.st.com/content/st_com/en/stm32cubeprogrammer.html)
supports memory inspection/extraction (checked 2026-09-05). Schedule connection
as a maintenance operation: debugger attachment can affect the running MCU.
Do not connect while printing or heating.

Read and record device identity and protection state before attempting a dump.
Preserve the full confirmed flash address range and readable option-byte state,
then perform a second read and compare hashes. Do not unlock, erase, modify option
bytes or write a bootloader to make a backup possible. If readout protection
blocks the capture, stop and reassess recovery. The
[general backup workflow](discovery-and-backup.md) cites ST's erase-on-unlock
behavior for STM32F10xxx.

Only after preservation and target identification should a concrete firmware
write procedure be prepared. The existing mainboard artifact's zero offset and
8 MHz build selection are supporting evidence, not verified settings for either
physical board. Swapping back the original eMMC alone will not restore changed
MCU firmware; host and both MCU versions must be recorded together for rollback.

## Acceptance

Advance `recovery_verified` only after the documented restoration has actually
been demonstrated on the identified hardware. Possessing adapters, a readable
archive, or a candidate vendor binary does not meet that criterion.
