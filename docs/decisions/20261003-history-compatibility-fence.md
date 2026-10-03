# Finite history compatibility fence proposal

Status: proposed bounded technical amendment to the existing history-rollover
approval, not new owner requirements or hardware authority. Date: 2026-10-03.

## Gap and candidate

The unchanged list-only Jobs reader returns an empty list for missing jobs.json.
A format marker understood only by new software cannot make that old code refuse.
Existing package staging checks matching sources but does not govern all old-slot
or later correctly signed old helpers. Never claim direct old load() refuses an
absent file. The planner preserved this counterexample.

Proposed minimal gate: use the old public command's existing strict lock-file
validation. When explicit migration begins under the existing persistent ledger
lock, create one durable directory-relative hardlink `history-format-v2.lock` to
that same `ledger.lock` inode. Do not unlink, replace or rotate the lock inode.
The unchanged old Jobs.lock requires st_nlink==1 and therefore refuses public
history/submit/resolution/upload/worker ledger entry after the fence exists.
The private directory stays0700 and files0600, same owner. The new implementation
accepts exactly the two expected names resolving to the same held regular inode,
link count exactly2, and otherwise refuses. Other locks, manifests, snapshots,
receipts and temporaries retain single-link rules. This explicit paired lock is
the only proposed exception to the earlier universal single-link wording.

The fence is shared persistent metadata, not generation state or an image setting.
Old-slot boot and rollback remain possible; old image-job mutation refuses rather
than forgetting history. No new signed metadata, boot-health mask, dependency,
daemon, permission service or boot policy is introduced. Newly installed tools
handle the format, including observations, repairs by separate future authorization
and strict missing/corrupt-history refusal; old tools do not mutate it.

## Exact invariants requiring independent review

- Every supported old public writer must be traced through the fenced ledger lock.
  A bare old load() with no lock still returns []; retain this negative test and
  exclude direct internal save()/load() calls as bypasses of supported admission.
  Do not relabel that counterexample a passing refusal. Existing owner root access
  is not contained; arbitrary deletion/replacement of both guard and history is
  outside the supported protocol.
- Fence creation occurs only during explicit reviewed migration/apply, never
  observation/retry/cancel. Check no active worker and serialize worker then ledger;
  retain required higher-lock ordering. Keep persistent original inode, including
  legacy waiters; never create a second independent exclusion domain.
- Gate creation is a monotonic compatibility transition. Validate alias/link/type/
  permissions/bound names and fsync directory/parent before publishing any archive
  or version2 view. If interrupted after the fence, new code can observe valid
  legacy data and explicitly resume migration; old public commands refuse. Never
  remove the fence after uncertain publication. Include it in bounds/export.
- An old process admitted before the transition cannot be retroactively changed.
  Explicitly test an old process waiting on the original inode: with a normal
  complete manifest publication it subsequently refuses the versioned manifest;
  old workers must acquire the fenced ledger after worker exclusion. Do not claim
  safety against arbitrary privileged deletion in that pre-admitted interval.
  Preserve the old/new complete commit or refusal guarantee for supported crash
  and contention paths; no publication step unlinks the authoritative manifest.
- Missing manifest plus fence or managed objects refuses for new software, never
  fresh-empty reconstruction. Corrupt/unsupported views never license cleanup.
  Missing/damaged fence in version2 refuses for new software. Corruption of both
  compatibility metadata and manifest is not a proof of old-code safety; record
  the boundary explicitly rather than promising root/tamper resistance.
- Test unchanged old supported entrypoints with present, absent, malformed and
  valid-list-replaced manifest while the fence remains. Test old named worker
  contention, startup, failed migration and rollback/update/recovery paths.
  Candidate assembly must include the matching new reader; archival bytes and
  the exact paired inode relationship must survive supported export/restore.
  If existing export/restore cannot retain/reconstruct that relationship through
  reviewed admission, identify and implement the narrow compatibility integration
  or refuse the unsupported restore before enabling writes. Never flatten history.

## Independent source-only feasibility observation

On unchanged Jobs code, creation of the paired private lock retained the same
inode and old history() refused with Invalid image job lock while jobs.json was
absent. Bare load() returned empty, as expected and explicitly retained. This is
not complete delivery, concurrency, restoration or installation proof. The probe
is preserved in ignored history-rollover-20261003/compatibility/fence-probe.json.

## Allocation and unchanged scope

Retain all previous seven acceptance IDs, receipt/identity/disposition promises,
finite ceilings and no-deletion policy. Use the planner's common leaf allocation
lock for history, upload and state-copy participants; preserve configured reserve
floors and bounded future result publication headroom. No ledger exclusion across
service/backend/device waits. This proposal changes only the technical lock schema
and the precise supported-old-entrypoint contract, not rollback availability,
signed policy or owner authority. Separate feature approval must decide whether
these explicit boundaries satisfy the accepted requirements before implementation.
