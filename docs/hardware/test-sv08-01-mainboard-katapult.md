# Test printer 01: mainboard Katapult installation

Date: 2026-09-08. **Katapult programmed; full 512 KiB readback matches the
expected image and option bytes are unchanged.** The mainboard application
area is erased. Mainboard USB boot and application upload remain pending.
The toolhead was not modified during this session.

## Target and programming attempts

The owner confirmed printer supply off and ST-Link connected to the mainboard
using the reviewed setup. Staged inputs passed SHA256SUMS. ST-Link/V2 firmware
V2J37S7 and OpenOCD 0.12.0-1build2 were used through native direct SWD.

A 5 kHz probe read chip ID 0x10036414 and 512 KiB capacity. The initial 100 kHz
installation failed during target examination, before any erase/write command.
A 5 kHz variant retained every identity, capacity, protection and original-flash
guard. It verified the entire factory image, erased sectors 0–255, then failed
during the flash-write algorithm with debug-port/control errors.

No blind rerun of the original-image installation was attempted. A 950 kHz
readback captured all 524,288 bytes as 0xff and found the original option bytes
unchanged. This established the actual intermediate state before recovery.
Its SHA-256 is
`043e238a765f7cfbc62596a50e53c8ffb6b188a99357b0ebede251725d67589f`.

The reviewed completion procedure rechecked identity, capacity and protection,
used a software `reset halt`, verified the entire erased image, wrote Katapult
at 0x08000000, verified the complete expected image, and dumped flash/options.
It ran successfully at 950 kHz. No additional erase, readout-protection unlock
or option-byte write was used in this completion step.

The failure's root cause is not established. Speed, target state and reset
handling differed between attempts. Do not generalize that lower SWD speed is
always more reliable or remove state-verification guards after an error.

## Final verification

| Item | Size | SHA-256 |
| --- | --- | --- |
| Katapult binary | 4,720 bytes | `0d293f1fabc3b6c81e8fe436230d0765d6e339e460f4e04b3228432022dec2b7` |
| Full mainboard readback | 524,288 bytes | `a6c964d9438c972281c53d8a93a94f17b063ed6d7b7dea9e02c7d44aab6ece9f` |
| Unchanged option bytes | 16 bytes | `c0b942fbb9fe967ec0e7b675e080d48c930fc5fe3fde70f6dd6f9646fdffc0d3` |

The transferred flash was byte-compared with the expected Katapult-only image;
all bytes after the 4,720-byte binary are 0xff. Option bytes were byte-compared
with the original backup. Katapult revision is
ec59b9bb9ad6c2ec8d4dc6831fbc77f0b308e29e and application start is 0x08002000.
No explicit run command followed programming. Stored-image verification is
not proof of boot or USB enumeration.

Private logs, intermediate erased readback and reviewed completion script:
`local/test-sv08-01/mainboard-katapult-install-20260908/`.
Final readback/options and manifest:
`backups/test-sv08-01/mainboard-katapult-20260908/`.
See the [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-08-mainboard-katapult-install.json).

## Next step

With printer supply still off, unplug ST-Link USB and remove all four target
wires. Restore normal printer power and report when the host is online.
Identify the mainboard Katapult USB device, check its application address, upload
the reviewed Klipper binary, and demonstrate software re-entry and repeat USB
upload. Then test both new MCU applications together with no outputs configured.

The mainboard currently has no Klipper application. Both original MCU images
remain preserved, but swapping factory eMMC alone no longer restores the
original MCU firmware. Factory restoration, interrupted-update recovery and
printing remain untested.

## References

- [Initial programming preparation](test-sv08-01-initial-programming.md).
- [Mainboard factory backup](test-sv08-01-mainboard-swd.md).
- [Reviewed builds](test-sv08-01-mcu-build.md).
- [Toolhead USB update results](test-sv08-01-toolhead-usb.md).
