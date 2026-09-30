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

## Handoffs, evidence and bounded retries

Give one task packet, not the full conversation or all project documents:

```text
Task/outcome and existing authorization/acceptance IDs:
Role; requested model/effort; reason for non-default effort:
Revision, relevant paths/evidence and existing results to reuse:
Owned files/worktree OR read-only scope; permitted commands/fixtures/ports:
Known facts, uncertainty, consequence of error and exact next question:
Completion checks, execution allowance, escalation/stop conditions:
Expected result; shared human dependency IDs and offline alternatives:
```

Read AGENTS.md and the applicable accepted requirements before behavioral changes.
Keep stable policy references compact and task-specific results bounded. Reuse
valid unchanged evidence, not stale conclusions. Parent and child must confirm
role/model/effort and permissions at launch; record unavailable observations as
unknown, never invent them. Workers return status (done/blocked/needs-escalation),
source revision, changed paths, commands/results, evidence limitations and the
smallest next action. Formal decisions/verifications keep their existing schemas.

A clear focused failure permits one bounded repair cycle within the assignment.
Persistent failure, design ambiguity or scope growth returns to the coordinator
with the actual patch/evidence; do not pay for a full restart or repeated unchanged
attempts. Escalation changes effort or assignment, not authorization. Review-driven
rework is a new bounded assignment. Missing hardware facts require observation,
not extra reasoning. A slow build requires waiting on its existing handle.

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
environment, but cannot repair the submitted code. Separate sessions reduce shared
assumptions; they do not prove statistical independence.

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
not isolate credentials. Enforce sandbox/private-backup/credential/device exclusion
in the execution environment; parent permissions may override profile defaults.
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
