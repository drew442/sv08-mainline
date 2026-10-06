# Printer hardware and definition-source delivery — 2026-10-06

## Scope and revision

Implementation starts at `3af537e` after fast-forwarding main from `11912e0`
to `651e86b` and replacing competing normative hardware-page guidance with links
to the owner-selected design briefs. Historical identities and evidence remain.
The complete implementation revision is bound by the feature record, rather than
embedding a self-referential commit hash here.

The owner clarified the initial hardware scope:

> just add the factory sv08 options. we will add the 3rd party upgrades and add-ons via the definition sources later

This delivery therefore bundles 15 factory SV08 public definitions. Existing
legacy configurations remain readable; no new Funssor, Eddy, CN3D or chamber-kit
hardware facts are invented. The public format remains draft 0.1; the requested
third-party combination trial and format freeze are deferred by that scope change.

## Delivered behavior and acceptance

| Requirement | Implementation / observed evidence |
| --- | --- |
| Component-first page | Seven component cards, searchable source-qualified choices, contextual details, Components/Connections/Changes tabs and collapsed Advanced. Factory-only normal choices. |
| Connections / board replacement | Logical map and table derive signals from documented connectors; unknown contacts remain labelled unknown. Board preview preserves or remaps assignments and marks unresolved connections, clearing dependent identity/calibration. |
| Changes / output | Semantic selection and field changes, defaults/overrides/reset and actual previous/candidate text. Incomplete selections save independently of generated output. Input gaps and definition gaps have distinct labels. |
| Calibration | Bed replacement clears dependent probe calibration; unrelated fan/shared-definition changes preserve it. PID remains commissioning data, not a hardware selection prerequisite. |
| Shared public format | Built-in adapter, JSON Schema family, shared runtime/creator validator, component/board/cross-category assembly/behaviour starter examples. Equivalent external and built-in component facts produce equal devices. |
| Sources | Public GitHub URL/ref/path preview, exact commit/tree/blob fetch, index and byte hashes, bounded staged admission, explicit update checking, disable/enable/remove and unified selectors. Import never executes repository scripts. |
| Composition | Source-qualified immutable versions, pinned closure/runtime assets, conflicts/cycles/required capability errors, explicit updates preserving overrides, shared dependency retention and offline generation after source removal. |
| Behaviour | Explicit check-only levelling hook composes independently of selection order; conflicting temperature bounds fail. Generated Jinja macro loads in pinned Klipper. Unsupported waits/heating/raw publisher macros remain unavailable. |
| Migration / privacy | Legacy preview preserves original backup and instance identities, identifies imported origins without guessing stock. Shareable export omits MCU identities/custom text; opaque future formats remain available as private diagnostic backups. |
| Revision / recovery | Existing Store/Budget lock, loaded identity and revision protocol covers selections, sources and publication. Stale tabs, changed generations and lost acknowledgments require reconciliation. |
| Managed publication | Exact explicit include inventory including SAVE_CONFIG; unmanaged text preservation/section conflict detection; immutable bundle plus single activation file; original permissions preserved; journals/receipts, interrupted reconciliation and restoration tested. |
| Admission / validation | Managed services must be stopped; reserve and managed-data budgets checked; exact fresh review and complete pinned parser validation required before writes. No service restart, G-code, heater or motion action. |
| Commissioning handoff | Saved selections, inactive candidate, applied configuration and commissioning are separate UI states; application leaves printer stopped and describes separate calibration/commissioning requirements. |

## Executed validation

Commands ran in the isolated `feature/printer-definition-redesign` worktree.
Final discovery `python3 -m unittest discover -s tests -p 'test_printer_*.py'`
ran 79 tests successfully, with the explicitly provisioned pinned-runtime test
skipped in that invocation. The pinned test was then run with its existing assets:

```sh
SV08_PRINTER_SOURCE_ROOT=/home/drew/sv08-mainline \
SV08_PRINTER_VALIDATION_PYTHON=/home/drew/sv08-mainline/build/printer-interface-prep-20260918/venv/bin/python \
python3 -m unittest discover -s tests -p 'test_printer_publication.py'
python3 -m unittest discover -s tests -p 'test_stage_printer_ui.py'
python3 scripts/printer_definitions.py validate examples/printer-definitions
```

Publication: 10 passed, including the complete-output positive fixture, generated
check-only macro integration, invalid kinematics and unsupported host section.
Staging: 12 passed, including payload closure/rollback and exact dictionary rejection.
The focused definition/configuration suites account for 18 and 46 passing tests.
Creator validation accepts all four starter records; built-in records pass schema
and semantic checks. Node syntax and `git diff --check` pass.

Pinned Klipper is `f0892d82b0f1c1228454f09eb508eddde2250f4b`.
Entry SHA-256: `aa9eb47fbe3598fc814d40ed8e0b2b814a0af459fca7acab6732c59bf42e4659`.
Simulated MCU dictionary SHA-256:
`86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b`.
The dictionary is not committed; deployment staging accepts only this exact asset.
Validation uses file output, a private API and CPU/memory/file/wall-time limits.

[Browser receipt](browser.json) records the actual Store/Budget fixture journey with
Chromium, a Cockpit session/RPC shim and Node 22.23.2. Viewports: 1024×600,
1440×900 and 390×844, plus 200% zoom. Keyboard, touch, selection/cancel/save,
local source addition/removal with retained external selection, logical connections,
stale sessions, disconnected authority, lost acknowledgment, restore and opaque
format recovery pass, with zero uncaught exceptions and no live-config change.
Screenshots, raw fixture data and generated images are excluded from publication.

## Limits of this evidence

These are coordinator self-validation results, not independent review, authenticated
installed Cockpit acceptance, hardware matching or a printing release. No physical
printer operation or installation was performed for this delivery. The approximately
one-minute usability target has not been observed with a human user. Source importer
unit fixtures exercise GitHub branch/commit/tree semantics and failure cases; the
browser exercises a local bundle, not authenticated or private GitHub access.

Heating/cooling waits, heat soak, new unsupported electrical/device families and raw
publisher macros require future capabilities. Explicit local custom configuration
has ownership review and complete-output parsing; parser acceptance is not a safety
assessment of arbitrary user code. Publication requires the exact validation asset
and refuses absent assets/unsupported startup or host-hardware sections. Wildcard
include adoption and conflicting unmanaged sections require explicit resolution.
Third-party source research/trials and physical commissioning remain separate work.
