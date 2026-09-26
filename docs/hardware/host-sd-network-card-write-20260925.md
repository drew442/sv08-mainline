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

## Physical result

The owner later inserted this card into the printer. The [first-boot record](host-sd-network-first-boot-20260925.md)
shows two SD-loader starts and a fail-closed U-Boot script stop before Linux.
The printer's Ethernet/NFS path, eMMC isolation and fallback remain unverified. The
temporary sanitized export at `/srv/sv08-sd-nfs` is configured for NFSv3 with
read-only and root-squash options. A Beelink-local NFSv3/TCP client mounted it
read-only, confirmed the init hash
`e344e547f7a0a55ec1e273eb0ba49adaa961b0ffcb2dd0999f93e452463cb918`, and a
write probe failed with `Read-only file system`. This validates the local
server/export path only, not printer reachability. Beelink currently has
`192.168.1.136` at MAC `84:39:be:9e:10:d9`; the image hardcodes `.136`, so the
owner must reserve that address before a physical test. Receive-only UART
capture is active and must be confirmed ready before serial reconnection.

## Corrected retry candidate

The first physical attempt reached SD U-Boot but failed before Linux because
the `hash -v` command was missing from the compiled configuration. The
corrected, cleanly rebuilt v2 image is 201,326,592 bytes with SHA-256
`53cc0b2696add39dae24480167d79807e72a15f824fbc9025aaf20a9aa63d08a`. Its
matching ignored receipt is
`local/sd-network-physical-20260925/composition-v2.json`. An independent
high-consequence review returned **GO WITH CONDITIONS** for that exact hash.
Before writing, freshly identify the unmounted SU02G card by CID, capacity and
reader path, transfer and verify the exact image hash, write only the first
192 MiB, flush, and read back that prefix directly to the same hash. Keep the
factory eMMC stored. Do not extend or sanitize the remainder of the SD card.

For the one retry, verify Beelink's `.136` reservation and the read-only export,
fully isolate printer power (including USB-serial back-power) during the card
move, and arm receive-only UART before reconnecting serial. Send no serial
input. The eMMC A boot counter is unknown after the two prior SD-loader starts;
do not infer that it remains at three. Stop after this single attempt or at any
repeated reset, eMMC/RAUC selection, hash/NFS failure or printer output. Inspect
the counter before considering another boot. The actual Linux Ethernet/DHCP/NFS
path has not yet been proven.
