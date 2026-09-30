# Feature delivery

Use the [agent guide](agent-guide.md) for task routing, model/effort selection,
independence and resources. Sol low is the normal research, implementation and
integration setting, adjustable to medium/high for harder assignments. Luna is
limited to exact lookup and mechanical edits. Planning and substantive review use
medium; explicit high review variants cover difficult review reasoning. Read the
[benchmark basis](../docs/development/codex-model-routing.md) when assessing the
policy, not in every child. Benchmark evidence justifies the defaults; observations
refine them after deployment, without a separate easy-task-only pilot.

Profiles do not change the main chat's model. Project [agent defaults](config.toml)
prevent unspecified children inheriting an expensive coordinator. Three worker
profiles deliberately leave effort unpinned so supported spawn overrides work.
Review profiles pin model and effort; use the explicit high variant when needed.
Confirm effective settings/permissions in the runtime, not from the model's claim.

The owner approved [decision 0011](../docs/decisions/0011-feature-agent-workflow.md).
Use the [design](../docs/design/feature-agent-framework.md),
[operating guide](../docs/development/feature-workflow.md),
[validation](../docs/development/feature-workflow-validation.md) and
[completed offline pilot](../docs/development/feature-workflow-pilot.md) for the
record and acceptance contracts. Python 3.11+ and Debian's `python3-jsonschema`
are workstation dependencies, not additions to the printer host image.

Read AGENTS.md, applicable project requirements/decisions and only relevant feature
records. Existing release checklists and [current goals](current-goals.md) retain
their authority. The coordinator selects work, updates records, commits candidate
changes in the owned worktree and integrates after independent verification.
Children do not commit or publish. Import existing approval rather than ask again.

Use optional `project_planner` for useful triage/design, separate `feature_approver`
for new substantive scope and separate `feature_verifier` (or its high variant) for
delivery. The planner replaces the old feature-suggester profile, not its independent
approval requirement. Small mechanical corrections use the short record and normal
review; substantive work still needs verification regardless of worker effort.
Use scripts rather than agents for predetermined test recipes. Integration supplies
execution evidence, not independent acceptance of its own work.

Before a consequential hardware, boot-policy, commissioning or release action,
obtain a fresh exact-operation review using
[`high_consequence_reviewer`](agents/high-consequence-reviewer.toml) on GPT-6.1 Sol,
or [`high_consequence_reviewer_high`](agents/high-consequence-reviewer-high.toml)
when material uncertainty needs high effort. Neither profile can grant hardware
authority, execute the operation or replace actual observations. Preserve recovery,
heater/motion and owner-authorization gates independently of implementation effort.

Keep one implementation active, no more than two concurrent children and at most
three ready proposals. The planner can recommend no new proposal. Continue eligible
offline work while another task awaits hardware/human input. Use the existing
coordinated human queue and reuse valid evidence without concealing its limitations.

The dispatcher starts no agents, runs no task commands and enforces no execution
sandbox. No unattended schedule is introduced. Provision source/disposable-build
environments that exclude printer credentials, private backups and physical devices;
parent runtime permissions can override TOML defaults. Worktrees alone are not isolation.

At session start run `python3 scripts/feature_workflow.py validate` and
`python3 scripts/feature_workflow.py next`. Select again after completion or blocking.
Null selection means inspect blockers/decisions, not that the project is complete.
Stop for the user's instruction, no authorized ready work or the execution allowance,
and record why. Unavailable required independent review stays pending; other ready
work may proceed. Runtime smoke checks and independent review precede deployment.
