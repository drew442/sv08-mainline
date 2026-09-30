# Full-access execution with role-preserving diagnostics

Date: 2026-09-30. Status: owner-authorized for implementation in a follow-up PR;
independent review and target-client deployment checks remain required.
Base: merged routing PR #1, `c056b4ec59ca5f0227a6eff133e0484812322b26`.

## Decision and authority

The owner requested autonomous YOLO operation, then clarified that agents must
retain their roles and cost controls while answering small supporting questions.
The owner explicitly requested a PR implementing that recommendation. This is
execution-policy authorization, not evidence that a live client has been tested.

Use project `approval_policy = "never"` and `sandbox_mode = "danger-full-access"`.
Named roles inherit execution permissions; their model/effort routing is unchanged.
Child profiles disable native delegation with `[agents] enabled = false`. Role
instructions also prohibit starting agents through shell, CLI or API, self-changing
models/effort/billing, or expanding their own task allowance. Only the coordinator
allocates work, extensions, shared resources and model/effort changes within the
owner's existing authorization. No new agent, router, scheduler or billing change
is introduced. Do not alter user-global configuration to hide a launch failure.

The [agent guide](../../.codex/agent-guide.md) is the shared role and diagnostic
contract. Roles may use assigned scratch space to answer necessary supporting
questions without taking over adjacent deliverables. Research remains diagnosis;
planning remains planning; integration does not repair production code or tracked
tests; reviewers do not modify or repair the submitted candidate. The coordinator
retains shared records, candidate commits, integration, publication and printer
operations. Existing independent review, hardware authorization, target identity,
recovery and heater/motion checks remain in force.

Default incidental allowance per question/task lineage: two experiments, 300
seconds cumulative elapsed process runtime, and 256 MiB cumulative generated data,
including inputs, output, logs and caches. These are initial operating limits, not
native Codex spending controls. The coordinator assigns the scratch directory and
primary-task budget, and carries remaining allowances across handoffs. Renaming,
relaunching or deleting files never resets accounting. Exhaustion produces an
actionable handoff, not self-escalation or a false passing result. Larger primary
builds/tests/reviews require separate assignments; these defaults do not truncate
required acceptance checks. One repair cycle concerns the same unresolved failure,
not every distinct failing test in a legitimate implementation.

Existing authentication can be used for specifically assigned development-host
connections without inspecting or exposing credential material. This does not
permit reading private backups or device dumps, contacting other hosts, or treating
printer access as a development connection. Even read-only printer commands remain
coordinator-owned. Do not expose keys, tokens or passwords in logs or commits.

## Supersession and unchanged boundaries

This decision supersedes only the restricted-execution requirements in
[decision 0011](0011-feature-agent-workflow.md), the original
[framework design](../design/feature-agent-framework.md), and the historical
[workflow validation](../development/feature-workflow-validation.md), including
its instruction not to substitute a full-access reviewer. Those texts describe
the earlier offline-pilot/isolation policy, not a requirement to re-sandbox current
reviewers. Their historical observations and evidence remain valid at their stated
revision and scope; do not rewrite their identities, decisions or hashes.

The current operating guides refer here for execution. Offline-only dispatch,
the single active implementation/review slot, two-child cap, primary queue writer,
worktree ownership, formal schemas, approval freshness and acceptance gates remain
unchanged. Scratch data is not public workflow evidence. The public-path defect is
fixed by explicitly admitting the three versioned `.codex` root configuration and
guide files, not by admitting arbitrary private `.codex` content.

Changing a requirement document can invalidate a pending approval through its
existing digest checks. Preserve that behaviour and obtain a genuine bounded
review against the changed requirements where needed. This decision is not a
hash-refresh shortcut and does not reopen completed historical evidence.

## Enforcement and validation limits

Full-access execution removes Codex sandbox and approval friction; it does not
provide enforced isolation between roles. Instructions, Git checks, tests and
disabled native delegation do not prevent an unrestricted shell from doing other
work. Hard secret/device protection or spending limits require controls outside
the worker. Report effective permissions rather than claiming a sandbox exists.

Before deployment, follow [agent execution checks](../development/agent-execution.md).
Deterministic tests cover configuration contracts and workflow path admission;
live role adherence, permission inheritance and effective model settings need
separate runtime evidence. Unavailable independent review stays pending. No physical
operation, production rollout or scheduled execution is authorized by a passing
configuration test.

## Sources and rollback

Official references checked 2026-09-30:
[custom subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[configuration](https://learn.chatgpt.com/docs/config-file/config-reference), and
[approvals/security](https://learn.chatgpt.com/docs/agent-approvals-security).
Configuration support must still be checked against the installed client.

Rollback stops affected workers without discarding work, reverts execution-policy
changes and reloads clients with verified settings. Preserve diagnostic results,
accepted source history and review provenance. Do not restore obsolete role names
or rewrite model-routing evidence merely to undo this execution change.
