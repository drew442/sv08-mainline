# Unverified CB1 boot-source compilation

2026-09-10. This is a source compilation/capacity fixture, not a printer bootloader
release. It has not been written to any device. Board revision and MMC environment
index remain unknown; the candidate manifest explicitly has `deployable=false`.

[The pinned inputs](../../configs/host-os/cb1-boot-compile-candidate.json) combine
upstream U-Boot v2026.07 (`ece349ade2973e220f524ce59e59711cc919263f`), the two
previously reviewed Armbian CB1 board patches, and upstream TF-A lts-v2.12.9
(`c2a0e7080d64d69940be4ad0ff6578501f3cbf9e`). TF-A's tag resolved to that commit;
the downloaded commit archive has SHA-256
`507a10e4a20d272124ee808c3d3083134c95113486e3d09b8236a6556e901536`.
This tests a narrow upstream-plus-board-patches combination, not the complete
Armbian platform patch set. No Armbian installer/build framework was run.

[The builder](../../scripts/build_cb1_boot_candidate.py) defaults to inspection,
checks archive/patch hashes, uses fresh build paths, and never assembles or writes
a disk image. Its fixed build timestamp is a reproducibility input, not a claimed
source commit date. It builds TF-A `PLAT=sun50i_h616 DEBUG=1 bl31` with an explicit
build string, then U-Boot's patched `bigtreetech_cb1_defconfig` with that BL31.
Missing-blob allowance is not enabled. The final FIT contains U-Boot, BL31 and the
CB1 DTB, with a matching default configuration. The earlier `.fit.itb` file is an
intermediate; inspect `.fit.fit` or the FIT embedded in the combined binary.

## Results

Fresh builds `build/cb1-boot-compile-v1/` and `v2/` produced identical binaries:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| U-Boot plus SPL/FIT | 771497 | `6b4329500390bf3b4aacd4cc5055305c2c2eecf8795fa98f041b62eb001cedd3` |
| TF-A BL31 | 53361 | `d35c461a0ea73bfb6b4301c4233fd6ff741e3c8eec98e9a5caff39f9b642f289` |

The combined binary has the expected eGON SPL header. Placed at byte 8192, it ends
at byte 779689, within the reserved boundary at 1048576. This is a file-size/header
check, not Boot ROM or DRAM initialization evidence. Cross compiler:
`aarch64-linux-gnu-gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`.
The [public result](host-cb1-boot-compile-20260910.json) retains the configuration,
artifact hashes and explicit limits. Build/FIT logs and artifacts remain local. After comparison, the first build
source trees were removed to reclaim space; its artifacts/logs, the second source
trees and original pinned archives remain.

## Findings that prevent activation

The patch selects `SUNXI_DRAM_H616_DDR3_1333` but does not set `DRAM_CLK`; the
selected U-Boot Kconfig supplies **720 MHz**, confirmed in the compiled `.config`.
This needs a review against the actual DRAM and controller requirements. The
patch's timing-profile name is not evidence of a verified operating clock.
Its AXP313 regulator topology, PC3 pull-down, radio GPIOs and power sequencing also
remain assumptions. The U-Boot eMMC limit is 20 MHz, distinct from the 45 MHz
Linux DTS setting discussed in the earlier source intake; neither is measured
hardware validation.

This configuration still uses a FAT environment and `distro_bootcmd`; RAUC boot
method and redundant raw environment are disabled. The separately tested A/B
sandbox configuration has not been transplanted into it because the physical
MMC environment target and recovery boot path need identification. This artifact
must not replace the printer's known bootloader. Compile success does not resolve
Linux display/radio/USB support or the remaining full-platform patch review.

## License/source provenance

Primary sources, accessed/read 2026-09-10:
[TF-A release](https://github.com/ARM-software/arm-trusted-firmware/releases/tag/lts-v2.12.9),
[TF-A license](https://github.com/ARM-software/arm-trusted-firmware/blob/c2a0e7080d64d69940be4ad0ff6578501f3cbf9e/docs/license.rst),
[U-Boot license policy](https://github.com/u-boot/u-boot/blob/ece349ade2973e220f524ce59e59711cc919263f/Licenses/README),
and the [Armbian board-patch directory](https://github.com/armbian/build/tree/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/patch/u-boot/v2026.07-sunxi64/board_bigtreetech-cb1).
TF-A's main license is BSD-3-Clause with documented third-party exceptions;
U-Boot's file-specific GPL/dual-license rules apply. The new board DTS identifies
GPL-2.0+ OR MIT. These observations do not complete a transitive release license
inventory. Preserve exact source archives/patches and complete that inventory
before distributing a board image. Retire the custom compilation wrapper when
the reviewed board pipeline supplies equivalent input, FIT and capacity checks.
