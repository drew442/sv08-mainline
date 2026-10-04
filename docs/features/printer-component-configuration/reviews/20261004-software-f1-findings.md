# Independent software verification: failed

Candidate: `cbf793a9003f6122091f0505b090ebf9a6e7a742`; run base: `30a7448c2915e82dd734ac7958eeff16ba290970`.
Assignment: `printer-component-configuration:software`, six offline checks and the applicable approved constraints. Fresh independent full `feature_verifier_high` session, native thread-limit fallback; requested GPT-6.1 Sol/high for durable state, concurrency and generation reasoning. Effective runtime model/effort and launch receipt remain coordinator-owned; this report does not invent a runtime observation. This session did not author, plan, approve or produce the submitted implementation evidence.

Software acceptance fails on three concrete implementation gaps. Installed acceptance remains a separate dependent task; deferred physical input transitions and fine calibration are not software blockers. No candidate, shared record, Git/config/runtime setting, original fixture, upstream source or hardware was changed. No agents, network operation, publication, credentials, private backups or raw dumps were used.

## Material findings

### F1 — stale import bypasses the revision the user actually compared (persistence/browser; high priority)

`runtime/sv08_printer_store.py:154` validates an import and returns the **current** revision without receiving the tab's expected revision or supplying the current comparison draft. `ui/printer/app.js:154` adopts that revision, but compares imported values against its old `saved.draft` at lines 140–151. The next Save therefore passes CAS even though the displayed comparison used stale state.

Reproduced against actual current Store/Budget in a unique private safe-ancestry fixture:

1. Save a valid sensor draft at revision 1, bed `max_temp=105`; tab A retains that state.
2. Tab B saves `max_temp=100`, creating revision 2.
3. Tab A imports its original 105 draft. Import returns `expected_revision=2`; its displayed before/after objects are identical, so the table says “No changes.” The separate notice says the import differs, making the presentation internally inconsistent rather than showing what will be overwritten.
4. Tab A explicitly saves using returned revision 2. It succeeds at revision 3 and overwrites B's 100 with 105. Current/previous candidates are not needed to trigger the defect.

Evidence: `critical-repro.py` and `critical-repro-result.json`. This is real generation-local persistence, not a mocked Store. Ordinary direct stale Save refusal is present; the overlooked import entry point defeats that protection.

Required correction: bind import to the tab's expected revision and reject stale context, or return and render the exact current saved state/revision under lock before permitting a compared replacement. Keep Save CAS, show the actual replaced values, and cover this two-tab import/save case without introducing permission tokens or a replay ledger.

### F2 — a candidate marked complete exceeds pinned Klipper's current contract (validation/generation; medium priority)

`runtime/sv08_printer_catalog.py:229` only compares driver RMS current to the owner-entered motor rating. All full motors are generated as `tmc2209`, but a motor with `run_current=3`, `current_rating_rms=4` passes validation and produces `complete=True` with `run_current: 3`.

Reproduction: use `full_draft()` from the submitted fixtures, change its first motor settings to those two values, then call `generate(catalog, draft, 'full')`. `critical-repro-result.json` records the result. Pinned source `upstream/klipper/klippy/extras/tmc2209.py` selects `tmc2130.TMCCurrentHelper`; `tmc2130.py:119` defines `MAX_CURRENT=2.000`, and lines 127–128 parse `run_current` with `maxval=MAX_CURRENT`. Thus this candidate is outside the selected software parser contract, independently of unknown physical motor/circuit limits. No hardware trial is necessary to establish this defect.

Required correction: retain incomplete draft support, but report a field blocker/refusal for selected-driver values outside the pinned upstream contract before calling output complete. Add the 3 A/4 A case and the valid boundary to focused generation/parser evidence. This correction must not imply 2 A is physically safe for a particular board or motor.

### F3 — documented defaults are largely absent from the requested easy board/component workflow (catalog/browser; medium priority)

The owner request explicitly requires prepopulated documented defaults/common options. The approved proposal adds component type/preset selection and says documented connector defaults should not require users to know raw MCU pins. The implementation supplies four board references, five named curves, finite typed forms and pin dropdowns, but `ui/printer/app.js:130` always creates `settings:{}`. Board selection likewise supplies only an ID. There is no declarative board/component preset data beyond the sensor pull-up/bounds button at lines 105–111; `catalog.kinds` describes field types, not reference component defaults.

Concrete journey: choose the SV08 mainboard, add `motor` named `stepper_x`, and choose the `stepper_x` connector. Microsteps, rotation distance, current, UART address and other source-configured reference settings remain blank; connector selection clears several fields and offers no reference preset. Even a bed sensor starts with neither the documented bed connection nor factory curve selected. A full workflow requires users to type the exact generator section names and populate almost every setting themselves. The browser test exercises one manually populated sensor and a thermal preset; it does not establish board/device preset usefulness for motors, drivers, bed/hotend, fans or inputs.

Required correction: provide source-qualified declarative component/board reference presets and useful device names/options through the forms, with explicit provisional selection where needed. Carry documented defaults and their origins; keep physical identities, motor ratings, measured circuits, polarity uncertainty and calibration unknown. Contributors should be able to extend defaults for existing kinds through catalog data and fixtures. Do not invent safe electrical limits or silently remap assignments on board changes. Reproduce at least the sensor and motor/component default-selection journeys against the owner's requirement. This is existing approved product scope, not a new acceptance gate.

## Six software checks

| Check | Assessment at submitted revision |
| --- | --- |
| catalog | Four exact source references, factory point sets, curve origins, reservation exclusions, partial-inventory warnings and extension fixture are present. Source hashes and 76 selectable signal mappings/sections match primary configuration files. F3 leaves useful component/default selection unmet. Connector drawing hashes match; independent visual label inspection could not be completed with available PDF tools. |
| validation | Typed/bounded data, canonical role+GPIO collision checks, positive numeric values, temperatures, current-versus-motor rating and polarity/circuit separation are present. F2 misses the pinned driver software limit. |
| generation | Unchanged valid sensor/full fixture bytes match current output. Retained file-output logs identify pinned `f0892d8`, both dictionaries with that version, and successful configuration/exits. Sensor positive allowlist/empty input actions and full CoreXY/four-Z protection defaults are intact. Full-with-controls fixture includes the separately owned controls exactly once. F2 invalidates universal software-completeness claims. |
| persistence | Actual Store/Budget, historical pre-Budget Store, private envelope, nonblocking Store-before-feature locks, context/view checks, CAS/review binding, interruption/capacity/schema/corruption and generation-copy/rollback evidence are present. F1 is an untested material integration path. |
| browser | Retained actual Chromium journey and screenshots are source-bound; forms, thermal preset, save/reopen, review/cancel/apply inactive, import/export/restore, keyboard/touch, Stop/disconnect/logout and lost-ack reconciliation are exercised. Cockpit transport/session are shimmed; real Store is used. F1/F3 remain unmet. The host app/upload scripts are omitted by the navigation fixture, so that fixture alone does not establish real host-RPC regression. |
| staging | Reviewed finite payload, one 58-byte host navigation delta, unchanged session bytes/host runtime, fresh/historical dependency closure and before/after restoration guards are supported by two tests plus the coordinator captured-source receipt. All 33 captured public beforeimage hashes match. Payload is 137633+58=137691 bytes. No installed ownership, authentication or deployment is certified. |

## Approved constraints, individually

1. **Provenance/catalog/defaults:** documented references remain distinct from installed/physical facts; exact non-Pro warning and EBB v1.2 are retained. Vendor point sets remain exact; reference pull-ups are not measured identities. Partial capacity inventories are explicit. F3 fails the defaults/component-choice portion. PDF labels are a stated independent-review limitation, not silently certified.
2. **Modes/generation/inactivity:** incomplete drafts and provisional inactive candidates remain supported, and fixed sensor allowlist excludes outputs/macros/raw includes. Full fixture retains Klipper heater/cold-extrusion protections. Helper writes only feature-owned state. F2 violates software-complete generation/validation; live activation remains separate.
3. **Context/concurrency/durability:** boot/registry/view resolve under Store exclusion, then feature lock; review binds draft/catalog/generator/mode/current/context. Existing tests cover stale direct Save/review, killed writer, concurrent CAS, capacity/corrupt/schema faults, actual generation copy/rollback and authority loss. F1 exposes stale-tab import/save replacement not covered by those tests.
4. **Bounds/resources/historical API:** 128 KiB structured data, 64 devices, 512 KiB generated text, 4 MiB including temporary footprint, inode counts, 0600 files/0700 feature directory and existing copy/reserve admission are retained. Current real Budget and historical API evidence use explicit small-fixture reserve parameters; injected capacity failures are not physical disk exhaustion. Factory 8 GB allocation is not expanded or validated. No sensitive values are added to logs/URLs/localStorage.
5. **Cockpit/staging/controls ownership:** separate finite package/helper, identical existing session/bridge declarations, one navigation delta, no daemon/dependencies/upstream edits, additive closure and restoration path are present. Selected 337 loader recipe exercises package/manifest source, not authentication. Separate printer-controls ownership is preserved; recovery/diagnostic staging adds nothing automatically.
6. **Evidence levels/full journey/dependencies:** submitted evidence correctly names offline, pinned file-output, actual disposable generations and shimmed browser levels. The absent baseline workflow versus added forms/storage is observable, but F1/F3 prevent acceptance of the requested complete software journey. Real authenticated installed ARM64 custom-Shell/helper/root-ro/masks/live-config/capacity checks remain exclusively the dependent installed task. H01/H05/H06, H12 exclusions and owner-deferred physical/calibration work are unchanged.

## Evidence binding and full-diff audit

`binding.json` independently recomputes the complete approved decision digest, including every constraint and proposal/requirement/scope hashes, and the submitted evidence-list digest using sorted JSON keys and comma/colon separators. Candidate and canonical approved decisions match. All six evidence entries bind actual HEAD; all submitted document/source hashes and proposal/requirement/scope hashes match.

`evidence-audit.json` records 24 original entries matched against original source revision `2d0b445` and 55 continuation entries matched against `49b5ad8`/retained outputs. Original partial failures/skips remain historical, superseded rather than erased. Author conversation/runtime packet material and the external dictionary artifact were not opened. Dictionary version/reservation facts here are checked from the authorized retained syntax logs, not a physical identity claim. Current public source/document hashes were verified separately against submitted HEAD. Coordinator's 67-byte author estimate is explicitly superseded by the measured 58-byte insertion in the public report.

`full-diff.patch` and `diff-inventory.txt` cover **all** 29 changed paths, including coordinator ADR, software-execution document and every public evidence addition. There are 27 additions and two modifications, all regular mode 100644; no deletions, mode changes or gitlink deltas. The host HTML changes by one navigation line; admin stager changes only the named-package allowance. Diff/check and cached/check pass; indexed gitlinks agree with `upstream-lock.json`. Worktree/index were clean before review and remained unchanged.

## Reproduction, resources and limitations

Primary diagnostic command: `PYTHONDONTWRITEBYTECODE=1 timeout 30 python3 <assigned scratch>/critical-repro.py`. Exit 0; actual Store/Budget stale-import case, invalid-current complete output and original sensor/full byte comparison reproduced in approximately 0.041 seconds. The guarded fixture retained 1598 logical file bytes under a unique 0700 directory in the separately authorized cache review root. Production reserve values were not changed; the disposable fixture uses existing constructor parameters (zero state/staging reserve, 8 MiB copy allowance).

Read-only source/hash/Git audits were bounded primary work. A source-format whitespace false positive was corrected once; both initial and corrected reports remain. No broad test/browser/image suite was rerun. Two bounded PDF rendering commands failed immediately because `pdftoppm` is absent; installed Python also lacks fitz/pypdf/pdfplumber. No packages or alternative environment were installed. Drawing hashes and retained author audit are available, but the independent visual drawing-label check remains uncompleted. Existing source-bound Chromium screenshot was viewed; no new browser/network fixture ran.

Retained scratch before final findings was approximately 916 KiB, chiefly the complete diff. Total including these documents is under 1 MiB, plus the 1598-byte guarded fixture, within the 32 MiB primary allowance. No auxiliary experimental allowance was consumed; critical reproductions belong to the expressly assigned primary review. Exact session wall time/effective runtime are coordinator observations; no unbounded process ran. The 300-second/16 MiB auxiliary allowance was not needed.

Smallest next action: return F1–F3 to the coordinator for bounded implementation and source-bound evidence, then fresh independent verification. Preserve this failed revision and reproductions. Do not install this software on the basis of this review; installation review/actual installed acceptance remain pending and no hardware profile or release is certified.
