# network-emmc-reimage-mode: Add an isolated installed-eMMC reimage image

Kind: feature. Author: root/coordinator. Date: 2026-09-26.

## Problem and evidence

The owner's goal is to reimage the installed eMMC over the network without
removing it or using the USB writer. Decision 0018 authorizes offline work toward
that goal but distinguishes a QEMU prototype from physical write authority. The
existing SD/NFS boot is a read-only diagnostic that probes eMMC and powers down
([builder](../../../scripts/build_sd_network_image.py),
[init](../../../tests/fixtures/sd-network-root/init.c)). The one-shot writer,
CID admission and opened-descriptor binding are currently QEMU-only fixtures;
the latest joined evidence is
[CID-to-descriptor binding](../../hardware/host-network-emmc-cid-fd-binding-qemu-20260926.md).
The readiness audit records that no isolated reimage image, production trigger,
or current live-CID comparison exists
([readiness](../../hardware/host-network-emmc-reimage-readiness-20260926.md)).
The H616 spare eMMC was measured at 61,079,552 sectors under the
`4022000.mmc` host during H10, but that does not prove CID-to-open-descriptor
mapping or safe physical writes.

## Intended outcome

Before, the printer can boot the read-only SD/NFS diagnostic, while only
synthetic QEMU code can consume a one-shot whole-image write job. After this
feature, the project can build a separately selected, non-default reimage image
whose writer shares the reviewed admission, claim, descriptor-binding,
full-write, flush, readback and terminal-failure behavior. The existing
diagnostic remains read-only. The new image is exercised only with disposable
QEMU storage and is marked commissioning-only; no physical write or release
claim is part of this task.

## Scope and alternatives

Add a separate reimage-image mode and job/writer implementation, with tests
that exercise the same writer and identity code used by that mode through an
explicit test-only QEMU MMC adapter. Network-delivered job fields must not choose
the trusted expected CID. The job must be authenticated independently of the
read-only image source and bind a unique job ID, exact raw-image hash and length,
the 8 GB disk extent, six-partition map, and a separately trusted local target
policy. Consume and durably sync a single-use authorization before opening the
target. Keep the opened descriptor through complete write, flush and readback;
on uncertainty, stop without retry or success. The selected target must match
the local CID policy, H616 controller/type/capacity rules, and the opened fd's
device number. No writer or trigger is added to the default diagnostic image.

The builder must require an explicit reimage mode and keep target identity
configuration separate from the network job. Production keys and the physical
CID stay in ignored local provisioning paths; only obviously synthetic test
values may be committed. The offline artifact must refuse physical devices
unless running under its dedicated reimage mode, and this proposal does not
place a deployable artifact on the printer. Do not change the U-Boot
environment, MCU firmware, normal A/B updater, existing SD image, or release
qualification.

The custom writer is justified only because the existing diagnostic is
read-only and no upstream mechanism performs this whole-device network reimage
with the required identity and one-shot checks. Keep it small and documented;
retire it if a supported recovery/update mechanism meets the same requirements.
The USB reader remains the manual fallback. H12 is the one later physical
commissioning session and still requires a live CID match, exact artifact/target
review, recovery plan, independent high-consequence review and explicit action
authorization.

## Acceptance and task split

| Check | Task | Acceptance |
| --- | --- | --- |
| `nrm-01` | `qemu-reimage-mode` | A separately selected builder mode produces an isolated reimage image; default diagnostic output remains read-only and contains no writer, claim trigger or write-capable service. Reproducible build records both modes and hashes. |
| `nrm-02` | `qemu-reimage-mode` | The QEMU test adapter exercises the actual reimage writer path. A trusted test-local CID policy is separate from the job; changed, malformed, ambiguous or mismatched CID/dev_t, capacity, source hash/length, signed job, or layout refuses before write. No physical block device can be opened by the QEMU harness. |
| `nrm-03` | `qemu-reimage-mode` | Disposable QEMU completes a full pinned-image write, flush and same-fd readback; host independently checks hash, both GPTs and all six partition entries. Wrong identity and interrupted writes consume the job, produce no success/retry and leave a terminal uncertainty. |
| `nrm-04` | `qemu-reimage-mode` | Focused native tests and strict ARM64 build pass. Documentation and workflow hashes validate. Evidence clearly excludes H616 live mapping, physical eMMC writes, real power-loss behavior, deployment and release qualification; H12 remains the single physical task. |

## Human dependencies

No interaction is needed for this offline implementation and QEMU evidence.
Do not boot the printer, access private CID material, change boot policy, move
eMMC, use the USB writer, or write hardware for this feature. Reuse H12 in
[`coordinated-human-tasks.md`](../../hardware/coordinated-human-tasks.md) if and
when its exact image, live target identity, recovery and high-consequence review
are ready. Keep the existing USB reader and stored factory eMMC as the accepted
manual recovery path.
