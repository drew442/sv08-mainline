# network-emmc-fd-binding: Keep the admitted block device bound through readback

Kind: improvement. Author: root/coordinator. Date: 2026-09-26.

## Problem and evidence

The offline QEMU writer at `tests/fixtures/sd-network-root/emmc_image_writer.c`
opens `/dev/sda`, checks a synthetic USB serial and capacity, writes and flushes,
then closes the descriptor and reopens `/dev/sda` read-only for verification.
That leaves its verification bound to a second path resolution rather than the
exact descriptor that received the bytes. The separate synthetic CID admission
helper validates sysfs identity before its callback, but correctly documents
that it does not bind the later opened descriptor. No physical target behavior
is measured by these fixtures.

## Intended outcome

In the QEMU-only writer, compare the already opened block descriptor's
`st_rdev` with the major/minor reported by the same synthetic target's sysfs
block `dev` attribute, while retaining existing serial, capacity and regular
file/source separation checks. Keep that descriptor open for the entire write,
flush and full readback; do not reopen the target path after writing. Refuse
before the first write if the descriptor and sysfs identity disagree. Use
synthetic syscall adapters and the disposable QEMU device to test mismatch and
success cases.

This strengthens the test writer's path-to-descriptor binding pattern for a
future eMMC adapter. It does not add or authorize a physical writer, compare a
real eMMC CID, provision expected identity, deploy production code, or change
boot policy. H12 remains the single later physical commissioning task.

## Scope and alternatives

Included: target `dev_t` parsing/validation in the test-only writer, descriptor
retention through readback and failure paths, focused unit tests, and a bounded
QEMU run with disposable target media. Keep the test writer and all new code out
of the production SD/NFS image. Preserve its one-shot durable claim, source
hash, full write/flush/readback and failure-stop behavior.

Excluded: touching private CID evidence, network-job changes, expected-CID
provisioning, block opens on the printer, physical tests, SD image/boot-chain
changes and hardware writes. The smallest alternative is to retain today's
close-and-reopen behavior; it misses the exact-descriptor property this feature
measures. A production writer is deferred until the identity source, target
binding, artifact, recovery and high-consequence review are all ready.

## Acceptance and task split

| Check | Task | Acceptance |
| --- | --- | --- |
| `nfb-01` | `qemu-fd-binding` | Before the first write, the opened descriptor is a block device whose `st_rdev` matches sysfs `dev`; mismatch, malformed metadata and changed synthetic identity refuse before writes. |
| `nfb-02` | `qemu-fd-binding` | The same opened descriptor is used for write, flush and independent full readback; no target-path reopen occurs. Injected errors produce no success receipt and no automatic retry. |
| `nfb-03` | `qemu-fd-binding` | Existing one-shot QEMU synthetic full write/readback still passes with exact serial, capacity, source hash, GPT checks and receipt; use only disposable regular-file-backed virtual media. |
| `nfb-04` | `qemu-fd-binding` | Native/static ARM64 tests, existing one-shot/CID/SD-NFS tests, workflow and docs/hash checks pass. Report remains QEMU-only, with physical identity and writer integration limitations explicit. |

All checks are offline. No production image changes or human actions are part
of this task.

## Human dependencies

No human work is needed for offline tests. Reuse H12 in
[`coordinated-human-tasks.md`](../../hardware/coordinated-human-tasks.md) for a
future exact target review and live CID comparison. Do not add another physical
task, use the USB writer, move eMMC modules or write hardware. Keep the factory
eMMC stored. Approval covers only this test-only QEMU adapter and grants no
hardware or release authority.
