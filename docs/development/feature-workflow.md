# Operating the feature workflow

Implements [decision 0011](../decisions/0011-feature-agent-workflow.md).
This workstation tool manages records around existing Codex sessions. It does
not operate the printer, run commands embedded in records, start agents, create
an unattended schedule or push Git changes. The coordinator performs those
development actions using the available supported tools and existing authorization.

## Inputs and role invocation

Install Python 3.11+ and `python3-jsonschema` on the development workstation.
The implementation uses the packaged JSON Schema validator rather than adding
another schema engine. The host OS image has no dependency on this tooling.

Use [the entry point](../../.codex/README.md) and the project TOML definitions:
`feature_suggester`, `feature_approver`, `feature_verifier`. If the client exposes
named custom agents, invoke the named role with a concrete bounded task. Otherwise
load the same TOML `developer_instructions` into a separate agent/session. Keep
reviewers separate from the author and implementer; an unavailable reviewer leaves
that review pending while other eligible work continues.

TOML permission defaults can be overridden by the parent runtime. In particular,
interactive collaboration inherits its parent's permissions. Do not describe
prompt-only restrictions as an enforced sandbox. Before unattended execution,
provision a restricted source/build environment without printer keys, backup
mounts or physical devices, and verify its effective permissions. Worktrees
isolate changes, not credentials. That deployment is outside the offline pilot.

Keep private session transcripts, run output and reports awaiting sanitization
under `local/feature-workflow/`. Version only reviewed role files, templates,
schemas, proposals and sanitized evidence. Personal `.codex` configuration remains
ignored. No API credentials or model override are introduced by this workflow.

## Record and approval

Copy [the record template](../../.codex/templates/record.json) into
`docs/features/<id>/record.json` and [the proposal form](../../.codex/templates/proposal.md)
into the adjacent `proposal.md`. Use [the short form](../../.codex/templates/fix.md)
for bounded corrections to already documented behavior. These files contain scope
and execution metadata; existing project requirements and release checklists
remain authoritative.

Assign each acceptance check to one task. Dependencies use `<feature>:<task>`.
Use `offline`, `hardware` or `human` environments honestly. Physical tasks link
their canonical entry in the existing human checklist. A feature with outstanding
physical acceptance remains open even if all its offline tasks finish.

Ask a separate approver to review the real proposal, relevant source and accepted
requirements. The `owner_decision_required` flag is an aid, not evidence that a
proposal stays within scope. Compute current inputs with:

```sh
python3 scripts/feature_workflow.py review-context <feature>
```

The returned hashes bind proposal text, requirement files and immutable record
scope, including task/check definitions and dependencies. Output must satisfy
[the decision schema](../../.codex/schemas/decision.schema.json). Save the review
privately, inspect it, then import it from the primary checkout:

```sh
python3 scripts/feature_workflow.py decide <feature> --result local/feature-workflow/decision.json
python3 scripts/feature_workflow.py --execute decide <feature> --result local/feature-workflow/decision.json
```

`approved-with-constraints` requires constraints linked to acceptance check IDs.
`needs-research` names a bounded investigation and its exit evidence in the
rationale/proposal; the research task itself needs authorized scope. `deferred`
and `rejected` work does not dispatch. Existing owner authorization can use
`owner-existing` with a cited decision, but an agent must not invent that consent.

The structured schemas are local validation contracts. A client can request JSON
output or use its supported structured-output mechanism, but the coordinator
always validates the returned JSON locally. Do not assume every client accepts
the entire JSON Schema dialect as a model-output constraint.

## Dispatch and implement

These commands inspect without creating locks, worktrees or records:

```sh
python3 scripts/feature_workflow.py validate
python3 scripts/feature_workflow.py status
python3 scripts/feature_workflow.py next
python3 scripts/feature_workflow.py packet <feature>:<task>
```

Selection favors the recorded priority, then oldest creation date and stable ID.
The coordinator sets priority from the approved design's ordering and explains
exceptions in the proposal. A ready task needs current approval, completed
dependencies, an offline environment and available implementation capacity.
The dispatcher rejects more than three ready features and allows one active task.
It does not manufacture another proposal when existing work should be finished.

Commit the approved proposal/record before starting its branch. Create a clean
worktree at the current integration HEAD using Git's supported command:

```sh
git worktree add -b feature/<feature>-<task> local/feature-workflow/worktrees/<feature>-<task> HEAD
python3 scripts/feature_workflow.py --execute claim <feature>:<task> \
  --actor <implementer> --session <session-id> \
  --worktree local/feature-workflow/worktrees/<feature>-<task>
```

All mutations require `--execute` before the subcommand. The primary checkout is
the sole queue writer; a lock in its ignored local directory is shared across
worktrees. Claiming saves a private run lease before recording active ownership.
Keep the recorded session ID stable for submit/complete/block operations. The
helper never evaluates shell text from a proposal, task or model output.

The implementer receives the task packet and relevant source. It performs the
bounded implementation, checks and documentation in its worktree, then commits
the complete change. Commit only intended files and retain private artifacts in
ignored paths. Normal code, build and foundation checks in AGENTS.md still apply.

## Evidence, verification and integration

Prepare a list satisfying [the evidence schema](../../.codex/schemas/evidence.schema.json).
Every required check needs a sanitized evidence document, exact method and
limitations. Record the document SHA-256, relevant source hashes and the complete
implementation commit. The commit must be the clean worktree's HEAD; it binds
the whole delivered tree even when the explicit input hash map is narrower.
Hash public inputs with `feature_workflow.py --repo <worktree> hash <paths...>`.

```sh
python3 scripts/feature_workflow.py --execute submit <feature>:<task> \
  --session <session-id> --evidence local/feature-workflow/evidence.json
```

Ask a separate verifier to inspect the entire diff from the run's base commit
to the submitted commit, the acceptance checks and actual execution evidence.
Reproduce critical checks where needed. Matching JSON and hashes do not themselves
prove test execution, useful behavior or hardware safety. A fixture does not meet
a hardware acceptance check. The verifier returns
[a verification result](../../.codex/schemas/verification.schema.json), binding
the complete approved decision through `decision_sha256` and the evidence list
with SHA-256 of canonical JSON (sorted keys and compact
comma/colon separators).

```sh
python3 scripts/feature_workflow.py --execute verify <feature>:<task> \
  --result local/feature-workflow/verification.json
```

A failed review blocks the task with actionable rationale and lets other ready
work proceed. A passed review permits integration; it does not complete the task.
The coordinator commits queue bookkeeping as needed, merges the reviewed branch
while preserving its commit in history, and checks the integration. Use Git's
normal merge/fast-forward operations. Squashing/cherry-picking requires review of
the replacement commit; an unreachable evidence commit will not survive a clone.

```sh
python3 scripts/feature_workflow.py --execute complete <feature>:<task> --session <session-id>
```

Completion requires committed evidence/source files, the reviewed commit in
integration history, and the reviewed source tree unchanged except feature
`record.json` bookkeeping. Unrelated concurrent source changes conservatively
require renewed integration review. Then commit/push the completed record under
the existing authorization and select the next ready task.

Completed records preserve historical evidence at its original commit. Later
approved changes do not erase that history. Status reports whether the recorded
input hashes still match the checkout; historical evidence cannot be reused as
proof of a new implementation or a current hardware release. Release checklists
are updated only when their own acceptance criteria are satisfied.
Do not reuse an old passing verification for changed acceptance criteria. Use a
follow-on feature/improvement record for completed work, or explicitly reopen
and review affected acceptance before trying to replace its decision.

## Blocking, interruption and resumption

Use `block <task> --session <id> --reason <reason>` with `--execute` to pause an
owned task and continue other ready work. The worktree and lease remain intact.
For a physical dependency, update/link the existing human task entry and keep its
required power/connection state, steps and expected evidence explicit.

Use `runs` to inspect retained lease/worktree locations. After an interruption,
inspect the previous session and worktree using the current client's session tools.
Stop the previous worker before reclaiming ownership. The helper does not infer
that a timeout or PID disappearance means an agent has stopped elsewhere.

```sh
python3 scripts/feature_workflow.py --execute recover <feature>:<task> \
  --expected-run <recorded-run-id> --previous-session-stopped \
  --reason '<what was inspected and stopped; where unfinished work remains>'
python3 scripts/feature_workflow.py --execute resume <feature>:<task> \
  --reason '<changed evidence, diagnosis or method>'
```

Recovery checks the exact run identity to avoid releasing a newer owner. It marks
the interrupted task blocked and preserves all files. Resuming clears stale
submission/review metadata, not the old worktree or lease. Reuse preserved work
only after reviewing and moving it into a clean worktree based on current HEAD.
The same unsuccessful resumption reason retains the failure counter; after two
failed repeats, change the investigation rather than repeating it indefinitely.

An orphan lease without an active record cannot dispatch work. Inspect it before
cleanup; cleanup is deliberately a separate Git/filesystem operation. Missing
ownership/evidence is an inspection problem, never permission to claim completion.

## Validation and retirement

```sh
python3 -m unittest discover -s tests -p 'test_feature_workflow.py'
python3 scripts/feature_workflow.py validate
```

Tests use disposable Git repositories/worktrees and actual file locks. No paid
agent calls, printer access or network is needed for deterministic gate tests.
The pilot separately exercises live suggestion/review and actual product behavior.
For a live review evaluation, give the approver only
[the case inputs](../../tests/fixtures/feature-workflow/review-cases.json) and request
[the result format](../../.codex/schemas/review-cases.schema.json), then run:

```sh
python3 scripts/feature_workflow.py check-review-cases --result local/feature-workflow/review-cases.json
```

The check rejects missing, duplicated or incompatible decisions and requires the
owner boundary to remain intact. A successful process exit or structurally valid
empty response is not a successful evaluation. Inspect rationales and tool evidence
as well; deterministic outcome checks do not establish the quality of every review.
Retire custom coordination when upstream mechanisms cover these same tested
record, dependency, ownership and evidence guarantees; keep the regression cases.
