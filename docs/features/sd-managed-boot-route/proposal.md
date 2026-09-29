# Remotely managed SD/eMMC boot route

This completes the owner's existing writerless eMMC goal, not an optional new
product feature. H13 supplies running immutable SD recovery with SSH and the
installed, unmounted spare eMMC. The SD-only loader disables eMMC; the accepted
p5 RAM writer needs a supported boot handoff. Reuse that writer and stager,
without weakening their entry admission or adding another live writer.

## Corrected loader capability

Independent review rejected sourcing the unchanged SD boot script using the
exact full-board loader: CMD_HASH is absent. Subsequent exact configuration
inspection also found CRC32_VERIFY absent, although CMD_CRC32 is enabled. Thus
plain CRC32 support does not establish the accepted p5 selector's crc32 -v
command. Generic sandbox results remain valid offline but cannot prove these
commands in the old ARM64 binary. Neither route may skip these integrity checks.

Prepare a narrowly revised main U-Boot from the same pinned source and effective
configuration, enabling only CMD_HASH, HASH_VERIFY and CRC32_VERIFY plus strictly
required Kconfig dependencies. Retain the exact previously booted loader's SPL
prefix byte-for-byte, and its identical BL31, board DT and default environment.
The source loader SHA is
166b4251ffb3c2db6d3b90536650c399b3e5443b06e5c78a0ad2f8ca9fbf6b40
(786105 bytes). Read-only comparison established a 40960-byte SPL prefix
(SHA c4fe12c6f2d344ac48cf39d1711d30734110ee3a55bb0eda1df2fccf80610a8d),
followed by the 745145-byte FIT. Enforce that exact boundary. Do not rebuild electrical settings,
change DRAM initialization, substitute an SPL or silently change the source pin.
The resulting loader is a new artifact with its own provenance/hash and pending
physical boot validation; the old artifact's physical result is not transferred.
Require exact effective-config diff, linked command evidence, extracted BL31/DT
hash equality and unchanged SPL bytes before calling it prepared. Reuse pinned
source/patch inputs and supported build mechanisms; keep the command fragment
separate from historical pinned diagnostic receipts.

The investigated FIT-on-FAT alternative is withdrawn: it would still lack the
old loader's crc32 -v capability needed by the existing p5 selector. No new FIT,
FAT staging or SD payload change is in this scope.

## Bounded transfer and serial routing

Default inspect/dry-run, fresh regular-file preparation and complete receipts.
Write only a separately reviewed new loader's exact length at SD byte8192,
entirely below the first partition at 2 MiB, with an enforced 1 MiB loader cap.
Physical installation requires an explicit private policy binding current SD
controller/CID/dev_t/capacity, exact overwrite-span preimage, readonly root
partition/mount and unmounted boot partition. Whole-device O_EXCL is unavailable
while root is mounted: restrict the admitted operation to the loader span,
require advisory exclusion/no competing users, kernel-readonly immutable root
and unchanged FAT/root/GPT hashes. Report advisory ownership accurately.
No full-card write, resize, partition/GPT/environment, FAT, eMMC or MCU write.
Recheck admission at the write boundary. Stop without retry or automatic rollback
on uncertain write/flush/readback; retain the complete overwrite-span preimage
and original SD image for the independently reviewed USB recovery path.

Serial execution owns only the privately identified Beelink CH340 bridge
(topology/path in addition to 1a86:7523), after capture ownership is released.
No DTR/RTS/HUPCL or power changes. Use bounded capture/timeouts, recognized
U-Boot countdown/prompt gates and a fixed command allowlist. Never transmit to
a Linux shell or interpolate user input into commands. SD route reads MMC info,
loads only mmc0:1 boot.scr, requires its exact loaded count and SHA256 before
source, and uses the existing script's kernel/initrd/DT SHA checks and fixed
root PARTUUID/envelope arguments. Unknown prompt/hash/identity/timeouts stop
commands. The physical U-Boot MMC mapping remains unproven until its reviewed
probe; Linux numbering is not a substitute.

Normal eMMC route releases standard autoboot rather than inventing A/B policy.
Before any reboot, review the exact fresh redundant environment and expected
A attempt decrement if interception misses. Record that risk; prohibit blind
retry. Keep signed-job/claim and writer target admission intact.

Owned files: scripts/sd_boot_route.py, scripts/sv08_serial_boot_route.py,
tests/test_sd_boot_route.py, tests/test_sv08_serial_boot_route.py,
configs/host-os/sv08-managed-boot.fragment and one hardware usage/evidence
document. Also own the bounded finalizer change in
tests/fixtures/sd-network-root/emmc_image_writer.c and its focused regression
checks in tests/test_h616_reimage_candidate.py. One implementer. No shared image builder, writer admission/transfer,
release policy,
userspace or upstream source changes. Coordinator owns actual regular artifact
build execution, private target policy, capture arbitration, SD transfer,
reboot/probe, documentation integration and publication.

## Acceptance and resources

Offline checks: source/config/prefix/BL31/DT/environment preservation and actual
linked command capability; range/preimage/partition exclusions, source aliases,
mount/identity changes and synthetic transfer/partial-write/flush/readback
failures; fragmented serial transcripts, prompt/hash/timeouts and forbidden
command refusals. Use compatible U-Boot sandbox for hash verification and
crc32 -v good/corrupt command semantics. A sandbox or mock cannot prove H616
booting. Require complete source/artifact receipts and independent delivery
verification. Preserve existing SD GTK/SSH/root proof, no userspace rebuild.

Stream preservation hashes in 1 MiB chunks; no full-card/image duplicate.
Existing hosts have about 2 GiB free. Bound new main-loader build scratch to
512 MiB and report actual use; loader/preimage/receipts/capture stay under
64 MiB total. Reuse existing source and tools without modifying retained builds
or another worker's files. Inspect space before building, stop if that bound
cannot be met, and retain accepted evidence.

After offline acceptance, separately review exact SD transfer plus one reboot
and SD return on test-sv08-01/H616_JC_6Z_V1.2. Verify actual mapping and new
commands without eMMC writes. Then continue accepted p5 staging/handoff/full
write under their own immediate reviews. Current hardware stays connected;
no SD/eMMC move is requested. Reboot-time clock remains a separately reviewed
physical preparation check. Retirement: replace this test
controller with supported recovery boot selection.

## Automatic return after verified success

The existing writer calls RB_POWER_OFF for every result, including PASS; the
accepted QEMU normal-return journey manually starts its second VM. Complete the
authorized unattended goal by using RB_AUTOBOOT only after the recovery-handoff
writer has completed all existing full readback/hash checks and reports exact
PASS. Preserve poweroff/stop for every refusal, failed/uncertain/post-open result
and for writer modes outside recovery handoff. No automatic retry, error reboot,
claim reuse or new target open. If reboot fails, stop and retain the result.
Keep environment-last transfer and signed admission unchanged.

Offline acceptance adds smbr-04: execute the actual finalizer with captured
syscalls to prove success-only selection and unchanged failure poweroff, compile
the ARM64 artifact, and use a small disposable ARM64 initramfs/QMP run to observe
actual guest-reset versus guest-shutdown events. Reuse unchanged bulk-write and
second-boot evidence; do not repeat an 8 GB write for a syscall-only correction.
This checks Linux reboot behavior on QEMU, not H616 reset/boot routing. The
physical full-write review must bind the newly hashed writer and normal
environment/loader return route; H12 physical success return remains mandatory.
