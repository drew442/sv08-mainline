# Replacement SanDisk SD preparation

Date: 2026-09-28 UTC. Profile: `test-sv08-01`, owner-reported host PCB
`H616_JC_6Z_V1.2`. The owner reported possible failure of the old SD and explicitly
requested writing a new 16 GB SanDisk card for another boot attempt. This renews
one supervised diagnostic boot for investigating the boot/network stall and
supersedes the earlier H10 “no more boot planned” dispatch. It does not authorize
eMMC/MCU writes, boot-policy changes, heater or motion operations.

## Media write evidence

Beelink measured the replacement as an SD card named `SC16G`, with capacity
15,931,539,456 bytes. Its stable by-id link resolved to `/dev/mmcblk0`; the
Beelink system disk is separate (`/dev/sda`). Before writing, the card and its
partition were unmounted, with no users, holders or swap. Private CID and target
admission evidence are retained on Beelink in
`/home/drew/sv08-captures/new-sd-20260928/card-write.json`.

A separate GPT-6 Sol/medium high-consequence reviewer returned PASS WITH
CONDITIONS for this write and one bounded boot. The exact previously tested
[H10 v3 image](host-sd-network-emmc-probe-20260926.md) was reused without rebuilding:
201,326,592 bytes, SHA-256
`cea51e9c0731c664563bf16a54fef585f1609ef90da03358eefd4d077b7aab28`.
Its hash was checked before and after transfer to Beelink.

The write opened the resolved block node exclusively with `O_NOFOLLOW`, bound
its device number and capacity, and rechecked the stable link and sysfs identity.
It wrote exactly the 192 MiB prefix, called `fsync`, and flushed block buffers.
Full direct-I/O readback of that prefix matched the image hash. `fsck.vfat -n`
passed (five files). The card tail was preserved. No GPT relocation, filesystem
resize or repair was performed; the fixed image's backup GPT remains at the
image boundary rather than the larger physical card end.

## Network root and capture

Beelink's reboot had removed the temporary extracted NFS server binaries and
service setup. Ubuntu packages `nfs-kernel-server` and `nfs-common`
`1:2.6.4-3ubuntu5.1`, plus `rpcbind` `1.2.6-7ubuntu2`, were installed instead.
Persistent configuration is in `/etc/exports.d/sv08.exports` and
`/etc/nfs.conf.d/sv08.conf`; mountd uses port 20048. The diagnostic export
`/srv/sv08-sd-nfs` is read-only with root-squash, restricted to Beelink
`192.168.1.136` and printer `192.168.1.141`.

A default NFSv3/TCP local mount succeeded without an explicit mountd port,
returned the exact tested init hash
`1e7afa9aaf337ccffdb4c7431648f7aba934dcc600b04e11751743e345e1dc11`,
and refused a write with `Read-only file system`. The retained composition
manifest matches SHA-256
`47928b1378278af64a307effe6c35d2ffe54d5b187172f23a4d0e77e5b131007`.
The reviewer noted that today's init source differs from its composition source
receipt; this retry serves the exact tested binary and makes no new rebuild
provenance claim.

Receive-only 115200 8N1 serial capture was armed before admitting the printer
to the export. Service `sv08-new-sd-capture` waits through USB disconnect and
reconnection, checks the onboard USB serial identity, and transmits no input.
Private events and `console.raw` are in the capture directory above. It runs for
up to 12 hours with a 50 MiB console limit; recheck it before any delayed boot.

## Owner handoff and acceptance

Fully power off the printer and disconnect USB serial, which back-powers the
host. Move only the new SD from Beelink into the printer. Keep the spare eMMC
installed and factory eMMC stored. Keep Ethernet connected. Once capture is
confirmed ready, reconnect USB serial for one diagnostic boot.

Observe SD loader, Linux, wired DHCP, NFS mount, separate diagnostic and bounded
eMMC-read markers, then intentional power-down. This image is a diagnostic,
not an interactive host: HDMI output or SSH availability is not its acceptance
criterion. Physical boot results on the replacement card remain pending.
On unexpected boot, errors, hang or missing shutdown, stop and remove all power;
do not retry automatically. H12 writerless reimage validation remains separate.
