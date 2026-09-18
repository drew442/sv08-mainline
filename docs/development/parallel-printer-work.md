# Parallel printer delivery work packet

Status: source-backed offline planning packet, 2026-09-18. Owner: printer
delivery coordinator. This packet prepares bounded work for `test-sv08-01`; it
does not activate services, change a runtime configuration, write firmware or
media, or certify hardware.

The canonical coordination records are [parallel work](parallel-work.md) and
[coordinated human tasks](../hardware/coordinated-human-tasks.md). The existing
human checklists remain authoritative:
[host OS tasks](../hardware/host-os-tasks.md#human-and-powered-printer-tasks)
and [printer recovery tasks](../hardware/test-sv08-01-recovery-tasks.md).

## Delivery boundary and current state

The target is the owner-described modified SV08 test machine, not an untouched
stock qualification target. Its profile remains `status: research` and
`hardware_verified: false` in [the profile](../../profiles/test-sv08-01/profile.json).
The upgraded bed and hotend are owner descriptions; exact heater/sensor parts,
board revisions, and mounting/travel effects remain unknown. The stock profile
is a comparison source only and is not inherited configuration.

The useful completed evidence is:

* Both MCUs have Katapult and the same Klipper application revision
  `f0892d82b0f1c1228454f09eb508eddde2250f4b`; repeated USB upload/readback,
  software bootloader re-entry, and paired `ready` with no outputs passed
  ([mainboard USB evidence](../hardware/test-sv08-01-mainboard-usb.md),
  [toolhead USB evidence](../hardware/test-sv08-01-toolhead-usb.md)). This is
  communication evidence, not output or print evidence.
* `configs/commissioning/test-sv08-01-no-outputs.cfg` plus the sensor include
  passes matching file-output checks. The configured hotend ADC is
  `extra_mcu:PA5` with an 11,500-ohm software pull-up; the bed ADC is `PC5`
  with the upstream 4,700-ohm default. These values came from the preserved
  resolved configuration and are not measured circuit identities.
* Twelve live samples on 2026-09-08 were short-term ambient-plausible
  (hotend 21.31–21.39 C, bed 20.06–20.36 C). After the reported thermistor
  repair, an earlier check showed hotend 29.42–29.44 C and bed 29.40–29.42 C.
  No independent current reference, heated-range check, or sensor-part
  identification exists ([sensor bring-up](../hardware/test-sv08-01-sensor-bringup.md),
  [temperature record](../hardware/test-sv08-01-temperature.md)).
* A private upstream printing candidate retained 30 of 116 resolved sections,
  preserves heater protections, and proposes conservative limits (50 mm/s,
  500 mm/s2, Z 5 mm/s and 50 mm/s2, minimum cruise ratio 0.5). It has
  placeholders and is not ready to install. Vendor pressure calibration,
  homing override, shell hooks, power-loss motion recovery, timelapse and
  optional displays were deliberately omitted pending compatibility evidence
  ([compatibility audit](../vendor-compatibility.md)).
* The new host image has offline/package evidence and physical boot/SSH
  evidence, but printer services are inactive. The host's DRAM, A/B, recovery,
  Wi-Fi, HDMI/touch, camera and cold-boot results remain separate host gates;
  do not treat host reachability as printer readiness.

Therefore the minimum first-print path is: identify and record the physical
inputs, validate the candidate against the exact paired revisions, activate the
reviewed configuration only after host readiness, then perform attended inputs,
outputs, motion/homing, temperature, calibration and print stages in order.
Automatic pressure-based Z calibration remains deferred; initial commissioning
uses a reviewed upstream manual Z-offset procedure.

## Bounded offline slices

These slices can proceed without printer access. They may inspect pinned source,
existing evidence and ignored private substitutions, but must not edit runtime
configuration, use private dumps as committed inputs, run an installer, flash an
MCU, or claim hardware validation.

### P1 — candidate and compatibility closure

Paths: `configs/commissioning/test-sv08-01-no-outputs.cfg`,
`configs/commissioning/test-sv08-01-sensors.cfg`,
`configs/commissioning/test-sv08-01-inputs.cfg`, the private candidate
described by [sensor bring-up](../hardware/test-sv08-01-sensor-bringup.md),
`docs/vendor-compatibility.md`, `configs/mcu/test-sv08-01/katapult-usb-8mhz.config`,
`configs/mcu/test-sv08-01/klipper-usb-8mhz-8k.config`, and pinned upstream
Klipper. The private candidate itself is not an automatic-worker input.

Acceptance: the coordinator supplies workers a sanitized inventory of every
retained section and every omitted vendor feature from the private candidate;
workers do not access that candidate or private captures directly. Bind both
serial placeholders, both MCU revision/hash records and the selected
configuration source revision; confirm no duplicate ADC/heater ownership;
preserve min/max heater limits and shutdown protections; and validate the
supplied inventory against the exact host/MCU revision pair. Record the manual
Z-offset sequence, ordinary print/pause/resume/cancel controls, and service
activation prerequisites. A file-output parse remains offline evidence only.

Reuse: the 30-section inventory, matching paired no-output check, vendor delta,
and existing artifact hashes. Invalidate this slice if either MCU revision,
serial mapping, candidate section inventory, upstream source, or installed
include tree changes.

### P2 — staged commissioning procedure and evidence forms

Paths: this packet, `docs/development/parallel-work.md`, and
`docs/hardware/coordinated-human-tasks.md`; source sequence is
[sensor bring-up](../hardware/test-sv08-01-sensor-bringup.md).

Acceptance: provide one operator record per stage with target identity, power
state, command/observation, timestamp, result, and evidence path. Keep fan,
motor, homing, heater, calibration and print results separate so a passing
communication check cannot satisfy a later stage. Include a stop condition for
unexpected temperature, motion, polarity, direction, endstop, noise, smoke,
loss of communication, or shutdown behavior.

Reuse: existing sanitized observation records and private hashes by reference;
never copy machine serials, credentials, raw captures, or calibration into
tracked docs. Invalidate downstream stage records after wiring, board, sensor,
firmware, host image, or configuration changes.

### P3 — offline control and service readiness checks

Paths: `configs/host-os/systemd/sv08-klipper.service`,
`configs/host-os/systemd/sv08-moonraker.service`, package records,
`tests/test_host_boot.py`, `tests/host_qemu_admission.py`, and the
coordinator-supplied candidate print-control inventory.

Acceptance: show that the selected host and both MCU artifacts are the same
reviewed revision, printer activation refuses a mismatch, and ordinary
Moonraker/Klipper service persistence exposes print, pause, resume, cancel and
shutdown controls without adding vendor shell hooks. Use VM/file-output checks
only; do not claim physical service readiness or a successful print.

Reuse: existing package, paired MCU and QEMU admission evidence. Invalidate on
service-unit, package, source revision, candidate macro, or MCU artifact change.

## Human dispatch mapping

Human work is dispatched only through the existing [coordinated human task
queue](../hardware/coordinated-human-tasks.md). This packet does not duplicate
its H01–H08 procedures. The first-print mapping is:

| Delivery concern | Canonical task | Packet-specific handoff and stage boundary |
| --- | --- | --- |
| Resolve essential board, installed sensor and circuit facts | H01 | Use existing marking evidence; request only unresolved PCB revisions or sensor/heater facts needed for safe configuration. Adequate pin and sensor evidence may proceed without a universal PCB-revision blocker. Keep power-isolated inspection separate from boot capture. |
| Establish capture-ready power and ordinary host/MCU start | H02 | Arm logging before reconnecting power and account for serial back-power. This gates host readiness and the paired MCU check; it does not enable outputs. |
| Read-only probe/filament and ambient reference session | H05 | Use `test-sv08-01-no-outputs.cfg` plus `test-sv08-01-inputs.cfg` and query `gcode_button probe_check` / `filament_check`. Record physical association and polarity; a logical label alone is insufficient. Keep current ambient reference separate from old samples. |
| Staged outputs through first print | H06 | Preserve its separate gates: fans/shutdown → bounded motors → X/Y sensorless and Z probe homing → controlled heat/reference → PID/extrusion → gantry/mesh/manual Z offset → attended first layer and print controls. Do not collapse these into one pass. |

H03/H04 remain separate host-media and console/peripheral coordination work;
H07/H08 remain recovery and release work. They are consumers or parallel gates,
not additional printer commissioning requests. The central queue's canonical
fields are `action`, `preconditions`, `evidence`, `consumers`, and
`invalidation`; this packet adds only the P1–P3 offline handoffs above.

## Ordering, handoff and blockers

P1–P3 can be prepared offline in parallel with H01/H05 scheduling. H01 and H02
establish the physical and host prerequisites; H05 gates H06. H03/H04 host
work, cold-boot/DRAM, HDMI/touch, Wi-Fi, A/B and recovery work may continue
separately and is not a reason to heat or move the printer. Hardware writes
remain separate authorized operations.

Current exact blockers are unresolved sensor/heater identity and independent
temperature reference, plus all H06 output, motion, homing, calibration and
print stages; the new host's printer services are inactive; and the modified
machine cannot certify stock support. PCB revision is an H01 information gap,
not a universal blocker when adequate pin, sensor and safety evidence exists.
The spare eMMC/ST-Link availability and prior readbacks are preservation
evidence, not permission to write or proof of restoration. No private dump,
credential, serial identity or raw capture is required in this tracked packet.
