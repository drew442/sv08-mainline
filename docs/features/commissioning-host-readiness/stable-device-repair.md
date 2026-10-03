# Stable eMMC identity repair

The first normal restart reached Linux and SSH, but the same physical eMMC changed
from mmcblk0 to mmcblk1. The helper refused before its writer because it bound a
boot-local path. The observer shared that assumption and could not report health.
The new boot's failure record and A2/B0 environment are retained; no relay cycle
has run. This is separate from the already repaired historical-bank comparison.

The private target now binds the stable controller alias, exact controller and
raw CID-file SHA256 (including newline). Each probe discovers the current whole
device, sysfs parent and device number, validates GPT/partition/mount identity,
and includes that observed identity in stable-window and post-write comparisons.
The selected tool uses the reviewed stable-alias environment map. Both raw banks
still receive full CRC/parser/policy checks; the old duplicate verifier rejected
symlink targets and is no longer called. No retry, kernel or bootloader change.

All 18 focused tests passed with the selected ARM64 tool (7.937 seconds), including
18 alias-backed regular-file tool cases. Final source passed 17 with the explicit
opt-in tool skip (6.321 seconds); unchanged tool evidence was reused. The historical
full dependency fixture covers positive renumbering and changed device numbers,
wrong CID/controller/partition parent/whole-device/GPT/mount/capacity, alias changes,
and all prior historical-environment negatives. Whitespace/AST/local links passed.

A coordinator read-only candidate probe on the actual new boot passed devices()
and environment() using a temporary /run read map. It verified the observed alias,
CID/controller/GPT/mounts and selected A2/B0 with unchanged bank hashes. It did not
run health/record/writer operations or exercise the new installed helper dependency
hash before installation. The exact three-file patch dry-run also passed.
Independent software and exact action reviews remain required. This is no physical
restart, MCU, printing or release acceptance. Preserve both previous failures.
