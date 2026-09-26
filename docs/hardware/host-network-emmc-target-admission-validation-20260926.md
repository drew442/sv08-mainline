# H616 eMMC admission offline validation

Date: 2026-09-26. Profile: `test-sv08-01`, measured H10 controller and module
capacity only. This record covers offline source and synthetic sysfs checks.

The reusable locator in `tests/fixtures/sd-network-root/emmc_locator.h` accepts
only one `MMC` card beneath the H616 controller path and the measured capacity
of 61,079,552 sectors. It rejects missing or malformed metadata, capacity
mismatch, multiple MMC candidates, and failed directory enumeration. Unrelated
SD/SDIO devices remain ignored. It reads sysfs only and returns a path for the
existing bounded read-only environment probe; it does not open any block node.
The builder's input receipt now includes the locator header hash beside the
probe source hash.

Validation completed offline:

* `python3 -m unittest tests.test_sd_network_env_probe tests.test_sd_network_image -v` — 10 tests passed, including synthetic host numbering, SD exclusion, exact capacity, malformed and absent metadata, ambiguous MMC inventory, read-only access contract, and SD/NFS image boot-policy checks.
* `aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -Werror -D_FORTIFY_SOURCE=2 -o /tmp/sd-network-init-target-admission tests/fixtures/sd-network-root/init.c` — successful static AArch64 compile.
* `python3 -m py_compile scripts/build_sd_network_image.py tests/test_sd_network_env_probe.py` — passed.
* `git diff --check` — passed.

No SD image was composed or booted during this validation. The builder source
manifest change is tested by source contract checks and has not been validated
in a newly composed image. No printer, eMMC block node, boot policy, or hardware
was accessed or changed. H10 did not record CID, so the locator cannot prove
unique module identity, data preservation, rollback, or physical write safety.
The full-eMMC writer remains separately gated by H12, an exact reviewed image
and target, recovery plan, and authorization.
