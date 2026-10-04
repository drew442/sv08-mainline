# Loaded configuration identity repair — 2026-10-04

The [second independent review](reviews/20261004-software-f2-findings.md)
reproduced a draft overwrite across actual A/B generations with equal revisions.
Failed candidate4f865df and its original evidence remain preserved.

Status now supplies an ordinary content/context identity binding saved draft,
revision, current candidate, catalog, generator and boot/generation context.
Every non-status operation compares it under existing Store/feature locks before
preparing or publishing a result. Revision comparison and mode-specific apply
review remain. The UI retains the identity from its last successful status; edits
never silently refresh it. No permission mechanism, nonce, replay ledger or
persisted-format change is introduced.

[Sixteen focused tests](evidence/repair-f2/focused.log) passed on actual current
Store/Budget and historical Store. Equal-revision divergent A/B drafts refuse
stale Save, restore, import, preset, review and apply, preserving stored bytes.
Boot/mode/catalog/generator/content changes, positive refresh and existing CAS,
locks and lost-ack paths are covered. [Actual Chromium](evidence/repair-f2/browser-result.json)
passed the generation-copy case through native controls, preserving both generations
and allowing explicit reload/edit/save/review/inactive apply. Existing preset,
two-tab, export/restore, keyboard/touch and session journeys remain. Authentication
and transport are shimmed; installed ARM64 acceptance is still separate.

[Source audit](evidence/repair-f2/audit-result.json) confirms six owned changed files,
syntax/links/diff and indexed gitlink/lock agreement. Helper/UI payload grows348
bytes: net additive256434 bytes, derived from exact source delta. Publication,
capacity, catalog, generation output and staging mechanisms are unchanged; retain
[prior repair evidence](software-repair-f1.md) and independent source/staging checks.
No broad durable-state, parser or physical campaign was repeated.

The full-role Sol6.1/medium author used approximately7 minutes; cumulative author
lineage approximately73 minutes. One browser profile measured10028627 bytes and
was removed; generated-write estimate below20MiB, not instrumented. No hardware
operations. Old tabs without the newly required field must reload. Independent
software review and exact installed acceptance remain pending. Physical input
checks and fine calibration remain owner-deferred; no outputs are activated.
