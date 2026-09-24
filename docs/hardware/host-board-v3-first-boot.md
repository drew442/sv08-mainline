# V3 board image: physical A boot and temporary Wi-Fi

2026-09-24, named profile `test-sv08-01`. The owner installed the reviewed spare
eMMC and powered the printer with the Beelink serial lead connected. The factory
eMMC remained stored. The printer was lying on its side; no printer output was
requested. This result applies to the exact [v3 image](host-board-image-20260923-v3.json).

The Beelink receive-only logger was armed before reconnection. Its first 106,085
bytes, copied into ignored `local/test-sv08-01/kvm-20260924/`, have SHA-256
`38129bc658b9d06a3812ff857d6ec3bc781eaad86f872396d99b497a78bfdf3c`.
The trace contains two A boots: v6 SPL initialized DRAM, U-Boot reported 1 GiB
and selected A, and Linux `6.18.51-sv08-candidate1` reached Debian login. A
later read-only environment check reported `BOOT_ORDER=A`, `BOOT_A_LEFT=1`,
`BOOT_B_LEFT=0`. The installed diagnostic root lacks `/etc/fw_env.config`; the
read used a temporary configuration with the reviewed eMMC environment offsets.
Coordinate any further reboot or rearm: another A selection could exhaust its
budget and enter independent recovery. This boot does not validate B, recovery
or health confirmation.

The GL-RM1V2 at `glkvm.drewnet.online` supplied HDMI video at 1280×720 and USB
HID keyboard. Console login succeeded with the private pilot credentials. This
does not test the printer touchscreen. The printer's Ethernet cable was used by
the KVM, explaining the absent Ethernet carrier without implying a port fault.

The onboard radio loaded, but NetworkManager lacked a supplicant because this
copied diagnostic root has no `wpa_supplicant` binary or D-Bus registration,
despite the package being in the intended manifest. Three hash-checked Debian
trixie arm64 packages were copied through the KVM's read-only USB mass storage
into ignored printer data and extracted under `/data/sv08/wifi-runtime`. A
temporary D-Bus policy bind mount under `/run` and a transient supplicant service
let NetworkManager join the owner's `iotnet` network. The connection profile is
on persistent data with mode 0600. Wi-Fi assigned `192.168.1.150`; SSH succeeded
after matching the host key to the private image identity. Root-A remained
read-only, and the USB package media was unmounted. The supplicant and temporary
policy will disappear on reboot, so the saved profile alone cannot reconnect.

`sv08-boot-health.service` failed because RAUC was deliberately masked and its
configuration absent. No health-ready claim or attempt reset was made. Source
checks now reject a diagnostic root missing the supplicant/D-Bus files, and
diagnostic root and boot arguments mask boot-health. The composer rechecks these
conditions even for an older receipt. These changes do not alter the installed
v3 image or normal deployable boot-health.

The KVM proves remote video, keyboard and small-file delivery. This image has
no reviewed remote full-disk/SPL/GPT update path; its A/B updater is disabled
because it is non-deployable, and installed recovery only exposes data export.
The USB writer remains the known complete-image recovery path until a separate
remote writer or deployable signed update passes physical validation.
