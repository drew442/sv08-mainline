# Author handoff: host-image-history-rollover:finite-history

Status: implementation and bounded offline evidence ready for fresh independent
feature_verifier_high review. No self-approval, independent acceptance, commit,
push, deployment, hardware or release claim. All seven checks have concrete author
runs; constraint 10's independent review/publication belongs to the coordinator.
Cumulative generated-data accounting remains unverified (see resources).

Base/current HEAD: f2d6a49ffa61b17279be2c59a32b31d4e8273f3f.
Claimed lineage: history-rollover-implementation-20261003. Effective model/effort:
gpt-6.1-sol/medium in runtime.json, runtime-resume1.json, runtime-resume2.json;
initial runtime session 01a10092-559c-7dc0-9311-3b2d8d820dac. The same preserved
patch continued through both coordinator interruptions. Current approval takes
precedence over recovered planner/fence text. All thirteen constraints were read.

## Delivered behavior

Explicit browser maintenance review/apply/cancel migrates legacy receipts and
rolls over only a complete settled 128-row batch. One authoritative validated
manifest commits immutable hashed active/archive snapshots. Original identities,
plans, boot/queue fields, outcomes and complete unknown disposition evidence are
retained across all-history retries; active-only saves preserve archive references.
Capacity is finite: 128 active, eight archives, 1152 distinct IDs, 64 MiB allocated,
16 batch objects (each <=2752512 bytes), 1 MiB metadata, 64 entries/inodes. Final
capacity refuses new IDs and rollover without offering eviction.

Monotonic migration links the held ledger inode to the exact second alias and
makes it durable before version publication. New lock validation occurs after
flock. Old public entrypoints refuse the pair; pre-admitted old waiters retain
same-inode exclusion and their pre-manifest legacy changes force fresh migration
review. Bare old load still returns [] when jobs.json is absent; direct internal
bypasses and arbitrary privileged metadata destruction remain outside protocol.
Old executable context construction precedes its ledger refusal. New named worker
rejects archived/disposed selection before controller construction, and cannot
consume a separately queued active job.

Object fsync/no-replace/directory durability precedes atomic jobs.json replacement;
manifest directory/parent fsync precedes acknowledgement or launch. Uncertain
publication never restores stale history. Recovery validates and settles current
complete view before reclaiming only unreferenced owned debris. Corruption never
becomes empty history or orphan reconstruction. Shared leaf allocation excludes
history, upload streams/direct staging receives and state generation creation/copy,
with configured F and future H/64-inode headroom. Product defaults remain 768 MiB;
zero-floor budgets are explicit deterministic component fixtures, distinguished
from real default-reserve shared-root/process and browser pressure tests.

Upload raw-phase gates and archived stage dependencies remain all-history. Browser
maintenance uses strict fixed RPC, explicit lost-ack retry, revision binding,
authority-change invalidation and archived pending-ID observation. Drafts survive.
Export inventories read-only source, records exact paired-lock tar relationship
bound to history revision and verifies semantic readback. Bounded library restore
reconstructs the pair only into a new isolated destination under explicit lease;
there is no exposed/live general restore service. Shared data remains outside A/B
generations. No signed policy, boot health, retention, heaters or upstream changes.

The exact format/publication/recovery/compatibility contract is in storage-format.md,
written before enabling writes and completed with canonical encoding/export schema.
execution.md maps seven checks and thirteen constraints to evidence and limits.
Generic integrate_host_os.py and recovery_image.py already copy all runtime *.py;
their existing mechanisms were retained. stage_admin_ui.py now strictly matches
history/budget dependencies before UI staging and includes their hashes.

## Changed owned paths

- docs/features/host-image-history-rollover/execution.md
- docs/features/host-image-history-rollover/storage-format.md
- runtime/sv08_admin.py
- runtime/sv08_admin_history.py
- runtime/sv08_admin_jobs.py
- runtime/sv08_admin_resolution.py
- runtime/sv08_admin_upload.py
- runtime/sv08_data_budget.py
- runtime/sv08_export.py
- runtime/sv08_staging.py
- runtime/sv08_state.py
- scripts/stage_admin_ui.py
- tests/admin_history_browser.mjs
- tests/admin_jobs_fixture.py
- tests/test_admin.py
- tests/test_admin_history.py
- tests/test_admin_history_allocation.py
- tests/test_admin_history_browser_fixture.py
- tests/test_admin_history_compatibility.py
- tests/test_admin_history_faults.py
- tests/test_admin_history_upload.py
- tests/test_admin_history_validation.py
- tests/test_admin_images.py
- tests/test_admin_jobs.py
- tests/test_admin_resolution.py
- tests/test_admin_upload.py
- tests/test_data_budget.py
- tests/test_export.py
- tests/test_export_readback.py
- tests/test_host_boot.py
- tests/test_host_integration.py
- tests/test_host_state.py
- tests/test_stage_admin_ui.py
- tests/test_staged_transaction.py
- tests/test_staging.py
- tests/test_transaction.py
- ui/host/app.js
- ui/host/index.html

The coordinator's .codex/current-goals.md edit is intentional, preserved and
excluded from author paths. No ownership conflict was found. No Git mutation,
source initialization, download, agent spawning or hardware connection occurred.

## Final commands and outcomes

Run from the assigned worktree. Environment for normal final regressions:

```sh
export SV08_TEST_ROOT=/home/drew/.sv08-history-rollover-tmpfs-20261003
export TMPDIR="$SV08_TEST_ROOT"
export XDG_CACHE_HOME="$SV08_TEST_ROOT/cache"
export PYTHONPYCACHEPREFIX="$SV08_TEST_ROOT/cache"
export PYTHONPATH=runtime:tests:scripts
python3 -B -m unittest test_admin_history test_admin_history_faults test_admin_history_validation test_admin_history_upload test_admin_history_compatibility test_admin_history_allocation test_data_budget test_admin_jobs test_admin_resolution test_admin_upload test_admin test_admin_images test_host_state test_staging test_transaction test_staged_transaction test_host_boot test_stage_admin_ui test_host_integration test_recovery_image test_export test_export_readback test_bundle_policy test_rauc_backend test_rauc_service test_service_admission test_update_admission test_host_boot_health
```

final-tests-2.log: **301 passed**, 57.777s against final production code and fixture
default repair. Two subsequently added old-process acquisition/ordering tests were
run in the complete compatibility module: compatibility-final.log **13 passed**,
10.650s. disposition-acquisition-final.log **1 passed**; final-compatibility-staging.log
**26 passed**, 10.680s, includes strict staged hash report. No subsequent product
code changes followed these runs. Subsequent edits are evidence documentation.

Optional-env fix commands (TMPDIR selects assigned safe parent; no new mandatory env):

```sh
env -u SV08_TEST_ROOT TMPDIR=/home/drew/.sv08-history-rollover-tmpfs-20261003 XDG_CACHE_HOME=/home/drew/.sv08-history-rollover-tmpfs-20261003/cache PYTHONPATH=runtime:tests:scripts python3 -B -m unittest test_host_state test_stage_admin_ui test_admin test_data_budget
env -u SV08_TEST_ROOT TMPDIR=/home/drew/.sv08-history-rollover-tmpfs-20261003 XDG_CACHE_HOME=/home/drew/.sv08-history-rollover-tmpfs-20261003/cache python3 -m unittest discover -s tests -p test_data_budget.py
```

no-env-regression.log **42 passed**, 0.141s; no-env-budget.log **2 passed**, 0.008s.
Without an override, fixture_root creates a private root under explicit TMPDIR or
Path.home and registers cleanup. An explicitly assigned root is retained. Product
safe-ancestry/free-space checks still apply on ordinary suitably resourced hosts.
fixture_budget optionally accepts a component root; its deterministic global
fixture use is not presented as real shared-data locking proof.

Actual filesystem/process coverage: allocation module uses Store, Jobs and Staging
at the same private /sv08 root with Budget production defaults; upload stream and
state-copy subprocess barriers hold the actual leaf exclusion. History refuses
busy quickly, then preserves receipts and uploaded artifacts; rollback keeps the
same manifest and ledger inode. Fault tests assert hooks were reached: migration
22 error boundaries, queue/running/result/disposition/rollover 75 cases, spawned
process os._exit(73) at 52 migration/rollover/active boundaries; repeated-failure
repair and orphan non-growth. Current copies: history-faults.json and
history-process-crashes.json. Error/exit injection is offline, not physical power
loss or a guarantee against uncooperative privileged allocators.

Frozen old code is read-only git-show extraction from exact base. Tests cover old
history, submit, disposition and upload admission plus named workers under present
v2, absent, malformed and replaced-valid-list manifests; no mutation or backend
call. Actual spawn barriers cover old admitted waiters through pre-flock validation,
fence-before-manifest legacy writes, complete-v2 refusal, old submit's second ledger,
old disposition's second ledger and an old writer preceding migrator admission.
Disposition's later ledger remains under worker/state/writer exclusion; a supported
migrator cannot insert a fence there. Old-slot/later correctly signed old-runtime
paths ultimately use the same /data/sv08 ledger inode; no policy/boot masking added.

## Native browser and staging recipes

The preserved browser server was launched with production reserve fixture mode:

```sh
SV08_TEST_PRODUCTION_RESERVE=1 python3 -B tests/test_admin_history_browser_fixture.py /home/drew/.sv08-history-rollover-tmpfs-20261003/browser-fixture-final
/usr/bin/node -r /home/drew/sv08-mainline/local/feature-workflow/probes/history-rollover-20261003/implement/browser-websocket.cjs tests/admin_history_browser.mjs /home/drew/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome /home/drew/.sv08-history-rollover-tmpfs-20261003/browser-fixture-final /home/drew/.sv08-history-rollover-tmpfs-20261003/browser-final
```

Use new private fixture/output names for a later independent rerun; script refuses
existing output. Inherit the environment above. Server binds only localhost
127.0.0.1 ephemeral port. Browser runs existing Chromium --no-sandbox with private
profile; node18 uses supplied existing undici WebSocket shim. No product dependency.
Four author fixture server PIDs 2211216/2211425/2212238/2212615 were terminated at
handoff; existing profiles, screenshots, original receipts and logs are preserved.
Do not mount/unmount the coordinator's bind aliases.

browser-final.log/result: full-128 review/cancel/migrate/rollover, authority change,
unsaved draft, lost ack/reload/manual retry, archived local pending-ID recovery,
separately reviewed image.cancel once (`bad` target backend call), originals128
unchanged. Maintenance backend calls empty, state/update journal byte-identical.
Separate worker transaction install barrier: initial reconnect history in **116ms**
before state becomes available; later stage completes. Real tmpfs pressure refuses
768 MiB floor without lowering product checks; peak **776151040 bytes**.
browser-diagnostics-2.log/result proves strict extra-field refusal, stale review,
no ordinary-apply fallthrough and corrupt-history diagnostic/disabled maintenance;
exact original bytes restored after the intentional corruption fixture.

Current browser is Cockpit API shim transport with real controller/transaction
and separate subprocess worker/backend fixtures, authenticated=false, hardware=false.
The browser-driving product modules are unchanged after that run; the later export
restore-parent guard is separately covered by final export tests. Fixture helper
optional-env changes preserve its explicit override behavior. This is not evidence
of a running installed systemd unit or authenticated current Cockpit.

history-staged-inventory.json contains **35** staged payload/hash entries. Current
runtime/UI/worker hashes were compared against these after final tests and match,
including new History/Budget modules. Missing and modified dependency cases refuse
before UI staging. source-checks.json: payload **400915 bytes**, baseline **362409**,
delta **38506**; this counts all runtime Python + host UI + worker unit, not a full
factory/rootfs image. Core/recovery fixture tests exercise existing glob integration;
no image/QEMU/chroot/package/build operation was run.

Historical authenticated/service evidence is reused solely at its recorded source
**7ae091807a0177639cb0d1ddc9e33f8e70f9ca08**, as recorded in resolution record.json:
- host-admin-image-job-resolution-browser-20260915.json: review/disposition;
- host-admin-image-job-resolution-debian-113-20260916.json: orphan service, idle and writer exclusion;
- host-admin-image-jobs-composed-20260918.json: authenticated safe-source journey;
- host-admin-image-jobs-20260912.json: earlier regression/bounds.
Original hashes and reviewer identities remain intact. It is historical unchanged
service/policy evidence, not a current feature authentication run.

## Measurements, resources and preserved failures

history-bounds-ext4.json: encoded23175662, allocated23199744, metadata12288,
entries15,objects9; publication peak23212032 bytes,17entries,10objects;
4096-byte rounding; traced read peak33044078 bytes,0.873529497s.
Actual ext4 free313483264 (< production768MiB). Exact recipe: inherited common
environment, override SV08_TEST_ROOT/TMPDIR to /home/drew/.sv08-history-rollover-20261003,
set SV08_HISTORY_MEASUREMENT_TAG=ext4 and run
`python3 -B -m unittest test_admin_history.HistoryTests.test_final_finite_capacity_and_measurement`.
That fixture explicitly uses zero configured floors while retaining H; allocation
measurements do not prove production reserve admission or complete factory8GB fit.
No ext4 large-image generation occurred. Ext4 cumulative96MiB allowance retained;
one bounded final-capacity fixture measured the above peak, but all cumulative
allocated writes were not instrumented.

history-bounds-tmpfs.json final full run: encoded23175662, allocated23195648,
metadata8192,entries15,objects9; publication peak23207936 bytes,17entries,10objects;
traced read peak33041776 bytes,0.843599s. Browser pressure measured all assigned-root
allocated blocks at **776151040**, below **805306368** (768MiB). This excludes full
process/browser RSS; no whole-process-memory peak was measured. Final fault matrix
peak90112 bytes/3objects/9entries; generated encoded case bytes4613385.

Cumulative generated writes were not fully metered, so compliance with original
1GiB or extended2GiB primary cumulative data and cumulative96MiB ext4 cannot be
certified. Earlier usage uncertainty/possible overrun is retained; extensions do
not reset or relabel it. Current root scratch allocation was ~1.5MiB and temporary
assigned root ~43MiB after pressure cleanup, within current storage ceilings.
Final root filesystem available333467648 and tmpfs available1557700608 bytes.
No new auxiliary diagnostic probe was initiated on resume2; distinct repairs/tests
continued within primary allowance. Prior auxiliary exact elapsed/data usage is
not independently reconstructed here. Prior primary18+35 minutes retained;
resume2 started about07:58:21UTC, completed handoff before its20-minute extension.

All failed logs remain, summarized in results-summary.json:
- regression-1:117 tests,70 errors: private ancestor775 invalid (fixture resource mismatch);
- regression-independent-1:93,1error: prior copy mock free-space lacked H;
- primary-2:79,4errors: wrong export fixture class, save mock signatures and headroom fixture;
- primary-3:87,1failure+2errors: whole-fstat compared atime and fork inherited held lock FD; stable identity stamp/spawn repaired, exact stuck child terminated;
- browser-1: click during prior busy state; disabled busy buttons and explicit driver readiness fixed;
- browser-diagnostics initial assertion assumed unfenced source already migrated; compare unchanged original pair instead;
- final-tests-1:300 tests,**10 missing-source errors**,290 passed. pinned-admission-repair:exactpin **10 passed**; coordinator mounted read-only only klippy and final candidate suite passed. Klipper pin f0892d82b0f1c1228454f09eb508eddde2250f4b; no gitlink/source edits;
- repeated-faults: initial steady-count assertion rejected shrinking uncertain debris; repair asserts non-growth then stable settled set, no stale commit recovery.
Passing primary-4/87, regression-2/148, expanded-1/26, expanded-2/37 and remaining
focused runs are also retained; no failed evidence was erased to make a run pass.

## Source/input integrity and remaining gates

handoff-input-hashes.json contains every author changed path, approved input,
recovered plan, launch/runtime metadata, evidence-log/result hashes and the pinned
Klipper util/reactor bytes. source-checks.json hashes all runtime/UI/worker payload.
Current strict inventory matches. Git diff --check and cached --check pass; all
indexed gitlinks agree with upstream-lock.json. Submodule status remains '-'
(uninitialized), including Klipper; only coordinator's required read-only klippy
mount supplies tests. JSON and local Markdown targets parse/resolve. No staged
Git changes from author. Preserve shared records and historical evidence.

Remaining gates/limits: fresh independent high verifier and coordinator commit/push;
no current authenticated service/systemd run; no hardware/release/physical-power-loss
or full factory image fit; isolated library restore only; cumulative resource use
not fully measured. Those evidence limits are explicit, not waived checks. No
known unresolved functional test failure remains. Coordinator should assess the
resource-accounting uncertainty and independently evaluate all seven checks before
acceptance. Do not interpret this handoff as self-verification.

Final handoff timestamp: 2026-10-03T08:12:43.814198+00:00. foundation-checks.json captures exact final Git read-only commands and exit codes.
