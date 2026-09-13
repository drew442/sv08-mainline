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
