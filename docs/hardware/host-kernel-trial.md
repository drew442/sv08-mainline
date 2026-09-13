# One-shot kernel trial on the existing spare

2026-09-13. This is a temporary test of the new kernel/DT against the existing
Debian bring-up root and vendor bootloader. It does not activate A/B or validate
printing. The [compile record](host-kernel-compile.md) and
[decision 0015](../decisions/0015-board-kernel-compile-baseline.md) define scope.

## Loader and target evidence

The [physical console capture](test-sv08-01-host-console.md) establishes the
vendor loader's `mmc 1:1` boot-script load path. The captured bootloader prefix
contains `bootdelay=-2`, `boot_scripts=boot.scr.uimg boot.scr`,
`boot_prefixes=/ /boot/`, and a scanner that continues to the next script when
`source` returns. It also contains the `fatrm` command/help. These are binary
defaults plus observed boot behavior, not an interactive environment dump.
The new dispatcher must be tested unarmed on hardware before those source
observations are promoted to a working fallback.

Fresh SSH inspection identifies the spare as a 31,272,730,624-byte MMC, product
SBG6PX, root on mmcblk2p2 and FAT boot on mmcblk2p1. Boot had 220,110,848 bytes
free and root about 6.09 GB free at inspection. No existing `boot.scr.uimg` or
extlinux configuration was found in the checked boot locations. UUIDs and raw
identity/hash records stay under ignored `local/host-kernel-61851/`.

## Dispatcher and staging boundaries

The [template](../../configs/host-os/diagnostic-boot.cmd.in) is rendered with the
freshly identified root UUID and target **`mmc 1:1`**, then wrapped with
`mkimage -A arm -T script -C none`. Its fixed trial directory is
`/sv08-trial-61851-c1/`, containing `Image`, `board.dtb`, `uInitrd` and, only when
separately armed, `armed`. Never reuse the marker for another artifact set.

1. Hash and retain the original boot files, confirm the target and absence of
   an existing dispatcher, and stage only the new **unarmed** dispatcher.
2. Start console logging and reboot. Require its return-to-original marker,
   unchanged original kernel and SSH, and unchanged original boot-file hashes.
3. After the kernel/module build and artifact review, stage the alternate files
   and unique module release without replacing the vendor files. Build a matching
   initramfs with Debian initramfs-tools and wrap it using the existing legacy
   ARM/Linux/ramdisk/gzip format. Inspect contents and module dependencies.
4. Check file sizes against the actual loader addresses: kernel 0x40080000,
   DT 0x4fa00000, script 0x4fc00000 and initrd 0x4ff00000. Account for kernel
   relocation/initrd expansion and firmware reservations, not only file sizes.
   Hash back the installed artifacts before creating the marker.
5. Arm and reboot with logging. The marker is consumed before any candidate
   load; failed deletion, a retained marker or any failed load refuses handoff.
   Candidate bootargs bypass vendor BoardEnv overlays and transiently mask
   Klipper, Moonraker and KlipperScreen services.
6. Inspect kernel, actual DT, root, regulator reports, Ethernet/SSH, USB,
   temperatures and failed units. Reboot to confirm return to the original
   kernel because the marker was consumed. Keep heater/motion tests separate.

The original boot.scr, boot.cmd, BoardEnv, Image, uInitrd, DT/overlay files and
vendor module directory remain the fallback. Do not save U-Boot environment or
change the raw bootloader. A hung candidate may still require the owner's reset
with all relevant power sources considered; the USB cable may keep the host
powered. Serial control-line reset has not been established.

## Offline validation

```sh
python3 tests/diagnostic_boot.py \
  --uboot build/u-boot-sandbox-v1/u-boot \
  --work build/diagnostic-boot-v1 --execute
```

Seven invocations pass against real temporary FAT files and U-Boot 2026.07
sandbox: marker consumption/returned boot, second invocation, no marker, missing
Image, deletion refusal using a nonempty directory, wrong-device refusal, and
subsequent correct-device use of the preserved marker. Only the target interface
and root UUID are substituted. Real `booti` receives deliberately invalid offline
payloads and returns; Linux execution is not claimed. The script's original
scanner variables remain unchanged. This is not the vendor 2021.10 binary or a
power-interruption test. No unattended update policy uses this temporary marker.
