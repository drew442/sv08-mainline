# Read-only H616 eMMC target admission

Date: 2026-09-26. Scope: offline diagnostic source and synthetic sysfs tests for
`test-sv08-01`. This is a metadata locator, not a physical write procedure.

The [H10 supervised probe](host-sd-network-emmc-probe-20260926.md) reported
`/dev/mmcblk0` under the H616 `4022000.mmc` controller with exactly 61,079,552
512-byte sectors. Its read-only environment pair passed CRC/layout checks.
H10 did **not** record the card CID. The controller, card type, capacity, and a
single candidate therefore do not establish the unique identity of the installed
module, its contents, or its suitability for a write.

`tests/fixtures/sd-network-root/emmc_locator.h` factors the probe's sysfs
lookup into a reusable metadata-only helper. It requires one `MMC` card under
`/sys/bus/platform/devices/4022000.mmc/mmc_host`, a single main user-area
`mmcblkN` entry, and exactly 61,079,552 sectors. It does not assume a stable
Linux `mmc_host` number. Additional MMC cards, unreadable/unknown card metadata,
malformed sizes, and a size different from H10 fail closed. SD and SDIO cards
under the controller are ignored. The returned `/dev/mmcblkN` string is only a
read-only probe input; the helper never opens a block node.

The existing diagnostic includes this helper and still opens the selected block
node read-only for its two bounded environment reads. The SD image builder now
records both the diagnostic source and included helper hash in its input receipt;
it adds no writer. Synthetic sysfs tests exercise host numbering, unrelated SD,
wrong controller/type, exact capacity, malformed numbers, missing metadata, and
ambiguous inventory. These offline fixtures do not validate physical module
identity, data preservation, rollback, or eMMC write safety. A different module
capacity needs a reviewed profile value. [H12](coordinated-human-tasks.md)
remains the separate gate for any whole-eMMC write, with exact artifact and
target review, recovery, and authorization.
