# Feature delivery entry point

**Coordinator:** use [the agent guide](agent-guide.md) for dispatch and
[the operating guide](../docs/development/feature-workflow.md) for records.
At queue-session start run `python3 scripts/feature_workflow.py validate` and
`python3 scripts/feature_workflow.py next`; select again after completion/blocking.
A null selection means inspect blockers, not declare the project complete.
For adoption/validation gaps, consult the optional
[follow-up register](../docs/development/agent-followups.md), not another onboarding read.

**Delegated worker:** read AGENTS.md, your profile and assigned sources/checks.
Do not select from the global queue or ingest all project history. Use
[the context map](../docs/context-map.md) only to locate relevant material.

The [development review decision](../docs/decisions/20261005-proportionate-development-review.md)
supersedes blanket independent approval/verification. New records use v2:
`self` for authorized reversible development, `targeted` for a named review need,
`consequential` for credible serious loss. All require actual validation evidence;
the latter two additionally require their selected independent assessment. Routine
self-validation is not independent review and must never be labelled as such.
Legacy v1 records retain their original gates; preserve history rather than invent reviews.
The coordinator retains shared records, commits, publication and all printer access.
The dispatcher executes neither tests nor hardware operations and supplies no sandbox.

Consult [decision 0011](../docs/decisions/0011-feature-agent-workflow.md),
[the framework](../docs/design/feature-agent-framework.md),
[validation history](../docs/development/feature-workflow-validation.md) and
[the pilot](../docs/development/feature-workflow-pilot.md) only when auditing
legacy contracts/evidence, not during routine onboarding. The
[execution decision](../docs/decisions/20260930-agent-execution-and-diagnostics.md)
retains full access and role limits. Python 3.11+ and `python3-jsonschema` remain
workstation dependencies, not printer-image additions. No new scheduler or agent is added.
