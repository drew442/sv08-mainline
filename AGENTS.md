# Working in SV08 Mainline

## Context

Read `README.md`, `docs/project.md`, `docs/roadmap.md`, and the applicable hardware
profile before changing behavior. The project supports stock and modified SV08
electronics, starting with stock. No hardware combination is validated yet.

## Evidence and hardware profiles

- Treat `docs/hardware/stock-sv08.md` as a source-backed inventory, not proof of
  the connected printer's identity. Record board revision and evidence with
  every hardware claim. Keep documented, inferred, and measured facts distinct.
- Unknown MCU clocks, bootloader offsets, GPIO polarities, thermistor circuits,
  and device identities must stay unknown until verified. Do not fill them from
  a similar printer. SV08 Max and Zero are separate hardware targets.
- Represent electronics changes in explicit profiles. Keep machine serials,
  calibration, network credentials, and private backups in ignored local paths.
- Cite primary documents with path/page or URL, revision where available, and
  access date. If sources disagree, document the discrepancy and required check.

## Agent execution and ownership

Use the [execution decision](docs/decisions/20260930-agent-execution-and-diagnostics.md)
and `.codex/agent-guide.md` for full-access execution and bounded scratch diagnostics.
They supersede historical read-only-runner requirements, not accepted product or
hardware requirements. Workers keep their assigned deliverables and file ownership.
The coordinator alone updates shared records, commits, publishes and operates the
printer. Supporting experiments do not authorize role changes, self-verification,
new agents, model/billing changes or hardware access. Preserve original candidates
and historical evidence; never waive a check to make a full-access run pass.

## Implementation

- Prefer upstream configuration and supported extension mechanisms. Add custom
  code only for an identified gap, with a test, provenance, and an upstreaming or
  retirement plan. Record architectural choices in `docs/decisions/`.
- Treat `upstream/` as pinned third-party source. Do not silently modify it or
  run bundled installers. Use a documented patch or an explicit fork when needed.
- A submodule update must include its gitlink and `upstream-lock.json` changes,
  the reason, and validation status. Do not use floating updates in build/install
  paths. Never describe a downloaded revision as tested compatibility.
- Build host and MCU Klipper artifacts from the same selected revision unless
  a separately tested compatibility policy is documented. Record toolchain,
  configuration, patches, and output hashes for reproducible artifacts.
- Keep bootstrap, build, backup, flash, and activation as separate operations.
  Default tooling to inspection/dry-run where a command can alter hardware.
  Hardware writes require an identified target, reviewed artifacts, and a
  recovery path; follow the user's authorization for the action.
- Preserve heater protections and validate sensor behavior before heat or motion.
  Do not turn off protections to make a migration appear successful.
- Immediately before an eMMC/MCU write, boot-policy change, heater/motion
  commissioning step, or release decision, spawn a separate reviewer using
  `.codex/agents/high-consequence-reviewer.toml` and GPT-6.1 Sol. Give it the exact
  target, artifact/configuration, planned operation and acceptance checks. If the
  runtime cannot load named project profiles, use a separate GPT-6.1 Sol agent and
  pass it that profile's instructions explicitly.
  Use medium by default. For material uncertainty, select
  `.codex/agents/high-consequence-reviewer-high.toml` (high effort) directly.
  Profile-file model/effort settings override spawn-time requests; verify the
  effective model and effort before relying on the review. An unavailable reviewer
  leaves the action blocked; use only an explicit, recorded fallback that preserves
  the review tier. See `.codex/agent-guide.md` for launch and fallback rules.
  The review cannot grant hardware authority or replace owner authorization;
  the coordinator records the review result before acting.

For new assignments, use the model/effort policy in `.codex/agent-guide.md`.
Sol/low is the normal bounded engineering setting; the adjustable research,
implementation and integration profiles use explicit spawn effort for harder work.
Luna handles exact extraction and mechanical transformations, not general diagnosis.
Task difficulty, independent review strength and hardware authority are separate.
Older task plans naming GPT-6 Sol retain their scope, dependencies and acceptance
checks but use the current role mapping at launch. Never rewrite historical
reviewer identities, evidence, decisions or hashes to claim a newer model ran.

## Validation and reporting

Run checks proportionate to the change. Documentation changes need link/path and
consistency checks. Code and firmware changes need relevant tests/builds; state
clearly which checks were offline and which used a named hardware profile.

For foundation changes, inspect `git diff --check`, `git diff --cached --check`,
`git submodule status`, and agreement between the lock file and indexed gitlinks.
Check JSON syntax and local Markdown targets when changing those files.

Update affected documentation with behavior changes. Report the result, evidence,
and remaining limitations. Do not commit secrets, device dumps, generated images,
or unrelated upstream changes.

The owner gives standing authorization to push every project commit to GitHub
(origin), on main and feature branches. The coordinator pushes promptly after
committing or accepting a worker commit, before reporting the work complete,
and verifies the remote contains the commit. Do not leave commits local-only
without reporting the concrete push failure and continuing to resolve it.
Preserve remote history: reconcile divergence without force pushes or deletion.
This is source publication authority, not release/deployment or hardware authority.
Private ignored artifacts and secrets remain excluded.

## Feature delivery and delegated review

The owner approved the [feature workflow](.codex/README.md), delegated approval
and an offline pilot on 2026-09-11; see [decision 0011](docs/decisions/0011-feature-agent-workflow.md).
For substantive new features or improvements, use that workflow and its durable
records. Previously approved work needs no repeated product approval.

Spawn a separate feature-approver agent for bounded proposal review and a separate
feature-verifier agent for delivery review; use `feature_verifier_high` when the
review itself needs high effort. Invoke `project_planner` when triage or a bounded
design plan is useful. It replaces the earlier feature-suggester profile and cannot
approve its own proposal. Give reviewers relevant source and evidence, not the
author's conversation as justification. Follow the agent guide's independence
rules; author, planner, approver and evidence-producing sessions are not reused as
the independent delivery verifier. Parallel research/review can accompany useful
implementation; keep one implementation active under the existing dispatcher.

Agents may approve bounded work within accepted project requirements. Changes to
owner requirements, material scope expansion or expanded agent authority require
the owner's decision. Preserve existing authorization for routine implementation,
validation, commits and pushes. Feature approval grants no hardware authority.

After finishing or blocking a task, continue the next authorized ready task.
Record physical dependencies in the existing human task lists and investigate
small non-destructive alternatives where useful. Keep offline, hardware and release
evidence distinct. Scheduling remains disabled unless explicitly configured.
