# Test SV08-01 printer configuration intake

Status: P1 public-source gap inventory, prepared offline on 2026-09-18. This is a proposal-ready intake boundary, not an installable printer configuration. Target: the owner-described modified test machine in [profile.json](../../profiles/test-sv08-01/profile.json), currently `status: research` and `hardware_verified: false`.

## Source and evidence boundary

The source pair is Sovol SV08 `a60644875f8c756d20b3828c9416518b414b5491` and upstream Klipper `f0892d82b0f1c1228454f09eb508eddde2250f4b`, pinned in [upstream-lock.json](../../upstream-lock.json). Public findings below come from the pinned vendor files and upstream files named in [vendor-compatibility.md](../vendor-compatibility.md). The commissioning templates are [no-outputs](../../configs/commissioning/test-sv08-01-no-outputs.cfg), [sensors](../../configs/commissioning/test-sv08-01-sensors.cfg), and [inputs](../../configs/commissioning/test-sv08-01-inputs.cfg).

The coordinator-supplied [sanitized section inventory](printer-candidate-sections.md) now crosschecks all 30 retained and 86 omitted section names. It is sufficient to close the inventory dependency for proposal work; it does not prove readiness or authorize installation. No serials, calibration, credentials, raw captures, or private paths belong here.

## Public configuration gaps and smallest proposal-ready scope

| Gap / exact public evidence | Current safe treatment | Smallest implementation scope after sanitized inventory | Required evidence / dependency |
| --- | --- | --- | --- |
| Vendor `printer.cfg` uses removed `max_accel_to_decel`; upstream records removal in `upstream/klipper/docs/Config_Changes.md` | Omit the removed option | Add reviewed motion limits and `minimum_cruise_ratio` in the candidate configuration; do not claim equivalence | Exact retained motion sections; mechanical bounds and H06 motor/homing evidence |
| Vendor `probe_pressure.py` and `[probe_pressure]` are vendor-only (`upstream/sovol-sv08/.../probe_pressure.py`, vendor `printer.cfg`) | Do not copy vendor extra | Select upstream/manual probing path for first commissioning; defer pressure implementation to a separately tested feature | H01 probe/circuit identity; decision on automatic calibration; H06 probe evidence |
| Vendor `z_offset_calibration.py` calls `run_probe`, while pinned upstream `klippy/extras/probe.py` exposes a different API | Automatic Z calibration remains deferred | Document and exercise reviewed manual Z-offset sequence; implement adapter only with regression tests and explicit approval | Sanitized retained calibration sections; upstream API comparison; H06 manual-offset result |
| Vendor `get_ip.cfg`, `Macro.cfg` shell hooks and `gcode_shell_command.py` have no upstream equivalent | Remove optional shell hooks from minimal stack | No custom shell implementation for first print; add one only as a separately scoped, tested feature | Sanitized macro/include inventory; host service requirements; no shell hook needed for print controls |
| Published vendor directory references `mainsail.cfg`, `timelapse.cfg`, `moonraker_obico_macros.cfg` not present beside the inspected `printer.cfg` | Resolve required includes from selected packages or omit optional includes deliberately | Produce a closed include list for the selected host payload; add only missing required files | Sanitized installed include tree; package/source revision; offline file-output check |
| Vendor thermistor curves and hotend `pullup_resistor: 11500` are configuration facts, not measured circuits | Input-only templates preserve values with explicit warning | Keep software curve/pull-up only as a candidate pending circuit and reference validation; do not tune from ambient samples | H01 sensor/circuit identity; current independent reference; H05 result |
| Vendor gantry/mesh macros combine homing, heat and mesh choreography | Keep commissioning gates separate | Reuse only upstream primitives after travel, probe and thermal checks; defer convenience choreography | Sanitized retained macro list; H06 separate gate results |
| `plr.cfg` invokes host scripts and `SET_KINEMATIC_POSITION`; inclusion is not established by file presence | Omit power-loss recovery from first commissioning | No implementation in first-print slice; later feature requires dedicated failure/recovery tests | Installed include inventory; H07 plan and recovery artifacts |
| Vendor config embeds `/home/sovol` paths, serial enumeration and saved calibration | Use private placeholders/local state | Bind two serial placeholders and local state paths in a reviewed candidate; keep calibration private | Sanitized path/section inventory; exact paired MCU identities and hashes |
| Vendor optional timelapse, Obico, displays and input-shaper calibration are omitted by the private candidate per existing audit | Keep out of minimum first-print scope | No implementation until core print path is accepted; add only with separate requirement and evidence | Owner requirement; host package/UI evidence; later bounded proposal |

## Candidate closure checklist

The coordinator should attach or link a sanitized record containing:

- every retained and omitted top-level section from the private resolved candidate, without serials, credentials, calibration values or raw captures;
- the exact host and both MCU source revisions, artifact hashes, MCU serial placeholder mapping, and selected include tree;
- confirmation that no ADC pin or heater ownership is duplicated between input-only checks and the printing candidate;
- preserved heater minimum/maximum limits and shutdown protections;
- ordinary print, pause, resume, cancel and shutdown control mapping;
- the selected manual Z-offset sequence and the explicit decision to defer pressure calibration;
- offline file-output results for the exact candidate and matching MCU dictionary.

This closure is the smallest implementation handoff. The bounded controls slice is documented in the [inactive upstream print-controls proposal](printer-controls-proposal.md); it deliberately leaves output-bearing resume/cancel behavior and all commissioned macros to a later H06 proposal. It does not authorize activation, flashing, heating or motion. Hardware dependencies remain H01 (board/sensor/circuit facts), H02 (capture-ready host/MCU start), H05 (input and ambient reference), and H06 (staged outputs through first print) in [coordinated human tasks](../hardware/coordinated-human-tasks.md).

## Offline next actions

1. Bind the supplied section inventory to the pinned host/MCU revision pair and mark each gap `resolved`, `deferred`, or `blocked` with a source path.
2. Run the existing file-output configuration check against the exact candidate; retain output and hashes in the coordinator's evidence path.
3. Prepare H01/H02/H05 requests with target identity, preconditions, capture owner, expected observations and stop conditions.
4. After H05 passes, review the smallest H06 candidate and its manual homing/offset procedures; do not issue ordinary `G28` from an unreviewed configuration.

No public-source gap here establishes a hardware value. The installed board, sensor circuits, input polarity, homing behavior, heater response and print controls remain measured or human-session evidence.
