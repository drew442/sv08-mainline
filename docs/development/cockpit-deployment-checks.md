# Cockpit deployment acceptance

The 2026-10-11 investigation found two boot ownership regressions: privileged
hardware state and published managed configuration were assigned application-user
ownership. Static hashes and a working HTTPS login page did not detect them.
[Investigation and measured repair](../features/cockpit-installed-readiness/evidence.md).

Changes to the ownership/status runtime and its tests trigger
[the real-ownership CI job](../../.github/workflows/cockpit-readiness.yml). It runs
both suites as root in private disposable storage and fails on any skipped test.
The regression requires hardware loading and repeat managed publication after
boot permission preparation and a copied/confirmed generation, preserving saved
bytes and the fallback. It does not run a device or approve a flashable image.

For a deployment, the coordinator must:

1. Record the source revision, exact compiled asset manifest, current installed
   preimages, saved hardware summary and rollback route. Preserve existing work.
2. Execute only the authorized change, recheck every deployed hash, and restore
   the original root mount mode. Do not activate printer services for a UI check.
3. Run [the installed functional checker](../../scripts/check_installed_cockpit.py)
   as administrator on the printer, with the compiled manifest and prior readiness
   receipt. Require exit zero and `passed: true`. Retain its nonsecret receipt.
4. Verify authenticated rendered interaction for changed user journeys using
   existing authorized authentication. If that evidence is unavailable, say so;
   do not treat a login page, asset hash, backend response or an empty fixture as
   proof that those interactions work with the owner's configuration.

Example after transferring the script and nonsecret manifests/receipt:

```sh
sudo python3 check_installed_cockpit.py --manifest manifest.json --baseline previous-readiness.json
```

The checker probes hardware, updates, software, network, identity and Mainsail
status, inspects hardware/managed ownership, and compares the prior hardware
summary. It reports only counts and booleans. It sends no apply, network-change,
identity-restore, service-start or reboot RPC. Status helpers may acquire normal
locks or initialize metadata. A failure stops a usable-deployment claim; diagnose
it, preserve data and reconcile or restore the exact authorized rollback rather
than suppressing the check. Initial unconfigured installations may legitimately
have zero devices/sources; an existing configured installation must not silently
be accepted as empty. Matching summaries alone do not prove byte preservation;
retain exact protected-state hashes when repairing stored metadata.

This supplements existing admission and operation requirements. It does not grant
printer authority, require an unnecessary reboot, or replace independent assessment
before a consequential operation. Physical boot, printing, full UI usability and
certificate-trust qualification remain distinct evidence.
