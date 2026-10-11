# Cockpit recurrence-prevention enforcement

The [new CI workflow](../../../.github/workflows/cockpit-readiness.yml) triggers on
push/PR changes to runtime, printer catalogue, checker, ownership tests and fixture
budget. It uses the same pinned checkout action as the existing workflow, read-only
repository permissions and a hosted disposable Ubuntu runner, without credentials,
model calls, schedules, devices or deployment. Its root test recipe rejects skips.

The exact final YAML test-step shell was extracted and executed locally: fourteen
tests passed, zero skips, in0.339seconds. YAML parsed, documentation links resolved
and complete stable diff/whitespace checks passed. Hosted execution is not yet
observed; local recipe execution does not establish GitHub runner provisioning.
[Exact receipt and source hashes](evidence.json).

[Deployment guidance](../../development/cockpit-deployment-checks.md) now requires
functional installed status/ownership/hash checks with prior hardware summary,
protected-byte comparison for metadata repairs and authenticated rendered evidence
appropriate to changed interactions. Missing evidence remains explicitly unknown.
The immediately preceding investigation measured physical before/after checks and
fixed both demonstrated ownership boundaries; it is separate from CI execution.

Local receipts retained in `/home/drew/.sv08-cockpit-readiness-20261011/`.
Self-validated deterministic development; no independent delivery review claimed.
