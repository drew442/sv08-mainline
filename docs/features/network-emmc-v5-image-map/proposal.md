# network-emmc-v5-image-map: Pin the audited v5 image GPT map

Kind: improvement. Author: root/coordinator. Date: 2026-09-27.

## Problem and evidence

The H616 commissioning builder has an empty `REVIEWED_PHYSICAL_IMAGES`
allowlist. It correctly refuses to build a non-synthetic candidate because no
reviewed image hash is bound to an image disk GUID and complete GPT map. The
new [v5 artifact audit](../../hardware/host-board-image-20260925-v5-gpt-audit-20260927.md)
records the exact raw image hash, image disk GUID, six partition GUIDs, offsets
and sizes, and verifies both GPT checks and the historical direct-readback
hash. It distinguishes the image's disk GUID from the prior target's private
pre-write identity. The H616 adapter is independently verified and merged, but
its builder still refuses this exact image.

## Intended outcome

Before: every physical image layout is refused by pure policy validation,
including the exact v5 artifact.

After: the builder recognizes only the v5 raw-image SHA-256 and image disk GUID
recorded by the artifact audit, and uses the existing reviewed board profile
for its six PARTUUIDs and offsets/sizes. Any altered hash or GPT map refuses.
The resulting H616 commissioning directory remains nonbootable and
nondeployable; no SD boot chain, trigger, claim service or physical key is
created by this change.

## Scope and alternatives

Limit work to the H616 builder's exact image allowlist, tests, and public
provenance documentation. Do not use the private target's pre-write GUID as
the image GUID. Do not include the private CID, production keys, backup, or
printer identity. Keep the default read-only diagnostic unchanged.

This does not resolve the HTTP claim acknowledgement trust gap, SD/NFS boot
trust chain, current live CID/dev_t mapping, or power-loss recovery. It grants
no physical build, write, boot-policy, or release authority. The separate H12
commissioning task still requires exact candidate/target review, an independent
high-consequence review and explicit authorization before any hardware write.

The alternative is to leave the allowlist empty until boot and claim trust is
reviewed. That preserves the current refusal but prevents further exact-image
policy and commissioning-directory tests offline.

## Acceptance checks

- **vmap-01** — The exact audited v5 raw SHA-256 resolves to the audited image
  disk GUID and six partition records (names, offsets, sizes and PARTUUIDs).
- **vmap-02** — Wrong image hash and any altered disk GUID, partition GUID,
  offset, size or order are refused by policy/job validation.
- **vmap-03** — Synthetic-image behavior remains unchanged; the default
  diagnostic stays writer/trigger-free and physical candidate outputs remain
  explicitly nonbootable and nondeployable.
- **vmap-04** — Focused builder/writer regressions, JSON and Markdown target
  checks, workflow validation and diff checks pass. Evidence binds exact source
  and manifest hashes and keeps offline results distinct from H12 physical
  commissioning.

No human interaction is needed for this offline task. Reuse H12 once, only
after the remaining boot/claim trust path and live target identity are ready.
