# Board recovery preparation

2026-09-13, test-sv08-01 diagnostic target. The owner authorized continued host
hardware preparation; new product features remain paused. This extends the
existing [independent recovery image](host-recovery-image.md) to the reviewed
[6.18.51 board kernel](host-kernel-packages.md). It does not validate a physical
recovery boot, printing, preserved-slot selection or signed restoration.

## Inputs and separation

[The board profile](../../configs/host-os/recovery-test-sv08-01.json) binds the
two reviewed Debian packages, packaged kernel/configuration/DT hashes, complete
installed module inventory, six partition identities and 512 MiB partition 5.
The recovery filesystem UUID is distinct from its GPT PARTUUID. A similar board
or a filesystem label is not sufficient identification.

[The builder](../../scripts/recovery_image.py) adds an explicit `derive` stage.
It checks the completed parent assembly receipt, copies that root, installs only
the hash-checked board package pair in private mount/PID/network namespaces, and
records the parent's unchanged inventory and receipt. It never alters the
authoritative QEMU recovery assembly. Package scripts receive temporary log and
build directories matching the recovery root's existing volatile symlinks.
Ordinary kernel post-installation hooks run; their unused generic initramfs is
removed from the derived copy before its receipt is written. The board recovery
initramfs is assembled separately.

Two failed derivations exposed and retained evidence of missing volatile build
directories and a shared module-directory mode difference. The latter was only
0775 versus 0755 on the release directory: all 2677 files, contents, ownership,
xattrs, hardlinks and generated depmod metadata matched. The builder explicitly
normalizes that directory and then requires the original complete inventory
hash; it does not relax module verification or replace the expected digest.

Recovery has no installed regulatory database and no enabled networking. Its
receipt records that absence. The running host independently selects Debian's
installed upstream regulatory-signature alternative; recovery does not download
an extra package or disable signature verification.

## Build sequence

On an isolated build machine with the preserved assembly and exact packages:

```sh
sudo unshare --mount --pid --fork --net \
  python3 scripts/recovery_image.py derive \
  --assembly build/board-inputs/recovery-base \
  --packages build/board-inputs \
  --board-profile configs/host-os/recovery-test-sv08-01.json \
  --work build/board-recovery-derived-v3 --execute

sudo unshare --mount --pid --fork --net \
  python3 scripts/recovery_image.py build \
  --assembly build/board-recovery-derived-v3 \
  --board-profile configs/host-os/recovery-test-sv08-01.json \
  --work build/board-recovery-image-v1 --execute
```

Omit `--execute` for inspection. Outputs must be fresh repository `build/` paths.
Do not reuse the parent's compressed `/usr`: its package contents differ.
The board initramfs checks built-in MMC, UART, H616 clocks/pins and PMIC/I2C
dependencies, and includes any modular ext4/loop/squashfs dependency closure.
It also checks that the installed BusyBox supports partition read-only control.

## Selection and validation

[The board selector](../../configs/host-os/recovery-board-root) requires exactly
one correct `root=PARTUUID=...` and one canonical manifest digest. Cache-free
`blkid`, canonical block identities and sysfs identify a unique partition;
wrong index, capacity, filesystem UUID, ambiguity and missing devices refuse.
It sets only that partition read-only and verifies both ioctl and sysfs readback
before mounting ext4 without journal replay. All existing manifest, compressed
userspace, mount and loop-device checks then run unchanged.

The default QEMU boot template remains byte-identical. Shell fixtures exercise
the actual generated parser and refusal paths. A separate real partitioned-QEMU
test attaches a writable disk and uses Debian 6.12 with its VirtIO closure and
the generated board selector. Its positive run passes every common gate and
`switch_root`, reporting whole-disk read-only **0**, recovery-partition read-only
**1**. Wrong manifest binding and same-size corrupted compressed userspace both
refuse and shut down before handoff.

That VM uses a minimal executable userspace fixture. It is not a complete GTK
boot or a QEMU test of the H616 kernel, which lacks the VirtIO/PL011 platform
configuration. The earlier complete QEMU UI evidence remains separately scoped.
The accepted VM gate SHA-256 is
`f17803f4d4cdaa9bc008e791a85c2e6179dd54a2eda4836494003b4fec4895ce`.
Private derivation, VM logs and preservation receipts remain in ignored paths.

The [complete diagnostic disk](host-board-image.md) must add its independent
raw kernel, exact DT and `recovery.scr` to partition 5 before the new loader can
dispatch it. A recovery partition image alone is not a whole-eMMC write image.
