# Installed shared Cockpit interface

Date: 2026-10-04. Profile: **test-sv08-01**, spare eMMC immutable slot A.
Mainboard revision **H616_JC_6Z_V1.2** is owner-reported; this UI check does not
validate electronics, MCU settings, outputs or printing. Independent delivery
acceptance is tracked in the adjacent [record](record.json).

## Observed result

Actual authenticated Cockpit navigation passed on the printer:

- One document, header, sidebar, authorization dialog and session; no iframe or
  duplicate IDs. Printer hardware is an ordinary persistent section of the shell.
- Unsaved host and printer edits survive section changes and Back/Forward.
  The old printer bookmark redirects into the integrated shell.
- Desktop 1440×900, touchscreen-sized 1024×600 and narrow 390×844 layouts retain
  active navigation, matching branding and no page-width overflow.
- Initial loading works during immediate navigation after authorization.
  The normal host-status poll settles the header after navigation.
- Read-only helper state before/after browser edits is identical. No draft save,
  candidate application, configuration activation or output operation was sent.
  Browser-only test edits were discarded on departure, and the session logged out.

[Browser results](receipts/installed/browser.json),
[exact preservation](receipts/installed/preservation.json),
[directory membership/type/metadata and capacity](receipts/installed/inventory.json),
[PSU state](receipts/installed/power.json), [installed manifest](receipts/installed/manifest.json),
and [private artifact hashes](receipts/installed/artifacts.json) bind the result.
Screenshots and complete receipts remain privately under
`local/feature-workflow/probes/printer-integration-20261004/installation-r2/`.
The coordinator visually inspected the desktop capture; the narrow and touchscreen
captures are available for independent review.

## Installation and closure

The reviewed first overlay changed ten UI assets (69303 bytes), preserving
historical host bytes outside finite shared-panel transformations. Actual login
then found the [initial status/navigation race](installed-race-repair.md).
That failure and its read-only closure are retained. The independently reviewed
one-file follow-up replaced only printer app.js (20632 bytes); its payload matches
source `4e8eed9`. Later commits change tests or evidence, not that controller.

Exact checks immediately after each write and after browser execution establish
14 UI assets and a 50-file UI/runtime/catalog closure. File hashes, modes and
ownership match; directory checks reject unexpected entries, links and types.
Unchanged saved configuration/context, boot identity, seven masked inactive
services and absent live printer.cfg were confirmed. Root and boot are read-only;
persistent data remains writable. PSU remained OFF. No restart or power switch.
Capacity retains root 512 MiB/data 768 MiB floors and at least 128 free inodes.
Both sets of original UI assets and exact operation packets remain privately on
persistent data for recovery; no whole-set power-loss atomicity is claimed.

The [operation review](installation-review.md) and follow-up review record contain
the exact write boundaries. Full-role independent reviewers used Sol6.1/high for
software/concurrency and Sol6.1/medium for exact operations, with effective settings
verified separately. Installed delivery review uses these observations, not the
offline browser shim. Heater/motion commissioning and physical checks remain outside
this UI delivery.
