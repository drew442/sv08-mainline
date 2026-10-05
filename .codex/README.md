# Feature delivery entry point

**Coordinator:** use [the agent guide](agent-guide.md) for dispatch and
[the operating guide](../docs/development/feature-workflow.md) when creating,
claiming, submitting, verifying or integrating a feature record. At the start of a
queue-management session run `python3 scripts/feature_workflow.py validate` and
`python3 scripts/feature_workflow.py next`; select again after completion/blocking.
A null selection means inspect blockers, not declare the project complete.

**Delegated worker:** read AGENTS.md, your profile and the assigned sources/checks.
Do not select from the global queue or ingest all project status/history. Use
[the context map](../docs/context-map.md) only to find relevant material. Read the
operating guide only for a record operation your role actually performs.

[Decision 0011](../docs/decisions/0011-feature-agent-workflow.md) governs delegated
approval; the [execution decision](../docs/decisions/20260930-agent-execution-and-diagnostics.md)
supersedes its old isolation assumptions. Existing approval is reused; new substantive
scope needs separate approval and substantive delivery needs independent verification.
Small mechanical corrections use the short record and normal review. The coordinator
owns shared records, candidate commits, integration and publication. Hardware authority
and exact-operation review remain separate. The dispatcher starts no agents or jobs.

Consult the [framework design](../docs/design/feature-agent-framework.md),
[validation history](../docs/development/feature-workflow-validation.md) or
[completed pilot](../docs/development/feature-workflow-pilot.md) only when auditing
those contracts or historical evidence, not as worker onboarding. For deployment
use [agent execution](../docs/development/agent-execution.md). Python 3.11+ and
`python3-jsonschema` are workstation dependencies, not printer-image additions.
