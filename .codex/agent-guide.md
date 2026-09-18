# Project subagent guide

These profiles support the [remaining work plan](../docs/remaining-work-plan.md)
and the existing [feature workflow](README.md). They do not expand delegated
approval or hardware authority. The coordinator owns task selection, integration,
durable records, authorized hardware operations and commits/publication.

| Agent | Model / effort | Useful assignment |
| --- | --- | --- |
| `project_researcher` | GPT-5.6 Luna / medium | Trace a recovery or boot code path; reconcile pin provenance; find a supported upstream configuration |
| `feature_suggester` | GPT-5.6 Luna / medium | Select one useful task when triage is needed; prefer finishing accepted work |
| `project_implementer` | GPT-5.6 Sol / medium | Implement an approved recovery, host administration, image assembly or printer configuration slice |
| `project_integration` | GPT-5.6 Sol / medium | Exercise installed packages, GTK/web flows and ARM64 VM/image acceptance checks |
| `feature_approver` | GPT-5.6 Sol / medium | Independently challenge scope, requirements and acceptance checks before substantive work |
| `feature_verifier` | GPT-5.6 Sol / medium | Independently assess the complete delivery diff and evidence against approved checks |

Luna handles narrow information gathering; Sol handles stateful implementation
and review. These are starting choices, not measured cost or quality guarantees.
No high-effort or premium-model worker is launched by default. If a task exceeds
the assigned model's capabilities, return the specific unresolved problem and
evidence to the coordinator; do not silently escalate or keep retrying.

## Assignments and cost controls

Use an agent only for a concrete task that benefits from delegation. Small local
edits do not need an entire team. Keep one implementation active. Research or
review may run alongside independent work; normally use one or two children,
up to three only with separate useful assignments and sufficient resources.
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
```

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

Integration workers require assigned disposable resources. Only one worker owns
a shared QEMU image, port or build directory at a time. A failed command is not
permission to change production media or restart another worker's process.
Hardware commissioning remains with the coordinator and the existing human task
lists; offline workers can prepare configurations and procedures but cannot
certify a printer through simulation.

## Loading and limitations

Definitions live in [agents/](agents/). Their `name` fields identify the roles.
The model and effort are explicit in each file to avoid inheriting an unnecessarily
expensive coordinator setting. No project-wide model default is changed.
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
accessed 2026-09-18. Profiles use standalone project TOML files with explicit model,
reasoning effort, sandbox defaults and developer instructions. TOML/schema checks
validate configuration structure, not actual model availability or future task
quality. Tune these choices from observed retries and successful delivery, rather
than adding specialist roles before there is a demonstrated need.
