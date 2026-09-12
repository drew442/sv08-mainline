# 0012: Selected Cockpit session integration

Date: 2026-09-12. Status: bounded implementation of accepted
[decision 0010](0010-host-administration-and-recovery-ui.md), under the
[approved feature proposal](../features/host-admin-cockpit-integration/proposal.md).

The selected ws/bridge packages lack the stock shell's privileged bridge manifest.
Stage Cockpit's supported custom Shell configuration and reuse only the selected
upstream sudo declaration. Do not install the stock system shell or expand sudo
policy. Existing configuration conflicts must be rejected before staging.

The appliance page needs explicit elevation, password prompts, cancellation,
Stop and logout. Cockpit 337's packaged shell uses the internal Superuser proxy;
use that same selected-version interface with expected-API checks and recorded
source hashes. This is a version-sensitive integration, not a stable public API
claim. Missing API or failed Stop closes local operation authority and provides a
diagnostic; Cockpit's required privileged bridge and the helper's effective-uid
check remain the actual authorization boundary.

Authority transitions discard pending reviews. Delayed responses cannot revive
an old review, and authentication never submits an operation. Keep credentials
out of storage/logs and clear prompt fields/state after answer or cancellation.

[Full ARM64 QEMU evidence](../hardware/host-admin-cockpit.md) exercises unchanged
packaged PAM/sudo and actual systemd units. Its synthetic Store and writable root
do not prove A/B mounting, hardware or production account/TLS integration. Retire
or replace the proxy adapter when upstream supplies an equivalent supported
explicit authority lifecycle. Preserve the authentication and transition tests.
