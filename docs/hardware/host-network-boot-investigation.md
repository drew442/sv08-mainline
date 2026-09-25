# Removable SD and network-boot investigation

Date: 2026-09-25. Scope: assess whether a removable SD card can boot a
development/recovery system without rewriting the installed eMMC. This is a
read-only investigation; it does not authorize a printer reboot, boot-policy
change or firmware write.

## Finding

This is worth pursuing as an optional development and recovery path. Keep the
eMMC as the default source and use a removable card to load a known, small
bootloader/kernel/initramfs. Let Linux initramfs obtain an ordinary DHCP lease
over wired Ethernet and mount a read-only NFS root from Beelink. This avoids
copying a multi-gigabyte root filesystem onto the card or eMMC for each test.
Keep writes volatile for the first trial. This is a development convenience,
not yet a recovery guarantee or release feature.

## Evidence and limits

- The current diagnostic Linux identifies the board as `Sovol SV08 test-sv08-01`
  and the device-tree compatibility as `sovol,sv08`, `bigtreetech,cb1`,
  `allwinner,sun50i-h616`. The owner reports PCB marking `H616_JC_6Z_V1.2`.
  These facts do not prove that the CB1 boot firmware is interchangeable.
- The current Linux kernel exposes wired `end0`; at inspection it had no carrier.
  The known Linux kernel path has previously provided Ethernet, but that does not
  prove Ethernet works in SPL or U-Boot.
- The pinned source-built U-Boot configuration contains DHCP and TFTP commands
  and a `SUN8I_EMAC` driver selection. Its SV08 U-Boot device tree currently
  inherits the H616 `emac0` node disabled. The selected driver and H616 GMAC
  clock/PHY integration have not been validated in U-Boot. Do not make the
  first prototype depend on TFTP or DHCP in U-Boot; keep the kernel and initramfs
  local on SD and use Linux's network initialization and NFS-root path instead.
- The H616 reference manual names SMHC0 as the external SD interface and SMHC2
  as eMMC. BIGTREETECH's CB1 eMMC instructions state that SD has boot priority
  over onboard eMMC. This is encouraging because the SV08 host shares H616/CB1
  lineage, but it is not measured evidence for this integrated SV08 board; the
  current board must still be tested before relying on SD-first selection.
- Beelink detects the inserted 2 GB FAT card, but its current filesystem is
  already populated and has no observed Linux boot files. The owner has said
  its contents may be erased. No files or media have been changed.
- The Linux kernel documents a DHCP plus NFS-root boot path. The selected kernel's
  built-in NFS/root autoconfiguration options still need checking.

## Network configuration choice

Do not add DHCP boot-file or TFTP-server options to the router for the first
prototype. Let Linux initramfs obtain an ordinary DHCP lease and place the
Beelink NFS server address in the SD boot configuration. Beelink currently uses
a DHCP lease, so reserve its address (or configure a stable local address) before
writing that configuration. No addresses or credentials belong in tracked
project files.

The printer must be connected by Ethernet to the same LAN as Beelink. Its
existing Wi-Fi is initialized by Linux and cannot be assumed to be available in
the bootloader or the earliest network initramfs.

## Safety and release boundary

The trial must use the spare card only and must leave the factory eMMC stored.
The current eMMC image has boot-health and RAUC services masked, and its A-slot
trial has not been confirmed. Do not reboot it merely to probe SD priority; first
prepare and independently review a boot/counter-safe procedure. Do not change
U-Boot environment counters or rewrite the installed loader during this work.

TFTP and ordinary DHCP do not authenticate images. A release recovery path must
verify signed boot artifacts before execution, define failure behavior when the
server is missing, and never write eMMC without explicit user action. Do not
advertise network boot as a supported recovery option until signature policy,
power-loss behavior and physical boot/fallback tests pass.

## Next gates

1. Correct U-Boot DT/driver support for the measured H616 GMAC and compile it;
   alternatively prove that the selected known-good loader can boot a kernel
   from the SD without changing persistent eMMC state.
2. Build a minimal SD launcher with the already-tested kernel and a read-only
   NFS-root prototype. Check memory use against the measured 1 GiB host and keep
   all mutable state volatile for the first trial.
3. Independently inspect the SD image and test its boot script, network timeout,
   read-only NFS root and refusal/fallback behavior offline.
4. Reconcile the current A-slot trial state and UART capture before requesting
   one supervised physical boot test.

Primary documentation accessed 2026-09-25: BIGTREETECH's [CB1 repository
README](https://github.com/bigtreetech/CB1#cb1-emmc-version) says its eMMC
version accepts an SD card as the OS source and gives SD higher priority than
onboard eMMC; that is a related-board statement, not SV08 validation. The
[U-Boot environment variables](https://docs.u-boot.org/en/latest/usage/environment.html)
and [PXE boot method](https://docs.u-boot.org/en/latest/develop/bootstd/pxelinux.html)
documents describe DHCP/TFTP flows but do not establish an enabled H616 Ethernet
device here. Linux documents the kernel `ip=dhcp` and `nfsroot=` path in its
[NFS-root guide](https://docs.kernel.org/admin-guide/nfs/nfsroot.html); the
selected kernel's built-in NFS/root autoconfiguration options still need checking.
The H616 controller mapping is from the pinned U-Boot source and Allwinner H616
User Manual v1.0, §3. The board-specific manual copy is referenced in the local
[SV08 hardware inventory](stock-sv08.md).
