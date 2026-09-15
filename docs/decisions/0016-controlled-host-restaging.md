# 0016: Controlled restaging of a copied diagnostic host root

Date: 2026-09-15. Status: accepted for non-deployable diagnostic-image
construction only.

## Context

The first complete board diagnostic root was finalized before the persistent
owner SSH-key initializer was corrected. Its source root is evidence for the
first composition and must remain unchanged. Rebuilding every pinned board
package merely to incorporate a reviewed runtime/UI correction is costly and
increases the chance of changing unrelated package state. A replacement root
still needs an explicit, fail-closed construction procedure rather than an
unreviewed in-place copy.

## Decision

Allow `integrate_host_os.py --refresh` and `stage_admin_ui.py --refresh` only
on a fresh private copy of a completed, reviewed host root. The normal command
continues to reject an already staged target. Refresh accepts only the regular
runtime directory, its two expected command symlinks, the expected host UI
directory, and regular UI configuration outputs. It rejects symlinks,
unrecognized commands and unexpected Cockpit packages before deleting the old
runtime or UI directory.

The copied root receives a new private finalization receipt and a new complete
disk composition. It never alters the original root or its receipt. The feature
does not authorize an eMMC write, a live-host change, package installation,
service activation, kernel/bootloader replacement, or a deployable release.

## Validation and retirement

Unit tests prove a recognized runtime/UI refresh removes stale project files,
seeds the owner key, and refuses an unexpected command before removal. The
normal construction still performs initramfs regeneration, package and
filesystem checks, a new inventory receipt, and complete-image byte review.

Retire this narrow refresh path when the release builder can reconstruct every
host artifact from pinned package inputs within routine build time. Until then,
use it only for a documented reviewed runtime/UI correction with a preserved
source root and a new independent artifact review.
