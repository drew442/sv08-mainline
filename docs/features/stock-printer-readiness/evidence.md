# Configured-printer software closure and commissioning handoff

The first report below is historical evidence at PR33 revision
`3f4677f4f9be0d8f8553dce61e706d17bd4cf05e`. Its limitations describe that
revision. The owner-requested follow-up is recorded separately below; historical
results and hashes have not been refreshed or relabelled as current proof.

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


## Owner-requested follow-up — 2026-10-24

The owner selected normal Klipper `SAVE_CONFIG` and its restart, followed by
automatic reconciliation. This supersedes the earlier manual-transcription
limitation. The qualification target is the configured printer, including
supported modifications; parameter contracts require boundary and representative
composition tests, not every combination or a factory-only physical print.

The implementation separates immutable wiring, heater limits and macros from a
registered top-level calibration lane and Klipper's native autosave footer. The
observer validates the pinned reader, complete include closure, actual loaded
configuration and persisted values, then acknowledges that loaded Klipper
instance on the same connection. Setup remains blocked. Reconciliation performs
no publication, restart, heater or motion operation. Normal stopped publication
and restore protections remain. Existing managed configurations need one reviewed
application of the new generated layout before normal native persistence works.
Installation must include the reconciler runtime, service and its Klipper wanted
link; static UI assets alone do not enable it. Host-image integration installs
that link, and the installed checker refuses an incomplete runtime or missing
link. No live deployment is claimed here.

Persisted zero is valid calibration. Factory starting zero and universal
calibration defaults are not measurements. Explicit local values remain available
as user-reported calibration, with origin metadata; they do not become verified
physical measurements. Native values survive unrelated edits and byte-preserving
update generations. Calibration dependencies reject incompatible hardware/source
changes. Unsupported native records, root drift and mismatched loaded settings
remain conflicts, rather than silently opening the printing guard.

Storage version2 retains the known envelope shape. The offline inspection and
exclusive-output migration commands preserve originals; an actual prior reader
can export the new envelope opaquely and refuses unsupported mutation. This is not
transparent downgrade editing or proof of physical rollback qualification.

The component selector again exposes current compatible choices without changing
pinned source assets. Numerical software plausibility bounds cover thermal and
motion/component inputs, with stricter declared limits retained. They reject
obvious mistakes such as a 1200°C bed while allowing a 120°C modification; they are
not component ratings or physical qualification.

Android acceptance targets 412×892 and 412×915 CSS pixels at 2.625 device scale,
with a shorter 412×780 case.1080/2.625=411.43 and2340/2.625=891.43;
2400/2.625=914.29. Partial recognizable component content is a scroll cue.
The navigation harness models MutationObserver. Trusted touch moves test actual
scrolling. The 512×300, DPR2 case is explicitly equivalent responsive reflow,
not a claim to have changed browser page zoom using CSS `zoom`.

Final source-bound validation and disposable installed acceptance are recorded
below. Publication is recorded in the existing task record and review PR. Full physical commissioning and the
separate ARM64/KVM recovery qualification remain pending tasks. No printer was
accessed or operated for this follow-up.


### Follow-up acceptance and source binding

| Check | Executed result |
| --- | --- |
| Native reconciliation and configured calibration | Final affected modules55/55 pass,0skips,45.913s; then restore-CAS3/3 pass,1.836s. Actual pinned Klipper SAVE_CONFIG across same-PID restarts and the actual archived previous reader are included, rather than mocked compatibility claims.26 final native source hashes match the release candidate. |
| Package/staging |13/13 stage/restore tests pass,41.438s, after adding the reconciler unit to the project file inventory;18/18 project-license tests pass,0.361s. |
| Finite read/ownership |4/4 installed-contract tests pass as actual root,0.011s. The full runtime/service hash manifest and wanted link are mandatory. |
| Hosted selection reproduced locally |100 discovered/run:93pass and7 exact opt-in skips,39.149s. Those skips require the file-output venv or archived prior reader; they were exercised in the local native runs, not represented as hosted CI passes. Unknown skips still fail. |
| Full composed browser |PASS at`ce9d192777e975b745fd1cef9ab90b61d659f5c6`, full_suite_executed=true,0uncaught exceptions. Actual Store/Budget with a Cockpit transport/session shim; no PAM or physical-hardware claim from this suite. |
| Rendered assessment |Coordinator opened the actual Android entry/parts, responsive footer and native-calibration screenshots. Partial component visibility invites scrolling; trusted touch moves reach components and final controls.512×300 equivalent reflow retains usable controls. |
| Disposable installed fixture |PASS in actual installed Cockpit/PAM/sudo: invalid login refusal, ordinary read, ordinary administrator denial, wrong-password cancellation, real UID0 elevation, factory save/reload and Stop returning to denied mutation.86 installed payload hashes and the observer wanted link checked. Source92d8c1c; synthetic ARM64/QEMU guest, private HTTP loopback; no physical hardware or production TLS claim. |

Representative sanitized screenshots: [Android412×892](images/android-412x892.png)
and [normal calibration tools/pending state](images/calibration-tools.png).
They show synthetic fixture data, not an installed printer.

The final browser run uses the new closed-by-default native acknowledgement
macro. Its first attempt retained an obsolete assertion for the prior guard's
wording; it failed and remains preserved. The corrected check asserts ready=0,
the actual readiness condition and the explicit refusal message, alongside the
existing clear/save/reload, source-value and nonmutation assertions. It does not
remove the printing-block requirement.

Real installed acceptance exposed independent disposable-input defects: the
finite helper grants for synthetic accounts, the missing generation config view,
and insufficient full-copy admission space. The fixture now creates the exact
active-generation view, retains unmodified packaged PAM/sudo, adds only the finite
read helper grants, and provides1.5GiB of data. Its capacity test runs the actual
production Budget calculation:1GiB fails full-save admission and the new capacity
passes with filesystem overhead. Production reserves and admission are unchanged.
The failed attempts and their source/image metadata are retained separately.

Validation source sequence: native checkpoint`6bc9bdc`; service-inventory fix
`ef29d3f`; browser assertion adaptation/full PASS`ce9d192`; disposable generation
view`91d188c`; disposable save capacity`439baeb`; sanitized images`92d8c1c`.
Changes after the full browser PASS are confined to the separate installed
fixture/tests and image evidence. Browser/runtime/UI source is unchanged.

Assigned retained evidence is`/home/drew/.sv08-pr33-followup`:
`native-calibration/{closure-checks,restore-cas-checks}.json`,
`staging-final.log`,`project-license-final.log`,`ci-offline-final.log`,
`browser-final-native-b/result.json`, and installed attempt metadata under
`installed/failed-final-{a,b}`. Original PR33 and all superseded attempts remain
historical evidence; their hashes were not refreshed.

| Retained follow-up artifact | SHA256 |
| --- | --- |
|native-calibration/closure-checks.json|cbfe7a82abb8d806541e084bc2cf168da43801df80f9fcf1654f29735ba96ec6|
|native-calibration/restore-cas-checks.json|47989b15f345c83604abf1c762c36e6745dbf32803b2ed460e30af4eaf30ea6a|
|staging-final.log|5a947c59edec5f9a5f98016080d35ad3a50cede7c89030806593fdbd4c4ae4d3|
|project-license-final.log|3fb1a5798c4df0352b619366ae480d71a73d286b310673cfbed6c59124870f2e|
|ci-offline-final.log|0664caf399b93acf88d0eeb6a8b9523ee38322bd73f1cff9eab269ce144a4183|
|browser-final-native-b/result.json|986112688a03868992c077b14390b2c4fe0ea373e5b200c3ae983e44721f4be5|

The actual work used named implementer/researcher medium assignments, plus a
normal-low integration assignment for the earlier concrete fixture diagnosis.
The Android UX worker explicitly read only the repository UX skill and relevant
references. Coordinator ran defined tests, provisioned the assigned disposable
resources and inspected source/rendered evidence. Effective per-turn model/effort
was not independently observed in this delivery; no token-savings or model-quality
measurement is claimed.

Cumulative allowance was expanded once for final disposable admission to8400
process-seconds/10GiB, without resetting prior attempts. Conservative current
charge6500seconds/8.5GiB includes prior delivery, failed attempts, worker700seconds,
boot/browser/test lifetimes, copied root and all reformatted disposable data.
Only one copied root and the reused current data image were needed; no unchanged
OS image was rebuilt, no host tool installed and no printer contacted. No review
PR merge, live deployment or physical printing qualification is authorized here.


Final installed result:`installed/composed-result.json`, SHA256
`187d45f07da816b85e7af83e9d190beff8a234c6406751dd5bee97a9771d271e`.
`installed/final-installed-evidence.json` records30 retained text logs/reports
scanned for the generated synthetic passwords/Basic encodings,0violations; this
is not a guest-journal or arbitrary-file scan. Synthetic credentials and owned
browser profiles were removed. Both fixture servers, all owned browsers and
QEMU are terminal. Guest cleanup confirms workstation identity files and Cockpit
units unchanged and the namespace PID file removed. The actual installed
save/reload screenshot was opened and inspected after the successful run.

Reproduction uses the pinned source/venv described by the existing composed-panel
recipe, not copied workstation paths. From the candidate checkout, assign fresh
private fixture/output/profile paths and run`tests/test_printer_browser_fixture.py`,
then`tests/printer_browser.mjs` with installed Node22/Chromium. For actual installed
acceptance follow [the disposable Cockpit recipe](../../hardware/host-admin-cockpit.md),
stage the composed panel/current runtime in its stopped disposable root, retain
packaged PAM/sudo, and boot in the private network/PID namespace. Run
`tests/cockpit_composed_browser.mjs WORK CHROMIUM hardware` through that namespace.
This mode consumes ephemeral`credentials.json`, a source-generated relative-path
SHA256 map`payload-final.json`, and`source-final.json` with the source revision.
The SHA256 map covers`stage_printer_ui.payload()` plus all runtime modules and
host assets, with`compose_host()` applied to the host index; include the pinned
validation dictionary when installed. Those expected hashes are calculated from
reviewed source before staging, not copied from the installed guest. Their
retained actual values, root/kernel/initrd/data image hashes and input scripts are
in the assigned private evidence directory. Never substitute a provisioned
printer root or owner backup for this synthetic fixture.

Configured-printer physical commissioning remains the existing session/H-queue
task: verify fitted parts and the actual print-start levelling/rehome/nozzle-bed
reference before extrusion, then qualify its first layer and print. This is not
an exhaustive parameter matrix or factory-only printing prerequisite. The
separate ARM64/KVM recovery qualification still awaits its host. No physical test,
image release, PR merge or printer deployment is claimed by these software checks.
