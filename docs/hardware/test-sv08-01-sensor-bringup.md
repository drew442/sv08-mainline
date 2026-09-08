# Test printer 01: upstream sensor bring-up and configuration migration

Date: 2026-09-08. Profile: [test-sv08-01](../../profiles/test-sv08-01/profile.json).
PCB revisions remain unknown. Host and both MCU applications use Klipper
`f0892d82b0f1c1228454f09eb508eddde2250f4b`.

## Input-only configuration

Use the [paired communication template](../../configs/commissioning/test-sv08-01-no-outputs.cfg)
with private serial substitutions and an include of
[test-sv08-01-sensors.cfg](../../configs/commissioning/test-sv08-01-sensors.cfg).
The include configures only temperature inputs. Do not combine it with heater
sections claiming the same ADC pins. It is not a printing configuration.

Conversion coefficients, pins and temperature bounds were copied from the
preserved, resolved installed configuration captured on 2026-09-05. The
[post-repair check](test-sv08-01-temperature.md) used unchanged conversion settings.
Hotend input is `extra_mcu:PA5`, configured pull-up 11,500 ohms; bed input is
`PC5`, with the upstream default pull-up of 4,700 ohms. These are software
settings, not measured resistor values or identification of the installed
sensors. Neither curve was tuned to the new readings.

Both the sensor-only configuration and a private printing candidate pass
Klipper file-output configuration checks using the matching MCU dictionary.
File-output checks do not access the boards or validate electrical behavior.
The temporary live sensor process queried status only and was stopped afterward;
printing services remain inactive. No heat or motion commands were issued.

Twelve live samples spanning 55.054 seconds remained ready: hotend
**21.31–21.39°C**, bed **20.06–20.36°C**. A current independent temperature
reference is not yet recorded. These observations establish communication and
short-term ambient plausibility, not sensor accuracy. See the
[measurement record](../../profiles/test-sv08-01/observations/2026-09-08-sensor-bringup.json).

## Printing candidate: offline only

A private candidate and explicit retained/omitted section inventory are in
`local/test-sv08-01/sensors-20260908/`. Thirty of the original 116 resolved sections
were retained: both MCUs, printer kinematics, steppers/drivers, thermistors,
heaters and their verification sections, probe, mesh, gantry leveling, fans and
filament switch. Calibration and identifiers stay private. Serial placeholders
prevent treating the offline candidate as a ready-to-run installation.

The removed `max_accel_to_decel` option is omitted. Initial candidate limits are
50 mm/s velocity, 500 mm/s² acceleration, 5 mm/s Z velocity, 50 mm/s² Z
acceleration and `minimum_cruise_ratio: 0.5`. These are proposed commissioning
limits, not an equivalent translation of the vendor's high-speed settings and
not validated motion parameters. Existing heater protections remain intact;
existing PID and probe calibration remain unvalidated on this stack.

Vendor pressure-based automatic Z calibration, homing override, delayed actions,
printing macros, shell hooks, power-loss recovery, timelapse, Obico, displays
and input-shaper calibration are omitted. The candidate is incomplete: ordinary
G28 must not be used before a reviewed homing procedure and endstop/probe checks.
The [compatibility audit](../vendor-compatibility.md) tracks vendor feature gaps.
No vendor Python extensions were copied into upstream Klipper.

## Remaining commissioning tasks

- Owner: record current room/reference temperature and installed hotend sensor
  part/repair details; compare both ambient readings against an independent
  instrument. Earlier room measurements are not a current reference.
- Owner, with power off when accessing wiring: identify sensor variants and board
  revisions; verify temperature circuits before accepting conversion settings.
- The [probe/filament input include](../../configs/commissioning/test-sv08-01-inputs.cfg)
  passes file-output validation with the sensor configuration. Empty button
  macros perform no actions. Live physical testing remains pending: owner must
  operate/observe the filament switch and probe to establish polarity and
  physical association. Query `gcode_button probe_check` and
  `gcode_button filament_check`; logical labels alone do not prove polarity.
- X/Y use TMC2209 virtual endstops, with configured DIAG pins PE15/PE13. They
  require an attended sensorless-homing validation; there are no configured
  mechanical X/Y switches to toggle. Z uses the probe virtual endstop.
- Agent and owner: verify fan identity/direction and shutdown behavior with an
  attended, bounded output test, then motor direction and a reviewed homing
  sequence. Retain these as separate activation steps.
- Validate temperature accuracy and heater response under supervision before
  PID calibration, extrusion or printing. Ambient plausibility is insufficient.
- Choose an upstream manual Z-offset workflow or a separately validated pressure
  calibration implementation before restoring automatic calibration macros.
- Complete normal-power-cycle, interrupted-update recovery and factory-restore
  checks listed in the [recovery task list](test-sv08-01-recovery-tasks.md).

Provenance: private resolved runtime and post-repair captures, 2026-09-05;
upstream pinned `klippy/extras/temperature_sensor.py`, `thermistor.py`,
`adc_temperature.py`, and `klippy/toolhead.py`, inspected 2026-09-08.
