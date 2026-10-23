# Stock-printer software closure and commissioning handoff

## Outcome and remaining boundary

The [current readiness matrix](../../development/stock-printer-readiness.md) traces factory selection, complete generation, managed publication, web startup, physical Klipper activation, installation, calibration and first print against actual source and installed evidence. The [single commissioning session](../../hardware/test-sv08-01-commissioning-session.md) now feeds existing H01/H02/H04/H05/H06, replacing repeated forms without inventing physical results. The human queue links it; older host-checklist checkpoints are explicitly historical.

The audit found actual software defects, not missing fundamental factory generation. This delivery fixes them:

- Bed/probe/hotend/motion and bundled replacements could remove an effective offset and then restore the old definition-instance measurement, leaving printing enabled. Explicit clears now suppress calibration input defaults, while source snapshots and unrelated measurements are preserved. PID clears and remapping use the same rule.
- Calibration/connection editors and generic instance-input controls could disagree with the authoritative input map. Measured edits, clears and ordinary controller identity edits now synchronize both representations. A cleared required identity cannot silently reappear on reload/regeneration; remapping clears prior explicit identity/ack.
- The ordinary stock component selector failed after factory definitions because its legacy profile was absent from pinned assets. Stock selection now uses the existing source-bound native definition path, including watermark before optional PID calibration. Non-native explicit selections pin only their selected compatible profile, preserving mappings/unrelated assets and refusing incompatibility.
- Required input checks no longer count a clear marker or synthesized starting offset as a supplied measurement. Generator version advances to9. Current factory selection tests no longer hardcode obsolete0.2.0; historical snapshots remain unchanged.

Baseline defects were reproduced before closure: probe offset0.25 and printing_enabled=true survived bed selection; untouched baseline legacy component preview raised Unknowncomponentprofile; remapping restored the previous mainboard identity from instance input. All source/fixture attempts are retained in assigned scratch and the superseded branch.

No measured values or hardware identities were guessed. Factory curves and starting offset zero remain sourced defaults, not measured calibration. Full factory generation remains possible before PID/probe calibration; pending probe calibration blocks file printing. Publication remains stopped, source snapshots/drift checks remain, and no diagnostic mask or OS-health guard was removed.

## Measured acceptance

| Check | Actual evidence |
| --- | --- |
| Inventory | Source trace plus separate config and installation researchers; delivered publication/web startup distinguished from intentional diagnostic/production boundaries and target-only qualification. Current named printer is modified, not proof of factory thermals. |
| Native configuration/runtime | 98 tests passed, zero skips,22.925seconds: factory11, definitions21, stack10, publication10, configuration46. Existing pinned Klipper Python3.12.3/parser/dictionaries exercised actual full/setup readiness and guarded printing refusal, including stock replacement without PID gains. |
| Staging/rollback contracts | 13 stage/restore/asset/capacity tests passed after final geometry dependency changes,37.956seconds. Earlier source also passed13; original logs retained. |
| Composed browser outcome | Explicit calibration-only journey PASS at1024×600 with actual Store/Budget and a Cockpit session/RPC shim. Factory selected through UI; connection identity edit/save/reload/regenerate and both editor/generic clears verified, unrelated board preserved. Prepared current/previous candidates remain intact;0.25→0.4 edit persists, clearing persists and generated printing guard returns. Live printer.cfg bytes unchanged, zero uncaught exceptions. |
| Rendered assessment | Coordinator opened actual final screenshots: measured0.4 survives reload, cleared measurement renders blank, inactive review remains explicit. No installed/browser-authentication/hardware acceptance is inferred. |
| New CI regression selection |52 cases discovered;47 runnable offline cases plus five exact named opt-in native-parser skips. Unknown skips, discovery/empty/incomplete runs and failures fail. Those five run locally within the98-test zero-skip result; no CI native-parser pass is invented. |
| Documentation/syntax |146 relative links across handoff/session/queue/checklist resolve after correcting the PR17-only evidence link. JS syntax, workflow YAML/selection/verifier syntax and complete stable diff checks pass. |

The browser driver default still retains all original full-suite assertions. Its first-component-before-fold assertion fails at390×844 on both the changed candidate and an actual untouched-product-code baseline, with identical first-card top892.34375. This predates the calibration repair and blocks the broad journey before calibration. Its assertion was not removed or weakened; the explicit focused mode verifies this task's real interaction and records full_suite_executed=false. The unrelated synthetic navigation VM test also lacks MutationObserver and fails on Node18/22; its unchanged script/navigation inputs establish no new product regression. These failures are preserved, not reported green, and broad/mobile UI acceptance is not claimed.

## Reproduction and retained evidence

Assigned scratch: `/home/drew/.sv08-stock-readiness-20261023`. Use a fresh private fixture/output/profile root; never reuse a browser profile with credentials.

```sh
SV08_PRINTER_SOURCE_ROOT=/home/drew/sv08-mainline SV08_PRINTER_VALIDATION_PYTHON=/home/drew/sv08-mainline/build/printer-interface-prep-20260918/venv/bin/python python3 tests/test_printer_browser_fixture.py "$SCRATCH/fixture-release"
SV08_CALIBRATION_ONLY=1 SV08_BROWSER_PROFILE_ROOT="$SCRATCH/browser-profile-root" "$NODE22" tests/printer_browser.mjs "$CHROME" "$SCRATCH/fixture-release" "$SCRATCH/browser-release"
```

Actual installed Node22.23.2 with native WebSocket and Chrome145.0.7632.6 were used. The pinned parser source/dictionary/root bindings are those documented by the existing complete-configuration fixture recipe. Native checks used explicit SV08_PRINTER_SOURCE_ROOT and SV08_PRINTER_VALIDATION_PYTHON; the new hosted offline selection does not possess that environment and records the five known skips. Temporary HTTP fixture processes were stopped, Chrome exited and its owned profile was deleted. No printer connection was made.

| Retained artifact | SHA256 |
| --- | --- |
| `implementation/geometry-calibration-regressions.log` | `81d40469c748626a3aea022ad310b931eac8b3c84d5977d26d4afae59caa183b` |
| `staging-tests-release.log` | `4250d4811cff219cebb705f629ad0f992671272153ef6c011810d45bf8628ddc` |
| `browser-release/result.json` | `2e0090c08c72c71b6aef0e9b7d8c2eecc853ab5253b02f294290e7ea7cf4334c` |
| `browser-release/calibration-measured-reloaded.png` | `3d98a7853342a7b48f7c6ddf5e8ab0760b04dc1eff2d6042a7e7aa93c367981f` |
| `browser-release/calibration-cleared-reloaded.png` | `36429dcf1f0eea6599f7f97d5971dac2f00a8dbaac73ac543c792d7efa162e7e` |
| `browser-release/calibration-pending-review.png` | `64dffcd3366ce76bb6794f50d389e616a7ae99e136bcdf9eef316a06d5106005` |
| `browser-a-run.log` | `1983bbcd820d52ae13b66c7f356572a8044956b26c2e4cf31223dded4b8b5a62` |
| `browser-baseline-run.log` | `95418f10e18c0d17ec6ab4d1266b6f62051067c0d72e9222e231b5902bb0cc46` |
| `navigation.log` | `c66228d83b153e08f0762b1a3a32ebd94cff52b3060aa288e108e07f5b978d28` |
| `navigation-node22.log` | `c16af14725bd792a169dea9668cc3ec0e04bb483a1eb194400956e916469b65c` |

## Commissioning usability and exclusions

One header and phase-specific config/launch/stop bindings cover fitted-part inspection, host/MCU access, input/ambient checks, fans/stop, motor direction, homing, heating/PID/extrusion, gantry plane, final manual probe measurement and mesh, first layer and print controls, then safe closure. It explains the actual Cockpit path for measured Z offset and heater gains/control. Normal SAVE_CONFIG cannot persist included managed settings; no automatic ingestion is claimed. Fine sensor fitting and proprietary pressure calibration remain deferred.

The exact physical target is not yet confirmed by the optional owner question; the plan deliberately supports stock or an explicitly declared modified target, with confirmation before scheduling. A modified bed/hotend cannot qualify factory heater/sensor behavior. The coordinator must prepare an exact-target reviewed launch and recovery/stop packet before attended outputs. Generic stock printing-image and physical activation qualification remain explicit dependencies, not missing values filled with guessed board clocks, serials or fake deployable/health flags. No further implementable installation defect was demonstrated by the separate installation trace. The ARM64/KVM complete recovery qualification remains a separate blocked lane.

The new explicit calibration-clear marker is valid in the current instance-values envelope and deliberately accepted only for numeric calibration inputs. A baseline old reader explicitly refuses it as nonnumeric instead of silently accepting a measured value. No all-version backward editing or new physical rollback qualification is claimed; saved envelopes/source snapshots are retained.

## Execution and publication

Two fresh named project_researcher children traced independent lanes (config explicitmedium; installation omitted/defaultlow). One named project_implementer explicitmedium handled related cross-component state correctness and tests; a capacity error was retried on the same role/model, with no generic/model fallback. Effective runtime settings/thread IDs were not exposed; self-validation and advisory source feedback are not independent physical operation assessment. Coordinator authored the readiness/session records, executed browser/staging checks and inspected rendered/source evidence.

Exact generator ownership was expanded through committed blocked/resumed/reauthorized records before edits; initial checkpoint80fff10 and failed attempts remain preserved. The primary7200process-second/4GiB allowance is cumulative across research, failures, scope renewal and browser modes. Conservatively charge2400process-seconds including workflow/unmetered reserve and512MiB generated including deleted profiles/fixtures; worker measured native tests22.925seconds, staging final37.956seconds and earlier37.173seconds, research~1.9seconds, remaining commands covered by reserve. No images, host installs, new infrastructure, firmware work, service activation, live deployment, heating, motion or physical test occurred.

Final source-bound submission, actual hosted CI state and review PR are recorded in existing project goal/task records after publication. This is autonomous software closure and a physical handoff, not a working-stock-print or supported release claim.
