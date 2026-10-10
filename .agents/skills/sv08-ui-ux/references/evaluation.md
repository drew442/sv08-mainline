# Author tests; execute them without the skill

Begin with the user's task and the accepted outcome, not implementation selectors.
For example: find installed hardware, understand a component's state, review a
change, cancel without mutation, apply an allowed change, and understand a failure.
Specify only applicable cases; do not impose a new acceptance campaign on every edit.

Reuse `tests/admin_browser.mjs` and the corresponding existing feature-specific
browser/controller tests. The base runner uses Node 22 and Chromium CDP without a
new npm dependency. Add tests to the correct suite rather than duplicating it in a
parallel framework. Hardware-panel changes use `tests/printer_browser.mjs` and
`tests/test_printer_browser_fixture.py`; follow the existing shared-panel recipe
with assigned paths, not copied historical workstation paths. A concrete selector can drive a test, but its assertion should
establish the intended result, feedback or absence of unintended mutation.

For an affected journey, select relevant checks for keyboard focus/activation,
Escape/cancellation, associated labels and understandable errors, preservation of
unfinished input, responsive overflow, and loading/empty/unavailable states. Cover
stale reviews and real controller state when mutation is involved. Screenshot
capture alone is not an assertion. Automated accessibility checks do not establish
complete accessibility conformance; do not claim WCAG certification from this suite.

## Two separate judgments

**Deterministic:** run the authored checks, retain exit status and result JSON,
capture screenshots/logs and identify the exact source bytes. No design skill or
high-effort model is required. Use `scripts/check_ui.py` for the existing base
fixture; run relevant feature-specific/installed recipes separately.

**Skilled:** open representative screenshots or interact with the disposable UI.
Can a first-time owner identify the page's purpose, important status, next action,
consequences and recovery without knowing Linux or the internal schema? Inspect
hierarchy, grouping, language, focus visibility and layout at supported sizes.
A model's evaluation is a useful self-check, not measured human usability. Record
uninspected states and any need for actual user acceptance separately.

Return a small finding per real defect: acceptance ID/user task, observed behavior,
expected outcome, severity/consequence, screenshot or reproduction reference, and
smallest useful correction. Infrastructure failures go to existing integration
triage; an assertion failure is not automatically a design failure. Cosmetic preference
alone does not justify scope expansion or higher-effort independent review.

After a correction, rerun checks whose inputs changed and required acceptance checks.
Do not repeat identical successful work or blindly accept new golden screenshots.
Carry the same unresolved failure's attempts/budget through handoffs. Missing visual
evidence stays unassessed; stop the affected completion claim rather than inventing
approval. A routine implementer can assess its own reversible UI work.
