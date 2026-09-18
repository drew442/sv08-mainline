# Test SV08-01 commissioning session record

Status: prepared offline; no session result is implied. Profile: [test-sv08-01](../../profiles/test-sv08-01/profile.json), whose hardware identity and support status remain unverified. Use this form only with the coordinator's reviewed configuration and an identified target.

This form groups the ready work for H01, H02, H05 and H06 while preserving their safety boundaries. The canonical dispatch queue is [coordinated human tasks](coordinated-human-tasks.md). Do not copy serials, credentials, raw captures or private calibration into this file; put them in the ignored local evidence path and record only its evidence reference below.

## Session header

| Field | Record |
| --- | --- |
| Session date / operator | `____________________________` |
| Target/profile and physical identity evidence | `____________________________` |
| Board revisions / sensor and heater evidence (H01) | `____________________________` |
| Host image / slot / boot ID (H02) | `____________________________` |
| Mainboard and toolhead Klipper revision | `f0892d82b0f1c1228454f09eb508eddde2250f4b` / `________________` |
| Reviewed configuration path and hash | `____________________________` |
| Private evidence directory / capture IDs | `____________________________` |
| Coordinator and stop contact | `____________________________` |

Record each stage separately. A communication or input pass does not pass a later output, motion, homing, thermal, calibration or print gate. If hardware, wiring, firmware, host image, or reviewed configuration changes, invalidate the affected downstream rows and begin a new session record.

## Stage H01 — unpowered inspection and identity

**Preconditions:** printer is fully unpowered and isolated; the inspection list and safe procedure have been reviewed. Do not remove unnecessary heatsinks or disturb wiring.

**Action / observation:** inspect and photograph markings and connectors privately; identify only facts supported by marking, schematic comparison or measurement. Reuse existing MCU/oscillator marking evidence. Record only unresolved installed board revisions, hotend and bed sensor/heater parts or unresolved status, probe and filament physical associations, and any wiring change.

| Field | Record |
| --- | --- |
| Power-isolated state confirmed by | `________________` at `________` |
| Target and board evidence path | `____________________________` |
| Mainboard revision / evidence level | `____________________________` |
| Toolhead revision / evidence level | `____________________________` |
| Sensor/heater identities and circuit evidence | `____________________________` |
| Probe and filament physical association | `____________________________` |
| Result: pass / fail / inconclusive | `________________` |
| Stop reason or unresolved dependency | `____________________________` |
| H01 evidence reference | `____________________________` |

**Stop immediately** for unexpected power, damaged insulation, an unidentified connection that must be disturbed, or any need to energize the printer to complete inspection. Dependency for H05 is sufficient sensor/circuit and input-association evidence; a universal PCB revision is not required if the relevant pins and safety facts are otherwise evidenced.

## Stage H02 — capture-ready power and paired MCU start

**Preconditions:** H01 physical state is recorded; the reviewed host image/slot and printer state are known; logs are armed before reconnecting power; serial/USB back-power risk is accounted for. This stage does not enable outputs.

**Allowed observations:** record cold/warm boot, host health, USB enumeration and the paired MCU `ready` result using the coordinator's reviewed capture procedure. Use the existing no-output configuration only with private serial substitutions: [test-sv08-01-no-outputs.cfg](../../configs/commissioning/test-sv08-01-no-outputs.cfg). The existing paired USB evidence is a reference, not a new session result.

| Field | Record |
| --- | --- |
| Capture armed before power reconnection (ID) | `____________________________` |
| Intended image/slot and safe printer state | `____________________________` |
| Mainboard identity / application revision | `____________________________` |
| Toolhead identity / application revision | `____________________________` |
| Host and MCU boot observations | `____________________________` |
| Output state confirmed disabled | `____________________________` |
| Result: pass / fail / inconclusive | `________________` |
| Stop reason or unresolved dependency | `____________________________` |
| H02 evidence reference | `____________________________` |

**Stop immediately** for smoke, heat, unexpected current or motion, loss of communication, boot failure, or any output becoming active. H02 passing permits H05 input-only checks; it does not permit H06 outputs or ordinary homing.

## Stage H05 — read-only inputs and ambient reference

**Preconditions:** H01 sensor/input facts and H02 paired no-output start pass; independent temperature instrument is present; outputs remain disabled; reviewed input-only configuration is loaded. Use [test-sv08-01-sensors.cfg](../../configs/commissioning/test-sv08-01-sensors.cfg) and [test-sv08-01-inputs.cfg](../../configs/commissioning/test-sv08-01-inputs.cfg) only as the documented input-only includes. Their settings are preserved software values, not verified component identities.

**Validated queries:** query `gcode_button probe_check` and `gcode_button filament_check` and record the physical action, observed transition and polarity. Do not infer physical association from the logical label. Record simultaneous ambient readings from both configured inputs and the independent instrument; old samples are historical references only.

| Field | Record |
| --- | --- |
| Configuration path/hash and paired MCU evidence | `____________________________` |
| Independent instrument / calibration reference | `____________________________` |
| Room/reference temperature and time | `____________________________` |
| Hotend input (`extra_mcu:PA5`, software pull-up 11500 ohm) | `____________` / `____________` |
| Bed input (`PC5`, upstream default pull-up 4700 ohm) | `____________` / `____________` |
| `probe_check` released → pressed observation | `____________________________` |
| `filament_check` released → pressed observation | `____________________________` |
| Physical association and polarity confirmed | `____________________________` |
| Result: pass / fail / inconclusive | `________________` |
| Stop reason or unresolved dependency | `____________________________` |
| H05 evidence reference | `____________________________` |

**Stop immediately** for a sensor outside its declared bounds, implausible or rapidly changing values, unexpected input transitions, inability to identify the physical input, or any output activity. H05 is the gate for H06; it does not validate heated operation.

## Stage H06 — attended outputs, motion, heat and first print

Run each row only after the preceding row passes. Use a reviewed configuration and operator-visible stop control. The candidate commissioning limits recorded in the source packet are proposals, not validated machine limits. Never issue ordinary `G28` from this form: use a separately reviewed homing sequence after endstop/probe checks.

| Gate | Preconditions and bounded action | Evidence / result |
| --- | --- | --- |
| Fans and shutdown | H05 pass; identify fan physically; perform the coordinator's bounded fan test and shutdown observation | `time ______ target ______ observation ____________________ pass/fail/inconclusive ______ evidence ______` |
| Motors and direction | Fan gate pass; clear workspace; test one bounded motor action at a time with immediate stop available | `time ______ axis ______ observation ____________________ pass/fail/inconclusive ______ evidence ______` |
| X/Y sensorless and Z probe homing | Motor gate pass; DIAG/probe facts reviewed; use attended, reviewed sequence; no unreviewed `G28` | `time ______ sequence ______ observation ____________________ pass/fail/inconclusive ______ evidence ______` |
| Controlled heat and reference | Homing gate pass; independent reference and limits reviewed; supervise temperature continuously | `time ______ heater ______ observation ____________________ pass/fail/inconclusive ______ evidence ______` |
| PID / extrusion | Controlled heat pass; heater response and sensor behavior accepted; run only reviewed bounded procedure | `time ______ procedure ______ observation ____________________ pass/fail/inconclusive ______ evidence ______` |
| Gantry / mesh / manual Z offset | Previous gates pass; reviewed upstream manual Z-offset procedure selected; pressure calibration remains deferred unless separately approved and evidenced | `time ______ procedure ______ observation ____________________ pass/fail/inconclusive ______ evidence ______` |
| First layer and print controls | All prior gates pass; attended first layer; verify pause, resume, cancel and shutdown controls separately | `time ______ file ______ observation ____________________ pass/fail/inconclusive ______ evidence ______` |

**Stop immediately** for unexpected temperature, heater runaway or shutdown failure, smoke, smell, noise, wrong direction, unexpected travel, endstop/probe failure, loss of communication, or any inability to stop. Record the exact gate and leave later rows blank. H06 evidence is physical commissioning evidence for this target only; it does not certify stock SV08 support.

**H06 dependency handoff:** `H05 evidence ____________________` → `reviewed candidate/config hash ____________________` → `next ready gate ____________________`. If any gate is fail or inconclusive, send the exact H06 sub-gate and evidence reference to the coordinator; do not request a second physical action until the affected configuration or safety dependency is reviewed.

## Handoff and dependency record

| Item | Record |
| --- | --- |
| H IDs consumed | `H01, H02, H05, H06` / `________________` |
| Passed gates and linked evidence | `____________________________` |
| Failed or inconclusive gate and reason | `____________________________` |
| Next ready offline action | `____________________________` |
| Physical dependency sent to coordinator | `____________________________` |
| Invalidation trigger for this record | `____________________________` |

The [configuration intake](../development/printer-configuration-intake.md) now links the coordinator-supplied sanitized section inventory. Next bind both serial placeholders and exact host/MCU revisions, then resolve the public-source gaps before any activation request. No new owner inventory is required for that offline preparation.
