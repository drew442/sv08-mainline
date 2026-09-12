# Stock SV08 / H616 6.18 source intake — 2026-09-12

Primary sources accessed **2026-09-12**, pinned to Armbian build
`a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015`. Source inspection only: no adoption,
patch application, build or hardware operation. This continues the
[radio/kernel intake](host-radio-kernel-intake-20260912.md). The
[test printer's](test-sv08-01-online-20260912.md) PCB revision remains unknown;
CB1 electrical equivalence is not established.

## Stock board source and inherited changes

The stock entry is `dt_64/sun50i-h616-sovol-sv08.dts` under
`patch/kernel/archive/sunxi-6.18/`. It is a copied DTS, not a dedicated `.patch`:
`0000.patching_config.yaml` declares the DTS copy and automatic Makefile entries.
The [stock source](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/patch/kernel/archive/sunxi-6.18/dt_64/sun50i-h616-sovol-sv08.dts)
includes `sun50i-h616-bigtreetech-cb1.dtsi` and explicitly says it is not yet
verified on hardware. Max and Zero have separate sources; neither supplies
missing stock-board evidence.

`patches.armbian/arm64-dts-sun50i-h616-bigtreetech-cb1.patch` modifies that included
CB1 file. It supplies the HDMI connector/endpoints, enables `de` and `hdmi`, and
supplies optional peripheral labels referenced by the stock DTS. The stock file
overrides eMMC to eight bits, no 1.8 V switching and 45 MHz, and overrides PI pins
without enabling the disabled optional WS2812/I2C/CAN/TFT nodes. These are source
settings, not electrical measurements. Copying the stock file alone does not
establish a complete compilable device tree; the exact base-kernel include and
header closure remains unresolved.

## Concrete display dependencies

These identifiers refer to exact filenames in the paired
[source manifest](host-sunxi-618-intake-20260912.json), all under `patches.drm/`.
The manifest retains primary URLs, hashes and actual files touched by each patch.

| Patch identifiers | Actual implementation |
| --- | --- |
| 0001–0030 | Shared sun4i mixer/layer/scaler/CSC refactoring, including the structures and APIs consumed by the later planes driver. |
| 0031–0032 | DE33 color-space conversion and video-plane format limits. |
| 0033 | Display-clock driver exports a restricted plane-mapping regmap. |
| 0034–0035 | New DE33 planes binding and `sun50i_planes` driver, with Kconfig/Makefile plumbing. |
| 0036–0037 | Mixer binding changes to `display`/`top` resources plus `allwinner,planes`; mixer code consumes the new planes device. |
| 0038 | H616 TCON TV match and HDMI-pad control quirk. |
| 0039 | H616-specific HDMI PHY tables and match entry in `sun8i_hdmi_phy.c`; the filename begins `0039-srm-`. |
| 0040–0041 | H616 display-engine match and SoC display graph, clocks, SRAM, mixers, planes, HDMI/PHY and TCON nodes. |
| 0042 | HDMI enablement for other boards; it does **not** modify CB1 or SV08. CB1's separate board patch supplies its enablement. |

This crosses DRM, clock code and device-tree bindings; it cannot be reduced to a
board DTS or a PHY compatible substitution. The new planes driver consumes the
clock regmap and refactored layer APIs. Its source leaves all-plane scaling as a
TODO. The graph uses source-authored H6 fallback strings for the HDMI controller
and TCON TOP, but the PHY uses H616-specific tables and compatible. Reusing an H6
initialization function does not justify replacing the PHY compatible with H6.
Do not mix the 6.12 and 6.18 binding shapes by name.

## Other inherited inputs and limits

The CB1 patch also changes PMIC ranges/delays, USB behavior, GPU and radio SDIO
settings. It adds a late GPU supply assignment to `reg_dcdc3`; the separate
`arm64-dts-sun50i-h616-bigtreetech-cb1-emac1-ac300.patch` shows an earlier GPU block
using `reg_dcdc1` in its context. The first patch's earlier GPU hunk shows no
supply assignment. Inspect the final combined tree before drawing conclusions
about its supply selection; neither is verified on this printer.

The AC300 change adds internal-PHY, PWM-clock and SID-calibration assumptions,
with separate stmmac/PHY driver changes. Those are inherited source dependencies,
not identification of the printer's Ethernet hardware. Full PWM/NVMEM and other
transitive platform inputs remain outside this bounded review.

The megous `fixes-6.18/0013` SRAM-link patch and `0014` follow-up change generic
`drivers/of/property.c` supplier handling. The latter's author reports an SV08
thermal-probe test; that is not our hardware evidence or complete-platform
validation. The separate Armbian SRAM **C1** driver patch must not be called a
proven display dependency merely because the display graph references SRAM **C**.

## Provenance and next review

The complete pinned tree was used to verify **53 downloaded files, 308,365 bytes**.
Every SHA-256 and Git blob ID was recomputed; blob IDs match the tree entries.
The paired manifest records all inputs and limitations. Raw files remain under
ignored `local/feature-workflow/board-source-audit/sunxi-6.18-review/`.

`series.conf` declares SRAM entries at lines 129–130, DRM 0001–0042 at 306–347 and
CB1/AC300 at 451–452. This is a declared manifest sequence, not a captured applied
set or proof of a minimal dependency set. The base kernel revision, framework
selection/exclusions, complete ordered patches, configuration and resulting tree
must still be recorded. Existing
[platform-adoption requirements](host-ab-armbian-intake.md#next-review-before-adoption)
remain authoritative, including the ADR and transitive license review. The
[U-Boot/TF-A compilation](host-cb1-boot-compile.md) remains separate. No source
revision is described as tested compatibility, and existing
[physical acceptance tasks](host-os-tasks.md) remain open.

The subsequent [kernel-base recipe intake](host-kernel-base-intake-20260912.md)
traces the pinned framework to a moving `linux-6.18.y` branch and exact config
seed. The selected kernel commit and final configuration remain unresolved;
the framework pin alone does not reproduce them.
