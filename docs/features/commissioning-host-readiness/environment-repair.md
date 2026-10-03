# Installed environment-history repair

The first installed helper refused before its writer. The selected raw dictionary
matched fw_printenv; the previous bank contained different historical non-counter
variables. Both whole bank hashes stayed unchanged. Earlier statements of full
non-counter agreement were incorrect. Original failure evidence is retained.

This bounded repair removes only the pre-write cross-bank equality requirement.
Both banks remain subject to existing eligibility, CRC and flag checks; full tool
output must match the selected bank. Readback still preserves the original selected
bank byte-for-byte and carries all its non-counter values into the new selected
bank. No same-boot retry or failure-record handling code is added.

The full historical dependency fixture now exercises actual admission/run with
old A3 and different/missing/empty/space/equals values, selected A1/A2/A3, selected
mismatch refusals and post-write stale-copy/preserved-bank mutation refusals.
The selected ARM64 libubootenv test exercises actual Runtime.environment across
18 cases with six flag pairs/orientations/wrap and three counters, historical
counter/dictionary differences, both-bank readback and unchanged outside bytes.
Final focused suite: 18 tests passed, including the opt-in real-tool case,
7.882 seconds. Ordinary suite: 17 passed, one opt-in skip. Whitespace and three
local Markdown targets passed. Earlier unchanged theme/overlay/lock/interruption
and software evidence remain scoped to their original candidates.

The three-file code/test/contract diff is independently reviewed separately from
the explicit coordinator failure-record reconciliation and physical operation.
No MCU, heater/motion, restart, release or physical storage behavior is certified
by these synthetic/QEMU tests. Installed access already passed; boot persistence
remains pending. The failed same-boot record is not erased or declared successful.
