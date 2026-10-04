# PASS WITH CONDITIONS — 2026-10-04

Exact bounded passive input observation for test-sv08-01 is justified. Unknown installed sensor model/circuit does not itself block reading these retained ADC inputs with the unchanged vendor conversion model and no heater outputs. Readings must be labelled model-dependent baseline observations. No physical fact was found that requires heated calibration before this read. Existing relevant pin provenance and historical paired reads support this limited step; they do not establish circuit identity, accuracy, physical switch polarity or formal H05/H06 acceptance.

## Exact bindings

- target: `test-sv08-01`
- capture_script_sha256: `0482b745e7d30cb206db901078b2de083e3b8393c4aa2641859254ea5173dbb6`
- packet_sha256: `9a90a51a5743a284e1f5a00d930626ed111383874c717526e2c80bf1a647c7c9`
- configuration_sha256: `48c5dfeda52fc6bff547cff631dafedbb70accb25a01444e579e3782f353de51`
- klipper_pin: `f0892d82b0f1c1228454f09eb508eddde2250f4b`
- sovol_pin: `a60644875f8c756d20b3828c9416518b414b5491`
- power_utility_sha256: `512ae106d30cf572f65eb400fd8955a27c2937bf9179f3090cfd2fd933f2acea`
- dictionary_sha256: `86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b`
- prior_host_boot_id: `2e1e3701-e7a3-4999-8fa5-107360d3a8b5`
- device_cid_sha256: `08d24eb0a58bc7288c07020a0432586ea6070b78abdd86b209de362c7b42fe8a`
- mainboard_by_id: `/dev/serial/by-id/usb-Klipper_stm32f103xe_[private-device-id]-if00`
- toolhead_by_id: `/dev/serial/by-id/usb-Klipper_stm32f103xe_[private-device-id]-if00`

Public config hashes are recorded in result.json. Measured local checks: Python AST parses; packet SHA256 agrees; public source hashes agree; packet is exact public concatenation with only the two recorded by-id substitutions; all thermal options equal pinned Sovol sections. No fitting. The handoff calls the utility binding “sha512”; retained receipt and its 64 hex characters establish SHA256, used here.

## Evidence and implications

Documented source: Klipper temperature_sensor.py configures a sensor and bounds, registers status, and creates no heater output. gcode_button.py returns immediately for empty rendered actions. buttons.py/src/buttons.c configure sampled GPIO inputs and acknowledgements; STM32 gpio.c uses GPIO_INPUT, with no pull-up/inversion flags for these packet pins. ADC source sets analog input mode. The only configured pins are PA5 on toolhead, PC5 mainboard, PB6 toolhead, PE9 mainboard. Kinematics is none; no actuator sections/includes/macros. Loading heaters/gcode_macro modules alone does not instantiate a configured heater or nonempty action.

Normal upstream MCU behavior matters: mcu.py MCUConfigHelper sends allocate_oids, ADC/button configuration/init and finalize_config, plus normal synchronization/query traffic. A configured MCU with mismatched CRC can request firmware_restart; klippy.py then sends klippy:firmware_restart and reconnects, with command reset (or config_reset fallback), affecting both connected MCU handlers. Matching existing configuration resends init commands. This is not identify-only or guaranteed reset-free. One script launch is not one transport request or guaranteed one connection. Internal behavior remains bounded by readiness 30 seconds and the enclosing unit; failed automated reset does not authorize manual retry. Accept this normal input-only configuration/reset behavior only within the stated scope; no flash, gcode API or output configuration.

Measured retained evidence: October4 mcu-results binds both exact by-ids to f0892d8, 139 commands, compiler metadata and the same retained dictionary hash. Powered/pre/post evidence and completion show same USB-powered host boot, closed ports, read-only roots/masks and OFF/statusOFF. These are prior observations requiring fresh admission. Firmware strings/dictionary do not attest complete flash or physical clocks/board revisions. September8 measured 12 ready temperature rows over55.054 seconds support ambient plausibility only. Unknown sensor models remain explicit in the profile.

Installed October3 file-output receipt exited0 with87/86-byte output. Its top-level config uses include files, unlike the concatenated packet: locally compared resolved section/option maps are equal. Reuse supports parsing of this resolved configuration, not a claim of identical top-level bytes or live electrical validation. Exact current packet and script hashes separately bind this action.

BLE prior intake is an ambient candidate only; BTH01 identity remains pending. Concurrent existing reader bounded100 seconds may produce timestamped private ambient evidence; neither reference accuracy nor contact/heated calibration follows. No BLE executable was submitted for implementation review here.

## Conditions before reliance/action and final observations

1. Coordinator must verify and record effective separate full-role GPT-6.1 Sol/medium runtime before reliance; this session cannot independently attest its runtime. No authority is granted by this review.

2. Before ON bind uploaded script and packet to these SHA256 values, immutable exact-pin installed package/venv/prebuilt-helper evidence, host identity/boot, root and boot read-only, controller/CID, seven masks/inactive units, no active printer config, no port users and utility hash plus fresh status OFF. Stage only diagnostic files in a new root-owned 0700 /run path; persistent evidence directory /data/sv08/sensor-observation-20261004 must be absent and its parent safe/root-owned. Run Python without -O/PYTHONOPTIMIZE because safety checks use assert.

3. Arm independent coordinator-side cleanup before the sole PSU ON; require separate status ON, two exact distinct by-id character devices and fresh idle check. Do not change USB relay. Use one root transient unit, RuntimeMaxSec=105, TimeoutStopSec=5, KillMode=control-group, --pipe/--wait and separate outer SSH deadline 120 seconds. No Restart policy or manual rerun. Log actual unit properties and start/stop outcomes.

4. Monitor streamed rows and stop the entire unit for unexplained button changes, implausible/rapidly changing temperatures, unexpected heat/motion/output, communication failure or identity mismatch. Script automatically stops on readiness/query failure and cold values outside 5..60 C, but has no transition or rate-of-change stop. Missing BLE/reference or BLE identity blocks comparison claims, not the bounded MCU baseline; preserve raw paired timestamps, do not fit or invent tolerance.

5. On every completion/failure stop whole unit if necessary and establish no serial users; independently issue PSU OFF and separate status OFF via Beelink even if printer SSH fails. Failure to stop/observe ports must not delay OFF. OFF failure/unconfirmed OFF requires coordinator escalation for owner physical intervention, no repeated ON or MCU query. Retain USB host power; OFF is not wiring isolation.

6. Final evidence must show unit/cgroup stopped, serial ports closed, same host boot/identity, root+boot read-only, seven masks/inactive units, no active configuration, private no-output config inactive, OFF/statusOFF and unchanged USB relay. Exactly 12 valid rows spanning about 55 seconds and readiness within 30 seconds are required for successful baseline; partial rows remain failed/incomplete evidence. No H05 polarity/accuracy, H06, heater/motion, UI feature or release acceptance follows.

The exact capture script itself checks root read-only, section names, empty button actions, masks/inactive units, absent active config and idle distinct ttyACM devices. It does not independently check fixed by-id/pin values against a trusted external constant (packet hash is self-declared), installed package/helper, boot read-only/CID, power state, outer unit properties, BLE identity, temperature rate or button changes. Coordinator binding and orchestration are therefore required conditions, not measured script guarantees. Script finally terminates its Klippy child, with kill fallback and partial observation persistence; SIGTERM/hard kill or setup failure can bypass Python finally, so unit cgroup cleanup and independent OFF are essential. Artifacts persist only under private /data directory and must remain inactive. Never reuse an existing directory or activate its config.

No unresolved material reasoning uncertainty requiring the high profile was identified within these fixed bounds. A changed artifact/plan, failed gate or unexpected reset/output requires reassessment; material uncertainty goes to separate high_consequence_reviewer_high, and missing physical evidence is not solved by higher effort. Reviewer runtime model/effort remains unknown here; coordinator must verify its separate fallback session record. This review is an input, not hardware authorization or evidence of execution.

Only review.md and result.json were written in assigned scratch. No hardware/network/Git, tracked edits, credentials/backups/dumps or agents. Local source/hash/AST/config comparisons only; initial `python` lookup failed, `python3` bookkeeping passed. No live tests or auxiliary diagnostic experiment. Generated results remain well below16MiB; primary reads/writes performed within the bounded review, exact cumulative elapsed reading time not instrumented.
