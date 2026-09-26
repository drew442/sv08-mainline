# Synthetic eMMC CID admission validation

Date: 2026-09-26. Scope: offline test-only helper for the `test-sv08-01`
controller and capacity profile. No printer or block device was accessed.

`tests/fixtures/sd-network-root/emmc_cid_admission.h` adds a CID gate after
the existing metadata locator. The caller must pass a separate, locally trusted
expected CID; its API has no network-job parameter. Both expected and live values
must be exactly 32 lowercase hexadecimal characters. The helper reads the live
CID from the selected card's sysfs directory, requires one matching MMC
candidate, and calls a supplied target-open callback only after admission.
The callback makes the ordering observable in synthetic tests. The existing
read-only diagnostic and production SD/NFS builder do not include this helper.

The format check follows Linux's read-only MMC `cid` sysfs attribute
([kernel documentation](https://docs.kernel.org/6.2/driver-api/mmc/mmc-dev-attrs.html),
accessed 2026-09-26) and upstream Linux `drivers/mmc/core/mmc.c`, which formats
four raw CID words using `%08x` followed by a newline
([current source](https://github.com/torvalds/linux/blob/6812ce4e4379ffc99c52401ec28f0d7ffbc36206/drivers/mmc/core/mmc.c),
accessed 2026-09-26). This source observation does not establish the behavior
of a future pinned printer kernel; that pin must be checked at integration.

Validation completed offline:

* `python3 -m unittest tests.test_sd_network_cid_admission tests.test_sd_network_env_probe tests.test_sd_network_image -q` — 13 tests passed. The native C spy reports zero target-open callbacks for missing, malformed, mismatched, wrong-type, wrong-capacity, and ambiguous synthetic inventory. An exact match calls it once. The API accepts the expected CID as a separate argument and has no network-job parameter. This slice has no network-job parser, so it does not claim to test end-to-end descriptor handling.
* The test command also compiled the helper and fixture as a static AArch64 binary with `aarch64-linux-gnu-gcc -static -std=c11 -Wall -Wextra -Werror`; compilation passed. It was not executed on ARM64.
* The existing locator and SD/NFS builder tests passed without changing either source. The synthetic CIDs (`00000000000000000000000000000001` and `00000000000000000000000000000002`) are deliberately fake.

This is a testable admission prerequisite, not a production writer or a verified
printer identity. Trusted expected-CID provisioning, binding the selected sysfs
identity to the exact opened device despite enumeration changes, and a live CID
comparison remain future work under [H12](coordinated-human-tasks.md). The
test-only helper may be integrated into a reviewed writer adapter or retired in
favor of an equivalent upstream mechanism. It grants no physical write or
release authority.
