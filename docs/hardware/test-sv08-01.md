# Test printer 01: owner inventory and discovery plan

Recorded: 2026-09-05. Source: owner's description in this project's working
session. This is a modified SV08 test machine; it is not evidence of an untouched
factory printer. The first [live discovery report](test-sv08-01-discovery.md)
identifies the installed software and running MCU versions; hardware suitability
and calibration remain unverified.

The [machine profile](../../profiles/test-sv08-01/profile.json) preserves unknown
values until inspection. The [stock profile](../../profiles/stock-sv08/profile.json)
is a comparison reference, not inherited electrical or calibration configuration.
Connection details and raw captures belong in ignored `local/test-sv08-01/`.

Current follow-up: [firmware artifact evidence](test-sv08-01-firmware.md) and
[recovery preparation](test-sv08-01-recovery.md). The owner has an ST-Link, an
eMMC USB reader and a spare nominal 32 GB eMMC module; adapter/module models and
compatibility are still to be checked. The plan preserves the original eMMC and
uses the spare for restoration testing and subsequent migration.

## Owner-reported hardware

| Assembly | Reported state | Verification needed |
| --- | --- | --- |
| Electronics | Mostly factory | Host/mainboard/toolhead identities, board revisions, wiring and firmware |
| Bed | cn3d/nadir/funssor 10 mm bed upgrade | Exact kit/plate, heater and thermistor, mounting, surface height and travel effects |
| Hotend | BLV CHCB-SV08 upgrade (owner's description) | Exact variant, heater, thermistor, nozzle geometry, fan arrangement and configured limits |
| Enclosure | Factory option | Installed arrangement and any associated fans/sensors |
| Displays | Klipper HDMI touchscreen plus retained factory LCD/control | HDMI model, touch interface, running UI service and factory display configuration |

Product names are recorded as supplied. They do not establish heater wattage,
thermistor curves, operating limits, probe offsets, or compatible replacement
parts. A touchscreen described as “Klipper” does not by itself establish the
installed KlipperScreen version or service state.

## Read-only discovery sequence

1. Collect host identity, OS/kernel, boot environment, storage layout and USB
   topology with the [host collector](../../scripts/collect_hardware.py).
2. Query existing Klipper/Moonraker status without G-code, identifying whether
   the printer is ready, printing, shut down or disconnected. Record the active
   service commands and their actual configuration/source paths.
3. Record application commits, remotes, local modifications and installed package
   versions. Do not run update managers, installers, Git fetch/pull on the printer,
   service restarts or MCU connection tools.
4. Preserve the active configuration/include tree and relevant existing logs in
   private workstation storage, including external symlink/include targets.
   Capture the resolved running configuration separately where the API exposes
   it; a file on disk may have changed since the last service start.
5. Obtain MCU versions and reported build constants from existing status/logs.
   Keep per-MCU identity mappings private. Do not infer bootloader offsets from
   a version string or treat a leftover firmware binary as installed firmware.
6. Compare captured configuration with the pinned Sovol snapshot and applicable
   upstream documentation. Separate vendor baseline, owner modifications,
   optional services, calibration, and unresolved differences.

For configuration comparison, pay particular attention to bed/hotend sensing,
heater limits and PID values, Z travel and offsets, probing/gantry/mesh geometry,
cleaning/purge macros, fan control and both display paths. Differences may be
intentional adaptations to these upgrades and should not be reverted merely
because they differ from the vendor reference.

## Preservation and verification status

Follow the [discovery and backup workflow](discovery-and-backup.md). Host inspection
and configuration copies do not constitute full storage or MCU flash backups.
No operating settings or validation status should be promoted on the basis of
the owner's inventory alone.

SSH access succeeded after the owner's power cycle on 2026-09-05. Host and runtime
API evidence was collected privately. The [observation record](../../profiles/test-sv08-01/observations/2026-09-05.json)
distinguishes discovery from operational validation and full backups.
