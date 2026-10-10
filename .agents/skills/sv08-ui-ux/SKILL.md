---
name: sv08-ui-ux
description: Design, implement, author UX tests, or assess rendered SV08 web UI in an assigned skilled phase. Not for provisioning, executing existing tests, logs, Git, or unrelated work.
---
# SV08 UI/UX skilled work

Use only when explicitly assigned this skill. Apply AGENTS.md and the existing
role/ownership/budget contract; this skill does not select a model, grant a new
role, authorize hardware, or add an independent review stage.

Start with the handoff's user task, acceptance IDs, source fingerprint, owned files
and relevant evidence. Do not load the coordinator guide, all Cockpit sources or
hardware history as onboarding. Read [Cockpit constraints](references/cockpit.md)
only for affected host UI; read [evaluation](references/evaluation.md) when creating
tests or judging rendered outcomes. Do not read both merely because they exist.

## Design and implementation

Define who is using the page and what they are trying to accomplish. Organize
around their tasks, not schemas, services or internal object names. Use familiar
labels and labeled outline icons, obvious primary actions, consistent components,
short contextual explanations and advanced details on demand. Preserve existing
technology; a new frontend stack is not a usability improvement by itself.

For a substantial journey, write a compact acceptance sketch before editing:
entry point, useful status, action, consequence, feedback, cancellation and error
recovery. Reuse existing accepted designs. A routine specified correction needs no
new persona document, mockup, planner or separate UX reviewer.

Implement the assigned design and meaningful outcome-based tests. Include relevant
loading, empty, unavailable, failure and stale-state behavior. Support semantic
controls, keyboard focus/activation, readable labels and supported viewport sizes.
Never hide a safety consequence or enable unavailable behavior to simplify a page.

## Evaluate and return

Inspect actual rendered evidence for changed visual journeys; a screenshot filename
or a green automation result is not a usability assessment. State what was inspected,
which user task succeeds, remaining confusion, acceptance gaps and evidence paths.
Keep failed checks; fix the behavior or explain a demonstrated test defect. Do not
weaken assertions, update visual baselines blindly or substitute mock behavior for
required installed acceptance.

Return the patch/design, test commands, exact evidence references, findings and next
required stage. Long logs and full screenshot collections stay out of the handoff.
Once judgment is complete, return execution to deterministic tooling/coordinator.
Carry unresolved failures and cumulative allowances forward. Higher effort, new
workers and publication remain coordinator decisions, never actions of this skill.
