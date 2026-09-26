# network-emmc-one-shot: consume a network reimage job exactly once

Kind: improvement. Author: root/coordinator. Date: 2026-09-26.

## Problem and evidence

The accepted [network eMMC reimage prototype](../network-emmc-reimage/proposal.md)
proves a whole-image transfer only to disposable QEMU media. The production SD/NFS
diagnostic remains read-only and powers off after probing. Its source export is
read-only, so it cannot itself record that a write job was consumed. The current
QEMU writer is not included in the SD image and has no live target identity,
one-shot authorization or retry policy ([readiness audit](../../hardware/host-network-emmc-reimage-readiness-20260926.md)).

## Intended outcome

Add an offline-tested job protocol around the existing QEMU-only writer. A
separately served, immutable descriptor binds one job ID, source digest/length,
target identity and expected layout. Before opening a target, the guest must
claim that job through a separate, narrow claim channel that records a durable,
atomic single-use claim. A duplicate, concurrent, stale, malformed or uncertain
claim refuses before target open. A claimed job is never automatically re-armed;
interrupted writes stop without success, retry or reboot. This improves the
existing offline prototype while leaving every real block device inaccessible.

## Scope and alternatives

Implement the smallest testable claim service/client contract and integrate it
only with the disposable QEMU harness and regular-file virtual target. Keep the
image export read-only and independent of the target; keep the claim channel
separate from the image bytes. Pin the descriptor and candidate hashes. Exercise
atomicity, duplicate/concurrent claims, lost acknowledgments, changed/missing
descriptors, source/target separation, full flush/readback/GPT validation, and
interruption. Bound storage, memory, and runtime. Record no secrets or private
hardware identifiers in the repository.

Do not add the writer to the diagnostic image builder, permit the client to pick
a block path, change boot policy, automate a reboot, or make a physical write.
The physical eMMC adapter, real CID admission, live server deployment, and
production activation remain outside this proposal and require a later exact
review. H616 SD U-Boot currently loads from SD and does not establish a safe
handoff to the newly written eMMC; do not solve that by silently changing boot
policy. A human-controlled follow-up boot remains part of H12. Keep H12 as the
single deduplicated physical task and continue offline work while its review is
pending.

The server-side claim is needed because the NFS image source is read-only and a
client-local marker is volatile. A local file or boot argument alone could replay
after reset. Retire the custom claim protocol if a supported recovery service
provides equivalent durable single-use authorization and target binding.

## Acceptance and task split

| Check | Task | Acceptance |
| --- | --- | --- |
| `nwo-01` | `qemu-one-shot` | The guest claims exactly one descriptor before target open. Atomic concurrent/duplicate requests yield one claimant; lost acknowledgment, stale/changed descriptor and service failure fail closed. A claim is never automatically reset. |
| `nwo-02` | `qemu-one-shot` | QEMU uses disposable regular-file media only. Source is read-only and independent of target. The job binds source digest/length, synthetic target identity/capacity and exact GPT map. Full write, flush, independent full readback and GPT checks must pass; mismatches refuse before open or produce no success receipt. |
| `nwo-03` | `qemu-one-shot` | Inject interruption before and during write, flush and readback. The consumed job remains consumed, the guest does not retry, reboot or claim success, and evidence identifies uncertain target state. |
| `nwo-04` | `qemu-one-shot` | Production SD image remains without a writer or trigger; H12 remains the sole physical task. Documentation distinguishes synthetic QEMU evidence from actual hardware and preserves live CID, exact-operation review and physical authorization gates. |

## Human dependencies

No physical interaction is needed for this bounded offline task. Do not move the
installed spare or factory eMMC, connect the USB writer, boot the printer, or
write hardware. Reuse H12 for any later supervised physical commissioning, after
the live CID is matched to private evidence and the exact writer/artifact receive
independent review. H12 is not authorized by this proposal.
