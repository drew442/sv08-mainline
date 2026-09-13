# 0015: Exact 6.18 board-kernel compilation baseline

Date: 2026-09-13. Status: accepted for offline compilation; hardware adoption
and release support remain unvalidated.

## Context

The Debian ARM64 baseline and application/update tests are complete enough to
prepare a board boot trial. The distro kernel used for those QEMU tests does not
provide the reviewed H616 display/platform integration. The Armbian framework
pin alone selected a moving branch; it did not pin the Linux source. Serial
capture now works on the physical host, including SPL through SSH after reboot.

## Decision

Use Linux **6.18.51**, stable commit
`f6388029ea9e2c9e807d73827658738ea131faee`, as an exact offline compile baseline
with Armbian build `a4ea8c49cd07b9d6604cbc32234a5f5cdfd99015`'s declared
`patch/kernel/archive/sunxi-6.18/series.conf`. Preserve all 521 enabled entries
in order and the eight declared exclusions. This avoids inventing an unreviewed
minimal collection while discovering cross-subsystem dependencies.

Record every source hash, patch result, copied DTS and configuration change.
No Armbian installer, external-driver harness, user hook or runtime overlay is
run. This experiment is not a reproduction of the full Armbian build. Patch
failures must remain visible; do not silently skip a failed driver change.

Keep the existing Debian userland and APT packaging direction. This decision
does not select a new production update supplier, replace the working host
bootloader, or authorize treating CB1 electrical assumptions as measured facts.
An initial compile may omit external radio injection, but the onboard radio
remains a host requirement and needs its separately pinned driver before a
complete candidate is accepted.

## Inputs, licensing and retirement

The [kernel.org release index](https://www.kernel.org/) listed 6.18.51 as its
latest longterm release on 2026-09-13. The exact source archive is
[linux-6.18.51.tar.xz](https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.18.51.tar.xz),
SHA-256 `ba2f60f858bf4d1f929101faa356c93dc8b925b17aaa9f95eabd4627758df613`.
Its checksum matches kernel.org's published SHA-256 list; signature verification
is not claimed. The Git tag `v6.18.51` dereferences to the commit above.

Linux is GPL-2.0-only with its documented syscall exception and per-file licensing;
retain `COPYING` and `LICENSES/`. Preserve the Armbian source license, patch
authorship and each copied DTS SPDX declaration. This compilation experiment
does not complete the transitive source/firmware inventory for redistribution.
The existing [source intake](../hardware/host-sunxi-618-intake-20260912.md)
records patch provenance and dependencies. Retire platform patches individually
as equivalent upstream/distro support becomes available, with board regression
tests; prefer a maintained distro package once it supplies the required support.

## Validation boundary

An independent review recommended this bounded ordered-series experiment.
Successful patch application and DT/kernel compilation must be recorded
separately from hardware activation. Before that activation, review the final
regulator/OPP assignments, eMMC, UART, Ethernet, display and radio configuration
against captured board evidence; then bind the exact boot artifacts and write
scope to the identified spare. The owner accepts the existing recovery paths.

The diagnostic DTS preserves captured vendor regulator constraints, omits CPU
OPP references and disables the unresolved GPU supply consumer. It keeps HDMI,
storage, networking and console nodes enabled. These temporary restrictions are
explicit in the named diagnostic profile and its binary-property test; retire
them only after power/performance validation, not merely a successful boot.

A temporary [one-shot dispatcher](../../configs/host-os/diagnostic-boot.cmd.in)
fills an identified test-access gap: the existing loader's `bootdelay=-2` prevents
relying on an interactive countdown. Its captured script order permits a new
`boot.scr.uimg` to return to unchanged `boot.scr`. A trial marker is deleted and
checked absent before loading the candidate; failure returns to the original
path. No persistent U-Boot environment is saved. Real FAT/sandbox refusal tests
are in [the dispatcher test](../../tests/diagnostic_boot.py). Validate an unarmed
fallback on the actual vendor loader before arming. Retire this dispatcher once
the supported A/B loader supplies equivalent trial/fallback behavior. FAT marker
deletion is not an atomic or power-loss-proof update mechanism.
