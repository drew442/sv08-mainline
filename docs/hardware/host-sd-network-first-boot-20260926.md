# Corrected SD/NFS diagnostic boot

Date: 2026-09-26 UTC. Hardware profile: `test-sv08-01`. The board marking
`H616_JC_6Z_V1.2` remains owner-reported; this test makes no new board-revision
claim.

## Result

The corrected SD image booted through Linux and mounted the Beelink NFS root.
The exact reviewed artifact was 201,326,592 bytes, SHA-256
`53cc0b2696add39dae24480167d79807e72a15f824fbc9025aaf20a9aa63d08a`. It had
been written to the identified, unmounted `SU02G` SD card, and the full image
prefix passed direct-I/O readback before installation. The factory eMMC was
not moved or written.

The receive-only serial trace showed U-Boot model
`Sovol SV08 test-sv08-01 SD network diagnostic`, then Linux
`6.18.51-sv08-candidate1`. The corrected `hash -v` path passed far enough to
start the kernel. Linux detected Ethernet link at 100 Mbps full duplex and
received DHCP on wired `eth0` using MAC `02:00:b2:76:83:5a`, address
`192.168.1.141`, and hostname `sv08`. This resolves the earlier DHCP
observation: the `f2:a8:…` address was the known Wi-Fi MAC; the wired interface
used the reserved address.

The initramfs mounted the root from Beelink `192.168.1.136`; the probe emitted
the exact pass marker:

```text
SV08_SD_NFS_PASS root_ro=1 data_tmpfs=1 dhcp_address=1
```

Beelink's wired-interface capture also observed NFS replies from
`192.168.1.136:2049` to the printer, with 79 packets captured and none dropped
by the capture kernel. The diagnostic then ended with `reboot: Power down`, as
designed. No host user space or printer workload was started.

The receive-only serial trace contains 28,123 bytes, SHA-256
`3594c7586321e0f9644cfa0eb10f9a9d93bdfecff3b124f0ec6d38d1ff1dc155`. The raw
trace, serial events, media readback, write receipt and structured result are
private on Beelink under `/home/drew/sv08-captures/sd-network-20260925/`.
No serial input was sent.

## Scope and remaining limits

This proves the board can start the SD-resident loader, kernel and initramfs,
then run a Linux root filesystem over the network without writing the eMMC.
The tested U-Boot has no Ethernet driver, so loader, kernel and initramfs
updates still require updating the SD card. The NFS export is read-only; this
trial changed no files on it. A future network-capable U-Boot would be needed
for a fully network-loaded kernel.

The card is larger than the bounded 192 MiB image. Linux reported that the GPT
backup header is at the image boundary rather than the physical end of the SD
card. That warning is expected from the reviewed prefix-only image; boot and
the NFS probe succeeded, and no GPT repair or write beyond the image prefix was
attempted.

This test did not assess visible HDMI output, persistent root filesystems,
eMMC boot-counter state or eMMC isolation under every boot path. It did not
test MCU firmware, printer control, motion or heaters. Do not infer that the A
counter still has three attempts; inspect it before any future boot that may
select eMMC.

See the [image and media record](host-sd-network-card-write-20260925.md) and
[H09 coordination record](coordinated-human-tasks.md).
