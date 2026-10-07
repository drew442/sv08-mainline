# Mainsail authentication repair — 2026-10-07

Owner request: “go ahead and resolve the usable login and authentication mistake”. Source main `3df5d21`; installed Mainsail 2.19.0 at pinned `32f99e1c`, Moonraker `985c1d0`. The preceding [service application](printer-services-configuration-20261007.md) started the web/API services, but its localhost-only trust configuration had no usable browser login. LAN API requests were rejected. Serving Mainsail locally does not make requests from its browser application local requests.

The installed configuration now provides a browser HTTP authentication prompt over HTTPS at `https://192.168.1.143:8443/`. Port 8080 redirects to HTTPS. A newly generated service-specific self-signed certificate covers the two observed printer addresses and localhost; it lasts 365 days. No existing Cockpit certificate or key was read or reused. The owner retrieves username `sv08` and the unique generated password from Cockpit’s authenticated Terminal:

```sh
cat /data/sv08/moonraker-login.txt
```

This retrieval file is mode 0600, owned by sv08. Passwords, tokens, backend API keys and private keys are absent from committed evidence. The TLS and gateway authentication directories are mode 0700; their files are mode 0600. Authentication assets are outside every registered Moonraker file root and the static website. The native Moonraker account and gateway initially share this newly generated password; later password rotation must update both boundaries, rather than assume native Moonraker password changes update nginx.

## Compatibility and access boundary

Creating the native Moonraker account and enabling `force_logins: True` passed authenticated API tests, but a fresh actual browser stalled at “Initializing”. The pinned Mainsail client has no Moonraker login dialog: its `server/init` identifies the client and returns on Unauthorized without a login flow. That failed browser observation led to the compatible gateway repair rather than a claim of success from API tests alone.

Nginx requires HTTP Basic authentication for every HTTPS route, including static files, configuration JSON, API and WebSocket upgrades. Its password file contains a newly salted SHA512 crypt hash. After browser authentication, the API/WebSocket locations supply Moonraker’s existing API key from a private include outside its file roots, and suppress the browser Basic Authorization header upstream. The backend key was used only for this assigned gateway connection; it was neither rotated nor exposed to browser code or committed configuration. Original client-address forwarding remains intact. Moonraker remains bound to loopback port 7125 with forced login; no LAN subnet was added to trusted clients.

The changes use existing packages. Independent medium high-consequence assessments passed with conditions for the exact account/TLS operation and the subsequent exact gateway operation. The first assessment identified unverified TLS in a proposed credential test; certificate verification and proxy bypass were corrected before execution. Review receipts bind exact scripts/configuration inputs. Runtime reviewer model/effort were not independently observable. Reviewers made no printer connections or experiments.

Root-only durable backups preserve the original authentication/proxy configuration. Failure recovery restores admitted original configuration and signals/restarts only the explicitly owned current-boot services. Newly acknowledged account/credential data is retained rather than deleted on a failed configuration step. Both operations completed successfully; recovery was not invoked.

## Observed acceptance

- Certificate-verified HTTPS authenticated HTTP and protected WebSocket calls succeeded. Unauthenticated requests and forged client-address headers were rejected, including WebSocket upgrades at the gateway. HTTP port 8080 redirects to HTTPS port 8443; the served static index matches the installed package.
- A fresh Chromium session pinned the exact certificate public key, answered the native browser authentication challenge, connected its Mainsail WebSocket, obtained Moonraker version `985c1d0`, and completed its actual initialization list. It reports Klippy disconnected, as expected. Its private disposable browser profile was removed.
- Saved hardware revision 13 and its complete state bytes are unchanged. The managed printer configuration closure still matches the publication receipt. Both owned temporary web/API services are active with the original sv08 user/group and isolation properties.
- Normal printer/recovery/update/nginx masks remain intact and inactive; root and boot remain read-only. No serial device descriptor is open, physical Klipper remains stopped, and the externally observed PSU remains OFF. No G-code, heating, movement or physical calibration occurred.

The authentication files persist in owner data. Web/API services remain current-boot transient units and end at reboot. This repair does not change production boot prerequisites or qualify the physical printer for operation. Owner authentication/TLS assets are host settings, separate from generated hardware configuration; preserve these installed settings rather than replacing them with unprovisioned export seeds.

The [sanitized receipt](mainsail-authentication-20261007.json) records exact operation and acceptance hashes. Private operational artifacts retain full admitted inputs and results without publishing credentials or hardware identities.
