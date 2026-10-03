# Installed checks — 2026-10-03

Status: healthy normal restart and relay power-cycle acceptance passed; current
two-MCU identification and independent final delivery review remain pending.
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

## Environment repair and first restart

The independent software and high action reviews passed. The exact two-file
repair was installed, the original failure archived byte-exact with an explicit
resolution receipt, and the corrected helper invoked once. It succeeded: selected
A3/B0, original selected bank preserved exactly, all selected non-counter values
unchanged, root ro and masks intact.

One normal restart reached Linux and SSH with a new boot ID. The eMMC was
renumbered from mmcblk0 to mmcblk1, with the same measured CID/controller and
persistent partition identities. The helper refused before its writer because
its configuration incorrectly bound the old boot-local device path. The original
observer made the same assumption, so its 120-second check could not report health
even after SSH returned. This was not failure to boot or loss of access.
A2/B0, both CRCs, root ro, public SSH identity and persistent marker were observed
on the new boot. The new failure record is retained; no relay cycle has run.
A bounded repair now binds the stable controller alias and CID while checking
current device/sysfs/partition identity on each boot. No kernel or bootloader
change is planned. Another reviewed confirmation/restart acceptance is required.

## Stable-device repair and successful restart acceptance

The independently reviewed repair now binds the eMMC controller alias and CID,
resolving its current Linux device number at each probe. The second normal
restart passed automatic boot confirmation, followed by one HW-667 power cycle
with five seconds off. Both returned to slot A with A3/B0 and valid redundant
environments. The relay boot enumerated the same eMMC as mmcblk2, exercising the
repair against another device number. Non-counter environment values, persistent
state, marker, SSH public identity and TLS fingerprint were preserved. Root and
boot stayed read-only; data stayed writable; all seven diagnostic service masks
and inactive printer configuration were preserved.

Actual browser login, administrator elevation, connected host status, demotion,
logout and relogin passed after each successful restart. The simple account
password and branding persisted. The existing stale authorization notice and
unavailable image-staging backend remain limitations. Totals are two normal
restarts (the first exposed the repaired defect) and one relay cycle. No MCU
communication has yet occurred in this acceptance run.

Full post-cycle hashes of boot B, root B and recovery match the pre-install
baseline. Fresh installed tool/dependency and controller/CID/GPT/partition checks
passed against the currently enumerated eMMC.
