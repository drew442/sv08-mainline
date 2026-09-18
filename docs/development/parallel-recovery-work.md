# Recovery export delivery packet

Status: ready for coordinator dispatch. This packet refines the already approved
[`host-recovery-export-composition`](../features/host-recovery-export-composition/record.json)
task; it does not create another feature, expand its scope, or authorize hardware.
Coordinate it through [parallel work](parallel-work.md), and deduplicate physical
work in [coordinated human tasks](../hardware/coordinated-human-tasks.md).

## Authority and ready state

The record's single `implement` task is pending. Both declared dependencies,
`host-recovery-independent-image:implement` and
`host-image-job-resolution:implement`, are done and independently verified. The
normal review-context command currently reproduces the approved bindings exactly:

```text
proposal_sha256     a808b4a507d5d367018004cc42f242b00cde478794503488e4f68cbe3d2f521f
requirement_sha256  585886fdb5456af033e8abab5458594cdeab3a3840bf52d7b88df12285ae5884
scope_sha256        b062b518fc383819fc6b606bc0485731840970e0989312a17d0bf2ab4f34857c
```

The coordinator should claim that existing task before code changes and retain
one implementation owner. A changed proposal, requirement, scope digest, or
dependency status stops dispatch and returns the record for independent review.
No product decision or owner interaction is otherwise required for the offline
delivery.

## First bounded implementation assignment

Assign one `project_implementer` the **trusted preparation and compressed-chain
admission slice**. Its purpose is to make the normal production adapter accept
only an authenticated preparation produced for the independently booted image,
while leaving export disabled on every incomplete or stale state.

Owned paths for this slice are:

- `runtime/sv08_recovery_media.py`;
- new `runtime/sv08_recovery_prepare.py`;
- new `configs/host-os/sv08-recovery-prepare.service`;
- the minimum `scripts/recovery_image.py` staging changes needed to install the
  preparer, policy, manifest binding and unit; and
- new focused `tests/test_recovery_prepare.py` and
  `tests/recovery_prepare_mounts.py`, plus necessary extensions to
  `tests/test_recovery_media.py` and `tests/recovery_media_mounts.py`.

The implementer must report an ownership conflict before touching another path.
It must not edit the feature record, evidence documents, UI/export code, upstream
sources, generated images, private backups or credentials. The coordinator owns
task-record mutations and integration; a later integration worker owns the full
ARM64 image/GTK exercise and its disposable build directory.

The slice is complete offline when focused tests establish all of the following:

1. The immutable root policy authenticates both the early envelope manifest and
   provider manifest. Per-boot observations cannot become their own trust input.
2. The preparer holds the fixed `MediaLease`, enumerates the complete reviewed
   recovery/source/A/B/additional-protected/destination topology, rejects omitted,
   duplicate, aliased or unsupported identities, and publishes context only after
   all preparation succeeds.
3. Whole source media and its selected partition are block read-only before the
   first source mount. The ext4 source mount uses `ro,noload` or `ro,norecovery`.
   Destination FAT mounting is an explicit target-bound write-capable action;
   there is no scan-driven mount, format or repair path.
4. The provider accepts exactly physical ext4 recovery root → immutable regular
   `/usr.squashfs` → read-only loop at offset zero with an extent bounded by the
   immutable file → read-only SquashFS `/usr`. It binds hashes, sizes, devices,
   inodes, loop backing, mount options, holders, submounts and post-`switch_root`
   paths. Legacy uncompressed admission remains valid, and generic virtual or
   stacked storage remains refused.
5. Failure, contention, cleanup failure, disk-sequence change, replacement and
   stale context never enable export. Tests state that `MediaLease` coordinates
   reviewed writers and cannot prevent arbitrary privileged interference.

Use focused unit and disposable mount-namespace tests first. Do not rebuild the
512 MiB image in this assignment. Submit the slice to the coordinator with exact
changed paths, commands/results and unresolved composition needs; do not mark the
feature task done from component tests.

## Full acceptance execution sequence

1. **Freeze inputs.** Re-run `python3 scripts/feature_workflow.py review-context
   host-recovery-export-composition`; verify the three bindings above, both
   dependencies, the final independent-image ADR/initramfs/services/package and
   module inventory, and the current git diff. Record any change from the verified
   independent-image source as implementation evidence.
2. **Land the bounded slice.** Complete the preparer/provider work above and its
   focused regressions. Preserve ordinary refusal when policy or context is
   absent, damaged or stale.
3. **Extend the disposable system fixture.** Use actual selected-guest SCSI/USB
   sysfs observations, stable cross-attribute identity, `diskseq` and geometry.
   Add A/B plus an additional protected unmounted medium. Never use synthetic
   sysfs or a fixture flag to authorize the normal entry point.
4. **Prove preservation and concurrency.** In separate disposable runs, use a
   QEMU read-only backing control and an initially writable dirty-journal source.
   Instrument the block-RO-before-mount order; compare complete source/recovery
   hashes after successes and failures; exercise the real lease, USB
   removal/replacement, UUID/device reuse, no-space, corruption and cleanup
   failures. Preserve older destination files.
5. **Compose the candidate.** Rebuild the exact ARM64 recovery image with ordinary
   installed service/main, production preparer/provider and initially attached
   removable FAT media. Preserve the 536,870,912-byte recovery filesystem and
   7,818,182,656-byte factory layout. Record package/module/code additions,
   compressed and allocated bytes, blocks/inodes, workspace and peak memory.
6. **Run the installed GTK journey.** From fresh boots, exercise separate
   touch-only, keyboard-only and keyboard-plus-mouse selection, review, cancel and
   apply flows. Export damaged-registry, representative configuration,
   SQLite-WAL and Unicode content without initialization or repair. Verify every
   archive member/hash and single-pass readback, plus useful diagnostics when
   preparation is absent or untrusted.
7. **Integrate and review.** Run affected exporter, provider, GTK, builder,
   filesystem and VM regressions; JSON/Markdown target checks; `git diff --check`;
   staged diff checks when applicable; submodule status; and lock/gitlink
   agreement. The coordinator records evidence and submits the complete stable
   diff to a fresh `feature_verifier`. Only a passed independent decision can
   complete the existing task.

Steps 3–6 belong to one assigned `project_integration` worker after the code slice
is stable. Give it exclusive disposable image/work directories, QMP socket and
ports. No other worker may reuse those resources concurrently.

## Evidence to reuse

- [`configs/host-os/recovery-evidence.json`](../../configs/host-os/recovery-evidence.json),
  SHA-256 `d8f60b8473815392fcaab17dc38dfc0ea0255e276ba946ab9828202c83bc13eb`,
  is the independently verified component baseline. It records candidate image
  SHA-256 `98e4030b0902e877d912d9a627e481cd0e24dddeb81d118050e82e9869001a56`,
  compressed `/usr` SHA-256
  `483fd43ed5c3f9a7b7acf3bc193275ddba1b3765646386167589254b796db960`,
  230,875,136 free bytes, 31,055 free inodes and two successful installed GTK
  boots. The referenced ignored build directories are absent in this checkout,
  so these receipts avoid repeating unchanged discovery but cannot replace the
  required new composition build.
- [`host-recovery-image.md`](../hardware/host-recovery-image.md) and
  [ADR 0014](../decisions/0014-independent-compressed-recovery.md) define the
  verified envelope, early `/usr` chain and known limitations. Their evidence is
  reusable until a touched integration input invalidates it.
- [`host-recovery-media.md`](../hardware/host-recovery-media.md),
  [`host-recovery-readback.md`](../hardware/host-recovery-readback.md) and their
  existing focused tests establish the workstation exporter/provider/GTK and
  single-pass readback behavior. Reuse passing unchanged cases; add tests only
  for the production composition seam and approved failure cases.
- The completed job-resolution evidence remains reusable for its independent
  administration contract. This recovery task must not borrow its A/B/data
  libraries or expand into image-job behavior.

Invalidate reused evidence when its recorded source hash changes, the relevant
package/module pin changes, the boot chain or media topology changes, or a new
failure contradicts the recorded result. Generated artifacts must receive new
hashes; an old receipt is never proof of a newly built image.

## Canonical human and release gates

No human action blocks the approved offline implementation. The following are
consumer definitions for existing queue items H04 and H07 in
[coordinated human tasks](../hardware/coordinated-human-tasks.md), not new tasks
or separate requests.

| Queue ID | Recovery-lane consumer | Added readiness condition |
| --- | --- | --- |
| H04 | Physical recovery-export UI and removable-media acceptance for the host OS candidate and release qualification | Independently verified bootable export composition with exact artifact hashes and printer outputs disabled |
| H07 | Export preservation during recovery failures; later restore/slot-selection acceptance after its separate approval | Export composition verified first; signed restore and slot selection independently approved before their cases run |

Use each H entry's canonical action, prerequisites, evidence and invalidators. Add
the recovery check IDs to its consumer list when the corresponding offline
artifact is ready; do not dispatch a separate recovery-lane interaction.

Physical HDMI/touch, real removable-media durability, power loss and board support
remain unproven after offline completion. They do not weaken or delay the offline
acceptance checks.

## Later proposals and release scope

The present approval ends at local export from initially attached reviewed media.
Prepare separate bounded proposals before implementing signed restore, preserved
slot selection, missing-state first-boot initialization, LAN intake, arbitrary
hotplug/ejection discovery, or recovery network/credential text entry. Restoration
must demonstrate that exported configuration, databases and user artifacts can be
consumed without treating a successful export as restore proof.

Release assembly remains coordinator work after those deliveries: compose the
board loader/kernel/driver set and complete factory-sized artifacts; close the
recovery-intake receipt race; preserve exact source/license inventories; execute
physical recovery and power-interruption gates; and qualify an actual stock
profile. None of those results may be inferred from this offline VM delivery.
