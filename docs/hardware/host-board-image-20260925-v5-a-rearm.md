# v5 A-slot attempt re-arm

Date: 2026-09-25. Hardware profile: `test-sv08-01`; board marking
`H616_JC_6Z_V1.2` is owner-reported. The spare eMMC was running the v5 image in
slot A. The factory eMMC remained stored.

## Preconditions and reviewed operation

The live root was PARTUUID
`26c68198-9248-47af-bbd3-643f1b604ef5`, resolved to `/dev/mmcblk1p2` and
mounted read-only. Its parent was the installed spare eMMC, an MMC device named
`SBG6PX`, 31,272,730,624 bytes. The full hardware CID and boot ID are kept in
ignored local evidence.

Both redundant 64 KiB U-Boot environment copies at 4 MiB and 8 MiB passed CRC
validation. The 4 MiB copy was flag 1 with `BOOT_A_LEFT=3`; the 8 MiB copy was
newer, flag 2, with `BOOT_A_LEFT=2`. Both contained `BOOT_ORDER=A`,
`BOOT_B_LEFT=0`, and `sv08_env_layout=ab-8gb-v1`. The pair SHA-256 before the
write was
`e580e94e2feed60177a208b202d751d955aa20fc5ab8d454310ee834bcc85f65`.

An independent GPT-6 Sol high-consequence review returned PASS WITH CONDITIONS
for a live, single-variable update and no reboot. The conditions required
rechecking the boot ID and target, validating both CRCs and current policy,
using only the two recorded environment regions, and preserving the running
host if readback failed. All preconditions matched immediately before the
operation. A temporary `/run/sv08-fw-env-read.config` contained:

```text
/dev/mmcblk1 0x400000 0x10000
/dev/mmcblk1 0x800000 0x10000
```

The installed `libubootenv-tool` was version `0.3.5-0.1+b2`. The sole write
command was:

```sh
fw_setenv -c /run/sv08-fw-env-read.config BOOT_A_LEFT 3
```

## Readback and limits

After `sync`, both raw copies were read again. Both CRCs remained valid. The
4 MiB copy became flag 3 with `BOOT_A_LEFT=3`; the 8 MiB peer remained byte for
byte unchanged at flag 2 with `BOOT_A_LEFT=2`. The pair SHA-256 became
`98cdc1d8cb93026f9bce651011281e10e41c7c9b37af43769b24fb137d4d3010`. The
selected `fw_printenv` policy is `BOOT_ORDER=A`, `BOOT_A_LEFT=3`,
`BOOT_B_LEFT=0`, and `sv08_env_layout=ab-8gb-v1`. Comparing the selected
pre-write and post-write environments found only `BOOT_A_LEFT` changed, from 2
to 3.

The same boot ID remained active through readback; no reboot occurred. This
restores one A attempt of headroom for a separately supervised test. It does
not mark A healthy, unmask boot-health/RAUC, validate A/B fallback, or authorize
a boot. The complete private before/after environment copies and command
transcript are under ignored `local/sd-network-physical-20260925/`.
