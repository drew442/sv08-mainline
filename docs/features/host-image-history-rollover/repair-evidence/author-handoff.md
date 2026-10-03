# Same-lineage F1–F4 repair handoff

Status: bounded repairs and all seven author evidence checks produced; ready for
fresh independent feature_verifier_high. No author approval/verification, commit,
push, publication, deployment, hardware or release claim. Stop source editing here.
Complete cumulative generated-write measurement remains unavailable, explicitly below.

Workflow session history-rollover-repair-20261003; run c9b18b2fc55c47778a4c30592a9e487f.
Recorded coordinator run base **9905f2b0950be07b6db3f296df8237aa051e0522**. Starting
and current HEAD **7e06df27ad1f2751375c6aa3cddbd73bdcaa364a**, branch
feature/host-image-history-rollover-repair. This differs intentionally from run
base because coordinator bookkeeping preceded assignment; neither was rewritten.
Original failed candidate **2995232441f4f0d6c95f5784817195238b1521e7**, independent
failed result and original execution/evidence remain in Git and unchanged.
Supplied runtime.json confirms continuing CLI01a10092-559c-7dc0-9311-3b2d8d820dac,
full implementer role, GPT-6.1 Sol/medium, never/danger-full-access. No settings changed.

Read AGENTS/agent guide and dated first-findings/first-result; unprefixed requested
first-result.json does not exist, actual20261003-first-result.json was read. Current
approval/all13constraints retained. No new approval inferred, no constraint waived.
Coordinator owns shared records/goals/proposal/plan, Git and later independent review.

## Repairs and concrete outcomes

F1: Budget now admits the actual existing administrator-owned0711 data root plus
private0700 fixtures, while exact0600/owned/single-link allocation.lock and held-name
validation remain. Read-only preflight now validates the root too, preventing false
available maintenance on invalid roots. Actual prepare_permissions chmods run in
tests/browser; os.chown is mocked for unprivileged offline ownership operations.
No boot policy/modes/owner application traversal changed. Production768MiB floor and
H/64inode headroom unchanged. Default-reserve Store generation, direct Staging.receive,
history migration/rollover and real upload/copy/history subprocess contention work
through a common actual0711 root. New test also rejects755/710/777 root modes,644
lock mode and additional allocation lock hardlink. A/B shared history unchanged.

F2: isolated restore mandates jobs.json even for legacy; exact history inventory
names equal extracted files plus the one alias, including duplicate/checksum/pair
and relationship checks. Omitted inventory payloads and missing manifests refuse
before final publication; temporary is cleaned and no destination exposed. Existing
source history directory lacking jobs.json refuses Export.prepare read-only without
repairing locks or publishing archive. Complete legacy/fenced round trips retain
unknown receipts, with old legacy identical retry preserved and unchanged-old fenced
history/submit rejected. Tests remove each jobs/ledger/alias/snapshot payload with
inventory retained, and remove record too: authoritative jobs and v2 refs/pair remain
mandatory. Unreferenced legacy ledger may be omitted if not recorded; jobs.json and
all original rows remain, destination is isolated with no old waiters. No general
restore service, live exclusion replacement or new signed authenticity design added.

F3: Jobs.acknowledged establishes complete committed-view durability under held
ledger exclusion: validation/revision binding, referenced snapshots/manifest/ledger
file fsync, history directory and parent fsync. Identical submit (both ledger
acquisitions), final submit response, retained disposition acknowledgement/inspection
and public Jobs.history call it before success, ahead of current controller/capacity
or service gates. No allocation lock, backend, launch, replay, manifest rewrite or
cleanup occurs there. Publication's separate settlement then bounded debris cleanup
is unchanged. Tests inject actual public post-replace directory/parent errors in
legacy/v2 submit and disposition; persistent recovery refusal retains original data
and namespace, while successful sync returns retained receipt without action.
Second submit acquisition test introduces another supported commit during controller
review and refuses its uncertain duplicate. Changed plans/evidence still refuse.
Native browser retains local pending ID when public observation cannot settle, and
removes it after successful sync. Raw internal load remains observation-only and the
original old bare missing-load counterexample remains truthful; no unsupported bypass
is presented as public durable acknowledgement.

F4: actual restore uses existing ReadbackReader with forward-only streamed tar and
TarInfo metadata-depth hook before PAX/GNU/sparse decoding. Fixed65536 header-chain
allowance +10240 buffer; <=1MiB underlying reads; regular input10240..2^32-1 bytes,
source identity/bytes-read rechecked. Member sizes/sparse/paths/counts and exact
namespace remain enforced. Six malicious fixed cases (PAX, global, nested, GNU name,
GNU link, GNU sparse map) refuse before publication, with observed reads within75776
bytes and <=10240 requests. Valid generated PAX exports still restore. Existing
verify_stream writer-derived header protections are unchanged. No giant malicious
fixture, external archive, package or private backup was opened.

## Owned changed paths

- docs/features/host-image-history-rollover/repair-execution.md
- docs/features/host-image-history-rollover/storage-format.md
- runtime/sv08_admin_history.py
- runtime/sv08_admin_jobs.py
- runtime/sv08_admin_resolution.py
- runtime/sv08_data_budget.py
- runtime/sv08_export.py
- tests/admin_history_browser.mjs
- tests/admin_jobs_fixture.py
- tests/test_admin_history_allocation.py
- tests/test_admin_history_browser_fixture.py
- tests/test_admin_history_repairs.py

Only these assigned code/tests/docs changed. Original execution.md, evidence/*,
review records, boot policy, signed policy, upstream sources and shared goals were
preserved. Generic integration/recovery copying and original strict staging code
already cover new runtime modules and were not redesigned.

## Commands and results

Working directory: assigned feature worktree. Common environment:

```sh
export SV08_TEST_ROOT=/home/drew/.sv08-history-rollover-tmpfs-20261003/repair
export TMPDIR="$SV08_TEST_ROOT"
export XDG_CACHE_HOME="$SV08_TEST_ROOT/cache"
export PYTHONPATH=runtime:tests:scripts
python3 -B -m unittest test_admin_history_repairs test_admin_history test_admin_history_faults test_admin_history_validation test_admin_history_upload test_admin_history_compatibility test_admin_history_allocation test_data_budget test_admin_jobs test_admin_resolution test_admin_upload test_admin test_admin_images test_host_state test_staging test_transaction test_staged_transaction test_host_boot test_stage_admin_ui test_host_integration test_recovery_image test_export test_export_readback test_bundle_policy test_rauc_backend test_rauc_service test_service_admission test_update_admission test_host_boot_health
```

Final regression-final-export.log: **310 passed,46.839s**, after final required export
negative-path fix. Earlier regression-1:308/47.274s and regression-final:309/46.772s
are preserved, before adding second-acquisition/source-export negative coverage.
There were no functional failures in these broader runs.
Focused final command: `python3 -B -m unittest test_admin_history_repairs test_export
test_export_readback test_admin_history.HistoryTests.test_export_relationship_and_isolated_restore
test_admin_history.ExportStabilityTests test_stage_admin_ui`: **49 passed,0.513s**,
export-final.log. Final full suite also includes all these cases.
initial-focused.log:64passed. repairs-1.log:5 tests/5 errors, diagnosed as fixture
uploads directory absent plus four assertions on private disposition outcome instead
of existing public plan-only disposition. repairs-2.log:5passed after repair. Later
final-focused-staging.log:20passed. These failures remain and were not relabeled.
One incidental source-extraction lookup for a GNU sparse label returned substring
not found; preserved in session.jsonl, not used as evidence; no unchanged retry.

Fresh main browser commands, inherited common env:

```sh
SV08_TEST_PRODUCTION_RESERVE=1 python3 -B tests/test_admin_history_browser_fixture.py /home/drew/.sv08-history-rollover-tmpfs-20261003/repair/browser-fixture-final
/usr/bin/node -r /home/drew/sv08-mainline/local/feature-workflow/probes/history-rollover-20261003/implement/browser-websocket.cjs tests/admin_history_browser.mjs /home/drew/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome /home/drew/.sv08-history-rollover-tmpfs-20261003/repair/browser-fixture-final /home/drew/.sv08-history-rollover-tmpfs-20261003/repair/browser-final
```

Browser is existing Chromium --no-sandbox with private profile, Node18 existing
undici shim, localhost-only ephemeral server. Native main journey passed:711 actual
shared mode, original128 retained incl unknown, explicit review/cancel/migrate/full
rollover, lost acknowledgement/reload/manual completion retry, authority change,
unchanged draft, archived pending recovery plus durable-observation failure pending
retention, separately reviewed image.cancel once. Maintenance original state/update
bytes unchanged and backend calls empty; subsequent cancellation backend `bad` once.
Real production reserve no-space pressure refused without lowered guards; measured
allocated peak**731254784 bytes**, worker state-barrier reconnect**114ms**. Later
stage transaction releases barrier and completes with originals intact. Authenticated
false/hardwarefalse; subprocess worker/backend fixtures, not installed systemd proof.

Native diagnostics command is same Node invocation with scratch browser-diagnostics.mjs,
fixture browser-diagnostics-fixture and output browser-diagnostics; same server command
with that new fixture name. Driver is exact copy of preserved first diagnostic driver,
executed again on repaired helper/actual711 root. Extra-field, stale review, maintenance
ordinary-apply fallthrough and corrupt-history diagnostics pass; exact fixture bytes
restored. Both result JSONs/logs copied to scratch and hashed. Initial server fixture
was stopped/replaced before main driver to load its added test fault hook; no failed
browser run is hidden. Server PIDs2230694,2230874,2231146 terminated by author. Browser
profiles/screenshots/source fixtures remain under repair root; old/verifier inputs
remain untouched/read-only. Use new names for independent rerun; never mount/unmount.

## All seven and thirteen constraints

pressure-journey/browser-staging use fresh corrected711 native runs, observer recovery,
strict diagnostics and current strict staged hash inventory. Identity/eligibility use
fresh schema/global uniqueness/historical retry/disposition/active-only worker/upload
raw-phase/dependency checks, new restore/ack negatives and old-public restored fences.
Concurrency-crash reruns22 reached migration hooks,75 save/rollover cases,52 spawned
exit73 cases, repeated failure non-growth, old pre-admitted writer/worker barriers and
submit/disposition repeated acquisition checks plus actual711 allocator exclusion.
Bounds reruns1152 finite ceiling/peak, F/H/inode edges/default reserves, production
browser pressure and new full-history acknowledgement read/heap cost. Regression is
310 final plus source/pin/JSON/Markdown/diff and strict staged artifacts.

repair-execution.md maps constraints1–13 precisely. Constraint10 requires a fresh
independent high verifier and coordinator publication. No acceptance claim is made.
Only the permitted raw internal bypass/external privileged-tamper exclusions remain;
there is no new boot, health or signed-policy fence, limit increase or retention deletion.

## Current source, staging and measured limits

repair-source-checks.json binds every current runtime/UI/worker source byte. Current
payload**405603 bytes**, first2995232 payload400915, repair delta**4688**. All35 staged
inventory entries retained; current runtime/UI/worker entries match their recorded
SHA-256 including final export fix. scripts/stage_admin_ui.py is strict unchanged.
Git diff/cached whitespace checks pass, indexed pins equal upstream-lock.json,
submodules remain formally uninitialized with coordinator's read-only pinned klippy
mount. Klipper pinf0892d82b0f1c1228454f09eb508eddde2250f4b supplies admission tests;
no Git source initialization/download. JSON and new/updated Markdown local links parse.

Final tmpfs finite report (JSON values, distinct from historical prose):
```json
{
  "encoded": 23175662,
  "entries": 15,
  "objects": 9,
  "metadata": 8192,
  "allocated": 23195648,
  "read_peak_bytes": 33043315,
  "read_seconds": 1.0342044619610533,
  "publication_peak_allocated": 23207936,
  "publication_peak_entries": 17,
  "publication_peak_objects": 10,
  "block_bytes": 4096,
  "actual_free_bytes": 1518317568,
  "fixture_floor": 0
}
```

acknowledged-capacity.json: real public Jobs.history1152 receipts, traced peak**57918069**
bytes,**0.713760295s**, unchanged manifest and namespace. Primary assigned measurement
recipe is scratch acknowledged-capacity.log command in session.jsonl: instantiate
HistoryTests setUp/test_final_finite_capacity_and_measurement, call Jobs.history under
tracemalloc/time, assert count1152/no mutations, doCleanups. This extra fsync cost is
reported, not called throughput improvement. Memory is traced Python allocation,
not total process/browser RSS.

Reused ext4 is exclusively original source**2995232441f4f0d6c95f5784817195238b1521e7**:
original evidence/history-bounds-ext4.json steady23199744,publication peak23212032,
metadata12288,15/17namespace entries,9/10objects,4096 rounding; actual free313483264
and explicit deterministic0floor preservingH. Snapshot encoding/names/limits/counting
and publication allocation algorithm remain unchanged; F1 changes root admission,
F3 adds only fsync/read acknowledgements, F2/F4 affect export/isolated decoder. No new
ext4 test was required/run; evidence does not prove production768MiB admission or
complete8GB factory fit. Fresh default711/pressure tests supply corrected admission.

Unchanged authenticated/service history remains at **7ae091807a0177639cb0d1ddc9e33f8e70f9ca08**
in existing resolution record and original browser/debian113/composed20260918 documents,
with original hashes/reviewer identities. Current staged bytes and shim cannot
become current authenticated/service evidence. All first evidence remains untouched.
Fresh source/input/output hashes in hashes.json include original failed candidate
artifacts, current decision/requirements/plans/run/runtime and pinned local modules.

## Resources, remaining gates and coordinator next action

Prior author18+35+~14minutes and first review~22minutes remain historical; prior
cumulative writes UNKNOWN. Repair started supplied runtime about08:38UTC, handoff
completed within30-minute allowance. No auxiliary question probe consumed; assigned
fixes/tests are primary. No agents, external network/packages/downloads, credentials,
private backups, hardware, remote hosts, full images, QEMU/chroot or Git mutations.
Normal boot ownership calls are mocked offline, actual root/application chmod policy
executes unchanged. All fixture/data writes are assigned repair root, logs scratch.

Allocated temporary peak731254784 (<805306368) measured by native driver across repair
root during production-pressure phase; pressure removed immediately. Sequential
finite snapshots peak~23.2MiB; fixed tar negative cases<=1MiB each. Logs far below32MiB.
Cumulative pressure payload has a conservative upper bound731254784 because it is
included in measured total peak and generated only once. Sequential fixture and
Chromium profile churn were not globally metered; complete repair cumulative2GiB
compliance cannot be certified. Unknown historical/current accounting is preserved,
not reset or hidden. No additional ext4 allocation was generated. Full process RSS
peak not measured; fixture allocation and traced acknowledgement heap are explicit.

No known unresolved functional test failure remains. Required coordinator work:
commit/push owned reviewed patch, update shared workflow, and fresh independent high
verification of full recorded-run-base-to-head diff and F1–F4/all7. Remaining limits:
no current authenticated installed service/systemd/hardware/release/factory-fit or
physical-power-loss acceptance; isolated library restore only; incomplete cumulative
resource accounting. Independent review should assess those evidence bounds rather
than assume author acceptance. Stop editing after this handoff.

Handoff timestamp: 2026-10-03T09:02:27.258716+00:00

Final resource end sample: repair fixtures15692KiB, root scratch548KiB (before this small handoff/hash append); both servers stopped. Final author source freeze/handoff completion: 2026-10-03T09:04:22.941388+00:00.
