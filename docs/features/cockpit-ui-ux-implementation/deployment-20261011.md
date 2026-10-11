# Cockpit UI deployment — 2026-10-11

Owner requested deployment after completion of the UI workplan. Deployed source
`85ec06cf2b4d696dda61ffa8ed0d8ee55667ca5d` to `sv08@192.168.1.141`.
[Exact hashes and final checks](deployment-20261011.json) record 14 static files,
247,034 bytes, including host HTML compiled using `compose_host` and the matching
printer panel/assets. Current root is `/dev/mmcblk1p4`; no slot update was performed.

The coordinator recorded exact file type, mode, owner and hash preimages plus boot
identity, rechecked them before mutation, retained a rollback archive, replaced
assets atomically per file with the host entry page last, checked every afterimage,
then synced and restored root read-only mode. The original UI is retained at
`/data/sv08/system/ui-deployments/20261011-85ec06c/before.tar`, with preflight,
manifest and result records beside it. Temporary deployment packet was removed.

Cockpit was inactive. Starting its existing socket activated its configured identity
and account dependencies; HTTPS subsequently returned the Cockpit login page with
HTTP 200. Final installed hashes match, boot identity is unchanged and root remains
read-only. Klipper, Moonraker and nginx remain inactive. Their existing masks were
not changed. No reboot, backend replacement, printer configuration write or output
activation occurred; inactive slot and recovery were not modified.

HTTP connectivity was checked with TLS verification disabled. No certificate-trust
or authenticated physical-browser acceptance is claimed; protected asset requests
returned 401 without authentication. A supplementary package-list parser expected
JSON but received another format and failed; it supplies no package metadata proof.
The implementation's separate disposable authenticated ARM64 evidence remains the
UI acceptance evidence. Reload/sign in at `https://sv08.drewnet.online:9090/` to use
the deployed interface.
