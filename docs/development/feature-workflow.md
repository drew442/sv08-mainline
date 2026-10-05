# Operating the feature workflow

Implements the [development review decision](../decisions/20261005-proportionate-development-review.md).
This source-workflow helper records authorization, ownership and evidence. It does
not launch agents, run test commands, operate hardware, merge/push Git, schedule work
or establish a sandbox. Use Python 3.11+ and `python3-jsonschema` on the workstation.
Workers load their role and relevant task sources, not this whole operating guide.

## Choose the actual review need

| Route | When | Completion basis |
| --- | --- | --- |
| `self` | Authorized reversible development, including substantive code | Actual implementer check evidence; no second agent or fabricated decision |
| `targeted` | A concrete question benefits from another perspective | Implementer validation plus the explicitly requested review |
| `consequential` | Credible serious loss | Validation plus independent assessment before the hazardous transition |

Declare hazards as applicable: physical-harm, hardware-damage, unrecoverable-state,
irreplaceable-data, secret-disclosure or external-impact. A nonempty hazard list
requires `consequential`; a missing/unknown policy never defaults to self. These are
reported classifications, not an automated safety analysis. An empty list is not
proof of safety. Preparation and execution can have different classifications.
Hardware actions remain with the coordinator and their real authorization/prechecks;
no format or `--checks-passed` flag makes them dispatchable.

Keep planning optional. `feature_approver` is an optional design/scope challenge, not
an obligatory stage for an owner-requested feature. Use medium/high only when the
reasoning warrants it. A reviewer may check a correction it suggested and an approver
may review delivery, unless it materially authored the solution. Do not spawn a new
reviewer merely because useful feedback was adopted. Material authors cannot provide
independent verification of their own work. Blocking findings need an accepted requirement,
demonstrated defect or concrete loss mechanism; optional hardening is not a veto.

## Register a new version-2 task

Copy [.codex/templates/record.json](../../.codex/templates/record.json) to
`docs/features/<id>/record.json`. Set its ID, dates, task/check IDs, environments,
review policy/reason, owned paths and dependencies. Use a short `proposal.md` stating
the outcome, scope, acceptance checks and authorization reference; a full design
proposal is needed only for an actual design question. Existing product requirements
remain authoritative. `decision` is null when no independent design decision occurred.

`owned_paths` names exact tracked files the task may change, including its evidence
document. Do not include shared record.json bookkeeping. `input_paths` names relevant
additional dependencies; a trailing `/` protects an entire subtree, including new
files. No globs. Both are part of authorized scope. Evidence input paths, proposal
and requirement files are added to the protected footprint automatically. Explicitly
include build/config/import dependencies; the helper cannot discover semantic coupling.

Include the actual public authorization reference among `requirements`; it may be
a recorded owner request or accepted standing scope. Commit scope/requirement sources,
then register that existing authority from the primary checkout:

```sh
python3 scripts/feature_workflow.py review-context <feature>
python3 scripts/feature_workflow.py --execute authorize <feature> \
  --actor coordinator --session <coordinator-session> --basis standing \
  --reference docs/decisions/<actual-authority>.md \
  --reason 'This bounded task is within the cited standing scope; no new owner decision.'
```

Use `--basis owner-request` for a direct recorded owner decision. Tasks marked
`owner_decision_required` cannot use standing authority. The tool does not determine
whether the cited text truly grants permission; inspect it, do not invent it. `authorize`
binds the committed scope/requirements, actual actor and source revision. It is not an
independent approval. Replacing an unused authorization requires a committed prior
record; no live/completed authorization is overwritten. A requested design review in
`decision` must be approved and match the same scope/requirement snapshot, or work waits.

Commit/push the registered record under standing source-publication authority.
No secret, transcript or private dump belongs in a public requirement/evidence file.

## Claim, implement and submit actual results

The coordinator uses these commands; delegated workers do not select the global queue:

```sh
python3 scripts/feature_workflow.py validate
python3 scripts/feature_workflow.py status
python3 scripts/feature_workflow.py next
git worktree add -b feature/<feature>-<task> local/feature-workflow/worktrees/<feature>-<task> HEAD
python3 scripts/feature_workflow.py --execute claim <feature>:<task> \
  --actor <implementer> --session <implementation-session> \
  --worktree local/feature-workflow/worktrees/<feature>-<task>
```

Only one task is `running`. V2 `review` and `validated` candidates release that slot,
but reserve their owned/input paths. Conflicting or dependent work waits; unrelated
v2 work can proceed with a distinct worktree/resource allocation. The two-child cap
remains a runtime/coordinator constraint, not a count of all durable queued records.
Keep submitted candidates frozen until completion. A timeout does not end ownership.

Implement, run relevant checks, inspect results and fix in-scope failures. The coordinator
commits the complete candidate and sanitized evidence in the assigned worktree. Prepare
an evidence list using the existing [evidence schema](../../.codex/schemas/evidence.schema.json):
one result per assigned check, actual commands/method, limitations, document/input hashes
and exact clean candidate HEAD. Test failures are blockers, not evidence of passing.

```sh
python3 scripts/feature_workflow.py --execute submit <feature>:<task> \
  --session <implementation-session> --evidence local/feature-workflow/evidence.json \
  --checks-passed --reason 'State the actual checks run, inspected results and remaining limits.'
```

`--checks-passed` attests observed results on behalf of the identified implementation
actor/session. It does not execute checks or prove the claim. The tool binds a distinct
`validation` object to those results, the candidate and authorization. It never invents
an independent reviewer. `self` enters `validated`; `targeted`/`consequential` enter `review`.
Missing evidence, ownership violations, dirty candidates or absent attestation fail.

## Review only when selected; then integrate

For `self`, skip `verify` entirely. For a requested review, give the actual candidate,
full diff for context, declared question/consequence and relevant validation evidence to
an appropriate independent session. Do not make it audit unrelated features. Use
[verification-v2.schema.json](../../.codex/schemas/verification-v2.schema.json).
Its `basis_sha256` is the SHA-256 of canonical JSON containing the full `authorization`
and `decision` values (including null); `evidence_sha256` hashes the submitted list.
Canonical JSON uses sorted keys and comma/colon separators. `review-context` and `packet`
report the current basis digest; the reviewer must inspect the actual bound inputs.

```sh
python3 scripts/feature_workflow.py --execute verify <feature>:<task> \
  --result local/feature-workflow/verification.json
```

Selected reviews must pass; failures block the task. A reviewer cannot share the
implementation actor or session. A passed targeted review answers the scoped question,
not a blanket hardware or release certificate. A substantive author cannot become
independent by changing a label; identity fields are not an anti-forgery mechanism.

The coordinator merges the actual validated/reviewed commit, preserving it in history,
and runs necessary integration checks. Evidence/owned/input changes, modes, deletions
and gitlinks are checked; unrelated committed changes no longer demand blanket re-review.
Uncommitted source outside record bookkeeping remains a conflict to reconcile, not
permission to discard someone else's work. Rebase/squash changes candidate identity:
submit current evidence again rather than asserting the old commit was integrated.

```sh
python3 scripts/feature_workflow.py --execute complete <feature>:<task> \
  --session <implementation-session>
```

Completion requires its recorded basis, committed evidence and preserved candidate.
It is reported as self, targeted or consequential, not universally independent.
Commit/push bookkeeping and continue. Keep candidate worktrees until completion so
freeze/ownership checks can inspect them. Later code changes do not erase historical
results; they may make those results inapplicable to the new checkout.

## Nonmaterial requirement changes

Whole-file hashes remain exact. When only unrelated explanatory text changed in a
requirement document, a coordinator can inspect the actual old/new diff and record
why this task's requirements and checks are unchanged. Commit the changed documents,
then use `review-context` to obtain `expected_recheck_sha256`:

```sh
python3 scripts/feature_workflow.py --execute recheck-requirements <feature> \
  --actor coordinator --session <coordinator-session> \
  --expected-sha256 <expected_recheck_sha256> \
  --reason 'Describe the exact nonmaterial change and why task acceptance is unchanged.'
```

The append-only recheck chain records original/new hashes, rationale and the actual
commit. Original authorization/decision/reviewer hashes stay unchanged. It cannot
replace task/proposal scope, the authorization reference or non-Markdown requirements.
It cannot bypass changed owned files, test inputs or evidence source paths, even if
those are also Markdown requirements. Fresh unacknowledged changes still block.
This is a coordinator judgment, not machine proof of semantic equivalence. Material
requirement changes need revised scoped work and the appropriate authority/review;
never call them nonmaterial merely to avoid rework. Leave completed historical records alone.

## Existing records, interruptions and checks

Version 1 remains readable under its unchanged schema. Its original approval,
independent verification, whole-tree freshness and review reservation still apply.
This is intentional compatibility, not the default for new work. The new template is
v2. No automatic/bulk migration is performed. Do not flip version numbers or invent
reviews. For unfinished legacy work, explicitly re-register remaining scope with its
requirements, dependencies and applicable constraints, retain the original record,
and mark superseded unfinished tasks blocked with the replacement reference. Update
future dependencies explicitly; a superseded task is not a completed dependency.
Completed tasks and their evidence/identities are never rewritten.

Existing `block`, `runs`, `recover` and `resume` commands retain leases/worktrees and
explicit stopped-session checks. Commit failed results before resumption. Rework
carries attempt history and budgets; the same reviewer may inspect the repair.
Resume clears stale submission/validation, not private artifacts. Never relabel a
failed review as self to skip its finding. Legacy verification still uses
[verification.schema.json](../../.codex/schemas/verification.schema.json) and its original
`decision_sha256`; v2 uses the distinct basis format. Both validate real source evidence.

```sh
python3 -m unittest discover -s tests -p 'test_feature_workflow*.py' -v
python3 -m unittest discover -s tests -p 'test_codex_agent_policy.py' -v
python3 -m unittest discover -s tests -p 'test_agent_context.py' -v
python3 scripts/feature_workflow.py validate
```

Tests use disposable Git repositories and no paid agent calls or hardware. They prove
record transitions and guards, not model behavior, semantic dependency completeness,
actual safety classification or the truth of a submitted test report. Real queue/history
validation requires a complete checkout. No API transport, scheduler, model or permission
change is introduced. All mutations remain inspection-only unless `--execute` precedes
the subcommand; shared records remain locked and coordinator-owned.
