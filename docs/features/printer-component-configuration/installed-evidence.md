# Installed printer hardware configuration — 2026-10-04

All installed execution checks passed; [independent delivery verification](reviews/20261004-installed-final-findings.md) passed.
Target: test-sv08-01 diagnostic slot A on the preserved spare eMMC; H616_JC_6Z_V1.2
is owner-reported, MCU board revisions remain unknown. Same host boot throughout;
PSU OFF and USB power unchanged. No restart, MCU operation, heat or motion.

## User workflow

Open **Printer hardware** from the SV08 Mainline Cockpit page. Select mainboard
and toolhead references, then documented components or explicit custom settings.
Thirty data-only reference presets cover sensors, motors/TMC2209, bed/hotend,
fans and inputs across SV08 main/tool and exact Octopus non-Pro/EBB v1.2 references.
Pins, defaults, bounds and their sources are visible. Missing physical ratings,
identity and calibration remain explicit. Contributors extend the
[catalog](../../development/printer-hardware-catalog.md) without executable plugins.

Incomplete drafts can be saved/exported. Review and Apply save a separate inactive
candidate; they do not alter live printer.cfg or start services. The useful final
saved draft selects the existing two MCU transports and both unchanged factory
sensor curves/bounds, with provisional references acknowledged. Private transport
identifiers, screenshots and downloads remain ignored. Finely calibrated curves,
physical probe/filament transitions and output commissioning are deferred.

## Exact installation and recovery evidence

[Software acceptance](reviews/20261004-software-final-findings.md) binds candidate
7a2894ad; main and WIP contain its reviewed source. Independent high action reviews
cover the [exact overlay](reviews/20261004-installation-high-review.md),
[preflight interpreter correction](reviews/20261004-installation-preflight-correction-review.md)
and [browser continuation](reviews/20261004-installed-browser-continuation-review.md).
Effective Sol6.1/high runtimes were checked by the coordinator.

The first preflight stopped before any write because system Python lacks cffi.
The existing pinned Klipper venv passed the unchanged check. No dependency was
installed. Absence of page/backup/unit and read-only mounts established no-write
reconciliation before renewed review. The first actual installation then passed
[readback and closure](evidence/installed/overlay-result.json): twelve new files
and only a58-byte link in the existing host page. [Payload inventory](evidence/installed/payload.json)
is256434 additive bytes (265476 whole afterimages). All33 inherited public source/
config files were preserved except that exact host navigation change. No broad
Store/core refresh, service restart, authentication or boot-policy change.

Per-file atomic replacement publishes navigation last; private beforeimages and
receipts remain available. The operation does not claim all-file power-loss
atomicity. Root was remounted read-only, and the bounded unit ended inactive/PID0.
All failure evidence is preserved in [this summary](evidence/installed/preserved-failures.json).

## Actual authenticated ARM64 journey

The [first browser attempt](evidence/installed/browser-first-partial.json) passed
real login/elevation, second-package navigation and incomplete save/reopen, then
hit a harness evaluation failure. The source-level lexical-scope diagnosis is an
inference, not a captured CDP exception. A newly reviewed continuation required
exact equality with the preserved revision1 envelope; no state was reset or erased.

The [continuation](evidence/installed/browser-continuation.json) passed documented
sensor/motor presets, import comparison/cancel, two factory default curves/pins/
bounds, keyboard Escape, review/apply inactive, prior candidate restore, board-change
clearing/discard, actual downloads, browser touch at1024×600, desktop1440×900,
Stop administrator access, logout/relogin and persistent draft reopening. Final
logout completed and own Chrome processes stopped; the existing SSH tunnel remains.
TLS fingerprint and tunnel destination were verified before credential submission.
Screenshots were visually inspected for board/preset layout; physical touchscreen
interaction and the entire long device form are not claimed visually inspected.

## Final named-host closure

[Exact final state](evidence/installed/final-state.json) is revision9, two-sensor
inactive candidate with previous retained,5964 apparent feature bytes, directory0700
and files0600. All13 installed afterimages match. Available data2433216512 bytes
and156681 inodes preserve existing shared reserves; factory8GB allocation is unchanged.
[Final closure](evidence/installed/final-closure.json) and
[inherited inventory/idle check](evidence/installed/final-inherited.json) confirm
same boot/CID/registry/environment, read-only root/boot, unchanged seven filesystem/
cmdline masks, no live printer.cfg/health-ready/serial users, unit inactive/PID0,
PSU OFF and unchanged inherited files. No outputs or printer services were activated.

This is installed configuration-page acceptance evidence, not printing, physical
hardware compatibility, heated calibration, full A/B qualification or release.
The separate [ambient baseline](../sensor-default-commissioning/intake.md#corrected-ambient-baseline-completed)
is already complete and was not repeated. Owner-deferred physical checks remain
in the [human task list](../../hardware/coordinated-human-tasks.md#component-configuration--2026-10-04).
