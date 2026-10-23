# One SV08 commissioning session

Status: prepared offline; no physical check is marked passed here. This is the
single H01/H02/H04/H05/H06 session form linked by the
[human queue](coordinated-human-tasks.md). Use it for an identified stock target or
an explicitly declared modified target. The filename retains its historical named
machine identity; it does not make that modified printer representative of stock.
See the [current readiness and remaining gaps](../development/stock-printer-readiness.md).

The purpose is to reach an attended first print with the correct configuration,
without asking for repeated inspections, media moves or calibration transcription.
Keep one private session record and link it from every consuming H row. Do not put
serials, private configuration, calibration, keys or raw captures in this document.

## Before scheduling the attended work

The coordinator prepares the exact candidate/configuration manifest, firmware/source
matches, last applicable evidence, logging and a known stop/restore route. The owner
confirms the actual target and available independent recovery medium. Reuse earlier
measurements only when the same parts, wiring and configuration still match; do not
ask the owner to recreate source inventories. Never ask for a media move before
reviewed bytes, target boundaries and the writing procedure are ready.

The session packet must identify how Klipper will be launched for each approved
phase, its configuration hash, service/socket ownership, output limits and stop
procedure. Configuration publication deliberately leaves Klipper stopped. Current
diagnostic images retain production masks and do not grant normal OS-health
readiness. Their physical commissioning launch must receive a separate exact-target
operation assessment and owner authorization. **No generic unmask/start command or
fabricated health marker is part of this form.** If no supported/reviewed activation
route is ready, stop at that explicit integration dependency before requesting
output tests; do not disguise it as a failed sensor or ask the owner to debug Linux.

For an unqualified factory host, prepare target-specific boot/MCU and independent
recovery checks before any installation. The existing complete diagnostic image is
not a generic stock printing installer. This session does not authorize flashing,
power cycling, motion or heating merely because its instructions exist.

## One header, one result log

Record these once in the assigned private session directory:

- Date/operator, physical target, selected profile and fitted parts; mark stock or modified.
- Image/source/slot/boot and both MCU revision/identity bindings; reuse exact known evidence where still applicable.
- Saved hardware revision and final Full configuration/manifest hash/publication receipt; record each earlier input-only, setup or calibration candidate separately.
- Independent reference instrument, approved phase limits, stop control, recovery route and capture paths.
- Exact reviewed activation procedure, operation authorization and coordinator contact.

Use a single row per phase: `time | configuration hash / launch-stop review binding | pass/fail/inconclusive | observation/evidence | next action`.
A failed/inconclusive prerequisite stops dependent phases. Leave later rows unpassed.
A safe pause between phases is allowed; changed hardware/configuration invalidates
its dependent evidence, not unrelated completed checks.

## The session, in order

| Phase | Owner/coordinator action and observable pass condition | H dependency |
| --- | --- | --- |
| 1. Identify the fitted machine | With power isolated, including USB/serial back-power, confirm board/connector/part evidence and wiring changes without unnecessary disassembly. Confirm factory bed/hotend/sensors or choose definitions for the actual replacements. Do not select a factory sensor merely because a hotend name matches. | H01 |
| 2. Establish the host and stopped setup | Arm capture, then use only the reviewed boot/installation procedure. Confirm intended slot, persistent configuration/identity, correct MCU revision/serial association, Mainsail/Moonraker access and no unintended outputs. Confirm the independent recovery/stop route. No trial, update or service race may be active. | H02/H04 |
| 3. Check inputs before outputs | Use the reviewed input-only configuration. Observe each actual probe/filament/endstop released–operated–released transition and physical association. Compare plausible stable ambient readings with the independent reference. Take pins, names and configured conversion settings from this session's generated manifest, not old hardcoded pin tables. | H05 |
| 4. Verify stop, fans and motors | After phase 3 and exact action review, enable only the approved phase. Verify the stop path and each physically identified fan; check one bounded motor action/direction at a time with clear travel. Wrong direction, unexpected motion or inability to stop is a failure. | H06 |
| 5. Establish homing/probing | Verify the configured probe and sensorless/DIAG dependencies before the separately reviewed bounded homing sequence. Do not issue ordinary `G28`, gantry levelling or mesh before these dependencies pass. Keep pressure GPIO observations separate from proprietary automatic calibration. | H06 |
| 6. Validate heating and extrusion | With identified sensor/heater parts, reviewed limits and an independent reference, observe each approved controlled heat response and shutdown. Stop on implausible readings, overshoot or protection failure. Perform reviewed PID/extrusion checks only after thermal behavior is accepted; persist any measured gains through Cockpit as described below, never by borrowing factory measured gains. Maximum configuration limits are not initial test targets. | H06 |
| 7. Record manual probe calibration | Perform the supported manual probe procedure under the reviewed motion/temperature state. Record the reported measurement in Cockpit as described below, save/regenerate/apply stopped, then restart only under the reviewed procedure. Confirm the saved value survives reload and the candidate no longer reports pending probe calibration. Perform the reviewed gantry/mesh checks in their correct thermal state. | H06 |
| 8. First layer and print controls | With all preceding gates passed, use a known bounded test file and matching slicer start/end controls. Attend the first layer; separately verify pause, resume, cancel and shutdown. Record observed behavior, not just a successfully uploaded file. | H06 |
| 9. Finish cleanly | Stop the job and outputs, preserve logs/calibration/configuration, confirm the intended persistent/stopped service state and record which capabilities are accepted. Stock support requires an actual stock target; a modified target proves only its selected configuration. | H02/H06 closure |

Stop immediately for smoke, unexpected heat/motion, wrong input association,
communication loss or any inability to stop. Use the reviewed independent stop
control. Do not continue by weakening heater protections, inventing offsets,
changing limits or disabling a guard. Send one exact failed phase/evidence reference
to the coordinator and keep the setup available for diagnosis where safe.

Fine sensor-curve fitting remains deferred. The earlier chamber BLE measurement is
a location-specific ambient reference, not proof of heater temperature accuracy or
a reason to fit a conversion curve. Forced update fallback and destructive recovery
are separate controlled maintenance qualifications, not extra first-print tasks.

## Manual Z offset: the supported persistence path

The generated configuration uses a sourced starting offset of zero while measured
calibration is missing; printing is blocked in that state. Under the reviewed manual
procedure, Klipper's `PROBE_CALIBRATE`/`TESTZ`/`ACCEPT` interaction reports the measured
`z_offset`. Those commands require the approved physical setup; do not run them as
an unattended test.

1. Record that measured result once in **Printer Hardware → Inspect changes → Configuration output, calibration and expert actions → Existing component calibration → Z offset**. A measured zero is valid; an unmeasured starting zero is not a completed calibration.
2. Save the hardware configuration, prepare/review the Full candidate and confirm the measured value and pending-calibration status. Reload to confirm persistence.
3. Publish/apply only through the stopped, drift-checked managed route. Restart using the separately reviewed activation procedure, then verify the active configuration matches the saved candidate before printing.

Do not rely on normal `SAVE_CONFIG` for this managed path: the generated probe
setting is in an include, and pinned Klipper refuses conflicting included settings.
Cockpit is the source of truth here; automatic `SAVE_CONFIG` ingestion is not
implemented. This is intentional explicit persistence, not permission to hand-edit
generated files or copy an old printer's offset. A bed/probe replacement clears its
dependent measurement; recalibrate the changed assembly before printing again.

## Retaining measured heater PID results

Factory Full configurations intentionally support watermark control before PID
calibration; do not invent gains or make PID a hardware-selection prerequisite.
If a reviewed PID calibration is performed, record its reported `pid_kp`, `pid_ki`
and `pid_kd` for the correct heater in **Existing component calibration**, and
select **PID (enter gains)** for that heater in its advanced device settings.
Save, regenerate and review the Full candidate, then publish stopped and restart
only through the reviewed procedure. Confirm the active control/gains and safe
thermal response before using them for a print. Ordinary `SAVE_CONFIG` is not the
persistence route for included managed heater settings either.

If PID is deferred, keep the explicitly selected watermark mode and document its
accepted thermal behavior/limits. Fine sensor-curve calibration remains deferred;
changing control mode does not authorize fitting an unknown sensor curve. Link
this phase's measured results and configuration hash once, without redoing
unaffected input checks.

## Handoff

The coordinator links this single result into H01/H02/H04/H05/H06, recording exact
passed phases and exclusions. Unresolved fitted parts, activation, calibration or
print behavior remain named dependencies with the next useful action. No H row is
closed from an empty form, a parser pass, an export or a publication receipt.
