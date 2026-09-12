# host-admin-cockpit-integration: exercise the actual authenticated host console

Kind: feature. Author: cockpit_intake_review. Date: 2026-09-12.

## Problem and evidence

The existing host page has controller/browser tests behind an explicitly test-only
bridge shim, but no actual Cockpit login/administrator bridge evidence. Accepted
[decision 0010](../../../docs/decisions/0010-host-administration-and-recovery-ui.md)
requires Cockpit authentication, authorization, supported extensions and guarded
appliance operations. Current `scripts/stage_admin_ui.py` stages the project page
without configuring a top-level shell. `configs/host-os/admin-ui.json` selects
cockpit-ws and cockpit-bridge; neither package's extracted manifest supplies a
privileged bridge configuration. In packaged 337, normal bridge startup obtains
these definitions from package manifests (`cockpit/packages.py:get_bridge_configs`);
`cockpit/superuser.py:SuperuserRoutingRule.apply_rule` rejects required privilege
when no elevated bridge is active. This is a concrete integration prerequisite,
not an observed target failure.

Read-only intake used selected snapshot `20260901T000000Z`, Cockpit
`337-1+deb13u2`, with URLs/hashes in ignored
`build/cockpit-intake-337/intake.json`. Debian archive SHA-256 values are
`8caa8c3f36d6eb2f95561614923518bc6e78d17962673d5be3d43b1967dc4961`
(cockpit-bridge all) and
`4af22eab0c00d741ee976f1f8cf71a33f2709242ee81be19933ee1fd592202b9`
(cockpit-ws ARM64). Extracted `ws/usr/share/man/man5/cockpit.conf.5.gz`
documents `[WebService] Shell=/sv08-host/index.html`. The extracted base1 API
implements binary spawn input and streamed output, but input has no drain promise.
The root coordinator reports an APT simulation resolving nine new packages and no
upgrades against the selected baseline; no package installation has occurred.
Preserve the actual simulation and resolve/hash the full closure during delivery.
Access date for these packaged primary sources: 2026-09-12.

## Intended outcome

After `host-admin-image-jobs:implement`, a fresh disposable image root can stage
and run the selected real Cockpit login/session/bridge stack with the SV08 page as
its shell. A synthetic administrator completes a reviewed helper operation;
invalid credentials fail and a non-administrator cannot perform privileged
operations. Logout and reconnect behave explicitly. Package and isolated runtime
evidence replace assumptions currently hidden by the shim.

This bounded integration precedes browser upload because upload needs verified
real session authority and transport. Authenticated bounded upload remains the
next feature; no upload implementation is included here. This is completion of
existing accepted administration requirements, with no new owner decision.

## Scope and alternatives

Include selected package closure provenance, hashes and footprint; supported
Cockpit shell configuration; an explicit reviewed privileged bridge manifest using
the selected upstream mechanism; session/logout and administrator-access UI where
needed; isolated staging and actual browser/login/bridge tests. The exact selected cockpit-system archive was also extracted, not installed, with
SHA-256 `309f12329a15cf5f465e8f8f328c70a1c24078637bb0e8334c10d88aad274c11`.
Its `system/usr/share/cockpit/shell/manifest.json` supplies the upstream sudo bridge
stanza: `spawn: ["sudo", "-k", "-A", "cockpit-bridge", "--privileged"]`, with
`SUDO_ASKPASS=${libexecdir}/cockpit-askpass`. Reuse only this supported declaration
with provenance; do not ship the stock shell or change sudo grants. The second
pkexec declaration is optional and its prerequisites are absent from the baseline.
The packaged shell uses the internal `cockpit.Superuser` proxy at `/superuser`;
selected Python code exposes Start/Answer/Stop, Prompt and Current/Bridges/Methods.
Use this selected-version bridge-state handling for prompts and cancellation,
without persisting secrets or inventing another authentication mechanism. Record
the exact packaged shell.js and Python source hashes for this internal API. If
the expected API is absent or incompatible, refuse elevation with a clear
diagnostic; do not fall back to weaker authorization. Clear password inputs and
in-memory prompt state after use/cancel/failure. Never put secrets in storage,
logs, URLs or evidence; authentication cannot confirm a pending operation review. Do not pull in the Cockpit
metapackage or ship unrestricted stock storage, PackageKit, terminal, reboot or
service controls. A custom shell routes ordinary use; it does not redefine the
security powers of an account already authorized as administrator.

Use one disposable overlay/copy of `build/host-ab-baseline-v1/rootfs`, with private
mount/PID/network namespaces, private runtime/state directories and synthetic
accounts. Preserve the source root and exclude printer devices, private backups,
real accounts/credentials and external network access. A candidate lightweight
session route is packaged cockpit-session behind systemd-socket-activate's
accept/inetd mode at `/run/cockpit/session`, with actual cockpit-ws on namespace
loopback and a browser joining that namespace. Validate PAM/session requirements;
provide private D-Bus/logind/systemd if needed. Never use `--local-session` to claim
authentication coverage: the packaged manpage says it skips authentication.
Any test-only service launch belongs entirely to the disposable environment.
The first milestone is actual login → elevation → uid proof before UI polish. If
namespace/chroot PAM or setuid execution cannot preserve the real semantics, a
fully disposable QEMU guest is an allowed fallback. Never weaken PAM or use
authentication bypasses to obtain a passing result.

Exclude production owner onboarding, credential resets, persistent account/TLS
identity, production network activation, deployment, printer connections, hardware
writes, upload, package-management UI, and target release certification. No source
root modification, host-wide package install, upstream modification or bundled
installer. Loopback HTTP may establish isolated PAM/bridge behavior but must be
labelled as lacking production TLS activation evidence. Packaged service unit
validation and any real service-manager execution must be reported separately.

Custom additions are limited to the project shell's missing session integration
and reproducible isolated harness. Prefer supported Cockpit manifests/APIs and
standard namespace/systemd tools. Keep regressions and provenance; retire custom
integration when upstream supplies the equivalent bounded appliance contract.
This changes no firmware revision, boot selection, rollback policy or calibration.
Measure host footprint without claiming recovery partition or full disk fit.

## Acceptance and task split

One offline task `implement`, priority 2, depends on
`host-admin-image-jobs:implement`. Separate approver and verifier review required.

- `actual-auth`: In actual selected Cockpit/PAM, reject bad credentials; permit
  synthetic ordinary login but reject required privileged helper requests; permit
  the synthetic administrator through the configured elevated bridge. Prove uid
  behavior without cached sudo credentials. Exercise a wrong elevation password,
  prompt cancellation, successful elevation, explicit Stop and post-Stop helper
  denial. Do not use the test bridge shim or auth-bypass launch flags. Missing
  expected internal API must fail closed with diagnostics; verify secret inputs
  and prompt state clear and no secret reaches browser storage, logs or evidence.
- `helper-session`: Through the actual SV08 shell, status and review perform no
  mutation; confirmed bounded helper apply changes only disposable state. Show
  review cancellation/staleness refusal and prove authentication itself never
  confirms review. After logout, an actual request using the old session must be
  rejected; reconnect must require authentication before reading persisted state. Check image-job status remains
  available through this transport after the prerequisite delivery.
- `package-closure`: Retain selected versions, source snapshot references,
  dependency closure, archive/output hashes and download/installed/root footprint.
  Reproduce resolution with no floating updates; account for any difference from
  the reported nine-package/no-upgrade simulation. Include sudo and cockpit-askpass
  runtime prerequisites; introduce no production sudo grants. A download is not
  compatibility.
- `staging-isolation`: Verify dry-run, expected shell/manifest/helper ownership and
  permissions, and prove excluded stock components are unavailable both through
  direct URLs and package discovery. Preserve any existing cockpit.conf settings
  or reject a conflict explicitly; never silently overwrite them. Check rejection
  of unsuitable/existing staging targets and package service/unit validity against
  the selected root. Verify
  service listeners and synthetic identities stay in the isolated environment;
  baseline/root source and host services remain unchanged after cleanup.
- `regressions`: Run affected controller/image-jobs/staging tests, real browser
  regressions and proportionate foundation checks (diff/cached diff whitespace,
  submodule/indexed-lock agreement, JSON syntax and local Markdown links). Record
  actual execution versus static unit checks and emulation limitations separately.

## Human dependencies

None blocks this offline task. Existing release authority remains the
[host OS task list](../../../docs/hardware/host-os-tasks.md), especially the
Cockpit closure/login/provisioning/TLS and ordinary-administration entries, and
[host UI limitations](../../../docs/hardware/host-admin-ui.md). Do not mark those
combined release items complete from this subset. Production account identity,
LAN/TLS access, assembled hardware and attended printer tests remain there; no
new physical action or owner requirement is introduced by this proposal.
