# Persistent printer panel

The selected host shell compiles `ui/printer/panel.html` with
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
replacement with the saved draft. Document reload warns for dirty selections. The skip link focuses the current section without changing its route.
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
These counts are not a factory8GB reserve admission result.

Publication and restoration use per-file atomic replacement, with host HTML published last and restored first. Temporary-name conflicts are prechecked. Unchanged backend/catalog files retain their inodes. The report also records net root byte delta and the largest per-file temporary. Retain the
planning report before execution; interrupted staging can use
`restore(root, report, interrupted=True)` to accept only exact pre/afterimages.
Normal restoration requires every afterimage and unchanged closure to match before
any mutation. Restoration removes navigation first. This is offline disposable-root
staging, not an installer or authorization for a printer operation. Multi-file
publication is not atomic, and arbitrary concurrent filesystem writers are not
serialized by this Python utility.

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
