# Running SD recovery host: physical boot, 2026-09-29

H13 host-only boot passed on `test-sv08-01`, owner-reported
`H616_JC_6Z_V1.2`. The owner moved the [prepared SanDisk SD](host-sd-recovery-host-write-20260929.md),
connected Ethernet and USB serial, and left PSU power off as requested. USB powers
the Linux host. The installed spare eMMC is visible; factory eMMC remains stored.
No media write, MCU, heater or motion operation was performed during this session.

## Measured result

The receive-only trace reaches the SD loader, Linux `6.18.51-sv08-candidate1`,
root/configuration admission, normal systemd and GTK. Ethernet `end0` reports
100 Mbps full-duplex carrier and DHCP `192.168.1.141`. The network ED25519 key
matches the fingerprint emitted by the trusted serial trace. Key-only SSH to the
named `recovery` account and `sudo -n id -u` succeed.

The recovery display and SSH units are active/running with no restarts; no failed
units were reported. The system remained available after eight minutes, beyond
the old diagnostic watchdog. Root is SD `/dev/mmcblk2p2`, ext4 `ro,norecovery`;
`/usr` is read-only SquashFS. A direct BLKROGET query confirms the root partition
is protected. Runtime mounts are volatile tmpfs with the configured limits.

Xrandr reports native 1024×600 at 59.82 Hz. The KVM snapshot visibly shows the
recovery interface and the expected missing `/data/sv08/state.json` diagnostic.
No persistent registry was initialized. Production restore/export/boot buttons
remain unavailable. The first KVM snapshot attempt encountered its inactive
streamer socket; a later active-stream snapshot succeeded. Physical touch,
keyboard/mouse interaction and panel behavior beyond the captured image have
not been tested.

Private evidence under `local/sd-recovery-host/`:

- Serial snapshot `physical-console.raw`: SHA-256
  `9fe3ded752ba879144d77db603e74d6644c9eb8b57c9c14fb859b210370ad797`.
  The receive-only remote collector continues; this hash binds the retained
  snapshot, not an indefinitely growing log.
- Actual KVM frame `physical-hdmi.jpg`: SHA-256
  `f22841cd6e3605c029df57be3facc1f3dd31c21c7e22ab1eef7a6d8e51a5ed8f`.
- MMC/controller/mount inventory `physical-mmc-intake.json`: SHA-256
  `9f2a1c917c50dd02b7a7ce323e84a2fed0832afd479d0cdce8eea699b6828152`.

## Read-only eMMC intake

The MMC card beneath `4022000.mmc` is the installed 31,272,730,624-byte spare,
Linux `/dev/mmcblk0`, device number `179:8`. SD is beneath `4020000.mmc` and is
Linux `/dev/mmcblk2`. This is measured Linux numbering; it does not establish
U-Boot numbering. Raw CID and complete partition/GPT results remain private.
No eMMC partition is persistently mounted.

Both 64 KiB environment records pass CRC checks. The 4 MiB copy has flag 3,
A=3/B=0; the 8 MiB copy has flag 2, A=2/B=0; both select A. These match the prior
H10 observations and were not changed. Read-only GPT inspection passed against
the exact v5 image footprint. Partition five was temporarily mounted in a private
mount namespace with `ro,noload,nodev,nosuid,noexec`, inspected, then unmounted.
It has 154,374,144 bytes free; original `recovery.scr` SHA-256 is
`57e414bec126a309085f3e2be211c6b8fe0e43f5833a5b5609f3e69457808dee`.

The SD userspace has mount/unshare but lacks several live-stager tools, including
`ip`, `dumpimage` and OpenSSL CLI. No package installation was attempted. The
existing trusted RAM writer cannot be invoked directly from this SD root: its
accepted entry requires its authenticated initramfs/NFS boot environment. The
current SD-only loader also disables U-Boot eMMC enumeration. These are the next
integration gaps for H12, not reasons to repeat the SD move.

The host initially reported an April 2026 wall clock. It was corrected from the
trusted coordinator over pinned-key SSH using CLOCK_REALTIME only; no RTC write
was attempted. A later reboot may reset that correction. Clock agreement must
be checked before preparing time-limited signed jobs. The known nonfatal sudo
hostname-resolution warning remains; commands succeed.

Keep this setup connected with PSU off. H12 exact writer artifact, target,
source/claim, boot routing and immediate independent review gates remain open.
This result does not validate A/B execution, automatic eMMC reimage/return,
printer operation, DRAM reliability, touch or a supported release.
