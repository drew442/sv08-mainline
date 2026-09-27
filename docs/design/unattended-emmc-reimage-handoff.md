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
