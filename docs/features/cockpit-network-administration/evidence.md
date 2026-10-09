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
Receipt and installed hashes are added below after final checks. Its recorded
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

Pending the exact bounded installation and real Cockpit status/review/cancel
journey. The operation changes controls/runtime and registers the rollback timer;
it does not apply a connection/name change, issue a live certificate, reboot,
start Klipper or activate printer outputs. Existing network, login, identity,
configuration, recovery route, read-only mode and printer masks must be preserved.

## Limits

IPv4/open/WPA-personal/WPA3-personal administration is implemented; enterprise,
WEP and an IPv6 editor are outside the form. VM Ethernet/DHCP/crypto and mock
browser evidence do not establish radio association on another network,
physical interruption, assembled boot/reboot rollback or printing qualification.
Current identity reconciliation timing remains owner-accepted. Corrupt journals
are refused rather than automatically repaired. Physical host checks remain open.
