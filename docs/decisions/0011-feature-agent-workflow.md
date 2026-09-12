# 0011: Feature delivery with delegated agent approval

Date: 2026-09-11. Status: accepted by the owner; implementation and the bounded
offline pilot completed on 2026-09-12. See the
[pilot report](../development/feature-workflow-pilot.md). Physical recovery
acceptance and unattended scheduling remain outside that completion.

## Decision

The owner approved the [feature framework design](../design/feature-agent-framework.md),
including delegated approval within existing project requirements and an offline
pilot. Use suggestion, proposal review, coordinated implementation and independent
delivery verification. These are invoked responsibilities rather than permanent
background agents.

Use one queue for new capabilities and improvements. Preserve existing project
requirements, decisions, hardware profiles and release checklists as authority.
Previously authorized unfinished work may proceed without renewed product approval.
New bounded work within those requirements may be approved by the review agent.
Owner requirements, material product expansion, new external spending, the project
license and expansion of agent authority remain owner decisions.

Persist task dependencies, decisions and evidence; continue other ready work when
one task needs hardware or human input. Require a separate review of substantive
proposals and delivered behavior. Keep implementation completion, offline evidence
and named-hardware acceptance distinct. Preserve existing commit/push authorization;
do not infer hardware authorization from a feature decision.

Start with one active implementation and at most three ready proposals. Use
isolated worktrees and one integration owner. Additional agents are authorized for
bounded suggestion, approval, verification and independent research; they receive
only the source and evidence needed for their task. Validate deterministic policy
and interruption handling before relying on the dispatcher. Scheduling remains
disabled during the offline pilot.

## Provenance and retirement

The design cites the reviewed ceph-spec-tool revision and official Codex mechanisms.
Use project-scoped role configuration and existing Codex execution. Custom code is
limited to durable records, validation, dependency selection and exclusive task
ownership that role prompts alone do not supply. Retire those helpers when supported
upstream mechanisms provide equivalent behavior, retaining regression coverage.

## Acceptance

Exercise missing/stale approval, incomplete evidence, dependency cycles, concurrent
ownership, interruption and failed verification. Run separate live reviews over
useful, duplicate, unsupported and conflicting proposals. Deliver an offline pilot
from the accepted host/recovery backlog and measure its actual before/after outcome.
Keep required physical tasks open; this decision does not make an image deployable.
