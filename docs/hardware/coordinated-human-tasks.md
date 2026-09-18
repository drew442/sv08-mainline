# Coordinated human tasks

Dispatch queue created 2026-09-18 for the [parallel assignments](../development/parallel-work.md).
All entries below are pending coordination, not requests to act immediately.
Historical evidence and detailed acceptance remain in the [host tasks](host-os-tasks.md#human-and-powered-printer-tasks),
[recovery tasks](test-sv08-01-recovery-tasks.md) and [sensor bring-up](test-sv08-01-sensor-bringup.md).
Do not interpret old unchecked preservation or v1 imaging tasks as new requests.
The owner has accepted existing backups and USB-reader/ST-Link recovery paths.

Only the coordinator asks the owner to act. Agents submit additional consumers
or prerequisites against an existing H ID before proposing a new physical task.
No current power state, reachability, installed slot or hardware identity is
inferred from a historical report. Inspect current state before acting.

| ID / shared action | Prepare before asking | Consumers and execution order | Evidence reuse / invalidation |
| --- | --- | --- | --- |
| H01 — One accessible, fully unpowered inspection | Consolidated list of unresolved board/sensor facts, existing marking evidence and a safe isolation procedure; no unnecessary heatsink removal | Host PCB/DRAM/radio/PMIC identity; installed bed/hotend sensor and circuit identity; outstanding board revisions | One private evidence set with public nonsecret conclusions; repeat only for changed hardware/wiring or an unresolved essential detail |
| H02 — Capture-ready power isolation and boot session | Start serial logging before any reconnection; account for serial/USB back-power; review intended image/slot/boot environment and safe printer state | True cold-boot/DRAM evidence, warm boot, ordinary MCU start, host health and A/B transitions, baseline HDMI observation | Distinct captures/boot IDs per required trial; repeatability needs multiple boots, not one reused success. Loader/kernel/firmware changes invalidate affected checks |
| H03 — Move spare eMMC to writer and reinstall, only if needed | Establish that remote staging cannot perform the selected operation; identify spare/reader, review complete artifact/hash/layout and readback command; collect all ready changes first | Host commissioning image and recovery composition share one reviewed image when ready; readback and safe eject precede reinstall; arm H02 logging before reconnection | Preserve exact artifact hash/readback evidence. Never request one swap per lane; a materially different artifact or failed write can require another cycle |
| H04 — One physical console and peripheral session | Installed reviewed UI and input tests ready; keep Ethernet recovery; prepare private Wi-Fi configuration and camera test; optional capture/HID setup only if useful | Normal HDMI/touch, recovery touch-only/keyboard-only/mouse paths, Wi-Fi association/reconnect, retained camera presentation/streaming, USB/peripheral observations | Record image, input device, network conditions and path separately. A normal desktop observation does not prove recovery; changed UI/driver/device invalidates affected results |
| H05 — Sensor reference and input session, outputs disabled | Reviewed input-only config, matching host/MCUs, exact queries, independent temperature instrument and known physical associations | Current bed/hotend ambient comparison; probe and filament operation/polarity; resolve sensor identity from H01 before accepting conversion | Record simultaneous references/configuration and input transitions once for printer and host consumers. Old room temperature cannot satisfy a new reference check |
| H06 — Attended staged output and printing session | H05 passes; reviewed limits/homing/stop procedure; operator can stop immediately; safe mechanics and clear workspace | Separate gated steps: fans/shutdown → bounded motor direction → X/Y sensorless and Z probe homing → controlled heat/reference → PID/extrusion → leveling/mesh/manual Z offset → first layer/prints/pause/cancel | Each step has its own result and must pass before dependent action. Reuse host UI/camera observations during safe prints; changes to mechanics/sensors/firmware/config invalidate relevant results |
| H07 — Controlled failure/recovery session | Reliable baseline, reviewed failure plan, expendable data, loads safe, captures and restoration artifacts ready | Power interruption, A/B exhausted/bad trials, watchdog, physical checks consuming recovery delivery's reviewed export/restore artifacts, partial MCU update and USB-reader recovery checks | Group ready cases in one session but preserve individual outcomes and distinct safe states. Deliberate interruption is not bundled into heating/printing; final artifact changes require relevant retests |
| H08 — Release decisions and stock access | Concise unresolved license/omission choices and a stock qualification plan; no re-asking settled OS/backup decisions | Owner license decision, any actual required-feature omission, access to an actual stock profile for supported-stock qualification | Record decisions once; modified test printer first print is independent of stock access, and never certifies stock support |

## Session dispatch and result record

Each request must list: H IDs, exact physical target/action, prerequisites that have
passed, which agent has armed capture, expected observations, stop conditions and
the next ready action while the setup remains connected. Do not ask for a media
move until the reviewed bytes and writing procedure are ready.

For each result record date, target/profile, artifact/configuration/firmware hashes
where relevant, observation/capture reference, passed/failed/inconclusive result,
consuming requirement/check IDs and remaining exclusions. Keep secrets, raw
captures and machine-specific measurements in appropriate ignored local paths;
commit only the safe evidence summary. Each consuming checklist links that same
result instead of requesting another human action.

Recommended setup sequence when required prerequisites are ready: H01 inspection;
H03 writer transfer only if necessary; H02 captured boot; H04 console/peripherals;
H05 inputs; H06 staged commissioning. H07 is a separate controlled session after
baseline acceptance. H08 decisions can happen independently. Availability may
change this order, but never bypass an input, motion or thermal gate.

No entry is marked done merely because its instructions exist. The coordinator
records actual session results here or links a canonical existing evidence record
before closing its consumers. Preparing an offline package remains useful while
any human entry is pending.
