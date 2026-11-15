# One SV08 commissioning session

Status: prepared offline; no physical check is marked passed here. This is the
single H01/H02/H04/H05/H06 session form linked by the
[human queue](coordinated-human-tasks.md). Use it for the identified printer with its actual selected definitions, including modifications. The filename retains its historical named
machine identity; an unmodified printer and exhaustive parameter combinations are not prerequisites for this session.
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
| 6. Validate heating and extrusion | With identified sensor/heater parts, reviewed limits and an independent reference, observe each approved controlled heat response and shutdown. Stop on implausible readings, overshoot or protection failure. Perform reviewed PID/extrusion checks only after thermal behavior is accepted; persist any measured gains with native `SAVE_CONFIG` as described below, never by borrowing factory measured gains. Maximum configuration limits are not initial test targets. | H06 |
| 7. Record manual probe calibration | Establish the reviewed gantry/bed plane at the intended thermal state, then run the supported manual probe procedure and native `SAVE_CONFIG`. Wait for restart and automatic reconciliation, then confirm the persisted value in Cockpit. Exercise the actual print-start levelling and Z-rehoming sequence and verify the nozzle-to-bed reference before first extrusion. If levelling changes that reference, recalibrate after levelling and rebuild the mesh before printing. | H06 |
| 8. First layer and print controls | With all preceding gates passed, use a known bounded test file and matching slicer start/end controls. Attend the first layer; separately verify pause, resume, cancel and shutdown. Record observed behavior, not just a successfully uploaded file. | H06 |
| 9. Finish cleanly | Stop the job and outputs, preserve logs/calibration/configuration, confirm the intended persistent/stopped service state and record which capabilities are accepted. Accept the actual configured printer and record its selected definitions; no exhaustive combination testing is required. | H02/H06 closure |

Stop immediately for smoke, unexpected heat/motion, wrong input association,
communication loss or any inability to stop. Use the reviewed independent stop
control. Do not continue by weakening heater protections, inventing offsets,
changing limits or disabling a guard. Send one exact failed phase/evidence reference
to the coordinator and keep the setup available for diagnosis where safe.

Fine sensor-curve fitting remains deferred. The earlier chamber BLE measurement is
a location-specific ambient reference, not proof of heater temperature accuracy or
a reason to fit a conversion curve. Forced update fallback and destructive recovery
are separate controlled maintenance qualifications, not extra first-print tasks.

## Native Klipper calibration and persistence

The generated setup uses the sourced starting offset of zero until a measured
probe offset is recorded. A persisted measured zero is valid; a starting zero is
not evidence that calibration has been performed. Full printing starts guarded
and the observer acknowledges only a matching loaded configuration and accepted
calibration. Explicit Setup mode remains blocked.

Under the reviewed physical procedure, use normal Klipper calibration tools:

1. Establish the intended warmed gantry/bed plane, then run the supported
   `PROBE_CALIBRATE` / `TESTZ` / `ACCEPT` interaction.
2. Issue normal `SAVE_CONFIG`. Klipper persists the result and restarts. There is
   no required transcription into Cockpit or separate hardware publication for
   this calibration-only save.
3. Wait for Klipper to become ready and Cockpit's calibration synchronization
   message to report acceptance. Confirm the persisted value survives reload in
   **Printer Hardware → Inspect changes → Configuration output, calibration and
   expert actions → Existing component calibration**. Pending/conflicting values
   are not a successful active calibration.
4. Before first extrusion, exercise the actual print-start levelling, Z-rehoming
   and mesh sequence in the reviewed thermal state, then verify the nozzle-to-bed
   reference. Record the active configuration hash for this phase.

The [pinned Klipper guidance](https://github.com/Klipper3d/klipper/blob/f0892d82b0f1c1228454f09eb508eddde2250f4b/docs/Probe_Calibrate.md#calibrating-probe-z-offset)
requires recalibration after changes to the motion system, hotend position or
probe location. With XY probe offsets, a changed bed tilt can also invalidate the
measurement and dependent mesh. QGL can change that relationship; it is not proof
of an offset's validity. The normal generated QGL → Z-rehome → mesh sequence is
retained, consistent with the [published Voron start example](https://docs.vorondesign.com/community/howto/EricZimmerman/SlicerAndPrintStart.html).
Whether this configured machine reproduces its calibrated reference is an attended
check. If it does not, stop, recalibrate after levelling and rebuild the mesh.

Supported native results are mirrored automatically against the applied hardware.
Unrelated root edits, immutable include drift and incompatible records are refused;
normal later hardware publication/restoration still requires stopped services.
Manual calibration fields remain optional overrides. If used, save, regenerate,
review and apply stopped; they do not authorize writing generated files by hand.
Replacement of affected hardware clears dependent measurements. The automatic
observer validates persisted data and loaded configuration, not physical accuracy.

## Optional heater PID calibration

Hardware selection does not require PID calibration. Supported Full configurations
can retain explicitly selected watermark control while PID is deferred. Do not
invent or borrow measured gains.

After thermal identity, limits and response have passed their reviewed checks,
use Klipper's normal PID calibration for the identified heater and agreed target,
then `SAVE_CONFIG`. The native result includes PID control and gains; automatic
reconciliation records them without manually copying numbers or changing an
advanced control selector. Wait for accepted synchronization and verify the active
control/gains and thermal response before printing.

If PID remains deferred, record the accepted watermark behavior and limits. Fine
sensor-curve fitting remains deferred; changing control mode does not identify an
unknown sensor. Keep this phase's result/configuration binding in the same session
record instead of repeating unaffected input checks.

## Handoff

The coordinator links this single result into H01/H02/H04/H05/H06, recording exact
passed phases and exclusions. Unresolved fitted parts, activation, calibration or
print behavior remain named dependencies with the next useful action. No H row is
closed from an empty form, a parser pass, an export or a publication receipt.
