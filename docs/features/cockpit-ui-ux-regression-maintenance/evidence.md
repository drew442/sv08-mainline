# Cockpit UX regression maintenance evidence

Completed 2026-10-11 by the coordinator; self-validation of reversible test maintenance.
This follows the [UI delivery](../cockpit-ui-ux-implementation/evidence.md).
Machine-readable commands, source hashes and results: [evidence.json](evidence.json).

The preserved navigation test now exercises task routes, contextual history, status
ownership and menu focus. Synthetic update fixtures provide the trusted-signer and
release-revision metadata required by the existing backend. Browser journeys enter
Updates before inspecting history and use the current maintenance controls and
status wording. Production UI/runtime and their safeguards are unchanged.

Four checks passed against these persisted candidate files:

- Navigation VM: task routes, contextual history, status ownership and menu focus.
- Image jobs: stage, arm and cancel succeeded; lost acknowledgement reused the same
  identity; closing/reopening the browser retained the operation. A real systemd
  user worker continued independently; reconnect took 121 ms in this fixture.
- Unknown receipt: uncertainty survived reload, a separately reviewed cancellation
  cleared pending state, source A remained selected, and no new installation ran.
- History: 128 originals preserved, maintenance cancellation and lost-ack recovery,
  pending retention on durability failure, one cancellation, unchanged maintenance
  state and a real tmpfs no-space refusal. Private tmpfs was 1088 MiB, retaining the
  production 768 MiB floor and full-copy reserve; pressure allocated 328,994,816 bytes.

These operation browsers use a Cockpit transport shim, synthetic signature verifier
and disposable disk backend. They do not establish authenticated Cockpit, actual
signature verification, physical updates or printer deployment. Native authenticated
ARM64 acceptance is recorded separately in the main delivery. Earlier diagnosed
fixture failures remain in coordinator scratch evidence; current persisted checks
passed without removing reserve, authority, receipt or backend assertions.

Receipts are retained at
`/home/drew/.sv08-cockpit-ux-coordinator-20261011/persisted-*-command.json`
and `persisted-*-browser/result.json`. Browser profiles are disposable and excluded
from publication. The coordinator inspected the complete stable diff and source-bound
results; no independent delivery verification is claimed.
