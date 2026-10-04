# Shared Cockpit panel: offline evidence

2026-10-04. Executed code commit `86fd625b8c4fd13d49e047bd4b3218c881ff34b5`.
The following documentation commit preserves that code tree unchanged.

## Results

- Six printer staging tests and seventeen host staging tests passed. Node navigation
  checks passed; actual Chromium journeys passed with zero uncaught exceptions.
- One document, header, sidebar and shared session; allowlisted routes, history,
  legacy redirect and reload; host/printer dirty values survive section navigation.
- Reviews and delayed responses are invalidated on navigation or authority loss.
  Lost apply acknowledgments spanning navigation and Stop/logout/disconnect require
  explicit saved-state reconciliation without discarding local edits or replaying.
- Host status failures cannot disable printer controls. Host upload and ordinary
  review cancellation regressions pass. Existing preset, import/export, inactive
  apply/restore, CAS and generation journeys pass using the real Store/Budget.
- Screenshots and root-overflow assertions cover 1440×900, 1024×600 and 390×844.
  Transport is a Cockpit shim; this is not authenticated installed evidence.
- Historical installed public assets were copied to a disposable fixture. Exact
  finite transforms preserve unrelated host bytes. Full restoration, beforeimage
  refusal, afterimage drift refusal and interrupted entry publication recovery pass.
  Offline fixture ownership differs from the recorded root-owned installed files.
  Publication is atomic per file, not across the whole set; retained originals and
  prechecked partial restoration supply recovery.

## Reproducibility and limits

[Source and artifact hashes](receipts/offline-source.json),
[commands/results](receipts/offline-commands.json),
[browser assertions](receipts/offline-browser.json),
[historical outcome](receipts/historical.json),
[complete staging inventory](receipts/historical-plan.json), and
[exact UI overlay summary](receipts/overlay.json) bind these results.
Private screenshots and full logs are retained under
`local/feature-workflow/probes/printer-integration-20261004/candidate-check-r1/`.

Fresh full payload is 295872 bytes; conservative staging peak is 164 4096-byte
blocks with three new files. The exact installed UI overlay is 68801 bytes across
10 files. Existing factory root/data reserve policies and private-feature limits
are unchanged. The coordinator must separately admit installed free blocks/inodes,
backup/temporary usage, metadata and preserved runtime closure before installation.
No backend/catalog/runtime, printer configuration, boot policy or upstream changes.
Uninitialized submodules in this worktree remain unchanged indexed gitlinks.
No hardware compatibility, commissioning or release claim.

## Preserved unsuccessful attempts

The first fixture lacked free workstation space; disposable pip cache removal
restored space without changing admission. A transport-shim argument mismatch,
narrow layout overflow and navigation readiness races were repaired and retested.
The initial coordinator run exposed a historical test using moving HEAD; the test
now pins the pre-integration commit. That failed run is retained as `candidate-check`;
`candidate-check-r1` is the passing source-bound run. No check was waived.
