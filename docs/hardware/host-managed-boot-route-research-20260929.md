# Managed boot route: exact-loader command and return audit

2026-09-29. This is source/regular-file research, with read-only physical intake
linked separately. Target is test-sv08-01, reported H616_JC_6Z_V1.2. No SD/eMMC
write, boot-policy operation or reboot was performed for this audit.

The earlier proposed unchanged SD script route is unavailable in the full-board
loader: its shell hash command is absent. A FIT fallback does not resolve the
accepted p5 selector's separate CRC verification requirement. The exact remote
generated config was read and hashed, not inferred from a generic sandbox:

- Beelink retained build: `/home/drew/sv08-mainline-v8-source/build/sv08-dram-diagnostic-v7`.
- Effective `.config` SHA-256: `52959a1a8761b00927b04cc460182527c7add51e50019d3b397438f98f7b2fb8`.
- CMD_CRC32, CMD_FAT, CMD_MMC, CMD_IMI, CMD_BOOTM, FIT, FIT_FULL_CHECK and SHA256 enabled.
- CMD_HASH, HASH_VERIFY and CRC32_VERIFY disabled. CMD_CRC32 does not imply crc32 -v.

Primary pinned U-Boot source `ece349ade2973e220f524ce59e59711cc919263f`,
`cmd/Kconfig` defines CRC32_VERIFY separately (lines825–831), CMD_HASH selecting
HASH (2798–2805) and HASH_VERIFY depending on CMD_HASH (2821–2826). Source and
effective-config inspection is distinct from physical command execution.
The compatible sandbox used by the [earlier research](host-unattended-reimage-route-research-20260927.md)
has CRC32_VERIFY; its successful selector result therefore cannot establish
this capability in the old ARM64 binary. Those sandbox results remain valid
at their stated evidence level; physical p5 selection is still pending.

The independently inspected regular loader SHA-256 is
`166b4251ffb3c2db6d3b90536650c399b3e5443b06e5c78a0ad2f8ca9fbf6b40`,
786105 bytes. It exactly equals the retained 40960-byte `spl/sunxi-spl.bin`
followed by the 745145-byte second-stage FIT. The boundary is 0xa000, not an
assumed 32 KiB. SPL SHA-256 is
`c4fe12c6f2d344ac48cf39d1711d30734110ee3a55bb0eda1df2fccf80610a8d`;
FIT SHA-256 is `575609afebef87e2004acdc17f6f5e8fa68918cace075fb841b4285b31db4586`.
Retained BL31 SHA-256 is
`36a39a1859a9c95d3e79239afe798e9fa6f805dcec8685ed2dbbd1ca1133d237`;
board `u-boot.dtb` SHA-256 is
`fdea9963522bc09efe3cbac8ebf33e01f730c3b1d2158ce2bb222b72a83f5ff4`;
default environment SHA-256 is
`7b09c2d72a8cb60402187e4ac8904f79fc5b11d552a04d11ce416504561f08bf`.
These match retained source/receipt values; a new build must independently
prove the FIT's extracted ATF/DT components match before assembly.

Provenance is the [v6 physical loader receipt](host-spl-diagnostics-20260915-v6.json)
and [v5 full-image receipt](host-board-image-20260925-v5.json). The actual SPL
has booted; main-U-Boot command changes are a new, untested artifact. Reusing
its exact prefix avoids assuming a freshly compiled SPL is byte-identical.
Only three command options and required dependencies are proposed; a new
main-loader config diff/artifact receipt and physical boot review remain gates.
The retained configured source occupies 417 MiB; the proposed 512 MiB scratch
bound needs measurement during its isolated copy/build. No retained build or
upstream source should be mutated.

A separate source audit found the writer finalizer calls RB_POWER_OFF for every
result, including PASS (`tests/fixtures/sd-network-root/emmc_image_writer.c`,
function finish and final PASS call). The accepted QEMU return journey starts
a second VM through its coordinator. It proves overwritten image bootability,
not automatic physical restart. The revised proposal includes a success-only
recovery-handoff reboot, preserving stop behavior for every failure and other
writer mode. Full readback, signed claims and environment-last transfer stay
unchanged; Linux/QEMU reset behavior and H616 physical return remain separate.

[H13 physical intake](host-sd-recovery-host-first-boot-20260929.md) provides the
current SD/eMMC/GUI/SSH proof and successful read-only live-stager admission.
The H616 RTC reads 1970-01-02 despite corrected Linux wall clock; setting and
checking it across warm reboot is a separately reviewed prerequisite for fresh
time-limited writer jobs. No RTC update has been performed.
