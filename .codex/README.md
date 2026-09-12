# Feature delivery

The owner approved [decision 0011](../docs/decisions/0011-feature-agent-workflow.md).
Use the [design](../docs/design/feature-agent-framework.md) for the full contract
and [operating guide](../docs/development/feature-workflow.md) for commands,
review formats and interruption handling. Workstation dependencies are Python
3.11+ and Debian's `python3-jsonschema`; no agent-framework packages enter the host image.

[Offline validation](../docs/development/feature-workflow-validation.md) records
the deterministic checks, independent review and current runner limitations.
The completed [offline pilot](../docs/development/feature-workflow-pilot.md)
records both deliveries, a rejected candidate and independently verified correction,
and the measured readback improvement.

Read `AGENTS.md`, the project definition, roadmap, applicable profile and relevant
accepted decisions. Load only the feature records needed for the current work.
The existing host completion checklist and hardware task lists remain release
authority. Do not duplicate their requirements or infer consent to change them.

Use separate suggestion, approval and verification roles for substantive work.
The project TOML definitions are in `agents/`; use their instructions explicitly
in separate sessions when the current client does not support named custom agents.
Do not silently substitute self-approval. Runtime permissions may override role
defaults; the interactive collaboration client inherits its parent permissions.
The current dispatcher starts no worker process and supplies no isolation itself.
The coordinator maintains records and integrates reviewed changes. Small fixes to
documented behavior use a short record and normal review. Import already-approved
work with its authorization reference rather than requesting approval again.

The suggester may recommend no new proposal. Prioritize regressions and finishing
accepted workflows; allow one active implementation and at most three ready
proposals. The approver may approve bounded work within existing requirements;
scope changes or expanded authority go to the owner. The verifier checks actual
behavior and evidence and cannot certify its own implementation.

Continue ready offline tasks when another task requires hardware or a human.
Record the exact physical action and evidence in the existing human task list.
Keep decisions, execution and acceptance evidence distinct. Printer access and
hardware writes require their own applicable authorization and recovery path.

This repository configures no unattended schedule. Use the workflow in the active
session; persistent records let subsequent sessions resume. Worker permissions and
private evidence access must be enforced by the execution environment as well as
these instructions. Do not expose printer credentials or backup mounts to automatic
offline workers.

At each session start, run `python3 scripts/feature_workflow.py validate` and
`python3 scripts/feature_workflow.py next`. Import relevant approved backlog work
when there is queue capacity. After a task finishes or becomes blocked, select
again. A null selection means inspect pending decisions and blockers; it does not
mean that all project work is complete. Stop only for the user's instruction, no
authorized ready work, or the configured execution allowance, and record why.
