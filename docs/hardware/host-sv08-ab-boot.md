# SV08 A/B bootloader composition candidate

2026-09-13. This source-built SPL/TF-A/U-Boot candidate now includes the existing
RAUC A/B policy and corrected diagnostic board inputs. It passed offline build
and independent artifact inspection. **It has not been written to the printer.**
The [physical Linux trials](host-kernel-trial.md) used the existing vendor loader.

The [manifest](../../configs/host-os/sv08-boot-compile-candidate.json) retains the
earlier pinned U-Boot, TF-A and two Armbian CB1 patches, then adds a hash-pinned
[diagnostic DT patch](../../patches/u-boot/0003-sv08-uboot-diagnostic.patch),
[configuration fragment](../../configs/host-os/sv08-uboot-ab.fragment) and
[complete default environment](../../configs/host-os/sv08-default.env).
PCB revision remains unknown. Source-backed configuration comparisons and
driver reports below are not instrument measurements or proof of new SPL operation.

## Corrections relative to the CB1 compile fixture

- The old SPL's `CONFIG_AXP_DCDC3_VOLT=1100` programs the DRAM rail through
  `board/sunxi/board.c` and `drivers/power/axp_spl.c`, independently of DT bounds.
  The new explicit **1500 mV** matches both vendor and diagnostic Linux driver
  reports. CPU DCDC2 stays at 1000 mV, matching the diagnostic report. Setting
  these SPL options to zero disables a rail; it does not preserve its setting.
- The vendor clock report is 1.44 GHz for pll-ddr0/dram. U-Boot's
  `arch/arm/mach-sunxi/dram_sun50i_h616.c` programs PLL5 at twice `DRAM_CLK`, so
  explicit 720 MHz agrees with that reported PLL setting. DDR3 training,
  timings, ODT and memory stability remain untested in the new boot chain.
- The bootloader-only DT removes inherited PH5/PF6/PG15 LED outputs and the
  USB VBUS PC16 GPIO; PC16 also belongs to the eMMC pin group. Tested Linux's
  USB supply has no such GPIO. SDIO is disabled in the loader and initialized
  by Linux. USB OTG stays peripheral; eMMC remains eight-bit, no 1.8 V switching,
  with a conservative 20 MHz loader limit. These are compiled settings.
- Explicit aliases assign SD controller 0 and eMMC controller 1. The pinned
  `mmc_get_env_dev()` maps MMC2 boot source to environment device 1, consistent
  with the observed vendor-loader path. New-loader enumeration is still untested.

The pinned U-Boot source uses `ENV_USE_DEFAULT_ENV_TEXT_FILE` and
`ENV_DEFAULT_ENV_TEXT_FILE`; obsolete names were caught in review before build.
Both `DEFAULT_DEVICE_TREE` and `OF_LIST` must name the new DT. The first build
correctly refused FIT assembly while its inherited list still selected CB1;
the corrected fresh build passed. Effective configuration is checked after
`olddefconfig`, preventing silently dropped required settings.

## Environment and recovery contract

The new layout reserves redundant 64 KiB environments at 4 and 8 MiB in the MMC
user area, with partition 1 starting at 16 MiB. **Never apply these offsets to
the current single-root spare:** its FAT partition starts at 4 MiB.

The default `bootcmd` invokes the exact existing
[guarded dispatcher](../../configs/host-os/boot-dispatch.cmd). Only valid layout,
order and counters permit RAUC scanning. RAUC's own missing-value initialization
means disabling reset-of-exhausted-tries alone is insufficient. The compiled
defaults deliberately omit `sv08_env_layout`, `BOOT_ORDER` and both counters.
Corrupt environments therefore cannot silently replenish trials.

Valid persistent environments replace compiled defaults. **Seed both copies with
the complete boot commands, addresses and console variables from the default
environment, plus the valid layout marker and initial slot order/counters.**
Seeding only counters would omit the guarded boot path.

RAUC uses boot/root partition pairs `1,2 3,4`, three tries, and mmc1-only boot
discovery. Recovery is loaded from partition 5 using its own script, kernel,
initramfs and root. The image assembler must supply those files and matching
partition identities. Do not copy the temporary one-shot dispatcher into this
layout. Failed SPL/DRAM initialization still uses the owner's accepted USB eMMC
writer recovery path; A/B cannot recover before its loader runs.

## Reproduce and validate

The existing [builder](../../scripts/build_cb1_boot_candidate.py) now accepts an
explicit manifest while retaining its original default compile fixture. It checks
source/integration hashes, defaults to inspection, requires a fresh build path,
and never assembles or writes a disk. Use the archive and patch paths recorded
in the manifest:

```sh
python3 scripts/build_cb1_boot_candidate.py \
  --config configs/host-os/sv08-boot-compile-candidate.json \
  --work build/sv08-ab-boot-new \
  --uboot-archive build/ab-source-intake/u-boot.tar.gz \
  --tfa-archive build/ab-source-intake/tf-a-c2a0e708.tar.gz \
  --patch-directory local/os-design-20260909/armbian/patch/u-boot/v2026.07-sunxi64/board_bigtreetech-cb1 \
  --execute
python3 tests/uboot_board_candidate.py \
  --build build/sv08-ab-boot-new --sandbox build/u-boot-sandbox-v1/u-boot
```

The [result](host-sv08-ab-boot-20260913.json) records all artifact hashes.
Independent inspection verified the 40,960-byte SPL checksum, linked calls with
1000/1500 mV arguments, FIT configuration-to-DT binding and combined binary end
at byte **794,297**, below the 1 MiB reservation. The default environment was
decoded from the linked ELF symbol, not merely checked in its source header.
Five missing/invalid/exhausted-state sandbox cases reached the recovery path.
The existing [raw CRC/RAUC/recovery fixture](host-environment-build.md) remains
separate evidence; these five tests do not simulate raw environment corruption
or successful physical recovery. A harmless U-Boot ELF section-link warning was
retained in readelf output; no warning-free-build claim is made.

## Remaining image composition

Integrate the [kernel packages](host-kernel-packages.md) into clean current host
roots, port the independent recovery early-root selection from its QEMU `/dev/vda`
fixture to the board partition identity, and assemble the complete six-partition
factory-capacity image with relocated GPT, new SPL/FIT and both seeded environments.
Validate layout, boot-file hashes, persistence and recovery references before
producing the separate USB-writer plan. Keep printer services masked in the first
host-only hardware trial. Cold boot, power loss, physical A/B and recovery remain
hardware tasks. No new backup proof or PCB-photo prerequisite is introduced.

Source evidence is the exact pinned U-Boot/TF-A files above and private
`local/host-kernel-61851/vendor-runtime-baseline.json`, read 2026-09-13. Licensing
and patch-retirement policy remain those of the
[earlier source intake](host-cb1-boot-compile.md); complete release source/license
distribution remains outstanding.
