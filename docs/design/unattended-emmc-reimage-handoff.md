# Installed-eMMC reimage handoff contract

Status: bounded offline design for `network-emmc-unattended-recovery-handoff`.
Date: 2026-09-27. It is not a printer activation procedure or evidence of a
physical boot. The stored factory eMMC and prepared SD path remain independent
recovery options.
The [prospective offline verification amendment](../decisions/0019-offline-reimage-handoff-verification.md)
keeps H616 U-Boot-to-FIT execution in the separate physical handoff gate.

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
A separately journaled boot-policy action then exhausts both slot counters and
sets an explicit job-bound arm token in the redundant environment. **Only after
both copies read back as intended** does it publish and sync the one-shot
marker. A crash during either environment write therefore selects an existing
slot or the original recovery UI, never the writer. The exact write sequence
and crash points must be exercised in disposable storage before physical use.

| State | Durable condition | Restart behavior |
| --- | --- | --- |
| Normal | No marker; A/B policy unchanged | Existing slot or recovery UI |
| Staged | Payload and wrapper durable; marker absent | Existing slot or recovery UI |
| Prepared | Policy partly or fully armed; marker absent | Existing slot or original recovery UI |
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

The production selector renderer is now used by the sandbox dispatch
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
scratch space. A separate full-transfer QEMU run at
`/mnt/sv08-qemu-trusted/urh-qemu-full-v2` on Beelink reached
`SV08_H616_COMMISSIONING_PASS`: the guest's full readback and the host's
independent 7,818,182,656-byte hash matched the synthetic source SHA-256
`7d17249b24f47f8d6fc501d0a5c07128b32ae7a9602f6c35ba6498fe913c70ec`,
and the host checked all six GPT records. The result JSON SHA-256 is
`77b24318c646540f155cdf0643e5c96804d14a0f9604cf7be05499f2c8420246`;
serial SHA-256 is
`337cf2481ae68768c2a95b811c44e2cf68ef9ece7dc5231406fda2548d353d09`.
The source was deliberately nonbootable, the guest had 2 GiB RAM, and Linux
logged five atomic page-allocation warnings. This proves the disposable
transfer/readback path, not normal slot boot or the 1 GiB board memory limit.
The separate 1 GiB Beelink QEMU trial at
`/mnt/sv08-qemu-trusted/urh-qemu-v5-source-v1` used the exact reviewed v5
source SHA-256
`ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`
against a disposable synthetic-identity target. It reached
`SV08_H616_COMMISSIONING_PASS`; guest and host full-image hashes, six GPT
records and the one-shot claim passed. A read-only host check during the bulk
comparison found both old environment copies CRC-valid, armed and exhausted.
After success both copies were CRC-valid with order A, A=3/B=0 and no arm
token. The result JSON SHA-256 is
`2ff8acc909b01cb6f294e2908a23bf050144c2f73c4c68cec8a111504d1de6d2`;
serial SHA-256 is
`0b009286322ee3544352b1b83ba71788295e65c6203e6af7853e981d71998c72`.
Linux logged two atomic page-allocation warnings without stopping the trial.

A subsequent read-only QEMU boot probe used that post-write target and the
pinned test kernel/initramfs. It started a shell from root-A, verified the
v5 `release.json` SHA-256
`aa3724f0aaea3f9a59e4fa4ea15014a2f3f4860b2cae5bf1c70f0ffc4b5af519`,
and observed `/dev/sda2` mounted read-only. Its result JSON SHA-256 is
`948979934f29814d8941609d6a540b51ff02bc177837fcc1a80499462f1f60ea`;
serial SHA-256 is
`2cb53c1356597cd298f0dd13f3bd85a9cad0fd8947a7c7721c6306af5159ccf4`.
The probe initramfs omits the normal persistent `/data` initialization hook
because the entire target is exposed read-only. This tests root-A readability
and shell startup, not the production initramfs, systemd, printer services or
physical H616 boot. The QEMU harness starts the same trusted RAM writer with
an external kernel/initramfs after separate U-Boot sandbox selector testing;
it does not emulate H616 U-Boot handing control directly to the FIT.

A further snapshot QEMU probe at
`/mnt/sv08-qemu-trusted/urh-repo/local/urh-v5-full-os-boot-final` booted the
unchanged reviewed v5 kernel and initramfs from the previously replaced
regular-file target. With the normal `rauc.slot=A` boot identity, it mounted
root-A read-only and `/data` read-write in QEMU's temporary overlay;
`sv08-prepare.service` passed, systemd reached `multi-user.target`, and the
`sv08 login:` prompt appeared. The source image prefix retained the exact v5
SHA-256. The result JSON SHA-256 is
`22be069b833632bcd64a807a3e1acaa5ce4294866e4f4845b8bd7d82ef74bd71`;
serial SHA-256 is
`7f5abbcadfa1129b0429102204e6dc8c87b2167f0a631e990552d07041b1c43e`.
The snapshot uses restricted QEMU user networking and 1 GiB RAM. This is a
normal Debian A-slot boot probe, not physical U-Boot handoff or a printer
service/heat/motion test.

The offline stager currently operates on a caller-supplied recovery directory
and arms **regular-file disks only**. It has no live block-device CLI. It
rechecks the exact signed job and image map at stage time, and requires
independently reviewed SHA-256 pins for its build manifest and the original
recovery script. An expired job or changed artifact is refused before a
journal or recovery file is made. It preserves the original recovery script,
installs the FIT and wrapper, journals a separate two-copy environment update,
then publishes the marker as the final boot trigger. It extracts
the compiled U-Boot script and compares its actual payload with the reviewed
selector. It also extracts all three FIT members and compares them with the
reviewed kernel, initramfs and DTB. Tests refuse a changed compiled script or
FIT kernel even when the surrounding manifest and wrapper are recomputed.
The offline arm now rechecks that the signed target policy matches the staged
journal and that the disposable disk's primary/backup GPT, disk GUID and all
six partition records match the signed image map at the 7.8 GB image
boundary. A changed policy or GPT CRC is refused before either environment
record is written. The regular-file prefix inspection is explicit and
read-only; this is not live eMMC admission.
A separate root-owned offline exercise mounted partition five from a fresh
31,272,730,624-byte sparse regular-file target through a loop device. The
stager checked the loop backing file, exact partition offset/size, ext4 mount,
signed GPT map, job, original script and FIT before arming; the separate arm
verified both environment copies before marker activation. An unmounted directory
and a different backing path were refused. Its result is in ignored
`local/urh-mounted-stage-v2/result.json`, SHA-256
`4381d23cea50c055f00c5391de5967bc904f778254afa6623c7dd1178ef666e2`.
This exercise does not identify a live `/dev/mmcblk0` or prove eMMC durability.
The arm operation now also binds the regular-file target's device/inode to the
earlier loop-mounted recovery admission, refusing a different file even if it
has the same signed GPT map. A fresh mounted-stage run under
`local/urh-mounted-stage-v3` passed after that guard; result JSON SHA-256 is
`b26c472cfec4b642d2b7f3c03522cec089f2d7d080d351985f1a0520c17cefe3`.
That run predates the marker-last correction. The corrected mounted-stage
exercise in ignored `local/urh-mounted-stage-v7` verified the original A-slot
policy after file staging, both armed environment copies before activation,
and all FIT members extracted from the staged filesystem. Its result is
`activation_phase=marker-durable` with
`prearm_normal_slot_policy_retained=true` and
`staged_fit_components_verified=true`; result JSON SHA-256 is
`e857a809fa65043bf4b3bec00b7b930ce1fa89afb807899f239d88749d7b5811`.
The same source revision must pass a
new full QEMU write and refusal before this change is submitted again.
The expanded U-Boot sandbox test in `build/urh-stage-fault-v2` exercised the
compiled A/B dispatcher with an original recovery entry before wrapper
replacement, no marker after wrapper replacement, one changed redundant
environment copy, and both armed copies before marker activation. None
selected the writer; the one-copy fixture reached original recovery. The
result JSON SHA-256 is
`dbb37a2746333a5f40e096318b2cdb7e2b07c4678565bec9e2f79ddb853a9701`.
This is a synthetic stage-state boot test, not execution of H616 `bootm`.
The controller-integrated QEMU harness now stages its disposable v5 recovery
partition with that same checked and journaled stager, then arms the two
regular-file environment copies before booting the exact staged kernel and
initramfs with the staged selector's boot arguments. Its first integrated
refusal at `/mnt/sv08-qemu-trusted/urh-qemu-integrated-refusal-v1` passed:
an intentionally corrupted signed job was rejected before claim or target
open, and the writer marker was removed. Its result JSON SHA-256 is
`73c160ceb9d720193c554f8d448e1cfa4998f33ab98c5637d1c74c38b9e6dc5b`;
serial SHA-256 is
`62c5d3a3d22ed773191423864dcf753fac72bc58d10dd60dca050d7b3e077f29`.
The QEMU `virt` machine still starts that verified kernel/initramfs externally;
it cannot establish the actual H616 U-Boot-to-FIT transition.

An integrated 1 GiB guest run at
`/mnt/sv08-qemu-trusted/urh-qemu-integrated-success-v1` did reach target open,
but repeated atomic page-allocation failures in emulated USB/NFS were followed
by an NFS timeout and no further write progress. The guest was killed as an
uncertain postopen interruption; this is **not** a success result. Serial
SHA-256 is
`9a2f701c199ae0e13eee0a3f1a6f36c9680680045ded35c066f08ba9b84881c0`.
Read-only host inspection afterward found both redundant environment copies
CRC-valid, exhausted and still carrying the same arm token. The recovery
marker was absent on a read-only, no-journal-replay mount. At 1 GiB offset a
nonzero MiB matched the source, while at 6,325,010,432 bytes a source MiB
remained zero on the target; the transfer was incomplete. The tested selector
therefore has no marker with which to relaunch the writer, but a second
QEMU/physical boot of this partial target was not performed. This result
shows the uncertain-write stop and 1 GiB QEMU transport pressure; it cannot
serve as full-transfer or board-memory acceptance evidence.

The shared-controller 2 GiB QEMU trial also encountered an NFS stall during
the bulk write (serial SHA-256
`40915643fcaeb7508b9f9bd62177d30dfb2812fd0133c80d9d6019eeef98cfc59b1`),
so the offline harness was corrected to put emulated USB networking and target
storage on separate xHCI controllers. A fresh 1 GiB split-controller refusal
passed at `/mnt/sv08-qemu-trusted/urh-qemu-split-refusal-v1`; result JSON
SHA-256 is
`8e8b1226836474fdcfb24a9325002a115852a70d3635fe96cd38d8a10e9b440b`.

The full split-controller trial at
`/mnt/sv08-qemu-trusted/urh-qemu-split-1g-success-v1` then staged and armed
the loop-mounted v5 recovery partition, booted the exact staged writer
kernel/initramfs with the staged selector's boot arguments, consumed the
one-shot claim, and wrote the exact reviewed v5 source on a 32 GB sparse
regular-file target. The guest and host full 7,818,182,656-byte SHA-256 both
matched
`ba05a82a44599fbf69b9f1f7c0f5d4b65746b350b3f00d350a898b60f9daff4f`;
the host checked all six GPT records and both CRC-valid final environment
records: A=3, B=0, order A, arm token absent. A read-only observation during
bulk transfer had found both old environment copies still CRC-valid, armed
and exhausted. The result JSON SHA-256 is
`eea94030b619b9b7b58121cd89185483f4ac1beea9d2b17c9e254fb64c0842fa`;
serial SHA-256 is
`34f7373d5ca2bfe9f064f89b483b9914f9f4949fa62797b692cf1eece7389f40`.
The 1 GiB guest logged one atomic page-allocation warning without a failed
transfer.

The same post-write target then passed the production-initramfs QEMU snapshot
probe at `/mnt/sv08-qemu-trusted/urh-repo/local/urh-split-normal-boot-v1`:
`sv08-prepare.service` succeeded, systemd reached `multi-user.target`, the
normal login prompt appeared, and the source target's v5 hash remained
unchanged. Its result JSON SHA-256 is
`9b14aec0da6571fb5db6d3fe891bfe63d1d8190ed9c377f4bde7f367f35d5068`;
serial SHA-256 is
`9019cba287e55a7ebe4e65f2eb08e1203eac4fc0ef57ec826d6584435f223163`.
This supplies a sequential offline writer-to-normal-A result on one target.
QEMU still does not execute the H616 U-Boot-to-FIT handoff or printer services;
those remain hardware acceptance checks.

The related regression run passed 31 tests after this check and addition of
the exact-v5-source synthetic-target policy; its log SHA-256 is
`c7674f377719f4fc8e61f2d1ff6480a63c242199db0672fbe34ff9c6c645e677`.
This does not yet prove installed-host target admission, physical durability,
printer services, or unattended scheduling/activation.
The exact v5 source image on Beelink was mounted read-only with ext4 journal
replay disabled for a staging-capacity check: its original `recovery.scr` is
720 bytes, SHA-256
`57e414bec126a309085f3e2be211c6b8fe0e43f5833a5b5609f3e69457808dee`,
and that recovery filesystem reported 154,374,144 bytes available. This is
an image-file observation; the currently installed recovery partition still
needs separate identity and free-space checks before any physical stage.

The existing [H12 human task](../hardware/coordinated-human-tasks.md) remains
the single physical session. Before its
read-only trial, verify wired LAN is connected to the printer for NFS and the
one-shot claim service: its Ethernet cable was last reported in use by the
KVM. Arm receive-only Beelink serial capture before connecting USB serial,
because that connection powers the host. The factory eMMC stays stored.
