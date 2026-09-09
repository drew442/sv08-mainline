# 0004: Immutable and writable OS operating modes

Date: 2026-09-09. Status: accepted product requirement and design policy;
implementation and hardware validation pending.

## Requirement

The owner selects immutable mode by default and a user-configurable writable
mode for users who need direct OS customization. Writable mode is a supported
long-term operating choice. It is not named or treated as maintenance/developer
mode. Both modes retain the A/B update and persistent user-data requirements.
See the [host OS design](../design/host-os-ab.md) for the wider assessment.

## Decision

Provide two named modes with a persistent setting, visible in the UI and
manageable through a documented local command:

| Behavior | Immutable mode (default) | Writable mode |
| --- | --- | --- |
| Active OS root | Read-only during normal operation | Read-write |
| Direct deb/apt package changes | Delivered through an image build | Available on the active slot |
| Printer config, calibration, network settings and uploaded files | Editable and persistent | Editable and persistent |
| Routine image updates | Tested whole-release A/B deployment | A/B deployment with explicit customization reconciliation |
| Local package/service customization | Add to release manifest | Install/edit directly; record for future deployments |
| Printing protections and update idle policy | Enforced | Enforced |

Mode selection does not grant a release permission to discard local software
changes or user artifacts. It also does not make writable slots byte-identical
to a tested release. Display the base release and customization status separately.
Immutable means normal system writes are disabled; it is not a claim of secure
boot, cryptographic integrity, or protection from a privileged administrator.

## Filesystems and switching

Prefer the same ext4 slot layout for both modes, mounted read-only or read-write
according to policy. Keep boot assets paired with their root; in immutable mode
mount boot read-only or leave it unmounted. In writable mode make supported
kernel/package boot changes possible only within the active pair. Integration
must prevent package boot hooks from changing the other slot, shared bootloader,
partition table or trial metadata. Kernel packages cannot be considered supported
for direct installation until those hooks are validated.

Store the requested mode in persistent system settings. Apply changes at an idle,
controlled reboot, after quiescing services and checking for a pending update or
package operation. The setting survives image updates, rollback and power cycles;
recovery uses its own fixed policy and offers mode repair. A pending release and
mode change must be reconciled before arming the next boot, not raced independently.

Switching immutable to writable makes the current slot writable; it does not
replace the OS or change printer data. Switching writable to immutable freezes
the current customized installation read-only. Preserve its contents and report
it as a customized image, not a pristine release. Restoring a standard release is
a separate, explicit action with export/reconciliation of local changes.

Do not use a permanent shared root overlay across releases: it can mix old
libraries, package metadata and new files. If compressed roots are needed to fit
8 GB, prove a mode-compatible alternative and its storage budget before adopting
it. EROFS/SquashFS cannot simply be remounted writable like ext4. A second larger
storage requirement for writable mode is not accepted by this decision.

## Package changes and A/B updates

APT and dpkg state stay with the active slot's installed files. The inactive slot
is never a live package-manager scratch area. Mode switching cannot make an apt
operation atomic; a power interruption during a local package upgrade remains a
recovery case, even though the other OS slot is retained.

Separate operating mode from update policy. Either mode may select automatic
idle staging and next-boot activation, or opt out. An automatic update must not
silently erase customization:

1. Record explicit extra packages, repositories, versions/pins and intended
   service overrides in a persistent customization manifest. Preserve package
   inventory and configuration differences; keep secrets private. Inventory
   alone cannot describe every manual script or edited file.
2. For a customized system, assemble a candidate that includes compatible
   requested packages/overrides using isolated build tooling. Check package
   availability, dependencies, storage, kernel/MCU constraints and service
   behavior. Keep the base release signature and derived-image provenance
   distinct; local customization is not an official tested release signature.
3. If reconciliation is unavailable, incomplete, conflicts or exceeds space,
   leave the current slot active and present the reason. Update policy remains
   configured, but that update is blocked. Do not erase user files or run blind
   apt replay at the next boot to make it proceed.
4. Offer a reviewed reconciled candidate, continued use of the current system,
   or an explicit return to a standard image after exporting local changes.
   Keep the previous slot and its compatible state for rollback. Replacing the
   older fallback on a subsequent update requires retaining needed customization
   records/exports independently of that slot.

Arbitrary root edits cannot be guaranteed to merge automatically into future
releases. That limit applies to both a writable system and a customized system
later switched to immutable. First implementation may block image activation
for customized systems while reconciliation tooling is incomplete; the UI must
explain this rather than silently disabling the selected update policy.

Prevent supported package/service updates during a print or image transaction,
including unattended package timers. Provide an idle-aware package workflow.
A user with unrestricted root access can bypass OS policy; this is not an excuse
to weaken Klipper heater protections or silently enable conflicting auto-updaters.
Writable mode may install compilers/DKMS on demand within available storage; the
standard images still ship modules built and tested before deployment.

## Validation and consequences

Both modes are release test targets. Verify default immutable boot, writable
package installation, persistence across reboot, both switching directions,
customized read-only boot, pending-update/mode-change races and interrupted apt.
Test A/B update/rollback in each mode, matching dpkg/files, customization conflict
blocking, free-space exhaustion, preservation/export and idle enforcement.
The factory 8 GB footprint, required Wi-Fi/HDMI, camera support plan and recovery
requirements remain unchanged. No image, mount or printer setting was altered
by accepting this design.

This decision records the owner's instruction and project integration policy.
It introduces no upstream patch or source revision; implementation must retain
separate build, activation and hardware-validation evidence.
