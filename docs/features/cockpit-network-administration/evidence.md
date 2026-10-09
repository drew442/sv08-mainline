# Cockpit network administration delivery

Implementation source: `f85857dc5af0ba4158a499501c272e41fe8c8bce`.
Backend SHA-256: `3a45cdcfd4c4a3f2e6843a40170786b75d77c3b7b000aaa53cbfb0772bd36ce4`.
The final evidence commit binds these unchanged implementation bytes.

## Source and browser checks

- `python3 -m unittest discover -s tests -p test_network_admin.py -v`: 16 passed,
  including naming/boot recovery, checkpoint expiry, activation and cleanup
  failure, secret-free transport/status, opaque literal-space SSID credential
  reuse, security-mode changes, corrupt-journal refusal, atomic idle restart,
  certificate failure rollback and real CA/SSH stability with old/new SANs.
- `test_network_ui.py`: actual disposable Chromium journey passed: elevated
  sidebar loading vs limited authority, raw NetworkManager scan security, review
  cancellation, HTTPS/password redaction, saved credentials, IPv4, name/restart,
  confirm/restore, lost response/pending-token recovery, stale authority/navigation
  and 390/1024 layouts.
- `test_host_integration.py`: 3 passed; runtime, timer and root prepare
  post-command staged. NetworkManager's own service lacks CAP_SYS_ADMIN, so boot
  cleanup runs after persistent preparation and before NM/identity startup.
- `test_stage_admin_ui.py`: 18 passed; `test_service_admission.py`: 4 passed;
  existing `test_mainsail_access_ui.py` actual Chromium journey passed.
- JavaScript syntax and complete diff/whitespace checks passed. Two initial
  coordinator test patterns matched zero tests; the correctly named staging and
  service-admission suites above were then run and inspected.

## Actual ARM NetworkManager execution

Disposable full-system QEMU with Linux `6.12.107+deb13-arm64`, NetworkManager
`1.52.1`, restricted user networking, fresh tmpfs data/profiles and synthetic keys.
Nine journeys passed: public saved Wi-Fi metadata/opaque cloning, refused journal
publication without mutation, static IPv4/DNS/confirm/cloning/rollback, live
bind-mounted hosts/hostname/kernel consistency, actual checkpoint expiry/stale
confirmation, injected activation failure recovery, daemon restart recovery,
actual DHCP lease/rollback, and real unchanged CA/SSH with verified new hostname
and IP SANs and Cockpit certificate publication. Final VM and shell exited 0.

The first ARM user-emulation daemon failed on a netlink assertion; full-system
QEMU supplied the required kernel behavior. Real NM exposed and corrected an
unsupported connection filename lookup and the zero-link inode retained by file
bind mounts. The extended DHCP fixture initially assumed a gateway; measured
restricted slirp DHCP advertises no gateway/DNS. The corrected fixture checks the
actual DHCP lease/options and absence of gateway, without claiming Internet
reachability. Final run: 105.437 seconds; cumulative fixture runtime about 421 of
900 seconds, allocated scratch about 76 MiB of 128 MiB.

Private receipt: `/home/drew/.sv08-network-fixture-20261009/integration-evidence.json`.
Receipt and installed hashes are recorded below. Its recorded
source bytes match the committed implementation; no mutable-checkout revision
is presented as a clean tested commit.

## Targeted assessment

A separate `feature_verifier_high` agent inspected the complete bounded diff and
root-secret/rollback/TLS paths, reproduced the boot kernel-name defect, and checked
its corrections. It independently ran the 16 backend and 3 integration checks;
its scratch-ancestry permission failure was corrected in the disposable harness,
and the affected real-CA test then passed without candidate changes. No independent
physical Wi-Fi, reboot, printer or release verification is claimed. The workflow
completion route is self-validation, with this additional targeted assessment.

## Installed acceptance

Installed on `test-sv08-01` diagnostic A through trusted Ethernet SSH with fresh
exact preimage/preservation admission. The separate reviewer passed the bounded
operation assessment after reproducing and checking unique temporary-file cleanup.
Nine assets were installed; the rollback timer is active. The installed older host
app received only the exact hostname-control removal and Network-button exemptions,
preserving unrelated deployed code. The composed printer panel was retained.

Actual HTTPS Cockpit PAM/sudo browser acceptance passed: already-elevated Network
sidebar entry, real Ethernet/Wi-Fi status and saved SSID metadata without passwords,
name/Wi-Fi/restart reviews cancelled, repeated navigation and existing Mainsail
**No login** access retained. Current leaf verified against the original printer CA
and address before using its exact SPKI in disposable Chromium. No connection/name
change, live certificate issuance, restart or printer output was performed.

Post-install checks passed all 38 preserved file hashes, exact installed asset
hashes, active timer, unchanged boot ID, hostname, active interfaces, configuration,
root/boot read-only, printer services masked/inactive and no MCU descriptors. The
historical password-policy baseline had changed before this task; current managed
No login policy was reconciled from read-only status and preserved. Backups are
root-only on persistent storage. This is installed software acceptance; the new
boot cleanup hook was not exercised by rebooting the physical printer.

Private local receipt hashes (no keys/passwords/profile contents published):

- `install.py`: `931adb8e6e1e50e5fe726c3f51875523fe121b5940336d3acf513b237742e728`.
- `packet.json`: `381ba9beaf1cbf1c3d82c77f3f4014ac5da39f54e115fde2d960bf2d0724bc71`.
- `admission-final.json`: `57d85b5e3a114e2a28a1edd77eb1f55fcc5a0fc5ebe73ad76e3fe3947f3c6ae0`.
- `installed.json`: `791091258d545be43aa9673de9ddcb0be8bb36da9f281614aca0044dca33f308`.
- `installed-state.json`: `a175364d79725ebaddd869618287012c2f1ac3f345220e72e98d676e5827779f`.
- `browser-result.json`: `e863053b49cc67d75d40b03d2997aad416a410c1f5d9bdc845c70425462ff371`.
- `tls-proof.json`: `f26c46099ba4bf7cac3bf8432f3ed26fb272e06d259e67f8e702cc10994f63b3`.
- ARM `integration-evidence.json`: `aa818e1248db1ffa545257f75c0cd9b0acd2e6e1f6894816ea4c2d504db92204`.

Independent exact-operation basis: `4bac227375a6dcdfee8a39aa53f3015f77767b2aaa498cac284232fc47aea38e`; canonical packet evidence: `fc21c04a378e2b175781fc0b9b7bf736907b4015f5cf93470ef680151da7620b`.

## Limits

IPv4/open/WPA-personal/WPA3-personal administration is implemented; enterprise,
WEP and an IPv6 editor are outside the form. VM Ethernet/DHCP/crypto and mock
browser evidence do not establish radio association on another network,
physical interruption, assembled boot/reboot rollback or printing qualification.
Current identity reconciliation timing remains owner-accepted. Corrupt journals
are refused rather than automatically repaired. Physical host checks remain open.
