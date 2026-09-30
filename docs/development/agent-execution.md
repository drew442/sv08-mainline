# Deploying full-access, role-preserving agents

Date: 2026-09-30. Implements the owner-authorized
[execution decision](../decisions/20260930-agent-execution-and-diagnostics.md).
This runbook is a procedure, not a claim that these live checks have run.
Use the [agent guide](../../.codex/agent-guide.md) for the authoritative role table,
diagnostic limits, handoff format and review-independence rules.

## Prepare and inspect

Use the intended owner-authorized development environment, not production or the
printer host. Full access permits anything available to its operating-system
account; do not mistake role instructions for enforced credential/device isolation.
No host package, global configuration, AppArmor, device or service change is needed
merely to adopt this project policy. Do not disable host protections to make a test
pass. Keep target hardware operations out of deployment smoke checks.

Record the checkout revision/dirty state and installed Codex version. Inspect its
help, project trust, project-local and user-global configuration, managed requirements,
live parent overrides and any wrapper used for separate `codex exec` sessions.
The project settings are `approval_policy = "never"` and
`sandbox_mode = "danger-full-access"`; profiles omit their own permission overrides.
Native children inherit live parent permission overrides, whereas a separately
started CLI process has its own invocation/configuration. An old
`codex exec --sandbox read-only` wrapper still asks for restricted execution.
For a separately launched authorized session, the explicit CLI equivalent is
`--dangerously-bypass-approvals-and-sandbox` (`--yolo`); verify installed help before
use. Do not combine incompatible launch flags or silently switch billing.

Preserve active worktrees and stop/close obsolete workers before starting a fresh
client. In the interactive CLI inspect `/status` and `/permissions`, plus available
runtime launch metadata. Check the actual parent and newly spawned child settings;
a model's self-report is not proof. Managed policy may prohibit the requested mode.
Report such a restriction instead of trying to bypass it or repeatedly spending
more reasoning tokens. Do not rewrite user-global settings to conceal the issue.

Confirm all eleven current profiles load. Check generic child Sol/low defaults,
explicit effort on adjustable research/implementation/integration profiles, pinned
reviewer effort and the named high variants. Each child profile sets
`[agents] enabled = false`; verify native delegation tools are unavailable. This
setting is not a hard prohibition on running another program through the shell.
Do not actually start a paid nested CLI/API session as a negative test.

## Allocate before dispatch

Give the child one question, deliverable, source revision, owned paths, primary-task
budget and coordinator-assigned scratch directory outside the candidate worktree.
A suitable location is `local/feature-workflow/probes/<task-id>/<attempt-id>/` in
the primary checkout. Use a unique existing directory with no symlink escape.
Allocate ports/fixtures exclusively. Explicitly name permitted development-host
connections and resources, or say none; printer access is never implicit.

Attach remaining diagnostic allowance: two experiments, 300 seconds cumulative
elapsed process runtime and 256 MiB cumulative generated data unless a documented
coordinator continuation changes it. Include inputs/logs/caches and earlier linked
attempts; do not reset it on handoff, deletion or a new session. Use process timeouts
and bounded output; inspect resource needs before running. Ordinary reading is
part of the primary task; a full image build is not an incidental experiment.

These limits are procedural operating controls, not an installed budget-enforcing
service. Hard runtime/disk/spending prevention needs an external supervisor that
the worker cannot modify. Do not claim a hard cost cap from timeouts or thread
count. Keep experimental token-budget features out of this change.

## Disposable live role checks

Use a stable disposable candidate with no production connections. Assign the
checks sequentially; do not launch a permanent test team. No printer write, key
disclosure, publication or paid nested-agent call belongs in these checks.

| Check | Expected result |
| --- | --- |
| Lookup | A small extraction script can write its assigned scratch result; it returns exact facts, not a causal diagnosis or tracked edit. |
| Research | A minimal reproduction answers a scoped question; the source/candidate remains unchanged and the result includes evidence, not a production repair. |
| Integration | A supplied candidate defect is reported with reproduction; only disposable inputs/invocation may be corrected, not candidate code or tracked tests. |
| Verifier | It reproduces a check against the unchanged submitted revision, preserves independence and returns the existing verification format. A missing check remains unresolved, not passed. |
| Allowance exhaustion | A handoff with zero remaining incidental allowance returns evidence and the smallest next assignment without another probe, model change, nested agent or owner interruption. |

Separately test a harmless assigned local scratch write under the effective mode.
Where the handoff explicitly assigns a development host, an existing-authentication
connection may inspect a named harmless fixture; never print keys or use the printer
as the connection test. This does not authorize generic host access.

The coordinator compares the complete before/after candidate state, including
tracked/untracked files, modes, deletions and gitlinks; retain any pre-existing
changes as baseline rather than attributing them to the child. Use existing Git
diff/status tools and inspect new paths. Keep review scratch outside the candidate.
Do not automatically discard unexpected edits: preserve evidence and reassign the
repair. A reviewer whose production repair is adopted is an author and needs a
fresh independent verifier. Reproducing the unchanged candidate is not authorship.

Static configuration tests do not establish the behaviours above. Record requested
and actual settings, source, commands, results, limits and observations in the
existing [observation form](../../.codex/templates/agent-task-observation.md).
Normal work needs only a compact handoff/result; use detailed samples for failures
and escalation. Track total observed cost through acceptance without counting
child usage twice when a parent total already includes it. Unknown usage is unknown.

## Repository checks and approval reconciliation

From a complete checkout run:

```sh
python3 -m unittest discover -s tests -p 'test_codex_agent_policy.py' -v
python3 -m unittest discover -s tests -p 'test_feature_workflow*.py' -v
python3 scripts/feature_workflow.py validate
python3 scripts/feature_workflow.py status
python3 scripts/feature_workflow.py next
git diff --check
git diff --cached --check
```

The path tests exercise explicit public configuration admission and continued
private/path-escape rejection. They do not admit `local/` scratch as public evidence.
The original workflow tests still cover independent verification, stale approval,
exclusive ownership, clean commits and offline/hardware evidence separation.

In the real queue, changed requirement-file hashes can make pending approvals stale.
Inspect `status` reasons and current `review-context`; obtain actual independent
review for changed inputs, not a mechanical overwrite of approval hashes. Preserve
completed historical evidence. A `next` result of null while a task is running or
in review is expected: the dispatcher still has one active slot. No hardware task
is made dispatchable by full access. The coordinator may continue eligible
coordination/research without claiming a second implementation lease.

Record exactly which checks ran and which require the target client or complete
Git history. A reconstructed source fixture can run deterministic unit tests but
cannot validate this repository's real pending queue or historical evidence.
Independent review and live deployment checks remain separate acceptance steps.
No schedule, printer operation or actual hardware certification is introduced.

## Failure and rollback

A permission failure goes to runner diagnosis; an unresolved reasoning question goes
to the coordinator with existing evidence and an appropriate effort request. Do not
retry a failed sandbox launch at higher model effort. One diagnosed repair cycle is
for the same unresolved failure, not a one-failing-test limit for a whole feature.
Review-driven rework carries prior attempts and remaining budgets forward.

On role drift, unreliable evidence or repeated allowance overruns, stop the affected
assignment and preserve work. Revert the execution-policy change and restart clients
only after reconciling their worktrees. Confirm effective settings after rollback;
do not erase evidence, relax hardware gates or change billing to make checks pass.

Official references (checked 2026-09-30):
[subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[configuration](https://learn.chatgpt.com/docs/config-file/config-reference),
[approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security).
