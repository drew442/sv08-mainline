# Shared Cockpit panel: repaired offline evidence

2026-10-04. Tested code commit `e7a81479c07f56a4bd06bf24fd12a4e1e63d9844`.
This evidence-only commit leaves that executable tree unchanged.
The original failed delivery and approval interpretation are preserved in
[review-repair.md](review-repair.md). Fresh independent acceptance is required.

## Executed checks

- Ten printer staging and eighteen host staging tests pass, plus Node navigation.
  Separate focused discovery exposed a test import-order assumption; it was fixed
  before this run. No production admission or acceptance check was weakened.
- Actual Chromium passes all prior shared-shell/session/navigation, dirty-draft,
  delayed-response, lost acknowledgment, host isolation and component journeys.
  New cases preserve local drafts for export across unsupported catalog, saved
  schema and draft schema responses. Editing/mutations remain disabled until
  recovery or explicit discard. No uncaught exceptions.
- Screenshots and no-overflow assertions cover 1440×900, 1024×600 and 390×844.
  Cockpit transport is a shim, with real Store/Budget. Installed authentication
  remains a separate check.
- Supported stage/restore/host-refresh calls use nonblocking exclusion on the
  stable root-directory inode. Fresh/historical contention refuses without writes;
  lock coverage spans validation and publication/restoration. Preexisting drift
  refuses without mutation, newly visible drift is preserved, and interruption
  recovery still passes. Exclusive offline-root ownership is required; arbitrary
  noncooperating writers and root-inode replacement are outside this contract.
- The final historical public installed fixture passes exact finite transforms,
  complete restoration, afterimage drift refusal and interrupted-entry recovery.
  Offline fixture ownership is distinct from root-owned installed metadata.

## Bound receipts and capacity

[Source/artifact hashes](receipts/repair/source.json),
[commands](receipts/repair/commands.json), [browser results](receipts/repair/browser.json),
[historical results](receipts/repair/historical.json),
[full historical inventory](receipts/repair/historical-plan.json),
[factory capacity accounting](receipts/repair/factory-capacity.json), and
[exact UI overlay](receipts/repair/overlay.json).
Private screenshots and complete logs are retained in
`local/feature-workflow/probes/printer-integration-20261004/candidate-check-r3/`.

Factory root is 2048 MiB, content budget 1536 MiB; boot is 192/144 MiB.
Data is 2447 MiB with 768 MiB floor and 6.25 MiB history overhead.
Conservative fresh/synthetic-historical composition peaks are 130/129 root blocks
and 97/127 data blocks (4096 bytes each), with 13/8 root and 3 data incremental
inodes. Data admission additionally retains 64 history inodes. Boot demand is zero.
Counts include hex originals inside the retained report, a report publication
copy, its directory and a root publication temporary. These bounds compare with
configured margins; they do not prove an arbitrary full image is within its content
budget or establish measured free factory inodes. Image-wide content admission
and actual installed capacity are separate retained gates. Exact historical
installed projection has its own complete capacity fields in the linked report.

The final UI-only installed packet is 69303 bytes across ten assets, three new
files. Runtime/backend/catalog and private feature limits remain unchanged.
Installation admission must account separately for packet/originals/status backup
files, check actual free blocks/inodes and preserve factory reserve policies.
The UI correction activates no printer configuration or outputs and changes no
boot policy. No hardware compatibility, commissioning or release claim.

## Attempt history

Earlier matching receipts remain in `receipts/` as historical evidence, not final
acceptance. The first repaired run failed a standalone test import; `candidate-check-r2`
preserves that attempt. `candidate-check-r3` is the passing final run. The worker's
browser startup failed private-directory ancestry; the coordinator used its assigned
private cache fixture for the actual successful run. Original review failures remain
in Git history. No test result was relabeled or threshold relaxed.
