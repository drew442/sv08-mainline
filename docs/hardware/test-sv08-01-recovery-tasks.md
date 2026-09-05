# Test printer 01: hands-on recovery tasks

Prepared 2026-09-05. Follow the [recovery plan](test-sv08-01-recovery.md).
No full disk backup, MCU backup, or restoration test is complete. Record results
privately under `local/test-sv08-01/` and `backups/test-sv08-01/`; publish only
sanitized findings. PCB revisions remain unknown.

## 1. Identify adapters and boards

- [ ] Record reader model, supported eMMC connector/voltage, spare module model,
  and the computer/OS that will run the capture. Provide access to that computer
  if remote assistance is wanted. Photograph module labels and orientation.
- [ ] Record ST-Link model and software version. With printer power disconnected,
  photograph both PCB revision labels, MCU markings, oscillator markings, and
  accessible SWD pads/connectors. Identify pin orientation against the actual
  board and schematic; do not infer wiring from a similar board.
- [ ] Arrange separate private storage for a second copy of all backups. Reserve
  at least 16 GB for two original user-area reads, plus space for other evidence.

These tasks can proceed independently. Neither the spare's nominal capacity nor
an MCU runtime target string establishes electrical compatibility or flash size.

## 2. Capture original eMMC offline

- [ ] Confirm idle, zero heater targets and cool hardware; cleanly shut down the
  host, then disconnect printer power. Remove and label the original eMMC.
- [ ] Disable automount on the reader computer before attaching it. Identify the
  original by topology, model, capacity and label. Confirm no partitions are
  mounted or used as swap. Resolve any size discrepancy before imaging.
- [ ] Capture and compare two full reads using the Linux example below, or an
  equivalent recorded procedure on the identified OS. Preserve command output,
  reader identity, tool versions and errors alongside the image.
- [ ] Retain the separate boot-region captures and eMMC metadata already saved
  privately. If the USB reader exposes only the user area, explicitly record
  that limitation; native MMC access was used for the existing boot captures.
- [ ] Copy backups to separate storage and verify hashes there. Label and retain
  the original module; do not use it as the migration destination.

Linux example, **only after source identification and unmounting**. This is a
manual template, not an auto-detecting capture tool. Set `SOURCE` to the reviewed
whole original device, not a partition, and `DEST` to a new directory on private
backup storage. The placeholder intentionally does not name a real device.

```sh
SOURCE=/dev/REPLACE_WITH_REVIEWED_ORIGINAL
DEST=backups/test-sv08-01/offline-original-UNIQUE_DATE
lsblk -b -o NAME,PATH,TYPE,SIZE,MODEL,SERIAL,MOUNTPOINTS "$SOURCE"
findmnt
swapon --show
sudo blockdev --getsize64 "$SOURCE"
# Continue only after confirming 7818182656 bytes and no mounted/in-use children.
umask 077
mkdir "$DEST"  # must be new; parent directory must already exist
```

Run each next command only if the preceding command succeeded. `oflag=excl`
refuses existing output files; `dd` opens the source for reading. Do not add
`conv=noerror` or `sync` to conceal read failures. Confirm sufficient free space
on the destination filesystem first with `df -B1 "$DEST"`.

```sh
sudo dd if="$SOURCE" of="$DEST/user-area.img" bs=4M iflag=fullblock oflag=excl status=progress
sudo dd if="$SOURCE" of="$DEST/user-area-second.img" bs=4M iflag=fullblock oflag=excl status=progress
stat -c '%n %s' "$DEST/user-area.img" "$DEST/user-area-second.img"
cmp "$DEST/user-area.img" "$DEST/user-area-second.img"
sha256sum "$DEST/user-area.img" "$DEST/user-area-second.img"
```

Both files must be exactly 7,818,182,656 bytes, both reads must exit successfully,
and `cmp` must exit zero. Save the hashes, UTC date and device identity in the
private inventory. A second read on the same disk is not a second storage copy.
The offline image's first 4,194,304 bytes can also be compared with the earlier
`user-area-prefix.bin`; investigate differences without assuming corruption.

## 3. Preserve each MCU independently

- [ ] Confirm MCU marking, PCB revision, flash capacity and SWD pin mapping for
  the mainboard; repeat independently for the toolhead.
- [ ] Review ST-Link voltage reference, ground, power/backfeed arrangement and
  software connection mode before connecting. Debug attachment may halt/reset
  the controller; perform only during planned maintenance with loads safe.
- [ ] Read identity and protection state. If protected, stop: do not unlock,
  erase, change option bytes or install a bootloader to obtain a backup.
- [ ] Read each confirmed full flash range twice and compare hashes. Preserve
  readable option-byte information and tool logs. Record base address, size,
  identity, exact command/tool version and errors for each board separately.

Do not choose between the documented 128 KiB toolhead candidate and the runtime
`stm32f103xe` report by guessing. Physical identity and device information must
resolve the range. Clock/offset candidates may be investigated offline, but
must not become flash settings without evidence.

## 4. Restore the spare and demonstrate recovery

- [ ] Identify the spare independently; confirm mechanical/electrical compatibility
  and actual capacity. Record accessible regions and settings. Review the exact
  saved image, target and recovery method before writing it.
- [ ] Restore the original user-area layout without resizing, plus any required
  boot regions/settings established by review. Do not copy every EXT_CSD setting:
  some fields are device-specific or irreversible. No restore command is selected
  until the spare and reader are identified.
- [ ] Verify the written image range, then boot the spare in the printer. Check
  services, configuration, MCU identities and ambient sensor readings with zero
  targets and no motion. Record results; this is not heat or print validation.
- [ ] Document rollback to the retained original and both preserved MCU images
  before migration. Mark recovery verified only after successful demonstration.

Host imaging and MCU identification can be scheduled independently while the
printer is powered down. Sensor identity, repair details and measured temperature
accuracy remain separate bring-up tasks; do not heat to test the restored image.
