# 0008: Redundant boot environment in reserved image space

Date: 2026-09-10. Status: offline-tested layout candidate; board integration open.

Use two 64 KiB U-Boot environment copies at byte offsets 4 MiB and 8 MiB in the
new image's eMMC user area. Both fit in the 16 MiB leading reservation, outside
the protective MBR, relocated GPT array and provisional SPL reservation. Enforce
these ranges against actual GPT headers, array CRCs and partition extents. These
are new-image allocations, never instructions to write the factory/current image.
The board's U-Boot MMC device index remains unknown.

Use upstream RAUC's U-Boot backend and libubootenv to exchange `BOOT_ORDER` and
bounded attempt counters with upstream RAUC bootmeth. Disable automatic resetting
of all-zero tries. Accept single-slot orders because RAUC removes marked-bad slots
from the order. Dispatch independent recovery when no eligible attempts remain,
the layout marker is absent/wrong, or counters/order are malformed. The layout
marker must exist only in the preseeded persistent environment, never compiled
defaults: otherwise two bad CRCs could masquerade as a fresh installation.

This detects ordinary corruption and supports the upstream redundant-copy write
protocol. It does not establish eMMC power-loss atomicity, protect against a root
owner changing policy, or implement health confirmation. Hardware power-cut tests
and a working recovery OS remain release gates.

Two patches are restricted to the sandbox test build. The first adds MMC to its
hardcoded selectable environment locations. The second retains `size_t` lengths
and offsets when mapping/accessing images larger than 4 GiB; the unpatched driver
could not read the recovery partition in this factory-sized fixture. No H616
board driver is changed. Keep the patches visible and pinned; retire them when
upstream provides equivalent fixes, with the large-image/corruption tests as
proposed upstream regression evidence. No upstream submission has been made.

See [build and test evidence](../hardware/host-environment-build.md), including
limits of sandbox defaults and recovery dispatch. The custom dispatch script
fills the invalid-environment/recovery-policy gap; retire it if the selected
upstream boot policy implements the same checks.
