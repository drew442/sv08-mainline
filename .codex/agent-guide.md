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
| `project_implementer` | GPT-6 Sol / medium | Implement an approved recovery, host administration, image assembly or printer configuration slice |
| `project_integration` | GPT-6 Sol / medium | Exercise installed packages, GTK/web flows and ARM64 VM/image acceptance checks |
| `feature_approver` | GPT-6 Sol / medium | Independently challenge scope, requirements and acceptance checks before substantive work |
| `feature_verifier` | GPT-6 Sol / medium | Independently assess the complete delivery diff and evidence against approved checks |

Luna handles narrow research and corrections; Sol handles complex implementation,
integration and independent review. Medium is the default effort across profiles.
Use Sol/high for a bounded review involving firmware writes, boot/recovery policy,
heater or motion safety, data-loss risk, or an unresolved conflicting source;
record why the higher effort is needed in the handoff. No Astra worker is launched
by default. If a task exceeds its assigned model, return the specific gap and
evidence to the coordinator for reassignment instead of retrying broadly. These
are routing defaults, not measured cost or quality guarantees.

## Assignments and cost controls

Use an agent only for a concrete task that benefits from delegation. Small local
edits do not need an entire team. Keep one implementation active. Research or
review may run alongside independent work; normally use one child and at most
two active children for distinct assignments. Run required independent approval
and verification sequentially when parallel work would only duplicate context.
Profiles do not start agents or schedules automatically.

Give each child a concise handoff rather than the full conversation:

```text
Task and desired result:
Approved feature/requirement and acceptance check IDs (when applicable):
Source revision and relevant paths/evidence:
Owned files, or read-only scope:
Allowed commands/environment and fixture directory/ports (for execution):
Existing results to reuse; unresolved question:
Completion condition and result format:
Shared human dependency IDs and offline work that can proceed while waiting:
```

Supply paths and acceptance IDs, not pasted whole documents or long raw logs.
First inspect existing evidence and current file hashes; rerun a check only when
its inputs changed, it failed, or the existing result cannot answer the question.
Use bounded searches/output and one shared physical task queue. A slow build or
VM run is a reason to wait on its existing handle, not to launch duplicate work.
Reserve Sol review for substantive acceptance; use direct coordinator checks for
small documented corrections that the workflow classifies as normal review.

For existing approved work, pass its record; do not request product approval again.
For new substantive work, use the existing proposal/approval/verification contracts.
The suggester is optional, not a mandatory stage. Respect an owner pause on new
features. Reviewers receive source and evidence, not the author's conclusions as
justification. An implementer or integration evidence producer cannot verify its
own delivery. Do not reuse their session for independent verification.

Workers report concise findings, affected paths, commands/results, evidence level
and actionable blockers. Use the existing JSON formats for formal decisions and
verification. Children return to the coordinator rather than delegating further.
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

Definitions live in [agents/](agents/). Their `name` fields identify the roles.
The model and effort are explicit in each file to avoid inheriting an unnecessarily
expensive coordinator setting. No project-wide model default is changed. These
TOML defaults apply when a client loads these custom profiles; they do not change
an already running chat or pre-registered agent role whose model/effort is fixed
by its runtime. The coordinator must verify the effective role settings at launch.
If the current session does not expose a new role, start a new session. If a
client cannot load custom agents, pass the profile instructions, model and effort
explicitly to a supported separate agent session. Report unavailable models and
choose a supported fallback explicitly; do not claim the configured model ran
without runtime evidence.

Sandbox settings are defaults, not proof of isolation. Runtime permissions can
override them; writable profiles also rely on assigned ownership. Enforce private
backup/credential exclusion in the execution environment. A read-only verifier
needing reproduction writes should use an authorized disposable environment;
otherwise request execution evidence from the coordinator and state the limit.

Configuration format follows the official [Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents),
checked 2026-09-23. Profiles use standalone project TOML files with explicit model,
reasoning effort, sandbox defaults and developer instructions. TOML/schema checks
validate configuration structure, not actual model availability or future task
quality. Tune these choices from observed retries and successful delivery, rather
than adding specialist roles before there is a demonstrated need.
