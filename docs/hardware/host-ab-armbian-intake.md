# Armbian board-support source intake

Access date: 2026-09-09. Research reference commit:
`a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015` in `armbian/build`.
This is a source audit, not an adopted build dependency or tested compatibility.
No installer, kernel build, bootloader build or hardware activation was run.

The pinned [SV08 board definition](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/config/boards/sovol-sv08.csc)
selects sun50iw9, `bigtreetech_cb1_defconfig`, FAT boot, ttyS0 and
`sun50i-h616-sovol-sv08.dtb`. File SHA-256:
`a6545b15a678a37f7bcfb0afd221280ffd76e833961a36dc11389b984999114e`.

The [SV08 DTS in its 6.18 patch archive](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/patch/kernel/archive/sunxi-6.18/dt_64/sun50i-h616-sovol-sv08.dts)
is explicitly marked by its author as not yet verified on hardware. It includes
the CB1 dtsi and declares SV08/CB1/H616 compatible strings. That does not identify
our physical board or prove the author's electrical-equivalence claim. File
SHA-256: `b6dd738949b7cbb5e54f285b275d22b1fd930f40be7959a8723e0394e2f695a6`.
The DTS license expression is GPL-2.0+ OR MIT; review all transitive source and
patch licenses before redistribution.

Its configured eMMC width of eight bits, 45 MHz limit and `no-1-8-v` agree with
the [captured vendor configuration](host-ab-build.md). This is agreement between
configurations, not electrical measurement. Optional LED, GPIO-I2C, CAN and TFT
pin assignments are not validated for this printer and must not be enabled by
copying this DTS wholesale. Separate Max and Zero targets do not supply missing
SV08 evidence.

The [SV08 U-Boot patch entry](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/patch/u-boot/v2026.07-sunxi64/board_sovol-sv08)
is a symlink to `board_bigtreetech-cb1`. It is a concrete route to audit, not proof
that our DRAM setup or boot medium layout matches. PCB revision, DRAM and radio
identity remain unresolved.

## Next review before adoption

1. Trace the board definition through its family configuration to exact kernel,
   U-Boot and TF-A commits, patch series, external drivers and firmware inputs.
2. Compare the complete Ethernet, HDMI and Wi-Fi bindings/clock/power dependencies
   with captured evidence and the Debian kernel package. Do not translate vendor
   compatibles by name alone. The SV08 DTS located in this intake is in the 6.18
   archive; this does not establish support or absence in every other branch.
3. Evaluate a maintained Armbian kernel/boot-support set with Debian userland
   against the preferred Debian-maintained kernel. Record any change in an ADR;
   do not create an unmaintained collection of core-driver backports merely to
   retain the existing package name.
4. Before building, pin adopted sources explicitly and record licenses, applied
   patches, validation limits and the path to retiring patches as upstream
   support becomes available. This research commit is not in upstream-lock.json.
5. Before hardware activation, validate DRAM, boot offsets, storage, networking
   and display on the named profile with the existing recovery path. Board/photo
   and device-identity tasks remain in the host build task list; source review
   and application packaging can continue offline.

The subsequent [GPT/SPL experiment](host-ab-layout.md) records the default raw-write
collision, a relocated GPT alternative and further family/boot-patch findings.

The subsequent [narrow boot-source compilation](host-cb1-boot-compile.md) resolves
the TF-A pin and produces repeatable U-Boot/BL31 artifacts. It records additional
configuration discrepancies and does not adopt full Armbian board equivalence.
