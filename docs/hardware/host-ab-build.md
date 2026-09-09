# A/B host OS: first offline preparation

Date: 2026-09-09. Status: implementation started; no bootable A/B image yet.
Scope: factory-capacity layout with test-sv08-01 as the initial board target.
The printer is offline; no SSH, device writes or hardware tests were performed.

## Implemented stages

The [preparation tool](../../scripts/prepare_host_os.py) and
[package/layout profile](../../configs/images/host-ab.json) provide separate
bootstrap, package installation, security-snapshot refresh and inspection stages. All default to dry-run.
They create only a workstation build directory and an isolated ARM64 chroot;
package installation temporarily mounts proc there and unmounts it afterward.
They do not partition media, assemble boot firmware, set printer services up,
or activate immutable/writable mode. Do not flash or deploy this rootfs.

The custom integration gap is enforcing the reviewed layout, stage identity and
size budgets while collecting a Debian package baseline. It delegates bootstrap
and package management to debootstrap/apt. The existing vendor-assisted builder
is unchanged. Once the new builder can replace it, consolidate the shared
bootstrap routines instead of maintaining two independent implementations.
Tests live in [test_prepare_host_os.py](../../tests/test_prepare_host_os.py).

The profile pins Debian trixie/arm64 and Debian/security snapshots to
`20260901T000000Z`, matching the prior host dependency intake date. Package lists
use `main` and `non-free-firmware`; signatures remain checked. Dated snapshots
make inputs repeatable, not permanently current: update them through a reviewed
release build. The output inventory records actual resolved package versions.

The initial dependency baseline includes the Debian kernel, NetworkManager,
RAUC, SSH, GTK/Xorg/libinput, VTE, Realtek firmware, V4L2 tools, FFmpeg and nginx.
These are package candidates, not validated application/driver compatibility.
NetworkManager is selected for the required Wi-Fi provisioning path; the final
image must not also configure networkd to manage the same interfaces.
The first [Klipper package](host-apps-build.md) now passes offline installation
and file-output checks. The [complete application payload build](host-stack-build.md) now includes
Moonraker, Mainsail and KlipperScreen with their pinned dependencies. Service
activation and operating-mode integration remain outstanding. No camera streamer is selected
merely by installing V4L2/FFmpeg. Firmware-realtek is not an `8189fs` driver.

## Reproduce on the build workstation

Requires Linux, root for chroot/proc, debootstrap, Debian archive keys,
qemu-user-static and enabled ARM64 binfmt, Python 3, coreutils and network access.
Do not run on the printer. Use a new work path for each attempt; failed package
stages are not silently rerun. The work path must be below repository `build/`,
without symlinks. Workstation chroot execution is not a hostile-code sandbox;
inputs must remain the reviewed signed repositories.

```sh
python3 scripts/prepare_host_os.py --stage bootstrap
sudo python3 scripts/prepare_host_os.py --stage bootstrap --execute
sudo python3 scripts/prepare_host_os.py --stage packages --execute
sudo python3 scripts/prepare_host_os.py --stage refresh --execute
sudo python3 scripts/prepare_host_os.py --stage inspect --execute
python3 -m unittest discover -s tests -v
```

Default outputs are ignored under `build/host-ab-baseline-v1/`: captured profile,
stage markers, rootfs, `packages.tsv` and `report.json`. The rootfs deliberately
retains a service-start suppression policy and is not finalized for deployment.
Bootstrap generates no per-printer keys/config; package finalization clears
package-generated SSH host keys and machine-id.

Inspection measures apparent root/boot bytes, including apt indexes, against
1,536/144 MiB content budgets, preserving headroom within the 2,048/192 MiB slots.
These measurements exclude filesystem metadata and are not a substitute for
populating/fsck-checking real slot images. Recovery, update bundles, application
state and user-data occupancy need separate measurements. A passing dependency
baseline does not prove the complete OS fits.

## Completed baseline result

All four stages completed on 2026-09-09. The
[sanitized report](host-ab-baseline-20260909.json) records 476 installed packages,
**1,145,965,060 apparent root bytes (1,092.88 MiB)** and
**74,531,314 boot bytes (71.08 MiB)**. Both content budgets pass, leaving about
443 MiB below the conservative root-content budget for later integration.
APT dependency checks and package-state inspection passed; proc was unmounted.
The package install generated a gzip initramfs because zstd was absent.

RAUC 1.13, NetworkManager 1.52.1 and FFmpeg 7.1.5 version commands ran under
ARM64 QEMU user emulation; Python GTK 3.24/Cairo 1.27.0 imports passed. These do
not test the running kernel, graphical output, networking or camera hardware.
Sixteen repository tests passed, including six new baseline/layout tests.

The report includes the exact inventory hash, boot-file hashes and tool versions.
Final review found three OpenSSL packages retained from the bootstrap version;
the separate refresh stage aligns the entire base with the same selected security
snapshot before inspection. It does not advance to a floating repository. Application packaging, recovery, filesystem
metadata and practical staging/user-data space are not included in the reported
root/boot content measurement. No complete second build has been performed.

## Captured boot-input audit

Evidence source: preserved private vendor boot-support archive SHA-256
`2d3d43ee70a88b10def8304b1a823ec9a94047d79a594cdedbb9733f205b077b`.
The selected `sun50i-h616-sovol-emmc.dtb` was decompiled offline; raw DTS and
compiler warnings remain private. PCB revision remains unknown. Entries below
are **configured**, not measurements of voltages, pin wiring or chip identity.

| Path / feature | Captured configuration | Required follow-up |
| --- | --- | --- |
| `/soc/mmc@4022000` | Enabled, eight-bit eMMC, 45 MHz cap, `no-1-8-v` | Compare mainline bindings and validate actual storage reliability |
| `/soc/mmc@4021000` | Enabled, four-bit SDIO, 25 MHz cap, non-removable, power sequence | Identify the actual radio and driver before selecting external source |
| `/wifi-pwrseq` | Simple MMC power sequence, active-low reset GPIO tuple, 200 ms delay | Resolve GPIO controller/pin against board evidence; do not guess or transpose to another board |
| `/vcc33-wifi`, `/vcc-wifi-io` | Configured fixed 3.3 V and 1.8 V supplies | Preserve as config evidence, not measured voltages |
| `/soc/ethernet@5030000` | Enabled vendor `allwinner,sunxi-gmac`, RMII; ethernet0 alias targets it | Audit this path, not only the disabled EMAC at 0x5020000 |
| Display engine and HDMI/PHY | H616-specific vendor compatibles | Audit DRM, clock/PHY and DTS changes as a coordinated set, not an assumed DKMS-only fix |

The upstream v6.12 H616 dtsi and HDMI driver are comparison sources, not proof of
Debian package contents or support. The captured vendor Ethernet binding differs
from the upstream stmmac binding and needs explicit conversion/driver analysis.
Sources inspected 2026-09-09:
[H616 dtsi](https://raw.githubusercontent.com/torvalds/linux/v6.12/arch/arm64/boot/dts/allwinner/sun50i-h616.dtsi),
[HDMI driver](https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/gpu/drm/sun4i/sun8i_dw_hdmi.c),
[Ethernet driver](https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/net/ethernet/stmicro/stmmac/dwmac-sun8i.c).

The preserved installed `crowsnest.conf` selects ustreamer at **640×480,
15 fps**, with RTSP disabled. This is the initial existing-camera compatibility
target, not a measurement of supported formats or delivered frame rate. Camera
identity remains private/unverified until the next device inspection. Package
ustreamer from a reviewed source and test MJPEG/snapshots before adding timelapse
encoding; the saved config alone does not justify selecting a different camera.

The pinned snapshot advertises Debian arm64 `ustreamer` **5.4-1+b2**
(source 5.4-1), so a distro-package candidate is available without a custom
streamer build. It is not installed in this first dependency baseline; add it
to the next application integration build and validate its options against the
preserved configuration.

The downloaded Debian **6.12.107-1** package was inspected directly. Its config
selects MMC_SUNXI, USB_ACM, USB_VIDEO_CLASS, SUNXI_WATCHDOG, DWMAC_SUN8I,
DRM_SUN4I, DRM_SUN8I_DW_HDMI, BLK_DEV_NBD and DM_VERITY as modules. This establishes
build configuration, not hardware operation. `modinfo -F alias` on its
`sun8i-drm-hdmi.ko.xz` lists A83T and H6 HDMI compatibles, not the captured H616
compatible. `dwmac-sun8i.ko.xz` does not advertise `allwinner,sunxi-gmac` used by
the enabled vendor Ethernet node. Do not fix these mismatches by blindly changing
compatible strings; the required clocks, PHY and controller support need review.

## Next work

- Continue from the [measured application stack](host-stack-build.md) through
  the [completion checklist](host-os-tasks.md).
- Continue the [Armbian source intake](host-ab-armbian-intake.md) for maintained
  SV08 boot support; its board definition is explicitly unverified.
- Inspect the exact installed Debian kernel config/modules against captured DT
  requirements; locate maintained driver/patch sources and record their pins,
  licensing and retirement criteria before building.
- Obtain source-reproducible SPL/U-Boot/TF-A and a reviewed board DTS; resolve
  DRAM/boot layout, Ethernet and display support. Do not copy the captured prefix
  into the proposed GPT layout.
- Implement operating modes, persistent mounts and package/update coordination
  from [decision 0004](../decisions/0004-os-operating-modes.md).
- Assemble/fsck real slot images, recovery and signed bundles; test 8 GB capacity,
  stage failure, slot selection and state migration before hardware activation.
- When the printer returns: capture actual Wi-Fi SDIO identity/driver, camera
  interface/formats, PCB/DRAM evidence and boot diagnostics. These human/online
  tasks do not prevent offline builds and audits.
