# FAIL — exact f1 sensor observation action continuation

The first-sample timing diagnosis is supported, but the submitted correction does not meet the exact five-second deadline and can ignore an already initialized sensor outside the cold-sanity bounds while waiting for the other sensor. Do not execute this bound candidate. Both are concrete source defects; no unknown physical sensor model or heated calibration blocks the passive reading, and no high-effort escalation is needed to establish these defects. A corrected byte-bound candidate requires continuation review.

## Bindings and unchanged scope

- capture-inputs.py: `7435ef96f0b6e3a6d262e9fb76797a60d2a60d31e893fbe3037b2458433df100`
- packet.json: `9a90a51a5743a284e1f5a00d930626ed111383874c717526e2c80bf1a647c7c9`
- run-session.py: `44622a7f6b18b64f1874a163f710f6a2833dca0b9c69f86b123bb53bcb009ed8`
- stream-session.py: `5df1a97cf2e05bbf80e058c0e136735e959727b328e2ab0c011a6197ca7c2179`
- configuration_sha256: `48c5dfeda52fc6bff547cff631dafedbb70accb25a01444e579e3782f353de51`

Local SHA256 checks agree with the submitted capture hash. All three Python files parse with AST. Packet bytes equal the original reviewed packet exactly. Capture diff contains only unique evidence directory and the first-callback polling block. Original review/config/source bindings remain applicable; curves, software pullups, configured ADC limits and no-output sections are unchanged. No experiment executed.

## Retained measured failure and cleanup

Original live-inputs.stdout has one ready query at5.341658seconds with both temperatures0.0, measured_min99999999.0/max0.0. Pinned temperature_sensor.py initializes last_temp/min/max to exactly these values; only temperature_callback updates them. This supports pre-callback observation rather than actual zero-degree readings. failure-summary records the cold assertion/late unit-properties failure; streamed unit error is coordinator-recorded, not a sensor measurement. final-unit.stdout shows inactive/dead/MainPID0; cleanup-idle shows no serial users, two enumerated devices and same boot2e1e3701. Separate psu-off-status says OFF. post-failure-observation shows same boot/CID, immutable root+boot and seven masks/inactive units. No valid samples or automatic retry authority result. First-attempt files and original review preserved.

## Acceptance-blocking fixes

F1: Five-second first-callback deadline is checked only when both sensors are not initialized. A request started before the deadline can return initialized values after it and take break without checking the deadline. Socket timeout bounds inactivity, not total request time. Required: Check monotonic deadline before each first-sample query and after its response, before accepting any response; cap I/O to remaining budget. Preserve shutdown/error and cold refusals. Bind and review corrected bytes.

F2: Cold sanity is conditional on all sensors initialized. If hotend has initialized at 80 C while bed retains its sentinels, that observed bad hotend value is ignored. A later in-range hotend plus initialized bed may then pass. This can suppress an actual observed cold-sanity failure during the wait. Required: For each sensor independently, once measured_min_temp<=measured_max_temp, immediately require its current temperature in5..60 on every polling response; wait only for uninitialized sensors. Do not require both initialized to check an initialized sensor.

For example, a first-query response with hotend temperature80/min80/max80 and bed0/min99999999/max0 takes the wait branch, not the cold-failure branch. A subsequent hotend50/bed25 response can break successfully. This is source-derived counterexample reasoning, not a measured device event or a test experiment. Configured upstream limits remain5..305/5..105 and shutdown is still refused, but those limits do not replace the diagnostic5..60 requirement.

## Wrapper assessment and follow-up conditions

run-session.py verifies script and packet hashes, current utility SHA256, initial OFF, prior host boot/CID, fresh package/prebuilt helper/root/masks/config/idle checks, exact distinct MCU enumeration, new0700 /run staging, absent persistent evidence path and an unused unit. Its sole ON is inside cleanup try/finally. Unit command carries105sec/5sec/control-group; stream monitor checks actual noRestart/properties, outer120sec bound, stable passive states and <=2C intersample changes. Those are conservative anomaly stops, not calibration tolerances. No gcode API call or curve change appears. Packet is passed through stdin and hashed remotely by capture.

stream-session finally preserves partial output and stops local SSH; run-session finally stops remote unit/observes closed ports, with PSU OFF/status nested even if host SSH fails. Unit hard deadline protects against lost SSH and interrupted Python finally. Failure in cleanup may skip BLE wait/close and final observation, so bounded remote BLE timeout110seconds remains necessary; reader itself requests100seconds. Normal upstream input config/restart behavior remains as in original review. A sole process launch does not guarantee a sole connection or reset-free behavior.

Inherited observe-host-v3.py creates/reuses /run/sv08-commissioning-observe-fw.config and reads known environment banks for an existing observation; that is an additional write outside the new stage and raw media read in the proposed operation, not performed by this reviewer. Coordinator must account for that inherited observation boundary under prior authority; no review claim that only new-stage writes occur. No credential or raw-media data was read here; only observer source and sanitized receipts.

1. Verify coordinator runtime receipt for this continuation; runtime model/effort is not independently observable here. Existing separate full-role Sol6.1/medium requirement remains.

2. Explicitly enforce fresh root/boot read-only and expected host/profile/controller/CID before ON and after cleanup. observe-host-v3.py records boot_mount but run-session.py does not assert read-only boot. Masks/root/config/package/helper and idle checks are enforced by preflight; recording alone is not enforcement.

3. On every failure, collect final preflight/observation/idle evidence after OFF where host reachable. Current final calls occur after try/finally and are skipped when an exception propagates; do not claim final host invariants from successful cleanup alone.

4. OFF attempt and separate status are nested independently of printer SSH cleanup and are appropriate. If OFF/status fails, coordinator must invoke existing physical-intervention escalation; supplied wrapper only raises, it does not implement that escalation. No repeated ON or MCU query.

5. Preserve all original attempt and review files. One newly reviewed corrected attempt only, no automatic retries or artifact overwrite. Rebind all revised wrapper/capture bytes, inherited preflight/observer and packet.

6. Keep original review scope/conditions: no actuators/gcode/flash/service activation, unchanged curves/pullups/limits, input-only normal upstream config/reset behavior,105sec cgroup unit and120sec outer limit, PSU OFF/USB unchanged,12 valid rows overabout55seconds. BLE identity owner-confirmed per handoff remains owner-reported here; ambient-only and no calibration fitting.

BLE exact-advertiser identity and BTH01Y_v3.1/pvvx THB2 firmware are supplied as owner-confirmed facts in the handoff, not independently measured by this source review. Beside-bed placement provides ambient context, not contact/reference accuracy or heated calibration. This does not change the blockers.

Only f1-review.md/f1-result.json in assigned review scratch were written; original results unchanged. No hardware/network/Git, tracked edits, agents, credential/backups/dumps or experiments. Local bounded reads/hash/AST/diff checks only; generated continuation files below8MiB. This FAIL returns exact fixes to coordinator and grants no operation authority.
