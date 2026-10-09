# Mainsail access acceptance — 2026-10-09

Direct owner request implemented with a dedicated Cockpit Mainsail access page.
Password remains the default, no login needs an explicit reviewed selection, and
CA-signed client certificate generation/download is separate from activating it.
Cockpit/SSH access and native loopback Moonraker credentials remain independent.

## Source and browser checks

- `python3 -m unittest discover -s tests -p test_mainsail_access.py -q`: 15 passed.
  Covers real encrypted PKCS12/clientAuth signing, native secret preservation,
  denied/expired/revoked modes, bounded parsing/storage, corrupt or missing policy,
  accepted publisher reconstruction, symlinks/permissions, and transaction
  validation/reload/publication failures and interrupted commit recovery.
- Existing web stack: 16 passed. Host integration: 3 passed. Admin UI staging:
  18 passed. Printer stack: 7 run, two existing pinned-parser environment skips.
  Identity regression: 16 run, one existing privileged SSH environment skip.
- `test_mainsail_access_ui.py`: one mocked Chromium journey passed. Actual private
  file download, all three choices, explicit review/cancel, password matching,
  generation without activation, revoke/list/expiry, authority restoration warning,
  privilege/navigation epochs, stale responses, remote HTTP refusal and narrow views.
- Complete stable source diff and `git diff --check` inspected. Staging copies the
  module through the existing runtime glob and verifies matching host RPC modules.

## Real ARM package fixture

An isolated mount/network/PID namespace used the existing non-deployable ARM root
with pinned Moonraker 985c1d0, nginx 1.26.3, Python 3.13.5 and OpenSSL 3.5.7. No
hardware devices, external network, systemd boot or production state were used.
Fresh persistent CA/SSH and native accounts were generated in disposable storage.

Static/API/WebSocket returned 200/200/101 for original and changed passwords;
old/anonymous passwords were rejected with 401. Explicit no-login returned
200/200/101. Imported client key/certificate returned 200/200/101; missing client
certificates and a password bypass attempt returned 400. Revoked certificates
returned 403 on all three routes. Certificate access survived actual nginx restart
and web prepare/auth; switching back to password worked. Native credential file,
proxy key and account DB bytes remained unchanged; anonymous direct API stayed 401.
Actual root RPC envelope passed. Strict TLS verified the generated server against
its fixture CA; exported PKCS12 was opened with the supplied password.

The fixture caught an ARM nginx default map bucket of 32, insufficient for client
fingerprint keys. The final implementation explicitly sizes it to 64; final exact
source fixture passed. Earlier runner input plumbing and parser failure receipts
were retained privately. Final receipt SHA256:
`da93c50eb52ff6cc557dcf870f165a25d60f95ff6f5d775015e8a430efbd9735`.
Three final child processes exited zero; all mounts were removed. Primary fixture
budget was 900 process seconds; final run 114.814 seconds and preceding runs about
200 seconds combined, below allowance. This is package integration evidence, not
printing or release qualification.

## Named diagnostic installation

The exact six-file operation was installed on diagnostic `test-sv08-01`, boot
`b1fbaf69-26b9-4f1d-a4e8-369b61ff563f`, with PSU OFF. Fresh target/preimage
admission passed. The operation installed source/UI only and retained existing password mode. It restarts no services, reboots nothing
and changes no hardware. Independent fixed-role high-consequence reviewer assessed
secret/access and rollback boundaries, including exact composed Cockpit HTML. Its
packet SHA256 is `8429493f4aa0569eba83cb93937bdf3db7c8ddea035d22bc5e1d5b5a4fa53c9d`;
installer `eb7abe5fc693aece7c8e02752c6972f3a84f17701adca33a70ee932dca80110b`;
passed decision `e9b77899d5c790efe8d712a5a36fce55c4d824e147fc7ca5599400f896fe802a`.
Actual HTTPS Cockpit PAM/sudo opened the installed page, showed all three choices,
and cancelled a password review without changing access state. Widths390/1024/1440
fit. Strict printer CA verification passed for Mainsail and Cockpit; native Chromium
Mainsail password, API and WebSocket authentication passed. Installation preserved
34 named hashes (including hardware selections, generated configuration, native
credentials and boot dependencies), original CA/SSH identities, masks and no MCU
file descriptors. Root/boot remain read-only and data writable. No private client
certificate was generated or access mode changed on the physical printer.
The coordinator retained printer authority and actual pre/post observations.

## Limits

Client certificate private keys are downloaded once, not part of printer identity
backups. Browser/OS certificate import is performed by the owner; automated TLS
clients and mocked browser downloads were tested. A graceful reload blocks revoked
certificates on new connections; established WebSocket streams can remain until
disconnected. The feature does not commission Klipper or qualify physical printing.
A separately registered small integration task exempts this independent page from
unrelated host image-operation error button disabling. Identity schedule is unchanged.

Implementer role model pins and requested medium backend/low UI effort were recorded;
independent reviewer profile pins GPT-6.1 Sol/medium. Runtime billing/effort telemetry
was unavailable; source profile and tool routing are not native isolation evidence.
