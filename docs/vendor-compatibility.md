# Initial vendor compatibility audit

Date: 2026-09-05. Method: static inspection of the pinned source checkouts; no
printer connection, configuration load, or firmware execution was performed.
This is an initial feature audit, not a complete diff of Sovol's Klipper fork.

Inputs are Sovol SV08 `a60644875f8c756d20b3828c9416518b414b5491` and Klipper
`f0892d82b0f1c1228454f09eb508eddde2250f4b`, also recorded in
[`upstream-lock.json`](../upstream-lock.json).

## Findings and proposed treatment

| Feature | Source evidence | Migration work |
| --- | --- | --- |
| Motion configuration | Stock `[printer]` sets `max_accel_to_decel`; upstream records its removal on 2025-08-11 [S1, K1] | Replace the removed setting with a reviewed `minimum_cruise_ratio` configuration. Do not assume a mechanical rename preserves behavior. |
| Pressure probing | Stock enables `[probe_pressure]`, provided by a vendor extra absent from our upstream checkout [S1, S3] | Determine the installed sensor/circuit behavior, then select a compatible implementation. Required for retaining the vendor automatic Z-offset workflow. |
| Automatic Z offset | `[z_offset_calibration]` and `Z_OFFSET_CALIBRATION` depend on both probe objects, repeated measurements, and a hard-coded saved-variables path [S1, S4] | Review the algorithm and path handling. Choose a replacement or explicitly defer automatic calibration; retain a validated calibration method. |
| Probe API compatibility | Vendor calibration calls `lookup_object('probe').run_probe(...)`; upstream `PrinterProbe` exposes session methods and has no `run_probe` method [S4, K2] | Copying the vendor calibration extra alone would leave an API incompatibility. An adaptation needs regression tests and hardware validation. |
| Shell commands | Stock includes `get_ip.cfg` and a factory-reset shell command in `Macro.cfg`; `gcode_shell_command.py` is absent upstream [S2, S5, S6] | Remove optional hooks from the minimal configuration or design a narrowly scoped replacement. Treat the extra as a separate dependency, not stock upstream behavior. |
| Configuration includes | `mainsail.cfg`, `timelapse.cfg`, and `moonraker_obico_macros.cfg` are referenced but absent beside the published `printer.cfg` [S1] | Resolve required includes from selected packages and omit optional ones deliberately. These files may exist on shipped printers; the published directory is not self-contained. |
| Thermistors | Vendor curves and hotend `pullup_resistor: 11500` are explicit; upstream supports custom thermistors and pull-up configuration [S1, K3] | First verify the electrical circuit and temperature response. Configuration may suffice; this finding does not establish a need for custom ADC firmware. |
| Gantry leveling and bed mesh | Vendor macros wrap upstream commands with heating, homing, and mesh behavior [S2] | Separate core commands from vendor choreography. Validate travel bounds, sensor behavior, and thermal sequencing before reusing macros. |
| Power-loss recovery | Separate `plr.cfg` invokes host scripts and `SET_KINEMATIC_POSITION`; it is not directly included by the inspected `printer.cfg` [S1, S7] | Treat as an optional feature pending an installed-config/include audit and dedicated recovery tests. Presence in the repository does not prove it is enabled on a printer. |
| Per-printer state | Config/macros embed serial enumeration, `/home/sovol` paths, calibration, and saved variables [S1, S2, S4] | Move environment-specific values into explicit local configuration; never copy another printer's calibration as validated defaults. |

The upstream checkout contains `load_cell_probe` [K4]. Its name does not establish
electrical or behavioral equivalence with Sovol's `probe_pressure` input; sensor
interface evidence is still needed before selecting it.

## Reproduce the initial observations

Compare top-level Python filenames in the vendor and upstream `klippy/extras`
directories. The vendor-only names at these pins are `gcode_shell_command.py`,
`probe_pressure.py`, and `z_offset_calibration.py`. This comparison does not
identify modifications inside same-named modules, MCU source, or host scripts.

Read each top-level `[include ...]` in [S1] and check it relative to that file's
directory. The three missing paths above establish a gap in the published
configuration directory, not a statement about an installed printer.

Inspect `ZoffsetCalibration.cmd_Z_OFFSET_CALIBRATION` in [S4] alongside
`PrinterProbe` in [K2] for the probe API mismatch. Inspect the dated removal
entry in [K1] for the obsolete motion setting.

## Next decisions and evidence

1. Obtain the [host discovery report](hardware/discovery-and-backup.md), actual
   configuration/include tree, board revisions, and backup inventory.
2. Audit same-named vendor modules and STM32 source against their historical
   upstream base. Comparing the old snapshot directly to current upstream alone
   would also include years of unrelated upstream changes.
3. Define the minimum stock feature set and decide the probing/calibration path.
4. Build a candidate configuration with all dependencies resolved; validate it
   offline before any heater or motion tests.

No custom runtime code or new hardware-support claim is introduced by this audit.

## Source locations

- [S1: vendor printer.cfg](../upstream/sovol-sv08/home/sovol/printer_data/config/printer.cfg).
- [S2: vendor Macro.cfg](../upstream/sovol-sv08/home/sovol/printer_data/config/Macro.cfg).
- [S3: vendor probe_pressure.py](../upstream/sovol-sv08/home/sovol/klipper/klippy/extras/probe_pressure.py).
- [S4: vendor z_offset_calibration.py](../upstream/sovol-sv08/home/sovol/klipper/klippy/extras/z_offset_calibration.py).
- [S5: vendor get_ip.cfg](../upstream/sovol-sv08/home/sovol/printer_data/config/get_ip.cfg).
- [S6: vendor gcode_shell_command.py](../upstream/sovol-sv08/home/sovol/klipper/klippy/extras/gcode_shell_command.py).
- [S7: vendor plr.cfg](../upstream/sovol-sv08/home/sovol/printer_data/config/plr.cfg).
- [K1: upstream configuration changes](../upstream/klipper/docs/Config_Changes.md).
- [K2: upstream probe.py](../upstream/klipper/klippy/extras/probe.py).
- [K3: upstream configuration reference](../upstream/klipper/docs/Config_Reference.md).
- [K4: upstream load_cell_probe.py](../upstream/klipper/klippy/extras/load_cell_probe.py).
