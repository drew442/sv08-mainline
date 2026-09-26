# network-emmc-target-admission: Reuse H616 eMMC target admission

Kind: improvement. Author: root/coordinator. Date: 2026-09-26.

## Problem and evidence

The verified `network-emmc-reimage:qemu-prototype` writes only to a synthetic
USB disk identified by `/dev/sda`, QEMU serial and exact virtual capacity. It
does not exercise the printer's eMMC identity. The supervised H10 boot measured
the spare as `/dev/mmcblk0`, 61,079,552 sectors, below the exact H616 eMMC
controller path `/sys/bus/platform/devices/4022000.mmc/mmc_host`. Those facts
are recorded in
[`host-sd-network-emmc-probe-20260926.md`](../../hardware/host-sd-network-emmc-probe-20260926.md).

The disposable read-only probe already implements eMMC discovery in
`tests/fixtures/sd-network-root/init.c::emmc_device_at`. Its host fixture verifies
that controller-local host numbering may vary, an unrelated small SD is ignored,
and multiple nominal 32 GB MMC candidates are refused. This code is tied to the
probe translation unit; it is not yet a small reusable admission component for
future reimage work. No eMMC CID was recorded by H10, so this proposal does not
claim a unique module identity beyond the measured controller/type/capacity and
single-candidate rule.

## Intended outcome

Factor the existing read-only H616 eMMC discovery rule into a reusable helper
used by the current diagnostic and native fixture tests. Extend tests to prove
that only one sufficiently sized `MMC` below the exact controller is admitted
and that missing, wrong-type/controller, undersized and ambiguous candidates
are rejected. Preserve current probe output and read-only behavior.

This supplies a directly testable target-admission building block for later
writer integration. It does not add or authorize an eMMC writer and does not
change the QEMU USB-disk target. The shared helper may be compiled into the
existing production SD image's read-only diagnostic probe; the builder must
include the helper's source in its provenance manifest. No writer code or
write-target operation is added to that image.

## Scope and alternatives

Included: factor the locator with an injectable sysfs root for tests; use the
default exact H616 controller path in the existing read-only probe; add synthetic
sysfs fixtures for valid, absent, wrong-type/controller, undersized, and
ambiguous cases; document which physical fields are measured and which remain
unknown.

Excluded: opening the block device, reading or writing image bytes, changing the
production SD image or boot chain, adding CID pinning without measured evidence,
or physical testing. The smallest alternative is leaving locator code embedded
in the probe. That would preserve current behavior but leave future writer code
without a standalone, tested admission interface. A physical writer is a
separate feature and remains subject to H12, an exact image/map, recovery plan,
independent high-consequence review and explicit hardware authorization.

## Acceptance and task split

- **nta-01** — One 61,079,552-sector `MMC` beneath the exact controller is
  selected regardless of `mmc_host` numbering; only sysfs metadata is read.
- **nta-02** — Absent card, SD/non-MMC, candidate outside the configured
  controller, undersized/oversized candidate and multiple matching MMCs all
  fail closed; tests also cover malformed sector metadata.
- **nta-03** — The existing read-only probe uses the shared helper with no
  output/probe behavior regression; no block node is opened by the helper, its
  source hash is bound into the builder's provenance manifest, and the
  production SD image contains no writer.
- **nta-04** — Existing SD/NFS probe tests, focused native tests, JSON/Markdown
  checks and feature workflow validation pass. Documentation records that the
  helper does not establish unique CID identity or physical write safety.

All checks run offline. No human dependency is introduced; the existing H12
physical commissioning entry remains the sole queued whole-eMMC hardware task.
