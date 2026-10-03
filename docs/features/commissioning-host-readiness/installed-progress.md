# Installed checks — 2026-10-03

Status: in progress; restart acceptance is paused for a diagnosed helper defect.
Board H616_JC_6Z_V1.2 is owner-reported. The owner reconfirmed PSU off,
USB power through HW667, Ethernet, spare eMMC installed, SD removed,
factory eMMC stored and no new irreplaceable spare data.

The separate [action review](reviews/20261003-installed-action-review.md) passed
with conditions; actual GPT-6.1 Sol/medium and full-role loading were verified.
All six exact action bindings and fresh target/preimage/idle checks passed.
The 12-file overlay and requested account password were installed, all file
hashes/modes/ownership and dependency/tool closure checked, and root restored ro.
No password or password database is included in repository evidence.

The first health invocation refused before its environment writer: selected
bank matches fw_printenv, but the older bank has different non-counter variables
saved during boot. Both complete bank hashes still match their preimages.
The earlier claim that both logical environments agreed was incorrect. The
same-boot failed-or-unknown diagnostic is preserved. No retry, reboot, relay
cycle or MCU communication has occurred. Repair must preserve the actual selected
bank and all its non-counter values, and must receive independent verification
and a new exact action review including explicit failure-record reconciliation.

Cockpit's previously failed socket also required reset-failed and start after
the TLS path repair. Actual Chromium authentication, administrator elevation,
Host connected status, Stop administrator access, logout and relogin passed.
Login and host branding are present at 1024×600 and 1440×900. The historical
page retains a stale authorization notice after elevation; status and authority
are correct. OS image staging remains explicitly unavailable until the normal
backend is integrated. This is not an installed update/release qualification.
The served SSH public key matches its persistent public file. TLS public
fingerprint was recorded privately. Restart persistence is still untested.

Evidence receipts below bind ignored coordinator observations, not synthetic
fixtures. Credentials and raw environment copies are excluded.
