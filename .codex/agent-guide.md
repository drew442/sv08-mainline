# Project subagent guide

Choose responsibility, reasoning effort and permissions separately. The coordinator
owns selection, records, resource allocation, authorized hardware operations and
publication. Roles are invoked for useful work, not a mandatory assembly line.
The [benchmark assessment](../docs/development/codex-model-routing.md) justifies
Sol low as the normal engineering default; it is not evidence of a deployed client
or of hardware safety. Do not load that assessment in every child context.

## Role selection

| Agent | Model | Default effort | Assignment / escalation |
| --- | --- | --- | --- |
| `project_lookup` | GPT-6 Luna | medium | Exact lookup/extraction; no causal analysis or planning. |
| `project_narrow_implementer` | GPT-6 Luna | medium | Mechanical edits with a supplied transformation/check; semantic fixes go to Sol. |
| `project_researcher` | GPT-6.1 Sol | low (adjustable) | Source tracing and bounded diagnosis; medium for cross-system evidence, high for a specific hard unknown. |
| `project_planner` | GPT-6.1 Sol | medium | Optional scope/design/acceptance planning; triage only when useful, never self-approval. |
| `project_implementer` | GPT-6.1 Sol | low (adjustable) | Normal substantive implementation; medium for difficult implementation reasoning. |
| `project_integration` | GPT-6.1 Sol | low (adjustable) | Bounded installed checks and reproduction; medium for cross-system diagnosis. |
| `feature_approver` | GPT-6.1 Sol | medium | Separate approval of new substantive scope; reuse valid existing approval. |
| `feature_verifier` | GPT-6.1 Sol | medium | Separate delivery review of full diff and evidence. |
| `feature_verifier_high` | GPT-6.1 Sol | high | Same delivery review with difficult recovery/concurrency/security reasoning. |
| `high_consequence_reviewer` | GPT-6.1 Sol | medium | Separate exact-operation review immediately before consequential action. |
| `high_consequence_reviewer_high` | GPT-6.1 Sol | high | Same operation review when material uncertainty needs deeper reasoning. |

Low is not a tiny-fix exemption. Use it for bounded substantive coding with settled
requirements and meaningful tests, including offline recovery/storage modules.
Select effort for reasoning difficulty, not file size or subsystem name. Select
review strength for consequences and uncertainty. Select execution permissions
from actual authorization: no worker profile may operate the printer. An approved
fixture patch is not an approved physical write or change to owner requirements.

Prefer direct scripts for predetermined searches, hashes and test recipes. Luna
is for easily checked transformations, not an obligatory first attempt at hard
coding. Do not add a Luna-high rung. Choose medium directly for known difficult
work; choose high for an identified unresolved reasoning problem, not unavailable
physical evidence. Xhigh/max or another model need an explicit bounded assignment
and usage allowance; no standing role or routine escalation is justified by these
charts. No Astra worker, speed mode or billing-account change is introduced.

## Native model/effort configuration

[Project settings](config.toml) set default spawned agents to Sol/low, including
built-in workers that would otherwise inherit an expensive coordinator. They do
not select the main session's model. Generic workers are not formal reviewers.

The three adjustable profiles pin `model = "gpt-6.1-sol"` and intentionally OMIT
`model_reasoning_effort`. The supported precedence for effort is the profile's
value (when present), explicit spawn effort, project agent default, then parent.
Thus an explicit medium/high spawn effort works for these three profiles; omitted
effort resolves to the project low default. Always record the requested and actual
setting. A prompt saying "think harder" is not proof of an effort override.

Planner, Luna and review profiles explicitly pin effort. Spawn arguments cannot
change their pinned values. Use the named high verifier/action-review variant,
not a high request on its medium profile. For any exceptional pinned-role change,
use a separate supported session with the full role contract and verified settings;
never silently substitute a different model or review tier.

This follows the official [subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
checked 2026-09-30. Check actual role loading, model/effort and effective permissions
in a fresh source-only client before deployment. Named profiles, adjustable effort
and agent defaults need runtime evidence; local TOML tests cannot establish them.
If unsupported, use an explicitly configured separate session with the same
contract, or leave that assignment pending. Record any fallback; it is not a Sol
6.1 result. Unavailable independent review blocks acceptance/action, not unrelated
authorized offline work. Never edit user-global config to conceal a launch failure.

## Execution policy and bounded self-service diagnostics

The owner requested full-access execution with strict role and cost boundaries;
see the [execution decision](../docs/decisions/20260930-agent-execution-and-diagnostics.md)
and [deployment checks](../docs/development/agent-execution.md). This supersedes
historical read-only-runner requirements, not project, hardware or acceptance rules.
Project settings select `approval_policy = "never"` and
`sandbox_mode = "danger-full-access"`; role files inherit that execution policy.
Full access is capability, not permission to take over another role. User-global
configuration, managed policy and live parent overrides still require inspection.

Each worker may perform supporting diagnostics necessary for its assigned question.
Lookup may create small extraction/comparison scripts, but not causal analysis.
Research may run minimal reproductions or targeted compilation, but not implement
production changes. Planning may test feasibility, but not implement or self-approve.
Integration may adjust its own disposable inputs/invocation, but not production
code, tracked tests or acceptance criteria. Reviewers may reproduce checks against
the unchanged submitted candidate, but not repair it or perform the reviewed action.
Implementers retain only their explicitly assigned tracked-file ownership.

The coordinator allocates a unique scratch directory before launch, normally
`local/feature-workflow/probes/<task-id>/<attempt-id>/` outside the candidate
worktree. No additional permission request is needed for qualifying diagnostics.
A missing scratch assignment is a coordinator handoff, not permission to use shared
build directories. Scratch scripts, inputs, output, temporary files and caches stay
inside the assigned directory; do not change host setup, install packages, use
physical devices, restart services or mutate remote hosts under this allowance.
Use installed tools and approved existing fixtures. Effects, not command length,
determine eligibility. Do not execute untrusted downloaded installers as a probe.

| Auxiliary diagnostic limit | Default per assigned question/task lineage |
| --- | --- |
| Experimental runs | 2 total: initial probe plus one corrected/discriminating follow-up |
| Execution time | 300 seconds cumulative elapsed process runtime across all probe runs |
| Generated data | 256 MiB cumulative, including scratch inputs, logs, outputs and caches |
| Additional agents, model/effort/billing changes | None initiated by the worker |

These are initial operating allowances, not native Codex config keys or hard
spending caps. Multiple commands can be one named experiment, but hiding repeated
experiments in a script is not a way around the limit. Use command timeouts no
larger than remaining time, bound output and stop before a known overrun. Unknown
resource needs require a larger assigned fixture/budget, not an unbounded probe.
Do not split or rename a question, delete outputs, spawn a CLI session or change
workers to reset cumulative accounting. Record probe ID, commands, results and
usage in the existing handoff/observation; a handoff carries remaining allowance.

These limits cover incidental questions, not the explicitly budgeted primary task.
A long assigned build/test or substantive review needs its own execution allowance.
For a known expensive reproduction, select integration directly. Ordinary reading
and source tracing remain within the primary-task budget. Exhaustion returns
`needs-escalation` with evidence and the smallest next action; do not claim an
incomplete check passed. Keep formal approval/verification JSON schemas unchanged.
The coordinator grants bounded continuations within standing owner authorization,
records the reason and cumulative usage, and does not ask the owner repeatedly
when that authorization is already sufficient.

Keep model/effort changes, additional agents, shared-record updates, commits,
publication and printer operations with the coordinator. Child profiles disable
native multi-agent tools with `[agents] enabled = false`; workers also must not
start other agents via shell, CLI or API. This is not a hard shell restriction.
A permission/startup failure is a runner issue, not a reason to spend more tokens
retrying with higher effort. One diagnosed repair cycle applies to the same
unresolved failure, not to every distinct defect in an implementation. A new
assignment or review-driven repair keeps the earlier attempt history.

Existing authentication may be used only for explicitly assigned development-host
connections and resources. Using an approved connection is not permission to read,
copy or disclose private keys, tokens, passwords, raw dumps or private backups.
Printer/board/media access is not a generic development connection; even read-only
printer commands remain coordinator-owned under existing hardware authorization.
These are conduct and acceptance rules, not enforced secret/device isolation.
Hard prevention or spending guarantees require controls outside the full-access
worker. Do not claim that worktrees, prompts, tests or token tracking provide them.

Before accepting results, the coordinator checks complete candidate/source diffs,
tracked-file ownership, untracked files, deletions, modes and gitlinks against the
recorded baseline. Researchers/reviewers must leave the candidate unchanged.
Never repair or automatically revert another worker's changes to make this check
pass. Preserve offending changes/evidence and reconcile ownership. Scratch evidence
must be sanitized and promoted by the coordinator before it becomes public evidence.

## Handoffs, evidence and bounded retries

Give one task packet, not the full conversation or all project documents:

```text
Task/outcome and existing authorization/acceptance IDs:
Role; requested model/effort; reason for non-default effort:
Revision, relevant paths/evidence and existing results to reuse:
Owned tracked files/worktree OR unchanged candidate; assigned resources/ports:
Scratch directory; question/attempt lineage; remaining diagnostic allowance:
Assigned development connections/authentication use, or none:
Known facts, uncertainty, consequence of error and exact next question:
Completion checks; primary-task execution allowance; escalation/stop conditions:
Prior probes/attempts and cumulative usage; baseline candidate state:
Expected result; shared human dependency IDs and offline alternatives:
```

Read AGENTS.md and the applicable accepted requirements before behavioral changes.
Keep stable policy references compact and task-specific results bounded. Reuse
valid unchanged evidence, not stale conclusions. Parent and child must confirm
role/model/effort and permissions at launch; record unavailable observations as
unknown, never invent them. Workers return status (done/blocked/needs-escalation),
source revision, changed paths, commands/results, evidence limitations and the
smallest next action. Formal decisions/verifications keep their existing schemas.

Use the diagnostic and same-failure repair limits above. Persistent failure,
design ambiguity or scope growth returns to the coordinator with the actual
patch/evidence; preserve useful work instead of restarting. Missing hardware facts
require observation, not extra reasoning. A slow build uses its existing handle.

## Review independence and workflow

Use the existing [feature workflow](README.md). Existing approved work needs no new
product approval. For new substantive scope, use a planner only when needed, then
a separate approver, implementation, necessary execution evidence and independent
verification. Small mechanical fixes to documented behavior use the short record
and normal review; low effort alone never qualifies for that exception.

The planner/proposal author cannot approve their own proposal. The implementer,
planner of that delivery and integration evidence producer cannot verify their own
delivery. A researcher whose design/fix was adopted counts as an author. Use fresh
review sessions with source and evidence, not inherited author conclusions. An
approver may not be reused as the delivery verifier: avoid reviewing its own earlier
acceptance judgment. The verifier may reproduce checks in an authorized disposable
environment under its assigned allowance, but cannot repair the submitted code.
Reproducing a check as verifier does not make that session an implementation author;
adopting its proposed production repair does, and requires a fresh verifier.
Separate sessions reduce shared assumptions; they do not prove statistical independence.

Choose medium OR high verification, not both as routine stages. High verification
is warranted by subtle irreversible-state, concurrency or security reasoning or an
unresolved material review issue. If a medium review needs escalation, transfer its
findings to the high reviewer and preserve the failed/pending result. Never count
a same-author rerun as independent acceptance. Approval and verification contracts
remain unchanged, including full-diff, source/decision/evidence hash checks.

Immediately before eMMC/MCU writes, boot-policy changes, heater/motion commissioning
or release decisions, obtain a separate high-consequence review of the exact target,
artifact, action and checks. Use the high variant directly when material uncertainty
is known. Code verification does not replace this action review, owner authorization
or execution evidence. Unresolved physical facts still stop the operation at high.

## Resources, measurement and migration

Keep one implementation active and at most two open children. A research/review
child may accompany independent useful work; do not launch idle roles. Only one
owner uses a QEMU image, port, build tree or physical task at a time. Worktrees do
not isolate credentials; full-access roles follow the execution contract above.
Parent runtime settings can override project defaults; verify the effective mode.
Send physical dependencies to the coordinator's existing human queue, not directly
to the owner. Continue eligible offline work while a physical dependency waits.

Keep lightweight routing observations in task handoffs/results. Use the detailed
[observation template](templates/agent-task-observation.md) for escalations, failures
and representative samples, not as an extra agent stage. Count coordinator, children,
rework and reviews through acceptance; unknown usage stays unknown. Monitor accepted
outcomes and latency after rollout rather than requiring an easy-task-only pilot.

Migration from the first draft:
- `feature_suggester` becomes `project_planner` for planning as well as optional triage.
- `project_routine_implementer` is absorbed into the normal adjustable `project_implementer`.
- `project_test_runner` is removed: direct script first, `project_integration` when judgment is needed.
- `project_lookup` separates Luna extraction from Sol investigation; `feature_verifier_high` adds explicit deeper delivery review.

Update live assignments to the current names/settings; these are mappings, not
runtime aliases. Stop/close old workers and restart clients that cache removed
roles before dispatching new work. Preserve active worktrees and all historical
review identities, decisions, source hashes and acceptance records. Older plans
naming Sol or removed roles retain scope/dependencies but use this routing on the
next assignment. The coordinator remains the only queue/Git writer. Role changes
do not start a scheduler, an agent server, an automatic router or hardware work.
