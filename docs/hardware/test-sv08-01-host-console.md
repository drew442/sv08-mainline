# Test printer 01: remote access for physical host testing

Recorded 2026-09-13. New feature development remains paused at the owner's
request. This work prepares physical testing of the existing host OS work.

## Established access and console evidence

Read-only SSH to the printer and the owner's Beelink succeeded today. The printer
still runs `5.16.17-sun50iw9`; Klipper, Moonraker and KlipperScreen are inactive.
No reboot, service change, firmware write, heat or motion was commanded.

The live kernel command line includes `console=tty0 console=ttyS0,115200`.
The live device tree has `chosen/stdout-path = serial0:115200n8`, with `serial0`
pointing to enabled `/soc/serial@5000000`. Its pinctrl selects `uart0` on PH0/PH1.
`/proc/consoles` lists ttyS0 and tty0; `serial-getty@ttyS0.service` is active.
These are measured software settings, not proof of an externally usable console
or the installed PCB revision. Bootloader output has not yet been captured.

Sovol's [mainboard pin drawing](../../upstream/sovol-sv08/Motherboard/MCU_PIN_definition.pdf),
PDF page 1 (printed page 23), depicts a **type-C (USB to UART)** socket above the
other type-C socket on the right edge, with the Ethernet/USB-A/HDMI edge at the
bottom. Its UART0 annotation points to that area. Source revision:
`Sovol3d/SV08` commit `a60644875f8c756d20b3828c9416518b414b5491`, inspected
2026-09-13. The drawing does not establish the installed board revision or USB
bridge model. The separately published MCU schematic does not establish the
host UART circuit. Do not substitute an SV08 Max/Zero or CB1 connector pinout.

## Human connection tasks

**Power isolation:** the host continued running across the owner's reported
printer switch-off/on during this session. Do not assume the printer switch
isolates the host while external cables are attached. USB back-power is a
possible explanation, not an electrically verified cause. Disconnect external
power-bearing cables as well as printer power before physical board work.

### Connection verified on 2026-09-13

The initial cable produced no USB enumeration, even with printer power on.
After the owner replaced it with a data cable, Beelink enumerated a QinHeng
`1a86:7523` USB serial bridge (`bcdDevice=2.64`) using `ch341`, at `ttyUSB0`.
It has no USB serial number, so the generic by-id name is not unique across
multiple identical adapters. Private evidence records its physical by-path name.
No process held the port; ModemManager reported it unsupported by its plugins.

A bounded exclusive-open probe configured 115200 8N1 without flow control and
sent one carriage return. Initial buffered bytes were garbled; the response was
a readable `Password:` prompt. No password or login credentials were supplied.
A second receive-only probe captured the exact ASCII marker
`SV08-CONSOLE-CHECK-20260913`, written through the printer's authenticated SSH
connection to `/dev/ttyS0`. This confirms the host-to-Beelink console path at the
selected settings, rather than relying on a USB descriptor alone. Raw captures
are in ignored `local/test-sv08-01/access-20260913/console-{probe,marker}.json`.

SSH was reachable again, with Klipper, Moonraker and KlipperScreen inactive.
No reboot or firmware/settings change was commanded. The probes are finished;
there is no persistent logger running. SPL/U-Boot/early-kernel capture still
requires starting a logger before a subsequent boot. Normal console open/close
was exercised without an observed host restart; control-line wiring is not
established by this check.

### Complete warm-reboot capture

At 02:19:47 UTC a bounded, receive-only logger opened the identified bridge at
115200 8N1 on Beelink. The owner's subsequent power-on produced a mainboard MCU
USB reconnect at kernel uptime 382 seconds, rather than a new host boot.
SSH still reported the existing host boot. With printer services inactive,
the agent issued `sudo systemctl reboot` through SSH, retaining the serial log
through shutdown, SPL, BL31, U-Boot, Linux and the Debian login prompt.

The host returned over SSH with a changed boot ID, kernel
`5.16.17-sun50iw9`, root `/dev/mmcblk2p2`, and no failed systemd units.
Klipper, Moonraker and KlipperScreen remained inactive. This establishes a
remotely observable warm reboot of the existing bring-up image, not cold-power
behavior or validation of the new A/B OS. No firmware or boot settings were
changed and no heat/motion was commanded.

Measured boot output:

- SPL and U-Boot identify `2021.10-->SPI-CB1`, built 2023-12-30 14:40:23 +0800;
  DRAM reports 1024 MiB. BL31 identifies v2.7 debug and H616.
- SPL says `Trying to boot from MMC2`. U-Boot enumerates `mmc@4020000: 0,
  mmc@4022000: 1`, selects `mmc1`, and loads `/boot.scr` from `mmc 1:1`.
  Linux later enumerates the spare as `mmcblk2`, 29.1 GiB. These namespaces differ.
  This mapping applies to the captured boot chain, not an untested replacement.
- U-Boot cannot read `uboot.env` from `mmc1:1`. The script prints
  `U-boot loaded from SD` despite the eMMC load path and reports a card voltage
  selection timeout. Neither that script message nor the missing FAT environment
  proves the new design's redundant raw environment locations work.
- BL31 reports an RSB initialization error; Linux reports HDMI-audio, AC200 and
  Panfrost probe errors. Shutdown reports an unsupported 10-minute watchdog
  timeout. Boot still completes; these messages are retained as baseline issues,
  not silently classified as harmless or new-kernel failures.

The logger was stopped after SSH returned. The private raw log is
`local/test-sv08-01/access-20260913/boot-20260913-01.raw`, SHA-256
`d491757094ab472e7976fc38196a3d6fdaeeb09b6e4cf68db7de703400ac3a4f`.
Adjacent event timestamps and `after-reboot.txt` retain capture and live-check
evidence. No persistent logger remains running. A true cold boot still needs
an established power-isolation/capture arrangement.

1. With the printer shut down and power disconnected, locate the socket labelled
   **USB to UART** on the actual mainboard and compare it with the linked drawing.
   If the label/location differs or is unreadable, provide a clear photograph
   before connecting. The MCU's four-pin ST-Link header is a different interface.
2. Connect a normal USB data cable from Beelink to that **USB to UART** USB-C
   socket. Leave raw UART pins and the other USB-C socket alone for this test.
   No separate TTL adapter or ST-Link is required for this documented USB path.
3. Report that the cable is attached. We can inspect Beelink's USB enumeration
   while printer power is off; USB enumeration alone does not establish normal
   host power or successful boot. Arrange the next power-on with capture running
   so the beginning of the boot log is retained.
4. Optionally connect printer HDMI output to capture-device HDMI input, and its
   USB capture connection to Beelink. Use passthrough to retain the touchscreen
   display if supported. Connect the HID emulator's target/device side to a
   printer USB host port and its control side to Beelink. Record the device models
   and control interface so we can drive the actual supported API.

HDMI capture observes video only after the boot stack enables it. It cannot
replace UART when debugging a failure before video/network startup. HID provides
keyboard/mouse input; it does not establish real touchscreen calibration. The
touchscreen's own USB touch connection must remain available for that test.

## Agent work after connection

- Compare Beelink USB inventory before/after attachment; record VID/PID, driver,
  topology and stable `/dev/serial/by-id/` or by-path identity privately. Today's
  inventory had no external capture device or serial adapter.
- Check device permissions and competing serial consumers. Open only the newly
  identified console at **115200, 8 data bits, no parity, 1 stop bit, no flow
  control**, initially without transmitting input. Retain timestamped output in
  ignored `local/test-sv08-01/`. Identify any bridge-specific control-line/reset
  behavior before interactive use; do not assume ST-Link serial support.
- Treat a logger's process start as insufficient. Before the next power cycle,
  require a recorded `ready` event after an exclusive open by the account that
  owns the capture. The 2026-09-15 v6 boot lost its early trace because the
  unprivileged logger lacked permission for the dialout-owned bridge; a later
  root-owned receive-only logger could open it and record the Debian login prompt.
- Capture an attended normal boot and confirm readable SPL/U-Boot/kernel output
  and the expected Linux host. A serial getty does not imply password login is
  provisioned: the existing image uses SSH keys. SSH remains the normal shell.
- Inventory capture formats and the HID control interface if attached; verify
  video and harmless input on the identified host before relying on remote UI.

## Minimum path to the first new host boot

The owner accepts the existing backups and USB-reader/ST-Link recovery paths.
Additional backups, a demonstrated restore, or completion of all pending admin
features are not prerequisites for this bounded boot test. Both MCU bootloaders
and matching Klipper applications have already been written and USB updates
verified; see [MCU evidence](test-sv08-01-mainboard-usb.md).

Remaining engineering work is to select/pin a board-compatible kernel, DT and
boot chain; assemble a separately named bootable test artifact with its manifest
and hashes; and check its layout, boot-file references and storage/network
drivers. The independent 512 MiB QEMU recovery filesystem is **not** a whole-device
printer image. Existing QEMU mode, RAUC and rollback evidence need not be repeated
unless relevant changes invalidate it. Full release/UI acceptance comes later.

Before a write, resolve the actual spare eMMC destination afresh from capacity,
topology and identity, and bind the chosen artifact hash and intended write scope
to it. Linux MMC numbering is not U-Boot numbering. Review those concrete inputs
within the owner's existing authorization; no additional blanket approval is
required. Keep assembly, writing and boot activation separate.

The first trial should establish boot, storage, Ethernet/SSH and diagnostic logs
with printer services inactive. UART is the preferred early-boot observation
path, not a requirement to finish every optional capture/HID facility. Keep
heater/motion commissioning separate from host boot testing.
