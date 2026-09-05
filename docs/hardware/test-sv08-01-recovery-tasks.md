# Test printer 01: hands-on recovery and image tasks

Updated 2026-09-05 to follow the owner's selected workflow: retain the factory
eMMC as the host rollback baseline and write the new image to the blank 32 GB
spare. A full factory disk-image file is optional; it does not block this work.
See the [image guide](test-sv08-01-image.md) and [recovery plan](test-sv08-01-recovery.md).

## Next: write and boot the spare

- [ ] Record the reader and spare module models, actual byte capacity and
  connector/voltage compatibility. Identify the writer computer and its OS.
- [ ] Follow the [Windows, Linux or macOS instructions](flashing-emmc.md):
  verify the image SHA-256, select the blank spare as the whole destination,
  write the image and complete the writer's readback validation. Do not format
  the Linux partitions if the computer prompts after writing.
- [ ] Confirm idle and zero heater targets; shut down the factory host cleanly,
  disconnect power, then remove and label the factory eMMC. Retain it unchanged.
- [ ] Insert the spare in the verified orientation, connect Ethernet and boot.
  Record HDMI output, DHCP address and SSH access as user `sovol` with the
  previously authorized key. The hostname is `sv08-mainline`; its address may
  differ from the factory host. No password login or Wi-Fi setup is included.
- [ ] Capture boot/storage/network evidence following the image guide. Do not
  activate printer services or command heat/motion for this host test.
- [ ] Demonstrate swap-back to the original after clean shutdown/power removal,
  with both MCUs unchanged. Record the outcome as a host rollback test.

The image is a host bring-up candidate, not yet a printing system. Unallocated
space on the 32 GB spare is intentional; expansion is a later recorded operation.

## Independent: prepare MCU preservation

- [ ] Record the delivered ST-Link's markings, USB identity, firmware/tool version
  and connector labels. The owner supplied Amazon ASIN B0C7QG6LHQ and a four-pin
  cable description; this does not establish the physical pinout or voltage.
- [ ] With power disconnected, record PCB revisions, MCU and oscillator markings,
  SWD pads/connectors and orientation for both printer boards separately.
- [ ] Verify SWD mapping, voltage reference, ground and power/backfeed arrangement
  before connecting. Debug attachment can halt/reset a controller; use planned
  maintenance with loads safe.
- [ ] Read device identity and protection state. Stop if protected: do not unlock,
  erase, alter option bytes or install a bootloader to obtain a backup.
- [ ] Read each confirmed full flash range twice and compare hashes; preserve
  readable option-byte state, tool logs, base address and length privately.

The documented toolhead 128 KiB candidate and its runtime `stm32f103xe` report
must be reconciled through actual device evidence. The programmer listing's
STM32F103C8T6 is not a printer MCU identification. Host image testing can proceed
without an ST-Link connection; MCU flashing cannot inherit the host rollback path.

## Optional additional host preservation

- [ ] Make a full offline image of the factory module with repeat-read comparison,
  retaining separately captured boot regions/settings; follow the
  [general workflow](discovery-and-backup.md).
- [ ] Copy private archives and manifests to separate storage and verify hashes.

Raw evidence, machine identifiers and private keys belong in ignored local
storage. No hardware profile is validated by possession of recovery adapters.
