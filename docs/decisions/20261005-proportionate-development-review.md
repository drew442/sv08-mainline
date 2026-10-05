# Proportionate development review

Date: 2026-10-05. Authority: the owner requested the follow-up PR after accepting
that universal independent approval/verification is disproportionate for this
project's development loop. Base: merged PR #3, `68b2b3675f012d44eb71bdb7d7c26801d5e0328d`.
Implementation is proposed here; merging is not a hardware-operation authorization.

## Decision

Authorized, reversible development is self-validated by default, including
substantive features and semantic fixes. Implement, run proportionate checks,
inspect the results and correct failures. No routine separate design approver or
fresh delivery verifier. Planning is optional. A direct owner request or existing
standing scope is recorded as authorization, not disguised as an independent decision.

Use a targeted reviewer when another perspective can resolve a named uncertainty.
Once explicitly selected for a task, that review must pass before completion.
Do not turn a failing targeted review into self-validation by relabelling the task.
A reviewer can check the implementer's response to its own feedback. An approver
can review delivery if it did not materially author the solution. Material coding
or solution-design authors cannot independently assess their own implementation;
identifying defects and suggesting corrections alone is not such authorship.

Require independent consequential assessment before credible physical harm,
hardware damage, loss of usable recovery, irreplaceable data loss, secret disclosure
or material external effects. Assess actual effects and recoverability, not subsystem
names, patch size or the word "feature". An offline patch or recoverable failed boot
is not itself an irreversible operation. Put the gate before the hazardous transition.
Do not restore withdrawn H12 anti-forgery/replay, RAM maintenance or cold-capture work.

Reasoning effort, independent review and execution authority are different decisions.
Difficult harmless diagnosis may warrant high effort; a simple repeated operation may
need only current precondition checks inside a previously reviewed procedure's scope.
Reuse the reasoning only when target/artifact classes, write boundary, recovery and
safety-relevant assumptions are explicitly covered. Recheck actual current facts;
changed safety-relevant inputs or an arbitrary new binary need reassessment. A review
cannot establish missing physical evidence or replace actual owner authorization.

Blocking findings identify an accepted requirement, demonstrated defect or concrete
serious-loss mechanism, with the smallest proportionate response. Speculative hardening
is non-blocking. Review must not silently add a threat model, protocol or acceptance
campaign. Required checks are not removed just to obtain success.

## Records, scheduling and provenance

New version-2 records explicitly select `self`, `targeted` or `consequential`, with a
short reason, declared hazards, owned files and relevant inputs. The workflow records
actual implementer validation separately from optional independent verification.
The program validates reported evidence/metadata; it neither runs tests nor proves
risk classification, reviewer independence, test truth or runtime isolation.

One implementation may run at a time. Frozen v2 candidates awaiting review or
integration reserve their outputs and input dependencies, not the whole implementation
slot. Independent work may continue under the two-child cap and exclusive fixtures.
Physical tasks remain manually coordinated and are never dispatched by this helper.

Keep exact candidate commits and evidence hashes. V2 integration can include unrelated
committed changes, but affected owned/input/evidence paths require renewed checks.
A coordinator may record a nonmaterial requirement-document recheck with old/new hashes,
exact commit and rationale, without overwriting the original authorization or decision.
This is an accountable relevance judgment, not automated semantic equivalence or a
permission protocol. It cannot excuse changed test inputs, source code or task scope.

## Supersession and adoption

This supersedes blanket independent-review and reviewer-feedback-disqualification
instructions in decision 0011, the framework, execution/routing guides and historical
PR descriptions. It does not supersede accepted product requirements, H12 exclusions,
source publication authority, hardware ownership, confidentiality, execution settings,
model routing or incidental allowances. Earlier reviews remain facts at their revisions.

The version-1 schema and its completion/freshness rules remain unchanged for compatibility.
Do not bulk rewrite completed records, manufacture reviewers or flip a live v1 record's
version. Use the new template for new tasks. Legacy reviews reserve the whole source tree
because they have no declared input/write footprint; v2 relaxation is not silently applied
to them. For existing unfinished work, explicitly re-register only the remaining work,
preserving requirements, dependencies and applicable constraints; keep the old record and
its evidence, mark superseded unfinished tasks blocked with the new reference, and never
pretend a superseded task completed. Dependent tasks must be explicitly reconciled.
This PR performs no automatic queue migration.

See [operating instructions](../development/feature-workflow.md). Rollback pauses affected
work and restores code/instructions without discarding v2 records. The old reader cannot
read v2: do not claim rollback is merely changing a version number. Preserve data and
use this reader to inspect it until a deliberate conversion or restored deployment.
