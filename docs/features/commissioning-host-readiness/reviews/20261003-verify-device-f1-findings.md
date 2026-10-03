# Stable-device F1 independent software verification

Outcome: **passed for the submitted software repair only**. Candidate `195dce6e0c67fa9beec3de0a45308e54abf4f46b`, run base `0f563c7a5dfefe56f614281ec1c5b0dd18bdc318`. Installed acceptance remains incomplete; exact-operation review is separately pending. No hardware profile, restart, release or printer readiness is certified.

This is the fresh independent full-role feature_verifier_high CLI fallback assigned after native capacity was unavailable. Requested GPT-6.1 Sol/high; effective settings and resumed-runtime confirmation are coordinator-owned receipts. This reviewer is separate from implementation, research/design, approval, earlier software verification and action review. The continuation preserves this same reviewer, evidence and allowance lineage. It did not launch a new agent, change settings or repeat experiments.

## F1 is closed by discriminating execution evidence

The prior failed result/findings were read as failed evidence, not adopted as acceptance. The original retarget case admitted only the original path as a block device: the alternate was a regular file and failed whole-device admission. Its passing broad exception assertion was inadequate. No production source defect was established by that review.

At this candidate, both stat and lstat mappings give the original and alternate valid block metadata. `retarget_valid_device()` copies the current disk bytes, changes the alias target, then positively asserts that `Runtime.devices(manifest)` admits the alternate and returns its resolved path. The fixture retains matching dev_t, canonical controller, newline-inclusive CID, capacity, GPT and mounted partition bindings. Three separate cases assert these specific reasons:

| Case | Required refusal | Writer calls | Persisted outcome and retry |
| --- | --- | --- | --- |
| alias-change | Health/identity/environment changed during stable window | 0 | failed-or-unknown; same-boot retry refused, still 0 writes |
| alias-in-probe | Device identity changed during environment probe | 0 | failed-or-unknown; same-boot retry refused, still 0 writes |
| alias-postwrite | Identity changed after mutation | 1 | failed-or-unknown; same-boot retry refused, still 1 write |

Independent `focused.log` records **17 passing tests, one explicit opt-in selected-tool skip, 10.722 seconds**. The unchanged actual focused suite includes the full historical GPT/dependency fixture and all three new cases. The historical test executes the current fixture in a child with the staged historical dependency closure, checks child success and verifies its completion output. None of the three cases is conditional or skipped. Their positive admission, exact failure reason, write counts, failed records and retry assertions therefore executed successfully.

Own-probe limitation: `run-focused.py` installed a parent-process Python trace. The historical fixture runs in a child, so its trace hits were not captured. The reported `identity-line:382` hits are not coverage evidence for the three retarget branches. No independent branch-coverage measurement, mutation test or additional direct fixture run is claimed. The child test result and inspected discriminating assertions establish the requested behavior. No failed test was hidden, repaired or rerun.

The real historical path also demonstrates unchanged private binding surviving mmcblk0 -> mmcblk1 and 179:0 -> 180:0 renumbering, with A1/A2 single writes and A3 no-op. Wrong CID/controller/partition parent/whole-device/GPT CRC/GUID/mount/capacity and historical-bank/tool mismatch negatives still refuse. Before/after is the retained actual prewrite missing-path failure plus former inadequate retarget fixture and the source-bound passing corrected fixture; no fresh physical before/after run is claimed.

## Complete diff and provenance

Read AGENTS.md, `.codex/README.md`, agent-guide, execution decision, complete approved decision/proposal/owner access amendment, prior failed findings, implementation evidence/runtime/logs, repair evidence/log, software contract and relevant helper/stager/unit entry points. Retained `full-diff.patch`, `full-diff-raw.txt` and `f1-diff.patch` cover the entire base-to-candidate diff and 7df21f8-to-candidate correction. Exactly four files changed: helper, focused tests, software contract and added repair report. All modes are 100644; no deletions, gitlink changes or unlisted files. F1 changes only tests and the repair report. The candidate was clean at initial and final audits, with HEAD matching the submitted evidence commit.

`hash-audit.json` independently matches every submitted document/source hash to both worktree bytes and candidate Git blobs. It also matches proposal, all five requirement hashes, canonical scope, unchanged runtime/stager/unit versus the failed review, all eight indexed gitlinks against the lock, Python syntax and local changed-document links. Base-to-HEAD and cached whitespace checks pass. Workflow validation reports valid with no next selected task. Third-party gitlinks remain pinned and uninitialized here; pin agreement establishes no installed compatibility.

Canonical complete approved decision SHA256: `f2891916b20c412c32e8031bcd09c032e1471368b4fb7de0be9d8c3886154eef`.

Canonical submitted `device-repair-f1-evidence-list.json` SHA256: `21559335f37288e0fee3863a8f88dabc873ba89d508fcc2aab5350d30474a81d`.

Both use sorted keys and comma/colon separators; the decision includes proposal, requirement and scope hashes and all six constraints. Owner amendment hash is `7a87f8095cb3946ced96176e213baa20e6f5f94024ae45bcae92012de0e0425a`. It changes the operational password/login assignment only; actual authenticated administration/persistence requirements and historical approval remain intact. No credential material was read.

Supporting historical evidence limitation: implementer `source_revision` is its precommit base. Its runtime/contract hashes match this candidate, while its former test hash belongs to the prior test source and is superseded by the submitted F1 test hash. Its transcript's recorded hash matches an exact 319113-byte prefix, with 15325 bytes subsequently appended, not the current whole transcript. Other implementation evidence hashes match; the repair log hash matches its receipt. Historical hashes were preserved, not rewritten.

## Independent source and entry-path assessment

The unit still calls main -> run -> probe under the private immutable config requirement and 60-second signal deadline. Schema admits exactly the reviewed by-path alias, canonical controller and raw CID SHA256, with obsolete persistent dev_t/sysfs and arbitrary alias/controller fields rejected. Every device probe freshly resolves the alias, requires whole-block type and no sysfs partition marker, canonical controller ancestry, matching CID/capacity and full six-partition GPT. Root/boot/data partition parents, numbers, offsets, sizes and actual mount device/modes must agree with that current disk. Resolved node, dev_t and sysfs are observed identity returned for comparisons, not persistent config identity.

Probe compares devices before/after environment reads; run compares complete observations through five stable seconds and final revalidation, then boot/state/manifest/device after one writer. Alias resolution precedes O_NOFOLLOW direct reads and fsync. The selected writer still uses the exact hash-bound alias config; no raw writer or retry is added. Removal of the alias-incompatible historical duplicate verifier leaves actual full bank validation in place: both lengths/CRCs, ASCII/double-NUL/duplicate-key parser, both eligible A-only dictionaries, unambiguous redundant flags including wrap, full tool-selected dictionary equality, selected-counter-only readback and preserved older-bank bytes.

Tool/package/version/library/executable lookup and complete dependency hashes remain checked. The unchanged stager invokes the new schema, emits the exact alias map, checks its digest and enforces the historical closure/preimages. A private schema/config/dependency refresh remains necessary for installation; copied-source checks do not establish installed hash agreement.

Store -> boot admission -> writer lock order, nonblocking acquisition, standard tool lock ownership, durable unknown outcome before the only invocation and same-boot refusal are preserved. Diagnostics retain failures without deletion under 64 KiB/boot and 1 MiB history bounds. Seven masks, immutable initial A-only registry, all update/trial/history/backend/RAUC refusals, bounded commands/input/output and no readiness marker remain intact. Additional device/GPT/mount polling is bounded by the existing deadline; offline test timing is not a physical-media timing guarantee. No package, daemon, scheduler, kernel/bootloader change or increased storage requirement was added.

## Acceptance and six constraints

| Acceptance ID | Review disposition at this revision |
| --- | --- |
| baseline | Passing focused A1/A2/A3, identity/config/GPT/mount/state/mask refusals; positive renumbering and corrected valid-block retarget evidence. |
| uncertainty | Passing focused lock contention, deadlines/output/storage bounds, SIGKILL, retained outcome/retry and new pre/during/postwrite comparisons. |
| overlay | Passing historical closure/staging/preimage tests; schema/map integration inspected; unchanged real ARM64 alias tool evidence reused. Installed agreement still pending. |
| theme | Sources/protocol/staging unchanged by this four-file repair; historical independent browser evidence reused, no new browser test. |
| regression | Full diff, candidate/source/decision hashes, pins, syntax/links/whitespace and entire affected focused suite supported. |
| boots | Physical installed acceptance incomplete; normal restart/relay and replenishment require separate exact-action review and observations. |
| access | Owner amendment preserved; actual authenticated access/persistence remains installed evidence, not established here. |
| sensors | Unchanged scope; no MCU/profile/sensor acceptance established here. |

Constraint 1: initial diagnostic A-only admission, protections/history/masks and selected-variable preservation remain enforced. Constraint 2: actual selected tools, hashes and redundant-bank/preservation checks remain; installed agreement is explicitly pending. Constraint 3: compatible locks, mid-window identity tests, durable uncertainty and no retry are exercised. Constraint 4: five seconds/60 seconds, input/command/log/storage limits remain; retained historical staging resource evidence is reused. Constraint 5: exact historical APIs/preimages and branding/protocol scope remain; no broad refresh/feed-timer installation is proposed by this repair. Constraint 6: this is independent high software verification only; coordinator hardware authority, separate exact-operation review, beforeimages/recovery and physical observations remain required. No owner requirement was waived.

## Reused tools, physical limits and accounting

The earlier opt-in log records all 18 tests passing in 7.937 seconds and its selected-tool JSON records 18 actual ARM64 QEMU alias-backed regular-file flag/counter cases. Its evidence hash matches, and the selected-tool class AST is identical between 7df21f8 and this candidate. The helper bytes are also unchanged (`88df3b93b932b1f6e973a8492a21e7067ca0c96fe02815b053d822e1cd38ffc8`). Reuse covers this unchanged method/tool software behavior only; no new ARM64 run was made. The earlier retarget test is expressly not reused as adequate evidence.

Sanitized coordinator read-only candidate probe reports successful devices/environment on the renumbered node, A2/B0, helper_run=false and installed helper hash not exercised until installation. Its code payload equivalence is the supplied coordinator observation; this reviewer did not contact the printer or inspect private bindings/dumps. No installed hash check before the patch, actual helper run, extra restart or physical write is claimed.

Exactly one auxiliary experiment ran: the focused suite against unchanged source, using the explicit 90-second/128 MiB allowance and assigned TMPDIR. Process reported 10.722 seconds and exited 0. Its known historical fixture holds a 32 MiB disk plus 32 MiB alternate; small source/state/retention fixtures accompany it. Exact cumulative generated bytes and peak scratch allocation were not instrumented; RSS is not treated as generated data. No additional diagnostic experiment remains. The earlier review's inadequate 16 MiB allocation and failed own control probe remain historical failures, not silently reset accounting. This assignment explicitly allowed the full fixture.

The outer launcher stopped the initial primary phase at 300 seconds before reports were finished. Coordinator granted the same review 180 seconds/8 MiB retained continuation, with no diagnostics. Existing logs/checks were preserved and no passing checks restarted. Only assigned scratch/TMPDIR was written, no candidate/shared-record edits, network/hardware/credentials/private dump access, Git publication or agents. Final report/schema/hash checks are bookkeeping, not a new experiment. Coordinator owns runtime receipt verification and evidence promotion.

Next action belongs to the coordinator: retain both failed reviews, obtain the separate exact three-file operation review, establish installed artifact/dependency/config hash agreement under that reviewed procedure, and complete the outstanding installed checks. This software verdict grants no authority to perform those actions.
