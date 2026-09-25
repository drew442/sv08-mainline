# host-sd-network-root: Boot disposable host candidates from SD and NFS

Kind: feature. Author: root/coordinator. Date: 2026-09-25.

## Problem and evidence

Testing each host image currently requires writing the spare eMMC. The owner
provided a 2 GB SD card for a network-root experiment and explicitly allowed
erasing its existing contents. The project has not booted this integrated board
from SD. BIGTREETECH documents SD priority over eMMC for its H616 CB1 eMMC board,
but that related-board behavior is not SV08 evidence. The current pinned U-Boot
device tree has H616 `emac0` disabled, so U-Boot networking is not established.

The 6.18.51 candidate has built-in DHCP autoconfiguration and `DWMAC_SUN8I`;
its initramfs contains NFS/SunRPC modules and Debian's NFS-root script. Their
hashes and limitations are recorded in
[`host-network-boot-investigation.md`](../../hardware/host-network-boot-investigation.md).
The owner-requested hardware profile is `test-sv08-01`, with owner-reported PCB
marking `H616_JC_6Z_V1.2`.

## Intended outcome

Create and offline-validate a disposable SD image whose own SPL/U-Boot loads the
candidate kernel, initramfs and device tree from SD, then lets Linux DHCP mount a
read-only NFS root hosted by Beelink. The network root's mutable state is
volatile. This avoids eMMC rewrites during host-image iteration while preserving
the eMMC as the normal boot source when the card is absent.

This is a development prototype only. It is not a supported recovery feature,
release boot path or proof that SD has priority on the SV08. Do not configure
router PXE/TFTP options. Reserve Beelink's address before any physical test; put
only a reviewed server address in the SD configuration, never credentials.

## Scope and alternatives

Include a regular-file image composer, explicit SD-only U-Boot environment,
hash-bound boot payloads, bounded network/root failure, and disposable ARM64
QEMU validation of the same kernel/initramfs NFS-root flow. Keep U-Boot/network
fetching out of scope. Keep the initial root read-only and `/data` volatile so
tests cannot mutate the installed system or printer state.

Do not modify the installed eMMC, its environment counters, bootloader, printer
MCUs or Beelink's persistent network/export configuration. Do not write the
physical SD as part of the offline implementation task. An independent reviewer
must inspect the image and evidence before the owner-supervised SD write/boot.
The current A-slot trial must first be reconciled under its separate reviewed
procedure; no reboot is authorized by this feature approval. Release signing,
authentication, recovery guarantee, failover and persistent writable state are
excluded. Reconsider release support only after owner review of a separate
proposal and physical power/fallback tests.

## Acceptance and task split

| Check | Task | Acceptance |
| --- | --- | --- |
| snr-01 | implement | Build a regular-file SD image no larger than the measured 2 GB card; static inspection verifies partition/SPL bounds, image hashes, SD-only MMC selection, and that generated commands contain no eMMC writes or environment-counter mutation. |
| snr-02 | implement | Boot the same candidate kernel/initramfs under disposable ARM64 QEMU with an isolated read-only NFS root; prove DHCP, root read-only, volatile `/data`, bounded server-missing failure, and host cleanup. |
| snr-03 | implement | Document exact physical prerequisites and evidence; explicitly leave SD priority, board Ethernet, printer boot, eMMC isolation and release behavior unverified. |

## Human dependencies

After the offline image is independently reviewed, the hardware checklist will
request a reserved Beelink address, an Ethernet connection from printer to the
same LAN, receive-only UART started before power-on, and one supervised SD boot.
That test remains blocked until the current A-slot trial state is reconciled.
Use only the owner-approved spare SD; keep the factory eMMC stored. Existing
human task entry is in
[`host-os-tasks.md`](../../hardware/host-os-tasks.md). No other owner decision
is required for this bounded offline prototype.
