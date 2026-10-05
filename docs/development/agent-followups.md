# Agent-workflow follow-ups: gaps, safeguards and deliberate non-features

Date: 2026-10-05. Reviewed baseline: `121a261453829bfb9ad134981244722616be46a9`
(PR #4 merged). This is the deduplicated register of qualifications in the preceding
model-routing, execution, context and review discussions and PRs #1–#4. It is not an
exhaustive printer-product backlog, a second roadmap, or mandatory worker reading.
A repeated “not done” does not create a feature requirement or authorize an operation.

## Assessment

Some qualifications expose real opportunities: finish repeatable validation, assess
legacy adoption, observe actual resource use, and remove residual assumptions that
all work requires a reviewer. Others are essential distinctions: a passing fixture
is not a physical test, a model's assertion is not runtime metadata, and fewer bytes
of entry instructions are not measured billing savings. A third group is deliberate
scope control: no new framework, maximum-effort team, scheduler or speculative
hardening merely because it is technically possible.

The owner's approved direction is reversible development first, actual scoped tests,
selected review for a reason, and independent assessment for credible serious loss.
The [review decision](../decisions/20261005-proportionate-development-review.md)
supersedes blanket review instructions, not actual owner requirements or historical
facts. Current goals and owner exclusions outrank old phase descriptions.

## Complete deduplicated inventory

“Implement” identifies the small changes in this follow-up. “Runtime check” means
only the intended client/host can supply the evidence. “Retain” is not a backlog item.
Historical qualifications below are not presented as current failures without a check.

### Validation and delivery limits

| ID | Earlier qualification | Disposition and cost/benefit |
| --- | --- | --- |
| V1 | PRs were created/published but not merged; main was unchanged during those actions. | **Resolved for #1–#4.** #4 is merged at this baseline. Creating the next PR is still not permission to merge/deploy it automatically. |
| V2 | Container DNS prevented a full Git clone although connector reads/writes worked. | **Implement a different validation location:** bounded GitHub-hosted CI. Do not modify user DNS/security or repeatedly spend model turns retrying the same failed route. |
| V3 | Tests used reconstructed relevant source, not a complete checkout or original history. | **Implement full-checkout CI.** Keep historical local-test claims accurate; adding a workflow is not a passing run. |
| V4 | Full workflow tests and, most recently, two collateral-document policy tests were omitted. | **Implement:** run all workflow, policy, context and inventory tests without exclusions in CI. Existing tests remain intact. |
| V5 | Real queue/history, approval freshness, leases and worktree state were not fully validated. | **Implement** committed-record validation with full Git history plus read-only adoption inventory. Live leases, processes and local worktrees still need **runtime checks**; a clone cannot establish their state. |
| V6 | Independent review was not performed by this chat's author. | **Not a universal missing stage after #4.** Self-validation is legitimate. Obtain a reviewer when selected or consequential; never manufacture an independent identity. |
| V7 | Wider repository tests, builds, firmware, installed journeys, QEMU and physical tests were not run. | **Task-specific**, not mandatory for every policy/doc edit. Select relevant product checks when product code/acceptance changes; these tooling changes do not commission hardware. |
| V8 | Fresh-client role loading, model availability, effective effort/defaults/overrides and high-review profiles were not demonstrated here. | **Runtime check:** follow the existing execution runbook once per material client/config change, using source-only tasks. Do not infer success from TOML or a model's self-report. |
| V9 | Live role adherence, permission inheritance, disabled child delegation and fallback invocation were not demonstrated here. | **Runtime check:** use bounded disposable exercises and recorded settings. Do not pay for a nested agent as a negative test or switch billing to make a launch succeed. |

Sources: [PR #1](https://github.com/drew442/sv08-mainline/pull/1),
[PR #2](https://github.com/drew442/sv08-mainline/pull/2),
[PR #3](https://github.com/drew442/sv08-mainline/pull/3),
[PR #4](https://github.com/drew442/sv08-mainline/pull/4), and
[existing execution checks](agent-execution.md). The old runbook's universal-review
language is superseded by the current review decision.

### Adoption, history and unfinished work

| ID | Earlier qualification | Disposition and cost/benefit |
| --- | --- | --- |
| A1 | Existing v1 task records were not silently converted to v2. | **Implement assessment**, not bulk conversion. Inventory states/dependants; re-register only authorized unfinished work when it will actually be resumed. Migration with no active benefit creates churn and can revive abandoned scope. |
| A2 | Completed records, failed candidates, reviewer identities and evidence/decision hashes were not rewritten. | **Retain.** New policy does not change what actually happened. Keep failures and supersession links; never label a superseded dependency “done”. |
| A3 | Current authorization/freshness was not mechanically repaired after referenced files changed. | **Retain honesty; use #4's bounded recheck** for genuinely nonmaterial changes. Material scope/dependency changes need a new basis, not a hash-refresh workaround. |
| A4 | Running clients, obsolete workers, existing feature branches, worktrees and cached definitions were not automatically updated. | **Check only affected active work.** Inspect remote branch tips and local ownership, preserve work, then reload/reconcile. Do not force-push, kill unknown jobs or merge into an unrelated branch as a housekeeping side effect. |
| A5 | Removed role names are migration mappings, not working runtime aliases. | **Retain.** Use current roles for new assignments; preserve old names as historical evidence. No alias layer without a demonstrated consumer. |
| A6 | Rollback was not simply flipping v2 records back to v1 or reverting a binary while keeping unreadable data. | **Retain.** Preserve v2 data and use a compatible reader. Explicit conversion/re-registration is an operational decision, not automatic rollback. |
| A7 | The helper did not execute tests, determine truth of attestations, discover all semantic dependencies or prove risk classification. | **Retain this limitation.** Tests plus coordinator inspection provide evidence; `--checks-passed`, an empty hazards list or a syntactically valid record is not proof. Do not add a new risk engine to pretend otherwise. |

Sources: [current workflow](feature-workflow.md),
[current goals](../../.codex/current-goals.md),
[feature overview](../features/README.md), and the review decision.
The goals record says no authorized ready task and defers the next physical work;
that dated statement is not a substitute for inspecting current records/leases.
Searching for the word “pending” also matches historical prose: it is not a count
of pending task states. This follow-up does not claim a full-queue state census from
search snippets, and does not migrate any live feature record.

### Measurements and limits on claims

| ID | Earlier qualification | Disposition and cost/benefit |
| --- | --- | --- |
| M1 | Smaller entry-file byte counts were not observed token/context, latency or billing savings. | **Implement sampled observation.** Record actual reads/inheritance when exposed; do not convert source bytes into measured tokens. |
| M2 | Cache hits, cache writes and retained prompt prefixes were not measured or guaranteed. | **Observe when exposed.** Do not enlarge prompts just to improve hit rate. A path reference is not evidence of caching. |
| M3 | API token prices or benchmark USD were not the user's included Codex allowance or measured credit consumption. | **Retain separate units/billing modes.** No account/key/speed-mode change in pursuit of a misleading comparison. |
| M4 | Total project cost per accepted task, including coordinator work, retries, escalation, review and failures, was not measured. | **Implement a light sample using the existing form.** Include all linked attempts, avoid double-counting and keep unknowns unknown. No telemetry service or mandatory form for every tiny edit. |
| M5 | Project-specific first-pass quality, review value, escaped defects and wall-clock completion benefits were not established by the benchmark. | **Measure on ordinary work**, not a compulsory benchmark campaign. Compare similar task classes and include rework/waiting. Do not assume fewer reviews means identical outcomes without observation. |
| M6 | Benchmark plots used rounded labels; no confidence intervals, role-specific review accuracy, per-task overlap or retry independence were established. | **Retain.** Broad terminal-task scores inform routing; normalized cost/score is not the cost of retrying one particular task. Do not make statistical or hardware-safety claims from them. |
| M7 | Some early exact prices/model availability/effort-level claims were unverified; live chart values and links were inaccessible. | **Historical retrieval gaps, not new requirements.** The supplied charts and eight captures resolved the evidence needed for the accepted changes. Retain version/date/provenance; do not restore earlier unsupported headline claims. |
| M8 | Raw benchmark data, original screenshots and whole browser MHTML captures were not published in the repository; hashes alone do not make them retrievable. | **Keep compact attributed snapshots.** Preserve originals with source evidence. Add a sanitized export only for a concrete reproducibility need; browser assets/state and private transcripts are not useful default repo context. |
| M9 | Decode time was not end-to-end runtime; the compute-proxy plot supplied no usable comparison for these OpenAI models. | **Retain.** Record build, model, review and owner waiting separately; do not infer nonexistent compute coordinates. |

Sources: [benchmark assessment and CSV](codex-model-routing.md),
[context audit](gpt6-context-audit.md), and
[observation template](../../.codex/templates/agent-task-observation.md).
The new optional fields complement existing records; no new telemetry keys are
inserted into historical hashed authorization/verification contracts.

### Context, requirements and application-level features

| ID | Earlier qualification | Disposition and cost/benefit |
| --- | --- | --- |
| C1 | The docs library, older decisions and history were not deleted, moved wholesale or rewritten. | **Retain.** Improve selective retrieval, not erase evidence or break references. Archive/restructure only a demonstrated navigation problem with links preserved. |
| C2 | A smaller starting context was not permission to ignore relevant requirements, necessary dependencies or a selected review's relevant diff. | **Retain honesty; right-size the obligation explicitly.** See below: derived checks may be simplified when their cost exceeds value, without silently degrading owner goals. |
| C3 | There was no proof that all 605 indexed docs loaded automatically; byte budgets were not task-context caps. | **Retain.** Search counts are not a tracked-file census or reading trace. Expand context for a real gap and measure actual ingestion when possible. |
| C4 | No new skills catalog, domain-agent collection, retrieval database, summarizer agent or automatic router was added. | **Defer.** Add one only for repeated demonstrated work that existing paths/tools cannot handle more cheaply. A large docs directory alone is insufficient justification. |
| C5 | Native/API compaction, async tool calling and mid-turn steering were not implemented or enabled by repository prose. | **Runtime-specific, defer custom transport.** Keep durable state/process handles and reconcile changes; use supported native features when verified, not invented TOML keys or a parallel orchestration service. |
| C6 | Cache diagnostics were not a context loader, cache-enabling switch or implemented Codex request feature. | **Retain.** Diagnose through the actual runtime only when needed; API comparison IDs do not alter caching behavior. |
| C7 | Timeouts/changed direction did not prove a process stopped, cancel a write, or authorize duplicate/replayed work. | **Retain.** Observe the existing handle, reconcile actual effects and wait for real results. CI cancellation below is confined to disposable source-check jobs, not printer actions. |
| C8 | “Finish the task” did not grant unlimited retries, budget resets, or permission to weaken failing tests. | **Retain.** Primary work and incidental diagnostics have different budgets; fix in-scope failures and justify additional work. Change an unnecessary requirement openly, not after pretending it passed. |

### Model, team and runtime non-changes

| ID | Earlier qualification | Disposition and cost/benefit |
| --- | --- | --- |
| R1 | Luna was not replaced everywhere; all Sol roles were not reduced to low. | **Retain task-based routing.** Sol low for bounded engineering, medium for known hard reasoning, Luna for easily checked exact/mechanical work. Benchmark evidence is a starting point, not a universal role guarantee. |
| R2 | No mandatory Luna-high escalation rung or Astra/xhigh/max team was introduced. | **Retain.** Select a suitable effort directly; use exceptional higher effort for a concrete hard problem, not a missing fact or startup failure. |
| R3 | No model/effort variant was created for every responsibility; no permanent domain specialists or test-waiting agent remained. | **Retain simplicity.** Adjustable workers and direct scripts cover normal needs. A new profile requires a distinct recurring contract, not just a new label. |
| R4 | Main-session/user-global model, billing, API credentials and speed mode were not changed. | **Retain.** No global/account edits in this follow-up. Unsupported settings need an explicit real fallback, not silent substitution. |
| R5 | No extra live-agent concurrency, multiple running implementations or broader ready queue was added. | **Retain initially.** #4 already frees the implementation slot for unrelated work while a v2 candidate is frozen. Further parallelism needs measured throughput benefit and resource ownership, not more profiles. |
| R6 | No unattended agent schedule, server, external project-management database, background monitor or new dependency framework was introduced. | **Defer.** Event-triggered source CI is not unattended product development. Add a scheduler/dashboard only for an actual operational need; no timetable or paid model calls here. |
| R7 | Universal independent review was preserved in #1–#3; targeted review effort and actual usefulness were not optimized from project results. | **Universal gate resolved by #4.** This follow-up fixes the lingering verifier assumption in the observation form. Sample targeted-review value before adding more roles or automatically lowering all review effort. |

### Safety, evidence and product scope

| ID | Earlier qualification | Disposition and cost/benefit |
| --- | --- | --- |
| S1 | Full access, prompts, worktrees and disabled child tools were not enforced secret/device isolation. | **Retain truthful limits.** External controls may be worthwhile for a specific deployment; do not claim a prompt can enforce them or silently restore sandbox friction against owner policy. |
| S2 | Time/data/thread limits were procedural, not hard monetary caps or proof that a shell cannot start another agent. | **Retain.** Actual hard caps need external account/process controls. Consider those only for a concrete overrun risk, not as a new permission platform. |
| S3 | No packages, host security, services, user-global config, credential material or unassigned remote hosts were changed. | **Retain for the user's systems.** CI installs the existing test dependency only on its disposable hosted runner, with no printer credentials, self-hosted runner or deployment access. |
| S4 | PR publication, stronger models and passing source tests did not authorize physical writes, activation, deployment or release. | **Retain.** Target/recovery/preconditions and actual owner authority still apply; review is proportionate to credible consequences, not every harmless preparation. |
| S5 | Offline/build evidence did not establish named-hardware compatibility, physical input accuracy, thermal/motion safety, representative printing or a supported release. | **Retain distinctions; follow the actual product plan.** These are not tasks for this tooling PR and not evidence that every prototype needs full release assurance. |
| S6 | Accepted upstream pins, matched host/MCU builds, storage/data/mode/idle constraints, recoverability and heater protections were not weakened. | **Retain primary invariants.** A concrete simplification can be proposed with evidence and owner approval where it changes owner requirements; no unexamined regression. |
| S7 | No project-license selection, new external spending, speculative security protocol or blanket scope expansion was authorized. | **Retain.** Source CI adds no paid model/API workflow; hosted-runner use is bounded and still subject to repository/account policies. No branch protection or mandatory approval gate is configured. |
| S8 | Abandoned H12 replay/anti-forgery, entropy/permission expiry, RAM maintenance, separate rehearsal and full cold-capture work were not resumed. | **Keep abandoned.** Historical records of these are not migration candidates just because their status is blocked or pending. |
| S9 | Automatic maintenance launch/return, deferred physical inputs/calibration and broader first-print/release work were not completed. | **Keep their actual status and owner deferrals.** Manual SD recovery remains the selected H12 route. No hardware action or new physical request is created by this register. |

Sources: [H12 scope reduction](../decisions/20261002-h12-scope-reduction.md),
[current goals](../../.codex/current-goals.md),
[project definition](../project.md), and [execution policy](agent-execution.md).

## What this follow-up implements

The selected changes have a low maintenance cost and do not alter printer behavior:

* A pinned, read-only-token, single-job GitHub workflow runs deterministic workflow,
  instruction/context and inventory tests in a complete source checkout. It also
  runs committed-queue validation with history and reports recorded adoption state.
  No mandatory branch-protection gate, matrix, nightly run or paid agent call.
* `scripts/workflow_inventory.py` reports canonical record versions, **recorded**
  states, blockers and forward/reverse dependencies without touching records. It
  intentionally works without historical objects/local leases, so its output is
  not authorization, readiness or evidence verification. It cannot migrate, resume,
  cancel or complete a task. Unknown route/version and malformed inventory fail.
* The existing optional observation form no longer requires a verifier for a self
  task; it adds actual-context and check/review-value fields for selected samples.
* This register provides a finite cost/benefit decision for every caveat above. It
  is linked as optional coordinator material, not added to every worker's prompt.

The code adds no writer or new schema. Existing state-transition logic, v1/v2
contracts, model routing and ownership/physical boundaries are unchanged.

## Adoption: inspect first, convert only when useful

Run in a source checkout (inventory itself needs only the standard library):

```sh
python3 scripts/workflow_inventory.py
python3 scripts/feature_workflow.py validate
python3 scripts/feature_workflow.py status
```

Use the inventory's file hashes to identify the records inspected. `checkout_head`
is nullable and is not a clean-checkout attestation. The inventory validates only
fields it reports, not the full schemas. Its inspection actions are guidance:

| Inspection action | Coordinator response |
| --- | --- |
| `preserve_history` | Do not rewrite a recorded completed result. Full historical validation is a separate check. |
| `reconcile_active_assignment` | Inspect the real worker/lease/worktree before changing ownership or scope. A source clone cannot prove the worker stopped. |
| `respect_existing_blocker` | Read the actual blocker and current owner decisions. Do not infer cancellation/permission from free text or revive abandoned work. |
| `manual_hardware_or_human_queue` | Keep the canonical human task and existing deferral. A review-policy change does not dispatch hardware. |
| `assess_remaining_scope_for_v2` | Only if the work is still authorized and valuable now: re-register remaining checks/constraints and reconcile both dependency directions. This is not an automatic recommendation to migrate. |
| `use_v2_after_workflow_checks` | Use existing authorization/freshness/ownership checks; a v2 label is not ready status. |

For an eligible legacy task, follow [the operating guide](feature-workflow.md),
carry applicable requirements, constraints, dependencies and evidence references,
choose effects/recovery-based review, and cite the actual product authority (not
just the template's process-policy reference). Keep the old record and mark genuinely
superseded unfinished work blocked with the replacement reference. Do not turn a
superseded task into a completed dependency. Preserve failed selected reviews and
resolve their findings; v2 is not a way to relabel failure as success. No migration
is performed by this PR, because that requires a task-specific scope decision and
live ownership check, not a blanket rewrite of the queue.

## Right-size obligations, not truth

“Not a smaller correctness obligation” was a distinction about evidence, not a
claim that every accumulated requirement is optimal or permanently untouchable.
For a proposed simplification, identify the primary user outcome, the actual failure
it prevents, recovery options, implementation/testing/maintenance cost, and the
smallest retained check that still protects the goal. Make the decision before
claiming completion; record who has authority to change that requirement.

For example, a disposable inactive configuration editor need not repeatedly pass a
physical A/B power-loss campaign for a layout correction. It still needs the actual
layout/user-journey check it claims. The attended SD procedure does not need the
abandoned anti-replay platform; it still needs target identification, confirmation
and complete write/readback because those are the selected procedure's requirements.
Changing heater protections or declaring an untested profile supported is not the
same kind of simplification. A targeted test/review cannot silently become a claim
that all behavior, hardware or release criteria were verified.

No numeric risk score or mandatory proposal form is introduced for ordinary edits.
Use existing authorization/records for a material requirement change and preserve
explicit owner choices. This is how cost/benefit can reduce unnecessary scope without
changing test reports to conceal a regression.

## Measurement and validation plan

On normal authorized work, sample actual read paths/inherited context when exposed,
model/effort, total observed usage, relevant tests, rework and outcome. Separate model,
build/tool, review and owner waiting. Use the existing observation template only for
representative tasks, exceptions and suspected waste. Do not buy duplicate production
runs or collect raw private prompts just to establish a benchmark. Unknown stays
unknown; a sampled improvement is not a universal saving. Tune model/effort, role
routing or review depth only when the observation supports the change.

The workflow has a ten-minute whole-job limit and cancels only superseded disposable
CI runs for the same PR/ref. It checks relevant source/doc changes and manual requests,
not a recurring schedule. Dependencies are the already documented `python3-jsonschema`
on an Ubuntu hosted runner; checkout fetches history but no submodules/LFS and does
not persist credentials. `pull_request`, not `pull_request_target`, is used. Failed
queue validation is visible; records/hashes are never repaired by CI. New CI is not
configured as a required check, so path-filtered runs do not introduce a new merge gate.

A complete Git history may still expose missing/unreachable legacy evidence or a live
lease unavailable on CI. Record the exact cause; do not mark it passed or fetch private
runtime state into CI. Runtime smoke tests and relevant product/hardware tests remain
separate. Adding CI does not prove it ran, and a CI pass does not prove effective
Codex model/permissions, actual savings or printer support.

Local validation of this follow-up: 18 inventory tests passed, including a real
subprocess CLI, byte preservation, malformed input, unknown routes, duplicate keys,
symlink refusal and dependency reporting. Source/JSON/YAML/whitespace checks are
recorded in the PR. Full-checkout test/queue results must be read from the actual CI
run; the execution container still cannot clone GitHub. No independent agent review
is claimed or required for this self-validated source-only tooling change.

Official CI reference: [GitHub workflow triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
The pinned [checkout action](https://github.com/actions/checkout/blob/11d5960a326750d5838078e36cf38b85af677262/action.yml)
was inspected for fetch-depth, credentials and submodule settings. CI workflow writes
or hosted execution can be blocked by installation/repository policy; report that
limit rather than changing account settings or asking for broader credentials.
