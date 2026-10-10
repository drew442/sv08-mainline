# Cost-aware UI/UX development

This workflow implements the owner's requested division: disposable environment →
skilled design/implementation and UX checks → standard project checks → publication.
It extends existing roles and recipes, not the agent roster or feature state machine.
No broad UI redesign, new frontend stack, mandatory reviewer or hardware authority
is introduced. Follow AGENTS.md and the current self/targeted/consequential policy.

## Dispatch by phase, not by the feature's UI label

| Phase | Execution / existing role | UX skill |
| --- | --- | --- |
| Prepare an existing disposable environment | Direct script; `project_integration` low only for actual troubleshooting | No |
| Design a new or ambiguous user journey | `project_implementer` with explicit medium effort; optional `project_planner` for a concrete design-only need | Yes |
| Implement a settled pattern or ordinary change | `project_implementer` low; medium for hard choices | Only the relevant guidance; none for a fully specified mechanical patch |
| Exact mechanical edit with a direct check | Existing `project_narrow_implementer`, unchanged Luna/medium | No |
| Author meaningful UX tests | Existing implementer, low for established patterns, medium for ambiguous coverage | Evaluation reference as needed |
| Run defined tests, collect logs/screenshots | Direct commands; no new child merely to relay them | No |
| Assess rendered usability, choose corrections | Existing implementer; medium for ambiguous visual/task decisions | Yes |
| Run standard checks; commit/push/create PR | Direct commands under coordinator ownership; integration low for diagnosis | No |

Keep the accepted `gpt-6.1-sol`/low default, adjustable implementer effort, existing
Luna role and two-child cap. High effort is for a specific unresolved reasoning
problem, not all frontend work. Skill selection and model selection are separate.
The coordinator requests effort at a supported spawn/session boundary; it must not
expect a skill or a natural-language instruction to change an existing worker's
model. Check observable runtime settings; unknown stays unknown, with no silent
fallback or global config/billing changes.

For a resumed medium/high worker, do not assume a new low-effort handoff de-escalates
its session. Use a supported verified setting change or close it and dispatch the
remaining bounded work through the existing low-effort route. Workers never launch
agents or alter their own model. Pure execution generally needs no LLM at all.
Do not move the entire coordinator to a different model just for this workflow.

## Context boundaries

The coordinator explicitly includes `$sv08-ui-ux` only in a skilled assignment.
The native skill is in `.agents/skills/sv08-ui-ux/`; its sidecar disables implicit
invocation. Where a client cannot invoke a repository skill in a child handoff,
explicitly assign reading that `SKILL.md` to that skilled worker only. Do not copy
it into AGENTS.md or every role as a compatibility workaround.

Skill discovery may still expose its short name/description to other turns.
This is a small metadata cost, **not zero overhead**. The body and references are
on demand. Do not load the skill to decide whether provisioning/testing/Git needs it.
Do not forward a specialist's full conversation, design documents, browser profiles
or long logs to an execution worker. Request task-scoped context where the client
supports it; inherited parent context can reduce the expected savings. Static file
checks cannot establish live context loading, model routing or monetary savings.

## Execute a bounded UI cycle

Choose the smallest **existing** disposable target that meets acceptance. Reuse the
loopback controller fixture for ordinary web UI; use the existing installed
Cockpit/QEMU recipes when session, elevation or assembled behavior is relevant.
Do not rebuild an unchanged OS image for every CSS iteration. No printer access,
host installs or service changes are authorized by invoking this workflow.

Use the coordinator-assigned disposable checkout for generated scratch, not a
frozen review candidate. Bind copied inputs to the exact candidate source hashes.
For the base browser journey, inspect the command plan, then execute it:

```sh
python3 scripts/check_ui.py --work build/ui-ux/iteration-01
python3 scripts/check_ui.py --work build/ui-ux/iteration-01 --execute
```

The wrapper uses installed Node 22/Chromium, `scripts/preview_admin_ui.py` and
`tests/admin_browser.mjs`. Override executable paths with `--node` and `--chromium`
when required. It provisions fresh disposable policy state for each run, because
the existing tests mutate that state. It does not provision a complete OS image or
replace other browser suites. For interactive design, the existing preview command
in [the fixture guide](../hardware/host-admin-ui.md) remains available; the
coordinator owns its process handle and cleanup.

The run's `summary.json` references source hashes, result JSON, screenshots and logs;
large profiles remain local. The wrapper limits elapsed execution and checks an
output allowance (`--timeout 180 --max-output-mib 256` by default), then terminates
only its owned process groups on success/failure. The periodic size check is not a
filesystem quota and can overshoot between checks. These are primary test allowances,
not a reset of the incidental two-experiment/300-second/256-MiB lineage budget.
No dependency is downloaded and no model, commit, push or merge is invoked.

Do not edit the candidate while a check runs. Before/after hashes cover the base
fixture's UI/runtime/test inputs, including untracked source; a change invalidates
the run. This is a consistency check, not an immutable snapshot or a complete
repository/release attestation. Keep the exact candidate and relevant additional
inputs bound to the normal feature evidence.

A passing summary means **base browser automation passed**. It explicitly leaves
visual assessment, standard project tests, installed Cockpit and hardware unproved.
The skilled worker opens the relevant screenshots or disposable UI and records its
assessment. Run additional feature-specific browser checks selected by the actual
change; do not infer coverage from the base suite's success.

## Iterate, validate and publish

Route fixture startup/tool failures to deterministic repair or integration low.
Route semantic assertion failures to the implementer and ambiguous user journeys
to skilled evaluation. Never weaken a test to get green or send every failure to
high effort. Reuse unchanged evidence, stop when all applicable criteria are met,
and retain attempts/remaining budgets across sessions. The existing one diagnosed
repair cycle concerns the same unresolved failure, not all defects in a delivery.
A bounded continuation requires a coordinator reason; there is no arbitrary mandatory
three-review loop or new automatic approval gate.

Then run the relevant standard `sv08-mainline` tests. UI tooling changes include:

```sh
python3 -m unittest discover -s tests -p 'test_ui_workflow.py' -v
python3 -m unittest discover -s tests -p 'test_agent_context.py' -v
python3 -m unittest discover -s tests -p 'test_codex_agent_policy.py' -v
```

For hardware-panel work, reuse `tests/test_printer_browser_fixture.py` and
`tests/printer_browser.mjs` with the [shared-panel recipe](printer-cockpit-panel.md)
and coordinator-assigned paths. The base wrapper does not cover that composed
panel; a passing base result is not printer-page coverage.

Product changes additionally run their existing controller/runtime and feature
checks; unit mocks do not replace required installed journeys. Inspect the full
stable diff and applicable acceptance evidence. The coordinator records actual
validation using the existing workflow, commits/pushes and creates the PR according
to existing authority. Creating a PR for review is not permission to merge it.
No child acquires Git/publication rights; no historical records/hashes are refreshed
to make validation pass. Consequential operations retain their independent gate.

## Compact handoff and adoption

Extend the existing handoff, not a second task-record schema:

```text
Phase; user task/acceptance IDs; owned files; worktree/source fingerprint:
Role; requested effort and reason; explicit skill or none:
Fixture/artifact paths; selected check commands; actual results:
Screenshots to inspect; assessment/findings or not assessed:
Unresolved failure/attempts; remaining primary/incidental budgets; active handles:
Next required phase; standard/installed/hardware checks still outstanding:
```

Use the existing observation form only where useful. Record actual context/usage,
retries and accepted outcomes during normal work, not a duplicate benchmark campaign.
Retain cheap execution and proportionate self-validation. Before adoption in a
cached client, verify explicit skill loading, no implicit invocation, effective
medium/low assignments and returned execution context on one normal source-only task.
This PR's static tests do not claim those live observations happened.

Configuration basis: [OpenAI skills](https://learn.chatgpt.com/docs/build-skills)
and [subagent setting precedence](https://learn.chatgpt.com/docs/agent-configuration/subagents),
checked 2026-10-10. Repository model policy remains the source of defaults; newer
generic documentation is not authorization to replace the accepted routing.
