# Installed-eMMC reimage handoff contract

Status: bounded offline design for `network-emmc-unattended-recovery-handoff`.
Date: 2026-09-27. It is not a printer activation procedure or evidence of a
physical boot. The stored factory eMMC and prepared SD path remain independent
recovery options.

## Boot and staging states

The existing A/B dispatcher remains the only normal boot entry. The recovery
partition retains its original `recovery.scr` as
`sv08-reimage/recovery-original.scr`. A temporary `recovery.scr` wrapper loads
that original script on every unarmed or invalid case. Its writer branch
requires a bounded marker, an exact FIT byte count and CRC32, and successful
FIT component-hash validation. U-Boot's `filesize` is hexadecimal; its CRC
check must use `crc32 -v`, since the tested `crc32 address count variable`
form did not set the environment variable. CRC and FIT hashes detect
accidental changes; signed-job verification remains in the RAM writer.
The disposable U-Boot probe also showed that splitting an `if ... && test`
condition across lines can admit a wrong arm token; keep the complete
boot-policy predicate on one line in the U-Boot script. The corrected ten-case
sandbox result is `build/urh-selector-v7/result.json`, SHA-256
`1f21a15f92aeb316fb70b06263d46353ab252f3956ed0e8894fed3d6bf3e0932`.

The running host must first verify the current eMMC controller/card identity,
capacity, six-partition GPT and recovery PARTUUID, the signed one-shot job,
source image/map, final FIT and free recovery space. It then stages all
content on partition 5 and syncs it, preserving the original recovery script.
The marker is placed only after the payload and wrapper are durable. Finally,
a separately journaled boot-policy action exhausts both slot counters and
sets an explicit job-bound arm token in the redundant environment. If either
environment copy cannot be read back as intended, the host does not reboot
into the writer. The exact write sequence and crash points must be exercised
in disposable storage before physical use.

| State | Durable condition | Restart behavior |
| --- | --- | --- |
| Normal | No marker; A/B policy unchanged | Existing slot or recovery UI |
| Staged | Payload and wrapper durable; marker absent | Existing slot or recovery UI |
| Prepared | Marker durable; no verified armed policy | Existing slot, or recovery UI if policy damaged |
| Armed | Exact marker/FIT, job-bound arm token and exhausted slots | RAM writer or recovery UI on any mismatch |
| Consumed | Marker durably removed; recovery unmounted; both environment copies exhausted | Recovery UI on an early failure; no automatic writer retry |
| Writing | One-shot claim consumed; whole-device target opened | Stop on uncertainty; manual independent SD/USB recovery after power loss |
| Complete | Full image/readback and final boot environment verified | New image's normal A slot |

The RAM writer must identify the target and mount only its partition 5 long
enough to validate and durably remove the marker (`unlink`, directory `fsync`,
filesystem `syncfs`, clean unmount). This happens before time, bundle or claim
checks so an early refusal cannot leave a marker that relaunches the writer.
It must verify both raw redundant environment copies have exhausted A/B
attempts and carry the same job-bound arm token before the first whole-device
write. It then obtains the one-shot Beelink claim, verifies the entire NFS
image and rechecks the target identity at the write boundary. A refusal
before target open may reboot into the original recovery UI; an uncertain
result after target open must stop and must not auto-rearm.

## Boot environment must be written last

The v5 source image contains a boot environment with A-slot attempts enabled
at raw offsets 4 MiB and 8 MiB. A simple sequential whole-image copy would
write these bytes early, before the OS and recovery partitions are complete.
A power loss could then make U-Boot try a partly written A slot. The physical
writer must keep **both existing exhausted environment records** in place
while writing and reading back every other image extent. Only after all other
extents are flushed and verified may it write the source image's two
environment records, flush/read them back, and finally verify the full image
hash and GPT. A partial transfer must never install a bootable new policy.

The guarded prototype in `env_last_transfer.h` writes and compares all bulk
chunks except those exact ranges. The C writer checks the old redundant
records, flushes and reads back the bulk, verifies the old records have not
changed, then writes and reads back each source record and finally hashes
the complete target. `tests/env_last_transfer.c` exercises the actual chunk
helpers on disposable regular files; it does not exercise the guest's block
device, marker mount or claim path. Fault tests must
interrupt before and after each final environment record, as well as during
the bulk transfer. It must show the last fully valid old record never enables
an incomplete image, and that a complete image ends with the source's normal
boot policy. If those properties cannot be established, physical H12 remains
blocked; the existing SD writer's sequential algorithm alone is insufficient
for this unattended installed-media route.

The `urh-01` sandbox result proves only selection and fallback to a marker
representing the original UI. `urh-02/03` must demonstrate staging, marker
consumption, ordered transfer and actual QEMU boot/readback/normal return.
Only `urh-04/05` can validate board-specific boot and a physical write.

## Current offline evidence and remaining gap

The production selector renderer is now used by the ten-case sandbox dispatch
test, so the arm-token predicate, marker, FIT CRC/component hashes and fallback
are not separate handwritten scripts. A 48,900,464-byte FIT made with the
reviewed 33 MiB kernel and 15 MiB base initramfs had SHA-256
`9c7440c672c980b13da2b32299e0eb503fc05bc6b41023ae4d68db543fc89dd4`.
U-Boot sandbox `iminfo` accepted all three SHA-256 FIT components; its log
SHA-256 was `1c23e503b2df6a28ec938e0550e08b6807c8e465b88d2e9c99d1967d42c61179`.
That FIT used an expired synthetic job solely to measure composition and
integrity; it is not a deployable printer artifact.

The disposable Beelink QEMU refusal at
`/mnt/sv08-qemu-trusted/urh-qemu-refusal-v1` used the exact v5 image only as
initial recovery/boot metadata and a synthetic signed-job policy. Its result
SHA-256 `3e74d97b7b1ee8ecd77532bbde91e7a589da97b3b4274c8c6de0e89c92e510a1`
and serial SHA-256 `680acf9ba39910f32089c29d8e46739a4854c43a21ddb1604623141b78ca9e6a`
record `REFUSED_BUNDLE`, no server claim, no target change and marker removal.
The disposable target bytes were removed after the logs were hashed to save
scratch space. The full-transfer QEMU run is separate and must be judged on
its own terminal result and host readback.

The offline stager currently operates on a caller-supplied recovery directory
and arms **regular-file disks only**. It has no live block-device CLI. It
rechecks the exact signed job and image map at stage time, and requires the
reviewed original recovery-script hash. An expired job is refused before a
journal or recovery file is made. It preserves the original recovery script,
installs the FIT and wrapper before
the marker, then journals a separate two-copy environment update. It extracts
the compiled U-Boot script and compares its actual payload with the reviewed
selector. It also extracts all three FIT members and compares them with the
reviewed kernel, initramfs and DTB. Tests refuse a changed compiled script or
FIT kernel even when the surrounding manifest and wrapper are recomputed.
The related regression run passed 24 tests after this check; its log SHA-256
is `d9d319e6d0d7fc8ef5e54657b206b751beb8c5f3427fde0fcd066f95ce832463`.
This does not yet prove installed-host target admission, physical durability,
normal boot of a replacement image, or unattended scheduling/activation.
