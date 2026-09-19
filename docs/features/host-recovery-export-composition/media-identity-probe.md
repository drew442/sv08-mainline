# Recovery composition: measured virtual media identities

Date: 2026-09-18. Offline ARM64 QEMU only; no physical printer evidence.
This is transport discovery for the approved export composition, not acceptance
of the final provider, filesystem geometry, source preservation or GTK journey.

The coordinator reconstructed the baseline from all 284 locked recovery archives.
The archive-lock hash matches the previous independent-image receipt. Current
source includes subsequent reviewed board and image-job changes, so the rebuilt
root is deliberately not claimed identical to that receipt: schema-2 inventory
`167b9d6bfde5aadf3af2efa70d664c0110fa785f55076b477248f6268ca2cf57`,
17,765 regular paths and 788,007,169 regular-path bytes. The old final image is not
present. New composition must record its own complete input and output hashes.

A disposable initramfs used the selected recovery kernel
`6.12.107+deb13-arm64`, its real module dependency closure and BusyBox to enumerate
kernel sysfs. QEMU used `virt`, Cortex-A53, two CPUs, 256 MiB RAM, no network, no
host sharing, and four sparse 64 MiB regular files with GPT partitions. No source
filesystem was mounted in this probe. Modules included virtio block/SCSI, SD,
xHCI, USB storage and UAS. The guest completed enumeration and powered down.

| Role | QEMU device properties | Actual selected-guest observation |
| --- | --- | --- |
| Recovery | `virtio-blk-pci,serial=SV08-RECOVERY` | Top-level block `serial` contains `SV08-RECOVERY` without a trailing newline; transport is virtio |
| Source | `scsi-hd,wwn=0x5000000000000001` on virtio SCSI | `device/wwid` is `naa.5000000000000001`; removable is 0 |
| Additional protected | `scsi-hd,wwn=0x5000000000000002` on virtio SCSI | `device/wwid` is `naa.5000000000000002`; removable is 0 |
| Destination | `usb-uas` with `scsi-hd,wwn=0x5000000000000003,removable=on` | USB SCSI ancestry, `device/wwid` is `naa.5000000000000003`; removable is 1 |

Each disk reported a distinct positive disk sequence and a real kernel block
node; each partition reported start 2048 and length 98,304 sectors. Holders/slaves
were empty where present. Device letters varied and are not policy identities.
The final integration fixture must independently bind its filesystem/partition
UUIDs, full geometry and complete unmounted topology; these discovery sizes are
not an approved final media policy.

An earlier real probe demonstrated why serial-only SCSI was not used: its
`device/wwid` read returned EINVAL, and `usb-storage` returned ENXIO. VPD bytes
were visible on SCSI but do not justify a new unreviewed parser. The chosen WWN
and UAS setup supplies ordinary kernel WWIDs. Missing or unreadable identities
must remain refusal conditions, not trigger a generic virtual-device exemption.

Ignored evidence: `build/recovery-composition-evidence-20260918/probe-v3.log`
and `build/recovery-composition-sysfs-v3-20260918/{command,modules}.json`.
The discovery generator is retained beside the log; reproducible final
composition belongs to the tracked integration harness rather than this probe.

- `probe_guest.py` SHA-256: `6fb645e79da9ca63c8c532370e645d8a0f179c85dfa6c467d6250210e2b1c255`
- `probe-v3.log` SHA-256: `f5cb690c9dee843dda136d9ffe47ecc9be19e63155c6d9b2cbe905c5f78684e4`
