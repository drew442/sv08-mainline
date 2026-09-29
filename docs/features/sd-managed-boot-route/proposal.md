# Remotely managed SD/eMMC boot route

This completes the owner's existing writerless eMMC goal, not an optional new
product feature. H13 now supplies running SD recovery with SSH and installed,
unmounted spare eMMC. Its SD-only U-Boot disables eMMC; the accepted p5 RAM writer
requires a boot handoff. Reuse that writer/stager instead of weakening its root
admission or adding another live writer implementation.

Build bounded tooling to transfer the exact previously booted full-board v5
loader (SHA166b4251ffb3c2db6d3b90536650c399b3e5443b06e5c78a0ad2f8ca9fbf6b40,
786105 bytes) into only the SD loader reservation at byte8192, and a Beelink
serial controller to interrupt its autoboot and choose the existing hash-verified
SD boot script. The loader source is the reviewed v5 regular image; do not build
new DRAM/electrical settings. Preserve SD FAT/root/GPT bytes. The full loader has
known Linux boot evidence; its operation when loaded from SD and actual U-Boot
MMC mapping still require a reviewed physical probe.

Default inspect/dry-run, fresh regular-file preparation and complete receipts.
Physical installation requires an explicit private policy binding SD controller,
CID/dev_t/capacity, expected preimage bytes, readonly root partition/mount and
unmounted boot partition. Whole-device O_EXCL is unavailable while root is
mounted: explicitly restrict the admitted operation to the reserved loader span,
require advisory exclusion/no competing users, immutable root and unchanged
FAT/root/metadata hashes; refuse ambiguity or any writable SD filesystem. No
full-card write, resize, partition/GPT/environment or eMMC write. Stop without
retry on an uncertain write/flush/readback; retain original loader for recovery.

Serial routing owns only identified CH3401a86:7523 after capture is released.
No DTR/RTS/HUPCL or power changes. Execution is explicit, with bounded capture,
recognized U-Boot countdown/prompt gates and fixed command allowlist. Do not
transmit to a Linux shell or interpolate command input. SD route reads MMC info,
loads only mmc0:1 boot.scr, requires its exact SHA before source, and boots the
existing SD kernel/root. Unknown prompt/hash/identity/timeouts stop commands.
Normal eMMC route releases standard autoboot rather than inventing an A/B policy.
Do not run it physically before the exact current environment and expected
attempt decrement have separate high-consequence review. If interruption misses,
a normal A boot may consume an attempt; record that risk and prohibit blind retry.

Owned files: scripts/sd_boot_route.py, scripts/sv08_serial_boot_route.py,
tests/test_sd_boot_route.py, tests/test_sv08_serial_boot_route.py and one
hardware usage/evidence document. No shared builder, release policy or C writer
change. Coordinator owns physical target policy, serial/capture arbitration,
loader transfer, reboot, documentation integration and publication.

Offline checks: exact-source/range/preimage/partition exclusions and source
preservation, synthetic transfer/flush/readback/error cases; serial fragmented
transcripts, prompt/hash/timeouts and forbidden-command refusals; complete source
and artifact receipts, independent verification. Do not claim mocks prove H616
routing. If compatible U-Boot sandbox execution of the fixed fallback command is
available, use it; otherwise state that physical gate remains. Preserve existing
SD root/GTK/SSH test evidence, avoiding another userspace build.

After offline acceptance, review exact SD transfer plus one reboot/probe and
SD return on named hardware. This establishes U-Boot mapping without eMMC writes.
Then continue the existing p5 staged handoff and full write under their separate
reviews. Current hardware stays connected; no SD/eMMC move is requested. Later
stager tool deployment and correct reboot-time clock remain separate preparation.
Retirement: replace this test controller with supported recovery boot selection.
