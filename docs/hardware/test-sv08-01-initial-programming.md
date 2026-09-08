# Test printer 01: initial Katapult programming preparation

Prepared 2026-09-07. The [toolhead installation](test-sv08-01-toolhead-katapult.md)
has now executed with complete readback verification. The
[mainboard installation](test-sv08-01-mainboard-katapult.md) also completed, after
a failed write and a verified erased-state recovery. Both factory rollback
procedures remain unexecuted. The staging description below
records preparation before that hardware session.

## Staged inputs

The host has the pinned Katapult source at `/opt/sv08-mainline/katapult` and
both reviewed binaries at `/opt/sv08-mainline/firmware/mcu-usb-v1/`.
The existing Klipper virtual environment runs its `flashtool.py --help`
successfully. Firmware hashes match the [build record](test-sv08-01-mcu-build.md).

The separate programming workstation has private inputs under
`~/sv08-recovery/install-20260907/`:

- `install-toolhead.cfg` and `install-mainboard.cfg`.
- `rollback-toolhead.cfg` and `rollback-mainboard.cfg`.
- Each board's complete original flash and an expected complete flash image
  containing only Katapult followed by erased bytes.
- The reviewed Katapult binary and SHA256SUMS for all staged inputs.

All transferred checksums pass. Tcl command completeness was checked before
execution. Both bootloader installations have now completed; see their separate
records for link speeds and the mainboard recovery procedure. Rollback remains
untested. The actual scripts and backups stay private;
their local copies are under `local/test-sv08-01/usb-staging-20260907/`.

## Reviewed installation sequence

Each script selects native ST-Link/V2 SWD at 100 kHz, disables debugger network
services and explicit reset, and clears the default examine-end hook. It then:

1. Checks the previously observed full chip ID, measured flash capacity, and
   absence of read protection/option error.
2. Halts the target and probes the flash bank.
3. Verifies **the entire current flash** against that board's original backup.
   A mismatch stops the installation before any erase.
4. Erases the main flash sectors: toolhead 0–127 (1 KiB each), mainboard 0–255
   (2 KiB each). This deliberately replaces the original zero-offset application.
5. Writes the 4,720-byte Katapult image at 0x08000000.
6. Verifies the entire confirmed flash range against the prepared bootloader-only
   image, including the erased application area, and prints readable option bytes.

No readout-protection unlock or option-byte write is included. Programming uses
the flash controller's normal write/erase mechanism; that is distinct from
removing readout protection. The scripts leave restart/power sequencing to the
maintenance session rather than issuing an automatic run/reset.

A failed attempt requires inspection before retry: the installation's
original-image guard intentionally fails once flash has changed. Do not remove
that guard to bypass a partial installation. Preserve logs and readback, then
choose a reviewed recovery action.

Rollback scripts recheck identity/capacity/protection, halt and capture the
pre-rollback flash, erase the appropriate main-flash sectors, restore the
board-specific complete factory image and verify it. Keep the pre-rollback
capture from each attempt separately. They do not restore host software or
change option bytes; factory operation also requires the matching host system.
This restore procedure is prepared, not demonstrated.

## Initial installation sequence (toolhead programming now complete)

1. Cleanly shut down the new host (`sudo shutdown -h now`), wait for shutdown,
   and disconnect printer supply power.
2. With ST-Link USB unplugged, connect it to the **toolhead** using the already
   verified four-wire mapping: 3.3V→3V3, GND→G, SWDIO→IO, SWCLK→CK.
3. Connect programmer USB to the separate workstation, keeping printer supply
   off. Confirm the target and power LED, then report ready.
4. The agent will identify/read-check the target and execute the reviewed
   initial installation during that maintenance session.
5. After programming, unplug ST-Link USB and disconnect its target leads before
   restoring printer power. The host can then test Katapult enumeration and
   upload the reviewed offset Klipper application over USB.
6. Repeat initial installation for the mainboard in its own powered-down session.

This physical work installs the bootloader once. Routine Klipper updates then
use USB; SWD remains an exceptional recovery path.

## Subsequent USB tests

Use the staged pinned tool with the existing host virtual environment and the
identified board's persistent USB path. Verify the reported application address
and bootloader identity before the first upload. After upload, demonstrate
software-requested re-entry and a second verified application update on each
board. Preserve the bootloader and do not enable printing configuration for
these tests.

Offline inspection confirmed the built Katapult signature and RAM request
location match the pinned Klipper reset implementation. This supports protocol
compatibility but does not substitute for live USB re-entry testing.

## Evidence

- [Staging observation](../../profiles/test-sv08-01/observations/2026-09-07-usb-staging.json).
- [Host integration](test-sv08-01-host-integration.md) and
  [MCU builds](test-sv08-01-mcu-build.md).
- Pinned [Katapult boot entry](../../upstream/katapult/src/bootentry.c),
  [STM32 flash geometry](../../upstream/katapult/src/stm32/flash.c), and
  [Klipper reset request](../../upstream/klipper/src/generic/armcm_reset.c),
  inspected 2026-09-07.
