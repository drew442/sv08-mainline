# Independent bounded environment-history repair verification

Outcome: **passed**, software repair only. Candidate `afee93824ec105906dea0bd2b13924fe38af451a`; recorded base `e5057bb900f6d910b340560e68207220b6b9cbb1`. Fresh separate full-role CLI fallback after native thread capacity exhaustion. Requested GPT-6.1 Sol/high, full role; runtime confirmation supplied separately by the coordinator. This session was not author, researcher, approver, integration producer or action reviewer. No concurrent review verdict was used.

## Binding and complete diff

Formal result: `result.json`, validated against `.codex/schemas/verification.schema.json`. Complete decision canonical JSON (sorted keys, comma/colon separators), including proposal/requirement/scope hashes and all six constraints: `f2891916b20c412c32e8031bcd09c032e1471368b4fb7de0be9d8c3886154eef`. Submitted `../env-repair-evidence-list.json` canonical list digest: `275787ede63f83a4159e2eeb88a9566f92792090b40e13a3eef4b1d520f5b259`. Owner access amendment independently read; SHA-256 `7a87f8095cb3946ced96176e213baa20e6f5f94024ae45bcae92012de0e0425a`. All 55 checks in `hash-audit.json` passed.

Entire base-to-candidate diff inspected, including raw modes and file list:

- `runtime/sv08_commissioning_health.py`: sole semantic change removes cross-bank non-counter equality at admission while retaining exact full selected/tool equality.
- `tests/test_commissioning_host.py`: differing old/current dictionaries and counters; actual historical admission/run, failure tests and actual selected-tool Runtime.environment coverage.
- `docs/features/commissioning-host-readiness/software-contract.md`: explicitly corrects the generated admission predicate and explains stale write destination versus preserved originally selected bank.
- `docs/features/commissioning-host-readiness/environment-repair.md`: coordinator evidence summary and limits, read as part of the complete four-file submission.

Three existing paths retain mode 100644; the report is newly added 100644. No deletions, gitlink changes or other paths. Worktree/index are clean and HEAD equals the evidence source_commit. Whitespace/index checks passed; all three local Markdown links resolve. Eight indexed gitlinks match the lock; submodule status indicates uninitialized checkouts, not tested upstream compatibility. AST comparison proves the entire runtime outside `Runtime.environment` is unchanged. Submitted source/document hashes match both working files and candidate Git blobs. Implementer final hashes match the candidate: its `source_revision` is the precommit base, not a claim that base contained the repaired source. Initial selected-suite evidence is explicitly superseded by final strengthened final-suite evidence; final log/source hashes support the current tests.

## Behavior and reproduced improvement

Entry path remains service -> main -> run -> probe -> environment. Admission still checks both CRCs, bank lengths/termination/ASCII/unique keys, both policy dictionaries, unambiguous incremental flags and complete selected/tool equality. Historical non-counter values are successive saved snapshots and need not be synchronized before a write. Approved preservation applies to the pre-write selected dictionary and the originally selected bank, not the stale destination's obsolete values.

One auxiliary experiment, `probe.py`, ran the unchanged candidate selected-tool test on the assigned read-only ARM64 root via existing QEMU. The recorded-base method was separately compiled in memory and called against the identical fixture before each candidate admission. No production source was patched. `focused.log`, `selected-tool.json` and `before-after.json` retain the result.

- Six pairs (1/2, 254/255, 255/0, 0/255, 0/1, 1/0), selected A1/A2/A3: all 18 actual-tool cases passed.
- Each initial differing dictionary was refused by the original exact method with `Tool selection or redundant logical values differ` and accepted by the candidate. These read-only calls invoke no writer. The six A3 post-observations likewise retain differing history, giving 24 discriminating before/after observations.
- The twelve A1/A2 transitions switch selection, preserve the original selected bank byte-for-byte, carry every selected non-counter value, and leave all outside-region bytes exact. The six A3 cases leave the complete file unchanged. Old counters also differ in every case.
- Empty values, leading/trailing spaces, embedded equals, different values and old-only/new-only names survive actual tool selection and write/readback. Binary and all six library/loader hashes match the pinned tool closure; fw_setenv lookup points to fw_printenv.

The source-bound supplied final focused log has 18 passing tests, no skips, 7.882 seconds. The historical dependency fixture uses actual historical GPT inspector, real bank/parser/CRC/environment/probe/run/Store/Diagnostics with synthetic mount/service/device/tool shims and fake time; it does not bypass environment admission. A1/A2 confirm once after five stable seconds; A3 is a zero-write no-op. Extra/missing/trimmed selected output refuses before writes; stale-value copy and original-selected-bank mutation refuse after the one writer and retain truthful failure. GUID/header/array CRC/mount/disk negatives remain. It is software behavior evidence, not installed ownership, services, block semantics or hardware evidence.

## Acceptance and constraints

| Check | Review disposition |
| --- | --- |
| baseline | Changed admission and historical full path covered; both-bank policy eligibility remains, selected preservation unchanged. |
| uncertainty | Entire Diagnostics/run/write, deadline, stable-window and lock code unchanged. Supplied focused failure, interruption, contention, overflow and retention tests pass. Existing record of every status still blocks same-boot retry. |
| overlay | Actual selected tools reproduced; historical dependency/staging code unchanged and source-bound supplied closure/overlay tests pass. No installed artifact is accepted here. |
| theme | All theme/UI/staging sources unchanged versus historical evidence; no repeated browser check. |
| regression | Complete diff/hash/path/lock review and focused reproduction passed. Historical 112 regression evidence remains at its original revision; unchanged relevant source traced, no broad rerun. |
| boots | Pending physical task; neither synthetic/QEMU result nor this verdict proves installed confirmation or persistence. |
| access | Unchanged software/protocol and owner amendment retained. Existing reported installed access progress is not recertified by this review; transition persistence stays pending. |
| sensors | Unchanged and outside this repair; no paired MCU or sensor acceptance inferred. |

All six constraints remain: (1) immutable identity-bound A-only diagnostic applicability, masks/state/history restrictions and selected-only mutation; (2) pinned real tools, reviewed configuration, complete selected preservation and outside-region bytes; (3) compatible lock order, durable uncertainty and no automatic retry; (4) five stable seconds/60-second deadline, bounded diagnostics and no new daemon/storage requirement; (5) exact historical closure, supported branding and retained UI/helper behavior; (6) independent verification/action authority and distinct installed/hardware/release evidence. The owner password amendment changes only operational actor, not authentication/persistence checks. H12 abandonments remain intact.

## Limits, resources and coordinator handoff

Prior failed software/installed evidence and original failure record were only read in sanitized reports and remain untouched. Sanitized env-difference and initial-observation hashes match diagnosis. Full selected/tool agreement with 14 historical non-counter differences supports the diagnosed prewrite refusal; the single initial snapshot alone does not independently prove before/after physical zero writes. No raw bank copies, credentials, private keys, network, hardware, agents, commits, source edits or shared-record changes were used. No failed record was erased, resolved or relabeled successful. No reconciliation mechanism or physical retry is approved by this software verdict.

Auxiliary use: 1/1 run, 2.742 seconds of 60 seconds; no runs remain. Temporary data stayed under assigned `TMPDIR=/home/drew/.sv08-commissioning-tmpfs-20261003/verify-env`, and the test removed its disposable tree. One sparse 0x820000-byte file was reused across all cases; synthetic bank writes total 18*2*65536 bytes and tool writes twelve bank images. Counting the initial logical file length plus these writes gives 11,665,408 bytes before small config/log/report overhead, below 16 MiB. This is a conservative known-fixture bound, not measured aggregate I/O. No broad suite/build was rerun. Primary task remained within eight minutes; exact session wall time is not instrumented.

Coordinator next step: bind this result/runtime receipt into the durable record without rewriting historical acceptance, then handle the separate failure-record reconciliation/exact-operation review and remaining physical installed checks. This result cannot substitute for that action review or establish named hardware/release support.
