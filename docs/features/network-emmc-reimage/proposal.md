# network-emmc-reimage: Reimage an installed eMMC from the network boot path

Kind: feature. Author: root/coordinator. Date: 2026-09-26.

## Problem and evidence

The owner wants to reimage the installed SV08 eMMC without removing it or using
the USB writer. The independently verified signed-feed QEMU journey proves
routine A/B OS updates only; it explicitly excludes a complete eMMC image write
([A/B evidence](../../hardware/host-unattended-update-qemu-evidence-20260926.json),
[A/B scope](../../hardware/host-unattended-updates.md)). The existing SD/NFS
prototype boots a read-only network root and its eMMC probe is read-only
([SD/NFS prototype](../../hardware/host-sd-network-root-prototype.md),
[H10 measured result](../../hardware/host-sd-network-emmc-probe-20260926.md)).
The SD image builder accepts regular files only, and the probe does not write
the eMMC ([builder](../../../scripts/build_sd_network_image.py),
[probe source](../../../tests/fixtures/sd-network-root/init.c)).

Measured hardware facts are limited to the named `test-sv08-01` profile's
2026-09-26 supervised SD/NFS boot and read-only access to `/dev/mmcblk0` with
both U-Boot environment copies CRC-valid. These facts do not establish safe
physical writes, the selected redundant environment, or a deployable image.

## Intended outcome

Before: a network-root boot can inspect the installed eMMC but has no exercised
whole-image write/verify workflow. After this bounded pilot: disposable ARM64
QEMU boots the same network-root path, writes a pinned complete disk image to a
separate virtual eMMC target, flushes it, reads the full image back, and checks
the raw hash, GPT and partition map. This advances the owner's no-writer goal
without claiming the physical printer has been written.

The A/B updater remains the preferred routine OS update path. This separate
reimage path is for a complete replacement/recovery image when the owner has
authorized that operation; the two workflows must not share ambiguous target
selection or imply each other's evidence.

## Scope and alternatives

Include a narrowly gated image-write component and QEMU integration for a
read-only SD/NFS source plus a disposable eMMC-like destination. Pin the
candidate image digest and exact layout. Require the live root/source to be
outside the target, unique target identity and sufficient capacity, full image
length/hash, write completion and flush, full direct readback hash, and GPT plus
partition identity checks. Add refusal/failure tests for ambiguous, wrong,
undersized, overlapping, unavailable, truncated or mismatched inputs. Bound
timeouts and preserve evidence when the outcome is uncertain.

The offline implementation must not open or mutate any real block device and
must not alter the live printer, SD card, NFS export, U-Boot policy, or MCU.
Keep the test bundle and image synthetic/private; do not commit private image
content, credentials, keys or device captures. Do not add an automatically
enabled physical writer to the diagnostic SD image in this pilot. Any real
device adapter and unattended trigger require a later independent
high-consequence review and exact write authorization.

Alternatives are to use the USB writer for whole-image provisioning, or use the
existing signed A/B path for routine host updates. Those are safer/proven in
their respective scopes but do not demonstrate an installed-eMMC whole-image
write from the network-root environment. The custom writer is a project gap;
retire it if a supported upstream/recovery mechanism provides equally bounded
target identity, full verification and rollback.

## Acceptance and task split

| Check | Task | Acceptance |
| --- | --- | --- |
| `nwr-01` | `qemu-prototype` | The disposable QEMU guest boots from the SD/NFS-root source and writes the exact pinned full-image fixture to a distinct virtual target. Evidence proves the source remains mounted outside that target and no host/physical block device is opened. |
| `nwr-02` | `qemu-prototype` | Full flush and readback produce the same SHA-256 and byte count as the source; GPT and every expected partition boundary/identity match. The guest rejects ambiguous/wrong/undersized target, overlap, missing or changed source image, truncation, I/O error and timeout without reporting success. |
| `nwr-03` | `qemu-prototype` | Tests and documentation state that this is offline QEMU-only evidence. The existing human task list gets one deduplicated future physical commissioning entry with exact prerequisites and stop conditions; no physical action is requested by this proposal. |

## Human dependencies

No new human action is required for the offline pilot. Reuse H09/H10 evidence.
Any future write to the printer must be a separate named hardware task after
image, target, recovery and independent high-consequence reviews. The spare
eMMC remains installed and the factory module remains stored; no eMMC move,
writer connection, printer boot or physical write is part of this proposal.
