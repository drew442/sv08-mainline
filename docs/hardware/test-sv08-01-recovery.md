# Test printer 01: recovery preparation

Status: planned, 2026-09-05. The owner reports an ST-Link, an eMMC USB reader and
a spare nominal 32 GB eMMC module. Models, connector compatibility and recovery
operation have not been verified. No raw storage or MCU writes have been made.

The proposed sequence preserves the original eMMC as the baseline and uses the
spare for migration. First demonstrate that the preserved system can be restored
to the spare; then make software changes there. Keep host replacement and MCU
firmware replacement as separate, recorded steps.

## Existing preservation evidence

| Item | Current state | Next evidence |
| --- | --- | --- |
| Configuration, logs, services, selected boot files | Private archive readable; 30 non-log hashes rechecked | Second private copy; log capture is not atomic |
| Loaded Klipper configuration | All 116 parsed archived sections match captured API values | Preserve local calibration when converting |
| eMMC user area | Size and mounted layout identified | Offline image, exact byte count, SHA-256 and repeat-read comparison |
| eMMC boot areas | Two 4,194,304-byte areas enumerated | Separate images and readback hashes; verify reader access |
| eMMC settings | Incomplete | Readable device/boot configuration metadata and a restore interpretation |
| Mainboard firmware | Matching vendor artifact candidate identified | Physical identity and complete SWD readback |
| Toolhead firmware | Runtime version identified; no matching file located | Physical identity and complete SWD readback |
| Spare eMMC | Owner reports 32 GB capacity | Model, electrical/mechanical compatibility, actual capacity and restore test |

See [discovery](test-sv08-01-discovery.md) and
[firmware evidence](test-sv08-01-firmware.md) for the completed checks.

## Host preservation sequence

1. Identify the computer/OS used for the USB reader and record reader/module
   models. This coding workspace currently exposes only virtual disks, so it
   has not identified an attached reader or spare module.
2. Arrange a shutdown while the printer is idle. After clean shutdown, remove
   power before handling the eMMC. Record the original module and connector
   orientation; check the spare's compatibility before inserting it.
3. On the reader's computer, identify the newly attached original module by
   device topology, model and capacity. Keep its filesystems unmounted and
   disable automount for the capture. Do not select a source by a remembered
   `/dev/sdX` or `/dev/mmcblkX` name.
4. Capture the complete original user area to a new private file. Expected
   source size from the printer is **7,818,182,656 bytes**; resolve discrepancies
   before accepting an image. Capture any separately exposed boot areas and
   readable eMMC configuration metadata. If the reader omits them, record that
   gap and choose a suitable MMC access path before declaring preservation complete.
5. Verify file sizes and SHA-256 hashes; compare a second complete source read
   against the saved image. Retain a second private copy on separate storage.
   Record source identity, tool/version, command, date, regions and read errors.
6. Remove and label the original module for retention. Identify the spare
   independently. Prepare the exact restore source, destination and relevant
   device settings for review before writing the spare.
7. Initially restore the original layout without resizing. Verify the written
   image range and required boot areas/settings, then test boot and existing
   service/configuration identity with heater targets zero and no motion. Use
   the spare's additional capacity only in a later, separately recorded change.

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
