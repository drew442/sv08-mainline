# Upstream CB1 minimal SD comparison

Date: 2026-09-29 UTC. Target profile: `test-sv08-01`, owner-reported host PCB
`H616_JC_6Z_V1.2`. The owner requested the unchanged upstream CB1 image as a
normal-OS boot comparison after the SD/NFS diagnostic intentionally shut down.
This is a troubleshooting baseline, not validated SV08 compatibility or a
project release.

Source: [BIGTREETECH CB1 V2.3.4 release](https://github.com/bigtreetech/CB1/releases/tag/V2.3.4),
accessed 2026-09-29. Exact asset:
[`CB1_Debian11_minimal_kernel5.16_20240319.img.xz`](https://github.com/bigtreetech/CB1/releases/download/V2.3.4/CB1_Debian11_minimal_kernel5.16_20240319.img.xz).

## Artifact and operation

Downloaded directly to Beelink over HTTPS. XZ integrity testing passed.
Measured compressed size: 393,901,476 bytes, SHA-256
`d02eb81bd9fdc610c543a90564f6b53cfc9349e254b46b6b4634579800e728cd`.
Expanded size: 2,193,620,992 bytes, SHA-256
`e1a38f3d30f1d9b4ed7e785923b77469c1a6dd70531f2e8aa6c0c6a3579a4895`.
These are measured hashes, not publisher signatures or compatibility evidence.

The owner returned the same SanDisk `SC16G` card to Beelink. Its measured
capacity is 15,931,539,456 bytes; stable-link, CID, block identity, mounts,
holders, swap and users are checked again immediately before the exclusive
write. Beelink's system disk remains separate. A GPT-6 Sol/medium reviewer
returned PASS WITH CONDITIONS for the SD write only.

The unchanged image has an MBR, FAT16 partition at sectors 8192–532479 and
Linux partition at sectors 532480–4284415. No project configuration, network
credentials, SSH keys or HDMI settings are inserted. Only the expanded image
prefix is written; the remaining card tail is preserved. Private admission,
write and readback evidence are retained at
`/home/drew/sv08-captures/cb1-v234-20260929/card-write.json` on Beelink.
The exclusive write, `fsync` and buffer flush completed, followed by full
direct-I/O readback of all 2,193,620,992 bytes matching the expanded hash above.
Read-only `fsck.vfat -n` and `e2fsck -fn` passed. The written MBR geometry
matches the source, and both partitions remain unmounted on Beelink.

## Boot behavior and limits

Read-only inspection found the image uses the CB1 SD device tree,
`sun50i-h616-biqu-sd`, kernel 5.16.17 and `console=display`. The boot and root
filesystems are selected by UUID. The normal first-boot filesystem resize
service derives the root partition and its parent from the mounted root.
The boot scripts configure the upstream user/network/display settings and
toggle GPIO 229 as a power LED; that pin's SV08 electrical function has not
been measured. No Klipper service was found in the enabled system service links.
This inspection is bounded and is not proof that all third-party behavior is
safe on SV08 hardware.

Fresh receive-only capture service `sv08-cb1-capture` is armed on Beelink before
USB reconnection; private logs are under the same directory's `serial/`.
Although the unchanged image selects display console, its boot script supplies
both `console=ttyS0,115200` and `console=tty1`. HDMI/KVM and wired DHCP
observations are also needed. No physical boot of this baseline has been
validated yet.

Keep the printer PSU off for this host-only comparison. Before inserting SD,
disconnect USB serial as well to remove host back-power. Keep the factory eMMC
stored. Do not run the upstream eMMC installer or printer commands. The earlier
[replacement-card capture](host-sd-replacement-20260928.md) already proves
successful bounded project SD/NFS boot and intentional shutdown.

## Independent boot review and physical handoff

The initial Sol/medium review declined boot with the spare eMMC retained because
root UUID ambiguity could precede automatic resize and the GPIO function was
unknown. A separate GPT-6 Sol/high follow-up returned PASS WITH CONDITIONS for
one host-only test **with the spare eMMC removed**. Bounded source comparison
found the vendor DT describes PH5 as a disabled status LED and a prior diagnostic
Linux DT inherits PH5 heartbeat. This supports software intent only; PH5's
electrical function remains unmeasured. The review accepts that uncertainty for
this owner-requested supervised comparison, not for commissioning or release.

The single owner action is to disconnect all printer power, including USB
back-power, remove and safely store the spare eMMC, and install this SD while
leaving both eMMC modules out. Connect Ethernet, keep the PSU off, and reconnect
USB serial only after capture readiness is confirmed. This excludes first-boot
resize writing either retained eMMC. Stop on unexpected behavior, abnormal
heating, odor or repeated resets; remove power and retain capture before any
further attempt. Do not invoke installers, MCU commands, heaters or motion.
