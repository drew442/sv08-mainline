# Redundant boot environment: offline evidence

2026-09-10. No physical printer was accessed. This is a new-image storage candidate,
not a factory-module modification or validated board boot chain.

The [layout](../../configs/host-os/environment-layout.json) allocates two 64 KiB
copies at 4 MiB and 8 MiB, before partition 1 at 16 MiB. The GPT checker now checks
these reservations against the protective MBR, both GPT headers/arrays, SPL space,
all partitions and each other. It also reports partition identities and extents.
Unit tests reject all of those collisions and unaligned ranges.

## Reproduce

Use the U-Boot v2026.07 archive pinned in
[tool sources](../../configs/host-os/offline-tool-sources.json), extracted into a
separate disposable build source tree. Apply, in order,
[the sandbox environment patch](../../patches/u-boot/0001-sandbox-mmc-environment.patch)
and [the large-image patch](../../patches/u-boot/0002-sandbox-mmc-large-images.patch).
Do not modify `upstream/` or the retained original source archive.

Start with `sandbox_defconfig`; set the following using U-Boot's `scripts/config`
and run `make olddefconfig` before building:

```text
CONFIG_EFI_CAPSULE_AUTHENTICATE=n
CONFIG_BOOTMETH_RAUC=y
CONFIG_BOOTMETH_RAUC_RESET_ALL_ZERO_TRIES=n
CONFIG_ENV_IS_NOWHERE=y
CONFIG_ENV_IS_IN_MMC=y
CONFIG_ENV_IS_IN_FAT=n
CONFIG_ENV_IS_IN_EXT4=n
CONFIG_ENV_IS_IN_SPI_FLASH=n
CONFIG_ENV_REDUNDANT=y
CONFIG_ENV_REDUNDANT_UPGRADE=n
CONFIG_ENV_MMC_DEVICE_INDEX=10
CONFIG_ENV_MMC_EMMC_HW_PARTITION=0
CONFIG_ENV_OFFSET=0x400000
CONFIG_ENV_OFFSET_REDUND=0x800000
CONFIG_ENV_SIZE=0x10000
```

Use a copy of the generated sandbox DTB: enable the existing `mmc10` node,
set `/bootstd` property `bootdev-order` to `mmc10`, and add `/bootstd/rauc` with
`compatible = "u-boot,distro-rauc"`. Its backing filename is `mmc10.img`.
The sandbox retains its nowhere environment as default, so the test explicitly
selects MMC and loads it. A board must load its verified MMC environment by default;
this fixture does not establish that integration.

With the previously checked factory-sized relocated GPT fixture and native RAUC
1.15.2, run without `--execute` for inspection, or execute this file-only test:

```sh
python3 tests/uboot_environment.py \
  --uboot build/u-boot-sandbox-raw-v2/u-boot \
  --dtb build/uboot-ab-tests/test.dtb \
  --image build/gpt-layout-v1/layout-test.img \
  --rauc build/rauc-native-v2/rauc \
  --work build/uboot-environment-new --execute
```

The test requires U-Boot tools, FAT/mtools, libubootenv tools and D-Bus on the
workstation. It creates its own harmless boot/recovery marker scripts and copies
the input disk into a new directory below ignored `build/`. It never opens the
system's `/etc/fw_env.config`: RAUC's subprocesses use wrappers that supply the
explicit regular-file configuration. A private D-Bus/service is stopped afterward.

## Results and limits

The final run is retained under `build/uboot-environment-v4/`; the
[public evidence record](host-environment-20260910.json) includes hashes and scope.
It verifies real U-Boot → libubootenv and libubootenv → U-Boot writes, real RAUC
`bootloader=uboot` selection/marking, B trial decrement and A fallback decrement.
Corrupting the newest copy falls back to the older valid CRC in both readers.
Corrupting both copies routes to the recovery script. Exhausted attempts, invalid
counters/order/layout, and attempts left only on an excluded slot also route to
recovery. All bytes outside the two environment regions remain unchanged.

The first large-image test failed to read recovery beyond 4 GiB. Source inspection
found signed-int truncation of mapped size and 32-bit multiplication of block
offsets in the sandbox MMC implementation. The documented patch corrects both;
the full factory-sized test passes afterward. Earlier A/B marker tests did not
read the recovery partition and therefore did not establish this behavior.

Marker scripts returning successfully are not a recovery OS or Linux boot. This
test does not install a bundle, boot the physical H616, validate eMMC power-loss
behavior, confirm application health, or reconcile interrupted update transactions.
The board MMC index, addresses, boot-device restriction and default environment
loading remain explicit integration requirements. See
[decision 0008](../decisions/0008-redundant-boot-environment.md) and the
[remaining task list](host-os-tasks.md).

## Source provenance

Primary source inspected locally on 2026-09-10: U-Boot commit
`ece349ade2973e220f524ce59e59711cc919263f`, `board/sandbox/sandbox.c`,
`drivers/mmc/sandbox_mmc.c`, `arch/sandbox/cpu/os.c`, `include/os.h`, `env/mmc.c`
and `boot/bootmeth_rauc.c`; RAUC commit
`4fb7c798d6ae412344fb8f8d310d773046af3441`, `src/bootloaders/uboot.c`.
Archive URLs/hashes are in the pinned tool-source record above. These source
claims and workstation observations do not identify the printer's board revision.
