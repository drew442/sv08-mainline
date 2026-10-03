Independent delivery review completed with outcome **failed** at submitted HEAD `2995232441f4f0d6c95f5784817195238b1521e7`. Status: done; failed delivery, requiring coordinator-directed implementation continuation. No source repair, record update, Git mutation, network connection, hardware operation, credential inspection, package installation, or additional agent was performed.

Reviewer session `01a100d5-f13d-7451-9ad9-b768000eb5a3` is distinct from the author/planner/approver. The supplied `runtime.json` reports full role loaded, GPT-6.1 Sol/high, full access/never. The formal result hashes the complete approved decision and the seven-entry submitted evidence list using sorted-key compact JSON without a trailing newline.

**F1 — High priority: normal boot permissions disable every supported allocation writer.**

`runtime/sv08_data_budget.py:35` requires the allocation root to have mode exactly 0700. Installed Jobs, Store and Staging select `/data/sv08` as that root (`sv08_admin.py:271`, `sv08_state.py:112`, `sv08_staging.py:31`, and History's default parent-root Budget). However, normal boot calls `sv08_boot.prepare_permissions`, which changes `/data/sv08` to **0711** at `runtime/sv08_boot.py:140`. This is the existing application traversal policy, not an unusual or corrupted directory. Store.initialize and Store.locked do not change an existing root back to 0700.

Consequently, history migration/rollover, ordinary queued/running/result/disposition saves, installed uploads, and new state-generation creation/copy fail at allocation admission with “Allocation directory must be private and owned.” A new release's generation copy can fail on its subsequent boot as well. Current maintenance status preflight does not perform this lock validation, so it can advertise available maintenance that apply cannot execute. The supplied shared-root and browser fixtures initialize 0700 roots and never carry their journey through normal boot permission setup; matching staged bytes do not cover this behavior.

Evidence is the unchanged installed source path, including the unconditional boot chmod and exact mode guard; no hardware observation is claimed. This was found after the two auxiliary runs were consumed, so no third experiment was launched. Required continuation: reconcile allocation admission with the actual boot permission contract while preserving application traversal and private owned single-link lock requirements; demonstrate offline history, upload and new-generation paths after normal permission preparation. Constraints 1, 6, 8, 9 and 13 and checks pressure-journey, bounds, browser-staging and regression are materially unmet.

**F2 — High priority: incomplete legacy export restores as empty writable history.**

At `runtime/sv08_export.py:419`, restoration verifies checksum records only for files actually extracted. It does not require every recorded history member, or even jobs.json, to be present. At line 430, Jobs.view treats a directory containing only a single-link ledger.lock as fresh empty legacy history; lines 436–438 publish that directory and report success.

Independent probe 1 produced a valid export containing one legacy receipt, removed only `data/admin-image-jobs/jobs.json`, and retained the original export-manifest inventory/checksums. `restore_history` succeeded with count zero and published a destination containing only ledger.lock. Jobs.load observed zero receipts, and the supported Jobs.submit route then accepted a new ID as queued. This is actual loss of exported receipt identity on a permitted isolated restore route, with the original missing file still listed in the archive's inventory. It does not require destroying a live compatibility fence or bypassing public admission.

Reproduction: `probe1.py` and `restore-completeness/result.json` in `/home/drew/.sv08-history-rollover-tmpfs-20261003/verifier`. Command: `TMPDIR=<verifier-root> SV08_TEST_ROOT=<verifier-root> PYTHONDONTWRITEBYTECODE=1 timeout 30s python3 -B <verifier-root>/probe1.py`. The isolated lease is nullcontext because this new private fixture has no helpers, workers or waiters.

Required continuation: incomplete inventories and missing authoritative legacy manifests must refuse restoration before publication/write admission; cover valid legacy and fenced history, omitted members, retained inventory records, and new/unchanged-old public writers. Constraints 9 and 12, and identity/regression preservation acceptance, fail. The successful supplied fenced round trip does not cover this negative case.

**F3 — High priority: public receipt retry acknowledges an unsettled manifest commit.**

Both duplicate-return branches in `runtime/sv08_admin_jobs.py:224` and line 240 return public receipts without durability recovery. The retained-disposition branch in `runtime/sv08_admin_resolution.py:116` has the same omission. History.completed explicitly settles maintenance completion, but receipt/disposition acknowledgement routes do not use equivalent settling or refuse unresolved durability.

Independent probe 2 injected persistent EIO at `manifest-directory-fsync`, after jobs.json replacement, during an actual public Jobs.submit. Initial submission failed and launched no worker. An identical public retry then returned an ordinary queued receipt while the failure remained configured; a spy on os.fsync recorded **zero fsync calls** during the retry. Thus acknowledgement succeeds without establishing durability of the possibly committed manifest. This does not prove a physical loss occurred; it proves the required durability boundary was not established. A later power loss may revert that directory publication and forget the acknowledged identity. The browser also removes its pending submission once this receipt is observed.

Reproduction: `probe2.py` and `retry-durability/result.json` under the verifier fixture root; same environment and 30-second timeout as probe 1. This covers the supported submit route rather than directly retrying Jobs.save as the supplied fault matrix does.

Required continuation: an identical public acknowledgement after post-replace directory/parent durability failure must settle the authoritative committed view or remain explicitly uncertain/refused, without backend invocation, replay, stale restoration or referenced-object cleanup before settlement. Add public submit and retained-disposition recovery cases. Constraints 2 and 4 and identity/concurrency-crash checks are unmet; maintenance completion alone does not establish them.

**F4 — Medium priority: isolated restore bypasses bounded tar metadata decoding.**

`runtime/sv08_export.py:385` opens the input with ordinary `tarfile.open(..., 'r:')`. Bounds in the loop are applied after TarInfo parsing. Installed Python's `/usr/lib/python3.12/tarfile.py`, TarInfo._proc_pax, reads `fileobj.read(self._block(self.size))` before yielding a member. Oversized PAX/global headers therefore allocate according to the archive's declared metadata size before restore's member size, count, sparse and destination checks. GNU long-name and sparse parsing likewise precede the loop's checks. There is no outer archive/metadata read budget on this path.

The existing verify_stream uses ReadbackReader plus BudgetInfo precisely to bound metadata parsing before allocations. That protection was not retained in the new restore reader. This is source-traced, not an executed large/malicious-archive test; no unbounded fixture was generated. Required continuation: demonstrate bounded pre-decode metadata handling and refusal for oversized/nested PAX and sparse declarations on the actual restore route. Constraints 9 and 12's preservation of bounded archive/readback protections remain unmet.

**Seven-check assessment**

| Check | Assessment at submitted revision |
| --- | --- |
| pressure-journey | Full-128 baseline and shim browser cancel/migrate/rollover/reconnect/once-only cancellation evidence is credible for its fixture. Installed post-boot route fails F1. |
| identity | Validated all-history lookup, complete dispositions, changed-plan refusal and active-only named-worker selection are supported. F2 loses legacy identity through restore; F3 leaves acknowledgement durability unestablished. |
| concurrency-crash | Supplied 22 migration fault boundaries, 75 mutation fault cases and 52 spawned-process exits cover their asserted complete-view/refusal outcomes. Persistent inode and old-waiter evidence is credible. Public acknowledgement recovery fails F3. No physical power-loss conclusion. |
| eligibility | Source and focused evidence support terminal/disposed-unknown eligibility and refusal for unresolved work, without boot/time/service inference or archived replay. No separate eligibility defect identified. |
| bounds | Finite object/byte/count/inode accounting and exact reserve-edge component tests are supported within the documented fixtures. Ext4 zero-floor allocation measurement is distinguished from production-floor admission. Actual post-boot shared allocation fails F1; restore parsing fails F4. |
| browser-staging | Real Chromium used a shim with a separate Controller/Transaction worker; cancel/apply/lost-ack/reconnect, authority cancellation, drafts, corruption and responsiveness are supported at that level. All 35 staged hashes match. The installed storage path is nevertheless blocked by F1. |
| regression | Supplied 301-test and subsequent 13-test compatibility evidence is source-bound. Unchanged policy/pins and A/B shared-history placement are supported. New-generation boot integration and restore negative paths fail F1/F2/F4. |

**All thirteen constraints**

| Constraint | Review disposition |
| --- | --- |
| 1 | Fixture journey supported; installed maintenance/subsequent image admission fails F1. |
| 2 | Global identity/disposition and active-only worker semantics supported; public acknowledgement durability fails F3, restore identity fails F2. |
| 3 | Exact manifest/receipt schemas, complete-reference validation, paired-fence checks and refusal on corrupt/missing committed versioned history supported by source and focused evidence. The fresh legacy exception must not be used as restore acceptance (F2). |
| 4 | Publication/settlement/cleanup and process fault evidence supported for writers; public acknowledgement recovery fails F3. |
| 5 | Approved finite ceilings preserved. Actual encoded/ext4/tmpfs allocation, namespace, read cost and installed-byte delta evidence checked; no complete factory-fit conclusion. |
| 6 | Shared reserve/headroom arithmetic and cooperative contention supported in 0700 fixtures; installed participants fail F1. |
| 7 | All Jobs.load consumers traced; upload raw-phase and archived stage dependencies remain all-history, and writable saves remain active-only. Narrow ownership was reconciled in plan.md. |
| 8 | Strict browser maintenance RPC and fixture journey supported; deployed write path fails F1 and public receipt acknowledgement has F3. No current authentication/service acceptance inferred. |
| 9 | Runtime glob copying and strict hash inventory inspected; shared history remains outside A/B generations, old public fence paths traced. Installed copy/write integration and complete bounded restore fail F1/F2/F4. |
| 10 | Fresh full-role independent review performed; full diff, hashes, JSON, Markdown and indexed pins checked. Material delivery failures prevent acceptance. No requirement waived. |
| 11 | Same-inode pair creation/durability and pre-admitted old waiters supported by source/process barriers, including old submit/disposition repeated acquisitions and current legacy revision revalidation. Exact bare-load/tamper exclusions retained. |
| 12 | Read-only source validation, link-count stability, exact tar relationship and valid isolated fenced round trip supported. Incomplete legacy restoration and unbounded metadata decoding fail F2/F4. |
| 13 | Leaf order, all claimed direct allocator callers, default F/H and result failure behavior inspected. Actual installed root permission incompatibility fails F1. |

**Integrity and evidence boundaries**

The complete recorded-run-base `1f4f74b4bf41ca620a4980e820e59abc1770754c` to HEAD diff has **60** paths, not the packet's 59: 33 additions and 27 modifications. All were accounted for, including coordinator current-goals/claim bookkeeping and evidence files. No deletions, mode changes, gitlink changes or unlisted source additions were found. New files are 100644. Candidate remained clean at initial and final inspections.

The submitted approval equals candidate approval; full scope digest agrees. All 72 unique submitted document/source/proposal/requirement hashes match. All 38 author-source, 21 input and 50 raw evidence-input hashes match. Source-check payload hashes match; all 35 staged inventory entries match current source or exact generated configuration/link text. Independently recomputed source payload counts are 400915 current bytes, 362409 baseline bytes, delta 38506. Frozen compatibility source is identical between the actual run base and the author's bookkeeping base. Eleven changed JSON files parse with duplicate-key rejection; five changed Markdown files have no missing local targets. Diff/cached whitespace checks pass. All indexed submodule commits agree with upstream-lock.json; submodules remain formally uninitialized, with the declared read-only pinned Klipper input exception. Workflow validate reports valid; next is null.

Historical authenticated/service evidence is retained exclusively at `7ae091807a0177639cb0d1ddc9e33f8e70f9ca08`. Current native Chromium is shim transport plus separate real worker; matching rootfs fixtures do not establish current authenticated Cockpit, running installed systemd supervision, printer support or release acceptance. Factory-image fit and physical power loss remain open. Author cumulative generated-write accounting remains unknown, as disclosed. Minor documentation discrepancy: the handoff's tmpfs traced-read timing/peak differs from the committed measurement JSON; this is not used to inflate or fail the finite envelope finding.

**Review resources and smallest continuation**

Two auxiliary probes consumed the two-run allowance. Each completed under its 30-second timeout; cumulative process runtime is conservatively bounded by 60 seconds, with internal scenario timings 0.006524 and 0.057220 seconds (excluding interpreter startup). Fixed fixtures are small: 86510 retained script/result/payload bytes before this report; reported 32768/69632-byte allocations are end samples, not measured process/fixture peaks. Fixed payload lengths and the bounded publication count give conservative review-fixture cumulative generation and allocated-peak bounds below 4 MiB, well below the assigned 256/128 MiB ceilings. No broad tests were rerun to inflate verification. Primary review completed within the 30-minute allowance.

Return F1–F4 to the coordinator for a bounded implementation continuation and fresh source-bound evidence. The smallest missing checks are a post-boot-permissions offline writer journey, incomplete legacy restore refusal, public post-rename durability acknowledgement recovery, and bounded restore metadata refusal. Preserve this candidate, original evidence and both verifier fixtures. No new product/hardware authorization follows from the review, and no additional auxiliary run was attempted after its allowance was consumed.
