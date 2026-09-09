# GPT/SPL layout experiment

Date: 2026-09-09. Offline regular-file experiment only; not a boot image.
The factory-capacity test file is 7,818,182,656 bytes with the six partitions in
[host-ab.json](../../configs/images/host-ab.json). No device was partitioned.

The pinned Armbian [sunxi64 family include](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/config/sources/families/include/sunxi64_common.inc)
writes `u-boot-sunxi-with-spl.bin` at byte 8192. Normal GPT places its primary
128-entry array at bytes 1024–17407, so the regions overlap even when the first
partition starts at 16 MiB. Leaving a large first-partition gap alone does not
solve this problem. Source accessed 2026-09-09; the writer was inspected, not run.

The alternative tested here moves the primary GPT entry array to LBA 4096
(2 MiB), retaining both normal headers and the backup array at the end of disk.
The array occupies sectors 4096–4127; first usable sector becomes 4128 and the
first partition still begins at 32768 (16 MiB). A provisional SPL reservation
from byte 8192 to byte 1048576 is now collision-free. That bound is a test
constraint, not a measured bootloader length; an adopted bootloader must fit or
the allocation must be reviewed again. Redundant environment locations are not
allocated by this experiment.

`sgdisk --verify` reports no problems and explicitly notes the deliberate gap
between the primary header and array. The [read-only checker](../../scripts/check_gpt_layout.py)
independently checks header/array CRCs, matching GPT copies, usable bounds and
SPL/metadata/partition overlap. Tests reject standard GPT and corrupted entries,
and accept the relocated fixture. This proves file-format consistency only.
Boot ROM, SPL, U-Boot partition discovery, eMMC boot selection and recovery tools
still need validation. Do not run partition-table repair tools that normalize the
array location without preserving the SPL reservation.

To reproduce the metadata experiment, use a **new regular file below build/**,
not a block device. Create it with the profile size, run `sgdisk --clear
--move-main-table=4096`, then add the six profile partitions at their recorded
MiB-aligned offsets. Validate with:

```sh
sgdisk --verify build/gpt-layout-v1/layout-test.img
python3 scripts/check_gpt_layout.py build/gpt-layout-v1/layout-test.img
python3 -m unittest discover -s tests -v
```

## Further boot-source findings

The pinned family include selects U-Boot tag `v2026.07`, TF-A tag `lts-v2.12.9`,
current kernel series 6.18, legacy 6.12 and edge 7.2. These are source references,
not adopted exact source commits; trace/resolve complete sources before builds.
The [sun50iw9 family](https://github.com/armbian/build/blob/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/config/sources/families/sun50iw9.conf)
selects the H616 TF-A platform. The CB1 U-Boot patch set comprises:

| Patch | SHA-256 |
| --- | --- |
| `001-bigtreetech-cb1-dts-and-defconfig.patch` | `0bff09f1763dd4e74249e3500bebcbfd84cde79ac66b9556ce706de958318416` |
| `002-bigtreetech-cb1-PC3-eMMC-selpin-set-to-pull-down-mode.patch` | `1fe801e57ce115f9d91dde132f1e756d2cf4a97284db4e4aa85c3bb0905eac81` |

Primary source: [pinned patch directory](https://github.com/armbian/build/tree/a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015/patch/u-boot/v2026.07-sunxi64/board_bigtreetech-cb1),
accessed 2026-09-09. It assumes an H616 DDR3-1333 profile, AXP313 power and PC3
pull-down for eMMC selection. Those are patch assumptions, not newly established
facts about test-sv08-01. The host PCB/DRAM/PMIC and boot diagnostics need evidence
before hardware use. A/B environment power-failure behavior is also unresolved.
