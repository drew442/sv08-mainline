# Printer shared-shell runtime invariants

Interface requirements are defined by [the current page design](printer-hardware-page-design.md)
and [definition sources](printer-definition-sources-design.md). This document
records integration and storage invariants rather than page layout.

The host shell compiles `ui/printer/panel.html` with
`scripts/stage_printer_ui.py:compose_host`. Browser fixtures use this same function.
The controller mounts once with prefixed IDs and panel-scoped CSS. The existing
host session adapter owns authorization. Hash navigation retains native form
values and private in-memory drafts; no fragment fetch, iframe or draft storage
is used. Legacy printer links redirect into the host's `#printer` route.

Navigation closes reviews and advances response epochs. An operation already
submitted may finish; invalidation does not cancel a backend write. An uncertain
save/apply or an authority transition with dirty selections blocks mutations
until explicit saved-state reconciliation. Reconciliation updates the saved
revision/context while retaining local selections. Discard separately confirms
replacement with the saved draft. Unsupported saved schemas or catalogs disable
mutations and form editing while preserving the local draft for export recovery;
only explicit discard replaces it. Document reload warns for dirty selections. The skip link focuses the current section without changing its route.
Host polling failures exclude printer buttons. Host notices and image jobs appear
only on host sections. Navigation invalidates upload reviews, retaining active
transfer semantics and existing submission receipts.

Staging accepts current fresh input or fixed known host HTML/app/upload preimages.
Historical application transformations replace only routing, control isolation
and review epochs; unrelated operation code is retained. A finite appended CSS patch constrains the shared grid and narrow header. The route function retains a fallback for old host HTML during interrupted publication. Unknown hashes or
ambiguous anchors fail before mutation. Existing backend/catalog bytes must match
and are never refreshed by the overlay. Complete file/directory preimages include
hashes, modes and ownership. The returned report retains originals and enumerates
all afterimages, additions, payload bytes, added inodes and conservative 4 KiB
payload-plus-backup blocks. The existing 4 MiB private-feature cap is retained.
The capacity report also bounds root publication/restoration temporaries and two
copies of the retained JSON report (including hex-encoded originals), with one
new report directory on `/data`. There are no separate on-disk backup files.
The focused factory accounting test compares both fresh and historical cases to
`configs/images/host-ab.json`: each root is 2048 MiB with a 1536 MiB content
budget (512 MiB reserve); each boot is 192 MiB with a 144 MiB content budget
(48 MiB reserve); data is 2447 MiB. The unchanged shared data floor is 768 MiB,
plus 6.25 MiB history admission overhead and 64 history inodes from
`runtime/sv08_data_budget.py`. Boot demand is zero. Root and data inode demand
is reported separately, including one root temporary and retained/temporary
report inodes. Factory free inode counts and actual installed usage are unknown;
these are conservative offline bounds against configured budgets, not measured
factory free space or installed admission. Deployment packet copies and any
additional operator backups require separate accounting. Set
`SV08_CAPACITY_RECEIPT` to an assigned private output path when running
`test_stage_printer_ui.py` to retain the reproducible calculation.

Publication and restoration use per-file atomic replacement, with host HTML published last and restored first. Temporary-name conflicts are prechecked. Unchanged backend/catalog files retain their inodes. The report also records net root byte delta and the largest per-file temporary. Retain the
planning report before execution; interrupted staging can use
`restore(root, report, interrupted=True)` to accept only exact pre/afterimages.
Normal restoration requires every afterimage and unchanged closure to match before
any mutation. Restoration removes navigation first. This is offline disposable-root
staging, not an installer or authorization for a printer operation. All supported printer stage/restore and admin stage/host-refresh entrypoints
hold the same nonblocking exclusive `flock` on the offline root directory inode
from before prechecks through their final writes. Contention refuses without
mutation, including dry runs. No lock file is created or deleted. The operating
precondition is an exclusively owned offline root: do not rename/replace the
root or run other writers outside these entrypoints. Complete preimage/afterimage
checks still precede mutation. Printer publication/restoration recheck the evolving
snapshot between writes and before replacement, stopping and preserving unexpected
changes when drift becomes visible. Interrupted work retains the original report.
Multi-file publication/restoration is per-file, not all-or-nothing against
uncooperative external writers: a writer can race the last check and replacement,
and earlier completed writes remain. Such writers violate the operating
precondition; no arbitrary-writer atomicity is claimed. Extending that guarantee
would need a separate design decision, not removal of the existing checks.

Host-only staging removes printer navigation when the package is absent. A host
refresh with the package requires matching compiled-panel assets before mutation.
Recovery assembly is unchanged. The custom integration can retire when upstream
shell navigation supports the accepted appliance controls and draft lifecycle.

Focused reruns from the candidate worktree:

```sh
python3 -m unittest discover -s tests -p test_stage_printer_ui.py
python3 -m unittest discover -s tests -p test_stage_admin_ui.py
node tests/printer_navigation.mjs
python3 tests/test_printer_browser_fixture.py /home/drew/.cache/sv08-printer-integration-20261004/fixture-next
node --require /home/drew/sv08-mainline/local/feature-workflow/probes/history-rollover-20261003/implement/browser-websocket.cjs tests/printer_browser.mjs /home/drew/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome /home/drew/.cache/sv08-printer-integration-20261004/fixture-next /home/drew/.cache/sv08-printer-integration-20261004/browser-next
```

The fixture supports successful host status, injected polling failure and delayed host/printer reviews and inactive apply acknowledgments. Browser execution requires sufficient free space for the unchanged Store/Budget
and private non-group-writable fixture ancestry. Browser shim evidence is offline,
not authenticated Cockpit or installed/hardware acceptance.

Existing managed directory membership is checked as well as file metadata. Extra
files, directories or links in that inventory refuse before staging or restoration,
including interrupted restoration. The only temporary entry allowed during a
replacement is that operation’s explicitly named publication temporary.
