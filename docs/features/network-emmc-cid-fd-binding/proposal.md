# network-emmc-cid-fd-binding: Bind admitted eMMC CID to the opened descriptor

Kind: improvement. Author: root/coordinator. Date: 2026-09-26.

## Problem and evidence

The test-only CID helper admits one candidate from controller, MMC type,
capacity and a locally supplied expected CID, but returns a path before open.
The separate descriptor-binding improvement keeps a synthetic QEMU `/dev/sda`
descriptor through write and readback, matching its `st_rdev` to synthetic
sysfs `dev`. The two protections have not yet been tested together, and the
QEMU target is not a real H616 eMMC. See the [CID report](../../hardware/host-network-emmc-cid-admission-validation-20260926.md),
[descriptor-binding report](../../hardware/host-network-emmc-fd-binding-qemu-20260926.md),
and [readiness audit](../../hardware/host-network-emmc-reimage-readiness-20260926.md).

## Intended outcome

Extend only the disposable QEMU writer and its synthetic fixtures so one
candidate is admitted using a test-local expected CID plus the existing H616
controller/type/capacity rules, then bind that candidate's sysfs block major and
minor to the opened descriptor before the first write. Re-read the synthetic
CID/device-number association immediately before writing. Keep the exact same
descriptor open through write, flush and complete readback. The network job
descriptor must not supply or override the expected CID. Any missing,
malformed, changed, mismatched or ambiguous identity must write zero bytes; a
previously consumed one-shot claim remains consumed and is never retried.

## Scope and alternatives

Included: test-only identity binding, synthetic MMC/sysfs and block-descriptor
fixtures, fail-closed refusal checks, and one bounded QEMU full-transfer run
with exact synthetic source/target, full readback and GPT validation. Use only
obviously synthetic CID values. The small alternative is to keep the CID and
descriptor checks separate; that leaves the relationship between the admitted
MMC and the descriptor being written unproven by the offline tests.

Excluded: production image-builder or SD/NFS-root changes, a live writer or
trigger, private CID access/provisioning, real eMMC opens, physical access,
boot-policy changes, hardware writes and release qualification. Do not claim
that synthetic sysfs proves the H616 kernel's live mapping or printer write
safety. H12 remains the sole physical commissioning task and still requires a
live CID comparison, exact candidate/target/recovery review, independent
high-consequence review and explicit action authorization.

## Acceptance and task split

| Check | Task | Acceptance |
| --- | --- | --- |
| `ncfb-01` | `qemu-cid-fd-binding` | Synthetic admission requires one exact CID/controller/type/capacity candidate and captures that candidate's block major/minor; malformed, missing, changed, mismatched or ambiguous state refuses. Expected CID is outside the job descriptor. |
| `ncfb-02` | `qemu-cid-fd-binding` | After open, `fstat` of the target descriptor matches the admitted candidate's major/minor, and a pre-write recheck still associates that dev_t with the expected CID. Every rejection writes zero bytes. The same descriptor remains open through flush and full readback. |
| `ncfb-03` | `qemu-cid-fd-binding` | Disposable regular-file-backed QEMU full transfer preserves durable claim-before-open, exact source hash, full readback, GPT/partition checks, no-replay and no-success-on-failure behavior. Include identity-refusal and one interrupted-write receipt. |
| `ncfb-04` | `qemu-cid-fd-binding` | Focused native and strict static ARM64 tests, relevant one-shot/CID/descriptor/SD-NFS regressions, workflow and documentation/hash checks pass. Production builder and diagnostic remain unchanged; report states QEMU-only limits and H12 remains open. |

## Human dependencies

None for this offline task. Reuse the existing H12 item in
[`coordinated-human-tasks.md`](../../hardware/coordinated-human-tasks.md) for
the one later physical commissioning session. Do not read or commit the private
CID, boot the printer, move eMMC, use the USB writer, or write hardware under
this proposal. Feature approval would authorize only synthetic QEMU work.
