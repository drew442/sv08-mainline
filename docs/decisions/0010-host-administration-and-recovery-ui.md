# 0010: Host administration and local recovery interfaces

Date: 2026-09-10. Status: accepted owner requirement; initial implementation with
workstation tests. Production service and board integration remain incomplete.

## Requirements

Ordinary owners must be able to administer OS images, updates, additional software
and host configuration without Linux commands. Recovery must offer an independent
HDMI interface usable with touch alone, keyboard alone, or keyboard and mouse.
These are first-release acceptance requirements, not optional documentation aids.

## Decision

Use Debian's Cockpit web service and privileged bridge for browser authentication,
TLS/session handling and administrator authorization. Add the `sv08-host` package
through Cockpit's supported package API. Its JavaScript calls one fixed Python
helper with bounded JSON on stdin. It never builds shell commands from UI input.
A generic PackageKit update button cannot implement our A/B, idle-admission and
customization policy, so OS/package writes use project operation adapters.

Use GTK 3 for the independent recovery screen. Native buttons, selections and
confirmation dialogs support touch, keyboard focus/activation and mouse input.
The recovery image needs its own display/input libraries and drivers; it must not
load libraries or a browser from damaged A/B roots. This avoids making a full web
browser part of the recovery closure. The complete GTK/X11/kernel/firmware closure
must still fit the 512 MiB recovery partition; source/assets size is not that proof.

Both interfaces use a finite status → review → apply contract. Reviews identify
the action and arguments and are bound to a state revision. Mutations recheck the
revision under their operation lock. User-selected raw device paths, arbitrary
commands, arbitrary package-manager arguments and automatic formatting are absent.
Unavailable operations include a reason. UI refresh or page load never installs,
reboots, changes a mode or declares a release healthy.

The host controller uses the existing persistent state registry. The image adapter
uses the existing private upload lease, signed-bundle verifier, device backend,
transaction journal and atomic idle admission. A browser click is not evidence
that a printer is idle. Staging and selection remain separate, and selection does
not reboot. Existing customized images remain protected.

Recovery's controller operates without a healthy/writable state registry. Its
basic inspection reads state without creating a lock or initializing missing data.
Actual boot selection, signed restoration and export require an independently
verified recovery adapter, with explicit target identity. The host backend's
assumption that an A/B root is running must never be bypassed to make it work in
recovery. A replacement adapter must validate its own running recovery medium.

## Product scope and remaining integration

The browser page includes overview, images/updates, additional software, host
configuration and recovery guidance. Policy changes and next-boot host naming are
implemented. Image stage/arm/cancel are connected at the adapter level; reviewed
board configuration is required before enabling them. The initial software catalog,
network provisioning and actual recovery write/export services remain unavailable.
The [implementation matrix](../hardware/host-admin-ui.md) distinguishes each status.

Before activation, integrate persistent owner accounts, credential reset/pairing,
TLS certificates and LAN access policy with Cockpit. Do not enable a network login
service with a shipped/shared password or clone private keys. Preserve that identity
across both OS slots. The fixture's browser bridge is excluded from production.

Complete authenticated, bounded image upload with progress and signature errors;
reviewed additional-software install/remove/dependency previews; writable-mode
package admission; customization reconciliation; and job progress/history that
survives browser disconnects. Network settings need rollback if a change loses
connectivity. General reboot/service controls must share printer-idle admission.
Do not ship unguarded stock storage/PackageKit controls as the appliance workflow.

Recovery needs signed images from USB and/or LAN, target-specific review, bootable
slot selection, export of readable files, progress and failure diagnostics. Avoid
free-form typing in the basic USB recovery path. Add an on-screen keyboard for
network/credential entry if those workflows require text. Storage repair and OS
restore must not silently format data or restore factory calibration over user data.

## Provenance, upstream use and retirement

Original code fills the project-specific transaction/persistence/UI gap; no
upstream checkout is modified. Reuse upstream Cockpit authentication/bridge and
GTK controls. Retire adapters or UI portions when supported upstream components
provide these same admission, state and recovery semantics. Preserve regression
cases for cancellation, stale review, corrupted state and print/update races.

Primary references accessed 2026-09-10:

- [Cockpit package manifests and API](https://docs.cockpit-project.org/cockpit-guide/362/guide/packages.html).
- [Cockpit process spawning and privileged bridge](https://docs.cockpit-project.org/cockpit-guide/main/guide/cockpit-spawn.html).
- [Cockpit PackageKit operations](https://docs.cockpit-project.org/cockpit-guide/360/guide/feature-packagekit.html).
- [GTK 3 native widgets](https://docs.gtk.org/gtk3/) and
  [key bindings](https://docs.gtk.org/gtk3/key-bindings.html).

The local selected Debian/security snapshot resolves Cockpit to
`337-1+deb13u2`; this is package-intake evidence, not a claim that the login/bridge
has been exercised on the target image. Pin and measure its entire dependency
closure during the next baseline build.

## Subsequent export implementation

2026-09-11: the [export implementation](../hardware/host-recovery-export.md) now
provides reviewed destination selection, bounded PAX archives, checksummed readback
and no-replace publication. It has native UI and read-only-source/FAT filesystem
tests. Its mandatory media admission callback must be supplied by the independently
verified recovery mount provider; no production USB discovery or hardware identity
is inferred from these tests.
