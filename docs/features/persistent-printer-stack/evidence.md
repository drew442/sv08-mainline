# Persistent printer web stack acceptance — 2026-10-09

Owner authorization is recorded in [the request](owner-request.md). This delivery
adds normal boot services for the authenticated printer web stack while preserving
physical Klipper gating. Source is self validated; coordinator-only installed access
and boot transitions receive separate independent consequential assessment.

## Source and image staging

The durable API uses pinned Moonraker `985c1d0`; Mainsail uses its existing packaged
static assets. Web preparation preserves the selected generation's saved hardware
and web settings. Fresh provisioning creates a native account and unique private
retrieval credentials, then a salted Basic gateway and private API-key include.
All HTTPS routes require authentication. Anonymous requests cannot access static
content, API or WebSocket; the loopback API retains forced login. Browser credentials
are stripped upstream and the original client address is forwarded.

Image integration stages the same runtime, wrapper and units, enables API/Mainsail,
and seeds matching web files. Default Debian nginx remains masked. Neither web
unit starts Klipper. Source tests exercise fresh state, retained settings, private
permissions, unknown-account refusal, interrupted publication recovery, storage
refusal and migration of accepted root-owned and quoted-key configuration.
Preparation is ordered after identity because both use the shared storage budget.
Native account creation has a bounded 15-second HTTP allowance; readiness reads
retain a two-second allowance and total authentication startup is bounded.

Focused commands use `SV08_TEST_ROOT=/home/drew/.sv08-persistent-stack-implementation-20261009`:

```sh
python3 -m unittest discover -s tests -p test_web_stack.py -v
python3 -m unittest discover -s tests -p test_host_integration.py -v
python3 -m unittest discover -s tests -p test_host_boot_health.py -v
python3 -m unittest discover -s tests -p test_printer_stack.py -v
git diff --check
```

Web: 16 passed. Host integration: 3 passed. Boot health: 17 passed. Printer stack:
5 passed, two existing pinned-parser environment skips. Unit assertions preserve
hardware exclusion and the identity/authentication dependency chain. Staging tests
use disposable completed-root fixtures and mock initramfs rebuild; they prove the
source staging contract, not a newly assembled flashable image.

## Real packaged offline execution

The integration agent uses a private mount/network/PID namespace and disposable
ARM64 overlay, never changes its lower image, and starts actual packaged Moonraker
and nginx as UID1000 with no Klipper socket. The fixture exercises fresh native
account provisioning, actual HTTP Basic routing, WebSocket upgrade plus RPC,
forwarded client address and two backend restarts. Credential/configuration bytes
and the native account row remain unchanged across restarts. Root-owned group-readable
configuration is admitted without replacement. The final fixture passed on web runtime SHA256
`b140b17437fe4be391c768e536dc7c89acfa4a94519c2782df3e4cb752f6dd0e`.
Fresh authentication took 6.30 seconds under emulation. Anonymous/wrong-password
static/API/WebSocket requests returned401; authenticated static/API returned200;
WebSocket101 and `server.info` RPC passed. Upstream access logging confirmed the
forwarded fixture client address. Two restarts preserved native account rows and
all private/configuration bytes. The fixture used bare keys; quoted-key migration
has targeted source tests and actual installed read-only admission evidence.

Final sanitized receipt SHA256:
`90903a3c6cd6de93b3dc03fc15f567522c3c1fcac0de62e80ae6b811734ef0c4`.
All fixture children exited and mounts were removed. Cumulative fixture runtime
444.72/600 seconds; retained scratch below185KiB. No workstation installs or
physical hardware were involved.

## Installed diagnostic-host acceptance

On test-sv08-01, the coordinator installed seven exact source assets and two normal
boot enablement links after independent operation-specific assessment. Two failed
attempts restored the accepted services and preserved all configuration/auth bytes.
The first exposed identity/web preparation overlap; shared-budget contention was a
source-supported inference. The corrected ordering was then measured successful.
The next exposed rejection of the previously installed quoted API-key syntax; the
parser was corrected and actual existing preparation/authentication admitted without
rewriting private state. Each changed operation received a new bounded assessment;
no unchanged installation retry or additional reset occurred.

Final installation succeeded. Effective units are durable files under
`/etc/systemd/system`, enabled in `multi-user.target.wants`, running as sv08 with
private devices. Measured ordering is identity, web preparation, API, authentication,
then Mainsail. Fresh actual Chromium login/WebSocket initialization and Cockpit
PAM/sudo passed before reboot; both service certificates verified against the
original CA. Anonymous static/API/WebSocket requests were rejected.

ONE normal reboot changed boot ID from
`2e1e3701-e7a3-4999-8fa5-107360d3a8b5` to
`b1fbaf69-26b9-4f1d-a4e8-369b61ff563f`. Diagnostic immutable A returned, the same
persistent generation/state was retained, and automatic commissioning confirmation
restored A3/B0. The non-A-counter logical environment digest remained
`18cdebcbeedbfbb0ef6dce74005f93fdff7a53601a49d0b3b1be3a42e51ad38f`.
Root/boot remain read-only, data writable, all seven production kernel/filesystem
masks remain inactive, no pending trial/update/readiness marker is present, and
no MCU descriptors are open. The PSU stayedOFF. No manual web service start was
performed after reboot; preparation/authentication and both application units passed.

The Wi-Fi DHCP address changed from192.168.1.143 to192.168.1.150; Ethernet remained
192.168.1.141. The first observer's old-Wi-Fi-only timeout was an address assumption,
not a second reboot or failed boot. Reconnection used the original SSH host identity
on Ethernet and revalidated the named disk/boot. All12 configuration/auth files and
all7 installed payload bytes match the admitted snapshots, including the complete
managed hardware bundle. Saved hardware state SHA256 remains
`3141fd19d4b4ad03af96c23fe2d3bd78efd01335191225baf9c6556a94078a39`.

CA fingerprint remains
`d103ff93f8a16cb3c39a4b61d097dc794bbb071ac34ba51fdd02e89b2e70aeaf`;
SSH fingerprint remains `SHA256:76y9QdGAfX0+DOKcexTyVWyaKqJGBBcBLkt63ohj7wU`.
The early boot leaf initially contained hostname/loopback SANs before network
addresses were available. The existing timer triggered automatically at2026-10-09 01:37:21UTC, approximately
10minutes after boot, and regenerated the service leaf for the observed hostname,
FQDN and current addresses. No manual reconciliation or service start was used.
Strict original-CA/SNI verification passed for sv08, sv08.local,
sv08.drewnet.online,192.168.1.141 and192.168.1.150 on both9090 and8443 (10 checks).
Fresh actual Mainsail browser Basic login, WebSocket connection and completed
initialization passed on the new Wi-Fi address. Fresh Cockpit HTTPS/PAM/sudo and
identity view passed at390/1024/1440px. The owner's accepted reconciliation schedule
has not been changed.

Final operation assessment: `/root/identity_install_review`, fixed
high-consequence-reviewer profile (GPT6.1Sol/medium configuration; runtime settings
are not independently observable). Assessment is independent of implementation;
source/offline tests remain self validation. Final quoted-operation packet SHA256
`4913f3d5d94213796b79d600b6f807d3092dce45f2ebaaf9214479ffdbdf764a`,
assessment SHA256 `cec5301a533d435854e20632ef7b1cbb372d801388eb29358771689303be0e59`.
These authorize only the specified transitions under owner scope, not printing or
release. Private operational receipts retain failed/recovered and completed steps;
credentials, API keys, private keys, bundles and hardware identifiers are unpublished.

## Limits

This is source staging, offline packaged execution and named diagnostic-host software
acceptance. It does not qualify physical heating, motion, firmware, calibration,
first print, A/B update, recovery-media rewrite or a flashable release. Existing CA/
SSH identity and the owner's accepted reconciliation schedule are retained.
