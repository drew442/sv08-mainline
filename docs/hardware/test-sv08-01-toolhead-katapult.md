# Test printer 01: toolhead Katapult installation

Date: 2026-09-07. **Katapult programmed and complete flash readback verified.**
The toolhead application area is erased; Klipper has not yet been uploaded.
Katapult USB boot/re-entry remains untested. The mainboard was not modified.

## Maintenance setup and execution

The owner confirmed completion of the power-off toolhead connection sequence:
host shut down, printer supply disconnected, ST-Link/V2 connected through the
verified four-wire header from the separate workstation.

The first 100 kHz connection failed during core examination before the identity
guard, halt, erase or programming commands. A 5 kHz identification read succeeded.
The unchanged guarded installation script then completed at 100 kHz.

Read identity was 0x20036410 with 128 KiB capacity; read protection and option
error bits were clear. OpenOCD 0.12.0-1build2 with native ST-Link/V2 SWD halted
the target, probed flash and verified all 131,072 original bytes against the
preserved factory backup before crossing the erase boundary.

It erased sectors 0–127, programmed the reviewed 4,720-byte Katapult binary at
0x08000000 and verified all flash against the expected bootloader-only image.
No readout-protection unlock or option-byte write was performed. No explicit
reset/run command followed programming.

## Independent verification

A subsequent OpenOCD session captured the complete 128 KiB flash and all
16 readable option bytes. Local byte comparison against the expected image
passed; option bytes equal the original backup.

| Item | SHA-256 |
| --- | --- |
| Katapult binary, 4,720 bytes | `0d293f1fabc3b6c81e8fe436230d0765d6e339e460f4e04b3228432022dec2b7` |
| Full installed readback, 131,072 bytes | `02ba3ae439db24559b6b8cfa2c495d077e301065990341f79b81648695a89cb0` |
| Unchanged option bytes, 16 bytes | `c0b942fbb9fe967ec0e7b675e080d48c930fc5fe3fde70f6dd6f9646fdffc0d3` |

Katapult source is ec59b9bb9ad6c2ec8d4dc6831fbc77f0b308e29e. Its application
address is 0x08002000. All bytes after the bootloader image are 0xff.
This verifies stored contents, not execution or successful USB enumeration.

Private programming logs:
`local/test-sv08-01/toolhead-katapult-install-20260907/`.
Private readback and manifest:
`backups/test-sv08-01/toolhead-katapult-20260907/`.
The [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-07-toolhead-katapult-install.json)
records scope and results.

## Next step

With printer supply still off, unplug ST-Link USB and remove all four target
wires. Restore normal printer power and report when SSH is available. The agent
can then identify the toolhead Katapult USB device, inspect bootloader status
and upload the reviewed offset Klipper binary from the staged host files.

Do not start printer services yet. Verify software-requested bootloader re-entry
and a repeat USB application update before installing the mainboard bootloader
in its separate power-off session.

The original toolhead flash remains preserved for SWD rollback. Factory eMMC
swap-back alone no longer restores the original toolhead firmware. A factory
restoration test has not been performed.

## References

- [Guarded initial programming procedure](test-sv08-01-initial-programming.md).
- [Build configuration and hashes](test-sv08-01-mcu-build.md).
- [Original toolhead backup](test-sv08-01-toolhead-swd.md).
