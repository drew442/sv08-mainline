# Disposable SD first boot result

Observed 2026-09-25 UTC; record prepared 2026-09-26. Profile:
`test-sv08-01`; board marking
`H616_JC_6Z_V1.2` is owner-reported. The owner inserted the disposable SD in
the printer and connected USB serial for power. The factory eMMC remains stored.

## Observed result

The receive-only serial log contains two starts of the SD-specific SPL/U-Boot
image, whose device-tree model is `Sovol SV08 test-sv08-01 SD network
diagnostic`. This establishes that the H616 selected the removable SD loader on
those starts. The raw serial evidence is retained privately on Beelink; the
public record contains only its sanitized result.

Both starts stopped in U-Boot before launching Linux. The relevant output was:

```text
MMC:   mmc@4020000: 0
Loading Environment from <NULL>... OK
Net:   No ethernet found.
hash - compute hash message digest
Usage: hash algorithm address count [[*]hash_dest]
SV08 SD diagnostic: no verified boot; stop here
CB1@uboot:~$
```

The SD-only U-Boot configuration intentionally has no Ethernet driver and uses
serial console output. Thus the blank HDMI display and `No ethernet found` at
the loader stage are expected; neither shows whether Linux Ethernet works. The
SD script requested `hash -v`, but the compiled U-Boot omitted
`CONFIG_HASH_VERIFY`, so U-Boot rejected the command and never ran the script.
`CONFIG_CMD_HASH` and `CONFIG_SHA256` were enabled. This exact omission is now
required to fail offline config inspection.

The DHCP entry at `192.168.1.141` used the address previously measured on the
printer's Wi-Fi interface. Its wired interface has a different, previously
measured address. The Wi-Fi lease does not establish the current SD boot's
network state. A Beelink-side capture saw no ARP response from `.141` and no
printer traffic to NFS during the observation window. Linux never ran, so wired
link, DHCP, NFS root, and `/data` behavior remain untested.

The private raw log contains two SD U-Boot sequences; the exact physical reason
for the repeated start is unknown. Do not make another boot attempt until the
corrected loader is reviewed, written and read back. The long-running legacy
receive-only reader captured these bytes; a separate fresh reader is now armed
on Beelink after the older reader was stopped. No serial input was sent. The
eMMC environment and attempt counter have not been re-read since this test
began, so do not infer their post-boot values from this log.

## Corrected candidate

The bounded fix enables and enforces `CONFIG_HASH_VERIFY=y` and
`CONFIG_SHA256=y` in
[`sv08-sd-network.fragment`](../../configs/host-os/sv08-sd-network.fragment),
so the already hash-pinned `hash -v sha256` script commands exist in the binary.
All SD boot payloads, server address and read-only NFS policy are otherwise
unchanged. The first v2 file was rejected during review because its composition
receipt contained a stale fragment hash. It was replaced by a fresh run of
`scripts/build_sd_network_image.py` against the corrected tracked fragment.
The new regular-file image is in ignored
`local/sd-network-physical-20260925/sv08-sd-network-v2.img`; its SHA-256 is
`53cc0b2696add39dae24480167d79807e72a15f824fbc9025aaf20a9aa63d08a`. The
matching private receipt is `composition-v2.json`. It records the corrected
fragment hash and effective U-Boot configuration, including
`CONFIG_HASH_VERIFY=y` and `CONFIG_SHA256=y`. Independent review returned
**GO WITH CONDITIONS** for this exact artifact. On 2026-09-26, the coordinator
wrote its 192 MiB prefix to the identified, unmounted SU02G SD card and
completed direct-I/O readback with the exact same hash. The CID and write
transcript remain private on Beelink. The card is ready for the single retry;
the review conditions are recorded in the media write procedure and H09.

See the [media write record](host-sd-network-card-write-20260925.md) and
[coordinated H09 task](coordinated-human-tasks.md).
