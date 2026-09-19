# Test SV08-01 minimal upstream print-controls proposal

Status: bounded proposal only; no implementation or activation is authorized by this document. Target profile: [test-sv08-01](../../../profiles/test-sv08-01/profile.json). Proposal source pair: Sovol SV08 `a60644875f8c756d20b3828c9416518b414b5491` and pinned upstream Klipper `f0892d82b0f1c1228454f09eb508eddde2250f4b` in [upstream-lock.json](../../../upstream-lock.json). The [sanitized candidate inventory](../../development/printer-candidate-sections.md) closes the section-name intake: 30 retained, 86 omitted.

## Purpose and boundary

The candidate has the machine and safety sections needed for later commissioning, but it omits the reusable host interfaces that connect a selected G-code file to Klipper and expose pause, resume, cancel and messages. This proposal defines only an inactive upstream-compatible include:

`virtual_sdcard`, `pause_resume`, `display_status`, and `respond`.

The include is not print-ready and is not to be activated by itself. It contains no custom motion, homing, heating, extrusion, probing, calibration, shell, power-loss, timelapse or display-hardware macros. Its exposed upstream commands are not authorized for invocation by this proposal; RESUME can move and restart arbitrary G-code. Output-bearing resume/cancel behavior remains an explicit later H06 proposal.

## Pinned upstream interfaces

| Interface | Pinned source contract | Proposed use |
| --- | --- | --- |
| `virtual_sdcard` | `upstream/klipper/klippy/extras/virtual_sdcard.py` registers `SDCARD_RESET_FILE`, `SDCARD_PRINT_FILE`, `M20`–`M27`; `[virtual_sdcard]` requires a host `path` and supports `on_error_gcode`. The reference is `upstream/klipper/docs/Config_Reference.md`, `[virtual_sdcard]`. | Use the fixed public host path `/run/sv08/printer_data/gcodes`. Omit `on_error_gcode` so Klipper retains its upstream default `TURN_OFF_HEATERS` behavior when applicable; this is configuration behavior, not a heater safety certification. |
| `pause_resume` | `upstream/klipper/klippy/extras/pause_resume.py` registers `PAUSE`, `RESUME`, `CLEAR_PAUSE`, `CANCEL_PRINT`, and Moonraker endpoints `pause_resume/{pause,resume,cancel}`. `[pause_resume]` supports `recover_velocity`; upstream default is 50 mm/s. | Include the section without wrappers. `RESUME` can execute `RESTORE_GCODE_STATE ... MOVE=1` at the default recovery velocity, so it is an output-bearing operation when a saved state exists. `PAUSE` does not shut down heaters and queued motion may drain; bare `CANCEL_PRINT` only cancels virtual SD/clears pause state and does not guarantee heater, fan or streaming-host shutdown. |
| `display_status` | `upstream/klipper/klippy/extras/display_status.py` registers `M73`, `M117`, `SET_DISPLAY_TEXT`; the pinned implementation is loadable as an upstream extra and uses virtual SD progress when available. | Include the standalone section for host status semantics. This does not add a physical `[display]` section or assert display hardware; physical display integration remains H01/H04 work. |
| `respond` | `upstream/klipper/klippy/extras/respond.py` registers `M118` and `RESPOND`; `[respond]` selects default output type/prefix. | Enable default upstream echo behavior for macro and UI messages. No shell or network command is attached. |
| `PAUSE` / `RESUME` / `CANCEL_PRINT` | `pause_resume.py` owns these commands and the documented Moonraker endpoints. | The include exposes upstream behavior only. Any output-bearing resume/cancel macro, including heater/fan shutdown or host-stream stop, requires a separate H06 proposal and evidence. |

## Proposed file ownership and paths

This is the smallest file boundary for implementation after independent approval:

| Owner path | Contents | Explicit exclusions |
| --- | --- | --- |
| `configs/commissioning/test-sv08-01-print-controls.cfg` | Inactive upstream sections `[virtual_sdcard]` with `/run/sv08/printer_data/gcodes`, `[pause_resume]`, `[display_status]`, and `[respond]`; no machine macro include | No steppers, heaters, probes, homing, calibration, shell commands, vendor extras, physical display sections or path placeholders |
| `tests/test_printer_controls.py` | Offline tests against a synthetic file-output fixture and pinned source: section contract, fixed path, default error template retention, command semantics, and no vendor/macro additions | No MCU connection, service activation, readiness, physical input/output behavior or print success claim |
| `configs/host-os/systemd/sv08-klipper.service` and `configs/host-os/systemd/sv08-moonraker.service` | Existing service ownership remains unchanged; the proposal only consumes their established paths: `/run/sv08/printer_data/config/printer.cfg`, `/run/sv08/printer_data/config/moonraker.conf`, `/run/sv08/printer_data`, and the Klippy UDS | No unit edits in this proposal |

The implementation should include this file from the selected private machine configuration rather than replace that configuration. It must not add a second `[mcu]`, `[printer]`, heater, sensor or motion section. The host packaging must create and expose `/run/sv08/printer_data/gcodes` before any service activation review.

## Stock and private machine separation

The public stock material remains reference input only: [stock-sv08.md](../../hardware/stock-sv08.md) and the vendor configuration are not a source of installed machine values. The modified target's private machine settings remain in ignored local configuration and evidence paths. These include serial mappings, board-specific pins, thermistor curves and pull-ups, travel and limits, driver settings, calibration, saved variables and host paths.

The tracked controls proposal owns behavior and interface names. A later private overlay owns values. The coordinator must bind the overlay to the exact paired MCU revision/hash and host revision before file-output validation. A stock profile or stock macro cannot supply missing modified-machine values, and controls passing offline cannot certify either stock or modified hardware.

## Before / after behavior

| Behavior | Current candidate | Proposed result after implementation and offline checks |
| --- | --- | --- |
| File selection/start | `virtual_sdcard` omitted; host cannot use the standard virtual SD command path | Inactive `[virtual_sdcard]` points to `/run/sv08/printer_data/gcodes`; command execution is tested only with synthetic file-output input |
| Pause/resume/cancel | Vendor control macros are omitted; no standard pause module in the inventory | Upstream `pause_resume` owns commands and Moonraker endpoints, with its documented movement and shutdown limitations retained |
| Progress/status | `display_status` and `respond` omitted | Standalone upstream status/message interfaces are included; no physical display is asserted |
| Print boundaries | Vendor start/end choreography omitted | No `PRINT_START`/`PRINT_END` names are reserved here; a commissioned slicer contract must define them later |
| Failure handling | Vendor shell and power-loss macros omitted | No shell or power-loss behavior is restored; the omitted `on_error_gcode` retains upstream default behavior for the synthetic error test |

## Acceptance IDs and checks

The independent approver can review these bounded checks:

| ID | Acceptance check | Evidence |
| --- | --- | --- |
| pc-01 | Controls file uses only the pinned upstream section interfaces and contains no vendor-only Python extras, shell commands, power-loss, timelapse, homing, motion, heat, calibration or macro sections | Source paths, parser output and `tests/test_printer_controls.py` result |
| pc-02 | Exact private overlay plus controls include has one `[virtual_sdcard]` at `/run/sv08/printer_data/gcodes`, one `[pause_resume]`, `[display_status]` and `[respond]`; no duplicate section ownership | Sanitized include tree, config parser output and fixed-path test |
| pc-03 | Synthetic file-output execution covers `SDCARD_PRINT_FILE`/`M24`, pause, resume and cancel paths; tests assert the pinned behavior rather than merely command registration | Synthetic G-code fixture/output and test result; no hardware claim |
| pc-04 | `virtual_sdcard` omits `on_error_gcode` and retains upstream default `TURN_OFF_HEATERS`; test exercises only the documented G-code error path and records that physical heater shutdown remains unverified | Source comparison and synthetic error test; no heater certification |
| pc-05 | `display_status` standalone commands `M73`, `M117`, `SET_DISPLAY_TEXT` and `respond` commands are covered without adding physical display hardware | Synthetic command/status assertions |
| pc-06 | Existing service paths remain coherent: Klipper reads `/run/sv08/printer_data/config/printer.cfg`, Moonraker uses `/run/sv08/printer_data/config/moonraker.conf` and `/run/sv08/printer_data`; no service unit change is needed | Unit-file inspection and offline path assertions |
| pc-07 | File-output configuration validation passes for the exact paired host/MCU revision and private overlay, while heater protections and all machine values remain unchanged | Existing file-output result plus candidate/MCU hashes; no activation claim |
| pc-08 | H01/H02/H05 remain prerequisites for any H06 control use; output-bearing resume/cancel behavior and all commissioned macros remain explicit later H06 work | Links to [commissioning session](../../hardware/test-sv08-01-commissioning-session.md) and [coordinated queue](../../hardware/coordinated-human-tasks.md) |
## Deferred commissioning macros and next handoff

The following remain deferred: `PRINT_START`, `PRINT_END`, output-bearing resume/cancel wrappers, vendor pressure probing and automatic Z offset, homing override, gantry/mesh choreography, heater/PID/extrusion procedures, fan and motor actions, timelapse/Obico, physical displays, input shaping, power-loss recovery, shell commands, and convenience macros such as filament change. Their omission is intentional until their own source compatibility and H06 safety evidence are reviewed.

The next implementation handoff is the inactive controls include plus `pc-01`–`pc-07` tests. It must be reviewed by an independent approver before any implementation. After those checks pass, the coordinator can bind the private overlay and schedule H06 only after H01/H02/H05 evidence remains valid. This proposal does not request a human action.

## Sources

- [Sanitized candidate section inventory](../../development/printer-candidate-sections.md), coordinator inspection 2026-09-18.
- [Klipper Config Reference](../../../upstream/klipper/docs/Config_Reference.md), `[virtual_sdcard]`, `[pause_resume]`, `[respond]`, `[gcode_macro]` sections, pinned commit above; [G-Code reference display_status section](../../../upstream/klipper/docs/G-Codes.md#display_status).
- [Klipper virtual SD implementation](../../../upstream/klipper/klippy/extras/virtual_sdcard.py).
- [Klipper pause/resume implementation](../../../upstream/klipper/klippy/extras/pause_resume.py).
- [Klipper display status implementation](../../../upstream/klipper/klippy/extras/display_status.py).
- [Klipper host responder implementation](../../../upstream/klipper/klippy/extras/respond.py).
- [Klipper sample macros](../../../upstream/klipper/config/sample-macros.cfg) (interface names only; motion/heat sample body is excluded).
- [Klipper G-Code reference](../../../upstream/klipper/docs/G-Codes.md), pause/resume, respond and virtual SD sections.
- [SV08 Klipper service](../../../configs/host-os/systemd/sv08-klipper.service) and [Moonraker service](../../../configs/host-os/systemd/sv08-moonraker.service).
