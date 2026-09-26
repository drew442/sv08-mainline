# 0018: Prototype writerless whole-eMMC reimaging

Date: 2026-09-26. Authority: owner-requested goal, bounded offline pilot only.

## Context

The unattended signed A/B updater now passes its joined disposable QEMU journey.
It updates only the inactive OS boot/root pair; it does not replace GPT, U-Boot,
the redundant boot environment, recovery, persistent data, or MCU firmware.
The owner separately requested a capability to reimage the installed eMMC
without removing it or using the USB writer. The printer's disposable SD to
read-only NFS-root path has completed a supervised boot, and H10 read the
installed eMMC's two CRC-valid environment records without writing.

## Decision

Develop an offline, disposable-QEMU prototype of a complete image transfer from
the SD/NFS-root environment to an eMMC-like target, followed by full readback
verification. The running source must be independent of the target, and the
test must prove the exact target identity, capacity, image identity, complete
write and GPT/partition result. The test must reject ambiguous/wrong/undersized
targets, source-target overlap, truncated or hash-mismatched images, and must
not open a physical block device.

This is separate from routine A/B OS updates. It does not authorize any printer
write, modify boot policy, create a deployable image, or establish physical
write safety. A future physical use requires a named candidate and target map,
independent high-consequence review, recovery plan and explicit action
authorization under the hardware workflow. The factory eMMC remains stored.

## Consequences

The first deliverable is an offline prototype and evidence, not a claim that the
printer can currently be reimaged. A successful disposable test can inform a
later physical commissioning task. Existing H09/H10 evidence is reused; do not
repeat those human actions unless the reviewed test finds they are insufficient.
