# Board kernel Debian packaging

2026-09-13. The physically tested diagnostic kernel now has an upstream-generated
Debian package and an exact-ABI board-support companion. Both installed and
configured successfully in an isolated ARM64 chroot. This is image-composition
input, not an A/B image or authorization to install a kernel on the printer.

The [result record](host-kernel-packages-20260913.json) contains package hashes.
Kernel configuration and decompressed Image match the
[physical trial](host-kernel-trial.md). Package identity:

| Package | Version | Scope |
| --- | --- | --- |
| linux-image-6.18.51-sv08-candidate1 | 6.18.51+sv08.1-1 | Kernel, modules and generic DTBs from the recorded patched tree |
| sv08-board-support-6.18.51-sv08-candidate1 | 0.1.0~diagnostic.1 | Exact diagnostic DTB and patched onboard-radio module |

## Kernel package build

Use the pinned, patched source/output from the [compile record](host-kernel-compile.md).
The build uses Linux's supported `bindeb-pkg` target, not a replacement package
builder. Required native build dependencies include debhelper, libdw-dev,
libelf-dev and libssl-dev, alongside the recorded kernel toolchain.

```sh
SOURCE_DATE_EPOCH=1789257600 \
KBUILD_BUILD_TIMESTAMP='2026-09-13 00:00:00 UTC' \
KBUILD_BUILD_USER=sv08 KBUILD_BUILD_HOST=builder KBUILD_BUILD_VERSION=1 \
KDEB_PKGVERSION='6.18.51+sv08.1-1' KBUILD_DEBARCH=arm64 \
KDEB_CHANGELOG_DIST=trixie DEB_BUILD_PROFILES=pkg.linux-upstream.nokernelheaders \
DEBFULLNAME='SV08 Mainline' DEBEMAIL='noreply@localhost' \
make -C "$KERNEL_SOURCE" O="$KERNEL_OUTPUT" \
  ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j4 bindeb-pkg
```

The Debian revision is `1` so the packaging rules retain the tested kernel build
version. Upstream creates a gzip `vmlinuz`; the slot boot script needs its
**decompressed raw Image**, verified against the tested hash. The package's 61
generic DTBs omit the SV08 diagnostic tree. Never choose a similarly named DTB
automatically. The separately generated `linux-libc-dev` package was not installed.

The supported `nokernelheaders` profile avoids unavailable ARM64 header-build
dependencies on this cross-build workstation. Headers/DKMS packaging remains
required for a future on-host module rebuild workflow; the current companion
ships the prebuilt module matched to this exact kernel package. Package-level
byte-identical rebuilds have not been demonstrated, despite the retained input
timestamps and matching kernel payload.

## Companion package assembly

Use a fresh staging directory and `dpkg-deb --root-owner-group --build`, with
`SOURCE_DATE_EPOCH=1789257600`. Copy these files with mode 0644, except the two
maintainer scripts with mode 0755:

| Source | Package path |
| --- | --- |
| [control](../../configs/host-os/board-support/control) | DEBIAN/control |
| [postinst](../../configs/host-os/board-support/postinst) | DEBIAN/postinst |
| [postrm](../../configs/host-os/board-support/postrm) | DEBIAN/postrm |
| Reviewed stripped 8189fs.ko | usr/lib/modules/6.18.51-sv08-candidate1/extra/8189fs.ko |
| Reviewed diagnostic DTB | usr/lib/linux-image-6.18.51-sv08-candidate1/allwinner/test-sv08-01-diagnostic.dtb |

Under `usr/share/doc/sv08-board-support-6.18.51-sv08-candidate1/`, include
[copyright](../../configs/host-os/board-support/copyright), the
[radio README](../../patches/rtl8189fs/README.md) as `radio-provenance.md`, its
[patch](../../patches/rtl8189fs/0001-strict-flex-arrays-and-thread-format.patch)
as `radio-compat.patch`, the [diagnostic DTS](../../configs/host-os/test-sv08-01-diagnostic.dts)
as `diagnostic.dts`, and the [kernel artifact record](host-kernel-compile-20260913.json)
as `kernel-artifacts.json`. Hash-check both binary inputs before packaging.
Retain the full pinned source/patch closure for eventual redistribution.

The companion's only runtime hook runs `depmod` for its named release. Its exact
kernel-version dependency prevents silently pairing it with another kernel.
It neither selects a boot image nor changes wireless country/configuration.
Retire these diagnostic packaging inputs when the complete board/release builder
owns the same source, ABI, DT-selection and dependency checks.

## Isolated installation result and remaining integration

A separate copy of the previous QEMU integration root accepted both packages
through real ARM64 `dpkg` under QEMU user emulation, with private mount/PID/network
namespaces. The sole kernel post-install hook was initramfs-tools; no bootloader
hook was present. Kernel packaging otherwise runs installed `/etc/kernel` and
`/usr/share/kernel` hooks, so inspect a new target root before installation.

Initramfs generation, exact installed Image/DT/module checks, empty `dpkg --audit`
and `apt-get check` passed. The old Debian kernel/meta-package were removed only
from this disposable copy. The matching upstream regulatory signature was
selected using Debian's documented alternative. No host-device or printer writes
were performed by these package-installation tests.

The copy still contains its historical QEMU probe and is explicitly **not a
deployable root**. Compose a fresh image from clean package inputs and current
integration code; do not ship this fixture. Its generated initramfs hash is
recorded separately from the earlier single-root hardware-trial initramfs.
Boot slots need raw Image, their matching raw initramfs, the explicit diagnostic
DT path, current persistence metadata and finalized application services.
