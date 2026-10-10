# Cockpit UI/UX review and workplan

Reviewed 2026-10-10 at `b4bfb437a3f3e4fe000e08768102855ea871d416`.
Status: proposed workplan; implementation and installed acceptance are outstanding.

## Recommendation

Improve task hierarchy and status correctness first, then simplify the hardware
selection and review journey. The current component cards, outline icons,
definition drill-down, advanced disclosure and separate Connections page are good
foundations. Preserve them and the existing frontend rather than starting again.

The primary audience is a printer owner who wants to describe fitted hardware,
understand whether settings are saved or applied, and administer the printer
without Linux commands. Definition authors are a secondary audience: their
repository tools should remain available without leading the owner's workflow.

The recommended first bounded delivery is **W1 + W2: trustworthy status and a
compact shared shell**. It addresses problems visible across several pages before
individual page polishing. This review does not authorize implementation or
printer operations and creates no native goal.

## Evidence and limits

Source review covered the composed host/printer shell, navigation, session/status
handling, hardware and source controls, and the host administration page markup.
The accepted [hardware design](printer-hardware-page-design.md),
[definition-source design](printer-definition-sources-design.md) and
[shared-panel contract](printer-cockpit-panel.md) remain authoritative. Later owner
decisions placing Connections, Definitions and Definition sources in the main
sidebar are preserved; historical navigation suggestions are not reinstated.

A disposable loopback fixture rendered all twelve routes at 1440×900, hardware
and updates at 1024×600, and hardware, definition sources and Network at 390×844.
A second capture inspected page content and the factory-selection replacement
dialog. There are 23 screenshots; twelve were opened for visual assessment:

- Initial capture: Overview, hardware, Definitions, Definition sources, Network
  and Mainsail access at 1440; hardware at 390; updates at 1024.
- Content capture: hardware/replacement dialog, Definition sources and updates
  at 1440; hardware at 390.

The screenshots show the existing HTML/CSS and JavaScript with a test session
bridge, not the outer production Cockpit shell. The fixture uses real disposable
printer state and a stub host status. Its scratch-only file allowlist was extended
to serve the existing identity/access/network/software modules. Their service RPCs
are unsupported: resulting “Unexpected fixture helper invocation” messages are
**fixture limitations, not product defects**. Happy-path states for those services,
real authentication, a populated connection graph, and installed behavior remain
unassessed. The factory-selection dialog was opened without confirming, saving or
applying; this is not evidence of the installed hardware configuration.

No horizontal document overflow appeared in the captured states. This does not
establish complete responsive behavior, keyboard accessibility or WCAG conformance.
Captures are review evidence, not execution of the existing acceptance suites.
No printer was contacted and no service or hardware output was activated.

Local evidence: `/home/drew/.sv08-ui-review-20261010/`, including
`rendered-review.json`, `detail-review.json`, screenshots, capture scripts and
process-retirement receipt. The companion
[evidence manifest](cockpit-ui-ux-review-evidence.json) binds source and screenshot
hashes without publishing browser profiles. The prior routing adoption evidence
is `/home/drew/.sv08-codex-adoption-20261010/report.md`.

## Findings

| ID | Priority | Finding and evidence | User consequence |
| --- | --- | --- | --- |
| F1 | P1 | An authorization-required notice remains after elevation, while the header reports administrator access and host connected. Reproduced in the fixture; `ui/host/app.js:refresh` renders successful status without reconciling the earlier notice. | Users cannot tell whether they are authorized or should retry. This is a notice-lifetime defect; installed authorization failure is not established. |
| F2 | P1 | Idle image operations, archive counters and a disabled maintenance button precede hardware, definitions, sources, identity and other pages. `navigation.js` hides this article on only three routes. In the fixture, hardware starts at about y=579 on 1024×600. | The page's purpose and main actions are below the first screen. The offline fixture banner contributes height, but the irrelevant panel also exists in production markup. |
| F3 | P1 | Hardware exposes Save selections, Review changes, Generate and review configuration, Save generated configuration, Review application to printer and Apply configuration as separate controls. Current markup explains their distinction mainly in prose. | Owners must infer which action makes the installed services use their selected hardware. |
| F4 | P2 | The replacement dialog leads with a monospace list such as `bed_sensor`, `heater_bed` and `stepper_z3`, followed by broad calibration text. Rendered factory-selection dialog and `previewDefinition` source. | Review requires knowledge of internal devices; the effect on the selected assembly is hard to scan. |
| F5 | P2 | Definition sources leads with two large author-download actions before the repository URL, preview and installed sources. Rendered source page; default preview status says saved configuration/candidates. | Adding a modder's repository is secondary to creating a repository; page feedback describes a different task. |
| F6 | P2 | Twelve sidebar entries share one category; narrow layouts use an overflowing horizontal navigation strip. The session strip presents both grant and revoke controls, even when one is disabled. | Discovering pages and reaching useful content requires excess navigation and scrolling, especially on phones. |
| F7 | P2 | Several operation reviews use `pre` text, JSON evidence or backend field names. Identity/access/network/software have separate feedback and disabled-control implementations. Source finding; full service journeys not rendered successfully here. | Consequences and recovery instructions can be inconsistent. Validate representative real states before asserting specific service-page defects. |
| F8 | P3 | Host status polls every 1.5 seconds regardless of the current page; visual refresh correctness relies on preserving drafts and control state. Source finding only. | Potential avoidable work and distracting updates. No CPU or performance improvement is measured or promised by this review. |

## Ordered work packages

Effort labels describe relative scope, not time commitments. Each package should
ship with its own relevant checks and truthful limitations; avoid one giant redesign.

| Package | Priority / scope | Dependencies | Main paths |
| --- | --- | --- | --- |
| W1 Trustworthy status and recovery | P1, small–medium | None | `ui/host/app.js`, `session.js`, `navigation.js`; affected page modules |
| W2 Shared shell and responsive navigation | P1, medium | W1 notice contract | `ui/host/index.html`, `style.css`, `navigation.js`; host composition |
| W3 Hardware selection-to-application journey | P1, medium–large | W1/W2 | `ui/printer/panel.html`, `app.js`, `style.css`; existing controller contracts |
| W4 Owner-first definition sources | P2, medium | W2 | Source and Definitions sections in printer panel/app/style |
| W5 Updates and software task hierarchy | P2, medium | W1/W2 | `ui/host/index.html`, `app.js`, `upload.js`, `software.js` |
| W6 Access, identity and network clarity | P2, medium | W1; representative service fixtures | `identity.js`, `mainsail-access.js`, `network.js`, host markup |
| W7 Cross-page accessibility and consistency | P2, distributed | Applied throughout W1–W6; final sweep afterward | Shared styles, dialogs, page modules and browser tests |
| W8 Refresh efficiency | P3, small–medium investigation | Stable status/draft behavior | Existing refresh/polling code and focused tests |

### W1 — Trustworthy status and recovery

Give authorization, connectivity, operation progress and saved-state feedback
separate ownership and lifetimes. Replace raw errors with a short explanation and
an actionable next step; retain technical details on demand. Do not clear durable
uncertain-submission or reconciliation warnings simply because a poll succeeds.

Acceptance:

- Elevating from a read-only session removes an obsolete authorization notice when
  successful status confirms access; the header and page agree. Revocation or
  disconnect promptly disables mutations without discarding non-secret drafts.
- An unrelated host failure does not imply that the hardware catalogue or Mainsail
  access is unavailable if its own backend still works.
- A lost acknowledgment offers receipt/reconciliation checking instead of inviting
  duplicate application. Loading/retry/completion messages describe the active
  task and do not announce success before the operation is confirmed.
- Background refresh cannot erase a still-valid warning or user-entered draft.

### W2 — Shared shell and responsive navigation

Put the page title, relevant status and useful next action first. Show full image
history only on Updates; show a compact link elsewhere only when an operation
actually needs attention. Put capacity counters and maintenance under details.
Use concise headings and a compact session indicator with the currently relevant
grant/revoke action. Consider sidebar groups for Printer, System and Access while
keeping all existing routes and the owner's separate main-menu sections.

On narrow screens, use an accessible menu control instead of making the complete
sidebar a long horizontal strip. Preserve the branding, visible focus and adequate
touch targets; do not solve density by shrinking controls or hiding consequences.

Acceptance:

- On an idle 1024×600 production-equivalent shell, hardware's title and at least
  one component choice are visible without scrolling. At 390×844 its purpose and
  first useful action are visible without first passing unrelated history.
- Active or uncertain update work remains discoverable from every route through a
  concise indicator; opening it leads to the correct operation and recovery action.
- All routes remain accessible by keyboard and touch. Menu opening/closing,
  Escape and focus return work; navigation preserves unfinished selections.
- Browser back/forward, direct hashes and the single shared authorization session
  retain the existing shared-panel invariants.

### W3 — Hardware selection-to-application journey

Keep component selection simple: choose installed mainboard, toolhead, bed, hotend
and other assemblies from definitions, then answer only genuinely missing facts.
Keep custom electrical values and configuration text under Advanced. Calibration
remains a separate activity; selecting hardware must not start PID, homing or heat.

Present a persistent, compact state summary: unsaved selections, saved selections,
generated configuration and applied configuration. Identify what differs and the
next allowed action. Saving incomplete selections must remain possible. Replace
device-name lists in ordinary replacement reviews with component effects; retain
actual generated diffs and technical provenance behind disclosure.

Acceptance:

- Selecting a known bed definition shows its name and meaningful setting changes
  (for example a supported maximum-temperature difference), rather than requiring
  manual pin or sensor editing. Test definitions supply evidence, not guessed
  third-party hardware facts.
- Replacement review identifies affected components, retained overrides and
  calibration consequences. Cancel changes no draft; confirming changes only the
  draft until explicitly saved. Unrelated calibration remains intact.
- A first-time owner can distinguish “Save selections,” “Generate configuration”
  and “Apply configuration,” and see which state currently matches the printer.
  A saved inactive candidate is never labelled applied or ready to print.
- Incomplete or conflicting input points to the affected component and a useful
  correction; stale reviews require reconciliation. Advanced sensor bias/curves
  remain available without cluttering the normal path.
- Application reviews retain the backend's exact service/restart consequences and
  admission checks. UI tests use disposable state; live application is a separate,
  authorized installed check.

### W4 — Owner-first definition sources

Lead with installed sources and “Add repository.” Preview should report the source,
resolved revision, available definitions and validation result in readable groups.
Use action-specific labels for adding versus updating a source. Keep the starter
ZIP and schema ZIP together under “Create a definition source,” secondary to owner
tasks and available without requiring hardware Advanced mode.

Acceptance:

- A user can paste a repository URL, inspect useful preview counts/details and add
  the source without encountering author tooling first.
- Empty, invalid, offline and incompatible previews explain why no definitions
  are available and retain the entered URL for correction.
- Adding/updating a source does not select hardware or apply configuration.
  Definitions remains read-only, searchable by source/category, with drill-down
  details and the same component icons.
- Imported definitions become discoverable from the relevant hardware selector;
  pinned revision/provenance remain available. Both downloads still work.

### W5 — Updates and software task hierarchy

Present installed release, update status and automatic-update preference before
manual bundle mechanics. Describe running/fallback roles first and expose A/B slot
identifiers as details. Organize manual update as upload → verify → review install
→ select next boot/restart, reflecting actual backend capabilities. Keep manual
exceptions attached to the reviewed operation and automatic advanced checks scoped
to policy; mandatory trust/integrity/layout/idle protections remain unchanged.

Acceptance:

- Opt-in review explains restart and health checking; cancel preserves saved policy
  and useful draft input, confirm persists the reviewed preference across reload.
- A manual update clearly shows which step is complete and the next allowed action;
  users can distinguish upload authentication from full installation verification.
- Opt-out, queued restart, uncertain acknowledgment and fallback produce distinct,
  understandable statuses. No automatic retry is implied when reconciliation is
  required, and no unsafe “bypass everything” action is added.
- Software availability explains writable-mode/idle/storage prerequisites and
  provides the appropriate next step without silently changing operating mode.

### W6 — Access, identity and network clarity

First add or reuse representative successful service fixtures; the current review
fixture cannot establish those journeys. Then refine existing tasks: change
Mainsail access, trust the printer CA, manage SSH keys, back up identity, connect to
WiFi and recover from a connection change. Keep certificate authentication distinct
from trusting the printer's CA and from Cockpit administrator access.

Acceptance:

- Mainsail clearly shows the current method and only the selected method's inputs;
  no-login consequences and client-certificate provisioning order are explicit.
- CA download, client-certificate download and private identity backup have distinct
  names and explanations. Secret material is not copied into UI diagnostics.
- Network leads with current connectivity and the selected interface. Scan/select
  WiFi, missing prerequisites and unavailable operations have clear explanations.
- Connection-change confirmation exposes the rollback deadline and reconnect links;
  disconnect does not falsely indicate failure or success. Preserve backend rollback,
  HTTPS requirements and review freshness. Installed tests require an authorized
  disposable system or specifically approved printer operation.

### W7 — Cross-page accessibility and consistency

Apply during each package, then sweep representative journeys at 1440×900,
1024×600 and 390×844, plus 200% zoom. Standardize action hierarchy, notices,
labelled controls, modal summaries and technical-detail disclosure.

Acceptance: useful heading/focus on route changes; labelled dialogs; keyboard
activation and Escape; focus returned to the trigger; associated field errors;
non-color status cues; no obscured save/review controls or document overflow;
long names, errors and fingerprints wrap safely. Do not claim full accessibility
certification from automated checks.

### W8 — Refresh efficiency

Record existing call counts and update behavior before changing polling. Consider
visibility-aware polling/backoff for passive pages while preserving background
job observation, stale-state detection and pending network rollback feedback.

Acceptance: passive pages avoid unnecessary repeated rendering; focused selects
and drafts survive refresh; operation progress and uncertain results remain timely;
returning to a page refreshes stale data. Any performance claim needs actual
measurements. This package does not authorize new hardware benchmarks.

## Delivery and verification

Use the [task-scoped workflow](ui-ux-workflow.md) and reuse the adoption report.
Ambiguous journey design uses the existing implementer with explicit medium effort
and this skill; settled implementation uses the normal low route. Deterministic
fixture/test execution needs direct commands. Return later execution to a fresh
low worker if needed; do not forward a specialist's full conversation. At most
two children and one active implementation; no permanent review team.

For each package: bind source; select the appropriate existing disposable fixture;
implement; run relevant checks; open rendered evidence; inspect the stable diff;
record limitations; commit/push under coordinator ownership. No new frontend,
browser framework, model policy or backend authorization protocol is needed.

Reuse suites according to affected behavior, not as one mandatory giant campaign:

- Shared host navigation/status: `tests/admin_browser.mjs`,
  `tests/admin_drafts_browser.mjs`, `tests/auto_policy_browser.mjs` and relevant
  controller tests. `scripts/check_ui.py` provides base fixture automation only.
- Hardware, sources, definitions and graph: `tests/printer_browser.mjs` and
  `tests/test_printer_browser_fixture.py`, with composed-shell coverage.
- Operation recovery/history: existing jobs/history/resolution browser suites.
- Identity/access/network/software: existing controller and UI tests, relevant
  browser fixtures, then installed Cockpit checks when authentication or assembled
  behavior changes. Do not interpret stub-service failures as product defects.
- Agent-policy/context/UI-workflow tests only if routing/tooling inputs change;
  reuse matching-revision adoption evidence otherwise.

Completion means applicable outcomes pass and rendered states have been assessed,
with offline versus installed evidence explicitly separated. Changes to physical
outputs, identity restoration, network reachability or recovery retain existing
authorization and consequential-operation gates. The workplan itself is a reviewed
proposal, not evidence that these improvements have shipped.
