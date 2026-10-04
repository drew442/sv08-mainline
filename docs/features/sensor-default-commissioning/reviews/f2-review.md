# PASS WITH CONDITIONS — exact F2 continuation

The submitted F2 correction closes both F1 rejection findings. One bounded corrected passive-input session is justified under the existing authorization and original input-only scope, subject to fresh admission and observed cleanup. This source review does not authorize hardware operation or establish physical sensor/input accuracy. No further physical attempt or F1 execution was observed by this reviewer; their absence is coordinator-reported.

## Exact bindings

- capture-inputs.py: `b3269815bf2022a301eaa5e8fee75cd3fc47e10f0320044279f3cf996ec85407`
- packet.json: `9a90a51a5743a284e1f5a00d930626ed111383874c717526e2c80bf1a647c7c9`
- run-session.py: `a7c91102405784e4affa2ae2ab49b5c6c34cd0f51d381b17ed483740948c8d88`
- stream-session.py: `5df1a97cf2e05bbf80e058c0e136735e959727b328e2ab0c011a6197ca7c2179`
- warmup-checks.json: `960fec408a8a0a7cc61e9eee7785f3aaedfa19beecc348be39fa8fd95ef45f4c`
- configuration_sha256: `48c5dfeda52fc6bff547cff631dafedbb70accb25a01444e579e3782f353de51`

Original target identities, source/power utility hashes and dictionary binding are retained in f2-result.json. Public packet is byte-identical to F1/original; stream-session is unchanged. Inherited preflight/observer hashes still equal F1 review bindings. Unique stage/unit/private evidence names now endf2; collisions refuse. Original review and F1 FAIL are preserved. All three submitted Python files parse with local AST; capture diff changes only request deadline handling, warmup guard and evidence name. Wrapper diff changes names/capture binding, boot-read-only guards and cleanup organization.

## Source-established fixes and synthetic evidence

F1 deadline: request computes min(now+2,caller deadline), recalculates remaining timeout before connect, send and every recv, then checks response completion. Warmup checks time before querying and after request returns, before accepting values. Poll sleep is capped by remaining budget. An expired budget, delayed response, socket error or missing callback refuses. Deadline bounds acceptance; scheduling/cleanup can finish after deadline, without admitting a late sample.

F2 cold refusal: every sensor with measured_min<=measured_max immediately undergoes5..60 current-temperature validation, before all(initialized). An initialized hot sensor can no longer be skipped while another remains at initialization sentinels. A genuinely initialized zero is refused. webhooks must remain ready on each warmup query, and original twelve-sample ready/cold checks remain. Upstream configured limits are unchanged; this fix neither alters protections nor turns ambient sanity into accuracy.

Retained warmup-checks.json reports actual_block=true for four cases: first callback accepted; one hot/one uninitialized, late valid and missing callback rejected with appropriate reasons. Local JSON consistency agrees. No extraction harness or execution transcript accompanies the receipt, so actual extraction/execution is coordinator-produced evidence rather than independently reproduced here. Source inspection independently supports both corrections. No synthetic result is physical evidence. No experiment run by this review.

## Wrapper correction and execution boundary

Initial and final boot mount must contain read-only option; inherited preflight enforces root read-only and masks/inactive config/package/helper. Every path entering the ON try block enters finally: bounded8second remote stop attempt; independent Beelink OFF and separate status; then final-unit, preflight, observer and idle checks, including sameboot/CID/state/masks/bootread-only. POWER/stop/postcheck exceptions are retained in cleanup-errors and prevent a successful result. Primary failure still propagates after cleanup. The grouped final-observation try short-circuits when a preceding check fails; it is an attempt, not a guarantee that every receipt exists on failure. A BLE termination/wait error could also prevent cleanup-result writing after OFF; coordinator retains individual OFF/status and reports missing summary rather than treating its absence as success.

Inherited existing /run/sv08-commissioning-observe-fw.config creation and read-only environment-bank observations are acknowledged diagnostic effects under coordinator's existing authorization. They are not new boot-policy writes, and no raw banks or credentials were read by this reviewer. No change to that helper is proposed. Existing source-only conclusions about normal input MCU configuration/reset behavior apply; no zero-reset or identify-only claim.

## Conditions and exact post-action evidence

1. Coordinator must verify and record effective separate full-role Sol6.1/medium continuation runtime before reliance; handoff confirmation is not independently observable runtime proof here.

2. Execute only these hash-bound files once, with the unchanged packet and inherited bound preflight/observer and exact previously identified target. Fresh package/helper/root+boot-read-only/CID/masks/inactive-config/idle checks, initial PSU OFF, sole ON/statusON, exact distinct MCU by-ids and unused f2 unit/stage/evidence path remain admission gates. No Python optimization; no automatic/manual retry after failure without another bounded review.

3. Preserve105sec RuntimeMaxSec/5sec TimeoutStopSec/control-group/noRestart and120sec outer capture deadline, only info/objects/query and upstream normal input-only MCU configuration/restart behavior. Stream stop on passive button change or >2C intersample change stays diagnostic only; no heater/motion/flash/gcode API or normal printer service activation.

4. On any primary failure execute the wrapper cleanup; independently monitor OFF/status result. Unverified OFF or POWER cleanup error requires prompt coordinator escalation for owner physical intervention, not waiting for the remaining host checks and not repeated ON/MCU queries. Host SSH failure must not prevent Beelink OFF.

5. Final observation commands are attempted after OFF even on primary failure, but grouped postchecks short-circuit on their first failure. If final-unit/preflight/observation fails, missing ports or mount/mask/config evidence stays unknown; coordinator obtains remaining bounded observations where reachable, without another powered MCU capture, and records incomplete cleanup otherwise. Do not report successful baseline until12 valid rows and all required final invariants/closed ports/OFF are evidenced.

6. Keep all original/F1 records and rejected candidates; F1 nonexecution is coordinator-reported here, not measured by this review. One newly reviewed F2 live session only. BLE capture remains bounded ambient context; no contact accuracy, fitting, H05 polarity/accuracy, H06, UI feature or release acceptance.

Required completion observations remain:12 real temperature/button query rows spanningabout55seconds, bounded ready/first-callback stages, no anomaly, stopped unit/cgroup/MainPID0 and closed ports, OFF/statusOFF, same USB-powered host boot/CID/root+bootread-only, masks/inactive normal services/no active config; private evidence config remains inactive. Partial observations/failure receipts stay partial and preserved. BLE advertiser identity/firmware/placement are owner-reported ambient context; no heated/contact calibration claim follows. Unknown physical sensor circuits/models do not block this passive read, but still block stronger commissioning claims.

No unresolved material reasoning uncertainty was identified within the fixed scope; high profile is not required to compensate for missing physical evidence. Changed artifacts, gates or unexplained behavior require coordinator reassessment and high profile if material uncertainty arises. Runtime verification remains coordinator-owned. Only f2-review.md/f2-result.json were written in assigned scratch. No hardware/network/Git, tracked edit, agents, credential/backups/dumps or diagnostics. Local source/diff/hash/AST/JSON bookkeeping only; generated data below8MiB within150second primary allowance.
