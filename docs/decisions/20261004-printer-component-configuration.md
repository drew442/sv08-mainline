# Printer component configuration in Cockpit

Date: 2026-10-04. Status: delivered; independent software and installed checks passed.
See [installed evidence](../features/printer-component-configuration/installed-evidence.md).

## Context

The owner requested board-first selection of printer components, their pins and
limits, sensible defaults and an easy route for contributors to add hardware.
The existing host administration page has no component catalog or configuration
generator. The [approved proposal](../features/printer-component-configuration/proposal.md)
and its six review constraints define this delivery.

## Decision

Use a separate `sv08-printer` Cockpit package and one navigation link from the
existing host page. Reuse Cockpit authentication and administrator-session support.
A finite helper handles structured drafts, review and inactive candidate storage;
there is no new daemon, remote catalog, authentication scheme or permission ledger.

The versioned JSON catalog describes boards, documented signals/connectors,
component choices and source provenance. Adding a board using existing component
types should require data and fixtures rather than new application code. Reference
configuration evidence does not establish a connected board's identity or every
electrical capability. Unknown values stay visible and unsupported assignments
remain unavailable. Preserve the upstream Octopus non-Pro versus Pro v1.1 warning.

Users can save incomplete drafts. Board replacement requires confirmation and
clears affected devices and electrical selections. Review explains software fields
needed to generate a candidate, while physical evidence gaps remain separate.
Selected factory curves are defaults; they are not fitted calibration or proof of
the installed thermistor part. Fine calibration is deferred by the owner.

Generate sensor-only configurations through a positive section allowlist. Full
printer candidates require complete selected geometry, currents, control settings
and component assignments, with upstream heater protections preserved. Both outputs
remain inactive. Saving or applying a candidate never changes live `printer.cfg`,
starts printer services, resets/flashes an MCU, or enables heat or motion. Existing
printer interface configuration retains ownership of its separate control include.

Keep each machine's structured draft and current/previous candidate in private
storage inside the active state generation. Verify actual boot, registry and
configuration-view agreement. Acquire Store exclusion before feature exclusion;
save uses revision comparison, and review/apply binds current content and generation.
A single durable replacement commits the coherent envelope. Preserve corrupt or
newer-schema originals and prior complete state on failure. Bound input, generated
output, allocated storage and inode use without weakening existing shared reserves.

Install through an additive, exact-preimage inventory with a bounded restoration
path. Support the existing installed Store API and current Store/Budget API without
refreshing unrelated host runtime. Offline fixtures and actual authenticated
installed ARM64 behavior are separate acceptance evidence.

## Why custom code is needed

Cockpit supplies the supported package, session and process transport mechanisms;
Klipper supplies configuration parsing and printer protections. Neither provides
this project's source-qualified board/component catalog, generation-aware private
draft workflow or inactive candidate generator. Those are the bounded custom gap.
No upstream files or pinned dependencies change for this feature.

## Validation and retirement

Require sourced catalog fixtures, collision/injection/completeness checks, pinned
Klipper file-output parsing, actual Store generation/failure/concurrency tests,
browser journeys and exact staging checks. Independent software review precedes
the exact installation review and named-host authenticated journey. Hardware
compatibility, physical input polarity, heating and motion remain separate checks.

Retain the catalog schema and contributor recipe as the extension boundary. If an
upstream maintained configuration workflow covers these requirements, evaluate
replacing the helper/generator with that implementation and migrating structured
drafts explicitly. Do not maintain a permanent fork of Cockpit or Klipper for this
page; no upstreaming claim is made before the custom gap and interface stabilize.
