# Running SD recovery host: prepared card, 2026-09-29

The SanDisk SC16G card in Beelink has the reviewed running recovery host image.
Complete prefix readback and read-only filesystem checks passed. The later [physical boot record](host-sd-recovery-host-first-boot-20260929.md)
confirms GTK, native HDMI and SSH; touch remains pending under
[H13](coordinated-human-tasks.md). This is a nondeployable host test, not a printing
system or a release.

## Evidence

The [offline delivery](host-sd-recovery-host.md) passed independent feature
verification at `d49351ee743d4f579d4a1401a8eece240b34df42`: normal systemd,
GTK keyboard interaction, SSH/sudo, refused authentication, protected root,
volatile runtime, fresh boots, disconnected-network GUI and three admission
refusals. Physical H616 kernel/DT bytes are unchanged from the successful H10
input; VM evidence uses the separately identified Debian kernel.

The exact owner-only image is 738,197,504 bytes, SHA-256
`2b0a6fa177515652722b53c0a7f306c3fb452c84b1af1ffa4dc01ab5c8ed0040`.
Its 512 MiB recovery root excludes the synthetic authorized test key. Freshly
compiled loader SHA-256:
`4def569998f4315d78687450276f9c1499b9d9b1eed03015044bf4177f8603e3`.
The loader receipt binds exact script/environment/configuration, source pins,
patches, toolchain and retained BL31 input.

Separate GPT-6 Sol/medium high-consequence review returned PASS WITH CONDITIONS
before the write. The exclusive target FD was bound to the SD identity and
15,931,539,456-byte capacity; factory/spare eMMC and Beelink's system disk were
not write targets. At 03:36:33 UTC the full 738,197,504-byte direct readback matched
the image hash. No bytes beyond the image prefix were written, and no resize or
repair was performed. Private write receipt SHA-256:
`4d398972a8bab82bf6b8645447dd4ab7c5a80092d3bf8688b706219b295b6179`.

Read-only FAT and ext4 checks exited zero. Partition 1 is 128 MiB at sector
32768; partition 2 is 512 MiB at sector 294912, PARTUUID
`deaf981d-7441-428c-bf43-ce40bca6ca65`, filesystem UUID
`27ea34a6-fb05-4814-aaee-251071577ae1`. GPT inspection reported its expected
backup header at the image end rather than the 16 GB card end, plus deliberate
metadata/table gaps for the SPL layout. No GPT adjustment was made.
Private filesystem/layout receipt SHA-256:
`cbbc513d22644b8760aea71f80405f727f7f8c4491085de59efed6e1d723cb26`.

The one-off writer's flat `lsblk` JSON parsing checked only the whole device
programmatically. Manual pre-write checks and fresh explicit post-write checks
of the disk and both partitions are separate evidence: unmounted, no holders,
users or device swaps. They do not prove correct automatic child enumeration.
The executed helper is retained at its reviewed hash; its working copy now
requests `lsblk --tree` and requires a new review before any future write.
The same independent reviewer reassessed the receipts and returned PASS WITH
CONDITIONS for boot; no repeat write is warranted.

Receipts, collector and reviews remain ignored under
`local/sd-recovery-host/`, with remote originals under
`/home/drew/sv08-sd-recovery-build/`. The verified compressed upstream CB1
baseline remains on Beelink as a disposable-SD fallback; factory eMMC is stored.

## Single pending physical action

Receive-only service `sv08-sd-recovery-capture` is active on Beelink, waiting for
the onboard USB serial device. The reviewed collector sends no console bytes,
uses 115200 8N1 without HUPCL, and bounds capture to 12 hours/50 MiB. Collector
SHA-256: `5c4e6cd4f1e8039949c83654c1265ffad51c269230268ca445e4491d7bf2b0ed`.
If the session is delayed beyond that window, re-arm capture before connecting.

1. Remove printer PSU power and disconnect USB serial, which back-powers the host.
2. Move only the prepared SanDisk SD from Beelink into the printer. Keep factory
   eMMC stored; no spare eMMC move is needed. Record whether the spare is installed.
3. Connect Ethernet, leave PSU off, and reconnect USB serial after capture is
   confirmed waiting. This powers the Linux host for the test.

The coordinator then checks trusted console SSH fingerprint, normal init,
continued GTK interface, wired DHCP, key-only `recovery` login, mounts/services
and idle operation. Missing persistent state is expected and must not be repaired
or initialized automatically. Do not select media or printer operations. Remove
USB power and stop if unexpected boot/activity occurs. No eMMC/MCU write,
boot-policy change, heater or motion action is part of this test.
