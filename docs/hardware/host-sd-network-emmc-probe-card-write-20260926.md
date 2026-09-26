# H10 disposable SD image write receipt

Date: 2026-09-26 UTC. Profile: `test-sv08-01`. This writes only the disposable
SU02G SD card; it does not write the printer eMMC or MCU. The printer was
reported powered off and USB serial disconnected during the write.

## Target and reviewed artifact

Beelink identified `/dev/mmcblk0`, stable link
`/dev/disk/by-id/mmc-SU02G_0x716f216e`, as the 1,977,614,336-byte SU02G card
(serial `0x716f216e`). The card and its partition had no mountpoint before the
write. The exact reviewed image was 201,326,592 bytes with SHA-256
`cea51e9c0731c664563bf16a54fef585f1609ef90da03358eefd4d077b7aab28`.
The high-consequence review returned PASS WITH CONDITIONS for one supervised
boot after exact direct-I/O readback, spare-eMMC reinstallation while powered
off, receive-only capture before power, and the listed stop conditions.

The image was transferred to Beelink and its hash verified before writing. The
write used `dd` with 48 × 4 MiB blocks, `oflag=direct,conv=fsync,notrunc`, at
byte zero, followed by `blockdev --flushbufs`. A direct-I/O read of the same
192 MiB prefix returned SHA-256
`cea51e9c0731c664563bf16a54fef585f1609ef90da03358eefd4d077b7aab28`, matching
the reviewed artifact. The remaining card tail was not overwritten or
sanitized. The private target/CID and command transcript are retained in
`local/sd-network-emmc-probe-20260926/card-write.json`.

The source image passes `sgdisk --verify` with no GPT errors (it reports the
intentional gap before the primary partition table), and the written FAT partition passes
`fsck.vfat -n`. Because this fixed 192 MiB image is written to a larger 2 GB
card without changing reviewed bytes, the secondary GPT header remains at the
image boundary instead of the physical card end. `sgdisk --verify` on the whole
card reports that expected geometry warning; no repair or image-tail write was
made. U-Boot loads the reviewed first partition, and exact readback confirms the
written image prefix. The card remains unmounted on Beelink.

## Next physical action

With the printer fully powered off and USB serial still disconnected, reinstall
the spare eMMC and this SD card, keeping the factory eMMC stored. Stand the
printer upright and reconnect Ethernet. Do not reconnect USB serial yet; the
coordinator must first arm and confirm receive-only capture because that cable
powers the host. Then permit one supervised boot only. See the
[H10 task and stop conditions](coordinated-human-tasks.md).
