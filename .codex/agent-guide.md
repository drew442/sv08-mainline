# Project subagent guide

These profiles support the [remaining work plan](../docs/remaining-work-plan.md)
and the existing [feature workflow](README.md). They do not expand delegated
approval or hardware authority. The coordinator owns task selection, integration,
durable records, authorized hardware operations and commits/publication.

| Agent | Model / effort | Useful assignment |
| --- | --- | --- |
| `project_researcher` | GPT-6 Luna / medium | Trace one bounded code path or source question |
| `feature_suggester` | GPT-6 Luna / medium | Select one useful task only when triage is needed |
| `project_narrow_implementer` | GPT-6 Luna / medium | Make a small, already-scoped documentation, test or tooling correction |
| `project_routine_implementer` | GPT-6.1 Sol / low | Opt-in pilot: settled, low-risk implementation larger than a tiny correction |
| `project_test_runner` | GPT-6 Luna / medium | Opt-in pilot: execute an exact offline recipe; otherwise run the script directly |
| `project_implementer` | GPT-6.1 Sol / medium | Implement an approved recovery, host administration, image assembly or printer configuration slice |
| `project_integration` | GPT-6.1 Sol / medium | Exercise installed packages, GTK/web flows and ARM64 VM/image acceptance checks |
| `feature_approver` | GPT-6.1 Sol / medium | Independently challenge scope, requirements and acceptance checks before substantive work |
| `feature_verifier` | GPT-6.1 Sol / medium | Independently assess the complete delivery diff and evidence against approved checks |
| `high_consequence_reviewer` | GPT-6.1 Sol / medium | Review the exact hardware, boot-policy, commissioning or release action before execution |
| `high_consequence_reviewer_high` | GPT-6.1 Sol / high | The same independent review when material uncertainty warrants high effort |

Here, Sol means GPT-6.1 Sol for new assignments. Luna roles stay on GPT-6 Luna.
Keep medium for complex implementation, integration, approval and verification;
benchmark gains do not prove low effort is sufficient for these project tasks.
The routine implementer is an explicit pilot for settled, low-risk work only:
exclude boot/recovery, A/B activation, storage writers, data migration, credentials,
hardware constants, heater/motion safety and release decisions regardless of diff
size. The test runner collects prescribed observations; it never diagnoses or repairs.
Prefer direct deterministic scripts over spawning an agent just to wait on them.

Route tiny known corrections to Luna/local checks, settled low-risk pilot work to
Sol/low, and complex work directly to Sol/medium. Do not route a task through every
tier. Stop an unsuitable pilot and return the exact gap/evidence to the coordinator;
one bounded in-scope repair is allowed only for a clear cause. No broad retry loop.
No Astra worker is launched by default. These are routing hypotheses, not measured
cost or quality guarantees. See the [evaluation and rollout](../docs/development/codex-model-routing.md)
only when planning or assessing the pilot; do not load it in every child context.

## Assignments and cost controls

Use an agent only for a concrete task that benefits from delegation. Small local
edits do not need an entire team. Keep one implementation active. Research or
review may run alongside independent work; normally use one child and at most
two active children for distinct assignments. Run required independent approval
and verification sequentially when parallel work would only duplicate context.
Profiles do not start agents or schedules automatically.

Give each child a concise handoff rather than the full conversation:

```text
Task and desired result; role, requested model/effort and pilot eligibility:
Approved feature/requirement and acceptance check IDs (when applicable):
Source revision and relevant paths/evidence:
Owned files, or read-only scope:
Allowed commands/environment and fixture directory/ports (for execution):
Existing results to reuse; unresolved question:
Completion condition, execution allowance, escalation trigger and result format:
Observation ID (pilot only); runtime-confirmed settings/usage if available:
Shared human dependency IDs and offline work that can proceed while waiting:
```

Supply paths and acceptance IDs, not pasted whole documents or long raw logs.
First inspect existing evidence and current file hashes; rerun a check only when
its inputs changed, it failed, or the existing result cannot answer the question.
Use bounded searches/output and one shared physical task queue. A slow build or
VM run is a reason to wait on its existing handle, not to launch duplicate work.
Reserve Sol review for substantive acceptance; use direct coordinator checks for
small documented corrections that the workflow classifies as normal review.
Before an eMMC/MCU write, a boot-policy change, heater/motion commissioning, or
a release decision, the coordinator must spawn a separate `high_consequence_reviewer`
on Sol/medium with the exact proposed operation. Select `high_consequence_reviewer_high`
directly when board identity, artifact provenance, recovery, safety limits or
acceptance evidence remain materially uncertain. If a medium review discovers
material uncertainty, hand its evidence to that separate high-effort review before
any action; unresolved physical facts still block action. This is an independent
review responsibility, not a second implementation lane. If named profiles are unavailable, use a separate Sol agent
and pass it the profile instructions explicitly. Wait for its review before action.

For existing approved work, pass its record; do not request product approval again.
For new substantive work, use the existing proposal/approval/verification contracts.
The suggester is optional, not a mandatory stage. Respect an owner pause on new
features. Reviewers receive source and evidence, not the author's conclusions as
justification. An implementer or integration evidence producer cannot verify its
own delivery. Do not reuse their session for independent verification.

Workers report concise findings, affected paths, commands/results, evidence level
and actionable blockers. Use the existing JSON formats for formal decisions and
verification. For opted-in pilot tasks the coordinator keeps one
[observation](templates/agent-task-observation.md) under ignored
`local/feature-workflow/model-routing/`, including all escalation/rework and review
costs. Unknown usage stays unknown; observations never replace acceptance evidence.
Children return to the coordinator rather than delegating further.
Reuse an existing research session for related questions; avoid duplicate scans.
Review a stable revision or explicit diff, not files another worker is changing.
Stop testing once the relevant checks pass unless new evidence warrants more.

Use the [current subclient goals](current-goals.md),
[parallel assignments](../docs/development/parallel-work.md) and
[coordinated human queue](../docs/hardware/coordinated-human-tasks.md). Children
send physical dependencies to the coordinator under existing H IDs; they do not
independently ask the owner for actions. The coordinator combines ready consumers,
arms capture before power/media reconnection, and records one result with links
for every applicable consumer. Reuse evidence only while its target and test
conditions remain valid; retain separate thermal/motion safety gates.

Integration workers require assigned disposable resources. Only one worker owns
a shared QEMU image, port or build directory at a time. A failed command is not
permission to change production media or restart another worker's process.
Hardware commissioning remains with the coordinator and the existing human task
lists; offline workers can prepare configurations and procedures but cannot
certify a printer through simulation.

## Loading and limitations

Definitions live in [agents/](agents/); `name` identifies each role. Model and
effort are explicit to avoid inheriting an expensive coordinator setting. No
project-wide coordinator model, speed mode or billing route is changed.
For a fresh coordinator, Sol/medium is a suggested starting point, not an override
of the owner's selected model or permission to use a different billing account.

The official precedence rule is important: a custom file's `model` and
`model_reasoning_effort` win over explicit spawn settings. Consequently requesting
"high" when spawning a medium-pinned role does not implement escalation. Use the
high profile for high-consequence review. For other justified effort changes,
use a separate supported session whose effective configuration actually selects
that effort; retain the role's full instructions, independence and restrictions.

Start a fresh client session when new roles are not exposed. Record requested and
runtime-confirmed model/effort separately, plus client version and effective
permissions; parsed TOML is not runtime evidence. If a client cannot load custom
roles, use their instructions in a supported separate session with the same
explicit model/effort. Do not claim an unobserved launch or setting succeeded.
If unavailable, report the error and stop that assignment. A coordinator may
explicitly record a supported fallback at the same review/effort tier (including
GPT-6 Sol at medium/high during rollout), never silently Luna/low for review.
A fallback does not count as a GPT-6.1 trial and needs its own effective-setting
check. An unavailable independent reviewer leaves review/action pending; other
authorized offline work can continue. Do not alter user-global configuration.

Sandbox settings are defaults, not proof of isolation. Runtime permissions can
override them; writable profiles also rely on assigned ownership. Enforce private
backup/credential exclusion in the execution environment. A read-only verifier
needing reproduction writes should use an authorized disposable environment;
otherwise request execution evidence from the coordinator and state the limit.

Configuration format follows the official [Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents),
checked 2026-09-30. Profiles use standalone project TOML files with explicit model,
reasoning effort, sandbox defaults and developer instructions. TOML/schema checks
validate configuration structure, not actual model availability or future task
quality. Tune these choices from observed retries and successful delivery, rather
than adding specialist roles before there is a demonstrated need.
