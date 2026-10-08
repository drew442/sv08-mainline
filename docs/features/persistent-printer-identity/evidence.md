# Persistent printer identity — delivery evidence, 2026-10-08

The owner-requested identity features are implemented and installed on
**test-sv08-01**. Cockpit's **Printer identity** menu downloads the persistent
public CA, manages the `sv08` account's trusted SSH public keys and reviews private
identity ZIP download/restore. See [usage and storage](../../hardware/printer-identity.md)
and [the owner policy](owner-request.md).

## Source checks

- Focused identity/boot/admin/recovery/integration/printer-stack regression:
  `PYTHONPATH=tests:runtime:scripts python3 -m unittest tests.test_identity tests.test_host_boot tests.test_stage_admin_ui tests.test_sd_recovery_host tests.test_recovery_image tests.test_host_integration tests.test_printer_stack`:
  **80 run, 77 passed, 3 skipped**. Root SSH acceptance ran separately below;
  printer-stack skipped checks retain their existing environment requirements.
- After complete host-button isolation: `PYTHONPATH=tests:runtime:scripts python3 -m unittest tests.test_identity tests.test_stage_printer_ui tests.test_stage_admin_ui`:
  **44 run, 43 passed, 1 root-only skip**.
- `sudo -n env PYTHONPATH=tests:runtime:scripts python3 -m unittest test_identity.IdentitySSHIntegrationTests`:
  **1 passed**. Real sshd/client in private mount/PID/network namespaces accepted,
  rejected and restored public-key access with the same host identity; real PAM
  accepted recovery/recovery. No host accounts, services or devices were changed.
- `node tests/identity_browser.mjs`: real Chromium and real Identity backend with
  simulated Cockpit transport passed CA/key uploads/downloads, export, malformed
  bundle refusal, preview/cancel/restore, authority-loss cancellation and
  390/1024/1440px layouts. This fixture is not a native Cockpit authentication claim.
- After nginx boot dependency integration, `PYTHONPATH=tests:runtime:scripts python3 -m unittest tests.test_host_integration`:
  **3 passed**. SSH/nginx depend on identity preparation; Cockpit socket startup is
  similarly ordered. Timer checks renewal without activating printer services.
- Python compilation, JavaScript syntax and `git diff --check` passed.

Cryptographic tests use native OpenSSL/ssh-keygen and a real TLS client. They prove
stable authority through leaf replacement, complete bounded ZIP/key validation,
atomic selection, injected failure/no-space refusal, stale revision refusal,
permission checks and explicit recovery of corrupt authority without regeneration.

Earlier failures are retained in private execution records: an invocation omitted
`tests` from PYTHONPATH; the old key-only recovery assertion conflicted with the
new owner policy; ambient umask made the CA certificate group-writable; a private
fixture parent and namespace `/run` permissions prevented the test SSH account
from traversing its keys. Each cause was corrected before the passing results.
Host-wide error handling was also isolated from identity controls. These were
not counted as passing attempts.

## Installed acceptance

The independent exact-operation assessment passed with bounded execution
conditions. Role configuration declares high_consequence_reviewer,
`gpt-6.1-sol`/medium; runtime model/effort introspection was unavailable and is not
claimed. No reviewer printer access or experiments were performed.

Reviewed installation script SHA256:
`15ecb85f470fd1dda4d7517b3bf79ce4561741b02827fd76b5cef00571aed52b`.
Packet SHA256:
`51c887b3d6a7f876c35ce2e168f1ef5119d7556b0716ed0510af4f6fe38a1a5f`.
Review report SHA256:
`b8285b194d9cd368ee8ac39f201692153bbc61422a9a2792a25f17837ad1f7aa`.
The discovered rollback edge was corrected: the newly published Cockpit certificate
hash is captured immediately around publication before authority assertions.

Fresh admission verified the powered-off printer PSU, exact running boot and
managed configuration, production masks/inactivity and owned temporary web/API
units. Root was writable only while allowlisted files were installed and returned
read-only; boot remained read-only. Durable private preimages, legacy SSH files
and old TLS certificates remain available. A separate SSH session was retained
through fresh reconnect. Installed old app/index bytes received narrow identity
additions rather than unrelated newer history-maintenance behavior.

Actual Cockpit HTTPS/PAM/sudo browser acceptance passed:

1. Download the public CA; review/cancel then download the private identity ZIP
   into a private local directory/profile, never a public artifact.
2. Upload a disposable public client key, cancel without changing revision, then
   confirm. A real external SSH connection using only that key authenticated.
3. Upload the downloaded baseline ZIP, inspect matching CA/SSH fingerprints,
   cancel without mutation, then confirm restore.
4. Restore returned the original trusted-key list; the disposable key was rejected,
   and the original owner key reconnected using the original host identity.
5. Cockpit and Mainsail both served different replacement leaf certificates that
   verified using the **original unchanged CA file**, including IP-name validation.
   The downloaded CA bytes matched the active authority.
6. A fresh authenticated Mainsail browser initialized completely, connected its
   websocket to Moonraker `985c1d0`, and retained the intended Klipper-disconnected
   state. Unauthenticated HTTPS/API/websocket requests remained challenged.

Public identity after restore:

- CA SHA256: `d103ff93f8a16cb3c39a4b61d097dc794bbb071ac34ba51fdd02e89b2e70aeaf`
- SSH fingerprint: `SHA256:76y9QdGAfX0+DOKcexTyVWyaKqJGBBcBLkt63ohj7wU`
- Original leaf SHA256: `7c53c1c7555d8a789954e2872074a9c432f7d1bf3f3c27d249cf1495c2c29efb`
- Replacement leaf SHA256: `ef7bed120fa82739f2e21285d123c616c145b0c19d847f3f8b832e5ad3392e56`
- Hardware state SHA256 remained:
  `3141fd19d4b4ad03af96c23fe2d3bd78efd01335191225baf9c6556a94078a39`.

Installed small-screen checking found the older stylesheet preserves code text
as unbroken lines. Cockpit also blocks parsed inline style attributes. The initial inline correction
had no effect; trusted CSSOM properties now wrap both fingerprints and size the
editor/review. Source and installed UI are corrected without relaxing CSP.
Fresh actual Cockpit acceptance passed at **390/1024/1440px**, with matching CA/SSH
fingerprints and healthy identity after restore. Private preimages and root
read-only state are retained. The source browser fixture enforces the same
style-source restriction and terminates its own Chromium process group before removing its private
profile. Earlier cleanup races were not counted as successful test exits. The
final CSP-aware fixture run passed and exited successfully.

Private execution records are under the ignored
`local/feature-workflow/probes/persistent-printer-identity-20261008/` directory.
They include original failed/passing results and exact installed payload hashes.
Private certificates/keys, backups, credentials, session material and dumps are
not committed or published.

## Completion boundaries

The [host task list](../../hardware/host-os-tasks.md) marks persistent CA/service
trust, persistent SSH identity, Cockpit public-key management/identity backup and
source recovery-password policy complete. Broader onboarding/network provisioning,
release-image fit, A/B/recovery boot and physical printing remain open.

No recovery media were rewritten. Recovery/recovery is verified in source and
isolated real PAM/SSH; it is not a claim about an already-built physical recovery
image. CA keys and SSH host authority persist under `/data`; replacement of that
storage needs the exported backup. Twenty-year CA expiry is documented; routine
renewal replaces service certificates only.

The current diagnostic host keeps production Klipper/health/RAUC services masked,
PSU OFF, no MCU session and unchanged hardware configuration. Existing Mainsail/API
availability remains the separately installed temporary diagnostic service
composition; this delivery does not qualify a normal printing boot or release.
