# Installed commissioning host intake — 2026-10-03

Goal: a dependable installed host ready for sensor-only commissioning, following
completed H12. This is not physical sensor, printer or release qualification.
Target: test-sv08-01, H616_JC_6Z_V1.2 host marking owner-reported. The spare eMMC
identity/controller agrees with the completed H12 write/boot record. Other board
revisions and sensor circuits remain unverified.

## Fresh coordinator observations

Authenticated SSH at 10:52 UTC found the same boot as H12 completion, kernel
6.18.51-sv08-candidate1, slot A, read-only root and writable /data. Persistent state
contains one immutable A generation, no pending trial and no update journal.
Installed release is 0.1.0-board.3 with deployable=false. No RAUC system config,
reviewed backend layout/environment inputs or fw_env.config are installed.
RAUC, boot health and all printer services remain masked in the kernel command
line. No printer.cfg is present. No failed unit appeared before testing HTTPS.

Read-only identity-bound environment inspection found both 65,536-byte copies
valid at the documented 4 MiB and 8 MiB offsets. Flags are 1/2. Both select A only,
B attempts zero, layout ab-8gb-v1; A attempts are 3/2 respectively. The newer copy
agrees with one consumed successful boot. No write or reset was performed.
Unmasking the existing health coordinator alone does not resolve this ordinary
nontrial boot's finite attempts: its idle path does not invoke trial mark-good.

Cockpit's socket is active. Actual HTTPS failed; the journal identifies certificate
publication under read-only /etc/cockpit/ws-certs.d. The supported persistence
link/directory from the accepted TLS correction is absent. The SV08 Cockpit page
is installed at /usr/share/cockpit/sv08-host, but admin-context.json is absent.
The sv08 account has a locked password and working owner-key SSH; actual browser
login remains unproved. No credential material was read or published.

The installed Klipper package is 0.0+gitf0892d82-1, consistent with the retained MCU
build revision. Only the mainboard-associated USB identity is currently enumerated.
Toolhead availability and both current firmware identities are not yet established.
The last owner-reported PSU state is off; do not infer the missing device's cause
or ask for flashing without evidence.

## Execution and next steps

Native planner launch failed with the thread limit. A separate full-role planner
session 01a10163-bc3e-70f0-b952-b36e29f9c12f ran verified GPT-6.1 Sol/medium,
full access/never. Source diagnosis of the narrow normal-boot policy gap uses a
separate full-role Sol/medium researcher. Neither accesses hardware or publishes.
Coordinator retains physical operation and Git ownership. Existing TLS, boot-health
and UI approvals are reused; new ordinary-boot semantics need bounded independent
approval. Exact changes to eMMC/boot policy need fresh independent action review.

Private raw observations and selected non-secret installed source copies are under
local/feature-workflow/probes/commissioning-host-20261003. No physical write,
reboot, MCU session, heater or motion has occurred for this goal. H12's abandoned
and deferred components remain excluded.

## Installed file-output configuration check

The installed ARM64 Klipper package passed dpkg file verification (no mismatches),
reports full source f0892d82b0f1c1228454f09eb508eddde2250f4b in its package manifest,
and its prebuilt helper SHA-256 matches the retained MCU/host build evidence.
A temporary /run fixture combined the communication-only template, temperature
include and empty-action input include, with the retained per-machine by-id mapping.
The current installed Python/host/helper configured both matching firmware
**dictionary fixtures** and exited zero in Klipper file-output mode. No serial
connection, MCU configuration, heater or motion command was issued. Device presence
and current MCU firmware still require separate live reconciliation.
The private packet remains inactive; no printer.cfg was installed in the active
generation and printer services remain masked.
