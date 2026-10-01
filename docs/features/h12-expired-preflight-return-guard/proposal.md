# H12: admit one guarded SD return after the failed preflight

Kind: fix. Author: coordinator with separate bounded planner/research evidence.
Date: 2026-10-01. Necessary H12 correction; optional features remain paused.

## Requirement and reproduction

Preserve the accepted writerless H616 physical preflight and independent recovery
requirements. [Standing urh-04 authority](../../decisions/20260930-h12-urh04-standing-authorization.md)
includes bounded preparation/corrections on the identified installed spare.
This proposal changes an offline guard admission rule; genuine independent scope
approval, delivery verification and exact operation review remain separate.

At integration commit `81c6640`, the guard binds the consumed
`sd-recovery-return-20260929-01` exception and requires disabled writer markers.
The failed [first physical preflight](../../hardware/host-h12-urh04-first-boot-20261001.md)
left original recovery booted, with unavailable SSH and unmeasured current raw
environments, RTC and marker. The expired service was independently observed
inactive with PID 0; expiry alone does not establish marker absence, disarm or
correct target time. Honest current facts fail existing admission. No used
attempt, receipt or approval may be reset or reused.

The existing Recovery GUI has Boot A/B controls that change policy, rather than a
generic SD restart. Existing coordinator SSH to the KVM can use the accepted
Keyboard gadget without new API authentication. The retained source CAD mapping
contains ordinary final reboot-force and potential early burst/stuck-key force;
event counts and target response remain unproven.

## Intended outcome and bounded correction

Add a distinct H12-only exception for one guarded return to the existing verified
SD host, then require current device identity, both redundant raw environment
CRC/layout/value checks, Linux/RTC comparison and read-only p5 reconciliation
before replacement jobs, selector staging or another boot. Keep
`fresh_environment_reviewed:false`, unknown counters/RTC and possible retained
preflight arm/marker explicit. Admission requires the genuinely approved new
scope/risk digest, exact-operation review binding and retained independent
stage/readback provenance for the exact compiled **preflight** FIT. Do not equate
an unused claim, server expiry or metadata assertions with measured target state.

The [separate source analysis](source-analysis.md) establishes conditional
missed-interception consequences and retained compiled-purpose bindings.
Retained staged-chain provenance must exclude an armed whole-image writer. Unresolved
purpose/artifact/stage provenance refuses admission. A potential preflight marker
consumption and normal-slot boot-counter/persistence writes must be considered
explicitly, including interrupted persistence under CAD burst or failed release.
Do not weaken preservation requirements or assert a current whole-filesystem hash:
the retained original recovery input hash predates the reviewed p5 additions.
Bind unchanged immutable recovery program/package/kernel/unit provenance separately.

Use a new fixed attempt identity and designated canonical exclusive receipt path;
reject aliases/alternate paths that could bypass consumption. Preserve historical
exception restrictions. The new exception admits only the SD route with the live
readiness hook; it must not grant eMMC or the historical stopped-prompt sd-resume
route. Bind the same attempt/state/source across primary, UART, HID and supervisor
channels. Wrong identity, approval, purpose/provenance, fake freshness or missing
state gates must refuse before HID/UART transmission.

Preserve exclusive UART and durable private capture, live PID/start/descriptor/
source/topology readiness, nonce challenge/ack, parent liveness, fresh gadget
metadata, exactly four fixed HID reports, partial-write stops and independently
surviving bounded receive-only collector restoration. No automatic retry, extra
release after uncertain write, reset/power operation, shell command injection,
media/environment write or selector replacement is added. HID delivery does not
prove received event counts, exactly one reboot or a successful SD return.

## Ownership, resources and alternatives

One implementer owns exactly:

- `scripts/sv08_recovery_boot_guard.py`
- `scripts/sv08_serial_boot_route.py`
- `tests/test_sv08_recovery_boot_guard.py`
- `tests/test_sv08_serial_boot_route.py`
- `docs/hardware/host-recovery-reboot-guard.md`

Coordinator alone owns proposal/record, shared records, commits and physical
operations. Return additional production ownership before editing. Use installed
Python/upstream HID, systemd and U-Boot mechanisms; no new image, loader, API
client, dependency, download, artifact copy or physical experiment is needed.
Assigned source/test scratch is bounded to 32 MiB, with two incidental experiments
and 300 seconds total; focused primary checks have a separately assigned budget.
Retain original source/candidates and all failed evidence. Custom code addresses
the existing cross-process admission gap; retire with supported authenticated
recovery reboot/selection. No-change retains the stopped state; GUI Boot A/B and
arbitrary power/shell controls do not satisfy this return workflow.

## Acceptance

- `hret-01` (offline): inspect actual staged-chain and compiled-purpose provenance,
  document every missed-interception branch and uncertainty; prove existing guard
  refuses honest current state, then only exact independently approved H12 state
  passes. Wrong purpose/hash/provenance, approvals, unknown-state omissions or fake
  freshness refuse. No whole-writer ambiguity may be waived.
- `hret-02` (offline): execute actual guard/serial protocol with disposable physical
  transports. Wrong route/attempt/channel/nonce/source, dead or reused process,
  lost channel, stale descriptor, capture failure and gadget drift refuse; fixed
  HID and partial-write behavior, serial gates, independent collector and original
  historical exceptions remain intact. Consumed designated receipts and alternate
  paths cannot admit another sequence.
- `hret-03` (offline): focused regressions, complete ownership/diff/hash review and
  fresh independent high delivery verification at a clean candidate; document
  exact current physical gates and postreturn reconciliation. No physical pass
  follows from fixture or receipt-schema success.

All three checks belong to one offline task. Hardware acceptance remains under
existing H12/urh-04 tasks, not a new duplicate physical task or permission grant.

## Physical dependency and stop conditions

[H12](../../hardware/coordinated-human-tasks.md) remains canonical. PSU off,
USB-powered host, Ethernet, installed spare, stored factory module and absence
of new irreplaceable spare data are owner-confirmed standing facts. Visual recovery
observation remains pending. Before action, the coordinator obtains immediate
separate high-consequence review with fresh live claim-service/listener quiescence,
UART/capture and KVM identity/control/source checks, current preservation and exact
one-shot policy/receipt bindings. A missed interception, uncertain outcome, source
or target ambiguity, changed setup or unavailable review stops; no retry. Source
inspection never supplies a new measurement of unreadable raw environments/RTC.
Standing authority does not authorize urh-05, commissioning or release.
