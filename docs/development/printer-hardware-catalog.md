# Printer runtime catalogue and storage contract

The current design requirements are [Printer hardware page](printer-hardware-page-design.md)
and [Creator-published definitions](printer-definition-sources-design.md).
These replace the prior board-first page and preset-form design. This document
records runtime compatibility facts, not an alternative interface specification.

The existing runtime validates `catalog/printer/catalog.json` and structured
instance drafts. Reference mappings carry pinned source paths, hashes and line
locators. Unknown hardware identity, contacts, electrical limits and calibration
remain unknown. No board identity, clock, polarity or curve is inferred from a
similar product. Octopus non-Pro/Pro references are distinct.

The printer Store acquires host exclusion before feature exclusion. Mutations
compare revision and loaded host identity. Reviews bind draft, catalogue,
generator and host context; uncertain acknowledgment requires reconciliation.
Corrupt/newer-schema input is preserved for diagnostic export. Private MCU
identities belong to the instance, not published definitions or browser storage.
Incomplete selections can be saved. Generated candidates remain inactive until
explicit, reviewed managed publication. See [the public contract and publication
requirements](printer-public-format.md). Built-in choices are factory SV08 only;
third-party definitions use the source workflow.

Sensor generation uses a positive allowlist. Full candidates require resolved
motion, currents and thermal inputs. Preserve upstream heater protections.
Custom curves and calibration belong to a specific sensor/component fingerprint.
The Funssor complete-bed reference lacks supplied thermistor identification;
manufacturer temperature claims do not establish a replacement software cutoff.
The Sovol MAX module uses a separate CAN controller; original-SV08 adaptation
and compatible module firmware remain installation requirements.

New supported catalogue data uses the same semantic validation and generation
pipeline. Public definitions, source identity, lock snapshots, deterministic
composition and managed output must follow the two current design briefs.

[Shared-shell runtime invariants](printer-cockpit-panel.md) cover session,
navigation and exact staging. [Dated installed evidence](../features/printer-upgrade-profiles/installed-evidence.md)
records previous delivered software, not the new design's acceptance.

## Complete factory SV08 reference

`sv08.factory` version 0.2.0 composes the two controller mappings and 24 devices
from Sovol's pinned `a60644875f8c756d20b3828c9416518b414b5491` tree: X/Y and
four geared Z motors, extruder/hotend and both thermistors, bed heater, inductive
probe, pressure contact, filament switch, three generic fans, the heater-controlled
hotend fan and tachometer, ADXL345, UC1701 display/controls, beeper, case LED,
display neopixels and both MCU temperature monitors. Bed mesh, gantry levelling
and documented motion defaults belong to the assembly. Host temperature monitoring
belongs to host software rather than an additional printer hardware device.

Reproduce the catalogue and public records with
`python3 scripts/update_factory_definitions.py --source-root /path/to/pinned/checkout`.
The script refuses a changed vendor configuration hash. Each hardware field has a
source line and transformation; derived software defaults cite their own pinned
source file and hash. LCD GPIOs resolve the vendor's EXP aliases. Board snapshots
retain exact electrical mappings and source lines without repeating the full
citation at every pin, keeping the complete selection within the existing 128 KiB
limit. Additional documented GPIOs cannot change an existing pin's capabilities,
reservation, connector/contact identity or motor bundle.

Mainline adaptations are explicit: ADXL345 uses the vendor SPI2 wires and rate
with software SPI; native `safe_z_home` uses documented home coordinates/speeds
instead of copying the vendor raw homing override; sensorless X/Y omit
`hold_current` as required by the pinned mainline TMC guidance. The vendor's 5 s
LED PWM period exceeds mainline's 3 s maximum, so the definition uses the pinned
0.1 s upstream default. Obsolete `max_accel_to_decel` is not emitted. The pressure
contact is an empty-action native input, not a replacement implementation of
Sovol's proprietary pressure probing/automatic Z-calibration workflow.

Private MCU identities and measured probe Z offset are local inputs. Published
motor currents are documented configuration defaults, not invented motor ratings;
changing a current or its connector requires a separate owner-entered rating.
Measured PID gains are excluded and watermark control is the uncalibrated state.
Hardware selection requires no PID calibration and never activates outputs.
