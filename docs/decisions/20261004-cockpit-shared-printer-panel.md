# Shared Cockpit printer configuration panel

Date: 2026-10-04. Status: approved; implementation and installed acceptance pending.

The [owner correction](../features/printer-cockpit-integration/owner-request.md)
requires Printer hardware to behave as a section of the existing Cockpit
interface. Matching colours on a separate page did not meet that requirement.
The [bounded proposal and acceptance checks](../features/printer-cockpit-integration/proposal.md)
passed independent approval in the adjacent record.

Keep the selected `sv08-host` shell and Cockpit337 authentication/privileged
bridge. Compose one persistent printer panel into that document; share its
navigation, branding and session controls. Keep the finite printer package as an
internal asset/helper boundary, with a compatibility redirect for the old URL.
The panel has namespaced IDs and scoped layout styles. Section changes retain
local drafts and invalidate pending confirmations; delayed or unacknowledged
writes require explicit reconciliation, never automatic replay.

This supersedes only the previous component decision's separate-page navigation
architecture. Backend/catalog/generation/persistence and inactive-candidate
requirements remain unchanged. No additional runtime dependencies or upstream
modifications are needed. Retire the local composition/navigation adapter if an
upstream extension mechanism meets the same appliance and draft-lifecycle needs.

Fresh staging and historical installed overlays must use deterministic finite
composition. Patch only reviewed navigation/control-isolation boundaries in the
historical host assets; do not replace them with current host/runtime code.
Installation requires exact preimages, retained originals, readback, restoration
of root read-only, and separate action/delivery reviews. Physical commissioning
and release remain separate.
