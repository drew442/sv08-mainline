# H616 commissioning eMMC node binding

2026-09-30. Offline implementation candidate for
[the approved node-binding repair](../features/h616-emmc-node-binding/proposal.md).
Independent high delivery review and physical `urh-04`/`urh-05` remain pending.
This record grants no media, boot-policy or printer authority.

## Signed phase contract

Legacy `sv08-h616-commissioning-policy-v1` retains its exact `/dev/mmcblk0`
staging and RAM expectation, field set and compiled-purpose record. Synthetic
builders remain v1 only. V2 requires exactly the v1 fields plus
`runtime_admission: controller-cid-boot-snapshot-v1`, with format
`sv08-h616-commissioning-policy-v2`. Its canonical signed `target_device` and
`dev_t` describe the staging host. Paths are canonical `/dev/mmcblkN`, with
one to seven decimal index digits and no leading zero except `0`. Aliases,
partitions, boot/RPMB nodes, extra fields and unknown modes refuse.

V2 accepts only physical commissioning with trusted initramfs and recovery
handoff; synthetic, fault-injection and claim-only builder modes refuse before
output creation. The signed job formats, detached signatures and receipts are
unchanged: the signed job's policy digest covers all canonical v2 bytes. The
preflight and full-writer purposes stay separate.

The running-host adapter uses that signed exact staging node for inspect, stage,
arm and activate. It checks the opened descriptor, controller/card ancestry,
CID/type/capacity/dev_t, unique user area, exact six-partition GPT, p5 parent,
number, PARTUUID, offset/size and the actual recovery mount. The admission reads
its snapshot before opening the descriptor and compares it again after GPT
inspection. Existing transaction/journal checks compare that admitted result
at durable boundaries; a changed mapping cannot become the transaction's new
mapping. V2 admission evidence explicitly identifies `phase: staging-host`.

The RAM writer resolves the unique user area under the exact controller and
signed CID/type/capacity once. It stores the canonical target, resolved
controller/card/block/p5 paths and both dev_t values in one bounded snapshot.
Later reads compare against that snapshot and cannot replace it. The signed
staging numbers supply no runtime override. This permits differing SD and RAM
numbers without accepting a changed mapping within the boot.

Before mounting recovery or reading its marker, v2 validates both GPT copies,
header/entry CRCs, signed disk identity and all six partition GUIDs/names/ranges,
and current p5 parent/number/PARTUUID/start/size. Whole-device reads bind the
opened read-only descriptor to the snapshot and exact capacity. The p5
read-only descriptor stays open through marker consumption; mounting uses its
`/proc/self/fd/` path, and the mounted directory's device must match the admitted
partition. Before mounting, whole-disk admission remains `O_RDONLY|O_EXCL`. While the
writer's ext4 mount holds p5, the final marker check opens the whole disk
read-only without claiming it: Linux's partition holder conflicts with an
exclusive whole-disk open. This read still checks descriptor dev_t/capacity,
both signed GPT copies and the immutable snapshot, with snapshot and pinned p5
descriptor checks around the GPT read. Subsequent unmounted preflight/full-writer
target admission remains exclusive. Snapshot, p5 descriptor and map checks
precede unlink. Existing
unlink/fsync/syncfs/unmount confirmation and return-readiness rules remain.

Preflight compiles out the writable target and image/environment transfer paths.
It reads both exhausted job-bound environment copies through a read-only
whole-device descriptor and checks the snapshot again before success. The full
writer's first writable descriptor is admitted against the same snapshot/GPT
and both environment copies. It revalidates during bulk transfer and before
each ordered final environment write. Source hashing, overlap/mount rules,
expiry/one-shot claim, original recovery, SD rescue and marker-last staging
remain required. Refusal never triggers automatic rediscovery, rearm or retry.

## Compiled binding and provenance

The builder's `SV08_H616_BOOT_SNAPSHOT_V2` guard selects both the actual C
algorithm and `sv08-h616-compiled-purpose-v2`. That record contains the signed
job/policy hashes, purpose and trusted-entry flags, plus the exact v2 policy
format and runtime admission. V1 emits its original record bytes. The owned
ELF verifier derives expected record bytes from the parsed canonical policy,
not an unsigned manifest admission label. Shared composition/staging continues
to check reviewed executable hashes and actual embedded FIT/initramfs members.
A v1 algorithm compiled with a v2 policy digest still refuses v2 composition.
The ELF record alone does not establish trust in arbitrary newly authored code;
independent source review and the reviewed artifact hash remain necessary.

Implementation base: `a44d6c8b8804fd3c3fc91ffab12d4e0c0c8f1c64`.
The project locator/CID and environment helpers are reused unchanged. The small
GPT/snapshot checks address the commissioning gap within the owned writer;
retire them with the temporary helper when supported recovery target admission
replaces it. No kernel, DT, loader, upstream or signed job schema change is used.
The [approved source trace](../features/h616-emmc-node-binding/record.json)
records Linux 6.18.51 `drivers/mmc/core/host.c:532-540` and
`drivers/mmc/core/block.c:2560/2617/2637`, with their SHA-256 values: host
ordinals and block minors have separate allocation. Source access date is
2026-09-30. This trace establishes no next-boot RAM enumeration or hardware
identity; board revision remains owner-reported in the
[test profile](../../profiles/test-sv08-01/profile.json).

All offline C builds use locally provisioned Monocypher 4.0.3 at
`ab2b16dd619ad5f6979a4fbe69cfa324a6fcc35f`; the checkout and source hashes were
checked. ARM64 compilation used GCC 13.3.0
(`aarch64-linux-gnu-gcc`, Ubuntu 13.3.0-6ubuntu2~24.04.1), static `-Os`,
`-D_FORTIFY_SOURCE=2`, function/data sections and linker garbage collection.
Complete commands, source/output hashes and stack reports are retained in the
coordinator's ignored implementation handoff. Public fixture keys authorize
only disposable tests, never production physical builder inputs.

## Offline checks and resource limits

The original implementation regression passed 58 tests in 49.545 seconds.
After the mounted-p5 repair, fresh final-source regression passed 60 tests in
54.067 seconds with the same command:

```sh
python3 -m unittest tests.test_h616_reimage_candidate \
  tests.test_h616_live_stage_cli tests.test_h616_recovery_handoff \
  tests.test_recovery_handoff_stage tests.test_prepare_h616_reimage_job \
  tests.test_h616_recovery_handoff_builder -v
```

A later focused check passed the live staging and policy tests after adding
snapshot comparison around GPT inspection, including a mutation during that
inspection. Actual native C syscall fixtures cover SD mmcblk2/RAM mmcblk0 and
the reverse with different dev_t, preflight and writable entry, both exhausted
environment copies, wrong identity/GPT/p5, valid within-boot remapping,
controller relocation, descriptor/close errors and marker durability errors.
They exercise the production functions with modeled sysfs and intercepted block,
mount and marker syscalls; no block device or hardware was used. Preparation
checks keep canonical v2 bytes and signature verification while mocking the
large source-image boundary. Actual ELF algorithm/mode mismatches and actual
FIT/member substitution refusals are covered by the small composition fixtures.

The independent earlier review found that the original syscall fixture omitted
Linux's mounted-partition claim conflict. The retained preserved source now
refuses at actual main's marker gate in all four purpose/numbering combinations
when that conflict is modeled. The repaired source reaches the existing expired
job gate after confirmed marker consumption/unmount in all four. The fixture
stops there before a claim or transfer and checks preflight reboot readiness
against full-writer poweroff. Mounted-boundary GPT, CID, target/p5 descriptor and
capacity changes refuse before unlink; durability/cleanup failures retain the
finalizer rules. A failed p5 unmount also keeps later target `O_EXCL` admission
from succeeding. These tests model Linux 6.18.51 holder semantics from
`fs/super.c:1623`, `block/bdev.c:542-552,587-589,640-645,924-932` and
`block/fops.c:661-686` (source access 2026-09-30, retained independent review
hashes); they do not mount a real block partition or establish physical behavior.

Fresh repaired ARM64 fixture builds with identical nonempty job/hash constants
compared with the retained original v1 baseline:

| Mode | Baseline v1 bytes | V2 bytes | Increment | Static BSS increment |
| --- | ---: | ---: | ---: | ---: |
| Preflight | 779064 | 780104 | 1040 | 6416 |
| Full writer | 780328 | 781312 | 984 | 6432 |

The snapshot symbol is 6424 bytes; paths/cardinality are bounded. GCC's ARM64
stack report gives 33904 bytes for GPT comparison and 11152 bytes for snapshot
identity (including inlined metadata checks), with 192 bytes in the descriptor
helper. These are function-frame sizes, not measured peak process RAM; call
chains and libc add usage. Existing FIT/load-memory gates remain intact. These
small executable fixtures do not validate a representative physical FIT's total
loaded memory. No representative image rebuild, bulk hash/transfer or QEMU run
was needed. Sparse regular-file GPT/environment regressions retain their original
offline scope and do not establish physical writes or mounted p5 behavior.

RAM entry/enumeration, physical marker/p5 mount behavior, RTC retention, target
recovery and physical preflight/full-write remain unmeasured. Fresh exact
artifact/source/target evidence, independent high delivery verification and
separate immediate operation review/owner authority are required before use.
