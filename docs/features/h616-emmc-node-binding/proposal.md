# H616 eMMC node binding across staging and RAM boot

2026-09-30. Necessary repair of the authorized H12 path; optional features stay
paused. The first proposal and independent needs-research decision are preserved
in commit `5b740dd` and ignored review evidence. This amendment resolves the
identified shared-policy design assumption before production changes.

## Source result and before/after behavior

Fresh authenticated intake measured the same controller/CID/capacity/dev_t with
kernel node `/dev/mmcblk2`. Existing signed-policy validation, live adapter and
compiled writer fix `/dev/mmcblk0`. Pinned Linux 6.18.51 host.c:532-540 assigns
host ordinals from an MMC DT alias or a dynamic allocator; block.c:2560/2617
allocates device minors separately, and block.c:2637 names disks from host index.
The exact retained DTB has no MMC aliases. SD and RAM use separate initramfs
and boot entries. No source or measurement establishes shared next-boot numeric
identity. Merely replacing 0 with 2 would retain an unsupported assumption.

Add an explicit signed `sv08-h616-commissioning-policy-v2` contract. Preserve v1
validation and compiled exact-path/dev_t admission unchanged for historical and
synthetic flows. V2 retains the existing fields, with one additional mandatory
`runtime_admission` string exactly `controller-cid-boot-snapshot-v1`.
Its signed `target_device` and `dev_t` describe the measured staging-host mapping
only; this semantic distinction is explicit and never inferred from unsigned
labels. All other signed controller, CID, card type, sectors, board compatible,
claim source, image bytes/hash and exact six-partition GPT fields are unchanged.
Canonical signing binds every field. Unknown version/mode or extra field refuses.

Live inspect/stage/arm/activate use the v2 staging mapping: require one canonical
`/dev/mmcblkN` real user-area node from the unique MMC under exact `4022000.mmc`,
with exact signed path/dev_t, controller/CID/type/capacity, opened descriptor and
p5 parent/PARTUUID/map agreement. Pin and revalidate the same admitted mapping at
every durable boundary; do not reselect changed nodes to continue a transaction.

A compiled physical v2 writer uses the signed RAM admission rule to discover
that same physical eMMC under the exact controller and CID. Resolve only one
canonical kernel user-area node, its actual sysfs dev_t and its p5 child once,
before marker access or any target transfer. Pin that boot-local path/dev_t and
partition snapshot; recheck exact snapshot plus signed stable identity at every
marker, target descriptor, environment and transfer boundary. Do not rediscover
and replace the snapshot on a mismatch. Validate p5 parent, PARTUUID, offset and
size against the signed map before mounting/consuming its marker. A runtime
argument, network job field or unsigned label cannot provide a numeric override.
No alias, node creation/rename, guessed tuple allowlist or kernel/DT change.

This explicitly amends the earlier numeric-policy architecture: staging numbers
remain signed exact expectations; RAM numbers become exact validated per-boot
snapshot values. It does not waive physical identity or descriptor checks or
claim current SD numbers are RAM facts. Independent approval must decide whether
this stays within delegated implementation authority. If any accepted owner
requirement or authority would change, return that concrete issue before edits.

## Preservation and scope

V2 is physical commissioning only; reject synthetic fixtures requesting v2 and
all incompatible flags. Legacy v1 defaults remain intact. Preserve signed job
purpose, canonical policy digest, compiled-purpose record, reviewed build/FIT
hashes and actual embedded member binding. Both preflight and full writer may
support v2; no physical full-write job or execution before measured urh-04 and
separate urh-05 review/authority. The preflight still compiles out target O_RDWR,
image/environment transfer and retains marker durability/return protections.
Keep one-shot claims, RTC/expiry, source overlap, trusted initramfs entry, exact
source/GPT/environment rules, original recovery and SD rescue. No automatic
retry, rearm or remapping. Source/job/receipt signing formats stay unchanged:
the signed job's existing policy digest binds the whole v2 policy. Do not weaken
staging, marker-last publication or journal admission to accommodate v2.

One implementer owns exactly:
`scripts/build_h616_reimage_candidate.py`, `scripts/live_h616_recovery_stage.py`,
`tests/fixtures/sd-network-root/emmc_image_writer.c`,
`tests/test_h616_reimage_candidate.py`, `tests/test_h616_live_stage_cli.py`,
`tests/test_h616_recovery_handoff.py`, `tests/test_recovery_handoff_stage.py`,
`tests/test_prepare_h616_reimage_job.py`,
and new `docs/hardware/host-h616-emmc-node-binding.md`.
Shared existing parsers/locator helpers may be reused unchanged. Return any
additional file/schema/boot-contract need before editing. No dependency download,
upstream change, kernel/DT/loader, normal updater, hardware service, real keys/jobs,
media, MCU, heater or motion operation belongs to this offline repair.

## Acceptance

- **enb-01**: v1 compatibility; strict v2 fields/canonicalization and physical-only
  mode; positive exact mmcblk0/mmcblk2 staging. Reject unknown modes/versions,
  malformed/leading-zero/alias/boot/RPMB paths, duplicate user areas, incorrect
  signed numbers, controller/CID/type/capacity, p5 parent/PARTUUID/GPT and changed
  descriptors/snapshots before any mutation. Persist phase semantics in evidence.
- **enb-02**: Actual compiled C admission/preflight/write-entry harnesses prove
  one v2 boot snapshot resolves valid eMMC independently of signed SD numbering;
  positive SD mmcblk2 / RAM mmcblk0 and SD mmcblk0 / RAM mmcblk2 fixtures,
  including different boot dev_t, retain the same signed physical identity.
  Wrong stable identity or changed within-boot path/dev_t/p5/controller/CID refuses
  without target writes or marker consumption before admission. Verify p5 mapping
  and both exhausted environment records, close/error paths, marker durability,
  descriptor revalidation and compile-time no-write preflight. V1 stays exact.
- **enb-03**: Relevant signed policy/preparation, purpose/build/FIT/actual embedded
  members, stage/journal/arm/activation regressions pass with v1 and v2 positive
  and negative cases. Reuse unchanged bulk/QEMU evidence at its original scope.
  Source/provenance report states unmeasured RAM enumeration/entry and physical
  urh-04/05 pending; high independent delivery verification precedes physical use.

Scratch under512MiB, retained output under64MiB; no full image copies, repeated
bulk/QEMU runs or downloads. Fixture policy support is only in isolated actual-C
harnesses, never an accepted physical builder mode. Exact physical candidate,
target/recovery and operations still require fresh evidence and immediate
high_consequence_reviewer/high review under existing owner authorization.
Retire this helper when supported recovery target admission replaces it.
