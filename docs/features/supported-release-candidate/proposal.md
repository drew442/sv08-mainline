# Supported candidate and clean-owner path

Extend existing builders/runtime, preserving diagnostic contracts, real OS health, A/B state, immutable/writable modes, identity, firmware policy, production validator and hardware protections. Current source: 22e3bd7. No parallel distribution or invented readiness markers.

## Source acceptance

- C1: supported composition has an explicit typed profile, complete backend/board/recovery inputs and rejects missing, private-pilot or fixture state. Diagnostic entry points retain their existing contracts.
- C2: blank installation contains no inherited normal password/identity. Existing verified recovery target admission provides reviewed owner enrollment/reset with cancellation and stale-target refusal; passwords stay outside public plans/logs. Fixed sv08 account authenticates durably across slots/modes without sharing other slot accounts.
- C3: publication alone cannot start physical services. Explicit commissioning/start admission preserves trial/health/shutdown/configuration/firmware distinctions; missing/stale evidence refuses. Never automatically flash MCU firmware.
- C4: composed source fixtures exercise intended setup/mount/activation contracts, including failures, and relevant regressions pass. Rendered recovery enrollment is inspected; installed/native and physical evidence remain separately identified.
- C5: source-bound commands/results, cumulative allowances and limitations are preserved; current handoff names next build/physical checks. The source task does not claim release completion.

## Settled boundaries

Owner password enrollment/reset uses the independent local recovery interface and verified finite current/fresh/restored state roots, with explicit review/CAS. Normal Cockpit Accounts cannot persist password changes against the read-only derived shadow; document recovery as the supported password-management route. Password bounds: 12–256 printable ASCII characters including spaces, no line breaks (existing OpenSSL stdin semantics). No default normal password.

Per-device boot-environment binding remains fail-closed. Public artifacts must not require private project credentials. Exact measured board/medium inputs are distinct from guessed defaults. Supported service activation is not a printing acceptance certificate.

## Execution

Self-validation for reversible source/disposable fixtures. Primary source allowance: 7,200 cumulative process-seconds and 1 GiB generated data, no full images locally. Initial two read-only traces used no experiments; routine reads/metadata only. Owner implementation may consume 3,000 seconds/384 MiB within this allowance. Builds/native KVM get a recorded separate bounded allocation after prerequisite/source checks. Local disk has 9.6 GiB free; native host has 196 GiB free but only 15,136 free inodes. Use private inode-rich filesystem for image work.

Authority: [owner request](owner-request.md), [canonical release contract](../../remaining-work-plan.md). Full release phases and attended dependencies remain in existing project/H records.
