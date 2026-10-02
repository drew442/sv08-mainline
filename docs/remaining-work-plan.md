# Remaining project work

**Owner scope change, 2026-10-02:** Keep installed-eMMC reimaging using SD
maintenance, simple target/image checks, full write verification and an attended
yes/no prompt. Abandon RAM maintenance, permission anti-forgery/anti-replay and
secure-randomness work, and complete cold-boot capture. Automatic maintenance
launch and automatic recovery return are deferred until further notice. SD
recovery is sufficient. Point 4 (a separate nonwriting rehearsal) awaits the
owner’s decision after explanation; the old RAM preflight is not a gate.
The [owner-selected scope](decisions/20261002-h12-scope-reduction.md)
supersedes conflicting historical requirements below. Existing source/artifacts
and installed boot settings have not yet been adapted to this simpler route.

Recalibrated: 2026-10-01 at the owner’s request. This is an execution order for existing requirements,
not new hardware authorization or a supported-release claim. Detailed acceptance
requirements remain in the [host checklist](hardware/host-os-tasks.md),
[project definition](project.md), and approved feature records.

The authoritative live order is [G1–G5](../.codex/current-goals.md), with an
[evidence-based assessment](development/goals-reset-20261001.md). Historical
assignments and shared resource ownership are in the
[parallel delivery plan](development/parallel-work.md). Use its
[single human dispatch queue](hardware/coordinated-human-tasks.md) to combine
physical actions across workstreams without duplicating the detailed checklists.

## Milestones and priorities

1. **First working printer:** reliable normal host boot, matching host/MCUs,
   commissioned inputs/outputs, safe homing/calibration and an attended print on
   test-sv08-01. This machine has a modified bed/hotend; its result cannot certify
   untouched stock hardware.
2. **Complete host OS candidate:** usable administration and independent recovery,
   integrated A/B updates and persistent state, required peripherals, and complete
   factory-capacity artifacts.
3. **Supported stock release:** repeatable installation/recovery, actual stock
   commissioning, representative printing and update reliability, licensing and
   release documentation.

Finish approved work and demonstrated defects before adding optional features.
Keep one implementation active. Independently review substantive deliveries under
[the feature workflow](../.codex/README.md). Do not rerun passed component tests
without a change, failure or unresolved integration question that justifies it.

## Current baseline

- **Warm boot capture passed physically on October 1:** continuous USB power and
  logging plus one KVM keyboard reboot captured SPL, DRAM, U-Boot and Linux
  recovery. No external adapter/soldering is needed for that measured route.
- Reviewed warm reboot and U-Boot interception reached the hash-verified SD
  system; authenticated SSH and passive collector restoration passed. Fresh
  intake identifies the same spare, both valid environment records with zero
  A/B counters and the expired job token, and the Linux/RTC time. Read-only p5
  and marker reconciliation subsequently passed: the retained old chain and
  marker match the recorded hashes. Fresh preflight preparation/build passed;
  staging and redundant expired-token retirement passed. A distinct new job
  subsequently passed staging/arm/marker readbacks and entered RAM preflight,
  then refused its claim. Its automatic return halted in SPL DRAM training.
  The startup repair is accepted offline; regain SD control through practical
  recovery and test it physically. Complete cold-boot capture is not a gate; G1 is open.
- First physical urh-04 failed before preflight entry. The selector environment
  correction, preflight executable and runtime MMC binding are independently
  accepted offline; the corrected selector is now physically delivered and reached
  the trusted RAM preflight. Claim refusal and the failed automatic return keep urh-04
  and urh-05 remain open. See [H12 evidence](hardware/host-h12-boot-capture-rethink-20261001.md).
- Recovery export composition, inactive printer-interface configuration and
  boot-health composition are done offline. Do not redispatch their implementations;
  carry their distinct physical and assembled-system acceptance forward.
- Both MCUs have matching firmware and physical USB/no-output communication
  evidence. Printer services, essential sensor verification, outputs and printing
  remain uncommissioned. Test-sv08-01 has modified bed/hotend hardware.
- Signed A/B, persistent state and administration have substantial component/VM
  evidence. Physical A/B/update/fallback, complete administration/recovery/restore,
  required peripherals and final factory-capacity composition remain open.
- No profile is release-qualified. Actual stock evidence and license/release work
  remain separate from getting the modified test printer working.
- Existing factory media, images and MCU recovery material remain accepted by
  the owner. Beelink storage growth is done; additional backups are not a new gate.

## Ordered work packages

| Priority | Goal/work | Immediate execution | Completion evidence |
| --- | --- | --- | --- |
| 1 / G1 | Regain SD control and pass corrected H12 preflight | Exact reviewed warm reboot, prepared serial interception, verified SD script; authenticated read-only reconciliation, fresh signed preparation and corrected selector delivery | Actual urh-04 admission/claim/preflight and required automatic return; current target/environment/RTC/p5 evidence |
| 2 / G2 | Finish writerless delivery and reliable commissioning host | Distinct reviewed/authorized urh-05 write/readback/return; compose accepted host fixes and establish normal host operation | Physical full-image verification/return, persistent access/state, usable administration and reliable enough boot/DRAM behavior for commissioning |
| 3 / G3 | Commission and print on test-sv08-01 | Finish actual configuration substitutions; H01/H05 facts; staged attended H06 | Matching host/MCUs, sensor/reference/input checks, outputs/homing/heat/calibration, first print and print controls |
| 4 / G4 | Complete host product and independent recovery | Integrate accepted work, then bounded required administration/update/restore/peripheral gaps | Factory-capacity complete artifact; physical A/B health/fallback, export/restore, persistent state/identity and required UI/peripherals |
| 5 / G5 | Qualify and document supported stock release | Source/license/rebuild closure plus stock install/recovery/printing/failure tests | Actual stock qualification, representative regressions, documented conversion/recovery and release decision |

G3 starts once its real host/sensor prerequisites pass; G4 administration completion
and G5 stock access are not universal first-print prerequisites. Continue authorized
offline requirements while physical work waits, with one implementation active.
Optional features remain paused. Each new substantive implementation still needs
its bounded approval and independent verification; this plan is not that approval.

### 1. Immediate H12 checkpoint

Owner decision, 2026-10-02: complete initial cold-boot serial capture is a
recorded limitation, not a dependency. Stop capture-specific research and
hardware development. Warm reboot already records early messages; when the host
is halted, use coordinated manual restart or existing SD/media rescue. HDMI,
SSH, later serial output and bounded diagnosis-driven trials can establish the
next action. Cold-start reliability remains a later outcome test without requiring
a complete early trace.

Regain SD access first. Once Linux runs, use the demonstrated warm reboot with a
prepared sole serial controller where U-Boot interception is needed; confirm the
actual stopped prompt before the known SD boot sequence. After authenticated SD
SSH, reconcile spare identity, both redundant environments, Linux/RTC and
read-only p5, preserving beforeimages outside target tmpfs. Then use the accepted
selector and startup repairs and fresh preflight inputs through the existing
distinct stage/arm/boot reviews. Required offline work can proceed while practical
physical recovery waits.

One capture success does not complete urh-04 or authorize urh-05. Never reuse an
expired job or assume an absent marker. The unapproved return-guard proposal is a
contingency outside the active implementation path. A specific interception failure
may justify a bounded correction or simpler physical recovery; it does not by
itself justify another general automation framework. Reuse unchanged offline
checks and decide the next experiment from the last actual result.

### G2–G3. Critical path to printing

Finish the vendor compatibility inventory with explicit outcomes: upstream
configuration, required adaptation, or deliberately deferred behavior. Use upstream
manual Z-offset calibration for initial commissioning; do not assume upstream
load-cell support matches the vendor pressure hardware. Automatic pressure-based
calibration can follow a separately validated electrical/software implementation.
Do not restore vendor shell hooks, homing overrides or power-loss motion resumption
merely to match the old configuration.

Prepare private per-machine settings separately from reusable stock configuration.
The upgraded bed/hotend need their own sensor, geometry and thermal evidence.
Preserve heater protections. Keep host and both MCU revisions matched; refuse
printer activation on mismatch. Complete ordinary print controls and service
persistence in the candidate before attended commissioning.

Inspect the actual installed boot environment before another reboot. Checklist
statements about exhausted A attempts describe prior captures, not current device
state. Correct normal boot-attempt/health handling and verify the intended target
before activation. Resolve inconsistent DRAM initialization through evidence from
true power isolation and repeated boots; do not promote a single 1 GiB detection
or short memory test to reliability.

Use the staged sequence in [sensor bring-up](hardware/test-sv08-01-sensor-bringup.md):

1. Independently check ambient temperature and sensor/circuit identity; exercise
   probe and filament inputs and verify physical association/polarity.
2. Test fans and shutdown behavior, then motor direction with bounded movements.
3. Validate sensorless X/Y homing and probe-based Z homing under observation;
   establish safe travel and the manual Z-offset procedure.
4. Verify controlled heater response and temperature accuracy, then PID and
   extrusion. Complete gantry leveling and mesh with validated motion/probing.
5. Run an attended first-layer test and representative prints; verify pause,
   resume, cancel, shutdown and restart. Expand performance only after baseline
   behavior passes.

Retain output tests as separate controlled actions. Never infer safety from
configuration parsing, plausible ambient readings or successful MCU communication.

### G4. Complete administration and transactional updates

- Connect boot reconciliation, bounded health confirmation, watchdog/fallback and
  board environment handling. Demonstrate A → B → A and exhausted/broken trials
  with state generations preserved. Do not confuse reachability with health.
- Integrate idle admission, configurable automatic staging, next-boot activation,
  opt-out and controlled idle reboot/mode changes. Keep competing application
  update mechanisms disabled for image-managed software.
- Complete additional-software catalog, dependency/space review, admitted APT
  operations and customization reconciliation for immutable/writable modes.
- Complete owner onboarding, persistent account/SSH/TLS identity, network/access
  forms with connectivity rollback, hostname consistency and service controls.
- Deliver separately scoped finite history rollover without losing retry identity
  or silently evicting unknown outcomes at the 128-receipt limit.
- Define and test coordinated host/two-MCU version transitions over Katapult,
  including partial failure and rollback. OS rollback does not roll MCU flash back.
- Run assembled-system races and failure cases: late state writes, job start vs
  update, disk/inode exhaustion, migration failures and customized-slot refusal.

### G4–G5. Recovery, peripherals and release qualification

Complete trusted signed restore, preserved-slot selection and explicit first-boot
state initialization through recovery UI. Missing state must not trigger automatic
repair. Demonstrate restoration of exported configuration/databases/user artifacts,
and diagnostic behavior without network, valid A/B slots or connected MCUs. Add
touch text entry where network/credential workflows require it.

Validate onboard Wi-Fi association/reconnection, visible HDMI and physical touch,
USB stability, thermal/cpufreq and watchdog behavior. Test sustained retained-camera
streaming in UI and during printing. Camera/timelapse may be deferred only with a
recorded path that keeps the existing camera usable.

Finish exact boot-chain/kernel/driver provenance, pinned build inputs, remaining
independent package rebuilds and source/license inventories. The recovery-intake completion-receipt race is now independently corrected
offline; retain fresh downstream assembly for the changed builder. Assemble signed boot/root/recovery/data
artifacts, measuring the complete 7,818,182,656-byte layout, updates, state-copy
workspace, inodes and reserve; preserve the accepted 512 MiB recovery allocation.

Perform attended power-interruption and recovery drills using expendable test data:
failed writes, redundant environment corruption, bad kernels, both slots failed,
watchdog hangs, migration failures, interrupted MCU updates and USB-reader restore.
Measure cold/warm boot and sustained concurrent print/UI/camera/network workloads.
Publish supported behavior only after repeating installation from clean media and
completing a real stock-profile run. Update conversion, Windows/Linux/macOS imaging,
recovery, administration and known-limitations documentation against those results.

## Human dependencies and decisions

Track execution in the existing [host human tasks](hardware/host-os-tasks.md#human-and-powered-printer-tasks)
and [printer recovery tasks](hardware/test-sv08-01-recovery-tasks.md); this plan does
not replace those lists.

- Establish true power isolation: the serial adapter can back-power the host.
  For warm capture keep USB connected and reset in software. For true cold capture,
  establish an independently ready receiver or verified reset/power arrangement;
  waiting for the power-supplying onboard bridge to enumerate can miss early bytes.
- Provide accessible board markings and hotend/bed sensor details, an independent
  temperature reference, and physical observations/input operations for commissioning.
- Attend motion, heating, first prints and power-interruption tests. Move only the
  identified spare eMMC to the writer when the selected operation requires it.
- Provide a suitable Wi-Fi test network and physical HDMI/touch observation;
  HDMI capture/HID assistance is optional when it saves repeated handoffs.
- Select the original project's license before release/external contributions.
  Decide any required vendor-feature omissions before release; initial manual
  calibration does not claim automatic calibration parity.
- Obtain an actual stock machine/profile for stock support qualification. The
  modified test printer can reach working status independently.

## Deferred work

Internet update delivery, additional modified-electronics profiles, optional cloud
integrations, automatic pressure calibration, print power-loss recovery and tuning
beyond reliable baseline printing follow the first-release requirements or an
explicit owner scope decision. Existing authorizations do not permit silently
reclassifying required Wi-Fi, HDMI, preservation or recovery as optional.

## Execution and reporting

For each package, keep a bounded proposal where required, implementation, targeted
validation, evidence and independent delivery review. Distinguish offline,
physical-test and release status. Continue independent authorized work while
human tasks wait. Reassess effort after the G1 SD-return/preflight checkpoint and the first
commissioning session; unresolved physical behavior prevents a reliable delivery
date. Recovery export composition is already accepted offline. Publishing and hardware actions follow their
applicable authorization; this planning update initiates neither.

### G1 checkpoint — 2026-10-01 12:22 UTC

The claim-startup repair passed independent offline verification and is integrated;
see [the delivery record](features/h616-claim-startup-readiness/record.json).
The prepared physical USB reset window expired without a disconnect. Passive
serial capture restoration passed independently. G1 now requires a fresh ready
receiver window and physical reset to regain SD control, current read-only intake,
and a distinct fresh signed preflight job incorporating the accepted repair.
No G1 physical pass or G2–G5 completion is claimed.

### Required G4 receipt correction — 2026-10-01

The [intake receipt delivery](features/recovery-intake-receipt-binding/record.json)
is independently accepted and integrated. Baseline intake verified A but named B
after replacement; the corrected path refuses changed/unreadable lock content and
reports captured bytes after completion comparison. All 23 offline regressions
passed independently. This closes the reporting defect, without certifying a fresh
assembled image, network intake on the installed host or physical recovery.
