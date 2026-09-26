# network-emmc-h616-writerless-adapter: Prepare an opt-in H616 reimage path

Kind: feature. Author: root/coordinator. Date: 2026-09-26.

## Problem and evidence

The owner’s goal is to reimage the installed eMMC without removing it or using
the USB writer. The default SD/NFS image is intentionally a read-only
diagnostic, and the newly verified `qemu-reimage` bundle refuses H616 before
opening any target. Decision 0018 and the accepted QEMU-mode proposal explicitly
reserve a real target adapter, trigger, provisioning and physical testing for a
separate review. H10 measured one 61,079,552-sector MMC under the H616
`4022000.mmc` controller and read both boot-environment copies, but did not
capture a current CID comparison or demonstrate CID-to-open-descriptor mapping.
The exact evidence and limitations are in the [readiness audit](../../hardware/host-network-emmc-reimage-readiness-20260926.md),
[H10 probe report](../../hardware/host-sd-network-emmc-probe-20260926.md),
[CID/descriptor QEMU report](../../hardware/host-network-emmc-cid-fd-binding-qemu-20260926.md),
and [isolated reimage-mode report](../../hardware/host-network-emmc-reimage-mode-qemu-20260926.md).

## Intended outcome

Before this work, full-image writing is tested only against synthetic QEMU
storage. After it, the project can assemble a separately selected,
non-release H616 commissioning candidate with a real H616 identity adapter and
single-use trigger path, while the existing diagnostic stays read-only. The
candidate must remain inert unless its exact locally provisioned target policy
and signed one-shot job both validate. Offline QEMU and source checks can
exercise the path, but cannot establish physical H616 identity, power-loss
recovery, successful printer boot or safe use. Those remain H12 evidence.

## Scope and alternatives

Implement the smallest opt-in H616 candidate that reuses the verified
single-use writer protocol: exact job/image binding, durable claim before target
open, local expected-CID policy outside the job, controller/type/capacity and
sysfs-dev_t admission joined to one opened descriptor, and full write, flush,
same-descriptor readback and terminal failure behavior. The commissioning
candidate must not be labeled deployable or included by the default diagnostic
builder. Keep private expected CID and signing material in ignored local
provisioning paths; commit only synthetic test identities and keys. Add a
synthetic H616-shaped adapter/QEMU harness that exercises the same target
adapter and writer code, plus fail-closed tests for absent, ambiguous, changed,
or mismatched inventory, source/job errors, claim uncertainty, interruption,
flush and readback failure. The boot trigger must have no automatic retry or
rearm path and must never fall through to another boot after an uncertain write.

Do not change the default diagnostic, normal A/B updater or boot policy. Do not
enable production key provisioning, create a supported release, modify MCU
firmware, touch physical media, or claim that synthetic H616-shaped QEMU
validates a real H616 kernel mapping. Keep H12 as the single deduplicated
supervised commissioning action. Its exact current CID, image, target map,
recovery procedure and one-shot operation need fresh independent review and
explicit action authorization before any physical write. If a code path cannot
be made safe without those facts, keep it unavailable and record the blocker.

The USB writer remains the known recovery fallback; the read-only diagnostic
cannot satisfy the writerless goal. No upstream whole-eMMC recovery mechanism
with this identity and one-shot contract has been identified. Keep custom code
limited to that gap and retire it if a supported upstream mechanism meets the
same requirements.

## Acceptance and task split

| Check | Task | Acceptance |
| --- | --- | --- |
| `h616-01` | `commissioning-adapter` | The default diagnostic remains behaviorally read-only and includes no writer, claim trigger, or write-capable service. Only an explicit commissioning mode can include the adapter. The resulting candidate is marked non-deployable. |
| `h616-02` | `commissioning-adapter` | An H616 adapter requires a single local trusted CID/controller/type/capacity record and binds its sysfs device number to the same opened descriptor retained through write/readback. Job fields cannot override local identity. Missing, malformed, changed, or ambiguous inputs refuse before writes. |
| `h616-03` | `commissioning-adapter` | A signed exact-image job consumes a durable one-shot claim before target open. Synthetic H616-shaped QEMU validates successful complete transfer/readback and independent image/GPT checks; identity, source, claim, interrupted transfer, flush and readback failures have no success and no automatic retry/rearm. |
| `h616-04` | `commissioning-adapter` | Strict ARM64 build and relevant regressions pass. The evidence names source and generated artifact hashes and distinguishes synthetic QEMU from physical H616 mapping, boot, power-loss and release evidence. H12 remains the only physical commissioning task. |

## Human dependencies

No physical interaction is required for offline implementation. Reuse the
existing [H12 task](../../hardware/coordinated-human-tasks.md) exactly once for
later capture of the live CID and supervised commissioning after the exact
candidate, target, recovery path and high-consequence review are ready. Do not
ask the owner to move the spare eMMC or use the USB writer for this feature.
No eMMC/MCU/boot-policy write is authorized by this proposal.
