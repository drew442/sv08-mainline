# H10 retry review: read-only SD/NFS diagnostic

Date: 2026-09-26 UTC. Profile: `test-sv08-01`. Review result: **PASS WITH
CONDITIONS** for exactly one supervised read-only boot. This review is not
hardware authorization and does not assert eMMC visibility.

The previous one-boot review was consumed by the attempt recorded in the
[H10 diagnostic record](host-sd-network-emmc-probe-20260926.md). The measured
serial trace reached Linux and DHCP, then failed before the probe because the
default NFSv3 mount returned `Connection refused`. It contains
`mmc0: Failed to initialize a non-removable card`; no eMMC environment or
counter result was produced. The trace SHA-256 is
`89dc52360d9c242d5b5348c3abc1ec3e902ad8bd6dbd7248457ca2108c54d4c5` and is
retained privately on Beelink.

The SD image remains the reviewed, written and read-back-verified artifact
`cea51e9c0731c664563bf16a54fef585f1609ef90da03358eefd4d077b7aab28`. Only the
NFS-served init changed. Source
`tests/fixtures/sd-network-root/init.c` SHA-256 is
`d92230d5252f1ae0c11ebf9785e75953961d6b206de4fac3a96e415cef867468`; the
warnings-as-errors static ARM64 executable is 772,864 bytes with SHA-256
`1e7afa9aaf337ccffdb4c7431648f7aba934dcc600b04e11751743e345e1dc11`, matching
the deployed Beelink file. Its manifest SHA-256 is
`47928b1378278af64a307effe6c35d2ffe54d5b187172f23a4d0e77e5b131007`. The new
locator stays below only `/sys/bus/platform/devices/4022000.mmc/mmc_host`,
accepts one nominal 32 GB MMC, does not assume a Linux `mmcN` index, and keeps
the fixed-offset device access read-only.

Offline checks passed: 10 focused Python/C tests and the existing QEMU kernel /
initramfs NFS-root harness. The QEMU run passed both a reachable read-only NFS
root and the missing-server halt case. On Beelink, mountd versions 1–3 are
registered over TCP/UDP at port 20048; a default NFSv3/TCP mount without an
explicit `mountport` fetched the deployed executable, a write attempt was
refused, and `/var/lib/nfs/etab` showed `192.168.1.141` as `ro,root_squash`.
The local mount originated at Beelink `192.168.1.136`; no printer-sourced NFS
request has yet been observed. mountd registration was restarted manually and
is not persistent, so it must be checked again immediately before the retry.

The independent GPT-6 Sol high-consequence reviewer approved one further
supervised boot with these conditions:

- Immediately before boot, confirm mountd v3/TCP registration, the `.141`
  read-only/root-squash export and deployed init SHA-256 above.
- Arm receive-only serial capture before the serial cable powers the host.
- Permit exactly one SD/NFS boot. Stop on NFS refusal, unexpected boot path,
  absent or ambiguous target, read failure, invalid CRC or unrecognized layout.
- Accept H10 counters only if a unique nominal 32 GB MMC is found beneath
  controller `4022000` and both environment copies pass CRC/layout checks.
- If the non-removable-card initialization failure repeats, do not retry the
  network method; use the existing USB-reader H10 path.

No eMMC, MCU or boot-policy write is included. Factory eMMC remains stored;
the spare remains the installed target. This review authorized one supervised
read-only boot, now completed; see the [measured result](host-sd-network-emmc-probe-20260926.md).
