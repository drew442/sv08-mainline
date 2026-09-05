# Test printer 01: first live discovery

Date: 2026-09-05. Read-only SSH and existing Moonraker GET APIs were used after
the owner's power cycle. The printer reported **ready / standby**, with both
heater targets at zero. No heat, motion, homing, probing, service restart, update
or firmware write was commanded during this inspection.

**Initial observation (subsequently repaired):** the hotend reported 119.88–120.11°C over repeated
queries while the bed reported 28.22–28.30°C. The owner subsequently measured
28°C with an external instrument. The [temperature analysis](test-sv08-01-temperature.md)
calculates the PT1000 hypothesis; sensor identity, wiring, circuit values and
firmware conversion remain to be verified across the operating range. After the
owner's thermistor repair, three samples showed hotend 29.42–29.44°C and bed
29.40–29.42°C with unchanged sensor settings and zero heater targets. The original
ambient anomaly is no longer observed; heated operation remains untested.

## Host and services

| Item | Observed state |
| --- | --- |
| OS | SPI-XI 2.3.3, Debian 11 Bullseye |
| Kernel / architecture | `5.16.17-sun50iw9`, aarch64; kernel build dated 2023-12-25 |
| Device-tree model | `BigTreeTech CB1` |
| Device-tree compatible | `allwinner,sun50i-h616` |
| Configured device tree | `sun50i-h616-sovol-emmc` |
| Memory reported by Linux | `MemTotal: 1010632 kB`; not a chip part-number identification |
| Storage | eMMC: 7,818,182,656-byte user area; two 4,194,304-byte boot areas |
| Mounted partitions | 268,435,456-byte FAT `/boot`; 7,377,780,736-byte ext4 root |
| Python | System Python 3.9.2; Klipper uses its own virtual environment |
| Active services | Klipper, Moonraker, KlipperScreen, Crowsnest and nginx |
| Configuration | `/home/sovol/printer_data/config/printer.cfg` |

The CB1 model string describes the loaded device tree and does not prove a
physical CB1 module is installed. Board revision and chip markings still need
inspection. `BoardEnv.txt` contains repeated `overlays` assignments (`uart3`,
then `ws2812 spidev1_1`); do not assume their effective combination without
checking the boot script and live device tree.

The eMMC enumerated as `mmcblk2` initially and `mmcblk1` after the repair/reboot.
The latter reports product name `8GTF4R`, type `MMC`, manufacturer ID `0x000015`
and manufacture date `09/2022`. Device numbering is not a persistent identity:
resolve the mounted root/boot source and parent device again before any capture.

The HDMI connector reports connected, with 1024×600 first in its mode list; the
`sun4i-drmdrmfb` framebuffer reports a 1024×600 virtual size. Linux input lists
the QinHeng `1a86:e5e3` USB2IIC_CTP_CONTROL device with absolute input events.
These establish detected display/input paths, not a tested touch calibration or
an exact screen model. The live device tree enables HDMI, eMMC, SPI1/spidev and
`serial@5000c00`. The boot script imports the text environment and then iterates
`overlays`; the effect of duplicate environment keys remains unverified.

## Application revisions

| Component | Observed version | On-disk HEAD / qualifications |
| --- | --- | --- |
| Klipper host | API: `v0.12.0-0-g02eeceb-dirty` | `02eecebfabfaddc087ccbe59f4da0e72d44df8b8`; remote is Sovol3d/klipper; local source changes |
| Moonraker | `v0.8.0-209-g4235789-dirty` | `42357891a3716cd332ef60b28af09f8732dbf67a`; substantial on-disk modifications |
| KlipperScreen | `v0.3.9-1-ge0af637-dirty` | `e0af63774db6cd56ab4757190a72cac286cffead`; six changed tracked files |
| Mainsail | `.version`: `v2.10.0` | Distribution directory; no Git HEAD obtained |
| Crowsnest | `v4.1.1-1-gf7ac6aa` | `f7ac6aa298143f0019eae9b2b2be8039196ebeda`; checkout reported clean |
| Moonraker timelapse | `v0.0.1-143-gc7fff11` | `c7fff11e542b95e0e15b8bb1443cea8159ac0274`; checkout reported clean |

These are observations, not endorsed versions. A dirty tree cannot be reproduced
from its HEAD alone. Some Git differences are executable-bit changes or generated
build/cache files; source-content inspection must separate those from behavior.
The running Python process may also differ from subsequently edited on-disk files.

## Running MCU reports

| MCU role in active configuration | Firmware report, sanitized | Build timestamp reported | Runtime constants |
| --- | --- | --- | --- |
| `mcu` / mainboard | `v0.12.0-40-g77619e91-dirty` | 2024-03-01 10:46:56 | `MCU=stm32f103xe`, `CLOCK_FREQ=72000000`, USB PA11/PA12 |
| `extra_mcu` / toolhead | `v0.12.0-4-g3bfe0b7-dirty` | 2025-07-22 06:22:09 | `MCU=stm32f103xe`, `CLOCK_FREQ=72000000`, USB PA11/PA12 |

Build timestamp timezone is unknown. The mainboard reports GCC 10.3.1 and the
toolhead GCC 8.3.1. Both use stable `/dev/serial/by-id/` paths in the active
configuration; unique IDs are retained privately.

The toolhead's firmware target string does not establish an F103VE physical chip:
the published toolhead schematic identifies F103CB. Firmware target aliases and
physical part/flash capacity need separate verification. Likewise, 72 MHz is the
firmware's runtime clock constant, not evidence of the external crystal frequency.

The installed Klipper `.config` and `out/autoconf.h` select AVR ATmega2560, as in
the previously noted vendor artifact mismatch. They are unsuitable as inputs for
rebuilding either running STM32 target. Installed bootloader offsets remain
unknown. A subsequent [firmware artifact inspection](test-sv08-01-firmware.md)
identified a matching mainboard build candidate with an 8 MHz clock reference
and application base `0x08000000`; this is file evidence, not MCU flash readback.

## Comparison with the Sovol reference

Reference: Sovol SV08 commit `a60644875f8c756d20b3828c9416518b414b5491`.
Compared the API's loaded raw configuration sections against the vendor files,
ignoring comments/outer whitespace and retaining the last duplicate option.
This comparison excludes include ordering and does not replace a disk/include
audit. Loaded settings report no pending `SAVE_CONFIG` operation or config warnings.

The inspected motion, heater, thermistor, stepper, gantry-leveling, mesh, pressure
probe, automatic Z-offset and factory display sections match the published
`printer.cfg`. The loaded probe Z offset is 1.0, matching its saved-config footer.
The ADXL345 adds `axes_map: x,z,y`.

Thermal settings are still the vendor values: hotend `my_thermistor_e` with
11,500-ohm configured pull-up and PID 33.838 / 5.223 / 47.752; bed `my_thermistor`
with PID 73.571 / 1.820 / 783.849. This establishes configuration equality only,
not correctness for the reported hotend or bed upgrades.

Observed macro differences from vendor `Macro.cfg`:

- `CLEAN_NOZZLE` moves to X321 instead of X315 before cleaning.
- `START_PRINT` calls `save_last_file`; `END_PRINT` calls `PRINT_END`.
- `RESUME` uses M104/M109 for nozzle heat where the vendor file uses M140/M190.
  Preserve that distinction; reverting to the vendor text would target the bed.
- The published `plr.cfg` sections are loaded on this printer, unlike the direct
  includes visible in the published top-level file. Its inspected option values
  match. Power-loss recovery is configured, but has not been tested here.

The three previously missing includes exist as symlinks on this printer:
`mainsail.cfg` points to mainsail-config's `client.cfg`; `timelapse.cfg` points to
moonraker-timelapse; and the Obico macro include points to moonraker-obico. Preserve
the referenced content as well as the links when archiving configuration.

The approved archive confirms a direct `plr.cfg` include in the installed
`printer.cfg`. A subsequent offline parse used the pinned vendor `PrinterConfig`
parser over the archived contents, including all six direct includes and the
`SAVE_CONFIG` footer. All 116 resulting sections matched the captured API raw
configuration, with zero option differences. No printer modules were started.
This establishes equality for that captured Klipper include tree; it does not
validate macro execution, external scripts, or settings for the upgraded hardware.

A hash comparison covered 413 vendor-listed `.py`, `.c` and `.h` files beneath
Klipper's `klippy/` and `src/`: 405 matched and eight differed, with no listed
files missing. It did not inventory additional installed files or other trees.
The eight differing modules cover configuration logging, shutdown metadata,
virtual-SD completion, fan handling, motion/power-loss bookkeeping and LCD menus.
One inspected change removes the configuration dump from Klipper logging, so
`klippy.log` alone must not be relied on to preserve the active configuration.

## Upgraded hardware reference checks

The manufacturer's [Trianglelab CHCB-SV08 listing](https://trianglelab.net/products/chcb-sv08-hotend-hot-side)
offers both NTC and PT1000 sensor options. It is a candidate match for the owner's
“BLV CHCB-SV08” description, not identification of this installed sensor.

The [Funssor/Nadir kit listing](https://funssorlab.com/products/sovol-sv08-3d-printer-upgrade-hotbed-complete-kit-with-3d-printed-parts-design-by-nadircn3d-10mm-riser-heated-bed-upgrade-kit-120-240v-silicone-heater-01mm-flat-aluminum-bed)
uses “10mm riser” wording but describes an 8 mm plate. Retain the owner's reported
10 mm upgrade description until the installed revision/dimension is checked.
Neither listing establishes the installed bed thermistor. Both checked 2026-09-05.

## Preservation and next checks

Private host and runtime API reports are stored under `local/test-sv08-01/` and
excluded from Git. Following explicit owner approval, the configuration/log/
service/selected-boot archive was created in ignored
`backups/test-sv08-01/20260905/`, with a private manifest and SHA-256 hashes.
It contains 32 regular files, including resolved contents of the three symlinked
includes. Gzip integrity and archive readability checks passed, and all 30
non-log file hashes matched subsequent printer-side reads.

Tar returned status 1 because the live `klippy.log` changed during capture; the
archive is a verified live file capture, not an atomic or fully consistent log
snapshot. No full eMMC image, MCU flash dump or restore test has been performed.

The owner has an ST-Link, an eMMC USB reader and a spare nominal 32 GB eMMC module.
The [recovery preparation plan](test-sv08-01-recovery.md) uses the original module
as the preserved baseline and the spare as the migration target, subject to
connector/voltage compatibility and verified backups. Next identify the reader's
computer, module/adapter models, PCB identities and MCU recovery connections.
Record the repaired sensor variant before later heater and motion validation.

The [observation record](../../profiles/test-sv08-01/observations/2026-09-05.json)
contains sanitized evidence scope and limitations. This machine remains a
research profile, not a validated stock or modified hardware release.
