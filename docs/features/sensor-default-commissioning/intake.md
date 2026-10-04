# Default-curve sensor commissioning intake — 2026-10-04

Owner requests default component conversion curves and defers fine calibration;
see [owner scope](../printer-component-configuration/owner-request.md).
The existing bed/hotend definitions exactly match pinned Sovol factory defaults.
Use them unchanged for the candidate input-only baseline; do not replace an unknown
installed sensor with an assumed Generic3950/PT1000 and do not fit to a BLE point.
Actual upgraded sensor part identities remain unknown. This is a proposed
observation configuration, not heater approval or completed H05 acceptance.

Separate [source research](source-findings.md) traces the preserved points,
software pull-ups and input pins to vendor and upstream revisions. Runtime
Sol6.1/medium/full role was coordinator-verified. Schematic pull-ups remain
unverified; source software values are not physical resistor measurements.
The existing installed file-output evidence can be reused for these unchanged
bytes; live MCU input configuration needs a fresh exact action review.

Beelink's existing BTHome reader completed a bounded25-second scan: five
advertisements across three packet IDs, one BTH01 advertiser, 27.67–27.68°C,
49.75%RH and100% battery. [Sanitized receipt](ble-intake.json) binds the private
capture. Owner confirmed the exact observed identity is the chamber BTH01Y_v3.1 running
[pvvx/THB2 custom firmware](https://github.com/pvvx/THB2); installed revision unknown;
this scan is not a simultaneous bed/hotend comparison. Decoder signed little-endian
0.01°C temperature handling agrees with [BTHome v2 format](https://bthome.io/format/),
accessed2026-10-04. A fresh paired capture is needed for an ambient comparison.

The hotend name alone cannot select a sensor: the manufacturer's current
[CHCB-SV08 page](https://www.trianglelab.net/products/chcb-sv08-hotend-hot-side)
lists NTC and PT1000 options (accessed2026-10-04). This does not identify which part
is installed. Catalog choices must distinguish these alternatives explicitly.

Planned operation (now completed below): prepare/review a bounded temporary input-only Klippy session, use autonomous
PSU on/off while retaining USB host power, collect repeated temperature/button
baselines alongside fresh BLE advertisements, stop the temporary session and
return PSU off. No heaters/steppers/fans or normal printer service activation.
Attended probe/filament resting→operated→resting checks are separate H05 rows;
X/Y sensorless homing is subsequent motion work. No automatic calibration fitting.

## Initial live observation and correction

The separately reviewed temporary input-only session reached ready, but the first
query preceded both ADC callbacks: temperature0/min99999999/max0 exactly match
pinned temperature_sensor.py initial sentinels. The cold sanity check stopped the
process; coordinator monitoring then observed the unit already inactive. These
are not measured zero-degree temperatures. Unit inactive/MainPID0, closed ports,
PSU OFF/statusOFF and unchanged host boot/masks were recorded. No valid12-sample
baseline was obtained. A bounded first-callback wait is prepared for separate
review; no curves/pull-ups/limits changed and no automatic rerun occurred.

## Corrected ambient baseline completed

The first correction was rejected by independent review before execution: late
responses and one initialized sensor beside an uninitialized sensor needed tighter
checks. The corrected F2 script passed [exact action review](reviews/f2-review.md)
with verified separate Sol6.1/medium runtime, then ran once. The original failure
and rejected F1 candidate remain preserved; neither was silently retried.

The [measured result](ambient-baseline.json) contains 12 valid samples spanning
55.04 seconds: hotend 26.56–26.62°C, bed 27.46–27.56°C. Beelink simultaneously
received 15 advertisements from the owner-confirmed chamber sensor, 27.68–27.70°C.
Different locations and unknown reference accuracy prevent treating their
difference as a calibration correction. Factory curves and pull-ups are unchanged;
fine calibration remains deferred.

Probe and filament inputs remained RELEASED throughout; no physical transitions
were tested. The temporary process exited, unit inactive/dead/MainPID0; there were
no open users of the remaining mainboard serial port, and the toolhead port was
absent after OFF. The redundant stop returned 5 because the completed transient
unit had already unloaded. PSU OFF was confirmed by Beelink's utility, not a
voltage measurement. Host boot/CID,
root and boot read-only mounts, masks, inactive printer services and absence of
active printer.cfg were preserved. No heater, motor or fan output was configured.
This completes the autonomous ambient observation slice, not H05 physical input
polarity, temperature accuracy over the operating range, or heat/motion acceptance.

[Independent closure review](reviews/closure-review.md) supports this result with
record clarifications, now incorporated. Its separate Sol6.1/medium/full-role
runtime was coordinator-verified. The inherited private review field
`target_bindings.capture_script_sha256` retains the original failed script hash;
the F2 `bindings.capture-inputs.py`, admission and executed staging instead use
`b3269815bf2022a301eaa5e8fee75cd3fc47e10f0320044279f3cf996ec85407`.
Historical fields are preserved rather than rewritten. Cleanup's empty exception
list does not mean every redundant command returned zero. Preservation claims
cover the sampled invariants, not an exhaustive host-file or cgroup inventory.
