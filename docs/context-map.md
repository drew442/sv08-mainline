# Find the context needed for this task

This is a navigation aid, not a required reading list or a second roadmap. Begin
with the task's explicit paths and acceptance IDs. Read the matching source and
applicable accepted requirements; expand only when dependencies or evidence need it.
Do not recursively follow every link. Full-diff and acceptance review are never
limited to the author's chosen paths. Missing/conflicting evidence stays explicit.

| Task | Start here | Read more when / checks to select |
| --- | --- | --- |
| Project orientation or proposed scope | [Project definition](project.md); [README](../README.md) for current overview | Relevant owner decisions before changing requirements; not every session or typo. |
| Select next work / resolve a scope pause | [Current goals](../.codex/current-goals.md) and [roadmap](roadmap.md) | Follow their current decision references; [remaining plan](remaining-work-plan.md) only for dependencies being selected. Historical phases do not reopen abandoned work. |
| Already-approved implementation | The named `docs/features/<feature>/record.json` and proposal, acceptance IDs, affected code and tests | Relevant requirement/design sections and callers. Do not scan every feature record. Run focused existing regression tests. |
| Source/identity investigation | Named module/log and its entry points; [reference index](references.md) when a primary source is missing | Relevant hardware profile, source revision and measured evidence. A cited similar board never supplies missing constants. |
| Host/A-B/operating modes | [Host design](design/host-os-ab.md) and applicable decisions linked there | Only relevant state transitions/constraints; select existing tests for changed modules, installed checks when acceptance requires them. |
| UI/installed user journey | Named feature and [UI decision](decisions/0010-host-administration-and-recovery-ui.md) | Relevant browser/GTK/Cockpit test and fixture. Unit mocks alone do not prove an installed journey. |
| Upstream/build/pin change | [Upstreams](upstreams.md), `upstream-lock.json` and indexed gitlinks | Relevant package/build instructions, matched host/MCU Klipper revision, artifact hashes and size checks. No floating inputs or bundled installers. |
| Physical action or release | [Coordinated human queue](hardware/coordinated-human-tasks.md), applicable profile and exact action evidence | [Stock inventory](hardware/stock-sv08.md) is not target identity; use relevant [host gates](hardware/host-os-tasks.md) and project release criteria. Coordinator only, with authorization and exact-operation review. |
| Queue/approval/evidence transition | [Workflow entry](../.codex/README.md), then [operating guide](development/feature-workflow.md) for that operation | Actual schema, source/decision/evidence hashes and full candidate diff. Dispatcher changes require `test_feature_workflow*.py`; no global queue scan by children. |
| Agent configuration/context change | [Agent guide](../.codex/agent-guide.md), relevant TOML and [execution decision](decisions/20260930-agent-execution-and-diagnostics.md) | `test_codex_agent_policy.py` and `test_agent_context.py`; [execution runbook](development/agent-execution.md) for runtime loading/permissions. |
| Historical evidence or process audit | The specific dated report/decision at its recorded revision | [Workflow design](design/feature-agent-framework.md), validation/pilot history and archived goals only when explaining that history. Do not treat old permission restrictions as current. |

Use filenames/headings and bounded searches before retrieving whole histories, for
example `rg --files docs` to find paths, then `rg -n 'exact symbol' <relevant-path>`.
Read the surrounding section when a match alone is insufficient. Paths/sections
are starting points, never a token cap that hides required evidence. Keep long raw
logs in assigned artifacts and return the relevant excerpt, source revision/hash,
result and limitation. Preserve the complete source for independent inspection.
