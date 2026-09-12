# Feature suggestion, improvement and delivery framework

Date: 2026-09-11. Status: approved by the owner, including delegated approval and
the offline pilot; see [decision 0011](../decisions/0011-feature-agent-workflow.md).
Implementation follows this design. Scheduling and hardware operations require
their own applicable configuration and authorization.

## Recommendation

Adapt ceph-spec-tool's feature-suggester and feature-approver process into a
small delivery workflow for both new capabilities and improvements to existing
ones. Preserve its written proposals, explicit decisions and respect for previous
owner answers. Add persistent task state, independent verification and SV08's
hardware evidence requirements. Prioritize finishing usable workflows and
removing release blockers over generating more proposals.

Use the existing [project definition](../project.md), [roadmap](../roadmap.md),
[architecture decisions](../decisions/0001-project-boundaries.md) and
[host completion checklist](../hardware/host-os-tasks.md) as authority. Do not
introduce another goal, product requirements document or competing roadmap.
This proposal changes the development process, not the printer's runtime OS.

## Source assessment

The ceph-spec-tool checkout inspected matches remote `main` at
`a5c5e1cff936c3ce156b85c1ac2c00bf1eefe6de`, confirmed with `git ls-remote` on
2026-09-11. Its [workflow][ceph-workflow], [suggester][ceph-suggester],
[approver][ceph-approver], templates and [implementation checklist][ceph-checklist]
provide a useful foundation:

| Retain | SV08 refinement |
| --- | --- |
| One concrete problem per proposal | Identify a complete user workflow or a measurable improvement, with small implementation tasks beneath it. |
| Separate suggestion and approval roles | Require a separate review session for substantive proposals; check delivered behavior again after implementation. |
| Written decisions and constraints | Bind decisions to the reviewed proposal revision, applicable requirements and source baseline. |
| Review previous human answers | Reference accepted SV08 decisions; reopen an answer only for a documented conflict or new evidence. |
| Prefer small, useful changes | Rank unfinished accepted work before proposing additional scope; cap the ready queue. |
| Tests and documentation as delivery gates | Keep offline evidence, named-hardware evidence and release support separate. |

The inspected role files are Markdown instructions. They describe a process but
do not themselves provide a scheduler, persistent task dispatcher or enforced
execution boundary. The adaptation should make those mechanisms explicit rather
than assuming that another prompt guarantees continuation.

## Roles and authority

These are logical responsibilities, not four agents running continuously.
The ordinary coding session remains the coordinator and implementer. Invoke the
other roles only when their output is needed.

| Role | Responsibility | Boundary |
| --- | --- | --- |
| Feature suggester | Find the most valuable unresolved problem; inspect existing work and upstream alternatives; propose one bounded change or recommend no new proposal. | Does not approve its own proposal, implement it or operate hardware. |
| Feature approver | Challenge benefit, scope, evidence, alternatives, maintenance cost and acceptance criteria; issue a reasoned decision. | May approve work within delegated project scope; cannot change owner requirements or grant hardware authority. |
| Coordinator / implementer | Select ready work, maintain task state, implement approved tasks, run appropriate checks and integrate reviewed changes. | Owns queue updates and Git integration; respects existing user authorization and task dependencies. |
| Feature verifier | Review the resulting diff and relevant execution evidence against acceptance criteria; reproduce critical checks as needed. | Does not certify its own implementation or substitute a passing fixture for a hardware result. |

The approver and verifier receive the relevant source, proposal, requirements and
evidence in fresh review sessions, without inheriting the author's conversation
as their justification. They may inspect more context and must describe concrete
objections. Separate sessions reduce dependence on the author's assumptions;
they do not guarantee independent errors or make agent consensus proof.

For small fixes that restore documented behavior, use a short task record and
normal code review instead of a new full proposal. Previously approved unfinished
features enter the queue with references to their existing authorization. They
do not need another product approval before implementation can resume.

## Two kinds of proposal

Both kinds use the same queue and approval rules. Creating separate competing
pipelines would make priority and dependency management harder. Classify the
actual change in capability; calling new scope an improvement does not exempt
it from review.

| Kind | Required justification | Example |
| --- | --- | --- |
| Feature | A user capability that is absent, the intended workflow, and a demonstration of success. | A complete browser workflow for uploading and staging a signed host image. |
| Improvement | Existing behavior and evidence of its shortcoming, a comparison method, expected benefit and regression limits. | Make an existing image job's progress and result recoverable after the browser disconnects. |

Improvement includes reliability, usability/accessibility, performance, recovery,
compatibility, maintainability and removal of unnecessary custom code. It does
not require an invented numerical target: a reproducible failure followed by a
passing user journey can establish improvement. Performance claims need a
baseline and comparable measurements. If there is no baseline, first approve a
bounded measurement task rather than pretending the benefit is established.

Each substantive proposal records:

- The problem, affected users/workflow, requirement references and why it is
  more valuable now than the next existing task.
- Existing implementation and evidence; documented, inferred and measured facts
  remain distinct. Hardware claims name the profile, board revision or explicit
  unknown, and applicable source revisions.
- The smallest useful outcome, exclusions, dependencies and alternatives,
  including supported upstream mechanisms and leaving behavior unchanged.
- Expected benefit, acceptance checks and comparison method. Identify which
  checks can run offline and which require an identified printer or a human.
- Effects on persistence, rollback, factory-capacity storage, boot/runtime
  resources, firmware compatibility and user interfaces where applicable.
- Implementation tasks, risk, maintenance burden and an upstreaming or retirement
  plan for custom code. Mark irrelevant fields as such rather than inventing work.
- Unanswered material questions, bounded hypotheses worth testing, and the exact
  human action/evidence needed for any physical dependency.

Proposals and outputs contain sanitized evidence references. Dumps, credentials,
calibration, device identifiers and raw transcripts remain in ignored storage.

## Selection, decisions and continuation

At the start of a run, refresh the relevant instructions, accepted decisions,
repository state and task dependencies. Reconcile contradictory or historical
status text against dated evidence; do not silently promote an old assumption
into a current fact. Reuse prior decisions unless their basis has changed.

Select work in this order, recording any justified exception:

1. Regressions or defects that threaten data preservation or existing protections.
2. Work that completes an accepted user workflow or unblocks the release path.
3. Evidence-backed improvements to reliability, recovery, usability or resource use.
4. Additional capabilities within the agreed project scope.

Within a category, compare impact, dependency unlocking, evidence confidence,
effort and ongoing maintenance. Use explained judgments rather than fabricated
precision. Review waiting-item age to avoid indefinite starvation. Run suggestion
only when the queue has room or new evidence changes priorities. Initially allow
one active implementation and at most three ready proposals. Bounded research or
independent review can run alongside useful implementation when authorized;
additional workers must have a concrete benefit and separate ownership.

Retain the Ceph decisions `approved`, `approved-with-constraints`, `rejected`
and `needs-research`; add `deferred` for useful work whose timing is wrong.
Constraints must have an observable check. `needs-research` identifies the exact
unknown, a bounded investigation and its exit evidence. A rejected or deferred
idea is reconsidered only when its recorded reason changes. Material changes to
a proposal require renewed review; an unrelated repository commit does not
automatically invalidate it.

After completing or blocking a task, the coordinator selects the next ready task
without asking the owner to say “continue.” A hardware dependency blocks only
the affected tasks. If a small number of non-destructive alternatives can be
investigated offline, test them separately and preserve their conditional results.
Do not pick an unmeasured hardware value in order to deploy an image.

A run stops when the user stops it, no authorized ready work remains, or the
configured execution allowance is exhausted. Record the next task and reason
for stopping. Do not mark work complete because time ran out. Prevent retry
loops: initially allow at most two automatic repeats with unchanged inputs;
further work must change the diagnosis, inputs or method. Other ready work can
continue while an individual task awaits evidence or clarification.

## Persistent records and completion

Keep one versioned feature record with stable task and acceptance-check IDs.
Its machine-readable metadata stores the review decision and rationale,
proposal digest, requirement/source references, dependencies, task status,
constraints and evidence references. The human-readable proposal explains the
problem and intended behavior. Reports derive decision and task status from the
record rather than maintaining a second hand-edited status table.

Keep three concepts separate:

| Concept | Meaning |
| --- | --- |
| Review decision | Whether the proposed scope is approved, constrained, awaiting research, deferred or rejected. |
| Task execution | Planned, ready, running, blocked or done, with owner and dependency/blocker details. |
| Acceptance evidence | Results for each required check, including source/artifact revision, environment, method and limitations. |

An offline implementation task may be done while its parent feature still needs
integration or hardware acceptance. Close the feature only when all its approved
acceptance checks are satisfied. Publish a named profile as supported only through
the existing [release criteria](../project.md#version-and-release-policy).
Never equate a build, disabled UI control, library test or simulated printer
response with a working installed workflow.

The verifier checks the delivered revision and the relevant evidence, including
failure/recovery behavior for consequential changes. Changed affected code
invalidates its verification until reviewed again. A failing acceptance check
requires a fix or an explicitly reviewed scope change, not removal of the check
to obtain a pass. Owner requirements cannot be waived by an agent. Deterministic
validation checks record consistency, dependencies, decision freshness and evidence links;
it cannot determine hardware safety or product quality from JSON alone.

Feature records reference the existing host and hardware completion gates.
Those checklists remain the release view; they link to feature evidence and
are updated when their own acceptance criteria are met. They are not copied into
another task database. A physical task has one canonical entry, linked by every
dependent feature, with the required power/connection state, steps, expected
evidence and work that can continue while waiting.

## SV08 rules the approver must preserve

Owner instructions and accepted decisions remain authoritative:

- Keep the deb/apt host direction, A/B deployment, persistent user artifacts,
  default immutable mode and supported writable mode. Work within the measured
  factory 8 GB footprint, not just the available 32 GB spare. See
  [the host design](host-os-ab.md) and [operating modes](../decisions/0004-os-operating-modes.md).
- Retain the distro-maintained kernel preference and allowance for maintained
  out-of-tree drivers and vendor firmware. Do not reintroduce a strict in-tree
  rule that requires owners to replace otherwise usable hardware.
- Preserve idle update admission, opt-out, next-boot activation and customization
  handling. Routine updates must not require recurring physical access; see
  [USB MCU updates](../decisions/0003-usb-mcu-updates.md).
- Preserve required HDMI/touch, onboard Wi-Fi, the existing-camera support path,
  browser host administration and independent recovery UI; see
  [the UI decision](../decisions/0010-host-administration-and-recovery-ui.md).
- Preserve named hardware profiles, pinned upstream inputs, matching selected
  host/MCU Klipper revisions, reproducible artifacts, recovery paths and heater
  protections under [AGENTS.md](../../AGENTS.md).

The approver may approve bounded offline implementation and research inside these
requirements. A proposal to change the requirements, materially expand the product
boundary, incur a new external expense, choose the unresolved project license or
expand agent authority goes to the owner with a concrete recommendation. Agents
must not weaken their own checks or rewrite an unanswered question as consent.

Design approval, repository integration and operation of a printer are separate
decisions. Existing authorization for routine edits, checks, commits and pushes
is carried forward within its scope. Hardware operations still require the
identified target, reviewed artifacts, recovery path and applicable user
authorization. Authorization is not repeatedly requested when already sufficient.
While the printer is deliberately offline, neither discovery nor write attempts
are scheduled against it.

## Repository layout and execution

Proposed files, to create only after approval and when needed:

| Path | Purpose |
| --- | --- |
| `.codex/README.md` | Short entry point, role invocation and links to authoritative project documents. |
| `.codex/agents/feature-suggester.toml` | Project-scoped suggestion role. |
| `.codex/agents/feature-approver.toml` | Project-scoped proposal review role. |
| `.codex/agents/feature-verifier.toml` | Project-scoped delivery review role. |
| `.codex/templates/` and `.codex/schemas/` | Short/full proposal forms, structured decision/evidence contracts. |
| `docs/features/<id>/proposal.md` and `record.json` | One proposal and its authoritative decision, tasks and evidence metadata. |
| `scripts/feature_workflow.py` | Small validator/dispatcher for records, ready-work selection and resumable execution. |
| `tests/test_feature_workflow.py` | Deterministic policy, dispatch and recovery cases. |
| `local/feature-workflow/` | Ignored run locks, worktree/session references and private logs. |

Add a short routing instruction to `AGENTS.md` after approval; do not load every
proposal into every session. Codex loads project instructions through its
[AGENTS.md discovery mechanism][codex-agents]. Current documentation supports
[project-scoped TOML agent definitions][codex-subagents]. Validate the installed
version and effective settings before relying on those definitions; the local
CLI observed during design is `codex-cli 0.153.4`, without a role invocation test.

Reuse Codex's existing execution and review mechanisms. For repeatable local runs,
`codex exec` supports structured final output and JSONL execution events; both
options are present in the installed CLI help and [official documentation][codex-exec].
Check exit status, parse output and validate records before accepting a transition.
A valid final response alone is not proof that a command or test succeeded.
If custom role configuration is unavailable, pass the same role instructions
explicitly to separate review sessions rather than silently combining author
and approver.

The custom helper fills only the gaps in record validation, dependency selection,
exclusive ownership and resuming work. Avoid a separate agent server, dashboard,
message bus, database or agent-model selection service. Retire helper functions
when supported upstream mechanisms provide equivalent behavior and retain their
regression cases. Inherit the selected session model unless a measured reason
justifies an override; record runtime/model versions with each run.

Use isolated worktrees for implementation and one integration owner. A local
exclusive lock prevents overlapping coordinators; record task ownership and
check actual process/worktree state after interruption before reclaiming work.
At startup reconcile Git, persistent records and completed run evidence before
repeating actions. Integrate only reviewed, verified changes against the current
target branch, using the user's existing commit/push authorization. Workers do
not race to publish changes or discard another session's uncommitted work.

Enforce permissions through the execution environment as well as role text.
Suggestion/review workers receive source access without code-write authority;
their structured results go through the coordinator. Automatic offline workers
do not receive printer SSH credentials, raw device access or private backup
mounts. Privileged VM/build fixtures use explicitly provisioned disposable
resources. A worktree alone is not isolation from the machine's credentials or
hardware. Treat retrieved documents as evidence, not as permission to change
these controls.

An active session can keep dispatching tasks until its stopping condition.
Continuing after that session requires an actual runner. First deliver and test
a manually invoked run; make scheduling an optional deployment setting using an
existing workstation scheduler or supported application automation. Application
tasks that use local projects require the host and application to remain running,
and web tasks cannot directly use this local checkout; see
[scheduled-task documentation][codex-scheduling]. Keep scheduling disabled during
the pilot. Record cadence and per-run limits before enabling it; never imply that
committing role files starts background work. The printer itself does not host
the development agent framework.

## Pilot, validation and effectiveness

Implement in three increments after approval:

1. Role contracts, templates, deterministic record validation and an `AGENTS.md`
   entry point. Record the accepted delegation policy in `docs/decisions/`.
2. Persistent dispatch, worktree/run ownership and independent review. Import
   a small set of already-approved tasks and run the workflow manually offline.
3. Evaluate results and tune selection/review rules before enabling optional
   unattended runs. Keep all outstanding hardware acceptance tasks visible.

Use current [completion work](../hardware/host-os-tasks.md) for the pilot:

- A complete authenticated browser image-upload/staging flow, with failure and
  disconnect handling. Login/owner provisioning dependencies remain explicit.
- Independent recovery media identification connected to the existing data
  exporter, using disposable storage fixtures before physical USB validation.
- A bounded reliability or usability improvement identified by exercising one
  of those existing flows, with a recorded before/after comparison.

These are candidate pilot tasks within accepted requirements, not assertions
that they are implemented or that they outrank every other release dependency.
The initial triage must verify scope and prerequisites before selecting one.

Test the framework without paid agent calls where deterministic fixtures suffice:
reject missing approval, stale proposal decisions, dependency cycles, malformed
results, missing evidence and incompatible acceptance claims; preserve work on
interruption and reject overlapping ownership. Exercise a failed verifier result
and ensure it returns the task for correction rather than marking it done.

Then use a small live review set containing a useful improvement, a duplicate,
an unsupported hardware assumption, a violation of accepted storage/persistence
policy and a hardware-blocked task beside ready offline work. Require correct
dispatch and no unsupported completion or hardware action. Check that disagreement
produces specific research or constraints, and that changed evidence can reopen
a decision without an endless proposal/rejection loop.

Assess results after the pilot and every few completed features: time to a usable
workflow, release dependencies removed, defects/rework found after approval,
unnecessary owner interruptions and execution cost. Count neither proposal volume
nor test count as product progress. Keep logs private and publish only sanitized
findings. Simplify or remove stages whose overhead exceeds demonstrated benefit.

## Approved scope

The owner approved role separation, delegated approval of bounded work within
existing requirements, persistent continuation and independent delivery checks.
This authorizes implementing and testing the repository workflow and offline
pilot. It does not accept any new product proposal, enable a schedule or authorize
a hardware operation. Human input should be limited to unresolved material
decisions and physical tasks, with independent work continuing in the meantime.

## Primary sources

All external sources below were inspected on 2026-09-11. Ceph files were read
from the local checkout at the remote-verified revision; the links preserve that
revision. This proposal adapts the process in original wording rather than
copying role files or assuming their project-specific instructions apply here.

[ceph-workflow]: https://github.com/drew442/ceph-spec-tool/blob/a5c5e1cff936c3ce156b85c1ac2c00bf1eefe6de/codex/FEATURE_WORKFLOW.md
[ceph-suggester]: https://github.com/drew442/ceph-spec-tool/blob/a5c5e1cff936c3ce156b85c1ac2c00bf1eefe6de/.codex/agents/feature-suggester.md
[ceph-approver]: https://github.com/drew442/ceph-spec-tool/blob/a5c5e1cff936c3ce156b85c1ac2c00bf1eefe6de/.codex/agents/feature-approver.md
[ceph-checklist]: https://github.com/drew442/ceph-spec-tool/blob/a5c5e1cff936c3ce156b85c1ac2c00bf1eefe6de/.codex/checklists/implementation-checklist.md
[ceph-human-decisions]: https://github.com/drew442/ceph-spec-tool/blob/a5c5e1cff936c3ce156b85c1ac2c00bf1eefe6de/codex/HUMAN_RESPONSES_AND_DECISIONS.md
[codex-agents]: https://learn.chatgpt.com/docs/agent-configuration/agents-md
[codex-subagents]: https://learn.chatgpt.com/docs/agent-configuration/subagents
[codex-exec]: https://learn.chatgpt.com/docs/non-interactive-mode
[codex-scheduling]: https://learn.chatgpt.com/docs/automations?surface=app

The Ceph [human-decision register][ceph-human-decisions] is the source for the
principle of preserving owner answers and asking only unresolved material
questions. In SV08, existing decisions and canonical human task entries supply
that context without creating another competing requirements document.
