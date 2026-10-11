# Cockpit readiness investigation and repairs

The original defect crossed subsystem boundaries: boot preparation recursively made
config application-owned; privileged hardware storage required root ownership. UI
fixtures exercised the store without that real ownership transition. Native Cockpit
acceptance used empty hardware state, and physical deployment checked static hashes
and an unauthenticated login response, not the saved hardware status. That evidence
was insufficient to call the installed feature usable. The coordinator missed it.

A second demonstrated defect had the same cause: printer-managed was application-
owned, but publication requires root-owned, application-group-readable directories.
Boot preparation now preserves both distinct ownership contracts. Installed managed
ownership was repaired under the Store lock, with all file bytes and modes unchanged.
The corrected module is installed in the current root, with its original retained.
Root remains read-only; no reboot, activation, application or inactive-slot changes.

Eleven boot tests and three readiness tests passed as root, without skips. The new
real-ownership lifecycle exercises current and copied/confirmed generations, saved
hardware status, repeat managed publication, byte preservation and untouched fallback.
The previous boot source fails that same regression at managed ownership; repaired
source passes. Fixture validator remains synthetic, never hardware approval.
Initial fixture ancestry/group/trial-context mistakes and original failed logs remain
recorded; their corrections retain allocation and trial safeguards.

`check_installed_cockpit.py` probes six supported status RPCs, fails on process or RPC
failure (including exit-zero error envelopes), validates expected UI hashes, checks
both managed storage contracts and optionally requires the same prior hardware
summary. It emits counts/booleans, never raw status payloads, secrets or RPC errors.
Status probes may acquire normal locks/initialize metadata; no mutation RPC is sent.

The physical check failed before repair despite fourteen good static hashes and all
six good RPCs, identifying printer-managed ownership. After repair it passed every
check and preserved revision13,24devices,26definitions,1source,current/previous present.
[Exact nonsecret evidence](evidence.json). Private helper responses are not published.

Future deployment acceptance must run the installed command with the compiled asset
manifest and prior readiness receipt, require exit0/`passed:true`, retain results and
compare saved state. A login page, asset-only check or empty/native fixture alone is
insufficient. Example on the printer after transferring this repository script:

```sh
sudo python3 check_installed_cockpit.py --manifest manifest.json --baseline previous-readiness.json
```

This is a functional backend/storage check, not a substitute for browser interaction
checks. Authenticated physical rendering, physical reboot and printing were not
exercised. Broader unrelated UI paths are not claimed defect-free. Root test receipts
and counterfactual logs are under `/home/drew/.sv08-cockpit-readiness-20261011/`.
