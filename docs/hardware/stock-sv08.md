# Stock SV08 hardware inventory

Research date: 2026-09-05. Scope: original SV08, stock electronics first.
No physical printer has been inspected in this repository's work so far.

**Documented** means supported by a cited source. **Inferred** means a working
hypothesis. **Verified on hardware** requires an identified board and recorded
inspection or measurement; no entries currently meet that level.

## Components

| Component | Initial identification | Evidence and limits |
| --- | --- | --- |
| Linux host SoC | Allwinner H616; quad-core Arm Cortex-A53 | H616 is indicated by Sovol's mainboard document name [S1]; CPU architecture is documented by [H1]. Host identity is provisional until board marking and device-tree compatible strings are captured. The published MCU sheet is not a full host schematic. |
| Mainboard MCU | STM32F103VET6, LQFP100 | Explicit U14 label on [S1], page 1. ST identifies the VE part as Cortex-M3, up to 72 MHz, 512 KB flash [M1]. This does not identify the installed bootloader or external clock. |
| Toolhead MCU | STM32F103CBT6, LQFP48 | Explicit U5 label on [S2], page 1. ST identifies the CB part as Cortex-M3, up to 72 MHz, 128 KB flash [M2]. Check actual board markings before building. |
| Host-to-MCU transport | USB serial for both MCUs in the published configuration | `[mcu]` and `[mcu extra_mcu]` use `/dev/ttyACM1` and `/dev/ttyACM0` in [S5]; USB nets appear on [S1]/[S2]. Enumeration order is not a reliable per-printer identity. |
| Motor drivers | TMC2209 configured for X, Y, four Z motors, and extruder | Sections in [S5]. Physical driver identity and sense resistor values need checking; do not blindly import current settings. Manufacturer reference [P1]. |
| Accelerometer | ADXL345 configured on toolhead SPI, CS PB12 | `[adxl345]` in [S5]. Component and orientation need inspection. Manufacturer reference [P2]. |
| Z sensing | Toolhead probe input plus vendor pressure-probe path | [S5] has `[probe]` at `extra_mcu:PB6` and `[probe_pressure]` at `^!PE12`. Sensor identity, electrical behavior, and mainline replacement need review. |
| Temperature sensing | Vendor thermistor curves; hotend config specifies an 11500-ohm pull-up | `[thermistor my_thermistor_e]`, `[thermistor my_thermistor]`, and heater sections in [S5]. Configuration evidence only; resistor network and temperature accuracy remain unverified. |
| Storage and memory | Exact installed parts/capacity unknown | Collect RAM and eMMC/SD details from the target. Do not transfer CB1 capacity claims to this board. |
| Networking, display, camera, power circuitry | Part numbers and revisions unknown | Collect USB/SDIO identities, board photos, and relevant schematics. Host device-tree and driver support are open work. |

The published mainboard filename refers to `H616_JC_6Z_V1_2`; it does not prove
that an owner's PCB is revision 1.2. Do not combine the SV08 with SV08 Max/Zero
pinouts or MCU targets.

## Migration gaps already visible

- The vendor configuration has `[probe_pressure]` and ships a corresponding
  `home/sovol/klipper/klippy/extras/probe_pressure.py`. Audit the probing and
  automatic Z-offset workflow before selecting a mainline implementation.
- Stock configuration includes vendor/optional macros and machine calibration.
  Review includes, commands, paths, deprecated options, and heater settings;
  copying the full file is not the conversion plan.
- The host boot chain needs board-specific investigation: boot media, device
  tree, regulators, DRAM setup, networking, and peripheral support.
- MCU oscillator source/frequency, flash layout, bootloader offset, and recovery
  method remain unresolved for both boards. Separate build targets are required.

## Evidence to collect next

Record PCB revision and chip markings for host, mainboard MCU, and toolhead MCU.
Gather the OS release, kernel version, boot configuration, device-tree model and
compatible strings, storage layout, USB identities, and existing Klipper build
information. Preserve full configuration and recoverable host/MCU backups with
sizes and SHA-256 hashes in private storage.

Then compare the actual board to the published connector drawings, establish
clock and flash settings, and record thermistor/probe circuit evidence. Put
sanitized findings in the stock profile; retain unique IDs and credentials in
`local/`. The [profile template](../../profiles/TEMPLATE.md) lists the fields.

## Sources

Sources below refer to the pinned Sovol checkout recorded in
[`upstream-lock.json`](../../upstream-lock.json); the PDFs were inspected locally.
The [reference library](../references.md) includes web links and further reading.

[`sources.sha256`](sources.sha256) records the four local board PDFs at intake.
From the repository root, verify them with
`sha256sum -c docs/hardware/sources.sha256`.

- [S1: mainboard MCU schematic](../../upstream/sovol-sv08/Motherboard/H616_JC_6Z_V1_2_MCU.pdf), page 1.
- [S2: toolhead MCU schematic](../../upstream/sovol-sv08/Motherboard/Extra_MCU.pdf), page 1.
- [S3: mainboard connector drawing](../../upstream/sovol-sv08/Motherboard/MCU_PIN_definition.pdf).
- [S4: toolhead connector drawing](../../upstream/sovol-sv08/Motherboard/Extra_PIN_definition.pdf).
- [S5: vendor printer configuration](../../upstream/sovol-sv08/home/sovol/printer_data/config/printer.cfg).
- [H1: linux-sunxi H616 documentation](https://linux-sunxi.org/H616).
- [M1: ST STM32F103VE](https://www.st.com/en/microcontrollers-microprocessors/stm32f103ve.html).
- [M2: ST STM32F103CB](https://www.st.com/en/microcontrollers-microprocessors/stm32f103cb.html).
- [P1: Analog Devices TMC2209](https://www.analog.com/en/products/tmc2209.html).
- [P2: Analog Devices ADXL345](https://www.analog.com/en/products/adxl345.html).
