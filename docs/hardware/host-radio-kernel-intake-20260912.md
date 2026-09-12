# Radio and kernel source continuation — 2026-09-12

Source intake only; no adoption, build, installation or hardware operations.
This continues the [Armbian source audit](host-ab-armbian-intake.md). The
[test printer](test-sv08-01-online-20260912.md) has an unknown PCB revision; the
SDIO comparison below uses its existing bring-up observation, not new measurement.
The [U-Boot/TF-A compilation](host-cb1-boot-compile.md) remains separate.

## Concrete new radio candidate

At Armbian build `a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015`,
`lib/functions/compilation/patch/drivers_network.sh:driver_rtl8189FS` selects
EvilOlaf/rtl8189ES_linux commit `be148d226d22214a173e5b2dfe4287e53685ceda`.
It copies the external driver into its kernel build, adjusts Kconfig, disables
RTW debug and applies `wireless-rtl8189fs-set-monitor-channel-6.12.101.patch`.
This is external source bundled into a kernel build, not upstream Linux support.
The patch addresses a cfg80211 API change; the driver pin alone is insufficient
as the complete Armbian build input. Source URL:
[Armbian driver selection](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/lib/functions/compilation/patch/drivers_network.sh)

The candidate's `os_dep/linux/sdio_intf.c:70-72` has SDIO `024c:f179` under
`CONFIG_RTL8188F`; its Makefile enables that family and SDIO and names the module
`8189fs`. This agrees with the enumerated device ID in the already captured
2026-09-12 bring-up evidence, not a physical chip-marking claim or runtime test.
`include/rtw_version.h` retains `v5.7.9_35795.20191128`, the same token reported by
the loaded vendor module. That token does not identify a source commit or prove
binary equivalence. The source header states GPLv2; a complete transitive source
and firmware license inventory remains necessary. No top-level DKMS metadata is
present in this exact tree. Do not run its bundled shell utilities/install targets.
Primary source:
[Candidate SDIO source](https://github.com/EvilOlaf/rtl8189ES_linux/blob/be148d226d22214a173e5b2dfe4287e53685ceda/os_dep/linux/sdio_intf.c)

Possible bounded later delivery: pin source plus the needed API compatibility
patch, build a reproducible external-module/DKMS package against the exact selected
Debian ARM64 kernel headers, inspect module alias/version/vermagic and package
footprint, then keep radio power/clock/GPIO and actual association tests physical.
It must not silently enable unverified vendor platform callbacks. The module is not an adopted build input or validated driver.

## Kernel/HDMI implications

Armbian's selected `mainline-kernel.conf.sh` defaults to a rolling stable branch
when no explicit override exists. Fixing its build-framework commit therefore
does not pin the kernel revision. A selected kernel tag/commit, configuration and
complete ordered patch inputs must be recorded before building. Source:
[Armbian kernel version selection](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/config/sources/mainline-kernel.conf.sh)

The complete, nontruncated pinned Git tree has 457 `.patch` blobs in sunxi-6.12
(181 Armbian, 34 DRM, 242 megous) and 526 in sunxi-6.18 (170 Armbian, 23 backports,
43 DRM, 6 media, 284 megous). These are archive inventory counts, not applied
patch counts or a minimal H616 dependency set. There is no path containing SV08
under this 6.12 archive; 6.18 contains distinct stock and Max DTS files. Do not
borrow the Max DTS or infer every other branch lacks SV08 support.
The 6.12 archive contains H616 HDMI PHY/DE33 bindings and CB1 HDMI/EMAC/storage
patches: adopting just a board DTS cannot substitute for reviewing platform code.

Upstream stable Linux v6.12.107's `sun8i_hdmi_phy.c` has A83T/H3/R40/A64/H6 match
entries and no H616 entry. This is a narrowly verified source observation, not a
complete audit of Debian's patches, all display paths or electrical compatibility.
Never replace an H616 compatible with H6 merely to bind a driver. Source:
[Stable Linux HDMI PHY](https://github.com/gregkh/linux/blob/v6.12.107/drivers/gpu/drm/sun4i/sun8i_hdmi_phy.c)

Before adopting a maintained Armbian platform set instead of the Debian kernel,
finish the existing ADR requirement and compare complete patch/driver/firmware
maintenance, boot/storage/display dependencies and release test costs. Do not
accumulate an unmaintained set of core backports simply to retain a package name.
A radio module package could be tested independently without deciding the entire
board kernel today. No new owner question or physical action is required for
that source/package work; the existing [release checklist](host-os-tasks.md) remains authoritative.

## Evidence inventory

The [source record](host-radio-kernel-intake-20260912.json) binds the downloaded
files to SHA-256 values and Git blob IDs. GitHub tree responses were complete;
selected files were checked against their tree/contents entries. The upstream
Linux v6.12.107 tag resolves to `f717995cb7dcd8998ab15516b8006aea09cfde0d`.
Raw intake stays under ignored `local/feature-workflow/board-source-audit/`.
No downloaded revision is claimed to be tested compatibility.
