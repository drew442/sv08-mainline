# Test printer 01: mainboard USB updates and dual-MCU check

Date: 2026-09-08. **Both MCUs now have Katapult and the selected Klipper
application. USB re-entry and repeat uploads have passed on each board.**
A temporary host process connected both MCUs together and reached ready with
no outputs configured. This is communication validation, not print validation.

## Mainboard USB update

After the owner restored normal printer power, the mainboard enumerated as
Katapult with its expected private identity. The toolhead enumerated as Klipper,
also demonstrating its application's boot after the intervening owner power cycle.

Pinned Katapult status reported protocol 1.1.0, 64-byte blocks and application
address 0x08002000. Uploaded the reviewed 41,588-byte Klipper f0892d8 binary.
The tool wrote 21 pages and verified 650 blocks, then the mainboard enumerated
as Klipper.

A second upload began using that identified Klipper USB path. The tool requested
Katapult entry over USB, detected re-enumeration and repeated programming and
readback successfully. No ST-Link operation or manual reset occurred.

- Application SHA-256:
  `5e989df184cdbb86b80d218e8c257fa655537f7f5add5c4281fdff5bd6ba59e5`.
- Both USB verification SHA-1 results:
  `6a574a2da5f16c0ebbd438d8959aca9f0d9c3e7f`.

The verification hash covers 41,600 bytes (650 blocks), with the final partial
block padded with 0xff. Independent local hashing reproduced that value.
Mainboard page count differs from the toolhead's 41 because their flash page
sizes differ; the application and verified data are identical. The version
report retained the same leading-NUL presentation anomaly observed on the
[toolhead](test-sv08-01-toolhead-usb.md), without preventing verified operation.

## Both MCUs with the matching host

An ignored local copy of the
[communication-only template](../../configs/commissioning/test-sv08-01-no-outputs.cfg)
used both recorded persistent USB identities. A bounded temporary Klippy process
used the existing pinned host environment. API results reported:

| Component | Version/result |
| --- | --- |
| Host | f0892d8 |
| Mainboard MCU | f0892d8 |
| Toolhead MCU | f0892d8 |
| Initial state | ready |
| Follow-up after 10 seconds | ready |

Both MCUs loaded 139 commands. The template contains no heaters, steppers, fans,
probes or output pins. The test issued host status queries and normal MCU
configuration/clock synchronization, not heat or motion commands. The temporary
process was terminated afterward; Klipper/Moonraker services remain inactive.

The follow-up clock estimates were approximately 72.004 MHz for each MCU.
These are host synchronization estimates, not independent crystal measurements.
Each reported nine retransmitted bytes and zero invalid bytes at that sample;
this short session does not establish long-duration link reliability.

## Remaining work

- Mainboard application boot after a normal power cycle and a longer paired
  connection test.
- Interrupted USB update recovery and factory restoration demonstrations.
- Port and review the installed printer configuration and vendor-dependent
  probing/macros; then validate sensors before enabling outputs.
- Controlled fan/endstop/probe, motion and heater checks followed by print tests.

No more ST-Link connection is needed for routine application updates under the
tested path. Keep it available for exceptional recovery. Factory eMMC swap-back
alone does not restore the changed MCU firmware.

Private logs, USB identities and the bounded live-test script:
`local/test-sv08-01/mainboard-usb-20260908/`.
See the [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-08-mainboard-usb-update.json),
[mainboard installation](test-sv08-01-mainboard-katapult.md) and
[build record](test-sv08-01-mcu-build.md).
