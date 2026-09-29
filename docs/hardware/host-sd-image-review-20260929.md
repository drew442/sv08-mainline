# Review of the apparently failed project SD boot

Date: 2026-09-29 UTC. Profile: `test-sv08-01`, owner-reported host PCB
`H616_JC_6Z_V1.2`. The owner reports that the upstream CB1 minimal SD image
boots visibly and requested investigation of the latest project SD image.
This is owner-observed baseline behavior; the CB1 receive-only capture file
was empty at inspection, so no Linux serial result is inferred from it.

## Finding

No regression in the delivered SD boot bytes was identified. The project
artifact was the **finite SD/NFS diagnostic**, not a normal host or recovery
OS. It boots Linux, runs a small C program as PID1, emits its checks on serial,
and intentionally powers down. It has no normal login, HDMI desktop, recovery
interface or SSH daemon. Leaving its PID1 running would not add those services.
The coordinator supplied an artifact whose behavior did not match the owner's
expectation of a visibly running system.

The [replacement-card capture](host-sd-replacement-20260928.md) contains two
successful Linux/NFS/read-only-eMMC sequences followed by `reboot: Power down`.
This proves bounded diagnostic boot, not a working interactive OS. The card
does not need another identical diagnostic write to establish that result.

## Exact-artifact and change review

The delivered image remains 201,326,592 bytes, SHA-256
`cea51e9c0731c664563bf16a54fef585f1609ef90da03358eefd4d077b7aab28`.
This matches the [successful H10 v3 artifact](host-sd-network-emmc-probe-20260926.md)
and its [original write receipt](host-sd-network-emmc-probe-card-write-20260926.md).
Local loader, boot script, kernel, initramfs and DTB size/hash checks against
the retained composition receipt all passed. The copy retained on Beelink has
the same whole-image hash. Beelink still serves the exact tested diagnostic init
at SHA-256
`1e7afa9aaf337ccffdb4c7431648f7aba934dcc600b04e11751743e345e1dc11`.

Changes since the successful H10 build include shared eMMC discovery code and
an explicit, separate trusted writer composition option. Source inspection
shows the default diagnostic boot arguments still select `/sd-network-init`;
the trusted writer option is not present in this delivered artifact. Today's
source differs from the retained composition's source hash, so source HEAD
must not be presented as the exact origin of the older binary. These source
changes did not alter the already-built image written on September 28.

A separate GPT-6 Sol/medium review independently confirmed the artifact
selection mismatch. Offline `test_sd_network_image.py` (six tests) and
`test_sd_network_env_probe.py` (four tests) passed. These tests do not validate
normal userspace or display output. The temporary NFS service outage after
Beelink's reboot was real, but was repaired before the captured successful
replacement-card boots; it does not explain their intentional final shutdown.

## Required correction

Use a separately named **SD host-test/recovery image** with complete userspace,
normal init, authenticated remote access and visible recovery/display
acceptance. Keep the bounded diagnostic unchanged and clearly identified.
Reuse existing project host/recovery assembly where possible. Validate the
selected root, volatile/persistent mounts, printer-service isolation and
absence of automatic eMMC or boot-policy writes before physical use. Do not
describe a bootloader/kernel probe as this complete system.

The owner has returned the SanDisk card to Beelink. Its partitions reflect the
CB1 baseline's first-boot root expansion. This is SD state, not evidence that
either retained eMMC changed. No replacement write was performed during this
review; the baseline remains available until the actual replacement is ready.
