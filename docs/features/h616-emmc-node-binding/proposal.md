# Bind H616 staging to the currently enumerated eMMC node

2026-09-30. This repairs a concrete blocker in the authorized H12 delivery;
optional features remain paused. Fresh authenticated inventory proves the same
CID/controller/capacity/dev_t now exposes `/dev/mmcblk2`, whereas accepted live
staging, signed-policy validation and the trusted writer require `/dev/mmcblk0`.
No device alias, fabricated policy, kernel change or relaxed identity check may
substitute for the current evidence.

## Bounded outcome

Permit only canonical `/dev/mmcblkN` user-area paths in the signed commissioning
policy. Derive the one user-area node from the unique MMC card beneath the exact
`4022000.mmc` controller, and require exact agreement with policy path, CID,
capacity and dev_t, kernel sysfs node, descriptor identity and recovery p5 parent.
The initial SD staging host and RAM writer may enumerate differently. Determine
from retained pinned DT/kernel source and existing observations whether that can
occur for the selected inputs. If so, report a concrete split-policy problem to
the coordinator before changing the signed schema or weakening exact-path
agreement. Preserve current mmcblk0 compatibility and all signed inputs, trusted
entry, one-shot claim, GPT/source overlap, root/mount and two-copy environment
checks. Recheck identity immediately before every read/write boundary. Paths
must be bounded, reject malformed suffixes, boot/RPMB nodes, symlinks, duplicates,
wrong parents, changed nodes or wrong policies. Do not create or rename nodes.

The live tool's inspection/stage/arm/activation remain separate and default to
inspection. The compile-time preflight excludes target writes. The full writer
keeps its existing write authority and descriptor checks; no runtime fixture flag
or unreviewed path argument may select a target. Raw environment and partition
checks must use the same pinned descriptor and sysfs identity as admission.

## Ownership and acceptance

One implementation owns only:
`scripts/build_h616_reimage_candidate.py`, `scripts/live_h616_recovery_stage.py`,
`tests/fixtures/sd-network-root/emmc_image_writer.c`,
`tests/test_h616_reimage_candidate.py`, `tests/test_h616_live_stage_cli.py`,
`tests/test_h616_recovery_handoff.py`, `tests/test_recovery_handoff_stage.py`,
and a new `docs/hardware/host-h616-emmc-node-binding.md`.
Return any additional needed file/schema/boot-contract change before editing.
Keep source/compiled-artifact provenance and existing build-purpose evidence
intact. No kernel/DT/loader, normal A/B updater, hardware services, real jobs,
keys, media, MCU or printer actions are part of this offline repair.

- **enb-01**: Policy and Python admission accept canonical mmcblk0 and mmcblk2
  only when they are the one current user area under the exact controller;
  prove mismatches, malformed/alias/boot paths, duplicate nodes, descriptor and
  recovery-parent changes refuse before writes. Preserve existing mmcblk0 flow.
- **enb-02**: Compile actual C admission/preflight/write entry harnesses. Prove
  mmcblk2 positive identity admission and wrong-path/CID/dev_t/controller/card/
  capacity/p5-parent refusal, compile-time no-write preflight, target descriptor
  revalidation and both environment record binding. Native fixtures remain
  offline; prior bulk/QEMU evidence retains its original scope.
- **enb-03**: Relevant signed-policy/build/purpose/stage/journal regressions pass,
  supported pinned boot enumeration is traced or explicitly reported unresolved,
  and documentation identifies fresh exact physical artifact reviews still
  required. Independent high delivery verification covers this repair before
  any physical use; physical urh-04/05 remain pending.

Keep scratch under512MiB, retained artifacts under64MiB. No repeated full image
copy/transfer/QEMU run or new dependency. Existing fixtures and pinned upstream
source only. Retire the helper with supported recovery target admission. Scope
approval grants no physical authority; exact-operation hardware reviews use the
owner-requested high_consequence_reviewer profile and high variant when required.
