# Printer Hardware journey delivery evidence

## Before and after

Baseline `6d6e2a6ce12e944567c8209194c50bc8c3cf811a` was clean, with the previous native goal complete and no running/review/validated source task conflict. Main remains unchanged. Draft tools hid saving and change navigation; application/candidate state was low in the footer. The populated composed-panel baseline was inspected before scope selection.

The page now shows saved/unsaved selections, a prepared inactive configuration and honest application status together. Owners can expand known attention items to reach the affected component, answer selected-definition questions before browsing replacements, save incomplete drafts, and understand what cancellation retained. Direct input edits update labels, change counts and the next action without replacing the focused control. Calibration, backend protections and live configuration operations are unchanged.

- [Before: populated hardware view](visuals/before.png).
- [After: configuration summary and attention](visuals/after-desktop.png).
- [After: selected component questions on a phone](visuals/after-mobile.png).

These are sanitized offline fixture captures, not visual baselines or installed-printer evidence. Desktop summary is 1280×900; selected questions are390×844. Representative files deliberately show different stages; automated viewport coverage below is broader. No private production configuration or credentials are included.

## Acceptance and validation

| Check | Observed outcome | Evidence |
| --- | --- | --- |
| PHJ-1 | Saved/unsaved, changed-component count and inactive/unknown state visible; direct edits update the next action. Reload never implies active printing readiness. | Final composed and ordinary-view browser outcomes; rendered summary. |
| PHJ-2 | Missing sensor, missing required answer and definition-author gap distinguished; links reach relevant fields. Filled/cleared labels follow input without focus loss or losing another unsaved answer. | Separate gap definition retains original dependency hashes; exact label/focus/draft/live-byte assertions. |
| PHJ-3 | Selected questions precede alternatives; ordinary viewing remains inspectable with writes disabled. | Actual targeted questions/sensor captures, DOM order and unchanged-state/RPC assertions. |
| PHJ-4 | Effects, calibration/override consequences and exact backend service action retained; selecting does not apply. | Existing replacement checks, generated/application review captures; original live bytes unchanged. |
| PHJ-5 | Incomplete draft saves/reopens. Review cancellation does not mutate; application cancel and Escape retain the already saved inactive candidate, preserve saved/live bytes, restore focus. | Final browser assertions and actual cancellation receipts. |
| PHJ-6 | Busy, stale, refusal and lost-ack reconciliation preserve protections and truthful unknown status. | Existing stale/session/lost-ack journeys plus actual publication refusal; no false confirmation. |
| PHJ-7 | Keyboard links are visible before Enter activation; initial first component stays visible;1440×900,1024×600,390×844 and200% zoom/reflow have no document overflow. | Browser assertions and actual responsive/reflow captures; vertical scrolling remains expected. |

Final source-bound receipts are in [evidence.json](evidence.json). All executed final runs report exit0 and unchanged source before/after; the JSON preserves earlier passing and failed receipts without refreshing their hashes.

Commands executed from the assigned candidate worktree:

- Node22 `tests/printer_browser.mjs <assigned Chromium wrapper> <private fresh fixture> <assigned output>`: full composed-panel journeys passed. Fixture is `tests/test_printer_browser_fixture.py`, actual Store/Budget and pinned installed software parser inputs; fresh data for each run.
- Same Node/Chromium tooling with `tests/config_view_browser.mjs`, populated `SV08_CONFIG_VIEW_FIXTURE=1`: ordinary read-only configuration journey passed, state bytes unchanged.
- `python3 -B -m unittest discover -s tests -p test_stage_printer_ui.py -v`:12passed on final UI.
- Same command for `test_stage_admin_ui.py`:20passed on final UI, including composed refresh.
- Same command for `test_config_view.py`:11passed; reused that receipt after checking unchanged relevant runtime/test inputs. Total43applicable standard tests.
- `node tests/printer_navigation.mjs`:passed; reused unchanged navigation inputs. JavaScript syntax and `git diff --check` passed; final code and authored assertions were inspected.

No unchanged OS images, browser frameworks or tools were built/installed. Node22.23.2 and Chrome for Testing145.0.7632.6 were already installed. `scripts/check_ui.py` was not substituted for Printer Hardware coverage. Native/physical acceptance was not required or performed.

## Repairs and rendered assessment

Retained failures: (1)new summary pushed the initial first component below the viewport; compact label/value rows and attention disclosure fixed it without weakening the assertion. (2)Adding an author gap to an existing example invalidated its assembly dependency SHA; a separate gap fixture now preserves original supported drill-down checks. (3)Chromium exited before DevTools startup; cause was not proven. With substantial unrelated shared-memory usage observed, an assigned file-backed-memory wrapper passed. No unrelated processes/data were touched.

Actual image inspection found initial targeted screenshots only showed the header; focused captures now show selected questions, the author gap, sensor adjustment and cancellation. The corrected captures then exposed a stale required-answer label; an in-place update and outcome assertions corrected it. Previous failures and misleading transitional captures remain in local evidence and are not presented as final success.

The same skilled named implementer inspected the actual baseline, dialogs, targeted final captures, summary viewports and zoom/reflow controls, then reported PHJ-1–7 met for this bounded offline scope. Coordinator inspected the stable source diff, receipts and representative renders. No independent reviewer was required or fabricated.

## Agents, adoption reuse and resource accounting

One actual `project_implementer` child, fork_turns=none, requested explicit medium effort; runtime thread metadata observed `gpt-6.1-sol`/medium, CLI0.162.1, thread `01a12a89-23a1-7491-beb9-8774825ead36`. Related skilled design/implementation/tests/rendered judgment stayed with it. Ordinary execution, provisioning, logs, Git and publication ran directly through coordinator tools. No generic substitute, nested agent or permanent team was created; one active implementation.

The child explicitly read the repository `sv08-ui-ux` skill body and relevant references, retaining only task-scoped work. Coordinator arranged delegation without loading its body. Native activation and hidden-context completeness remain unobserved. Worker process usage under2seconds, no incidental experiments or generated fixture data; browser/testing work was coordinator-owned.

Adoption evidence reused from `/home/drew/.sv08-codex-adoption-20261010/report.md` and its intake/results/source-hashes/runtime/probe/test companions, located through the existing workplan handoff. All recorded input hashes still match. The18policy,9context and24UI-workflow checks were reused; the adoption audit was not repeated. Other profiles remain not exercised here; no measured model quality, savings or hidden-context guarantee is claimed.

Private scratch/evidence: `/home/drew/.sv08-printer-journey-20261011`; exact assigned worktree is in execution receipts. Initial free space32GiB. Primary runtime1800seconds, with a conservative600-second reservation for earlier uninstrumented setup and cumulative instrumented process totals in JSON. Initial output ceiling256MiB was continued to512MiB under existing coordinator safe-development authority to conservatively cover removed staging fixtures across distinct repairs; no counters/reset or new spending. Retained bytes and measured deleted browser profiles are recorded; cumulative temporary logical writes were not fully byte-instrumented. Incidental limits remain separate; one root infrastructure diagnosis, under300seconds/128MiB, no worker experiments.

## Limits and deferred work

Browser transport/session is a Cockpit shim with real generation-local storage, not authenticated installed Cockpit/PAM or hardware qualification. Successful-publication confirmation is source-reviewed only: the fixture deliberately refuses publication admission. No printing release, human usability study, accessibility certification or deployment is claimed.

Authoritative applied/active status, comprehensive backend-validator-to-field navigation and catalogue restructuring remain deferred in the existing [bounded proposal](proposal.md). Known attention supplements the backend validator; it does not certify completeness.

The delivery goal ends at a published review PR. The source task stays **validated awaiting owner integration**; it is not marked integrated/deployed and no PR is merged.
