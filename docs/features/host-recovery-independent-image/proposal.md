# Independently booted recovery OS within the factory-capacity layout

Kind: feature. Author: root-recovery-design. Date: 2026-09-12.
Requirement: [decision 0010](../../../docs/decisions/0010-host-administration-and-recovery-ui.md).
Dependency: authenticated host bundle upload, preserving the current delivery order.

## Problem and result

The existing GTK recovery export fixtures load workstation libraries. Recovery
script dispatch does not boot an independent OS. Deliver a reproducibly assembled,
measured 512 MiB recovery filesystem and actual ARM64 QEMU boot of its own kernel,
initramfs, libraries and existing GTK diagnostics with no A/B roots available.
This is an offline recovery candidate, not a board-bootable or export-certified
release. Complete trusted media preparation/export composition subsequently.

The accepted [layout](../../../configs/images/host-ab.json) remains exactly
7,818,182,656 bytes with a 512 MiB recovery partition. Do not enlarge recovery,
borrow indispensable content from A/B or data, replace GTK with a browser, remove
accepted touch/keyboard/mouse interfaces, or silently abandon accessibility.

## Existing evidence and format choice

Private read-only intake is in `local/feature-workflow/recovery-closure-estimate.json`
and `local/feature-workflow/recovery-fit-options-20260912.md`. A conservative closure
from existing installed package dependencies contains 273 packages and 691.13 MiB
of declared installed size, before missing dbus-x11/at-spi2-core and generated
initramfs. Unique listed regular files total 672.68 MiB. Even removing all listed
doc/man/info/locale files leaves 576.83 MiB before missing packages and filesystem
metadata. These are estimates, not fresh dependency resolution or fit evidence.
The selected Xorg package path has hard Mesa/LLVM/Z3 dependencies; deleting those
libraries is not a supported way to meet size requirements.

Evaluate standard SquashFS compression for `/usr` inside the existing physical
ext4 recovery root. Keep `/etc`, the image manifest, independent kernel/initramfs
and the regular compressed image on that root; mount `/usr` read-only before
switch_root. This preserves the current physical ext4 root topology and uses
distro packages rather than creating a custom graphics stack. Record the final
format and boot integration in an ADR based on measured fit. A simpler complete
uncompressed ext4 image is acceptable only if actual closure/occupancy proves it
fits without dropping required interfaces. Use no RAM-decompressed whole-root
fallback, writable overlay, unrecorded library deletion or firmware assumption.

Merged-/usr Debian needs `/usr` before init and its dynamic loader run. The
initramfs must independently carry ext4/loop/SquashFS modules and dependencies,
utilities and the mount/verification logic. Bind the selected compressed image's
hash, size and location in the external reviewed manifest without circular
hashing. Reject wrong/missing/replaced contents and unexpected backing/mount
identity before launching the recovery service; display useful boot diagnostics.
No external authenticated-boot claim follows merely from a supplied manifest hash.

The current production media provider rejects this extra compressed `/usr` mount.
Do not weaken or bypass it in this delivery. Ordinary diagnostics may boot, but
export/write/slot-selection capabilities must remain unavailable with an accurate
reason until a separate reviewed preparer/provider composition supports the exact
backing chain. Do not ship test-loop exceptions, synthetic verified media contexts
or fixture flags as production identity evidence.

## Implementation scope

Resolve a minimal complete recovery package closure from selected Debian/security
snapshot `20260901T000000Z`, including actual UI imports, accessibility/input,
fonts, systemd/udev, own kernel/initramfs and existing diagnostics/export runtime
requirements. Record versions, archive hashes, source/license provenance and
custom integration retirement plan. Reuse existing package caches where identical;
never run upstream bundled installers or modify selected baseline/upstream trees.
Keep original copyright/license material. Any doc/cache/translation exclusion must
be explicit, reproducible and compatible with declared languages and dpkg metadata.
Do not pretend recovery packaging completes future LAN restore provisioning.

Keep source intake, package assembly, filesystem build and isolated boot as
separate operations; inspect/dry-run by default. Only fresh reviewed ignored
workstation paths are outputs. Refuse symlinks, overlapping inputs/outputs and raw
block targets. Use private mount/PID/network namespaces for privileged preparation,
service-start suppression, bounded runtime resources and source/host preservation
checks. Use a full ARM64 VM with isolated listeners and no printer or private
backup mounts. Do not install workstation-wide dependencies implicitly.

Use the real installed recovery UI entry and service, without its preview mode
or workstation Python/GTK at runtime. Configure only reviewed writable runtime
mounts on the otherwise read-only candidate. No host login/password or network
listener is needed for this bounded local diagnostic boot. Test through real VM
virtual display/input: keyboard navigation/activation, mouse selection and touch
injection if the selected VM supports meaningful independent touch events. Label
any unavailable virtual input coverage; physical touch alone, keyboard alone and
mouse tests remain canonical release work. Preserve existing offline input
coverage and do not infer physical usability from screenshots.

## Acceptance

One offline `implement` task follows host-admin-bundle-upload:implement.

- `closure`: Exact snapshot dependency/archive/source/license inventory, own kernel
  and generated initramfs, complete actual GTK imports and runtime dependencies;
  documented deterministic exclusions and no borrowed A/B/workstation contents.
- `capacity`: Populated and fsck-checked 512 MiB ext4 candidate includes every
  indispensable boot/runtime artifact with explicitly measured remaining blocks
  and inodes. Record logical and allocated footprint, compressed/uncompressed
  sizes and peak preparation/boot memory and workspace. Preserve the accepted
  full-disk partition sizes. A failed fit is a finding requiring changed-method
  resumption, not successful delivery or permission to enlarge the partition.
- `independent-boot`: Full ARM64 QEMU starts its own kernel/initramfs and actual
  installed GTK service with A/B roots absent. Read-only root/optional usr and
  bounded tmpfs mounts are observed, boot/service errors checked, diagnostics and
  relevant virtual input exercised. A restart repeats the journey without state
  initialization or dependence on previous guest RAM.
- `identity-refusal`: Missing/changed compressed content or manifest and unexpected
  mount inputs fail before UI service activation; unsupported verified-media
  capabilities remain refused with useful reasons in normal diagnostics. No
  source/destination media mutation, trust bypass or synthetic export capability.
- `integration`: Builder/default refusal tests, actual relevant UI regressions,
  baseline/host preservation and cleanup, source/toolchain/artifact hashes and a
  repeat build comparison with explained nondeterministic fields. Run proportionate
  JSON/Markdown/diff/indexed-gitlink checks. Distinguish VM boot and static checks
  from H616 board support, recovery export, secure boot and complete release fit.

## Boundaries and continuation

No physical boot/flash, new kernel/platform-driver adoption, recovery media
premounter, restored-slot activation, signed restore, data formatting, host upload
change or owner-account/TLS/network provisioning. The initial VM kernel/graphics
profile is explicit, not the SV08 hardware identity. Keep all physical tasks in
[the canonical list](../../../docs/hardware/host-os-tasks.md#human-and-powered-printer-tasks).
No owner action blocks offline assembly. After this task, continue the reviewed
compressed-mount/premounter/provider/export composition and existing job-recovery
and ordinary-administration requirements; this subset does not complete recovery.
