# Printer certificate SAN correction — 2026-10-08

The owner reported missing hostname/FQDN/IP subject alternative names. Direct
inspection of both Cockpit LAN endpoints showed the served certificate already
contained `sv08`, `sv08.local`, `192.168.1.141` and `192.168.1.143`; strict TLS
validation with the original printer CA succeeded for both IPs. The missing name
was **sv08.drewnet.online**.

Both DHCP leases supply `drewnet.online`, `/etc/resolv.conf` contains
`search drewnet.online`, and reverse DNS for both addresses returns
`sv08.drewnet.online`. However, the local hosts mapping causes `hostname -f` and
`socket.getfqdn()` to return only `sv08`. Name discovery previously used only
persistent/running hostnames, `.local` variants and global interface addresses.

`runtime/sv08_identity.py` now includes the canonical hostname and qualified
short hostnames derived from configured resolver search/domain suffixes. It
retains the original hostname/IP coverage, deduplicates names and handles a
missing resolver file. Native discovery/CA renewal/TLS regression command:

```
PYTHONPATH=tests:runtime:scripts python3 -m unittest \
  tests.test_identity.InstalledNameTests \
  tests.test_identity.IdentityTests.test_ca_and_ssh_stable_across_boot_and_leaf_renewal \
  tests.test_identity.IdentityTests.test_real_tls_client_trusts_ca_after_server_certificate_replacement
```

**Four tests passed**, 2.969 seconds. `git diff --check` passed.

The exact installed renewal procedure passed independent consequential review
before execution. Its SHA256 is
`e31dc7341793b0cb77f4a65e3f04a32581b1ca6d55eeb7314b31876bddf1ef30`;
packet SHA256 is
`027b5fead50873e6218e2253152ce8bcdaa397d19569ab4a84f997cb50e0cebd`;
review report SHA256 is
`c01ce06d308f54f9cddd53568c14ea49543cbdcd48620e9be9e93af7f63670ea`.
No reviewer hardware access was used; configured review role is Sol/medium,
with runtime settings unobservable. Fresh admission verified PSU OFF, unchanged
printer state, production masks and read-only root/boot. The old runtime,
selector and Cockpit certificate have a private durable rollback copy. A separate
SSH session was retained until fresh reconnect succeeded.

The runtime was installed and the existing identity service reissued/reloaded
service certificates. Final SAN entries are:

- DNS: `localhost`, `sv08`, `sv08.local`, `sv08.drewnet.online`.
- IP: `127.0.0.1`, `::1`, `192.168.1.141`, `192.168.1.143`.

Strict original-CA TLS validation passed for **all five printer names/IPs on both
9090 (Cockpit) and 8443 (Mainsail)**: ten successful connections, with hostname
verification enabled and no certificate-error bypass. Both services offer leaf
SHA256 `5b6bc2060f633089ebd1fc0773090600eae82f6444f445015be0891507daf5af`.
The CA remains
`d103ff93f8a16cb3c39a4b61d097dc794bbb071ac34ba51fdd02e89b2e70aeaf`;
SSH remains `SHA256:76y9QdGAfX0+DOKcexTyVWyaKqJGBBcBLkt63ohj7wU`.
Original owner keys, Mainsail's authentication challenge, root/boot read-only
state, production masks and hardware-state hash
`3141fd19d4b4ad03af96c23fe2d3bd78efd01335191225baf9c6556a94078a39`
are unchanged. No MCU session was opened.

Private operation/results are retained under ignored
`local/feature-workflow/probes/printer-san-fqdn-20261008/`; no private keys,
credentials or certificate bundles are published. This is live certificate
identity acceptance, not a reboot, recovery-media or printing qualification.
The existing printer CA trust continues to apply; clients still need to import
that CA into their trusted authorities.
