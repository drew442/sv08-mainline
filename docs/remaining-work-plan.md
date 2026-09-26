# Remaining project work

Planning baseline: 2026-09-18. This is an execution order for existing requirements,
not new hardware authorization or a supported-release claim. Detailed acceptance
requirements remain in the [host checklist](hardware/host-os-tasks.md),
[project definition](project.md), and approved feature records.

Execution assignments and shared resource ownership are in the
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

- Host and both MCU firmware candidates are built; Katapult USB updates and paired
  MCU communication have physical evidence. A new bootloader installation is not
  a prerequisite for ordinary updates.
- The diagnostic host has booted physically into Linux, SSH and Cockpit. Repeatable
  cold boot/DRAM behavior and complete physical A/B behavior remain unproven.
- The disposable SD diagnostic has booted its local loader/kernel/initramfs and
  mounted Beelink's read-only NFS root on the printer. It proves this limited
  development path without an eMMC write, not a complete host OS or recovery
  product. Before another eMMC-selected boot, inspect the current redundant
  environment and A counter read-only; the SD diagnostic did not access them.
- Klipper, Moonraker, Mainsail and KlipperScreen packages have offline evidence.
  Full printer services and printing remain uncommissioned.
- A/B transactions, persistent state and operating modes have component/VM
  evidence. They still need final board/service/release composition.
- Interrupted image-job resolution is independently verified offline in its
  [delivery record](features/host-image-job-resolution/record.json). History
  rollover remains separate work.
- Independent recovery diagnostics fit 512 MiB; approved boot-to-export
  composition and offline implementation are complete. Physical UI/media
  validation remains open; restore and production first-boot provisioning are
  separate unfinished requirements.
- Existing factory media, images and MCU backups are accepted by the owner.
  Additional preservation recommendations must not become a new prerequisite for
  proceeding. Recovery demonstrations remain acceptance tests, not demands for
  redundant backups before development.

## Ordered work packages

| Order | Work | Execution | Completion evidence |
| --- | --- | --- | --- |
| 1 | Finish approved independent recovery export composition | Offline ARM64 VM | Installed GTK workflow exports readable data, including damaged-registry cases, using trusted media preparation; source preservation, input methods, failure paths and 512 MiB bounds verified independently |
| 2 | Complete the minimal printing configuration and commissioning package | Offline | Reviewed upstream configuration/includes, pin provenance, conservative limits, explicit homing sequence, manual Z-offset procedure, required print/pause/cancel macros, and matching host/MCU version checks pass configuration validation |
| 3 | Integrate a bounded board commissioning image | Offline, then hardware | Selected loader/kernel/driver packages, persistent state, explicit first-boot setup, access and disabled-by-default printer outputs compose into an identified artifact; normal boot/recovery selection and source-slot state are reviewed |
| 4 | Establish reliable host operation on the printer | Hardware and human | Real cold/warm boots, consistent memory/storage, MCU identities, network, HDMI/touch and basic service readiness pass on the named profile |
| 5 | Commission and print | Attended hardware | Temperature reference, inputs, fans, motor directions, homing, probing, heaters, leveling, mesh, Z offset and representative printing pass in controlled stages |
| 6 | Finish host update and administration integration | Offline plus hardware | A/B health/fallback, idle staging/next-boot activation, opt-out, customization, software/network/access administration and bounded history are usable together |
| 7 | Finish recovery and complete release assembly | Offline plus hardware | Signed restore, preserved-slot boot, missing/corrupt state handling and user-data restore work; full factory-sized artifact and source/license manifests pass |
| 8 | Qualify and document the supported stock release | Hardware, offline and owner | Clean installation, recovery drills, sustained workload/print/update regressions, actual stock profile evidence and release/license decisions complete |

The numbering is priority, not an instruction to wait for unavailable hardware.
After packages 1–3, begin hardware commissioning when available; meanwhile continue
ready offline portions of 6–8. Production convenience features are not a dependency
of first-print testing. Conversely, a successful first print does not complete the
host OS or establish a supported release.

### 1. Independent recovery export

Execute the already approved [export composition proposal](features/host-recovery-export-composition/proposal.md).
Reinspect the independent recovery artifact and its package/module inventory;
prepare trusted media context; establish partition and whole-medium read-only
state before mounting sources with journal replay suppressed; validate the exact
compressed `/usr` chain. Exercise installed GTK touch, keyboard and mouse workflows
with emulated removable media. Cover dirty sources, damaged state, removal/change,
lock contention, corruption, insufficient space and failure cleanup. Record image,
source-preservation and resource measurements, then obtain independent verification.
Do not expand this delivery to restoration or networking.

### 2–5. Critical path to printing

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

### 6. Complete administration and transactional updates

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

### 7–8. Recovery, peripherals and release qualification

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
independent package rebuilds and source/license inventories. Resolve the known
recovery-intake completion-receipt race. Assemble signed boot/root/recovery/data
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
  Start capture before reconnecting it or restoring power.
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
human tasks wait. Revisit estimates after recovery composition and the first
cold-boot/commissioning session; elapsed time for unknown DRAM and sensor behavior
cannot yet be estimated responsibly. Publishing and hardware actions follow their
applicable authorization; this planning update initiates neither.
