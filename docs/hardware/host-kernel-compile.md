# Exact H616 kernel compilation experiment

2026-09-13. This advances the existing host OS work toward a physical boot trial.
It is not a supported kernel release or an assembled printer image. See
[decision 0015](../decisions/0015-board-kernel-compile-baseline.md).

## Inputs and patch application

The [candidate manifest](../../configs/host-os/kernel-61851-compile-candidate.json)
pins Linux 6.18.51 and Armbian's source tree, all 774 downloaded files with SHA-256
and Git blob IDs, and the 521 enabled patches in declared order. All downloaded
Armbian bytes matched the complete pinned Git tree. Kernel archive SHA-256 matched
the published kernel.org list. Independent verification of the detached signature
over the decompressed archive passed for the developer fingerprint recorded in
the manifest, using kernel.org's official HTTPS fingerprint and WKD key. No
personal web-of-trust certification is claimed.

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
`LOCALVERSION=-sv08-candidate1`, and enable DM verity with device mapper as
modules and built-in sun8i Ethernet glue. The seed omitted DM verity; it is required by the tested
signed-update format. Built-in Ethernet avoids making initial SSH depend on an
initramfs module list. Keep the rest of the seed's effective configuration.

The exact configuration operations are:

```sh
scripts/config --file ../output/.config \
  --disable DEBUG_INFO --disable DEBUG_INFO_DWARF5 --enable DEBUG_INFO_NONE \
  --disable DEBUG_INFO_BTF --disable DEBUG_INFO_BTF_MODULES \
  --set-str LOCALVERSION '-sv08-candidate1' \
  --module BLK_DEV_DM --module DM_VERITY --enable DWMAC_SUN8I
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
the pinned stock DTS and changes the model string, six regulator bound values,
four CPU OPP references, GPU status and the CPU critical temperature. An
independent full-DTB comparison of the initial twelve-property variant resolved
phandles and confirmed no other semantic changes. Further thermal review found
the inherited critical trip increased from the vendor's 105°C to 110°C; the
diagnostic variant now preserves 105°C with 2°C hysteresis. HDMI, UART, Ethernet,
eMMC and optional-node states remain intact.

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
enabled display/storage/network/console, preserved CPU critical shutdown threshold,
eMMC width/frequency/no-1.8-V switching,
and disabled optional nodes. A mutated GPU-enabled copy was rejected. These are
binary-property acceptance checks, not electrical or device-tree-schema tests.

Standalone dtc reports 36 inherited warnings: 15 unique-unit-address, 12
simple-bus-reg, seven unit-address-versus-reg and two graph-child-address.
Two additional diagnostic lines are source continuations, not warnings. The
kernel target suppresses several warning classes. Retain the unsuppressed log;
do not claim schema validation. The PWM child nodes include configuration phandle
targets consumed by the patched PWM driver; verify the PWM5/AC300 Ethernet clock
on hardware rather than treating those warnings as missing register proof.

## Completed build and first physical trial

Kernel, modules and separately pinned radio compilation completed successfully.
The [artifact record](host-kernel-compile-20260913.json) records configuration,
toolchain, hashes and warning counts. The runtime module directory contains
2,663 modules; Debian initramfs-tools 0.148.4 built the matching initramfs on the
bring-up host. Independent inspection checked ARM64 headers, loader memory
ranges, initramfs ELF/dependency closure and root discovery. This was an
incremental build, not a demonstrated byte-identical clean rebuild.

Radio compilation emitted 568 warnings, including an overlapping `snprintf` on
the normal SDIO transmit-thread startup path and two legacy zero-length trailing
arrays under `-fstrict-flex-arrays=3`. Compile success does not establish runtime
safety. The first wired trial blacklists `8189fs`. A separately
[reviewed patch](../../patches/rtl8189fs/README.md) subsequently removed those
15 targeted warnings; its physical follow-up initialized the radio and completed
a passive scan. Association and sustained operation remain untested. The kernel
itself emitted 19 compiler warnings.

The [physical trial and return to the original kernel](host-kernel-trial.md)
both passed. This uses the existing vendor bootloader and single-root Debian
bring-up filesystem. New A/B bootloader/environment integration, required radio
association and full device/application validation remain separate milestones.
