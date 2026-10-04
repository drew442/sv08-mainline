# Installed initial-load navigation repair

2026-10-04. The first exact reviewed UI installation passed asset, metadata,
configuration, service-mask and read-only closure checks, before and after browser
inspection. Actual authenticated acceptance then found an initial-load race:
authorize on Overview and immediately enter Printer hardware while status is
pending. Navigation invalidated the status epoch and marked reconciliation even
though only a read had been submitted. The panel remained unloaded. Private
browser failure/diagnosis is retained in `installation-r1/` under the integration
probe directory. No configuration write, output activation or reboot occurred.

The installed task includes a bounded repair to distinguish status response
validity from navigation/review validity. Route changes may allow a current
read-only load to finish; authority, edit and load transitions still reject stale
responses. Submitted mutations are never replayed. A missing local draft can be
populated from saved state when keeping selections, since there are none to lose.
The delayed initial-load browser regression covers the observed sequence.

The original software acceptance remains historical. The repaired controller,
regression evidence, exact one-file follow-up operation and final installed
observations require independent reviews under this same approved feature.

## Bound offline regression

Code commit `8ec6aec8758e09bdb362c5782a43fcdf8ba78e5c` passed all 29 focused
staging tests, Node navigation and the complete actual Chromium suite. New checks
hold status across Overview→Printer and reverse navigation, require a populated
panel without false reconciliation and prove no mutation was requested. Delayed
status after Stop/logout/disconnect remains rejected; dirty edits survive both
rejection and subsequent deliberate reconciliation. Prior unsupported-state export,
lost-acknowledgment and host/printer isolation journeys remain passing.

[Bound source/artifacts](receipts/navigation/source.json),
[commands](receipts/navigation/commands.json), and
[browser assertions](receipts/navigation/browser.json) preserve final results.
Earlier attempts remain under `navigation-check*` and `navigation-diagnostic`.
Chromium reported disk exhaustion and failed script loads while temporary buffers
used the nearly full workstation disk. Disposable profile/shared-memory placement
and removal of already merged clean worktrees resolved the resource issue. Tests
now wait for a new document and an enabled Authorize button, so they do not click
before Stop has finished. No application admission or assertion was relaxed.
No installed success is claimed by this offline run.

## Review before the follow-up write

Separate Sol6.1/high delivery review passed the bounded repair at `31632ab`,
including a targeted before/after probe and actual source/artifact hash checks.
Separate Sol6.1/medium action review passed the exact one-file operation with
fresh target/power checks and full immediate/post-browser closure conditions.
Both full-role effective runtimes were coordinator-verified.

Packet SHA256 `f3e9aed7d143304e68f1db93731f435b5470e41b7c232a358982591dff1f66bf`;
script SHA256 `add426b8d5a83bc4bc261e4fa8afcc17e4ed2475573df1b27bf8a36a1332f522`;
printer app afterimage `992569b53168b37d3231114674ffc032a0885ca2785a7f7cc4b882488680a0dd`.
The script differs from the first reviewed installation only in its distinct
`-navload` backup directory. Both sets of originals are retained. All 14 UI assets
and the 50-file UI/runtime/catalog closure are checked, with supplemental exact
membership/type/metadata and capacity-floor enforcement. These reviews authorize
no broader operation and do not themselves establish installed success.
