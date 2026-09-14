# First diagnostic A boot on test-sv08-01

2026-09-13. The owner reinstalled the spare and reported power-on after the
[instrumented SPL write](host-spl-diagnostics.md). This attempt completed DRAM
initialization, selected slot A, and reached Debian over wired SSH. It is one
successful diagnostic boot, not proof of reliable startup or a fixed DRAM cause.
PCB revision and independently observed cold electrical isolation remain unknown.

## Measured result

The receive-only console capture began receiving at 07:15:25 UTC. Its initial
bytes are garbled; the readable portion shows successful training, 1024 MiB DRAM,
TF-A 2.12.9, U-Boot 2026.07, the redundant MMC environment and slot A. Linux
6.18.51-sv08-candidate1 starts with the exact root-A PARTUUID. The logger did not
capture a complete readable SPL entry sequence on this attempt.

SSH host-key verification matched the image's private seeded identity. The host
reported release `0.1.0-board.1`, immutable mode, root-A and boot-A mounted
read-only, and the exact persistent data partition mounted read-write. The first
state generation was created successfully and the administration status helper
returned success. Both environment copies have valid CRCs; the newer copy has
`BOOT_A_LEFT=2`, `BOOT_B_LEFT=0`, `BOOT_ORDER=A`. No health confirmation or attempt
budget refresh was issued. Runtime `trial=false` describes the initial state
registry; it does not mean U-Boot's attempt budget is unlimited or marked good.

Linux enumerates eMMC as **mmcblk0** with this loader, unlike mmcblk2 on the prior
vendor-loader trials. PARTUUID-based mounts resolved correctly. Never reuse the
old numeric device path for writes or raw environment access.

The HDMI DRM controller reports an active 1024×600/60 Hz framebuffer console and
a connected display. Visual appearance and physical touch input still require
owner observation. Both previously identified Klipper USB MCUs enumerate;
all five printer-service names remain masked. No heat or motion was requested.
Host thermal zones were approximately 43°C, with about 882 MiB memory available
at the initial idle sample. These are short observations, not load/stability tests.

The administration HTTPS page returned 200, its certificate fingerprint matched
the private seed, and the prepared account authenticated through Cockpit's login
endpoint. This proves actual LAN/TLS/login, not all graphical actions or completed
production account provisioning. Private address/credentials remain local.

The MGS1 USB camera is now `/dev/video1`; `/dev/video0` is the Cedrus codec. An
initial codec-target format request was rejected. After reading actual device
identity/formats, 30 camera MJPEG frames at 640×480 were captured and all decoded
with PyMuPDF 1.28.2. Images remain private. Do not assume video numbering across
bootloader/kernel combinations.

## Integration findings

- Debian's daily `dpkg-db-backup` job was the only failed unit: `/var/backups` is
  read-only in immutable mode. The package database is frozen in that mode.
  An upstream systemd [writeability condition](../../configs/host-os/systemd/dpkg-db-backup.service.d/20-sv08-readonly.conf)
  now skips that job only when its destination is read-only; writable mode keeps
  Debian's existing command and timer. The [image integrator](../../scripts/integrate_host_os.py)
  installs the drop-in. An isolated actual-staging fixture preserved the vendor
  unit, and physical condition checks covered read-only `/var/backups` and writable
  `/run`. A temporary `/run/systemd/system` drop-in on the printer produced a
  condition skip and zero failed units with root still read-only. This live test
  **does not persist across reboot**; the installed image has not been rewritten.
- The radio module loads, but `wpa_supplicant.service` is absent. NetworkManager
  cannot create the supplicant interface. The next pinned host baseline now adds
  `wpasupplicant` and `locales`, with deterministic `C.UTF-8` defaults; the
  currently installed image is unchanged and Wi-Fi association remains open.
- SSH PAM logs a missing `/etc/default/locale`; generate the selected locale
  defaults during image finalization. Login succeeds, but the packaging warning
  remains outstanding.
- The diagnostic shared-wait messages in the installed image use `%p`, unsupported
  by the selected SPL tiny formatter. Those labels are shifted and must not be
  treated as valid measurements. The source patch now uses the supported `%08lx`
  form with an explicit cast and the native test checks both changed helpers;
  a fresh artifact is required before using those labels on hardware. This does
  not invalidate later U-Boot/Linux boot evidence.

The added serial output changes timing, and this successful attempt therefore
does not establish the cause of the previous stop. Repeat captured boots and
memory testing remain necessary. Physical B, independent recovery, rollback,
Wi-Fi association and printing remain unvalidated.

Raw console, mount/service/environment records, web-login checks, camera output
and independent dpkg-fix review are under ignored
`local/feature-workflow/spl-diagnostic/`. Source evidence is the exact pinned
U-Boot `lib/tiny-printf.c` and compiled SPL configuration, the installed Debian
`dpkg-db-backup.service`, and named-board measurements, read 2026-09-13.

## Captured warm reboot

A subsequent controlled warm reboot completed DRAM initialization and returned
to SSH in slot A with a different kernel boot ID and the same persistent state
generation. The readable full SPL sequence reports one rank, 32-bit width,
10 column bits and 15 row bits before the 1024 MiB result. This is autodetection
output, not a PCB/chip-marking identification. The two successful diagnostic
boots do not prove cold-start reliability or identify the earlier failure.

On this warm boot eMMC enumerated as **mmcblk2**, while the first boot used
mmcblk0; PARTUUID mounts remained correct. A read-only inspection helper refused
its stale numeric-device assertion, then was corrected to derive the parent
from the exact root PARTUUID and check partition number/capacity. No write used
that stale path. Numeric MMC enumeration must not be part of the deployment
contract.

Both raw environment CRCs remain valid. The newer copy now has one A attempt
remaining, with B still at zero; no counters were refreshed or marked healthy.
The temporary dpkg condition was re-applied under `/run` after reboot, and the
host again has zero failed systemd units. CPU temperature was about 46°C.
Do not spend the remaining attempt on unrecorded exploratory reboots; select
and review the next B/recovery or boot-diagnostic operation explicitly.

## Recovery rearm preparation

The subsequent diagnostic boots exhausted the A attempt budget and selected the
independent recovery image. The normal A boot has already demonstrated the
first-boot state initializer and LAN services; recovery intentionally does not
create persistent state. `scripts/prepare_boot_rearm.py` builds a separate,
inspect-only-by-default pairable 128 KiB U-Boot environment that restores only
the reviewed diagnostic policy: `BOOT_ORDER=A`, `BOOT_A_LEFT=3`, and
`BOOT_B_LEFT=0`. A later target-specific writer must verify the identified eMMC,
the two current environment copies, and full readback before writing either
offset `0x400000` or `0x800000`.

On 2026-09-14, the identified spare module was connected through the recorded
USB reader and both environment regions were rearmed after target/GPT/loader
validation. The old valid serial flags were 3 and 4; the two new CRC-valid copies
use flags 5 and 6 respectively and both contain `BOOT_ORDER=A`,
`BOOT_A_LEFT=3`, `BOOT_B_LEFT=0`, and `sv08_env_layout=ab-8gb-v1`. Direct
readback matched the complete 128 KiB prepared pair. This only re-arms the
previously validated diagnostic A boot; it does not validate recovery policy,
health confirmation, or normal-host operation after this write.
