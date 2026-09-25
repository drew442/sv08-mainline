# Disposable SD/NFS prototype media write

Date: 2026-09-25. Hardware profile: `test-sv08-01`; the board marking
`H616_JC_6Z_V1.2` is owner-reported. The owner stated that the SD card's prior
contents were unimportant and may be erased. This operation wrote the disposable
SD card in Beelink's USB reader; it did not write the printer eMMC or MCU.

## Reviewed artifact and media

The physical-address image was composed with Beelink's current address
`192.168.1.136` and export path `/srv/sv08-sd-nfs`. Its exact SHA-256 is
`11226b0e6c6f9e2c1e9642e3026d2505446acf23f3a5fd7d397eb89896bf6a2d`, with a
length of 201,326,592 bytes (192 MiB). An independent artifact inspection
verified its GPT, SPL placement, partition bounds, direct payload readbacks,
hash-checked U-Boot commands, and absence of eMMC environment/counter access.
The separate high-consequence review returned PASS WITH CONDITIONS for writing
only this image-sized prefix.

Immediately before writing, Beelink identified `/dev/mmcblk0` as the unmounted
2 GB `SU02G` SD card, capacity 1,977,614,336 bytes. Its CID, serial, and USB
reader path are retained in ignored local evidence rather than published here.
The transferred image under `/tmp` was rehashed and matched the reviewed
SHA-256. The write command used 48 blocks of 4 MiB, `conv=fsync,notrunc`,
starting at byte zero. This writes exactly 201,326,592 bytes; the remaining
card tail was not overwritten or sanitized.

After flushing, a direct read of the same 192 MiB prefix produced SHA-256
`11226b0e6c6f9e2c1e9642e3026d2505446acf23f3a5fd7d397eb89896bf6a2d`, matching
the source image. The resulting partition 1 is the expected 128 MiB FAT boot
partition. The private target-identity, write, and readback transcript is in
ignored `local/sd-network-physical-20260925/`.

## Not yet physically tested

The SD has not been inserted in the printer and no boot was attempted. The
printer still runs its v5 eMMC A image; the separate
[A-attempt re-arm record](host-board-image-20260925-v5-a-rearm.md) documents
its reviewed counter update and confirms that no reboot occurred. SD priority,
printer Ethernet/NFS path, eMMC isolation and fallback remain unverified. The
temporary sanitized export at `/srv/sv08-sd-nfs` is configured for NFSv3 with
read-only and root-squash options. A Beelink-local NFSv3/TCP client mounted it
read-only, confirmed the init hash
`e344e547f7a0a55ec1e273eb0ba49adaa961b0ffcb2dd0999f93e452463cb918`, and a
write probe failed with `Read-only file system`. This validates the local
server/export path only, not printer reachability. Beelink currently has
`192.168.1.136` at MAC `84:39:be:9e:10:d9`; the image hardcodes `.136`, so the
owner must reserve that address before a physical test. Receive-only UART
capture is active and must be confirmed ready before serial reconnection.
