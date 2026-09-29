# Managed SD loader transfer and failed return probe

2026-09-29, test-sv08-01; owner-reported host PCB H616_JC_6Z_V1.2.
This records a successful loader transfer followed by a failed coordinator
probe. It does not establish unattended eMMC replacement or normal printing.

The [approved route](host-managed-boot-route.md) passed independent offline
verification, including the corrected capture-before-transmission behavior.
A separate Sol reviewer accepted only the SD transfer with conditions. Fresh
read-only admission identified the installed SanDisk SD on controller
`4020000.mmc`, device `179:0`, capacity 15,931,539,456 bytes. Its root was
kernel-readonly and mounted `ro,norecovery`; boot was unmounted.

One 786,225-byte loader write at byte 8192 passed flush and exact readback.
Loader SHA-256:
`350a941a7ec67b541308d235bffa4b937b8171f683f3e96b0c51dd32fab64544`.
All seven streaming preservation hashes matched before and after: protective
MBR, both GPT headers/arrays, full FAT partition and full root partition.
The complete overwrite preimage and original SD composition remain private.
No eMMC, FAT, MCU or deliberate environment write was performed by this transfer.

A separate Sol/high reviewer accepted one warm reboot subject to confirmed
controller readiness. The coordinator supplied the bridge's `/dev/serial/by-id`
symlink, but the controller deliberately uses `O_NOFOLLOW` and refused it with
`ELOOP` before transmitting. The readiness check failed; the coordinator
incorrectly continued with the SSH reboot. That was an orchestration error.
The attempted receive-only collector restart also failed because stopping its
transient systemd unit had removed the unit. The same collector was subsequently
recreated and resumed receiving.

The retained late console trace shows Linux reaching the original
`sv08-recovery.target` and starting its recovery display. It does not show the
intended SD-host return or the complete U-Boot transition. Original recovery
does not provide the SD host's SSH/network services. The current redundant
environment values and warm RTC retention therefore remain unmeasured;
do not infer preservation from the earlier values or issue another blind reboot.
The original script's inherited reset paths can also consume normal boot
attempts. No job, claim or writer marker was armed for this probe.

Before another reviewed probe, bind the concrete `/dev/ttyUSB0` character
device to its measured topology, require a live exclusive controller and durable
fresh capture before resetting, and recreate the transient receive-only unit on
controller exit. Resolve current environment visibility and review the exact
recovery action first. No additional SD or eMMC writer move has been requested.

Private evidence under `local/sd-recovery-host/` includes
`managed-sd-readonly-inspection.json`, `managed-sd-deployed-hashes-space.txt`,
`managed-sd-transfer-review.json`, `managed-sd-transfer-result.json`,
`managed-sd-transfer-stderr.txt`, `managed-preboot-environments.json`,
`managed-warm-return-review.json` and `managed-after-warm-console.raw`.
The successful transfer result SHA-256 is
`0ec555ced4263f725bf28f09d338a6b684b1aba199b83ad2b269c103b0f0803c`.
Sources are the pinned build inputs, independent reviews and named measured
captures, accessed 2026-09-29. Private identifiers and raw storage remain ignored.
