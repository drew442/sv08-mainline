# Component configuration repair — 2026-10-04

Source repair commit `7cb0394`; the delivery record binds the final evidence commit.
The [original candidate evidence](software-execution.md) remains historical;
[its failed independent review](reviews/20261004-software-f1-findings.md) identified
stale imports, the TMC2209 current bound and insufficient component presets.

## Repairs and evidence

- Import now requires the revision loaded by the tab under the existing locks.
  Stale import and subsequent save refuse; refresh shows the exact replacement.
- Driver current independently enforces pinned Klipper's 2.000 A software maximum.
  Physical motor ratings remain explicit unknowns. This is not a safe-current claim.
- Thirty declarative presets provide friendly source-qualified sensor, motor,
  bed/hotend, fan and input choices across the four reference boards. Every field
  has an exact source and transformation. Dependencies are added atomically to an
  unsaved draft; collisions refuse without overwriting existing selections.
  The documented SV08 Z 80:12 gearing is retained. Ratings and calibrated probe
  offsets are never supplied as defaults; source polarity is not measured polarity.
- [Nineteen focused tests](evidence/repair-f1/focused-final.log) and
  [two staging tests](evidence/repair-f1/staging-final.log) passed without skips.
  These include actual current/historical Store stale-import behavior, preset
  provenance/collisions, contributor extension, typed gearing and current limits.
- [Actual Chromium journeys](evidence/repair-f1/browser-result.json) passed at
  1024×600 and 1440×900, including two real tabs, stale import/save refusal,
  refreshed exact comparison, sensor and motor presets and existing inactive
  apply/restore/session flows. Cockpit transport/authentication is shimmed;
  the Store is real. Installed authentication remains a separate task.
- [Pinned file-output parser](evidence/repair-f1/parser-result.json) accepted
  2 A with exact gearing and rejected 3 A/4 A. The retained actual results report
  exit255 for refused cases; the author's handoff saying exit0 is superseded here.
  Acceptance is based on parser log inspection. Original positive sensor/full
  bytes are unchanged. No device was opened and no physical current is certified.
- [Source audit](evidence/repair-f1/audit-result.json) and
  [source manifest](evidence/repair-f1/source-hashes.json) cover the ten owned
  changed files, syntax/schemas, Markdown targets, modes and gitlink/lock agreement.
  New root payload256028 bytes plus58-byte navigation delta totals256086 bytes.
  Existing shared reserves and the4MiB feature storage cap remain unchanged.

Original persistence, killed-process, no-space and generation-copy checks remain
applicable to unchanged publication code; their [evidence](software-execution.md)
is retained. Failed browser cleanup/accounting and intermediate extraction/audit
attempts remain in private repair evidence; final corrected runs passed. No
historical failure was replaced. Full-role Sol6.1/medium repair used approximately
19 minutes, cumulative author lineage approximately66 minutes. Own browser profiles
were removed after measurement; generated-write estimate below56MiB, not instrumented.

Independent final software review and exact installed acceptance are still pending.
Physical filament/probe checks and fine calibration are owner-deferred. No heat,
motion, live configuration activation, compatibility or release claim is made.
