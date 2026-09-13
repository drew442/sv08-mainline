# Exact H616 kernel compilation experiment

2026-09-13. This advances the existing host OS work toward a physical boot trial.
It is not a supported kernel release or an assembled printer image. See
[decision 0015](../decisions/0015-board-kernel-compile-baseline.md).

## Inputs and patch application

The [candidate manifest](../../configs/host-os/kernel-61851-compile-candidate.json)
pins Linux 6.18.51 and Armbian's source tree, all 774 downloaded files with SHA-256
and Git blob IDs, and the 521 enabled patches in declared order. All downloaded
Armbian bytes matched the complete pinned Git tree. Kernel archive SHA-256 matched
the published kernel.org list; PGP signature verification is not claimed.

Patch application took place in a fresh extracted kernel tree under ignored
`build/host-kernel-61851-v1/linux-6.18.51/`. It has its own empty Git repository
so `git apply` resolves kernel paths locally. Without that boundary, Git inherited
the enclosing project and reported skipped patches with a zero exit status;
that initial no-op was detected from verbose output and discarded as evidence.
The successful pass checks both exit status and absence of `Skipped patch`.

All 521 enabled patches applied. Entry 90, the RTL8723CS Bluetooth resume patch,
needed `git apply -C2` because its final context line expected a duplicate match
entry absent in Linux 6.18.51. Its actual one-line code change was unchanged.
All other patches used normal context. No failed patch was silently omitted.
An independent review checked every applied patch hash and the recorded results.

The stock `dt_64/sun50i-h616-sovol-sv08.dts` was copied into the kernel's Allwinner
DTS directory; only that copied board and the diagnostic variant are build targets.
No generic DTS Makefile rewrite, installer, external-driver harness, user hook or
runtime overlay was run. This is an explicit compile recipe, not the complete
Armbian build framework. Preserve Linux `COPYING`/`LICENSES`, Armbian licensing,
patch authorship and DTS SPDX notices with the retained sources.

## Configuration and build method

Start with the pinned `linux-sunxi64-current.config` and run `olddefconfig`.
For the diagnostic candidate, disable debug information/BTF, set
`LOCALVERSION=-sv08-candidate1`, and enable built-in device mapper, DM verity and
the sun8i Ethernet glue. The seed omitted DM verity; it is required by the tested
signed-update format. Built-in Ethernet avoids making initial SSH depend on an
initramfs module list. Keep the rest of the seed's effective configuration.

The exact configuration operations are:

```sh
scripts/config --file ../output/.config \
  --disable DEBUG_INFO --disable DEBUG_INFO_DWARF5 --enable DEBUG_INFO_NONE \
  --disable DEBUG_INFO_BTF --disable DEBUG_INFO_BTF_MODULES \
  --set-str LOCALVERSION '-sv08-candidate1' \
  --enable BLK_DEV_DM --enable DM_VERITY --enable DWMAC_SUN8I
make O=../output ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
KBUILD_BUILD_TIMESTAMP='2026-09-13 00:00:00 UTC' \
KBUILD_BUILD_USER=sv08 KBUILD_BUILD_HOST=builder KBUILD_BUILD_VERSION=1 \
make O=../output ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j6 \
  Image modules allwinner/sun50i-h616-sovol-sv08.dtb \
  allwinner/test-sv08-01-diagnostic.dtb
```

Run these from the isolated patched kernel source, with the configuration seed
already at `../output/.config` and both DTS files copied. Never run these build
commands on the printer. This build does not install modules or write devices.
Compiler and final artifact hashes belong in the result record; compilation
alone does not prove reproducibility or a working hardware driver.

## Diagnostic board configuration

The [diagnostic DTS](../../configs/host-os/test-sv08-01-diagnostic.dts) includes
the pinned stock DTS and makes twelve effective property changes: a distinct
model string, six regulator bound values, four removed CPU OPP references, and
GPU disabled. An independent full-DTB comparison resolves phandles and confirms
no other semantic property changes. HDMI, UART, Ethernet, eMMC and optional-node
states remain intact.

Captured vendor limits are DCDC1 0.81–0.99 V, DCDC2 0.81–1.10 V and DCDC3
1.35–1.50 V. They are configuration evidence, not measured electrical limits.
The inherited candidate broadens those ranges and permits speed-bin CPU OPPs
up to 1.16 V. The diagnostic configuration preserves the captured limits and
omits CPU OPP selection, relying on the known bootloader's initial CPU setup.
CPU frequency scaling and its associated thermal cooling operation are therefore
not acceptance claims for this first diagnostic trial; do not stress-test it as
a production performance configuration.

The inherited GPU supply resolves to the DRAM-labelled DCDC3 rail. Unlike the
vendor tree, the candidate has no GPU OPP table, so an actual GPU-driven voltage
transition is not established. GPU is nevertheless disabled until its power
description is resolved. HDMI display uses separate DRM nodes.

AXP1530 versus AXP313a is not by itself a board-identification blocker:
the upstream [v6 support submission](https://lists.openwall.net/linux-kernel/2023/01/16/903)
renamed the support, and the [maintainer discussion](https://lkml.iu.edu/hypermail/linux/kernel/2301.1/02086.html)
reports BIQU's confirmation of the internal name. The early AXP1530 controls
at 0x10 and 0x13–0x17 agree with the candidate's AXP313A definitions. Sources
accessed 2026-09-13; this is upstream mapping evidence, not a photographed marking.

## Device-tree validation

The inherited stock DTB compiled successfully and its 19-file include closure
was independently captured. The diagnostic DTB also compiled; its effective
properties are checked with:

```sh
python3 tests/host_diagnostic_dtb.py PATH/TO/test-sv08-01-diagnostic.dtb
```

The check verifies regulator bounds, absent CPU OPP references, disabled GPU,
enabled display/storage/network/console, eMMC width/frequency/no-1.8-V switching,
and disabled optional nodes. A mutated GPU-enabled copy was rejected. These are
binary-property acceptance checks, not electrical or device-tree-schema tests.

Standalone dtc reports 36 inherited warnings: 15 unique-unit-address, 12
simple-bus-reg, seven unit-address-versus-reg and two graph-child-address.
Two additional diagnostic lines are source continuations, not warnings. The
kernel target suppresses several warning classes. Retain the unsuppressed log;
do not claim schema validation. The PWM child nodes include configuration phandle
targets consumed by the patched PWM driver; verify the PWM5/AC300 Ethernet clock
on hardware rather than treating those warnings as missing register proof.

## Remaining before the physical trial

Finish kernel/modules and separately pinned onboard-radio compilation; record
the final configuration, toolchain and hashes. Assemble the matching modules,
initramfs and diagnostic DT into a bounded test boot using the existing working
bootloader. Preserve the vendor boot files as the fallback, and keep printer
services inactive. The new A/B bootloader/environment integration remains a
separate milestone. The [verified serial path](test-sv08-01-host-console.md)
allows the next trial to be observed from early boot through SSH.
