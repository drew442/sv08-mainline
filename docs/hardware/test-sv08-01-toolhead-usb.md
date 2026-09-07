# Test printer 01: toolhead USB update validation

Date: 2026-09-07. **Two Klipper uploads verified over USB, including automatic
re-entry from Klipper into Katapult without physical intervention.**
A temporary host connection with no outputs configured reached ready.
Mainboard firmware remains unchanged.

## Hardware session

The owner confirmed ST-Link USB and target wires removed, then normal printer
power restored. The toolhead enumerated as Katapult with the same private
device identity previously associated with its factory Klipper application.

The pinned USB tool reported Katapult protocol 1.1.0, block size 64 and
application address 0x08002000. Its software-version field contained four
leading NUL bytes followed by v0.0.1-113-gec59b9b; the raw log is preserved.
This presentation anomaly did not prevent status, upload or readback checks.

Uploaded the reviewed 41,588-byte Klipper artifact from the staged host path.
The tool detected version f0892d8 and STM32F103, wrote 41 pages, read back 650
blocks and completed verification. The toolhead re-enumerated as Klipper.

Invoked the same upload against the identified **Klipper** USB path. The pinned
tool requested the bootloader over USB, observed Katapult re-enumeration and
successfully repeated upload/readback. It returned to Klipper afterward.
No ST-Link connection or manual reset was used for either USB upload.

| Validation value | Result |
| --- | --- |
| Application SHA-256 | `5e989df184cdbb86b80d218e8c257fa655537f7f5add5c4281fdff5bd6ba59e5` |
| Tool readback SHA-1, both uploads | `6a574a2da5f16c0ebbd438d8959aca9f0d9c3e7f` |
| Readback extent | 650 × 64 = 41,600 bytes |
| Application offset | 8,192 bytes |

Katapult's verification SHA is SHA-1 of the application padded to 64-byte blocks
with 0xff. Independently hashing the reviewed binary with that padding matched
both tool reports. This is application readback verification, not a fresh SWD
capture of the entire flash/option area. Bootloader functionality is demonstrated
by the second re-entry.

## Live communication check

A private single-MCU variant of the
[communication-only template](../../configs/commissioning/test-sv08-01-no-outputs.cfg)
selected only the updated toolhead. A temporary Klippy process used the pinned
host environment, reported 139 MCU commands and firmware f0892d8, configured
the MCU, and returned API state `ready`.

It defined no heater, stepper, fan, probe or output pins. This was a real USB
connection/configuration test, unlike the earlier file-output simulation.
The process was terminated after the check. Klipper/Moonraker services remain
inactive. No heat or motion commands were issued.

The archived host source initially reported version “?” despite its earlier
2,327-file hash match. Added the upstream-supported `klippy/.version` metadata
file containing f0892d8 and verified the version reader. No upstream source
code was patched.

## Scope and next task

Routine USB update and software re-entry now work on this toolhead. Power-cycle
validation of the new application, interrupted-update recovery, factory
restoration and printing remain untested.

For the next installation, shut down the host and disconnect printer power.
With programmer USB unplugged, connect ST-Link to the **mainboard** using its
previously verified four-wire mapping. Connect programmer USB to the separate
workstation while printer supply stays off, then report ready.
Follow [initial programming preparation](test-sv08-01-initial-programming.md).
Do not use the toolhead script for the 512 KiB mainboard.

Private logs and the bounded live-test script are under
`local/test-sv08-01/toolhead-usb-20260907/`.
The [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-07-toolhead-usb-update.json)
records results and remaining tests.

## Source

Pinned [Katapult USB tool](../../upstream/katapult/scripts/flashtool.py),
commit ec59b9bb9ad6c2ec8d4dc6831fbc77f0b308e29e, inspected 2026-09-07:
USB re-entry, block padding and readback SHA-1.
